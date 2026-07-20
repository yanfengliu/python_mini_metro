import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  mkdir,
  readFile,
  readdir,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';

import {
  assertCivEngineStateAllowed,
  captureCivEngineState,
  civEngineStateSummary,
} from './source-provenance-engine.mjs';

export const SOURCE_STATE_SCHEMA_VERSION = 1;
export const SOURCE_STATE_ARTIFACT = 'source-state.json';
export const SOURCE_DIFF_ARTIFACT = 'source-diff.patch';

const HASH_ALGORITHM = 'sha256';
const TREE_ROOTS = ['src', 'scripts'];
const ROOT_FILE_PATTERNS = [/^package.*\.json$/, /^requirements.*\.txt$/];
const CACHE_DIRECTORIES = new Set([
  '.mypy_cache',
  '.pytest_cache',
  '.ruff_cache',
  '.tox',
  '.venv',
  '__pycache__',
  'node_modules',
]);
const CACHE_FILE_PATTERNS = [/\.py[co]$/, /^\.DS_Store$/];
const GIT_PATHSPECS = [
  ':(top)src',
  ':(top)scripts',
  ':(top,glob)package*.json',
  ':(top,glob)requirements*.txt',
];

export async function captureSourceState({
  repoRoot,
  enginePackageRoot,
  expectedEnginePackageRoot,
  expectedEngineCommit,
  expectedEngineTreeDigest,
  expectedEngineVersion,
}) {
  const resolvedRoot = path.resolve(repoRoot);
  const [files, engine] = await Promise.all([
    inventorySourceFiles(resolvedRoot),
    captureCivEngineState({
      repoRoot: resolvedRoot,
      enginePackageRoot,
      expectedEnginePackageRoot,
      expectedEngineCommit,
      expectedEngineTreeDigest,
      expectedEngineVersion,
    }),
  ]);
  const status = relevantGitStatus(resolvedRoot);
  return {
    schemaVersion: SOURCE_STATE_SCHEMA_VERSION,
    algorithm: HASH_ALGORITHM,
    treeDigest: digestJson(files),
    fileCount: files.length,
    gitCommit: currentGitCommit(resolvedRoot),
    worktreeDirty: status.length > 0,
    statusDigest: digestJson(status),
    status,
    files,
    engine,
    diffAvailable: false,
  };
}

export async function captureSourceProvenance(options) {
  const { repoRoot } = options;
  const resolvedRoot = path.resolve(repoRoot);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const sourceState = await captureSourceState({
      ...options,
      repoRoot: resolvedRoot,
    });
    const sourceDiff = sourceState.worktreeDirty
      ? relevantGitDiff(resolvedRoot, sourceState.status)
      : '';
    const confirmedState = await captureSourceState({
      ...options,
      repoRoot: resolvedRoot,
    });
    if (!sameCapturedState(sourceState, confirmedState)) continue;
    if (!sourceDiff) {
      return { sourceState, sourceDiff: null };
    }
    return {
      sourceState: {
        ...sourceState,
        diffAvailable: true,
        diffDigest: sha256(sourceDiff),
        diffArtifact: SOURCE_DIFF_ARTIFACT,
      },
      sourceDiff,
    };
  }
  const error = new Error('relevant source changed repeatedly during provenance capture');
  error.code = 'ERR_SOURCE_CAPTURE_UNSTABLE';
  throw error;
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
    });
  validateCapturedDiff(captured.sourceState, captured.sourceDiff);

  const resolvedRunDir = path.resolve(runDir);
  const sourceStatePath = path.join(resolvedRunDir, SOURCE_STATE_ARTIFACT);
  const sourceDiffPath = captured.sourceState.diffAvailable
    ? path.join(resolvedRunDir, SOURCE_DIFF_ARTIFACT)
    : null;
  await mkdir(resolvedRunDir, { recursive: true });
  if (sourceDiffPath) {
    await writeFile(sourceDiffPath, captured.sourceDiff, {
      encoding: 'utf8',
      flag: 'wx',
    });
  }
  await writeFile(
    sourceStatePath,
    `${JSON.stringify(captured.sourceState, null, 2)}\n`,
    { encoding: 'utf8', flag: 'wx' },
  );
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
  const endProvenance = await captureSourceProvenance(captureOptions);
  const comparison = compareSourceStateSummaries(
    startSourceState,
    endProvenance.sourceState,
  );
  if (!comparison.ok) {
    const error = new Error('local or civ-engine source changed during recursive run');
    error.code = 'ERR_SOURCE_CHANGED_DURING_RUN';
    error.startSourceState = structuredClone(startSourceState);
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

async function inventorySourceFiles(repoRoot) {
  const relativePaths = [];
  for (const root of TREE_ROOTS) {
    await walkFiles(repoRoot, root, relativePaths);
  }
  const rootEntries = await readdir(repoRoot, { withFileTypes: true });
  for (const entry of rootEntries) {
    if (
      entry.isFile()
      && ROOT_FILE_PATTERNS.some((pattern) => pattern.test(entry.name))
    ) {
      relativePaths.push(entry.name);
    }
  }
  relativePaths.sort(compareText);
  return Promise.all(relativePaths.map(async (relativePath) => {
    const contents = await readFile(path.join(repoRoot, ...relativePath.split('/')));
    return {
      path: relativePath,
      bytes: contents.byteLength,
      sha256: sha256(contents),
    };
  }));
}

async function walkFiles(repoRoot, relativeDirectory, results) {
  let entries;
  try {
    entries = await readdir(path.join(repoRoot, relativeDirectory), {
      withFileTypes: true,
    });
  } catch (error) {
    if (error?.code === 'ENOENT') return;
    throw error;
  }
  entries.sort((left, right) => compareText(left.name, right.name));
  for (const entry of entries) {
    const relativePath = normalizePath(path.join(relativeDirectory, entry.name));
    if (isExcludedPath(relativePath)) continue;
    if (entry.isDirectory()) {
      await walkFiles(repoRoot, relativePath, results);
    } else if (entry.isFile()) {
      results.push(relativePath);
    }
  }
}

function relevantGitStatus(repoRoot) {
  const output = runGit(repoRoot, [
    'status',
    '--porcelain=v1',
    '-z',
    '--untracked-files=all',
    '--',
    ...GIT_PATHSPECS,
  ]);
  return parsePorcelainStatus(output)
    .filter((entry) => (
      isRelevantPath(entry.path)
      || (entry.originalPath && isRelevantPath(entry.originalPath))
    ))
    .sort((left, right) => compareText(
      `${left.path}\0${left.originalPath ?? ''}\0${left.code}`,
      `${right.path}\0${right.originalPath ?? ''}\0${right.code}`,
    ));
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
    const entry = { code, path: normalizePath(record.slice(3)) };
    if (/[RC]/.test(code)) {
      const originalPath = records[index + 1];
      if (!originalPath) throw new Error('git rename status omitted its original path');
      entry.originalPath = normalizePath(originalPath);
      index += 1;
    }
    status.push(entry);
  }
  return status;
}

