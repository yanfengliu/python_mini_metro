import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import * as setupModule from '../scripts/civ-engine-setup.mjs';
import { CIV_ENGINE_PIN } from '../scripts/civ-engine-pin.mjs';
import {
  phaseNames,
  setupOperationHarness,
} from './civ-engine-setup-fixtures.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const {
  parseSetupArgs,
  resolveSetupRepoRoot,
  runCivEngineSetup,
} = setupModule;

test('setup entry point shares the clean Node startup boundary before effects', async () => {
  const cases = [
    {
      nodeOptions: '--import=data:text/javascript,globalThis.secretSetupEnv=true',
      execArgv: [],
    },
    {
      nodeOptions: '',
      execArgv: [
        '--import=data:text/javascript,globalThis.secretSetupArgv=true',
      ],
    },
  ];

  for (const startup of cases) {
    let setupStarted = false;
    await assert.rejects(
      setupModule.runCivEngineSetupEntryPoint({
        argv: ['--verify-only'],
        ...startup,
        runSetup: async () => { setupStarted = true; },
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_NODE_STARTUP'
        && error.message === 'public Node entry point requires clean startup'
        && (!startup.nodeOptions || !error.message.includes(startup.nodeOptions))
        && startup.execArgv.every((argument) => !error.message.includes(argument))
      ),
    );
    assert.equal(setupStarted, false);
  }

  let cleanOptions;
  await setupModule.runCivEngineSetupEntryPoint({
    argv: ['--verify-only'],
    nodeOptions: '',
    execArgv: [],
    runSetup: async (options) => { cleanOptions = options; },
  });
  assert.deepEqual(cleanOptions, { argv: ['--verify-only'] });
});

test('setup argv accepts only setup strict verify and recursive canary modes', () => {
  assert.deepEqual(parseSetupArgs([]), { mode: 'setup', allowDirty: false });
  assert.deepEqual(parseSetupArgs(['--verify-only']), {
    mode: 'verify',
    allowDirty: false,
  });
  assert.deepEqual(parseSetupArgs(['--verify-only', '--allow-dirty']), {
    mode: 'verify',
    allowDirty: true,
  });

  for (const candidate of [
    ['--allow-dirty'],
    ['--allow-dirty', '--verify-only'],
    ['--verify-only', '--verify-only'],
    ['--verify-only', '--allow-dirty', '--force'],
    ['--url', CIV_ENGINE_PIN.repositoryUrl],
    ['--path', '.civ-engine-pin'],
    ['--ref', CIV_ENGINE_PIN.commit],
    ['--repair'],
    ['--force'],
    ['--'],
  ]) {
    assert.throws(
      () => parseSetupArgs(candidate),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_ARGS',
      candidate.join(' '),
    );
  }
});

test('setup repository root comes from the module location rather than cwd', () => {
  assert.equal(resolveSetupRepoRoot(), repoRoot);
  const moduleUrl = pathToFileURL(path.join(
    repoRoot,
    'scripts',
    'civ-engine-setup.mjs',
  )).href;
  for (const cwd of [path.join(repoRoot, 'scripts'), path.join(repoRoot, 'test')]) {
    const child = spawnSync(process.execPath, [
      '--input-type=module',
      '-e',
      `import { resolveSetupRepoRoot } from ${JSON.stringify(moduleUrl)}; `
      + 'console.log(resolveSetupRepoRoot());',
    ], {
      cwd,
      encoding: 'utf8',
      shell: false,
    });
    assert.equal(child.status, 0, child.stderr || child.stdout);
    assert.equal(child.stdout.trim(), repoRoot);
  }
});

test('missing setup uses only descriptor authority and preserves phase order', async () => {
  const harness = setupOperationHarness();
  await runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations });

  assert.deepEqual(phaseNames(harness), [
    'validate-contract',
    'acquire-lock',
    'create-transaction',
    'classify-pin',
    'clone-pin',
    'audit-pin',
    'inspect-explicit-runtime',
    'install-pin',
    'build-pin',
    'verify-explicit',
    'promote-pin',
    'audit-pin',
    'classify-root-dependency',
    'install-root',
    'verify-default',
    'cleanup-transaction',
    'release-lock',
  ]);
  const clone = harness.calls.find(({ phase }) => phase === 'clone-pin').input;
  assert.equal(clone.repositoryUrl, CIV_ENGINE_PIN.repositoryUrl);
  assert.equal(clone.commit, CIV_ENGINE_PIN.commit);
  assert.equal(clone.destination, harness.transaction.checkoutPath);
  assert.equal(clone.repositoryUrl.includes('@'), false);
});

test('an exact installation takes the locked validation fast path', async () => {
  const harness = setupOperationHarness({
    pinKind: 'exact',
    explicitRuntimeExact: true,
    rootDependencyKind: 'exact',
  });
  await runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations });

  assert.deepEqual(phaseNames(harness), [
    'validate-contract',
    'acquire-lock',
    'create-transaction',
    'classify-pin',
    'audit-pin',
    'inspect-explicit-runtime',
    'classify-root-dependency',
    'verify-default',
    'cleanup-transaction',
    'release-lock',
  ]);
});

