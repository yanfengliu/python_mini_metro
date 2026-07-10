import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

export const EXPECTED_CIV_ENGINE_COMMIT = 'e0cb614a516c449159a4562c2ac45bd40bffd3df';
export const EXPECTED_CIV_ENGINE_VERSION = '2.2.0';
export const EXPECTED_CIV_ENGINE_TREE_DIGEST = '960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891';

const SCHEMA_VERSION = 1;
const HASH_ALGORITHM = 'sha256';
const PACKAGE_NAME = 'civ-engine';
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const TEXT_RUNTIME_EXTENSIONS = new Set(['.js', '.json', '.map', '.ts']);

export async function captureCivEngineState({
  repoRoot,
  enginePackageRoot,
  expectedEngineCommit = EXPECTED_CIV_ENGINE_COMMIT,
  expectedEngineVersion = EXPECTED_CIV_ENGINE_VERSION,
  expectedEngineTreeDigest = EXPECTED_CIV_ENGINE_TREE_DIGEST,
}) {
  const resolvedRepoRoot = path.resolve(repoRoot);
  const requestedRoot = path.resolve(
    enginePackageRoot ?? path.join(resolvedRepoRoot, 'node_modules', PACKAGE_NAME),
  );
  try {
    const resolvedPackageRoot = await fs.realpath(requestedRoot);
    const packageDocument = JSON.parse(await fs.readFile(
      path.join(resolvedPackageRoot, 'package.json'),
      'utf8',
    ));
    const runtimeEntry = resolveRuntimeEntry(packageDocument);
    const files = await inventoryRuntimeFiles(resolvedPackageRoot);
    if (!files.some((entry) => entry.path === runtimeEntry)) {
      throw new Error(`resolved civ-engine runtime entry is missing: ${runtimeEntry}`);
    }
    const status = gitStatus(resolvedPackageRoot);
    const gitCommit = runGit(resolvedPackageRoot, ['rev-parse', 'HEAD']).trim();
    const treeDigest = digestJson(files);
    const summary = {
      schemaVersion: SCHEMA_VERSION,
      available: true,
      packageName: packageDocument.name ?? null,
      resolvedPackageRoot: portablePackageRoot(resolvedRepoRoot, resolvedPackageRoot),
      packageVersion: packageDocument.version ?? null,
      expectedPackageVersion: expectedEngineVersion,
      versionMatches: packageDocument.version === expectedEngineVersion,
      runtimeEntry,
      gitCommit,
      expectedGitCommit: expectedEngineCommit,
      commitMatches: gitCommit === expectedEngineCommit,
      worktreeDirty: status.length > 0,
      statusDigest: digestJson(status),
      algorithm: HASH_ALGORITHM,
      treeDigest,
      expectedTreeDigest: expectedEngineTreeDigest,
      runtimeMatches: treeDigest === expectedEngineTreeDigest,
      fileCount: files.length,
      error: null,
    };
    assertCivEngineStateSummary(summary);
    return {
      ...summary,
      localResolvedPackageRoot: normalizePath(resolvedPackageRoot),
      status,
      files,
      summary: structuredClone(summary),
    };
  } catch (error) {
    const summary = {
      schemaVersion: SCHEMA_VERSION,
      available: false,
      packageName: null,
      resolvedPackageRoot: portablePackageRoot(resolvedRepoRoot, requestedRoot),
      packageVersion: null,
      expectedPackageVersion: expectedEngineVersion,
      versionMatches: false,
      runtimeEntry: null,
      gitCommit: null,
      expectedGitCommit: expectedEngineCommit,
      commitMatches: false,
      worktreeDirty: null,
      statusDigest: null,
      algorithm: HASH_ALGORITHM,
      treeDigest: null,
      expectedTreeDigest: expectedEngineTreeDigest,
      runtimeMatches: false,
      fileCount: 0,
      error: error instanceof Error ? error.message : String(error),
    };
    assertCivEngineStateSummary(summary);
    return {
      ...summary,
      localResolvedPackageRoot: normalizePath(requestedRoot),
      status: [],
      files: [],
      summary: structuredClone(summary),
    };
  }
}

