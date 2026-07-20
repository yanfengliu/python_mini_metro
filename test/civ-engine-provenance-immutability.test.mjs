import assert from 'node:assert/strict';
import { appendFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  assertCivEngineStateAllowed,
  captureCivEngineState,
} from '../scripts/source-provenance-engine.mjs';
import {
  sourceOptions,
  withRepository,
} from './source-provenance-fixtures.mjs';

test('direct dirty engine capture blocks alternating getter forgery', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await appendFile(path.join(engine.root, 'README.md'), 'dirty engine\n', 'utf8');
    const state = await captureCivEngineState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    assert.equal(state.worktreeDirty, true);
    assert.equal(Object.isFrozen(state), true);
    assert.equal(Object.isFrozen(state.summary), true);
    assert.equal(Object.isFrozen(state.status), true);

    let summaryReads = 0;
    let dirtyReads = 0;
    assert.throws(() => Object.defineProperty(state, 'summary', {
      configurable: true,
      enumerable: true,
      get() {
        summaryReads += 1;
        return { ...state.summary, worktreeDirty: false };
      },
    }), TypeError);
    assert.throws(() => Object.defineProperty(state, 'worktreeDirty', {
      configurable: true,
      enumerable: true,
      get() {
        dirtyReads += 1;
        return false;
      },
    }), TypeError);

    assert.throws(
      () => assertCivEngineStateAllowed(state),
      (error) => error?.code === 'ERR_CIV_ENGINE_PROVENANCE' && /worktree is dirty/.test(error.message),
    );
    assert.equal(summaryReads, 0);
    assert.equal(dirtyReads, 0);
  });
});
