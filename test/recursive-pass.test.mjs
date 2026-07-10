import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { assertImprovementRunManifest } from 'civ-engine';

import {
  appendManifestPair,
  appendValidatedManifestRow,
  assertCompleteManifest,
  buildPassManifest,
  buildRunManifest,
  createManifestPairIntent,
  reconcileManifestPairIntents,
  repoRelativePath,
  selectFixCandidate,
  writeValidatedManifest,
} from '../scripts/recursive-pass.mjs';
import { sourceStateFixture } from './recursive-fixtures.mjs';

function completeInput(overrides = {}) {
  const gitCommit = '11161a54e402c33dd5d08c67d355dc02a5900a0a';
  return {
    id: 'python-mini-metro-recursive-2026-07-10',
    objective: 'Run and verify the deterministic scripted metro scenario.',
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

function verifiedFinding(overrides = {}) {
  return {
    schemaVersion: 2,
    id: 'candidate-a',
    title: 'Candidate A',
    severity: 'medium',
    category: 'bug',
    observed: 'Observed A.',
    verificationStatus: 'verified',
    verificationMethod: 'replay',
    evidence: [{ kind: 'bundle', sessionId: 'run-a' }],
    nextAction: 'manualFix',
    promotionTarget: 'test',
    disposition: 'candidate',
    data: { class: 'candidate-a' },
    ...overrides,
  };
}

test('pass and run manifests satisfy engine and repo completeness contracts', () => {
  const pass = buildPassManifest(completeInput());
  const run = buildRunManifest(completeInput({ stopReason: 'verified' }));

  for (const manifest of [pass, run]) {
    assert.doesNotThrow(() => assertImprovementRunManifest(manifest));
    assert.doesNotThrow(() => assertCompleteManifest(manifest));
    assert.equal(manifest.gameId, 'python_mini_metro');
    assert.equal(manifest.engineVersion, '2.2.0');
    assert.equal(manifest.provider, 'scripted');
    assert.equal(manifest.costUsd, 0);
    assert.equal(manifest.data.sourceState.treeDigest, 'a'.repeat(64));
    assert.ok(manifest.tags.includes('source-state-v1'));
  }
});

test('new manifests require strict source state while legacy rows remain readable', () => {
  assert.throws(
    () => buildPassManifest(completeInput({ sourceState: undefined })),
    /source state/i,
  );

  const current = buildPassManifest(completeInput());
  const invalid = structuredClone(current);
  invalid.data.sourceState.treeDigest = 'not-a-digest';
  assert.throws(() => assertCompleteManifest(invalid), /source state/i);

  const legacy = structuredClone(current);
  legacy.tags = legacy.tags.filter((tag) => tag !== 'source-state-v1');
  delete legacy.data.sourceState;
  assert.doesNotThrow(() => assertCompleteManifest(legacy));
});

test('repo completeness rejects sparse engine-valid manifests', () => {
  const sparse = { schemaVersion: 1, id: 'sparse' };
  assert.doesNotThrow(() => assertImprovementRunManifest(sparse));
  assert.throws(
    () => assertCompleteManifest(sparse),
    /gameId|objective|seed|gitCommit/,
  );
});

test('repo completeness rejects invalid outcomes, seeds, and artifact descriptors', () => {
  const valid = buildPassManifest(completeInput());
  const invalid = [
    { ...valid, stopReason: 'banana', data: { ...valid.data, outcome: 'banana' } },
    { ...valid, seed: -1 },
    { ...valid, seed: 1.5 },
    { ...valid, seed: 'not-unavailable' },
    { ...valid, artifacts: [{ kind: '', path: '' }] },
  ];
  for (const manifest of invalid) {
    assert.throws(() => assertCompleteManifest(manifest));
  }
});

test('candidate selection requires strict verified evidence, routing, and stable class', () => {
  const highUnverified = verifiedFinding({
    id: 'unverified',
    severity: 'critical',
    verificationStatus: 'unverified',
    verificationMethod: undefined,
    evidence: [{ kind: 'step', step: 0 }],
    data: { class: 'unverified' },
  });
  const highProposal = verifiedFinding({
    id: 'proposal',
    severity: 'high',
    nextAction: 'proposalOnly',
    data: { class: 'proposal' },
  });
  const medium = verifiedFinding();
  const critical = verifiedFinding({
    id: 'candidate-critical',
    severity: 'critical',
    data: { class: 'candidate-critical' },
  });

  assert.equal(
    selectFixCandidate([highUnverified, highProposal, medium, critical]).id,
    'candidate-critical',
  );
  assert.equal(selectFixCandidate([
    verifiedFinding({ data: {}, id: 'missing-class' }),
  ]), null);
});

test('manifest files and ledgers are validated after read-back', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'mini-metro-manifest-'));
  const manifestPath = path.join(temp, 'pass-manifest.json');
  const ledgerPath = path.join(temp, 'passes.jsonl');
  const manifest = buildPassManifest(completeInput());

  await writeValidatedManifest(manifestPath, manifest);
  await appendValidatedManifestRow(ledgerPath, manifest);

  const persisted = JSON.parse(await readFile(manifestPath, 'utf8'));
  assert.deepEqual(persisted, manifest);
  const rows = (await readFile(ledgerPath, 'utf8')).trim().split('\n');
  assert.equal(rows.length, 1);
  assert.deepEqual(JSON.parse(rows[0]), manifest);
});

