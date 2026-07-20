// Proposal-only recursive pass for python_mini_metro.
//
// Drives the checked-in scenario through MiniMetroEnv, re-drives the exact
// recorded inputs in a fresh Python process, promotes only mechanically
// re-derived findings, selects the highest-severity fix candidate, and writes
// complete run/pass manifests plus append-only ledgers. A proposal is a handoff
// to the driving agent, not a finished pass.

import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

import {
  assertSourceStateAllowed,
  captureSourceProvenance,
  recaptureAndAssertSourceUnchanged,
  sourceStateSummary,
  writeSourceStateArtifacts,
} from './source-provenance.mjs';
import { parseRecursiveArgs } from './recursive-args.mjs';

const repoRoot = process.cwd();
const args = parseRecursiveArgs(process.argv.slice(2));
let sourceProvenance;
try {
  sourceProvenance = await captureSourceProvenance({ repoRoot });
  assertSourceStateAllowed(sourceProvenance.sourceState, {
    allowDirty: args.allowDirty === true,
  });
} catch (error) {
  console.error(`[recursive] ${error instanceof Error ? error.message : String(error)}`);
  const policyError = error?.code === 'ERR_RELEVANT_SOURCE_DIRTY'
    || error?.code === 'ERR_CIV_ENGINE_PROVENANCE';
  process.exit(policyError ? 2 : 1);
}
const {
  buildPassManifest,
  buildRunManifest,
  findingClassOf,
  persistManifestPair,
  reconcileManifestPairIntents,
  repoRelativePath,
  selectFixCandidate,
} = await import('./recursive-pass.mjs');
const { verifyRun } = await import('./playtest-verify.mjs');
const outputBase = path.resolve(repoRoot, 'output');
const outputRoot = path.resolve(args.outputRoot ?? path.join(outputBase, 'recursive'));
assertInsideOutput(outputRoot);
await fs.mkdir(outputRoot, { recursive: true });
await reconcileManifestPairIntents({ outputRoot, repoRoot });

const startedAtMs = Date.now();
const startedAt = new Date(startedAtMs).toISOString();
const stamp = startedAt.replace(/[:.]/g, '-');
const runId = `recursive-${stamp}-${randomUUID().slice(0, 8)}`;
const runDir = path.join(outputRoot, runId);
await fs.mkdir(runDir, { recursive: false });
await writeSourceStateArtifacts({
  runDir,
  sourceState: sourceProvenance.sourceState,
  sourceDiff: sourceProvenance.sourceDiff,
});
const capturedSourceState = sourceStateSummary(sourceProvenance.sourceState);

const context = {
  startedAt,
  startedAtMs,
  runId,
  runDir,
  outputRoot,
  pythonBin: process.env.PYTHON || 'python',
  hashSeed: process.env.PYTHONHASHSEED || '0',
  scenario: path.resolve(args.scenario ?? path.join(
    repoRoot,
    'scripts',
    'fixtures',
    'recursive-playtest.json',
  )),
  gitCommit: sourceProvenance.sourceState.gitCommit,
  sourceState: capturedSourceState,
  startSourceState: sourceProvenance.sourceState,
  seed: 'unavailable',
  finalized: false,
};

let result;
try {
  result = await executePass(context);
} catch (error) {
  result = failureResult(error, context.seed);
}

try {
  result = await finalize(context, result);
  console.log(JSON.stringify({
    runId,
    outcome: result.passOutcome,
    candidate: result.candidate?.id ?? null,
  }, null, 2));
  process.exit(result.exitCode);
} catch (error) {
  console.error(`[recursive] finalization failed: ${error instanceof Error ? error.stack : String(error)}`);
  process.exit(1);
}

