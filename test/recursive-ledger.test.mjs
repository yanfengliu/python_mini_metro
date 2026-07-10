import assert from 'node:assert/strict';
import {
  appendFile,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  utimes,
  writeFile,
} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { withLedgerLock } from '../scripts/recursive-ledger.mjs';
import {
  appendValidatedManifestRow,
  buildPassManifest,
  buildRunManifest,
  createManifestPairIntent,
  persistManifestPair,
  reconcileManifestPairIntents,
} from '../scripts/recursive-pass.mjs';
import { sourceStateFixture } from './recursive-fixtures.mjs';

const LOCK_DIRECTORY = '.ledger-lock';
const OWNER_FILE = 'owner.json';

function completeInput(overrides = {}) {
  const gitCommit = '11161a54e402c33dd5d08c67d355dc02a5900a0a';
  return {
    id: 'ledger-test',
    objective: 'Exercise recursive ledger persistence.',
    startedAt: '2026-07-10T10:00:00.000Z',
    completedAt: '2026-07-10T10:00:01.000Z',
    durationMs: 1000,
    seed: 42,
    gitCommit,
    sourceState: sourceStateFixture({ gitCommit }),
    stopReason: 'no-fix-candidate',
    artifacts: [],
    gates: [{ name: 'fresh-process-redrive', ok: true }],
    data: { outcome: 'no-fix-candidate' },
    ...overrides,
  };
}

function manifestPair(baseId, seed = 42) {
  const shared = completeInput({ id: baseId, seed });
  return {
    runManifest: buildRunManifest({
      ...shared,
      id: `${baseId}-run`,
      stopReason: 'verified',
    }),
    passManifest: buildPassManifest({
      ...shared,
      id: `${baseId}-pass`,
    }),
  };
}

test('a stale heartbeat from a live owner is never stolen', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-live-lock-'));
  const original = await writeStaleOwner(outputRoot, {
    pid: process.pid,
    token: 'slow-live-owner',
  });
  let entered = false;

  await assert.rejects(
    withLedgerLock(outputRoot, async () => {
      entered = true;
    }, {
      isProcessAlive: async (pid) => pid === process.pid,
      retryDelayMs: 0,
      staleAfterMs: 10,
      waitTimeoutMs: 0,
    }),
    /timed out waiting for ledger lock/,
  );

  assert.equal(entered, false);
  assert.deepEqual(await readOwner(outputRoot), original);
});

test('a stale lock is recovered only after its owner is dead', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-dead-lock-'));
  await writeStaleOwner(outputRoot, {
    pid: 999_999,
    token: 'dead-owner',
  });
  let entered = false;

  await withLedgerLock(outputRoot, async ({ token }) => {
    entered = true;
    assert.notEqual(token, 'dead-owner');
  }, {
    isProcessAlive: async () => false,
    retryDelayMs: 0,
    staleAfterMs: 10,
    waitTimeoutMs: 0,
  });

  assert.equal(entered, true);
  assert.equal(
    (await readdir(outputRoot)).some((name) => name.startsWith(LOCK_DIRECTORY)),
    false,
  );
});

test('an old owner cannot release a successor lock', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-successor-lock-'));
  const successor = {
    schemaVersion: 1,
    pid: process.pid,
    token: 'successor-owner',
    acquiredAt: new Date().toISOString(),
  };

  await assert.rejects(
    withLedgerLock(outputRoot, async ({ token }) => {
      assert.notEqual(token, successor.token);
      await rm(path.join(outputRoot, LOCK_DIRECTORY), {
        recursive: true,
        force: true,
      });
      await mkdir(path.join(outputRoot, LOCK_DIRECTORY));
      await writeFile(
        path.join(outputRoot, LOCK_DIRECTORY, OWNER_FILE),
        `${JSON.stringify(successor)}\n`,
        'utf8',
      );
    }, {
      heartbeatIntervalMs: 60_000,
    }),
    /lost ledger lock ownership/,
  );

  assert.deepEqual(await readOwner(outputRoot), successor);
  await rm(path.join(outputRoot, LOCK_DIRECTORY), {
    recursive: true,
    force: true,
  });
});

