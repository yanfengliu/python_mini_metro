import fs from 'node:fs/promises';
import path from 'node:path';

import {
  CIV_ENGINE_PIN,
  resolveCivEnginePinRoot,
} from './civ-engine-pin.mjs';
import { resolveInstalledCivEngine, samePath } from './civ-engine-runtime.mjs';
import {
  planPinnedTypeScriptBuild,
  removePinnedBuildOutput,
} from './civ-engine-setup-build.mjs';
import {
  authenticateCheckoutContent,
  authenticateDirtyCanaryCheckoutShape,
} from './civ-engine-setup-content.mjs';
import { clonePinnedRepository } from './civ-engine-setup-clone.mjs';
import {
  buildSetupEnvironment,
  planNpmInvocation,
  resolveTrustedNpmExecutable,
  runSetupProcess,
} from './civ-engine-setup-process.mjs';
import { publishOwnedDirectory } from './civ-engine-setup-promotion.mjs';
import {
  acquireSetupLock,
  assertNoActiveSetupLock,
  assertSetupLockOwnership,
  assertSafeGeneratedTree,
  auditCheckoutMetadata,
  classifyRootDependencyRepair,
  classifySetupState,
  cleanupSetupTransaction,
  createSetupTransaction,
  releaseSetupLock,
} from './civ-engine-setup-safety.mjs';
import { validateRootInstallContract } from './civ-engine-setup-root-contract.mjs';
import {
  assertCivEngineStateAllowed,
  captureCivEngineState,
} from './source-provenance-engine.mjs';

export {
  resolveTrustedGitExecutable,
  resolveTrustedNpmExecutable,
} from './civ-engine-setup-process.mjs';
export { clonePinnedRepository } from './civ-engine-setup-clone.mjs';

export function createSetupOperations() {
  return {
    validateRepositoryContract,
    assertNoActiveSetupLock,
    acquireSetupLock,
    assertSetupLockOwnership,
    createSetupTransaction,
    classifyPin: classifySetupState,
    clonePinnedRepository,
    auditPin,
    explicitRuntimeIsExact,
    installPinDependencies,
    buildPin,
    verifyExplicitPin,
    promotePin,
    classifyRootDependency,
    installRootDependency,
    verifyDefaultPin,
    verifyOnly,
    cleanupSetupTransaction,
    releaseSetupLock,
  };
}

export async function validateRepositoryContract({ repoRoot, pin = CIV_ENGINE_PIN }) {
  return validateRootInstallContract({ repoRoot, pin });
}

export async function auditPin({ checkoutRoot, pin = CIV_ENGINE_PIN }) {
  const result = await auditCheckoutMetadata({
    checkoutRoot,
    expectedCommit: pin.commit,
    expectedRepositoryUrl: pin.repositoryUrl,
  });
  await authenticateCheckoutContent({ checkoutRoot, expectedCommit: pin.commit });
  await Promise.all([
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'dist'),
      label: 'civ-engine dist',
    }),
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'node_modules'),
      label: 'civ-engine node_modules',
    }),
  ]);
  return result;
}

export async function explicitRuntimeIsExact({ repoRoot, checkoutRoot }) {
  const state = await captureExplicitState(repoRoot, checkoutRoot);
  try {
    assertCivEngineStateAllowed(state);
    return true;
  } catch (error) {
    if (error?.code === 'ERR_CIV_ENGINE_PROVENANCE') return false;
    throw error;
  }
}

export async function installPinDependencies({
  checkoutRoot,
  transaction,
  pin = CIV_ENGINE_PIN,
  planNpm = npmPlan,
  runProcess = runSetupProcess,
}) {
  await authenticateCheckoutContent({ checkoutRoot, expectedCommit: pin.commit });
  const plan = await planNpm({
    cwd: checkoutRoot,
    transaction,
    args: ['ci', '--ignore-scripts', '--no-audit', '--no-fund'],
  });
  runProcess(plan, { phase: 'civ-engine dependency install' });
  await assertSafeGeneratedTree({
    ownerRoot: checkoutRoot,
    treeRoot: path.join(checkoutRoot, 'node_modules'),
    label: 'civ-engine node_modules',
  });
}