async function executePass(current) {
  const drive = await runCaptured(
    current.pythonBin,
    [
      path.join(repoRoot, 'src', 'recursive_playtest.py'),
      '--scenario',
      current.scenario,
      '--out',
      current.runDir,
      '--run-id',
      current.runId,
    ],
    {
      cwd: repoRoot,
      env: { ...process.env, PYTHONHASHSEED: current.hashSeed },
    },
  );
  await fs.writeFile(path.join(current.runDir, 'drive.stdout.log'), drive.stdout, 'utf8');
  await fs.writeFile(path.join(current.runDir, 'drive.stderr.log'), drive.stderr, 'utf8');
  if (drive.spawnError) {
    throw phaseError('spawn', `drive spawn failed: ${drive.spawnError.message}`);
  }
  if (drive.exitCode !== 0) {
    throw phaseError('drive', `drive exited ${drive.exitCode}`);
  }

  const inputs = await readJson(path.join(current.runDir, 'inputs.json'));
  current.seed = inputs.seed;
  const comparison = await verifyRun({
    runDir: current.runDir,
    pythonBin: current.pythonBin,
    repoRoot,
  });
  if (!comparison.verification.ok) {
    throw phaseError('verify', 'fresh-process verification diverged');
  }
  const candidate = selectFixCandidate(comparison.verifiedFindings);
  return {
    exitCode: 0,
    passOutcome: candidate ? 'proposal-only' : 'no-fix-candidate',
    runOutcome: 'verified',
    seed: inputs.seed,
    candidate,
    verification: comparison.verification,
    failurePhase: null,
    errorMessage: null,
  };
}

function failureResult(error, seed) {
  return {
    exitCode: 1,
    passOutcome: 'run-failed',
    runOutcome: 'run-failed',
    seed,
    candidate: null,
    verification: null,
    failurePhase: error?.phase ?? 'orchestration',
    errorMessage: error instanceof Error ? error.message : String(error),
  };
}

async function finalize(current, passResult) {
  if (current.finalized) throw new Error('recursive pass finalized more than once');
  current.finalized = true;
  passResult = await attributeFinalSourceState(current, passResult);
  const completedAtMs = Date.now();
  const completedAt = new Date(completedAtMs).toISOString();
  const durationMs = completedAtMs - current.startedAtMs;
  const artifacts = await collectArtifacts(current.runDir);
  const gates = passResult.exitCode === 0
    ? [
      { name: 'scripted-drive', ok: true },
      { name: 'fresh-process-redrive', ok: true },
    ]
    : [{
      name: passResult.failurePhase,
      ok: false,
      detail: passResult.errorMessage,
    }];
  const shared = {
    startedAt: current.startedAt,
    completedAt,
    durationMs,
    seed: passResult.seed,
    gitCommit: current.gitCommit,
    sourceState: current.sourceState,
    artifacts,
    gates,
  };
  const runManifest = buildRunManifest({
    ...shared,
    id: `${current.runId}-run`,
    objective: 'Drive and mechanically verify the recorded Mini Metro scenario.',
    stopReason: passResult.runOutcome,
    data: resultData(passResult),
  });
  const runManifestPath = path.join(current.runDir, 'run-manifest.json');

  const passArtifacts = [
    ...artifacts,
    { kind: 'run-manifest', path: repoRelativePath(repoRoot, runManifestPath) },
  ];
  const passManifest = buildPassManifest({
    ...shared,
    id: `${current.runId}-pass`,
    objective: 'Select the top verified recursive improvement candidate.',
    stopReason: passResult.passOutcome,
    artifacts: passArtifacts,
    data: resultData(passResult),
  });
  const passManifestPath = path.join(current.runDir, 'pass-manifest.json');
  await persistManifestPair({
    outputRoot: current.outputRoot,
    runManifest,
    passManifest,
    runManifestPath,
    passManifestPath,
    repoRoot,
  });
  return passResult;
}