test('one reconciliation drains many intents after confirming both ledgers', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-many-intents-'));
  const pairs = Array.from(
    { length: 48 },
    (_, index) => manifestPair(`many-${index}`, index),
  );
  await Promise.all(pairs.map((pair) => createManifestPairIntent({
    outputRoot,
    repoRoot: outputRoot,
    ...pair,
  })));

  await reconcileManifestPairIntents({ outputRoot, repoRoot: outputRoot });

  assert.equal((await readRows(path.join(outputRoot, 'ledger.jsonl'))).length, 48);
  assert.equal((await readRows(path.join(outputRoot, 'passes.jsonl'))).length, 48);
  assert.deepEqual(
    (await readdir(path.join(outputRoot, 'ledger-intents')))
      .filter((name) => name.endsWith('.json')),
    [],
  );
});

test('crash repair retains the intent until both rows are durably confirmed', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-crash-intent-'));
  const pair = manifestPair('crash-repair');
  const intentPath = await createManifestPairIntent({
    outputRoot,
    repoRoot: outputRoot,
    ...pair,
  });
  await appendValidatedManifestRow(
    path.join(outputRoot, 'ledger.jsonl'),
    pair.runManifest,
    { repoRoot: outputRoot },
  );

  assert.equal((await stat(intentPath)).isFile(), true);
  await reconcileManifestPairIntents({ outputRoot, repoRoot: outputRoot });

  assert.deepEqual(await readRows(path.join(outputRoot, 'ledger.jsonl')), [
    pair.runManifest,
  ]);
  assert.deepEqual(await readRows(path.join(outputRoot, 'passes.jsonl')), [
    pair.passManifest,
  ]);
  await assert.rejects(() => stat(intentPath), /ENOENT/);
});

test('versioned finalization intent repairs every persistence boundary', async () => {
  for (const boundary of [
    'intent',
    'run-manifest',
    'pass-manifest',
    'run-row',
    'pass-row',
  ]) {
    const outputRoot = await mkdtemp(path.join(os.tmpdir(), `metro-${boundary}-`));
    const pair = await finalizationPair(outputRoot, `boundary-${boundary}`);
    await assert.rejects(
      persistManifestPair({
        outputRoot,
        repoRoot: outputRoot,
        ...pair,
        onBoundary: async (completed) => {
          if (completed === boundary) throw new Error(`injected after ${boundary}`);
        },
      }),
      new RegExp(`injected after ${boundary}`),
    );

    const pendingIntents = await intentNames(outputRoot);
    assert.equal(pendingIntents.length, 1);
    const intent = JSON.parse(await readFile(
      path.join(outputRoot, 'ledger-intents', pendingIntents[0]),
      'utf8',
    ));
    assert.equal(intent.schemaVersion, 2);
    assert.deepEqual(intent.targets, {
      runManifestPath: `${pair.runManifest.id.replace(/-run$/, '')}/run-manifest.json`,
      passManifestPath: `${pair.passManifest.id.replace(/-pass$/, '')}/pass-manifest.json`,
    });
    assert.deepEqual(intent.runManifest, pair.runManifest);
    assert.deepEqual(intent.passManifest, pair.passManifest);
    await reconcileManifestPairIntents({ outputRoot, repoRoot: outputRoot });

    assert.deepEqual(JSON.parse(await readFile(pair.runManifestPath, 'utf8')), pair.runManifest);
    assert.deepEqual(JSON.parse(await readFile(pair.passManifestPath, 'utf8')), pair.passManifest);
    assert.deepEqual(await readRows(path.join(outputRoot, 'ledger.jsonl')), [
      pair.runManifest,
    ]);
    assert.deepEqual(await readRows(path.join(outputRoot, 'passes.jsonl')), [
      pair.passManifest,
    ]);
    assert.deepEqual(await intentNames(outputRoot), []);
  }
});

test('versioned finalization serializes concurrent writers and exact retries', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-finalization-concurrent-'));
  const pairs = await Promise.all(Array.from(
    { length: 12 },
    (_, index) => finalizationPair(outputRoot, `concurrent-${index}`),
  ));

  await Promise.all(pairs.map((pair) => persistManifestPair({
    outputRoot,
    repoRoot: outputRoot,
    ...pair,
  })));

  assert.equal((await readRows(path.join(outputRoot, 'ledger.jsonl'))).length, pairs.length);
  assert.equal((await readRows(path.join(outputRoot, 'passes.jsonl'))).length, pairs.length);
  assert.deepEqual(await intentNames(outputRoot), []);

  await persistManifestPair({
    outputRoot,
    repoRoot: outputRoot,
    ...pairs[0],
  });
  assert.equal((await readRows(path.join(outputRoot, 'ledger.jsonl'))).length, pairs.length);
  assert.equal((await readRows(path.join(outputRoot, 'passes.jsonl'))).length, pairs.length);
});

