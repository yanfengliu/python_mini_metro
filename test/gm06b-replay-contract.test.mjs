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
const carriageContract = 'explicit_carriage_attachment_v1';

function baseInputs(schemaVersion) {
  return {
    schemaVersion,
    runId: `run-v${schemaVersion}`,
    sourcePath: `scenario-v${schemaVersion}.json`,
    seed: 42,
    defaultDtMs: 16,
    pythonExecutable: 'python',
    pythonHashSeed: '42',
    operations: [{
      name: 'noop',
      action: { type: 'noop' },
      expectedActionOk: true,
    }],
  };
}

function baseProjection(schemaVersion) {
  const input = baseInputs(schemaVersion);
  const { runId: _runId, sourcePath: _sourcePath, ...projection } = input;
  return projection;
}

async function readFixture(name) {
  return readFile(path.join(fixtureRoot, name), 'utf8');
}

function sha256(text) {
  return createHash('sha256').update(text).digest('hex');
}

test('frozen checkpoint and recursive fixture bytes are exact', async () => {
  const expected = new Map([
    ['checkpoint-v1.json', 'a2ca592cd34befcdf3aced1793a500ba348ee6f7816feb7d80f4146790d2c7f0'],
    ['checkpoint-v2.json', '1a18165f5aef625359ba72f5bc438f87ca2ac5713b697c3528b62603d0ba1350'],
    ['recursive-playtest-v1.json', 'e6ce51a06423675d4b933a7fc34bfdb235f46b0c941124786c5ae49c52f1eab4'],
    ['recursive-playtest-v2.json', 'e9f78980ce5d3dcf2ca243b4d8b142a803fba7a8518b1a62b089f6151a4d2228'],
    ['recursive-playtest-v3.json', 'c1eb0f8541a1614398abef6a8e2f9dc333ba95717d78f64eecc281d3177cb9ed'],
  ]);

  for (const [name, digest] of expected) {
    assert.equal(sha256(await readFixture(name)), digest, name);
  }
});

test('the default recursive fixture is v5 and uses replay-safe resource indices', async () => {
  const document = JSON.parse(await readFixture('recursive-playtest.json'));
  assert.equal(document.schemaVersion, 5);
  assert.equal(document.environmentRewardContract, 'deliveries');
  assert.equal(document.overduePassengerThreshold, 2);
  assert.equal(document.fleetActionContract, fleetContract);
  assert.equal(document.carriageActionContract, carriageContract);

  const assignment = document.operations.find(
    (operation) => operation.action.type === 'assign_locomotive',
  );
  assert.ok(assignment);
  assert.deepEqual(assignment.action, {
    type: 'assign_locomotive',
    path_index: 0,
  });
  const attachment = document.operations.find(
    (operation) => operation.action.type === 'attach_carriage',
  );
  assert.ok(attachment);
  assert.deepEqual(attachment.action, {
    type: 'attach_carriage',
    path_index: 0,
  });
  assert.equal(JSON.stringify(document).includes('path_id'), false);
});

test('Node replay projection preserves literal v1 v2 and v3 contracts exactly', () => {
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
});

test('Node replay projection binds every v4 environment and fleet field', () => {
  const v4 = {
    ...baseInputs(4),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
    fleetActionContract: fleetContract,
  };

  assert.deepEqual(replayableInputs(v4), {
    ...baseProjection(4),
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
    fleetActionContract: fleetContract,
  });
});