async function attributeFinalSourceState(current, passResult) {
  try {
    await recaptureAndAssertSourceUnchanged({
      repoRoot,
      startSourceState: current.startSourceState,
    });
    return passResult;
  } catch (error) {
    const changed = error?.code === 'ERR_SOURCE_CHANGED_DURING_RUN';
    if (changed) await writeFinalSourceStateArtifacts(current.runDir, error);
    const attributed = failureResult(
      phaseError(
        changed ? 'source-changed' : 'source-recapture',
        error instanceof Error ? error.message : String(error),
      ),
      current.seed,
    );
    if (changed) {
      attributed.sourceChange = {
        start: error.startSummary,
        end: error.endSummary,
      };
    }
    return attributed;
  }
}

async function writeFinalSourceStateArtifacts(runDir, error) {
  const finalStateName = 'source-state.final.json';
  const finalDiffName = 'source-diff.final.patch';
  const finalState = {
    ...error.endSourceState,
    ...(error.endSourceState.diffAvailable ? { diffArtifact: finalDiffName } : {}),
  };
  if (error.endProvenance?.sourceDiff) {
    await fs.writeFile(
      path.join(runDir, finalDiffName),
      error.endProvenance.sourceDiff,
      { encoding: 'utf8', flag: 'wx' },
    );
  }
  await fs.writeFile(
    path.join(runDir, finalStateName),
    `${JSON.stringify(finalState, null, 2)}\n`,
    { encoding: 'utf8', flag: 'wx' },
  );
}

function resultData(result) {
  return {
    ...(result.candidate ? {
      candidateFindingId: result.candidate.id,
      candidateClass: findingClassOf(result.candidate),
    } : {}),
    ...(result.verification ? { verification: result.verification } : {}),
    ...(result.failurePhase ? {
      failurePhase: result.failurePhase,
      errorMessage: result.errorMessage,
    } : {}),
    ...(result.sourceChange ? { sourceChange: result.sourceChange } : {}),
  };
}

async function collectArtifacts(directory) {
  const candidates = [
    ['source-state', 'source-state.json'],
    ['source-diff', 'source-diff.patch'],
    ['source-state-final', 'source-state.final.json'],
    ['source-diff-final', 'source-diff.final.patch'],
    ['inputs', 'inputs.json'],
    ['transcript', 'transcript.jsonl'],
    ['authored-findings', 'findings.authored.json'],
    ['run-result', 'run-result.json'],
    ['drive-stdout', 'drive.stdout.log'],
    ['drive-stderr', 'drive.stderr.log'],
    ['verification', 'verification.json'],
    ['verified-findings', 'findings.verified.json'],
    ['verification-findings', 'findings.verification.json'],
    ['redrive-inputs', path.join('redrive', 'inputs.json')],
    ['redrive-transcript', path.join('redrive', 'transcript.jsonl')],
    ['redrive-findings', path.join('redrive', 'findings.authored.json')],
    ['redrive-result', path.join('redrive', 'run-result.json')],
    ['redrive-stdout', path.join('redrive', 'redrive.stdout.log')],
    ['redrive-stderr', path.join('redrive', 'redrive.stderr.log')],
  ];
  const artifacts = [];
  for (const [kind, relative] of candidates) {
    const absolute = path.join(directory, relative);
    try {
      await fs.access(absolute);
      artifacts.push({ kind, path: repoRelativePath(repoRoot, absolute) });
    } catch {
      // Failure manifests list only evidence that was actually written.
    }
  }
  return artifacts;
}

function runCaptured(command, commandArgs, options) {
  return new Promise((resolvePromise) => {
    let child;
    try {
      child = spawn(command, commandArgs, {
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

function assertInsideOutput(target) {
  const relative = path.relative(outputBase, target);
  if (
    relative === '..'
    || relative.startsWith(`..${path.sep}`)
    || path.isAbsolute(relative)
  ) {
    throw new Error(`recursive output root must stay under ${outputBase}`);
  }
}

function phaseError(phase, message) {
  const error = new Error(message);
  error.phase = phase;
  return error;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}