export async function buildPin({
  checkoutRoot,
  transaction,
  pin = CIV_ENGINE_PIN,
  planBuild = planPinnedTypeScriptBuild,
  runProcess = runSetupProcess,
}) {
  await authenticateCheckoutContent({ checkoutRoot, expectedCommit: pin.commit });
  await removePinnedBuildOutput({ checkoutRoot });
  await authenticateCheckoutContent({ checkoutRoot, expectedCommit: pin.commit });
  const plan = await planBuild({
    checkoutRoot,
    homePath: transaction.homePath,
    tempPath: transaction.tempPath,
  });
  runProcess(plan, { phase: 'direct civ-engine TypeScript build' });
  await Promise.all([
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'dist'),
      label: 'civ-engine dist',
    }),
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'node_modules'),
      label: 'civ-engine node_modules',
    }),
  ]);
}

export async function verifyExplicitPin({ repoRoot, checkoutRoot }) {
  return assertCivEngineStateAllowed(await captureExplicitState(repoRoot, checkoutRoot));
}

export async function promotePin({
  source,
  destination,
  transaction,
  fileSystem,
}) {
  return publishOwnedDirectory({ source, destination, transaction, fileSystem });
}

export async function classifyRootDependency({ repoRoot, pinRoot }) {
  await auditRootNodeModules({ repoRoot, pinRoot, requireExactSlot: false });
  const rootSlot = path.join(repoRoot, 'node_modules', CIV_ENGINE_PIN.packageName);
  let resolution;
  try {
    resolution = resolveInstalledCivEngine(CIV_ENGINE_PIN.packageName);
  } catch (error) {
    if (error?.code !== 'ERR_MODULE_NOT_FOUND') throw error;
    return classifyRootDependencyRepair({
      repoRoot,
      expectedPinRoot: pinRoot,
      requestedPackagePath: rootSlot,
      resolvedPackageRoot: null,
    });
  }
  let rootSlotTarget = null;
  try {
    rootSlotTarget = await fs.realpath(rootSlot);
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error;
  }
  const requestedPackagePath = (
    samePath(resolution.packageRoot, rootSlot)
    || (rootSlotTarget && samePath(resolution.packageRoot, rootSlotTarget))
  ) ? rootSlot : resolution.packageRoot;
  return classifyRootDependencyRepair({
    repoRoot,
    expectedPinRoot: pinRoot,
    requestedPackagePath,
    resolvedPackageRoot: await fs.realpath(resolution.packageRoot),
  });
}

export async function installRootDependency({
  repoRoot,
  pinRoot,
  pin = CIV_ENGINE_PIN,
  createRootLink = fs.symlink,
}) {
  await validateRepositoryContract({ repoRoot, pin });
  await auditRootNodeModules({ repoRoot, pinRoot, requireExactSlot: false });
  await validateRepositoryContract({ repoRoot, pin });
  await repairRootDependencyLink({ repoRoot, pinRoot, createRootLink });
  await auditRootNodeModules({ repoRoot, pinRoot, requireExactSlot: true });
  await validateRepositoryContract({ repoRoot, pin });
}

export async function verifyDefaultPin({ repoRoot, pinRoot }) {
  const rootDependency = await classifyRootDependency({ repoRoot, pinRoot });
  if (rootDependency.kind !== 'exact') {
    throw setupError('ERR_CIV_ENGINE_RESOLUTION_SHADOW', 'default civ-engine resolution is not the pinned root');
  }
  return assertCivEngineStateAllowed(await captureCivEngineState({ repoRoot }));
}

