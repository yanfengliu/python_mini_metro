import assert from 'node:assert/strict';
import {
  readFile,
  rename,
  rm,
  stat,
  utimes,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { runReadOnlyGit } from '../scripts/civ-engine-setup-process.mjs';
import {
  assertSourceStateAllowed,
  captureSourceState,
} from '../scripts/source-provenance.mjs';
import {
  sourceOptions,
  withRepository,
} from './source-provenance-fixtures.mjs';

test('HEAD byte crosscheck catches a same-length timestamp-restored replacement', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const sourcePath = path.join(fixtureRoot, 'src', 'app.py');
    const clean = await captureSourceState(options);
    const [original, metadata] = await Promise.all([
      readFile(sourcePath, 'utf8'),
      stat(sourcePath),
    ]);
    const replacement = original.replace('fixture', 'mutated');
    assert.equal(Buffer.byteLength(replacement), Buffer.byteLength(original));
    await writeFile(sourcePath, replacement, 'utf8');
    await utimes(sourcePath, metadata.atime, metadata.mtime);

    const captured = await captureSourceState({
      ...options,
      rootGitRunner: statusBlindGit,
    });
    assert.notEqual(captured.treeDigest, clean.treeDigest);
    assert.equal(captured.worktreeDirty, true);
    assert.deepEqual(captured.status, [{ code: ' M', path: 'src/app.py' }]);
    assert.throws(
      () => assertSourceStateAllowed(captured),
      /src\/app\.py/,
    );
  });
});

test('HEAD byte crosscheck synthesizes deterministic add delete and rename evidence', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    await Promise.all([
      rm(path.join(fixtureRoot, 'src', 'app.py')),
      writeFile(path.join(fixtureRoot, 'src', 'new.py'), 'NEW = True\n', 'utf8'),
    ]);
    await rename(
      path.join(fixtureRoot, 'scripts', 'drive.mjs'),
      path.join(fixtureRoot, 'scripts', 'renamed.mjs'),
    );

    const captured = await captureSourceState({
      ...options,
      rootGitRunner: statusBlindGit,
    });
    assert.equal(captured.worktreeDirty, true);
    assert.deepEqual(captured.status, [
      { code: ' D', path: 'scripts/drive.mjs' },
      { code: '??', path: 'scripts/renamed.mjs' },
      { code: ' D', path: 'src/app.py' },
      { code: '??', path: 'src/new.py' },
    ]);
  });
});

test('HEAD byte crosscheck treats pure LF and CRLF working bytes as equivalent', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const sourcePath = path.join(fixtureRoot, 'src', 'app.py');
    const original = await readFile(sourcePath, 'utf8');
    await writeFile(sourcePath, original.replace(/\n/g, '\r\n'), 'utf8');

    const captured = await captureSourceState({
      ...options,
      rootGitRunner: statusBlindGit,
    });
    assert.equal(captured.worktreeDirty, false);
    assert.deepEqual(captured.status, []);
    assert.doesNotThrow(() => assertSourceStateAllowed(captured));
  });
});

function statusBlindGit(options) {
  if (options.args[0] === 'status') return '';
  return runReadOnlyGit(options);
}
