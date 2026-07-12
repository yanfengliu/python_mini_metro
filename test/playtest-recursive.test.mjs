import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import {
  access,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { assertCompleteManifest } from '../scripts/recursive-pass.mjs';
import { sourceStateSummary } from '../scripts/source-provenance.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const defaultScenario = path.join(
  repoRoot,
  'scripts',
  'fixtures',
  'recursive-playtest.json',
);
const testOutputBase = path.join(repoRoot, 'output', 'node-tests');

test('default recursive pass writes verified evidence and complete ledgers', async () => {
  await withOutputRoot(async (outputRoot) => {
    const run = await runRecursive({ outputRoot, scenario: defaultScenario });
    assert.equal(run.exitCode, 0, run.stderr || run.stdout);

    const passRows = await ledgerRows(path.join(outputRoot, 'passes.jsonl'));
    const runRows = await ledgerRows(path.join(outputRoot, 'ledger.jsonl'));
    assert.equal(passRows.length, 1);
    assert.equal(runRows.length, 1);
    assert.equal(passRows[0].stopReason, 'no-fix-candidate');
    assert.equal(runRows[0].stopReason, 'verified');
    for (const row of [...passRows, ...runRows]) {
      assert.doesNotThrow(() => assertCompleteManifest(row));
      await assertArtifactsExist(row);
    }

    const runDir = await onlyRunDirectory(outputRoot);
    const inputs = JSON.parse(await readFile(path.join(runDir, 'inputs.json'), 'utf8'));
    const transcriptRows = await jsonlRows(path.join(runDir, 'transcript.jsonl'));
    const authored = JSON.parse(
      await readFile(path.join(runDir, 'findings.authored.json'), 'utf8'),
    );
    const verification = JSON.parse(
      await readFile(path.join(runDir, 'verification.json'), 'utf8'),
    );
    const sourceState = JSON.parse(
      await readFile(path.join(runDir, 'source-state.json'), 'utf8'),
    );
    assert.equal(inputs.schemaVersion, 2);
    assert.equal(inputs.environmentRewardContract, 'deliveries');
    assert.equal(transcriptRows.length, inputs.operations.length);
    assert.equal(verification.ok, true);
    assert.equal(verification.finalStateMatches, true);
    assert.equal(verification.findingsMatch, true);
    assert.deepEqual(passRows[0].data.sourceState, sourceStateSummary(sourceState));
    assert.deepEqual(runRows[0].data.sourceState, sourceStateSummary(sourceState));
    assert.ok(passRows[0].artifacts.some((artifact) => (
      artifact.kind === 'source-state'
      && artifact.path.endsWith('/source-state.json')
    )));
    assert.equal(
      passRows[0].artifacts.some((artifact) => artifact.kind === 'source-diff'),
      sourceState.diffAvailable,
    );
    assert.ok(authored.every((finding) => (
      finding.verificationStatus === 'unverified'
      && finding.verificationMethod === undefined
    )));

    const originalVerificationPath = path.join(runDir, 'verification.json');
    const originalVerification = await readFile(originalVerificationPath, 'utf8');
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const repeated = await runVerifier(runDir);
      assert.equal(repeated.exitCode, 0, repeated.stderr || repeated.stdout);
      assert.equal(await readFile(originalVerificationPath, 'utf8'), originalVerification);
    }
    const attempts = await readdir(path.join(runDir, 'verification-attempts'), {
      withFileTypes: true,
    });
    assert.equal(attempts.filter((entry) => entry.isDirectory()).length, 2);
  });
});

test('a missing Python executable appends exactly one attributable failure row', async () => {
  await withOutputRoot(async (outputRoot) => {
    const missingPython = path.join(outputRoot, 'missing-python-executable');
    const run = await runRecursive({
      outputRoot,
      scenario: defaultScenario,
      env: { PYTHON: missingPython },
    });
    assert.equal(run.exitCode, 1);
    await assertSingleRunFailed(outputRoot, 'spawn');
  });
});

test('a nonzero child appends exactly one attributable failure row', async () => {
  await withOutputRoot(async (outputRoot) => {
    const run = await runRecursive({
      outputRoot,
      scenario: defaultScenario,
      env: { PYTHON: process.execPath },
    });
    assert.equal(run.exitCode, 1);
    await assertSingleRunFailed(outputRoot, 'drive');
  });
});

