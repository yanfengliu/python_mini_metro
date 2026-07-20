import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { CIV_ENGINE_PIN, resolveCivEnginePinRoot } from './civ-engine-pin.mjs';
import { assertCleanNodeStartup } from './node-startup-contract.mjs';

const VERIFICATION_LEASES = new WeakMap();

export function parseSetupArgs(argv) {
  if (!Array.isArray(argv)) throw setupArgsError();
  if (argv.length === 0) return { mode: 'setup', allowDirty: false };
  if (argv.length === 1 && argv[0] === '--verify-only') {
    return { mode: 'verify', allowDirty: false };
  }
  if (
    argv.length === 2
    && argv[0] === '--verify-only'
    && argv[1] === '--allow-dirty'
  ) {
    return { mode: 'verify', allowDirty: true };
  }
  throw setupArgsError();
}

export function resolveSetupRepoRoot() {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
}

export async function runCivEngineSetupEntryPoint({
  argv,
  nodeOptions = process.env.NODE_OPTIONS,
  execArgv = process.execArgv,
  runSetup = runCivEngineSetup,
} = {}) {
  assertCleanNodeStartup({ nodeOptions, execArgv });
  return runSetup({ argv });
}

export async function runCivEngineSetup({
  repoRoot = resolveSetupRepoRoot(),
  argv = [],
  operations,
} = {}) {
  const root = path.resolve(repoRoot);
  const options = parseSetupArgs(argv);
  const setupOperations = operations ?? await loadDefaultOperations();
  if (options.mode === 'verify') {
    await setupOperations.assertNoActiveSetupLock({ repoRoot: root });
    return setupOperations.verifyOnly({
      repoRoot: root,
      allowDirty: options.allowDirty,
      pin: CIV_ENGINE_PIN,
    });
  }

  const pinRoot = resolveCivEnginePinRoot(root);
  let lock;
  let transaction;
  let primaryError;
  let preserveTransaction = false;
  try {
    await setupOperations.validateRepositoryContract({
      repoRoot: root,
      pinRoot,
      pin: CIV_ENGINE_PIN,
    });
    lock = await setupOperations.acquireSetupLock({ repoRoot: root });
    transaction = await setupOperations.createSetupTransaction({ repoRoot: root });
    const state = await setupOperations.classifyPin({
      repoRoot: root,
      pinRoot,
      pin: CIV_ENGINE_PIN,
    });
    if (state.kind === 'suspicious') {
      throw Object.assign(
        new Error('existing civ-engine checkout is not safe to replace'),
        { code: 'ERR_CIV_ENGINE_SETUP_REFUSED' },
      );
    }
    if (state.kind !== 'missing' && state.kind !== 'exact') {
      throw Object.assign(new Error('unknown civ-engine setup state'), {
        code: 'ERR_CIV_ENGINE_SETUP_REFUSED',
      });
    }

    let candidateRoot = pinRoot;
    let needsPromotion = false;
    if (state.kind === 'missing') {
      candidateRoot = transaction.checkoutPath;
      needsPromotion = true;
      await setupOperations.clonePinnedRepository({
        repoRoot: root,
        repositoryUrl: CIV_ENGINE_PIN.repositoryUrl,
        commit: CIV_ENGINE_PIN.commit,
        destination: candidateRoot,
        transaction,
      });
    }
    await setupOperations.auditPin({
      repoRoot: root,
      checkoutRoot: candidateRoot,
      pin: CIV_ENGINE_PIN,
      transaction,
    });
    const runtimeExact = await setupOperations.explicitRuntimeIsExact({
      repoRoot: root,
      checkoutRoot: candidateRoot,
      pin: CIV_ENGINE_PIN,
    });
    if (!runtimeExact) {
      await setupOperations.installPinDependencies({
        repoRoot: root,
        checkoutRoot: candidateRoot,
        transaction,
      });
      await setupOperations.buildPin({
        repoRoot: root,
        checkoutRoot: candidateRoot,
        transaction,
      });
      await setupOperations.verifyExplicitPin({
        repoRoot: root,
        checkoutRoot: candidateRoot,
        pin: CIV_ENGINE_PIN,
      });
    }
    if (needsPromotion) {
      await setupOperations.promotePin({
        repoRoot: root,
        source: candidateRoot,
        destination: pinRoot,
        transaction,
      });
      try {
        await setupOperations.auditPin({
          repoRoot: root,
          checkoutRoot: pinRoot,
          pin: CIV_ENGINE_PIN,
          transaction,
        });
      } catch (error) {
        if (error && typeof error === 'object') {
          error.preserveSetupTransaction = true;
        }
        throw error;
      }
    }
    const rootDependency = await setupOperations.classifyRootDependency({
      repoRoot: root,
      pinRoot,
      pin: CIV_ENGINE_PIN,
    });
    if (rootDependency.kind === 'repairable') {
      await setupOperations.installRootDependency({
        repoRoot: root,
        pinRoot,
        transaction,
      });
    } else if (rootDependency.kind !== 'exact') {
      throw Object.assign(new Error('unsafe civ-engine package resolution'), {
        code: 'ERR_CIV_ENGINE_RESOLUTION_SHADOW',
      });
    }
    return await setupOperations.verifyDefaultPin({
      repoRoot: root,
      pinRoot,
      pin: CIV_ENGINE_PIN,
    });
  } catch (error) {
    primaryError = error;
    preserveTransaction = error?.preserveSetupTransaction === true;
    throw error;
  } finally {
    const recoveryErrors = [];
    if (transaction && !preserveTransaction) {
      try {
        await setupOperations.cleanupSetupTransaction(transaction);
      } catch (error) {
        recoveryErrors.push(error);
      }
    }
    if (lock) {
      try {
        await setupOperations.releaseSetupLock(lock);
      } catch (error) {
        recoveryErrors.push(error);
      }
    }
    if (recoveryErrors.length > 0) {
      if (!primaryError && recoveryErrors.length === 1) throw recoveryErrors[0];
      const failures = primaryError
        ? [primaryError, ...recoveryErrors]
        : recoveryErrors;
      const aggregate = new AggregateError(
        failures,
        primaryError
          ? `civ-engine setup failed: ${safeErrorMessage(primaryError)}; recovery was incomplete`
          : 'civ-engine setup recovery failed',
        primaryError ? { cause: primaryError } : undefined,
      );
      aggregate.code = primaryError?.code ?? 'ERR_CIV_ENGINE_SETUP_RECOVERY';
      throw aggregate;
    }
  }
}

