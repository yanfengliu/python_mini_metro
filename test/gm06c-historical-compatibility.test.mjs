import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { replayableInputs } from '../scripts/playtest-verify.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fixtureRoot = path.join(repoRoot, 'scripts', 'fixtures');
const fleetContract = 'explicit_locomotive_assignment_v1';
const expectedHashes = new Map([
  ['checkpoint-v1.json', 'a2ca592cd34befcdf3aced1793a500ba348ee6f7816feb7d80f4146790d2c7f0'],
  ['checkpoint-v2.json', '1a18165f5aef625359ba72f5bc438f87ca2ac5713b697c3528b62603d0ba1350'],
  ['checkpoint-v3.json', '9ca2f5bce174a8c59c608cb08bc3e5903151ab0ad04df6553c21f166bed63c02'],
  ['recursive-playtest-v1.json', 'e6ce51a06423675d4b933a7fc34bfdb235f46b0c941124786c5ae49c52f1eab4'],
  ['recursive-playtest-v2.json', 'e9f78980ce5d3dcf2ca243b4d8b142a803fba7a8518b1a62b089f6151a4d2228'],
  ['recursive-playtest-v3.json', 'c1eb0f8541a1614398abef6a8e2f9dc333ba95717d78f64eecc281d3177cb9ed'],
  ['recursive-playtest-v4.json', '807429bf99283a79341c1e78d4984880ec53deaccab1d5bc36ec2b4cf9610cee'],
  ['gm06b-legacy-outcomes.json', '5b234533ede170d9b4419a42e0e2d8f1e4dfa5005a4932c09ddeb8df8b22cbfe'],
  ['gm06c-pre-carriage-outcomes.json', 'd070943f3de09df8cb18ef6e96caea875dd72541f5b5598c669e35563459e67a'],
]);

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function baseInputs(schemaVersion) {
  return {
    schemaVersion,
    runId: `historical-v${schemaVersion}`,
    sourcePath: `recursive-playtest-v${schemaVersion}.json`,
    seed: 42,
    defaultDtMs: 16,
    pythonExecutable: 'python',
    pythonHashSeed: '0',
    operations: [{
      name: 'noop',
      action: { type: 'noop' },
      expectedActionOk: true,
    }],
  };
}

function baseProjection(schemaVersion) {
  const { runId: _runId, sourcePath: _sourcePath, ...projection } = baseInputs(schemaVersion);
  return projection;
}

test('GM-06c historical fixture bytes remain exact LF evidence', async () => {
  for (const [name, expected] of expectedHashes) {
    const payload = await readFile(path.join(fixtureRoot, name));
    assert.equal(payload.includes(13), false, `${name} contains CR bytes`);
    assert.equal(payload.at(-1), 10, `${name} lacks its terminal LF`);
    assert.equal(sha256(payload), expected, name);
  }

  const checkpointV3 = await readFile(path.join(fixtureRoot, 'checkpoint-v3.json'));
  const recursiveV4 = await readFile(path.join(fixtureRoot, 'recursive-playtest-v4.json'));
  assert.equal(checkpointV3.length, 16_262);
  assert.equal(recursiveV4.length, 1_608);

  const outcomes = JSON.parse(
    await readFile(path.join(fixtureRoot, 'gm06c-pre-carriage-outcomes.json'), 'utf8'),
  );
  assert.equal(outcomes.schemaVersion, 1);
  assert.equal(outcomes.recursiveV4.transcript_rows, 9);
  assert.equal(outcomes.recursiveV4.checkpoint_sha256.length, 9);
  assert.equal(outcomes.agentV4.schema, 'mini-metro-agent-play-v4');
  assert.equal(outcomes.agentV4.checkpoint_count, 3);
});

test('Node replay projection preserves literal v1 through v4 fields', () => {
  const v1 = baseInputs(1);
  const v2 = {
    ...baseInputs(2),
    environmentRewardContract: 'deliveries',
  };
  const v3 = {
    ...baseInputs(3),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
  };
  const v4 = {
    ...baseInputs(4),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
    fleetActionContract: fleetContract,
  };

  assert.deepEqual(replayableInputs(v1), baseProjection(1));
  assert.deepEqual(replayableInputs(v2), {
    ...baseProjection(2),
    environmentRewardContract: 'deliveries',
  });
  assert.deepEqual(replayableInputs(v3), {
    ...baseProjection(3),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
  });
  assert.deepEqual(replayableInputs(v4), {
    ...baseProjection(4),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
    fleetActionContract: fleetContract,
  });
});
