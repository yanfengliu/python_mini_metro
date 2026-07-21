import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { replayableInputs, verifyRun } from '../scripts/playtest-verify.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const defaultScenario = path.join(
  repoRoot,
  'scripts',
  'fixtures',
  'recursive-playtest.json',
);
const pythonBin = process.env.PYTHON || 'python';
const fleetContract = 'explicit_locomotive_assignment_v1';
const carriageContract = 'explicit_carriage_attachment_v1';

function runCaptured(command, args, options) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      ...options,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', (error) => resolve({ error, stdout, stderr, exitCode: null }));
    child.on('close', (exitCode) => resolve({ stdout, stderr, exitCode }));
  });
}

async function jsonlRows(filePath) {
  return (await readFile(filePath, 'utf8'))
    .split(/\r?\n/)
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line));
}

function assertCarriageBijection(checkpoint) {
  const recordKeys = ['attachment_index', 'capacity', 'metro_motion_index'];
  let cursor = 0;
  for (const [metroIndex, metro] of checkpoint.metroMotion.entries()) {
    const expected = Array.from(
      { length: metro.carriage_indices.length },
      (_, offset) => cursor + offset,
    );
    assert.deepEqual(metro.carriage_indices, expected);
    for (const [attachmentIndex, carriageIndex] of expected.entries()) {
      const carriage = checkpoint.carriages[carriageIndex];
      assert.deepEqual(Object.keys(carriage).toSorted(), recordKeys);
      assert.equal(carriage.metro_motion_index, metroIndex);
      assert.equal(carriage.attachment_index, attachmentIndex);
    }
    cursor += expected.length;
  }
  assert.equal(cursor, checkpoint.carriages.length);

  const globalCount = checkpoint.structured.metros.length;
  const globalCarriageCount = checkpoint.metroMotion
    .slice(0, globalCount)
    .reduce((total, metro) => total + metro.carriage_indices.length, 0);
  assert.equal(checkpoint.structured.carriages.length, globalCarriageCount);
  assert.deepEqual(
    checkpoint.structured.carriages,
    checkpoint.carriages.slice(0, globalCarriageCount),
  );
  for (const carriage of checkpoint.structured.carriages) {
    assert.deepEqual(Object.keys(carriage).toSorted(), recordKeys);
  }
  for (const [metroIndex, metro] of checkpoint.structured.metros.entries()) {
    assert.deepEqual(
      metro.carriage_indices,
      checkpoint.metroMotion[metroIndex].carriage_indices,
    );
    assert.equal(metro.capacity, checkpoint.metroMotion[metroIndex].capacity);
    for (const carriageIndex of metro.carriage_indices) {
      assert.ok(carriageIndex >= 0 && carriageIndex < globalCarriageCount);
    }
  }
  for (const metro of checkpoint.metroMotion.slice(globalCount)) {
    for (const carriageIndex of metro.carriage_indices) {
      assert.ok(carriageIndex >= globalCarriageCount);
    }
  }

  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (value !== null && typeof value === 'object') {
      for (const [key, item] of Object.entries(value)) {
        assert.notEqual(key, 'id');
        assert.equal(key.endsWith('_id'), false, key);
        assert.equal(key.endsWith('_ids'), false, key);
        visit(item);
      }
      return;
    }
    if (typeof value === 'string') {
      for (const prefix of ['Metro-', 'Carriage-', 'Path-', 'Station-', 'Passenger-']) {
        assert.equal(value.includes(prefix), false, value);
      }
    }
  };
  visit(checkpoint);
}

test('Node replay projection binds both v5 fleet contracts exactly', () => {
  const inputs = {
    schemaVersion: 5,
    runId: 'gm06c-node-v5',
    sourcePath: 'scripts/fixtures/recursive-playtest.json',
    seed: 42,
    defaultDtMs: 16,
    pythonExecutable: 'python',
    pythonHashSeed: '0',
    environmentRewardContract: 'deliveries',
    overduePassengerThreshold: 2,
    fleetActionContract: fleetContract,
    carriageActionContract: carriageContract,
    operations: [{
      name: 'attach',
      action: { type: 'attach_carriage', path_index: 0 },
      expectedActionOk: true,
    }],
  };
  const { runId: _runId, sourcePath: _sourcePath, ...expected } = inputs;
  assert.deepEqual(replayableInputs(inputs), expected);
});

test('Node fresh-process v5 redrive compares a retained nonempty carriage checkpoint', async () => {
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), 'gm06c-node-redrive-'));
  try {
    const runDir = path.join(temporaryRoot, 'original');
    const initial = await runCaptured(
      pythonBin,
      [
        path.join(repoRoot, 'src', 'recursive_playtest.py'),
        '--scenario',
        defaultScenario,
        '--out',
        runDir,
        '--run-id',
        'gm06c-node-v5',
      ],
      {
        cwd: repoRoot,
        env: { ...process.env, PYTHONHASHSEED: '0' },
      },
    );
    assert.equal(initial.error, undefined, initial.error?.message);
    assert.equal(initial.exitCode, 0, initial.stderr || initial.stdout);

    const inputs = JSON.parse(await readFile(path.join(runDir, 'inputs.json'), 'utf8'));
    assert.equal(inputs.schemaVersion, 5);
    assert.equal(inputs.fleetActionContract, fleetContract);
    assert.equal(inputs.carriageActionContract, carriageContract);

    const outputDir = path.join(temporaryRoot, 'verification');
    const replayDir = path.join(outputDir, 'redrive');
    const verification = await verifyRun({
      runDir,
      pythonBin,
      repoRoot,
      outputDir,
      replayDir,
      replayLabel: 'gm06c-node-v5-redrive',
    });
    assert.equal(verification.verification.ok, true);
    assert.equal(
      verification.verification.method,
      'fresh-process-full-checkpoint-vector',
    );

    const transcript = await jsonlRows(path.join(runDir, 'transcript.jsonl'));
    const attachment = transcript.find(
      (row) => row.action?.type === 'attach_carriage',
    );
    assert.ok(attachment);
    assert.equal(attachment.actionOk, true);
    assert.equal(attachment.checkpoint.schemaVersion, 4);
    assert.ok(attachment.checkpoint.carriages.length > 0);
    assert.ok(attachment.checkpoint.structured.carriages.length > 0);
    assertCarriageBijection(attachment.checkpoint);

    const replayTranscript = await jsonlRows(path.join(replayDir, 'transcript.jsonl'));
    assert.deepEqual(
      replayTranscript.map((row) => row.checkpoint),
      transcript.map((row) => row.checkpoint),
    );
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
});