export function verifyCivEngineSetup({
  allowDirty = false,
  repoRoot = resolveSetupRepoRoot(),
} = {}) {
  const argv = allowDirty
    ? ['--verify-only', '--allow-dirty']
    : ['--verify-only'];
  return runCivEngineSetup({ repoRoot, argv });
}

export async function acquireCivEngineVerificationLease({
  repoRoot = resolveSetupRepoRoot(),
  operations,
} = {}) {
  const root = path.resolve(repoRoot);
  const setupOperations = operations ?? await loadDefaultOperations();
  const lock = await setupOperations.acquireSetupLock({ repoRoot: root });
  const lease = Object.freeze({ repoRoot: root });
  VERIFICATION_LEASES.set(lease, { lock, operations: setupOperations });
  return lease;
}

export async function verifyCivEngineSetupUnderLease({
  repoRoot = resolveSetupRepoRoot(),
  allowDirty = false,
  lease,
} = {}) {
  const root = path.resolve(repoRoot);
  const state = VERIFICATION_LEASES.get(lease);
  if (!state || !samePath(root, lease.repoRoot)) throw leaseError();
  await state.operations.assertSetupLockOwnership(state.lock);
  const result = await state.operations.verifyOnly({
    repoRoot: root,
    allowDirty,
    pin: CIV_ENGINE_PIN,
  });
  await state.operations.assertSetupLockOwnership(state.lock);
  return result;
}

export async function releaseCivEngineVerificationLease(lease) {
  const state = VERIFICATION_LEASES.get(lease);
  if (!state) throw leaseError();
  await state.operations.releaseSetupLock(state.lock);
  VERIFICATION_LEASES.delete(lease);
}

async function loadDefaultOperations() {
  const module = await import('./civ-engine-setup-operations.mjs');
  return module.createSetupOperations();
}

function setupArgsError() {
  return Object.assign(
    new Error('usage: node scripts/civ-engine-setup.mjs [--verify-only [--allow-dirty]]'),
    { code: 'ERR_CIV_ENGINE_SETUP_ARGS' },
  );
}

function leaseError() {
  return Object.assign(new Error('invalid or inactive civ-engine verification lease'), {
    code: 'ERR_CIV_ENGINE_SETUP_LEASE',
  });
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function safeErrorMessage(error) {
  return String(error?.message ?? 'unknown setup failure')
    .replace(/https?:\/\/[^\s/@:]+:[^\s/@]+@/gi, 'https://[redacted]@')
    .replace(/(token|password|secret|authorization)\s*[:=]\s*\S+/gi, '$1=[redacted]')
    .trim()
    .slice(0, 1024);
}

function isMainModule() {
  return Boolean(process.argv[1])
    && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
}

if (isMainModule()) {
  runCivEngineSetupEntryPoint({ argv: process.argv.slice(2) })
    .then(() => {
      process.stdout.write('civ-engine setup verified\n');
    })
    .catch((error) => {
      process.stderr.write(`${error?.message ?? 'civ-engine setup failed'}\n`);
      process.exitCode = 1;
    });
}
