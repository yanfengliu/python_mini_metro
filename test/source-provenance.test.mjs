import assert from 'node:assert/strict';
import {
  readFile,
  realpath,
  rm,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  assertSourceStateAllowed,
  compareSourceStateSummaries,
  captureSourceProvenance,
  captureSourceState,
  recaptureAndAssertSourceUnchanged,
  sourceStateSummary,
  writeSourceStateArtifacts,
} from '../scripts/source-provenance.mjs';
import {
  commit,
  git,
  normalize,
  sha256,
  sourceOptions,
  withRepository,
} from './source-provenance-fixtures.mjs';

test('source and resolved engine inventories are deterministic and clean at the pin', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const first = await captureSourceState(options);
    const second = await captureSourceState(options);

    assert.deepEqual(second, first);
    assert.deepEqual(
      first.files.map((entry) => entry.path),
      [
        'package-lock.json',
        'package.json',
        'requirements-dev.txt',
        'requirements.txt',
        'scripts/drive.mjs',
        'src/app.py',
      ],
    );
    assert.match(first.treeDigest, /^[0-9a-f]{64}$/);
    assert.match(first.statusDigest, /^[0-9a-f]{64}$/);
    assert.equal(first.fileCount, first.files.length);
    assert.equal(first.worktreeDirty, false);
    assert.deepEqual(first.status, []);
    assert.equal(first.engine.available, true);
    assert.equal(first.engine.packageName, 'civ-engine');
    assert.equal(first.engine.packageVersion, '2.2.0');
    assert.equal(first.engine.expectedPackageVersion, '2.2.0');
    assert.equal(first.engine.gitCommit, engine.commit);
    assert.equal(first.engine.expectedGitCommit, engine.commit);
    assert.equal(first.engine.commitMatches, true);
    assert.equal(first.engine.versionMatches, true);
    assert.equal(first.engine.expectedTreeDigest, engine.treeDigest);
    assert.equal(first.engine.treeDigest, engine.treeDigest);
    assert.equal(first.engine.runtimeMatches, true);
    assert.equal(first.engine.worktreeDirty, false);
    assert.equal(
      first.engine.resolvedPackageRoot,
      normalize(path.relative(fixtureRoot, await realpath(engine.root))),
    );
    assert.equal(
      first.engine.localResolvedPackageRoot,
      normalize(await realpath(engine.root)),
    );
    assert.deepEqual(first.engine.files.map((entry) => entry.path), [
      'dist/index.js',
      'dist/state-digest.js',
      'package.json',
    ]);
    assert.doesNotThrow(() => assertSourceStateAllowed(first));
    assert.ok(first.files.every((entry) => (
      Number.isInteger(entry.bytes)
      && entry.bytes >= 0
      && /^[0-9a-f]{64}$/.test(entry.sha256)
    )));
  });
});

test('only relevant source changes affect dirty state and the tree digest', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const sourcePath = path.join(fixtureRoot, 'src', 'app.py');
    const original = await readFile(sourcePath, 'utf8');
    const clean = await captureSourceState(options);

    await writeFile(path.join(fixtureRoot, 'README.md'), 'irrelevant\n', 'utf8');
    const irrelevantChange = await captureSourceState(options);
    assert.equal(irrelevantChange.treeDigest, clean.treeDigest);
    assert.equal(irrelevantChange.worktreeDirty, false);

    await writeFile(sourcePath, `${original}# one-line canary\n`, 'utf8');
    const canary = await captureSourceState(options);
    assert.notEqual(canary.treeDigest, clean.treeDigest);
    assert.equal(canary.worktreeDirty, true);
    assert.deepEqual(canary.status, [{ code: ' M', path: 'src/app.py' }]);

    await writeFile(sourcePath, original, 'utf8');
    const restored = await captureSourceState(options);
    assert.equal(restored.treeDigest, clean.treeDigest);
    assert.equal(restored.worktreeDirty, false);
  });
});

