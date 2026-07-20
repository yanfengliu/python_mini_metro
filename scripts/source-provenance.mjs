import { createHash } from 'node:crypto';
import {
  mkdir,
  open,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';

import {
  assertCivEngineStateAllowed,
  captureCivEngineState,
  civEngineStateSummary,
} from './source-provenance-engine.mjs';
import {
  crosscheckRelevantWorkingBytes,
  inventoryRelevantSourceFiles,
  isRelevantSourcePath,
  normalizeRepoPath,
  SOURCE_GIT_PATHSPECS,
} from './source-provenance-content.mjs';
import { auditSourceGitMetadata } from './source-provenance-git-safety.mjs';
import { runReadOnlyGit } from './civ-engine-setup-process.mjs';

export const SOURCE_STATE_SCHEMA_VERSION = 1;
export const SOURCE_STATE_ARTIFACT = 'source-state.json';
export const SOURCE_DIFF_ARTIFACT = 'source-diff.patch';

const HASH_ALGORITHM = 'sha256';
const FRESH_SOURCE_STATE_SNAPSHOTS = new WeakMap();

export async function captureSourceState({
  repoRoot,
  enginePackageRoot,
  expectedEnginePackageRoot,
  expectedEngineCommit,
  expectedEngineTreeDigest,
  expectedEngineVersion,
  rootGitRunner = runReadOnlyGit,
}) {
  const resolvedRoot = path.resolve(repoRoot);
  await auditSourceGitMetadata(resolvedRoot);
  const [inventory, engine] = await Promise.all([
    inventoryRelevantSourceFiles(resolvedRoot),
    captureCivEngineState({
      repoRoot: resolvedRoot,
      enginePackageRoot,
      expectedEnginePackageRoot,
      expectedEngineCommit,
      expectedEngineTreeDigest,
      expectedEngineVersion,
    }),
  ]);
  const status = await relevantGitStatus(resolvedRoot, inventory, rootGitRunner);
  const { files } = inventory;
  return registerFreshSourceState({
    schemaVersion: SOURCE_STATE_SCHEMA_VERSION,
    algorithm: HASH_ALGORITHM,
    treeDigest: digestJson(files),
    fileCount: files.length,
    gitCommit: await currentGitCommit(resolvedRoot, rootGitRunner),
    worktreeDirty: status.length > 0,
    statusDigest: digestJson(status),
    status,
    files,
    engine,
    diffAvailable: false,
  });
}

export async function captureSourceProvenance(options) {
  const { repoRoot } = options;
  const resolvedRoot = path.resolve(repoRoot);
  let previousCapture = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const captured = await captureProvenanceAttempt(options, resolvedRoot);
    if (!captured) {
      previousCapture = null;
      continue;
    }
    if (previousCapture && isDeepStrictEqual(previousCapture, captured)) {
      return captured;
    }
    previousCapture = captured;
  }
  const error = new Error('relevant source changed repeatedly during provenance capture');
  error.code = 'ERR_SOURCE_CAPTURE_UNSTABLE';
  throw error;
}

async function captureProvenanceAttempt(options, resolvedRoot) {
  const sourceState = await captureSourceState({
    ...options,
    repoRoot: resolvedRoot,
  });
  const sourceDiff = sourceState.worktreeDirty
    ? await relevantGitDiff(
      resolvedRoot,
      sourceState.status,
      options.rootGitRunner ?? runReadOnlyGit,
    )
    : '';
  const confirmedState = await captureSourceState({
    ...options,
    repoRoot: resolvedRoot,
  });
  if (!sameCapturedState(sourceState, confirmedState)) return null;
  if (!sourceDiff) return { sourceState, sourceDiff: null };
  return {
    sourceState: registerFreshSourceState({
      ...sourceState,
      diffAvailable: true,
      diffDigest: sha256(sourceDiff),
      diffArtifact: SOURCE_DIFF_ARTIFACT,
    }),
    sourceDiff,
  };
}