export async function verifyOnly({ repoRoot, allowDirty = false, pin = CIV_ENGINE_PIN }) {
  await validateRepositoryContract({ repoRoot, pin });
  const pinRoot = resolveCivEnginePinRoot(repoRoot, pin);
  const state = await classifySetupState({
    repoRoot,
    pinRoot,
    expectedCommit: pin.commit,
    expectedRepositoryUrl: pin.repositoryUrl,
    allowDirty,
  });
  if (state.kind !== 'exact') {
    throw setupError(
      'ERR_CIV_ENGINE_SETUP_REFUSED',
      state.reason ?? 'pinned civ-engine checkout is unavailable',
    );
  }
  if (allowDirty) {
    await authenticateDirtyCanaryCheckoutShape({
      checkoutRoot: pinRoot,
      expectedCommit: pin.commit,
      expectedRepositoryUrl: pin.repositoryUrl,
    });
  } else {
    await authenticateCheckoutContent({
      checkoutRoot: pinRoot,
      expectedCommit: pin.commit,
      expectedRepositoryUrl: pin.repositoryUrl,
    });
  }
  await Promise.all([
    assertSafeGeneratedTree({
      ownerRoot: pinRoot,
      treeRoot: path.join(pinRoot, 'dist'),
      label: 'civ-engine dist',
    }),
    assertSafeGeneratedTree({
      ownerRoot: pinRoot,
      treeRoot: path.join(pinRoot, 'node_modules'),
      label: 'civ-engine node_modules',
    }),
  ]);
  const dependency = await classifyRootDependency({ repoRoot, pinRoot });
  if (dependency.kind !== 'exact') {
    throw setupError('ERR_CIV_ENGINE_RESOLUTION_SHADOW', 'root civ-engine dependency needs repair');
  }
  return assertCivEngineStateAllowed(
    await captureCivEngineState({ repoRoot }),
    { allowDirty },
  );
}

async function captureExplicitState(repoRoot, checkoutRoot) {
  return captureCivEngineState({
    repoRoot,
    enginePackageRoot: checkoutRoot,
    expectedEnginePackageRoot: checkoutRoot,
  });
}

async function npmPlan({ cwd, transaction, args }) {
  const pathValue = path.dirname(process.execPath);
  const environment = buildSetupEnvironment({
    sourceEnv: process.env,
    homePath: transaction.homePath,
    tempPath: transaction.tempPath,
    npmUserConfigPath: transaction.npmUserConfigPath,
    npmGlobalConfigPath: transaction.npmGlobalConfigPath,
    pathValue,
  });
  const options = {
    npmArgs: args,
    cwd,
    env: environment,
  };
  if (process.platform !== 'win32') {
    options.npmExecutablePath = await resolveTrustedNpmExecutable();
  }
  return planNpmInvocation(options);
}

async function auditGeneratedTrees(checkoutRoot) {
  await Promise.all([
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'dist'),
      label: 'civ-engine dist',
    }),
    assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'node_modules'),
      label: 'civ-engine node_modules',
    }),
  ]);
}

async function auditRootNodeModules({ repoRoot, pinRoot, requireExactSlot }) {
  const nodeModulesRoot = path.join(repoRoot, 'node_modules');
  if (!await pathExists(nodeModulesRoot)) {
    if (requireExactSlot) {
      throw setupError(
        'ERR_CIV_ENGINE_SETUP_UNSAFE',
        'root node_modules is missing after exact-link repair',
      );
    }
    return;
  }
  await assertPhysicalDirectory(nodeModulesRoot, 'root node_modules');
  const entries = await fs.readdir(nodeModulesRoot);
  let foundSlot = false;
  for (const name of entries) {
    const candidate = path.join(nodeModulesRoot, name);
    if (name === '.package-lock.json') {
      await assertPhysicalFile(candidate, 'root node_modules lock metadata');
      continue;
    }
    if (name !== CIV_ENGINE_PIN.packageName) {
      throw setupError(
        'ERR_CIV_ENGINE_SETUP_UNSAFE',
        'root node_modules contains an unexpected entry',
      );
    }
    foundSlot = true;
    const metadata = await fs.lstat(candidate);
    if (!metadata.isSymbolicLink()) {
      throw setupError(
        'ERR_CIV_ENGINE_SETUP_UNSAFE',
        'root civ-engine dependency slot must be a link',
      );
    }
    if (
      requireExactSlot
      && !samePath(await fs.realpath(candidate), await fs.realpath(pinRoot))
    ) {
      throw setupError('ERR_CIV_ENGINE_SETUP_UNSAFE', 'root dependency link has the wrong target');
    }
  }
  if (requireExactSlot && !foundSlot) {
    throw setupError('ERR_CIV_ENGINE_SETUP_UNSAFE', 'exact-link repair omitted the root dependency');
  }
}