test('artifact writer records a tracked dirty patch and exposes a stable summary', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const runDir = path.join(fixtureRoot, 'evidence', 'run-1');
    const sourcePath = path.join(fixtureRoot, 'src', 'app.py');
    await writeFile(sourcePath, 'print("changed")\n', 'utf8');
    await writeFile(path.join(fixtureRoot, 'src', 'new.py'), 'NEW = True\n', 'utf8');

    const captured = await captureSourceProvenance(options);
    await writeFile(sourcePath, 'print("changed after capture")\n', 'utf8');

    const written = await writeSourceStateArtifacts({
      repoRoot: fixtureRoot,
      runDir,
      ...captured,
    });
    const persisted = JSON.parse(
      await readFile(path.join(runDir, 'source-state.json'), 'utf8'),
    );
    const patch = await readFile(path.join(runDir, 'source-diff.patch'), 'utf8');

    assert.deepEqual(persisted, written.sourceState);
    assert.deepEqual(persisted, captured.sourceState);
    assert.notEqual(
      persisted.treeDigest,
      (await captureSourceState(options)).treeDigest,
    );
    assert.equal(persisted.worktreeDirty, true);
    assert.equal(persisted.diffAvailable, true);
    assert.equal(persisted.diffArtifact, 'source-diff.patch');
    assert.equal(persisted.diffDigest, sha256(patch));
    assert.match(patch, /-print\("fixture"\)/);
    assert.match(patch, /\+print\("changed"\)/);
    assert.match(patch, /new file mode 100644/);
    assert.match(patch, /\+NEW = True/);
    assert.deepEqual(sourceStateSummary(persisted), {
      schemaVersion: 1,
      algorithm: 'sha256',
      treeDigest: persisted.treeDigest,
      fileCount: persisted.fileCount,
      gitCommit: persisted.gitCommit,
      worktreeDirty: true,
      statusDigest: persisted.statusDigest,
      diffAvailable: true,
      diffDigest: persisted.diffDigest,
      engine: persisted.engine.summary,
    });

    assert.throws(
      () => assertSourceStateAllowed(persisted),
      /fresh civ-engine capture/i,
    );
    assert.throws(
      () => assertSourceStateAllowed(persisted, { allowDirty: true }),
      /fresh civ-engine capture/i,
    );
    assert.throws(
      () => assertSourceStateAllowed(captured.sourceState),
      (error) => (
        error?.code === 'ERR_RELEVANT_SOURCE_DIRTY'
        && /--allow-dirty/.test(error.message)
        && /src\/app\.py/.test(error.message)
      ),
    );
    assert.equal(
      assertSourceStateAllowed(captured.sourceState, { allowDirty: true }),
      captured.sourceState,
    );
  });
});

test('clean artifact writer omits the patch and refuses to overwrite evidence', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const runDir = path.join(fixtureRoot, 'evidence', 'run-clean');
    const written = await writeSourceStateArtifacts({
      ...options,
      runDir,
    });

    assert.equal(written.sourceState.diffAvailable, false);
    assert.equal(written.sourceState.diffDigest, undefined);
    assert.equal(written.sourceDiffPath, null);
    assert.equal(
      assertSourceStateAllowed(written.sourceState),
      written.sourceState,
    );
    await assert.rejects(
      () => writeSourceStateArtifacts({ ...options, runDir }),
      (error) => error?.code === 'EEXIST',
    );
  });
});

test('same-version modified engine runtime changes its digest and requires override', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const clean = await captureSourceState(options);
    await writeFile(
      path.join(engine.root, 'dist', 'state-digest.js'),
      'export const stateDigest = () => "modified";\n',
      'utf8',
    );

    const modified = await captureSourceState(options);
    assert.equal(modified.engine.packageVersion, '2.2.0');
    assert.equal(modified.engine.gitCommit, engine.commit);
    assert.equal(modified.engine.worktreeDirty, false);
    assert.notEqual(modified.engine.treeDigest, clean.engine.treeDigest);
    assert.equal(modified.engine.runtimeMatches, false);
    assert.throws(() => assertSourceStateAllowed(modified), /civ-engine/i);
    assert.equal(
      assertSourceStateAllowed(modified, { allowDirty: true }),
      modified,
    );
  });
});