export async function writeSourceStateArtifacts({
  repoRoot,
  runDir,
  sourceState: capturedState,
  sourceDiff: capturedDiff,
  enginePackageRoot,
  expectedEnginePackageRoot,
  expectedEngineCommit,
  expectedEngineTreeDigest,
  expectedEngineVersion,
  rootGitRunner,
}) {
  const captured = capturedState
    ? { sourceState: capturedState, sourceDiff: capturedDiff ?? null }
    : await captureSourceProvenance({
      repoRoot,
      enginePackageRoot,
      expectedEnginePackageRoot,
      expectedEngineCommit,
      expectedEngineTreeDigest,
      expectedEngineVersion,
      ...(rootGitRunner ? { rootGitRunner } : {}),
    });
  assertFreshSourceStateIdentity(captured.sourceState);
  const sourceStateSnapshot = structuredClone(captured.sourceState);
  validateCapturedDiff(sourceStateSnapshot, captured.sourceDiff);

  const resolvedRunDir = path.resolve(runDir);
  const sourceStatePath = path.join(resolvedRunDir, SOURCE_STATE_ARTIFACT);
  const sourceDiffPath = sourceStateSnapshot.diffAvailable
    ? path.join(resolvedRunDir, SOURCE_DIFF_ARTIFACT)
    : null;
  await mkdir(resolvedRunDir, { recursive: true });
  assertFreshSourceStateIdentity(captured.sourceState);
  const sourceStateDocument = `${JSON.stringify(sourceStateSnapshot, null, 2)}\n`;
  const sourceStateHandle = await open(sourceStatePath, 'wx');
  try {
    if (sourceDiffPath) {
      await writeFile(sourceDiffPath, captured.sourceDiff, {
        encoding: 'utf8',
        flag: 'wx',
      });
    }
    await sourceStateHandle.writeFile(sourceStateDocument, { encoding: 'utf8' });
  } finally {
    await sourceStateHandle.close();
  }
  assertFreshSourceStateIdentity(captured.sourceState);
  return {
    sourceState: captured.sourceState,
    sourceDiff: captured.sourceDiff,
    sourceStatePath,
    sourceDiffPath,
  };
}

export function sourceStateSummary(sourceState) {
  const summary = {
    schemaVersion: sourceState.schemaVersion,
    algorithm: sourceState.algorithm,
    treeDigest: sourceState.treeDigest,
    fileCount: sourceState.fileCount,
    gitCommit: sourceState.gitCommit,
    worktreeDirty: sourceState.worktreeDirty,
    statusDigest: sourceState.statusDigest,
    diffAvailable: sourceState.diffAvailable,
    engine: civEngineStateSummary(sourceState.engine),
  };
  if (sourceState.diffAvailable) summary.diffDigest = sourceState.diffDigest;
  return summary;
}

export function assertSourceStateAllowed(sourceState, { allowDirty = false } = {}) {
  assertFreshSourceStateIdentity(sourceState);
  assertCivEngineStateAllowed(sourceState.engine, { allowDirty });
  if (!sourceState.worktreeDirty || allowDirty) return sourceState;
  const changedPaths = sourceState.status
    .flatMap((entry) => [entry.path, entry.originalPath])
    .filter(Boolean)
    .slice(0, 8);
  const suffix = sourceState.status.length > changedPaths.length ? ', ...' : '';
  const error = new Error(
    `relevant source worktree is dirty (${changedPaths.join(', ')}${suffix}); `
    + 'commit or restore it, or explicitly rerun with --allow-dirty',
  );
  error.code = 'ERR_RELEVANT_SOURCE_DIRTY';
  error.sourceState = sourceState;
  throw error;
}

export function compareSourceStateSummaries(startSourceState, endSourceState) {
  const startSummary = sourceStateSummary(startSourceState);
  const endSummary = sourceStateSummary(endSourceState);
  return {
    ok: isDeepStrictEqual(startSummary, endSummary),
    startSummary,
    endSummary,
  };
}

