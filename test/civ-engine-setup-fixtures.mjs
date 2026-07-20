import {
  mkdir,
  mkdtemp,
  rm,
  writeFile,
} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { CIV_ENGINE_PIN } from '../scripts/civ-engine-pin.mjs';
import { digestParsedRootLock } from '../scripts/civ-engine-setup-root-contract.mjs';

export async function withSetupRepository(callback) {
  const fixtureRoot = await mkdtemp(path.join(os.tmpdir(), 'mini-metro-setup-'));
  await mkdir(path.join(fixtureRoot, 'scripts'), { recursive: true });
  const lockDocument = {
    name: 'python-mini-metro-fixture',
    lockfileVersion: 3,
    requires: true,
    packages: {
      '': { dependencies: { 'civ-engine': 'file:.civ-engine-pin' } },
      '.civ-engine-pin': { name: 'civ-engine', version: '2.2.0' },
      'node_modules/civ-engine': {
        resolved: '.civ-engine-pin',
        link: true,
      },
    },
  };
  const pin = {
    ...CIV_ENGINE_PIN,
    rootLockSha256: digestParsedRootLock(lockDocument),
  };
  try {
    await Promise.all([
      writeFile(
        path.join(fixtureRoot, '.npmrc'),
        'install-links=false\nloglevel=silent\n',
        'utf8',
      ),
      writeFile(path.join(fixtureRoot, 'package.json'), JSON.stringify({
        name: 'python-mini-metro-fixture',
        private: true,
        type: 'module',
        dependencies: { 'civ-engine': 'file:.civ-engine-pin' },
      }, null, 2), 'utf8'),
      writeFile(
        path.join(fixtureRoot, 'package-lock.json'),
        JSON.stringify(lockDocument, null, 2),
        'utf8',
      ),
    ]);
    await callback(fixtureRoot, { pin });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
}

export function setupOperationHarness(overrides = {}) {
  const calls = [];
  const state = {
    pinKind: 'missing',
    explicitRuntimeExact: false,
    rootDependencyKind: 'repairable',
    ...overrides,
  };
  const record = (phase, result) => async (input = {}) => {
    calls.push({ phase, input });
    if (state.failAt === phase) throw new Error(`fixture failure: ${phase}`);
    return typeof result === 'function' ? result(input) : result;
  };
  const transaction = {
    parentPath: 'fixture-transaction',
    checkoutPath: 'fixture-transaction/checkout',
    token: 'fixture-owner',
  };
  const operations = {
    validateRepositoryContract: record('validate-contract'),
    assertNoActiveSetupLock: record('assert-no-lock'),
    acquireSetupLock: record('acquire-lock', { token: 'fixture-lock' }),
    createSetupTransaction: record('create-transaction', transaction),
    classifyPin: record('classify-pin', () => ({ kind: state.pinKind })),
    clonePinnedRepository: record('clone-pin'),
    auditPin: record('audit-pin'),
    explicitRuntimeIsExact: record(
      'inspect-explicit-runtime',
      () => state.explicitRuntimeExact,
    ),
    installPinDependencies: record('install-pin'),
    buildPin: record('build-pin'),
    verifyExplicitPin: record('verify-explicit'),
    promotePin: record('promote-pin'),
    classifyRootDependency: record(
      'classify-root-dependency',
      () => ({ kind: state.rootDependencyKind }),
    ),
    installRootDependency: record('install-root'),
    verifyDefaultPin: record('verify-default'),
    verifyOnly: record('verify-only'),
    cleanupSetupTransaction: record('cleanup-transaction'),
    releaseSetupLock: record('release-lock'),
  };
  return { calls, operations, transaction };
}

export function phaseNames(harness) {
  return harness.calls.map(({ phase }) => phase);
}