test('engine runtime digest canonicalizes platform text line endings', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const clean = await captureSourceState(options);
    const entryPath = path.join(engine.root, 'dist', 'index.js');
    const contents = await readFile(entryPath, 'utf8');
    await writeFile(entryPath, contents.replace(/\n/g, '\r\n'), 'utf8');

    const crlf = await captureSourceState(options);
    assert.equal(crlf.engine.worktreeDirty, false);
    assert.equal(crlf.engine.treeDigest, clean.engine.treeDigest);
    assert.equal(crlf.engine.runtimeMatches, true);
    assert.doesNotThrow(() => assertSourceStateAllowed(crlf));
  });
});

test('wrong clean engine commit fails closed unless mismatch evidence is allowed', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    await writeFile(path.join(engine.root, 'README.md'), 'second commit\n', 'utf8');
    git(engine.root, ['add', 'README.md']);
    commit(engine.root, 'second');

    const changed = await captureSourceState(options);
    assert.equal(changed.engine.worktreeDirty, false);
    assert.notEqual(changed.engine.gitCommit, engine.commit);
    assert.equal(changed.engine.commitMatches, false);
    assert.throws(() => assertSourceStateAllowed(changed), /commit/i);
    assert.equal(
      assertSourceStateAllowed(changed, { allowDirty: true }),
      changed,
    );
  });
});

test('dirty sibling outside dist fails closed and remains fully attributable', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const clean = await captureSourceState(options);
    await writeFile(path.join(engine.root, 'README.md'), 'dirty sibling\n', 'utf8');

    const dirty = await captureSourceState(options);
    assert.equal(dirty.engine.worktreeDirty, true);
    assert.equal(dirty.engine.treeDigest, clean.engine.treeDigest);
    assert.ok(dirty.engine.status.some((entry) => entry.path === 'README.md'));
    assert.throws(() => assertSourceStateAllowed(dirty), /dirty/i);
    assert.doesNotThrow(() => assertSourceStateAllowed(dirty, { allowDirty: true }));
  });
});

test('start/end comparison catches local or engine mutation with both snapshots', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const start = await captureSourceProvenance(options);
    const unchanged = await recaptureAndAssertSourceUnchanged({
      ...options,
      startSourceState: start.sourceState,
    });
    assert.equal(unchanged.ok, true);
    assert.equal(
      compareSourceStateSummaries(start.sourceState, unchanged.endSourceState).ok,
      true,
    );

    const localSourcePath = path.join(fixtureRoot, 'src', 'app.py');
    const originalLocalSource = await readFile(localSourcePath, 'utf8');
    await writeFile(localSourcePath, `${originalLocalSource}# changed during run\n`, 'utf8');
    await assert.rejects(
      () => recaptureAndAssertSourceUnchanged({
        ...options,
        startSourceState: start.sourceState,
      }),
      (error) => (
        error?.code === 'ERR_SOURCE_CHANGED_DURING_RUN'
        && error.startSourceState.treeDigest === start.sourceState.treeDigest
        && error.endSourceState.treeDigest !== start.sourceState.treeDigest
        && error.endProvenance?.sourceDiff?.includes('changed during run')
      ),
    );
    await writeFile(localSourcePath, originalLocalSource, 'utf8');

    await writeFile(
      path.join(engine.root, 'dist', 'index.js'),
      'export const ENGINE_VERSION = "mutated";\n',
      'utf8',
    );
    await assert.rejects(
      () => recaptureAndAssertSourceUnchanged({
        ...options,
        startSourceState: start.sourceState,
      }),
      (error) => (
        error?.code === 'ERR_SOURCE_CHANGED_DURING_RUN'
        && error.startSourceState.engine.treeDigest
          === start.sourceState.engine.treeDigest
        && error.endSourceState.engine.treeDigest
          !== start.sourceState.engine.treeDigest
      ),
    );
  });
});

test('an unavailable resolved engine fails closed even with dirty override', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    await rm(path.join(fixtureRoot, 'node_modules', 'civ-engine'), {
      recursive: true,
      force: true,
    });

    const unavailable = await captureSourceState(options);
    assert.equal(unavailable.engine.available, false);
    assert.throws(
      () => assertSourceStateAllowed(unavailable, { allowDirty: true }),
      /unavailable/i,
    );
  });
});
