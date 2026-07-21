import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { stateDigest, assertImprovementFinding } from 'civ-engine';

export function compareEvidence({
  originalTranscript,
  replayTranscript,
  originalFindings,
  replayFindings,
  originalRunId,
  replayRunId,
  inputsMatch = true,
}) {
  requireRunId(originalRunId, 'originalRunId');
  requireRunId(replayRunId, 'replayRunId');
  validateAuthoredFindings(originalFindings, 'original');
  validateAuthoredFindings(replayFindings, 'replay');
  validateTranscript(originalTranscript, 'original');
  validateTranscript(replayTranscript, 'replay');

  const originalCheckpointDigests = originalTranscript.map((row) => (
    stateDigest(row.checkpoint)
  ));
  const replayCheckpointDigests = replayTranscript.map((row) => (
    stateDigest(row.checkpoint)
  ));
  const checkpointVectorsMatch = exactJsonMultiset(
    originalTranscript.map((row) => row.checkpoint),
    replayTranscript.map((row) => row.checkpoint),
    false,
  );
  const transcriptInputsMatch = exactJsonMultiset(
    originalTranscript.map(transcriptEvidenceWithoutCheckpoint),
    replayTranscript.map(transcriptEvidenceWithoutCheckpoint),
    false,
  );
  const findingsMatch = exactJsonMultiset(
    originalFindings,
    replayFindings,
    true,
  );
  const finalStateMatches = checkpointVectorsMatch && transcriptInputsMatch;
  const ok = finalStateMatches && findingsMatch && inputsMatch;

  const verifiedFindings = ok
    ? replayFindings.map((finding) => verifiedSuccessor(finding, originalRunId))
    : [];
  const verificationFindings = ok
    ? []
    : [replayMismatchFinding({
      originalRunId,
      replayRunId,
      checkpointVectorsMatch,
      transcriptInputsMatch,
      findingsMatch,
      inputsMatch,
    })];

  return {
    verification: {
      schemaVersion: 1,
      method: 'fresh-process-full-checkpoint-vector',
      originalRunId,
      replayRunId,
      ok,
      finalStateMatches,
      findingsMatch,
      inputsMatch,
      transcriptRows: originalTranscript.length,
      replayTranscriptRows: replayTranscript.length,
      originalCheckpointDigests,
      replayCheckpointDigests,
      verifiedFindingIds: verifiedFindings.map((finding) => finding.id),
    },
    verifiedFindings,
    verificationFindings,
  };
}

export async function verifyRun({
  runDir,
  pythonBin,
  repoRoot,
  outputDir = runDir,
  replayDir = path.join(runDir, 'redrive'),
  replayLabel = 'redrive',
}) {
  const originalInputs = await readJson(path.join(runDir, 'inputs.json'));
  const originalTranscript = await readJsonl(path.join(runDir, 'transcript.jsonl'));
  const originalFindings = await readJson(
    path.join(runDir, 'findings.authored.json'),
  );
  const originalRunId = originalInputs.runId;
  requireRunId(originalRunId, 'recorded inputs runId');

  const replayRunId = `${originalRunId}-${replayLabel}`;
  await fs.mkdir(outputDir, { recursive: true });
  await fs.mkdir(replayDir, { recursive: false });
  const runner = path.join(repoRoot, 'src', 'recursive_playtest.py');
  const replay = await runCaptured(
    pythonBin,
    [
      runner,
      '--inputs',
      path.join(runDir, 'inputs.json'),
      '--out',
      replayDir,
      '--run-id',
      replayRunId,
    ],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONHASHSEED: String(originalInputs.pythonHashSeed ?? '0'),
      },
    },
  );
  await fs.writeFile(
    path.join(replayDir, 'redrive.stdout.log'),
    replay.stdout,
    'utf8',
  );
  await fs.writeFile(
    path.join(replayDir, 'redrive.stderr.log'),
    replay.stderr,
    'utf8',
  );
  if (replay.spawnError) {
    throw phaseError('verify', `redrive spawn failed: ${replay.spawnError.message}`);
  }
  if (replay.exitCode !== 0) {
    throw phaseError('verify', `redrive exited ${replay.exitCode}`);
  }

  const replayInputs = await readJson(path.join(replayDir, 'inputs.json'));
  const replayTranscript = await readJsonl(path.join(replayDir, 'transcript.jsonl'));
  const replayFindings = await readJson(
    path.join(replayDir, 'findings.authored.json'),
  );
  const inputsMatch = stableJson(replayableInputs(originalInputs))
    === stableJson(replayableInputs(replayInputs));
  const comparison = compareEvidence({
    originalTranscript,
    replayTranscript,
    originalFindings,
    replayFindings,
    originalRunId,
    replayRunId,
    inputsMatch,
  });
  await writeJson(
    path.join(outputDir, 'verification.json'),
    comparison.verification,
  );
  await writeJson(
    path.join(outputDir, 'findings.verified.json'),
    comparison.verifiedFindings,
  );
  await writeJson(
    path.join(outputDir, 'findings.verification.json'),
    comparison.verificationFindings,
  );
  return comparison;
}

