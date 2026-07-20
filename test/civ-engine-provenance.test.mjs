import assert from 'node:assert/strict';
import {
  copyFile,
  mkdir,
  readFile,
  realpath,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  assertSourceStateAllowed,
  captureSourceState,
} from '../scripts/source-provenance.mjs';
import {
  assertCivEngineStateAllowed,
  assertCivEngineStateSummary,
  captureCivEngineState,
} from '../scripts/source-provenance-engine.mjs';
import {
  commit,
  copyProvenanceModules,
  git,
  normalize,
  runCopiedCapture,
  seedEngineRepository,
  sourceOptions,
  withRepository,
} from './source-provenance-fixtures.mjs';

test('a wrong physical engine root is non-overridable and fully attributable', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await writeFile(
      path.join(engine.root, 'package.json'),
      JSON.stringify({
        name: 'civ-engine',
        version: '9.9.9',
        type: 'module',
        exports: { '.': { import: './dist/index.js' } },
      }, null, 2),
      'utf8',
    );
    git(engine.root, ['add', 'package.json']);
    commit(engine.root, 'wrong version');
    const options = {
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      expectedEnginePackageRoot: path.join(fixtureRoot, '.civ-engine-pin'),
    };

    const changed = await captureSourceState(options);
    assert.equal(changed.engine.available, true);
    assert.equal(changed.engine.locationMatches, false);
    assert.equal(changed.engine.versionMatches, false);
    assert.equal(changed.engine.commitMatches, false);
    assert.equal(changed.engine.runtimeMatches, false);
    for (const allowDirty of [false, true]) {
      assert.throws(
        () => assertSourceStateAllowed(changed, { allowDirty }),
        (error) => (
          error?.code === 'ERR_CIV_ENGINE_PROVENANCE'
          && /resolved package root/.test(error.message)
          && /version 9\.9\.9 does not match 2\.2\.0/.test(error.message)
          && error.message.includes(changed.engine.gitCommit)
          && error.message.includes(engine.commit)
          && error.message.includes(changed.engine.treeDigest)
          && error.message.includes(engine.treeDigest)
        ),
      );
    }
    assert.throws(
      () => assertCivEngineStateAllowed(changed.engine.summary),
      /fresh civ-engine capture/i,
    );
    const forged = {
      ...changed.engine,
      expectedPackageRootPhysical: true,
      locationMatches: true,
    };
    assert.throws(
      () => assertCivEngineStateAllowed(forged, { allowDirty: true }),
      /fresh civ-engine capture/i,
    );
    changed.engine.expectedPackageRootPhysical = true;
    changed.engine.locationMatches = true;
    assert.throws(
      () => assertCivEngineStateAllowed(changed.engine, { allowDirty: true }),
      /fresh civ-engine capture/i,
    );
  });
});

test('the configured pin root must be a physical in-repo directory', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await symlink(engine.root, path.join(fixtureRoot, '.civ-engine-pin'), 'junction');
    const captured = await captureCivEngineState({
      repoRoot: fixtureRoot,
      enginePackageRoot: 'node_modules/civ-engine',
      expectedEngineCommit: engine.commit,
      expectedEngineTreeDigest: engine.treeDigest,
    });

    assert.equal(captured.available, true);
    assert.equal(captured.expectedPackageRootPhysical, false);
    assert.equal(captured.locationMatches, false);
    assert.equal(
      captured.localExpectedPackageRoot,
      normalize(path.join(fixtureRoot, '.civ-engine-pin')),
    );
    assert.equal(
      captured.localResolvedExpectedPackageRoot,
      normalize(await realpath(engine.root)),
    );
    for (const allowDirty of [false, true]) {
      assert.throws(
        () => assertCivEngineStateAllowed(captured, { allowDirty }),
        (error) => (
          error?.code === 'ERR_CIV_ENGINE_PROVENANCE'
          && /pinned root .* is not a physical in-repository directory/.test(error.message)
          && /cannot be overridden/.test(error.message)
        ),
      );
    }
  });
});

test('a top-level dist junction cannot escape the engine package root', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const externalDist = `${engine.root}-external-dist`;
    try {
      await mkdir(externalDist, { recursive: true });
      for (const fileName of ['index.js', 'state-digest.js']) {
        await copyFile(
          path.join(engine.root, 'dist', fileName),
          path.join(externalDist, fileName),
        );
      }
      await rm(path.join(engine.root, 'dist'), { recursive: true, force: true });
      await symlink(externalDist, path.join(engine.root, 'dist'), 'junction');

      const captured = await captureCivEngineState(
        sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      );
      assert.equal(captured.available, false);
      assert.match(captured.error, /dist must be a physical directory/i);
      for (const allowDirty of [false, true]) {
        assert.throws(
          () => assertCivEngineStateAllowed(captured, { allowDirty }),
          /unavailable/i,
        );
      }
    } finally {
      await rm(externalDist, { recursive: true, force: true });
    }
  });
});

