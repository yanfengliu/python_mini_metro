import assert from 'node:assert/strict';
import {
  access,
  mkdir,
  readFile,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  acquireSetupLock,
  classifyRootDependencyRepair,
  classifySetupState,
  cleanupSetupTransaction,
  createSetupTransaction,
  releaseSetupLock,
} from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('the setup lock excludes every concurrent setup and only its owner releases it', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const first = await acquireSetupLock({
      repoRoot: fixtureRoot,
      token: 'first-owner',
    });
    await assert.rejects(
      acquireSetupLock({ repoRoot: fixtureRoot, token: 'second-owner' }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LOCKED',
    );
    await assert.rejects(
      releaseSetupLock({ ...first, token: 'wrong-owner' }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP',
    );
    await access(first.path);
    await releaseSetupLock(first);
    await assert.rejects(access(first.path), { code: 'ENOENT' });
  });
});

test('transaction ownership is two-level and cleanup requires unchanged identity', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const transaction = await createSetupTransaction({
      repoRoot: fixtureRoot,
      token: 'transaction-owner',
    });
    await access(transaction.parentPath);
    await access(transaction.markerPath);
    await assert.rejects(access(transaction.checkoutPath), { code: 'ENOENT' });

    await mkdir(transaction.checkoutPath);
    await writeFile(
      path.join(transaction.checkoutPath, 'owned-clone-sentinel'),
      'owned\n',
      'utf8',
    );
    await cleanupSetupTransaction(transaction);
    await assert.rejects(access(transaction.parentPath), { code: 'ENOENT' });

    const tampered = await createSetupTransaction({
      repoRoot: fixtureRoot,
      token: 'original-owner',
    });
    await writeFile(tampered.markerPath, 'replacement-owner\n', 'utf8');
    await assert.rejects(
      cleanupSetupTransaction(tampered),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP',
    );
    assert.equal(
      await readFile(tampered.markerPath, 'utf8'),
      'replacement-owner\n',
    );
  });
});

test('transaction cleanup refuses a nested external junction without touching its target', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const transaction = await createSetupTransaction({ repoRoot: fixtureRoot });
    const externalRoot = path.join(fixtureRoot, 'external-cleanup-target');
    const linkPath = path.join(transaction.parentPath, 'nested-escape');
    const sentinel = path.join(externalRoot, 'sentinel.txt');
    await mkdir(externalRoot);
    await writeFile(sentinel, 'cleanup target survives\n');
    await symlink(
      externalRoot,
      linkPath,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    await assert.rejects(
      cleanupSetupTransaction(transaction),
      /escape|link|junction|reparse|owned/i,
    );
    assert.equal(await readFile(sentinel, 'utf8'), 'cleanup target survives\n');
    await rmLink(linkPath);
    await cleanupSetupTransaction(transaction);
  });
});

test('missing state is classifiable but suspicious existing destinations are untouched', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    assert.deepEqual(
      await classifySetupState({ repoRoot: fixtureRoot, pinRoot }),
      { kind: 'missing' },
    );

    await writeFile(pinRoot, 'pre-existing file sentinel\n', 'utf8');
    await assert.rejects(
      classifySetupState({ repoRoot: fixtureRoot, pinRoot }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_UNSAFE',
    );
    assert.equal(await readFile(pinRoot, 'utf8'), 'pre-existing file sentinel\n');
  });

  await withSetupRepository(async (fixtureRoot) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    await mkdir(pinRoot);
    const sentinel = path.join(pinRoot, 'unowned-sentinel');
    await writeFile(sentinel, 'do not mutate\n', 'utf8');
    await assert.rejects(
      classifySetupState({ repoRoot: fixtureRoot, pinRoot }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_UNSAFE',
    );
    assert.equal(await readFile(sentinel, 'utf8'), 'do not mutate\n');
  });

  await withSetupRepository(async (fixtureRoot) => {
    const outside = path.join(fixtureRoot, 'outside-engine');
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    await mkdir(outside);
    const sentinel = path.join(outside, 'sibling-sentinel');
    await writeFile(sentinel, 'outside must survive\n', 'utf8');
    await symlink(outside, pinRoot, 'junction');
    await assert.rejects(
      classifySetupState({ repoRoot: fixtureRoot, pinRoot }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_UNSAFE',
    );
    assert.equal(await readFile(sentinel, 'utf8'), 'outside must survive\n');
  });
});

async function rmLink(candidate) {
  const { unlink } = await import('node:fs/promises');
  await unlink(candidate);
}

test('only the expected root dependency slot is repairable', () => {
  const fixtureRoot = path.resolve('fixture-repository');
  const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
  const rootSlot = path.join(fixtureRoot, 'node_modules', 'civ-engine');
  assert.deepEqual(classifyRootDependencyRepair({
    repoRoot: fixtureRoot,
    expectedPinRoot: pinRoot,
    requestedPackagePath: rootSlot,
    resolvedPackageRoot: pinRoot,
  }), { kind: 'exact' });
  assert.deepEqual(classifyRootDependencyRepair({
    repoRoot: fixtureRoot,
    expectedPinRoot: pinRoot,
    requestedPackagePath: rootSlot,
    resolvedPackageRoot: null,
  }), { kind: 'repairable' });
  assert.deepEqual(classifyRootDependencyRepair({
    repoRoot: fixtureRoot,
    expectedPinRoot: pinRoot,
    requestedPackagePath: rootSlot,
    resolvedPackageRoot: path.join(fixtureRoot, 'stale-pin'),
  }), { kind: 'repairable' });

  for (const requestedPackagePath of [
    path.join(fixtureRoot, 'scripts', 'node_modules', 'civ-engine'),
    path.resolve(fixtureRoot, '..', 'civ-engine'),
  ]) {
    assert.throws(
      () => classifyRootDependencyRepair({
        repoRoot: fixtureRoot,
        expectedPinRoot: pinRoot,
        requestedPackagePath,
        resolvedPackageRoot: requestedPackagePath,
      }),
      (error) => error?.code === 'ERR_CIV_ENGINE_RESOLUTION_SHADOW',
    );
  }
});
