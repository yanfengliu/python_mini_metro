import assert from 'node:assert/strict';
import {
  mkdir,
  readFile,
  realpath,
  rename,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { CIV_ENGINE_PIN } from '../scripts/civ-engine-pin.mjs';
import { installRootDependency } from '../scripts/civ-engine-setup-operations.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('root exact-link repair preserves an EEXIST race winner', async () => {
  await withRootLinkRepository(async ({ fixtureRoot, nodeModulesRoot, pin, pinRoot }) => {
    const rootSlot = path.join(nodeModulesRoot, CIV_ENGINE_PIN.packageName);
    const winnerRoot = path.join(fixtureRoot, 'race-winner');
    const sentinel = path.join(winnerRoot, 'sentinel.txt');
    await mkdir(winnerRoot);
    await writeFile(sentinel, 'race winner must survive\n');

    await assert.rejects(
      installRootDependency({
        repoRoot: fixtureRoot,
        pinRoot,
        pin,
        createRootLink: async (_target, linkPath, type) => {
          await symlink(winnerRoot, linkPath, type);
          throw Object.assign(new Error('simulated exclusive-create collision'), {
            code: 'EEXIST',
          });
        },
      }),
      /slot changed.*exact-link repair/i,
    );

    assert.equal(await realpath(rootSlot), await realpath(winnerRoot));
    assert.equal(await readFile(sentinel, 'utf8'), 'race winner must survive\n');
  });
});

test('root exact-link repair detects and preserves a swapped container', async () => {
  await withRootLinkRepository(async ({ fixtureRoot, nodeModulesRoot, pin, pinRoot }) => {
    const displacedRoot = path.join(fixtureRoot, 'displaced-node-modules');
    const metadataPath = path.join(nodeModulesRoot, '.package-lock.json');
    const rootSlot = path.join(nodeModulesRoot, CIV_ENGINE_PIN.packageName);
    await writeFile(metadataPath, 'original container\n');

    await assert.rejects(
      installRootDependency({
        repoRoot: fixtureRoot,
        pinRoot,
        pin,
        createRootLink: async (target, linkPath, type) => {
          await rename(nodeModulesRoot, displacedRoot);
          await mkdir(nodeModulesRoot);
          await symlink(target, linkPath, type);
        },
      }),
      /node_modules identity changed.*exact-link repair/i,
    );

    assert.equal(
      await readFile(path.join(displacedRoot, '.package-lock.json'), 'utf8'),
      'original container\n',
    );
    assert.equal(await realpath(rootSlot), await realpath(pinRoot));
  });
});

test('root exact-link repair rejects contract drift during link creation', async () => {
  await withRootLinkRepository(async ({ fixtureRoot, nodeModulesRoot, pin, pinRoot }) => {
    const npmrcPath = path.join(fixtureRoot, '.npmrc');
    const rootSlot = path.join(nodeModulesRoot, CIV_ENGINE_PIN.packageName);

    await assert.rejects(
      installRootDependency({
        repoRoot: fixtureRoot,
        pinRoot,
        pin,
        createRootLink: async (target, linkPath, type) => {
          await writeFile(npmrcPath, 'install-links=true\nloglevel=silent\n');
          await symlink(target, linkPath, type);
        },
      }),
      /npmrc|configuration|contract/i,
    );

    assert.equal(await realpath(rootSlot), await realpath(pinRoot));
    assert.equal(
      await readFile(npmrcPath, 'utf8'),
      'install-links=true\nloglevel=silent\n',
    );
  });
});

async function withRootLinkRepository(callback) {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const pinRoot = path.join(fixtureRoot, CIV_ENGINE_PIN.installPath);
    const nodeModulesRoot = path.join(fixtureRoot, 'node_modules');
    await Promise.all([mkdir(pinRoot), mkdir(nodeModulesRoot)]);
    await writeFile(path.join(pinRoot, 'package.json'), JSON.stringify({
      name: CIV_ENGINE_PIN.packageName,
      version: CIV_ENGINE_PIN.version,
    }));
    await callback({ fixtureRoot, nodeModulesRoot, pin, pinRoot });
  });
}