function validateAuthoredFindings(findings, label) {
  if (!Array.isArray(findings)) {
    throw new TypeError(`${label} authored findings must be an array`);
  }
  for (const finding of findings) {
    assertImprovementFinding(finding, { requireVerificationEvidence: false });
    if (
      finding.verificationStatus !== 'unverified'
      || finding.verificationMethod !== undefined
    ) {
      throw new Error(`${label} findings must be born unverified`);
    }
  }
}

function validateTranscript(rows, label) {
  if (!Array.isArray(rows)) {
    throw new TypeError(`${label} transcript must be an array`);
  }
  for (const [index, row] of rows.entries()) {
    if (!row || typeof row !== 'object' || row.index !== index || !('checkpoint' in row)) {
      throw new Error(`${label} transcript row ${index} is invalid`);
    }
  }
}

function verifiedSuccessor(replayFinding, originalRunId) {
  const evidence = [
    ...(replayFinding.evidence ?? []).map((ref) => structuredClone(ref)),
    { kind: 'bundle', sessionId: originalRunId },
  ];
  const verified = {
    ...structuredClone(replayFinding),
    evidence,
    verificationStatus: 'verified',
    verificationMethod: 'replay',
  };
  assertImprovementFinding(verified, { requireVerificationEvidence: true });
  return verified;
}

function replayMismatchFinding({
  originalRunId,
  replayRunId,
  checkpointVectorsMatch,
  transcriptInputsMatch,
  findingsMatch,
  inputsMatch,
}) {
  const mismatches = [
    ...(!checkpointVectorsMatch ? ['checkpoint vector'] : []),
    ...(!transcriptInputsMatch ? ['transcript result'] : []),
    ...(!findingsMatch ? ['authored finding semantics'] : []),
    ...(!inputsMatch ? ['recorded input metadata'] : []),
  ];
  const finding = {
    schemaVersion: 2,
    id: 'deterministic-replay-mismatch',
    title: 'Fresh-process replay diverged',
    severity: 'critical',
    category: 'regression',
    observed: `Fresh replay changed: ${mismatches.join(', ')}.`,
    expected: 'Recorded inputs must reproduce every transcript result, checkpoint, and oracle claim exactly.',
    suggestion: 'Make the drive deterministic or extend the canonical checkpoint before promoting findings.',
    area: 'recursive playtest harness',
    evidence: [
      { kind: 'bundle', sessionId: originalRunId },
      { kind: 'bundle', sessionId: replayRunId },
    ],
    verificationStatus: 'unverified',
    nextAction: 'improveHarness',
    promotionTarget: 'test',
    disposition: 'candidate',
    data: { class: 'deterministic-replay-mismatch' },
  };
  assertImprovementFinding(finding, { requireVerificationEvidence: false });
  return finding;
}