export function civEngineStateSummary(state) {
  const summary = state?.summary ?? state;
  assertCivEngineStateSummary(summary);
  return structuredClone(summary);
}

export function assertCivEngineStateAllowed(state, { allowDirty = false } = {}) {
  const summary = civEngineStateSummary(state);
  if (!summary.available) {
    throw provenanceError(`civ-engine runtime is unavailable: ${summary.error}`);
  }
  const issues = [];
  if (summary.packageName !== PACKAGE_NAME) {
    issues.push(`package name is ${summary.packageName}`);
  }
  if (!summary.versionMatches) {
    issues.push(
      `version ${summary.packageVersion} does not match ${summary.expectedPackageVersion}`,
    );
  }
  if (!summary.commitMatches) {
    issues.push(
      `commit ${summary.gitCommit} does not match ${summary.expectedGitCommit}`,
    );
  }
  if (!summary.runtimeMatches) {
    issues.push(
      `runtime digest ${summary.treeDigest} does not match ${summary.expectedTreeDigest}`,
    );
  }
  if (summary.worktreeDirty) issues.push('worktree is dirty');
  if (issues.length > 0 && !allowDirty) {
    throw provenanceError(
      `civ-engine provenance rejected (${issues.join('; ')}); `
      + 'use --allow-dirty only for attributed canary/development evidence',
    );
  }
  return state;
}

export function assertCivEngineStateSummary(summary) {
  const stableKeys = [
    'algorithm',
    'available',
    'commitMatches',
    'error',
    'expectedGitCommit',
    'expectedPackageVersion',
    'expectedTreeDigest',
    'fileCount',
    'gitCommit',
    'packageName',
    'packageVersion',
    'resolvedPackageRoot',
    'runtimeEntry',
    'runtimeMatches',
    'schemaVersion',
    'statusDigest',
    'treeDigest',
    'versionMatches',
    'worktreeDirty',
  ];
  if (
    !summary
    || typeof summary !== 'object'
    || Array.isArray(summary)
    || Object.keys(summary).sort().join('\0') !== stableKeys.sort().join('\0')
    || summary.schemaVersion !== SCHEMA_VERSION
    || summary.algorithm !== HASH_ALGORITHM
    || typeof summary.available !== 'boolean'
    || typeof summary.resolvedPackageRoot !== 'string'
    || summary.resolvedPackageRoot.length === 0
    || typeof summary.expectedPackageVersion !== 'string'
    || typeof summary.expectedGitCommit !== 'string'
    || typeof summary.versionMatches !== 'boolean'
    || typeof summary.commitMatches !== 'boolean'
    || typeof summary.runtimeMatches !== 'boolean'
    || !SHA256_PATTERN.test(summary.expectedTreeDigest)
    || !Number.isSafeInteger(summary.fileCount)
    || summary.fileCount < 0
  ) {
    throw new TypeError('invalid civ-engine provenance summary');
  }
  if (summary.available) {
    if (
      summary.packageName !== PACKAGE_NAME
      || typeof summary.packageVersion !== 'string'
      || typeof summary.runtimeEntry !== 'string'
      || !/^[0-9a-f]{40,64}$/.test(summary.gitCommit)
      || typeof summary.worktreeDirty !== 'boolean'
      || !SHA256_PATTERN.test(summary.statusDigest)
      || !SHA256_PATTERN.test(summary.treeDigest)
      || summary.fileCount <= 0
      || summary.error !== null
    ) {
      throw new TypeError('invalid available civ-engine provenance summary');
    }
  } else if (
    summary.packageName !== null
    || summary.packageVersion !== null
    || summary.runtimeEntry !== null
    || summary.gitCommit !== null
    || summary.worktreeDirty !== null
    || summary.statusDigest !== null
    || summary.treeDigest !== null
    || summary.fileCount !== 0
    || typeof summary.error !== 'string'
    || summary.error.length === 0
  ) {
    throw new TypeError('invalid unavailable civ-engine provenance summary');
  }
  return summary;
}

