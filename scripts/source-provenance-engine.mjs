import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';

import {
  CIV_ENGINE_PIN,
  EXPECTED_CIV_ENGINE_COMMIT,
  EXPECTED_CIV_ENGINE_TREE_DIGEST,
  EXPECTED_CIV_ENGINE_VERSION,
  resolveCivEnginePinRoot,
} from './civ-engine-pin.mjs';
import {
  assertPhysicalDirectory,
  inspectExpectedPackageRoot,
  inventoryRuntimeFiles,
  isStrictlyInside,
  normalizePath,
  resolveFromRepoRoot,
  resolveInstalledCivEngine,
  resolveRuntimeEntry,
  samePath,
} from './civ-engine-runtime.mjs';

export {
  EXPECTED_CIV_ENGINE_COMMIT,
  EXPECTED_CIV_ENGINE_TREE_DIGEST,
  EXPECTED_CIV_ENGINE_VERSION,
} from './civ-engine-pin.mjs';

const SCHEMA_VERSION = 1;
const HASH_ALGORITHM = 'sha256';
const PACKAGE_NAME = CIV_ENGINE_PIN.packageName;
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const FRESH_CAPTURE_SNAPSHOTS = new WeakMap();
const SUMMARY_KEYS = [
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

export async function captureCivEngineState({
  repoRoot,
  enginePackageRoot,
  expectedEnginePackageRoot,
  expectedEngineCommit = EXPECTED_CIV_ENGINE_COMMIT,
  expectedEngineVersion = EXPECTED_CIV_ENGINE_VERSION,
  expectedEngineTreeDigest = EXPECTED_CIV_ENGINE_TREE_DIGEST,
}) {
  if (typeof repoRoot !== 'string' || !path.isAbsolute(repoRoot)) {
    throw new TypeError('repoRoot must be an absolute path');
  }
  const resolvedRepoRoot = path.resolve(repoRoot);
  const explicitPackageRoot = enginePackageRoot === undefined
    ? null
    : resolveFromRepoRoot(resolvedRepoRoot, enginePackageRoot, 'enginePackageRoot');
  const usesConfiguredPinRoot = expectedEnginePackageRoot === undefined;
  const expectedPackageRoot = usesConfiguredPinRoot
    ? resolveCivEnginePinRoot(resolvedRepoRoot)
    : resolveFromRepoRoot(
      resolvedRepoRoot,
      expectedEnginePackageRoot,
      'expectedEnginePackageRoot',
    );
  const expectedRootIdentity = await inspectExpectedPackageRoot({
    repoRoot: resolvedRepoRoot,
    expectedPackageRoot,
    requireContained: usesConfiguredPinRoot,
  });
  const resolvedExpectedPackageRoot = expectedRootIdentity.resolved;
  const localExpectedPackageRoot = normalizePath(expectedPackageRoot);
  const localResolvedExpectedPackageRoot = normalizePath(
    resolvedExpectedPackageRoot,
  );
  const expectedPackageRootPhysical = expectedRootIdentity.physical;
  const requestedRoot = explicitPackageRoot ?? expectedPackageRoot;
  try {
    const resolution = explicitPackageRoot
      ? { packageRoot: explicitPackageRoot, runtimePath: null }
      : resolveInstalledCivEngine(PACKAGE_NAME);
    const resolvedPackageRoot = await fs.realpath(resolution.packageRoot);
    const packageDocumentPath = path.join(resolvedPackageRoot, 'package.json');
    const packageDocumentStat = await fs.lstat(packageDocumentPath);
    const resolvedPackageDocument = await fs.realpath(packageDocumentPath);
    if (
      !packageDocumentStat.isFile()
      || packageDocumentStat.isSymbolicLink()
      || !samePath(packageDocumentPath, resolvedPackageDocument)
    ) {
      throw new Error('civ-engine package metadata must be a physical file');
    }
    if (!samePath(path.dirname(resolvedPackageDocument), resolvedPackageRoot)) {
      throw new Error('resolved civ-engine package metadata escapes its package root');
    }
    const packageDocument = JSON.parse(await fs.readFile(
      path.join(resolvedPackageRoot, 'package.json'),
      'utf8',
    ));
    await assertPhysicalDirectory(resolvedPackageRoot, 'dist');
    const runtimeEntry = resolveRuntimeEntry(packageDocument);
    const declaredRuntimePath = path.join(
      resolvedPackageRoot,
      ...runtimeEntry.split('/'),
    );
    const declaredRuntimeStat = await fs.lstat(declaredRuntimePath);
    const declaredRuntimeEntry = await fs.realpath(declaredRuntimePath);
    if (
      !declaredRuntimeStat.isFile()
      || declaredRuntimeStat.isSymbolicLink()
      || !samePath(declaredRuntimePath, declaredRuntimeEntry)
      || !isStrictlyInside(resolvedPackageRoot, declaredRuntimeEntry)
    ) {
      throw new Error('declared civ-engine runtime must be a physical file below its package root');
    }
    const resolvedRuntimeEntry = resolution.runtimePath
      ? await fs.realpath(resolution.runtimePath)
      : declaredRuntimeEntry;
    if (!isStrictlyInside(resolvedPackageRoot, resolvedRuntimeEntry)) {
      throw new Error('resolved civ-engine runtime entry escapes its package root');
    }
    const runtimeEntryMatches = samePath(resolvedRuntimeEntry, declaredRuntimeEntry);
    const locationMatches = expectedPackageRootPhysical && samePath(
      resolvedPackageRoot,
      resolvedExpectedPackageRoot,
    );
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
    return registerFreshCapture({
      ...summary,
      localResolvedPackageRoot: normalizePath(resolvedPackageRoot),
      localExpectedPackageRoot,
      localResolvedExpectedPackageRoot,
      expectedPackageRootPhysical,
      locationMatches,
      localDeclaredRuntimeEntry: normalizePath(declaredRuntimeEntry),
      localResolvedRuntimeEntry: normalizePath(resolvedRuntimeEntry),
      runtimeEntryMatches,
      status,
      files,
      summary: structuredClone(summary),
    });
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
    return registerFreshCapture({
      ...summary,
      localResolvedPackageRoot: normalizePath(requestedRoot),
      localExpectedPackageRoot,
      localResolvedExpectedPackageRoot,
      expectedPackageRootPhysical,
      locationMatches: false,
      localDeclaredRuntimeEntry: null,
      localResolvedRuntimeEntry: null,
      runtimeEntryMatches: false,
      status: [],
      files: [],
      summary: structuredClone(summary),
    });
  }
}

export function civEngineStateSummary(state) {
  const summary = state?.summary ?? state;
  assertCivEngineStateSummary(summary);
  return structuredClone(summary);
}

export function assertCivEngineStateAllowed(state, { allowDirty = false } = {}) {
  const summary = civEngineStateSummary(state);
  assertFreshCivEngineIdentity(state, summary);
  if (!summary.available) {
    throw provenanceError(`civ-engine runtime is unavailable: ${summary.error}`);
  }
  const physicalRootMismatch = !state.expectedPackageRootPhysical;
  const locationMismatch = !state.locationMatches;
  const runtimeEntryMismatch = !state.runtimeEntryMatches;
  const issues = [];
  if (physicalRootMismatch) {
    issues.push(
      `pinned root ${state.localExpectedPackageRoot} is not a physical in-repository directory `
      + `(resolves to ${state.localResolvedExpectedPackageRoot})`,
    );
  }
  if (
    locationMismatch
    && !samePath(state.localResolvedPackageRoot, state.localResolvedExpectedPackageRoot)
  ) {
    issues.push(
      `resolved package root ${state.localResolvedPackageRoot} does not match pinned root `
      + `${state.localExpectedPackageRoot}`,
    );
  }
  if (runtimeEntryMismatch) {
    issues.push(
      `resolved runtime entry ${state.localResolvedRuntimeEntry} does not match declared entry `
      + `${state.localDeclaredRuntimeEntry}`,
    );
  }
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
  const identityMismatch = (
    physicalRootMismatch
    || locationMismatch
    || runtimeEntryMismatch
  );
  if (issues.length > 0 && (!allowDirty || identityMismatch)) {
    throw provenanceError(
      `civ-engine provenance rejected (${issues.join('; ')}); `
      + (identityMismatch
        ? 'resolved package location and runtime identity cannot be overridden'
        : 'use --allow-dirty only for attributed canary/development evidence'),
    );
  }
  return state;
}

export function assertCivEngineStateSummary(summary) {
  if (
    !summary
    || typeof summary !== 'object'
    || Array.isArray(summary)
    || Object.keys(summary).sort().join('\0') !== SUMMARY_KEYS.join('\0')
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
      || summary.versionMatches
        !== (summary.packageVersion === summary.expectedPackageVersion)
      || summary.commitMatches !== (summary.gitCommit === summary.expectedGitCommit)
      || summary.runtimeMatches !== (summary.treeDigest === summary.expectedTreeDigest)
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
    || summary.versionMatches !== false
    || summary.commitMatches !== false
    || summary.runtimeMatches !== false
    || summary.fileCount !== 0
    || typeof summary.error !== 'string'
    || summary.error.length === 0
  ) {
    throw new TypeError('invalid unavailable civ-engine provenance summary');
  }
  return summary;
}

function assertFreshCivEngineIdentity(state, summary) {
  const capturedSnapshot = state && typeof state === 'object'
    ? FRESH_CAPTURE_SNAPSHOTS.get(state)
    : undefined;
  if (
    !state
    || typeof state !== 'object'
    || Array.isArray(state)
    || !capturedSnapshot
    || !isDeepStrictEqual(capturedSnapshot, state)
    || !Object.hasOwn(state, 'summary')
    || !isDeepStrictEqual(
      summary,
      Object.fromEntries(SUMMARY_KEYS.map((key) => [key, state[key]])),
    )
    || typeof state.localResolvedPackageRoot !== 'string'
    || typeof state.localExpectedPackageRoot !== 'string'
    || typeof state.localResolvedExpectedPackageRoot !== 'string'
    || typeof state.expectedPackageRootPhysical !== 'boolean'
    || typeof state.locationMatches !== 'boolean'
    || typeof state.runtimeEntryMatches !== 'boolean'
    || !Array.isArray(state.status)
    || !Array.isArray(state.files)
    || (summary.available && (
      typeof state.localDeclaredRuntimeEntry !== 'string'
      || typeof state.localResolvedRuntimeEntry !== 'string'
    ))
    || (!summary.available && (
      state.localDeclaredRuntimeEntry !== null
      || state.localResolvedRuntimeEntry !== null
    ))
  ) {
    throw new TypeError(
      'a fresh civ-engine capture with resolved identity is required',
    );
  }
}

function registerFreshCapture(state) {
  FRESH_CAPTURE_SNAPSHOTS.set(state, structuredClone(state));
  return state;
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