test('verification is read-only and maps only the explicit canary mode', async () => {
  for (const [argv, allowDirty] of [
    [['--verify-only'], false],
    [['--verify-only', '--allow-dirty'], true],
  ]) {
    const harness = setupOperationHarness();
    await runCivEngineSetup({ repoRoot, argv, operations: harness.operations });
    assert.deepEqual(phaseNames(harness), ['assert-no-lock', 'verify-only']);
    const verification = harness.calls.at(-1).input;
    assert.equal(verification.allowDirty, allowDirty);
    assert.equal(verification.repoRoot, repoRoot);
  }
});

test('suspicious checkout and phase failure short-circuit before mutation', async () => {
  const suspicious = setupOperationHarness({ pinKind: 'suspicious' });
  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: suspicious.operations }),
    (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_REFUSED',
  );
  assert.deepEqual(phaseNames(suspicious), [
    'validate-contract',
    'acquire-lock',
    'create-transaction',
    'classify-pin',
    'cleanup-transaction',
    'release-lock',
  ]);

  const failedBuild = setupOperationHarness({ failAt: 'build-pin' });
  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: failedBuild.operations }),
    /fixture failure: build-pin/,
  );
  assert.deepEqual(phaseNames(failedBuild), [
    'validate-contract',
    'acquire-lock',
    'create-transaction',
    'classify-pin',
    'clone-pin',
    'audit-pin',
    'inspect-explicit-runtime',
    'install-pin',
    'build-pin',
    'cleanup-transaction',
    'release-lock',
  ]);
});

test('a primary setup failure is retained when cleanup also fails', async () => {
  const harness = setupOperationHarness({ failAt: 'build-pin' });
  harness.operations.cleanupSetupTransaction = async (input) => {
    harness.calls.push({ phase: 'cleanup-transaction', input });
    throw new Error('fixture cleanup failure');
  };
  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations }),
    (error) => (
      error instanceof AggregateError
      && /fixture failure: build-pin/.test(error.message)
      && /fixture failure: build-pin/.test(error.cause?.message ?? '')
      && error.errors.some((entry) => /fixture cleanup failure/.test(entry.message))
    ),
  );
  assert.equal(phaseNames(harness).at(-1), 'release-lock');
});

test('post-claim publication failure retains transaction evidence and releases the lock', async () => {
  const harness = setupOperationHarness();
  harness.operations.promotePin = async (input) => {
    harness.calls.push({ phase: 'promote-pin', input });
    throw Object.assign(new Error('fixture publication ownership loss'), {
      code: 'ERR_CIV_ENGINE_SETUP_OWNERSHIP',
      preserveSetupTransaction: true,
    });
  };

  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations }),
    (error) => (
      error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
      && error.message === 'fixture publication ownership loss'
    ),
  );
  assert.deepEqual(phaseNames(harness), [
    'validate-contract',
    'acquire-lock',
    'create-transaction',
    'classify-pin',
    'clone-pin',
    'audit-pin',
    'inspect-explicit-runtime',
    'install-pin',
    'build-pin',
    'verify-explicit',
    'promote-pin',
    'release-lock',
  ]);
});

test('post-promotion audit failure retains source evidence before root installation', async () => {
  const harness = setupOperationHarness();
  let audits = 0;
  harness.operations.auditPin = async (input) => {
    harness.calls.push({ phase: 'audit-pin', input });
    audits += 1;
    if (audits === 2) {
      throw Object.assign(new Error('published checkout changed'), {
        code: 'ERR_CIV_ENGINE_SETUP_MISMATCH',
      });
    }
  };

  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations }),
    (error) => (
      error?.code === 'ERR_CIV_ENGINE_SETUP_MISMATCH'
      && error.preserveSetupTransaction === true
    ),
  );
  assert.deepEqual(phaseNames(harness).slice(-4), [
    'verify-explicit',
    'promote-pin',
    'audit-pin',
    'release-lock',
  ]);
  assert.equal(phaseNames(harness).includes('classify-root-dependency'), false);
  assert.equal(phaseNames(harness).includes('cleanup-transaction'), false);
});

test('pre-claim promotion refusal still cleans its setup transaction', async () => {
  const harness = setupOperationHarness({ failAt: 'promote-pin' });
  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations }),
    /fixture failure: promote-pin/,
  );
  assert.deepEqual(phaseNames(harness).slice(-3), [
    'promote-pin',
    'cleanup-transaction',
    'release-lock',
  ]);
});

test('retained publication evidence preserves both primary and lock-release failures', async () => {
  const harness = setupOperationHarness();
  harness.operations.promotePin = async (input) => {
    harness.calls.push({ phase: 'promote-pin', input });
    throw Object.assign(new Error('fixture retained publication'), {
      code: 'ERR_CIV_ENGINE_SETUP_OWNERSHIP',
      preserveSetupTransaction: true,
    });
  };
  harness.operations.releaseSetupLock = async (input) => {
    harness.calls.push({ phase: 'release-lock', input });
    throw new Error('fixture lock release failure');
  };

  await assert.rejects(
    runCivEngineSetup({ repoRoot, argv: [], operations: harness.operations }),
    (error) => (
      error instanceof AggregateError
      && error.cause?.message === 'fixture retained publication'
      && error.errors.some((entry) => entry.message === 'fixture retained publication')
      && error.errors.some((entry) => entry.message === 'fixture lock release failure')
    ),
  );
  assert.deepEqual(phaseNames(harness).slice(-2), ['promote-pin', 'release-lock']);
});
