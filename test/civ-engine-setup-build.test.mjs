import assert from 'node:assert/strict';
import {
  mkdir,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { planPinnedTypeScriptBuild } from '../scripts/civ-engine-setup-build.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('TypeScript build uses physical Node and pin-local CLI without search state', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const nodePath = path.join(fixtureRoot, 'node-distribution', 'node.exe');
    const compilerPath = path.join(
      fixtureRoot,
      'checkout',
      'node_modules',
      'typescript',
      'bin',
      'tsc',
    );
    const homePath = path.join(fixtureRoot, 'home');
    const tempPath = path.join(fixtureRoot, 'temp');
    await Promise.all([
      mkdir(path.dirname(nodePath), { recursive: true }),
      mkdir(path.dirname(compilerPath), { recursive: true }),
      mkdir(homePath),
      mkdir(tempPath),
    ]);
    await Promise.all([
      writeFile(nodePath, 'physical node'),
      writeFile(compilerPath, '#!/usr/bin/env node\n'),
    ]);
    const sentinel = 'ancestor-search-must-not-pass';
    const plan = await planPinnedTypeScriptBuild({
      checkoutRoot: path.join(fixtureRoot, 'checkout'),
      compilerPath,
      execPath: nodePath,
      homePath,
      tempPath,
      sourceEnv: {
        PATH: sentinel,
        PATHEXT: sentinel,
        npm_lifecycle_event: sentinel,
        npm_node_execpath: sentinel,
        NODE_OPTIONS: sentinel,
      },
    });
    assert.equal(plan.command, nodePath);
    assert.deepEqual(plan.args, [compilerPath, '-p', 'tsconfig.build.json']);
    assert.equal(plan.options.cwd, path.join(fixtureRoot, 'checkout'));
    assert.equal(plan.options.shell, false);
    assert.equal(plan.options.windowsHide, true);
    assert.equal(Object.hasOwn(plan.options.env, 'PATH'), false);
    assert.equal(Object.hasOwn(plan.options.env, 'PATHEXT'), false);
    assert.equal(JSON.stringify(plan).includes(sentinel), false);
  });
});

test('TypeScript build rejects a compiler link outside the pinned checkout', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const checkoutRoot = path.join(fixtureRoot, 'checkout');
    const compilerPath = path.join(
      checkoutRoot,
      'node_modules',
      'typescript',
      'bin',
      'tsc',
    );
    const outsideBin = path.join(fixtureRoot, 'outside-typescript-bin');
    const outsideCompiler = path.join(outsideBin, 'tsc');
    const nodePath = path.join(fixtureRoot, 'node');
    await Promise.all([
      mkdir(path.dirname(path.dirname(compilerPath)), { recursive: true }),
      mkdir(outsideBin),
    ]);
    await Promise.all([
      writeFile(outsideCompiler, 'outside compiler'),
      writeFile(nodePath, 'node'),
    ]);
    await symlink(
      outsideBin,
      path.dirname(compilerPath),
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    await assert.rejects(
      planPinnedTypeScriptBuild({
        checkoutRoot,
        compilerPath,
        execPath: nodePath,
        homePath: fixtureRoot,
        tempPath: fixtureRoot,
        sourceEnv: {},
      }),
      /compiler|physical|contained|link/i,
    );
  });
});