async function repairRootDependencyLink({ repoRoot, pinRoot, createRootLink }) {
  const nodeModulesRoot = path.join(repoRoot, 'node_modules');
  const rootSlot = path.join(nodeModulesRoot, CIV_ENGINE_PIN.packageName);
  const containerIdentity = await ensurePhysicalDirectory(nodeModulesRoot, 'root node_modules');
  await assertPhysicalDirectory(pinRoot, 'pinned civ-engine root');
  let slotMetadata = null;
  try {
    slotMetadata = await fs.lstat(rootSlot);
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error;
  }
  if (slotMetadata) {
    if (!slotMetadata.isSymbolicLink()) {
      throw setupError(
        'ERR_CIV_ENGINE_SETUP_UNSAFE',
        'root civ-engine dependency slot must be a link',
      );
    }
    try {
      if (samePath(await fs.realpath(rootSlot), await fs.realpath(pinRoot))) return;
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
    throw setupError(
      'ERR_CIV_ENGINE_SETUP_UNSAFE',
      'existing root dependency link is not safe to replace',
    );
  }
  await assertSameDirectoryIdentity(nodeModulesRoot, containerIdentity);
  try {
    await createRootLink(
      pinRoot,
      rootSlot,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
  } catch (error) {
    if (error?.code === 'EEXIST') {
      throw setupError(
        'ERR_CIV_ENGINE_SETUP_UNSAFE',
        'root dependency slot changed during exact-link repair',
      );
    }
    throw error;
  }
  await assertSameDirectoryIdentity(nodeModulesRoot, containerIdentity);
}

async function ensurePhysicalDirectory(candidate, label) {
  try {
    await fs.mkdir(candidate);
  } catch (error) {
    if (error?.code !== 'EEXIST') throw error;
  }
  return assertPhysicalDirectory(candidate, label);
}

async function assertSameDirectoryIdentity(candidate, expected) {
  const current = await assertPhysicalDirectory(candidate, 'root node_modules');
  if (current.dev !== expected.dev || current.ino !== expected.ino) {
    throw setupError(
      'ERR_CIV_ENGINE_SETUP_UNSAFE',
      'root node_modules identity changed during exact-link repair',
    );
  }
}

async function assertPhysicalDirectory(candidate, label) {
  const [metadata, physical] = await Promise.all([
    fs.lstat(candidate, { bigint: true }),
    fs.realpath(candidate),
  ]);
  if (!metadata.isDirectory() || metadata.isSymbolicLink() || !samePath(candidate, physical)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_UNSAFE', `${label} must be a physical directory`);
  }
  return metadata;
}

async function assertPhysicalFile(candidate, label) {
  const [metadata, physical] = await Promise.all([fs.lstat(candidate), fs.realpath(candidate)]);
  if (!metadata.isFile() || metadata.isSymbolicLink() || !samePath(candidate, physical)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_UNSAFE', `${label} must be a physical file`);
  }
}

async function pathExists(candidate) {
  try {
    await fs.lstat(candidate);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}

function setupError(code, message) {
  return Object.assign(new Error(message), { code });
}