export async function recaptureAndAssertSourceUnchanged({
  startSourceState,
  ...captureOptions
}) {
  if (!startSourceState) throw new TypeError('startSourceState is required');
  assertFreshSourceStateIdentity(startSourceState);
  const startSnapshot = structuredClone(startSourceState);
  const endProvenance = await captureSourceProvenance(captureOptions);
  assertFreshSourceStateIdentity(startSourceState);
  const comparison = compareSourceStateSummaries(
    startSnapshot,
    endProvenance.sourceState,
  );
  if (!comparison.ok) {
    const error = new Error('local or civ-engine source changed during recursive run');
    error.code = 'ERR_SOURCE_CHANGED_DURING_RUN';
    error.startSourceState = startSnapshot;
    error.endSourceState = structuredClone(endProvenance.sourceState);
    error.endProvenance = endProvenance;
    error.startSummary = comparison.startSummary;
    error.endSummary = comparison.endSummary;
    throw error;
  }
  return {
    ...comparison,
    endSourceState: endProvenance.sourceState,
    endProvenance,
  };
}

async function relevantGitStatus(repoRoot, inventory, rootGitRunner) {
  const output = await runGit(repoRoot, [
    'status',
    '--porcelain=v1',
    '-z',
    '--untracked-files=all',
    '--',
    ...SOURCE_GIT_PATHSPECS,
  ], [0], rootGitRunner);
  const indexOutput = await runGit(repoRoot, [
    'ls-files',
    '-v',
    '-z',
    '--',
    ...SOURCE_GIT_PATHSPECS,
  ], [0], rootGitRunner);
  const trackedPaths = parseRelevantIndex(indexOutput);
  const status = parsePorcelainStatus(output)
    .filter((entry) => (
      isRelevantSourcePath(entry.path)
      || (entry.originalPath && isRelevantSourcePath(entry.originalPath))
    ));
  return crosscheckRelevantWorkingBytes({
    inventory,
    status,
    trackedPaths,
    readGit: (args) => runGit(repoRoot, args, [0], rootGitRunner),
  });
}

function parsePorcelainStatus(output) {
  const records = output.split('\0');
  const status = [];
  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (!record) continue;
    if (record.length < 4 || record[2] !== ' ') {
      throw new Error(`unexpected git status record: ${JSON.stringify(record)}`);
    }
    const code = record.slice(0, 2);
    const entry = { code, path: normalizeRepoPath(record.slice(3)) };
    if (/[RC]/.test(code)) {
      const originalPath = records[index + 1];
      if (!originalPath) throw new Error('git rename status omitted its original path');
      entry.originalPath = normalizeRepoPath(originalPath);
      index += 1;
    }
    status.push(entry);
  }
  return status;
}

function parseRelevantIndex(output) {
  const trackedPaths = new Set();
  for (const record of output.split('\0')) {
    if (!record) continue;
    if (record.length < 3 || record[1] !== ' ') {
      throw unsafeGitIndex('unexpected relevant index record');
    }
    const tag = record[0];
    const relativePath = normalizeRepoPath(record.slice(2));
    if (!isRelevantSourcePath(relativePath)) continue;
    if (tag === 'S' || tag === 's') {
      throw unsafeGitIndex(`skip-worktree flag on ${relativePath}`);
    }
    if (tag === tag.toLowerCase()) {
      throw unsafeGitIndex(`assume-unchanged flag on ${relativePath}`);
    }
    if (tag !== 'H') {
      throw unsafeGitIndex(`unsupported index state on ${relativePath}`);
    }
    trackedPaths.add(relativePath);
  }
  return trackedPaths;
}