async function inventoryRuntimeFiles(packageRoot) {
  const relativePaths = ['package.json'];
  await walkDist(packageRoot, 'dist', relativePaths);
  relativePaths.sort(compareText);
  return Promise.all(relativePaths.map(async (relativePath) => {
    const rawContents = await fs.readFile(
      path.join(packageRoot, ...relativePath.split('/')),
    );
    const contents = canonicalRuntimeContents(relativePath, rawContents);
    return {
      path: relativePath,
      bytes: contents.byteLength,
      sha256: sha256(contents),
    };
  }));
}

function canonicalRuntimeContents(relativePath, contents) {
  if (!TEXT_RUNTIME_EXTENSIONS.has(path.extname(relativePath).toLowerCase())) {
    return contents;
  }
  return Buffer.from(contents.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
}

async function walkDist(packageRoot, relativeDirectory, results) {
  const entries = await fs.readdir(path.join(packageRoot, relativeDirectory), {
    withFileTypes: true,
  });
  entries.sort((left, right) => compareText(left.name, right.name));
  for (const entry of entries) {
    const relativePath = normalizePath(path.join(relativeDirectory, entry.name));
    if (entry.isDirectory()) {
      await walkDist(packageRoot, relativePath, results);
    } else if (entry.isFile()) {
      results.push(relativePath);
    } else {
      throw new Error(`unsupported civ-engine dist entry: ${relativePath}`);
    }
  }
}

function resolveRuntimeEntry(packageDocument) {
  const rootExport = packageDocument.exports?.['.'];
  let candidate = typeof rootExport === 'string' ? rootExport : rootExport?.import;
  if (candidate && typeof candidate === 'object') candidate = candidate.default;
  candidate ??= packageDocument.main;
  if (typeof candidate !== 'string' || !candidate.startsWith('./dist/')) {
    throw new Error('civ-engine package must expose an imported dist runtime');
  }
  const normalized = path.posix.normalize(candidate.slice(2));
  if (normalized.startsWith('../') || path.posix.isAbsolute(normalized)) {
    throw new Error('civ-engine runtime entry escapes its package root');
  }
  return normalized;
}

function gitStatus(packageRoot) {
  return parsePorcelainStatus(runGit(packageRoot, [
    'status',
    '--porcelain=v1',
    '-z',
    '--untracked-files=all',
  ])).sort((left, right) => compareText(
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
      throw new Error(`unexpected civ-engine git status: ${JSON.stringify(record)}`);
    }
    const code = record.slice(0, 2);
    const entry = { code, path: normalizePath(record.slice(3)) };
    if (/[RC]/.test(code)) {
      const originalPath = records[index + 1];
      if (!originalPath) throw new Error('civ-engine rename omitted original path');
      entry.originalPath = normalizePath(originalPath);
      index += 1;
    }
    status.push(entry);
  }
  return status;
}

function runGit(packageRoot, args) {
  const safeRoot = normalizePath(path.resolve(packageRoot));
  const result = spawnSync('git', ['-c', `safe.directory=${safeRoot}`, ...args], {
    cwd: packageRoot,
    encoding: 'utf8',
    shell: false,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(
      `civ-engine git ${args[0]} failed with exit ${result.status}: `
      + `${(result.stderr || result.stdout).trim()}`,
    );
  }
  return result.stdout;
}

function provenanceError(message) {
  const error = new Error(message);
  error.code = 'ERR_CIV_ENGINE_PROVENANCE';
  return error;
}

function normalizePath(candidate) {
  return candidate.split(path.sep).join('/');
}

function portablePackageRoot(repoRoot, packageRoot) {
  const relative = path.relative(repoRoot, packageRoot);
  if (!relative || path.isAbsolute(relative)) {
    if (!relative) return '.';
    throw new Error('resolved civ-engine package root is not portable from repo root');
  }
  return normalizePath(relative);
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