function relevantGitDiff(repoRoot, status) {
  const trackedPaths = [...new Set(status
    .filter((entry) => entry.code !== '??')
    .flatMap(
    (entry) => [entry.path, entry.originalPath]
      .filter((candidate) => candidate && isRelevantPath(candidate)),
  ))].sort(compareText);
  const patches = [];
  if (trackedPaths.length > 0) {
    patches.push(runGit(repoRoot, [
      'diff',
      '--no-ext-diff',
      '--no-color',
      '--binary',
      '--full-index',
      'HEAD',
      '--',
      ...trackedPaths.map((changedPath) => `:(literal)${changedPath}`),
    ]));
  }
  const untrackedPaths = status
    .filter((entry) => entry.code === '??' && isRelevantPath(entry.path))
    .map((entry) => entry.path)
    .sort(compareText);
  for (const untrackedPath of untrackedPaths) {
    patches.push(runGit(repoRoot, [
      'diff',
      '--no-index',
      '--no-ext-diff',
      '--no-color',
      '--binary',
      '--full-index',
      '--',
      '/dev/null',
      untrackedPath,
    ], [0, 1]));
  }
  return patches.filter(Boolean).map(ensureTrailingNewline).join('');
}

function currentGitCommit(repoRoot) {
  return runGit(repoRoot, ['rev-parse', 'HEAD']).trim();
}

function runGit(repoRoot, args, allowedStatuses = [0]) {
  const safeRoot = normalizePath(path.resolve(repoRoot));
  const result = spawnSync(
    'git',
    ['-c', `safe.directory=${safeRoot}`, ...args],
    {
      cwd: repoRoot,
      encoding: 'utf8',
      shell: false,
    },
  );
  if (result.error) throw result.error;
  if (!allowedStatuses.includes(result.status)) {
    throw new Error(
      `git ${args[0]} failed with exit ${result.status}: `
      + `${(result.stderr || result.stdout).trim()}`,
    );
  }
  return result.stdout;
}

function sameCapturedState(left, right) {
  return compareSourceStateSummaries(left, right).ok;
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

function isRelevantPath(candidate) {
  const normalized = normalizePath(candidate);
  if (isExcludedPath(normalized)) return false;
  if (TREE_ROOTS.some((root) => (
    normalized === root || normalized.startsWith(`${root}/`)
  ))) return true;
  return !normalized.includes('/')
    && ROOT_FILE_PATTERNS.some((pattern) => pattern.test(normalized));
}

function isExcludedPath(candidate) {
  const parts = normalizePath(candidate).split('/');
  if (parts.some((part) => CACHE_DIRECTORIES.has(part))) return true;
  return CACHE_FILE_PATTERNS.some((pattern) => pattern.test(parts.at(-1)));
}

function normalizePath(candidate) {
  return candidate.split(path.sep).join('/');
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