function transcriptEvidenceWithoutCheckpoint(row) {
  const { checkpoint: _checkpoint, ...evidence } = row;
  return evidence;
}

function exactJsonMultiset(left, right, ignoreOrder) {
  if (left.length !== right.length) return false;
  const leftJson = left.map(stableJson);
  const rightJson = right.map(stableJson);
  if (ignoreOrder) {
    leftJson.sort();
    rightJson.sort();
  }
  return leftJson.every((value, index) => value === rightJson[index]);
}

function stableJson(value) {
  return JSON.stringify(sortJson(value));
}

export function replayableInputs(inputs) {
  const replayable = {
    schemaVersion: inputs.schemaVersion,
    seed: inputs.seed,
    defaultDtMs: inputs.defaultDtMs,
    pythonExecutable: inputs.pythonExecutable,
    pythonHashSeed: inputs.pythonHashSeed,
    operations: inputs.operations,
  };
  if (
    inputs.schemaVersion === 2
    || inputs.schemaVersion === 3
    || inputs.schemaVersion === 4
  ) {
    replayable.environmentRewardContract = inputs.environmentRewardContract;
  }
  if (inputs.schemaVersion === 3 || inputs.schemaVersion === 4) {
    replayable.overduePassengerThreshold = inputs.overduePassengerThreshold;
  }
  if (inputs.schemaVersion === 4) {
    replayable.fleetActionContract = inputs.fleetActionContract;
  }
  return replayable;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function readJsonl(filePath) {
  return (await fs.readFile(filePath, 'utf8'))
    .split(/\r?\n/)
    .filter((row) => row.length > 0)
    .map((row) => JSON.parse(row));
}

async function writeJson(filePath, value) {
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  return readJson(filePath);
}

function runCaptured(command, args, options) {
  return new Promise((resolvePromise) => {
    let child;
    try {
      child = spawn(command, args, {
        ...options,
        shell: false,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (error) {
      resolvePromise({
        exitCode: null,
        stdout: '',
        stderr: '',
        spawnError: error,
      });
      return;
    }
    let stdout = '';
    let stderr = '';
    let spawnError = null;
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', (error) => { spawnError = error; });
    child.on('close', (code) => resolvePromise({
      exitCode: code,
      stdout,
      stderr,
      spawnError,
    }));
  });
}

function phaseError(phase, message) {
  const error = new Error(message);
  error.phase = phase;
  return error;
}

function sortJson(value) {
  if (Array.isArray(value)) return value.map(sortJson);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, sortJson(value[key])]),
    );
  }
  return value;
}

function requireRunId(value, label) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new TypeError(`${label} must be a non-empty string`);
  }
}

async function main() {
  const runDir = process.argv[2];
  if (!runDir || runDir === '--help' || runDir === '-h') {
    console.log('Usage: npm run playtest:verify -- <output/recursive/run-id>');
    process.exit(runDir ? 0 : 2);
  }
  const repoRoot = process.cwd();
  const pythonBin = process.env.PYTHON || 'python';
  try {
    const absoluteRunDir = path.resolve(runDir);
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const replayLabel = `verify-${stamp}-${randomUUID().slice(0, 8)}`;
    const outputDir = path.join(
      absoluteRunDir,
      'verification-attempts',
      replayLabel,
    );
    const replayDir = path.join(outputDir, 'redrive');
    const result = await verifyRun({
      runDir: absoluteRunDir,
      pythonBin,
      repoRoot,
      outputDir,
      replayDir,
      replayLabel,
    });
    console.log(JSON.stringify(result.verification, null, 2));
    process.exit(result.verification.ok ? 0 : 1);
  } catch (error) {
    console.error(error instanceof Error ? error.stack : String(error));
    process.exit(1);
  }
}

if (
  process.argv[1]
  && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  await main();
}