async function relevantGitDiff(repoRoot, status, rootGitRunner) {
  const trackedPaths = [...new Set(status
    .filter((entry) => entry.code !== '??')
    .flatMap(
    (entry) => [entry.path, entry.originalPath]
      .filter((candidate) => candidate && isRelevantSourcePath(candidate)),
  ))].sort(compareText);
  const patches = [];
  if (trackedPaths.length > 0) {
    patches.push(await runGit(repoRoot, [
      'diff',
      '--no-ext-diff',
      '--no-textconv',
      '--no-color',
      '--binary',
      '--full-index',
      'HEAD',
      '--',
      ...trackedPaths.map((changedPath) => `:(literal)${changedPath}`),
    ], [0], rootGitRunner));
  }
  const untrackedPaths = status
    .filter((entry) => entry.code === '??' && isRelevantSourcePath(entry.path))
    .map((entry) => entry.path)
    .sort(compareText);
  for (const untrackedPath of untrackedPaths) {
    patches.push(await runGit(repoRoot, [
      'diff',
      '--no-index',
      '--no-ext-diff',
      '--no-textconv',
      '--no-color',
      '--binary',
      '--full-index',
      '--',
      '/dev/null',
      untrackedPath,
    ], [0, 1], rootGitRunner));
  }
  return patches.filter(Boolean).map(ensureTrailingNewline).join('');
}

async function currentGitCommit(repoRoot, rootGitRunner) {
  return (await runGit(
    repoRoot,
    ['rev-parse', 'HEAD'],
    [0],
    rootGitRunner,
  )).trim();
}

async function runGit(repoRoot, args, allowedStatuses, rootGitRunner) {
  await auditSourceGitMetadata(repoRoot);
  return rootGitRunner({ repoRoot, args, allowedStatuses });
}

function sameCapturedState(left, right) {
  return compareSourceStateSummaries(left, right).ok;
}

function assertFreshSourceStateIdentity(sourceState) {
  const snapshot = sourceState && typeof sourceState === 'object'
    ? FRESH_SOURCE_STATE_SNAPSHOTS.get(sourceState)
    : undefined;
  if (
    !snapshot
    || !isDeepStrictEqual(snapshot, sourceState)
    || !Array.isArray(sourceState.status)
    || !Array.isArray(sourceState.files)
    || typeof sourceState.diffAvailable !== 'boolean'
  ) {
    throw new TypeError('an intact fresh source capture is required');
  }
}

function registerFreshSourceState(sourceState) {
  const frozenState = freezeCapture(sourceState);
  FRESH_SOURCE_STATE_SNAPSHOTS.set(frozenState, structuredClone(frozenState));
  return frozenState;
}

function freezeCapture(value, seen = new Set()) {
  if (value === null || typeof value !== 'object' || seen.has(value)) return value;
  seen.add(value);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || descriptor.get || descriptor.set) {
      throw new TypeError('source capture must contain only data properties');
    }
    freezeCapture(descriptor.value, seen);
  }
  return Object.freeze(value);
}

function ensureTrailingNewline(value) {
  return value && !value.endsWith('\n') ? `${value}\n` : value;
}

function validateCapturedDiff(sourceState, sourceDiff) {
  if (!sourceState.diffAvailable) {
    if (sourceDiff) {
      throw new Error('source diff was supplied but source state marks it unavailable');
    }
    return;
  }
  if (typeof sourceDiff !== 'string' || sourceDiff.length === 0) {
    throw new Error('source state requires nonempty source diff content');
  }
  if (sourceState.diffArtifact !== SOURCE_DIFF_ARTIFACT) {
    throw new Error(`source diff artifact must be ${SOURCE_DIFF_ARTIFACT}`);
  }
  if (sourceState.diffDigest !== sha256(sourceDiff)) {
    throw new Error('source diff content does not match its recorded digest');
  }
}

function digestJson(value) {
  return sha256(JSON.stringify(value));
}

function sha256(value) {
  return createHash(HASH_ALGORITHM).update(value).digest('hex');
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function unsafeGitIndex(message) {
  return Object.assign(new Error(`source Git index rejected: ${message}`), {
    code: 'ERR_SOURCE_GIT_UNSAFE',
  });
}