test('pending intent repairs an unterminated final JSONL fragment', async () => {
  const outputRoot = await mkdtemp(path.join(os.tmpdir(), 'metro-torn-tail-'));
  const pair = await finalizationPair(outputRoot, 'torn-tail');
  await assert.rejects(
    persistManifestPair({
      outputRoot,
      repoRoot: outputRoot,
      ...pair,
      onBoundary: async (completed) => {
        if (completed === 'run-row') throw new Error('injected after run-row');
      },
    }),
    /injected after run-row/,
  );
  const passLedger = path.join(outputRoot, 'passes.jsonl');
  await appendFile(passLedger, '{"schemaVersion":1,"id":"torn', 'utf8');

  await reconcileManifestPairIntents({ outputRoot, repoRoot: outputRoot });

  assert.deepEqual(await readRows(passLedger), [pair.passManifest]);
  assert.deepEqual(await intentNames(outputRoot), []);
});

test('reconciliation fails closed for terminated or earlier JSONL corruption', async () => {
  for (const [label, corrupted] of [
    ['terminated', '{not-json}\n'],
    ['middle', '{not-json}\n{"unterminated":true'],
  ]) {
    const outputRoot = await mkdtemp(path.join(os.tmpdir(), `metro-${label}-`));
    const pair = await finalizationPair(outputRoot, `corrupt-${label}`);
    await assert.rejects(
      persistManifestPair({
        outputRoot,
        repoRoot: outputRoot,
        ...pair,
        onBoundary: async (completed) => {
          if (completed === 'pass-manifest') throw new Error('stop before ledgers');
        },
      }),
      /stop before ledgers/,
    );
    const runLedger = path.join(outputRoot, 'ledger.jsonl');
    await writeFile(runLedger, corrupted, 'utf8');

    await assert.rejects(
      reconcileManifestPairIntents({ outputRoot, repoRoot: outputRoot }),
      /JSON|Unexpected|position|property/i,
    );
    assert.equal(await readFile(runLedger, 'utf8'), corrupted);
    assert.equal((await intentNames(outputRoot)).length, 1);
  }
});

async function writeStaleOwner(outputRoot, owner) {
  const completeOwner = {
    schemaVersion: 1,
    acquiredAt: new Date(Date.now() - 60_000).toISOString(),
    ...owner,
  };
  const lockDirectory = path.join(outputRoot, LOCK_DIRECTORY);
  const ownerPath = path.join(lockDirectory, OWNER_FILE);
  await mkdir(lockDirectory);
  await writeFile(ownerPath, `${JSON.stringify(completeOwner)}\n`, 'utf8');
  const staleTime = new Date(Date.now() - 60_000);
  await utimes(ownerPath, staleTime, staleTime);
  await utimes(lockDirectory, staleTime, staleTime);
  return completeOwner;
}

async function readOwner(outputRoot) {
  return JSON.parse(await readFile(
    path.join(outputRoot, LOCK_DIRECTORY, OWNER_FILE),
    'utf8',
  ));
}

async function finalizationPair(outputRoot, baseId) {
  const runDirectory = path.join(outputRoot, baseId);
  const runManifestPath = path.join(runDirectory, 'run-manifest.json');
  const passManifestPath = path.join(runDirectory, 'pass-manifest.json');
  await mkdir(runDirectory, { recursive: true });
  const pair = manifestPair(baseId);
  pair.passManifest = buildPassManifest({
    ...completeInput({ id: `${baseId}-pass` }),
    id: `${baseId}-pass`,
    artifacts: [{
      kind: 'run-manifest',
      path: `${baseId}/run-manifest.json`,
    }],
  });
  return { ...pair, runManifestPath, passManifestPath };
}

async function intentNames(outputRoot) {
  return (await readdir(path.join(outputRoot, 'ledger-intents')))
    .filter((name) => name.endsWith('.json'));
}

async function readRows(filePath) {
  return (await readFile(filePath, 'utf8'))
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((row) => JSON.parse(row));
}