test('a resolved runtime entry mismatch is non-overridable', async () => {
  await withRepository(async (fixtureRoot) => {
    const expectedRoot = path.join(fixtureRoot, '.civ-engine-pin');
    await seedEngineRepository(expectedRoot);
    const packagePath = path.join(expectedRoot, 'package.json');
    const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
    packageDocument.exports['.'] = {
      node: './dist/alternate.js',
      import: './dist/index.js',
    };
    await Promise.all([
      writeFile(packagePath, JSON.stringify(packageDocument, null, 2), 'utf8'),
      writeFile(
        path.join(expectedRoot, 'dist', 'alternate.js'),
        'export const alternate = true;\n',
        'utf8',
      ),
    ]);
    git(expectedRoot, ['add', 'package.json', '-f', 'dist/alternate.js']);
    commit(expectedRoot, 'conditional runtime');
    await mkdir(path.join(fixtureRoot, 'scripts', 'node_modules'), { recursive: true });
    await symlink(
      expectedRoot,
      path.join(fixtureRoot, 'scripts', 'node_modules', 'civ-engine'),
      'junction',
    );
    await copyProvenanceModules(fixtureRoot);

    const { state: captured, policyErrors } = runCopiedCapture(fixtureRoot);
    assert.equal(captured.available, true, JSON.stringify(captured, null, 2));
    assert.equal(captured.locationMatches, true);
    assert.equal(captured.runtimeEntry, 'dist/index.js');
    assert.match(captured.localResolvedRuntimeEntry, /dist\/alternate\.js$/);
    assert.match(captured.localDeclaredRuntimeEntry, /dist\/index\.js$/);
    assert.equal(captured.runtimeEntryMatches, false);
    for (const error of policyErrors) {
      assert.equal(error.code, 'ERR_CIV_ENGINE_PROVENANCE');
      assert.match(error.message, /resolved runtime entry/);
      assert.match(error.message, /cannot be overridden/);
    }
  });
});

test('engine summary validation rejects dishonest match booleans', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const clean = await captureSourceState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    for (const key of ['versionMatches', 'commitMatches', 'runtimeMatches']) {
      const dishonest = structuredClone(clean.engine.summary);
      dishonest[key] = !dishonest[key];
      assert.throws(
        () => assertCivEngineStateSummary(dishonest),
        /invalid available civ-engine provenance summary/,
      );
    }
  });
});

test('default provenance follows nested ESM resolution and rejects its physical root', async () => {
  await withRepository(async (fixtureRoot) => {
    const decoyRoot = `${fixtureRoot}-decoy-engine`;
    try {
      const decoy = await seedEngineRepository(decoyRoot);
      await seedEngineRepository(path.join(fixtureRoot, '.civ-engine-pin'));
      const packagePath = path.join(decoy.root, 'package.json');
      const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
      packageDocument.version = '9.9.9';
      await writeFile(packagePath, JSON.stringify(packageDocument, null, 2), 'utf8');
      git(decoy.root, ['add', 'package.json']);
      commit(decoy.root, 'decoy version');

      await mkdir(path.join(fixtureRoot, 'scripts', 'node_modules'), {
        recursive: true,
      });
      await symlink(
        decoy.root,
        path.join(fixtureRoot, 'scripts', 'node_modules', 'civ-engine'),
        'junction',
      );
      await copyProvenanceModules(fixtureRoot);
      const { state: captured, policyErrors } = runCopiedCapture(fixtureRoot);

      assert.equal(captured.available, true, JSON.stringify(captured, null, 2));
      assert.equal(captured.packageVersion, '9.9.9');
      assert.equal(captured.locationMatches, false);
      assert.equal(
        captured.localResolvedPackageRoot,
        normalize(await realpath(decoy.root)),
      );
      assert.equal(
        captured.localExpectedPackageRoot,
        normalize(path.join(fixtureRoot, '.civ-engine-pin')),
      );
      for (const error of policyErrors) {
        assert.equal(error.code, 'ERR_CIV_ENGINE_PROVENANCE');
        assert.match(error.message, /resolved package root/);
      }
    } finally {
      await rm(decoyRoot, { recursive: true, force: true });
    }
  });
});