test('an unparseable scenario appends exactly one attributable failure row', async () => {
  await withOutputRoot(async (outputRoot) => {
    const scenario = path.join(outputRoot, 'unparseable-scenario.json');
    await writeFile(scenario, '{ definitely not json', 'utf8');
    const run = await runRecursive({ outputRoot, scenario });
    assert.equal(run.exitCode, 1);
    await assertSingleRunFailed(outputRoot, 'drive');
  });
});

test('normal recursive CLI refuses relevant dirty source without override', async () => {
  await withOutputRoot(async (outputRoot) => {
    const probePath = path.join(repoRoot, 'requirements-provenance-probe.txt');
    await writeFile(probePath, 'temporary dirty-source probe\n', {
      encoding: 'utf8',
      flag: 'wx',
    });
    try {
      const run = await runRecursive({
        outputRoot,
        scenario: defaultScenario,
        allowDirty: false,
      });
      assert.equal(run.exitCode, 2);
      assert.match(run.stderr, /relevant source worktree is dirty/i);
      assert.match(run.stderr, /--allow-dirty/);
      assert.deepEqual(await readdir(outputRoot), []);
    } finally {
      await rm(probePath, { force: true });
    }
  });
});

test('mid-run source drift records a complete final source patch', async () => {
  await withOutputRoot(async (outputRoot) => {
    const probePath = path.join(repoRoot, 'requirements-provenance-probe.txt');
    const scenario = path.join(outputRoot, 'slow-scenario.json');
    await writeFile(probePath, 'before recursive drive\n', {
      encoding: 'utf8',
      flag: 'wx',
    });
    await writeFile(scenario, JSON.stringify({
      schemaVersion: 1,
      seed: 42,
      defaultDtMs: 16,
      operations: Array.from({ length: 200 }, (_, index) => ({
        name: `noop-${index}`,
        action: { type: 'noop' },
        expectedActionOk: true,
      })),
    }), 'utf8');
    try {
      const running = runRecursive({ outputRoot, scenario });
      const runDir = await waitForRunArtifact(outputRoot, 'source-state.json');
      await writeFile(probePath, 'after recursive drive\n', 'utf8');
      const run = await running;

      assert.equal(run.exitCode, 1, run.stderr || run.stdout);
      await assertSingleRunFailed(outputRoot, 'source-changed');
      const finalState = JSON.parse(await readFile(
        path.join(runDir, 'source-state.final.json'),
        'utf8',
      ));
      const finalPatch = await readFile(
        path.join(runDir, 'source-diff.final.patch'),
        'utf8',
      );
      assert.equal(finalState.diffArtifact, 'source-diff.final.patch');
      assert.match(finalPatch, /\+after recursive drive/);
      assert.ok(finalState.diffAvailable);
    } finally {
      await rm(probePath, { force: true });
    }
  });
});

test('public verifier recovers append-only after a failed first attempt', async () => {
  await withOutputRoot(async (outputRoot) => {
    const runDir = path.join(outputRoot, 'drive-only');
    const drive = await runDrive(runDir);
    assert.equal(drive.exitCode, 0, drive.stderr || drive.stdout);

    const missingPython = path.join(outputRoot, 'missing-python-executable');
    const failed = await runVerifier(runDir, { PYTHON: missingPython });
    assert.equal(failed.exitCode, 1);

    const recovered = await runVerifier(runDir);
    assert.equal(recovered.exitCode, 0, recovered.stderr || recovered.stdout);
    await assert.rejects(
      () => access(path.join(runDir, 'verification.json')),
      /ENOENT/,
    );

    const attempts = await readdir(path.join(runDir, 'verification-attempts'), {
      withFileTypes: true,
    });
    const attemptDirectories = attempts.filter((entry) => entry.isDirectory());
    assert.equal(attemptDirectories.length, 2);
    const verificationResults = await Promise.all(attemptDirectories.map(
      async (entry) => {
        try {
          await access(path.join(
            runDir,
            'verification-attempts',
            entry.name,
            'verification.json',
          ));
          return true;
        } catch {
          return false;
        }
      },
    ));
    assert.deepEqual(verificationResults.sort(), [false, true]);
  });
});