test('persistence rejects nonexistent artifact paths before writing', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'mini-metro-artifact-'));
  const manifestPath = path.join(temp, 'pass-manifest.json');
  const manifest = buildPassManifest(completeInput({
    artifacts: [{ kind: 'missing', path: 'output/does-not-exist.json' }],
  }));
  await assert.rejects(() => writeValidatedManifest(
    manifestPath,
    manifest,
    { repoRoot: temp },
  ), /does not exist|regular file/i);
  await assert.rejects(() => readFile(manifestPath, 'utf8'), /ENOENT/);
});

test('manifest-pair transactions serialize concurrent writers and exact retries', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'mini-metro-pairs-'));
  const pairs = Array.from({ length: 16 }, (_, index) => {
    const shared = completeInput({
      id: `pair-${index}`,
      seed: index,
    });
    return {
      runManifest: buildRunManifest({
        ...shared,
        id: `pair-${index}-run`,
        stopReason: 'verified',
      }),
      passManifest: buildPassManifest({
        ...shared,
        id: `pair-${index}-pass`,
      }),
    };
  });
  await Promise.all(pairs.map((pair) => appendManifestPair({
    outputRoot: temp,
    repoRoot: temp,
    ...pair,
  })));
  const runs = await readRows(path.join(temp, 'ledger.jsonl'));
  const passes = await readRows(path.join(temp, 'passes.jsonl'));
  assert.equal(runs.length, pairs.length);
  assert.equal(passes.length, pairs.length);
  assert.deepEqual(
    new Set(runs.map((row) => row.id.replace(/-run$/, ''))),
    new Set(passes.map((row) => row.id.replace(/-pass$/, ''))),
  );

  await appendManifestPair({ outputRoot: temp, repoRoot: temp, ...pairs[0] });
  assert.equal((await readRows(path.join(temp, 'ledger.jsonl'))).length, pairs.length);
  assert.equal((await readRows(path.join(temp, 'passes.jsonl'))).length, pairs.length);
  await assert.rejects(() => appendManifestPair({
    outputRoot: temp,
    repoRoot: temp,
    runManifest: { ...pairs[0].runManifest, objective: 'conflicting retry' },
    passManifest: pairs[0].passManifest,
  }), /conflict/i);
});

test('durable pair intent reconciles a crash between ledger appends', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'mini-metro-reconcile-'));
  const shared = completeInput({ id: 'crash-pair' });
  const runManifest = buildRunManifest({
    ...shared,
    id: 'crash-pair-run',
    stopReason: 'verified',
  });
  const passManifest = buildPassManifest({
    ...shared,
    id: 'crash-pair-pass',
  });
  await createManifestPairIntent({
    outputRoot: temp,
    repoRoot: temp,
    runManifest,
    passManifest,
  });
  await appendValidatedManifestRow(
    path.join(temp, 'ledger.jsonl'),
    runManifest,
    { repoRoot: temp },
  );
  const prefix = await readFile(path.join(temp, 'ledger.jsonl'), 'utf8');

  await reconcileManifestPairIntents({ outputRoot: temp, repoRoot: temp });

  assert.equal((await readRows(path.join(temp, 'ledger.jsonl'))).length, 1);
  assert.equal((await readRows(path.join(temp, 'passes.jsonl'))).length, 1);
  assert.ok((await readFile(path.join(temp, 'ledger.jsonl'), 'utf8')).startsWith(prefix));
});

test('repoRelativePath returns portable in-repo paths and rejects escape', () => {
  const root = path.resolve('C:/workspace/repo');
  assert.equal(
    repoRelativePath(root, path.join(root, 'output', 'run', 'inputs.json')),
    'output/run/inputs.json',
  );
  assert.throws(
    () => repoRelativePath(root, path.resolve(root, '..', 'secret.txt')),
    /outside/i,
  );
});

async function readRows(filePath) {
  return (await readFile(filePath, 'utf8'))
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((row) => JSON.parse(row));
}