test('public verifier replays genuine v1 inputs without a reward-contract field', async () => {
  await withOutputRoot(async (outputRoot) => {
    const legacyScenario = path.join(outputRoot, 'legacy-v1-scenario.json');
    const runDir = path.join(outputRoot, 'legacy-v1-drive');
    await writeFile(legacyScenario, JSON.stringify({
      schemaVersion: 1,
      seed: 42,
      defaultDtMs: 16,
      operations: [{
        name: 'legacy-noop',
        action: { type: 'noop' },
        expectedActionOk: true,
      }],
    }), 'utf8');

    const drive = await runDrive(runDir, legacyScenario, 'legacy-v1-drive');
    assert.equal(drive.exitCode, 0, drive.stderr || drive.stdout);
    const inputs = JSON.parse(await readFile(path.join(runDir, 'inputs.json'), 'utf8'));
    assert.equal(inputs.schemaVersion, 1);
    assert.equal('environmentRewardContract' in inputs, false);

    const verification = await runVerifier(runDir);
    assert.equal(verification.exitCode, 0, verification.stderr || verification.stdout);
    const result = JSON.parse(verification.stdout);
    assert.equal(result.ok, true);
    assert.equal(result.inputsMatch, true);
  });
});

async function assertSingleRunFailed(outputRoot, expectedPhase) {
  const passRows = await ledgerRows(path.join(outputRoot, 'passes.jsonl'));
  const runRows = await ledgerRows(path.join(outputRoot, 'ledger.jsonl'));
  assert.equal(passRows.length, 1);
  assert.equal(runRows.length, 1);
  for (const row of [...passRows, ...runRows]) {
    assert.equal(row.stopReason, 'run-failed');
    assert.equal(row.data.failurePhase, expectedPhase);
    assert.doesNotThrow(() => assertCompleteManifest(row));
    await assertArtifactsExist(row);
  }
}

async function assertArtifactsExist(manifest) {
  for (const artifact of manifest.artifacts) {
    await access(path.join(repoRoot, artifact.path));
  }
}

async function withOutputRoot(callback) {
  await mkdir(testOutputBase, { recursive: true });
  const outputRoot = await mkdtemp(path.join(testOutputBase, 'recursive-'));
  try {
    await callback(outputRoot);
  } finally {
    await rm(outputRoot, {
      recursive: true,
      force: true,
      maxRetries: 5,
      retryDelay: 100,
    });
  }
}

async function waitForRunArtifact(outputRoot, artifactName) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    const entries = await readdir(outputRoot, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory() || entry.name === 'ledger-intents') continue;
      const runDir = path.join(outputRoot, entry.name);
      try {
        await access(path.join(runDir, artifactName));
        return runDir;
      } catch {
        // The driver writes provenance before spawning Python; keep polling.
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error(`timed out waiting for ${artifactName}`);
}

function runRecursive({ outputRoot, scenario, env = {}, allowDirty = true }) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(
      process.execPath,
      [
        'scripts/playtest-recursive.mjs',
        ...(allowDirty ? ['--allow-dirty'] : []),
        '--scenario',
        scenario,
        '--output-root',
        outputRoot,
      ],
      {
        cwd: repoRoot,
        env: { ...process.env, ...env },
        shell: false,
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => resolvePromise({
      exitCode: code ?? -1,
      stdout,
      stderr,
    }));
  });
}

function runDrive(runDir, scenario = defaultScenario, runId = 'public-verifier-partial-probe') {
  return runChild(
    process.env.PYTHON || 'python',
    [
      path.join(repoRoot, 'src', 'recursive_playtest.py'),
      '--scenario',
      scenario,
      '--out',
      runDir,
      '--run-id',
      runId,
    ],
    { PYTHONHASHSEED: '0' },
  );
}

function runVerifier(runDir, env = {}) {
  return runChild(
    process.execPath,
    ['scripts/playtest-verify.mjs', runDir],
    env,
  );
}

function runChild(command, args, env = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(
      command,
      args,
      {
        cwd: repoRoot,
        env: { ...process.env, ...env },
        shell: false,
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => resolvePromise({
      exitCode: code ?? -1,
      stdout,
      stderr,
    }));
  });
}

async function onlyRunDirectory(outputRoot) {
  const entries = await readdir(outputRoot, { withFileTypes: true });
  const directories = entries.filter((entry) => (
    entry.isDirectory() && entry.name !== 'ledger-intents'
  ));
  assert.equal(directories.length, 1);
  return path.join(outputRoot, directories[0].name);
}

async function ledgerRows(filePath) {
  return jsonlRows(filePath);
}

async function jsonlRows(filePath) {
  return (await readFile(filePath, 'utf8'))
    .split(/\r?\n/)
    .filter((row) => row.length > 0)
    .map((row) => JSON.parse(row));
}
