import fs from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';

import {
  assertImprovementFinding,
  assertImprovementRunManifest,
  createImprovementRunManifest,
} from 'civ-engine';

import { createRecursiveLedger } from './recursive-ledger.mjs';
import { assertCivEngineStateSummary } from './source-provenance-engine.mjs';

const GAME_ID = 'python_mini_metro';
const SOURCE_STATE_TAG = 'source-state-v1';
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const PASS_OUTCOMES = new Set([
  'no-fix-candidate',
  'proposal-only',
  'run-failed',
]);
const RUN_OUTCOMES = new Set(['verified', 'run-failed']);
const FIX_ACTIONS = new Set(['autoFix', 'manualFix', 'improveHarness']);
const CLOSED_DISPOSITIONS = new Set(['rejected', 'wontFix']);
const SEVERITY_RANK = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

export function selectFixCandidate(findings) {
  const candidates = (findings ?? []).filter(isSelectableFinding);
  candidates.sort((left, right) => (
    (SEVERITY_RANK[right.severity] ?? 0)
    - (SEVERITY_RANK[left.severity] ?? 0)
  ));
  return candidates[0] ?? null;
}

function isSelectableFinding(finding) {
  if (
    !finding
    || finding.verificationStatus !== 'verified'
    || !FIX_ACTIONS.has(finding.nextAction)
    || CLOSED_DISPOSITIONS.has(finding.disposition ?? 'candidate')
    || !findingClassOf(finding)
  ) {
    return false;
  }
  try {
    assertImprovementFinding(finding, { requireVerificationEvidence: true });
    return true;
  } catch {
    return false;
  }
}

export function buildPassManifest(input) {
  if (!PASS_OUTCOMES.has(input.stopReason)) {
    throw new Error(`unsupported recursive pass outcome: ${input.stopReason}`);
  }
  return buildCompleteManifest(input, 'recursive-pass');
}

export function buildRunManifest(input) {
  if (!RUN_OUTCOMES.has(input.stopReason)) {
    throw new Error(`unsupported recursive run outcome: ${input.stopReason}`);
  }
  return buildCompleteManifest(input, 'recursive-run');
}

function buildCompleteManifest(input, tag) {
  if (!input.sourceState) {
    throw new Error('new recursive manifests require source state');
  }
  const manifest = createImprovementRunManifest({
    id: input.id,
    gameId: GAME_ID,
    objective: input.objective,
    startedAt: input.startedAt,
    completedAt: input.completedAt,
    durationMs: input.durationMs,
    seed: input.seed,
    gitCommit: input.gitCommit,
    provider: 'scripted',
    costUsd: 0,
    stopReason: input.stopReason,
    artifacts: [...input.artifacts],
    gates: input.gates.map((gate) => ({ ...gate })),
    tags: [GAME_ID, tag, SOURCE_STATE_TAG],
    data: {
      ...input.data,
      outcome: input.stopReason,
      sourceState: structuredClone(input.sourceState),
    },
  });
  assertCompleteManifest(manifest);
  return manifest;
}

export function assertCompleteManifest(manifest) {
  assertImprovementRunManifest(manifest);
  for (const key of [
    'id',
    'gameId',
    'objective',
    'startedAt',
    'completedAt',
    'gitCommit',
    'engineVersion',
    'provider',
    'stopReason',
  ]) {
    if (typeof manifest[key] !== 'string' || manifest[key].trim().length === 0) {
      throw new Error(`complete manifest requires ${key}`);
    }
  }
  if (manifest.gameId !== GAME_ID) {
    throw new Error(`manifest gameId must be ${GAME_ID}`);
  }
  if (manifest.engineVersion !== '2.2.0') {
    throw new Error('manifest engineVersion must be the pinned civ-engine 2.2.0');
  }
  const isPass = manifest.tags?.includes('recursive-pass') === true;
  const isRun = manifest.tags?.includes('recursive-run') === true;
  if (isPass === isRun) {
    throw new Error('complete manifest requires exactly one run/pass tag');
  }
  const outcomes = isPass ? PASS_OUTCOMES : RUN_OUTCOMES;
  if (!outcomes.has(manifest.stopReason)) {
    throw new Error(`unsupported ${isPass ? 'pass' : 'run'} outcome: ${manifest.stopReason}`);
  }
  const numericSeed = Number.isSafeInteger(manifest.seed)
    && manifest.seed >= 0
    && manifest.seed <= 0xffff_ffff;
  const unavailableSeed = manifest.seed === 'unavailable'
    && manifest.stopReason === 'run-failed';
  if (!numericSeed && !unavailableSeed) {
    throw new Error('complete manifest requires a uint32 seed or run-failed unavailable sentinel');
  }
  if (manifest.costUsd !== 0) {
    throw new Error('scripted recursive manifests require costUsd 0');
  }
  if (!Number.isFinite(manifest.durationMs) || manifest.durationMs < 0) {
    throw new Error('complete manifest requires a non-negative durationMs');
  }
  const started = Date.parse(manifest.startedAt);
  const completed = Date.parse(manifest.completedAt);
  if (!Number.isFinite(started) || !Number.isFinite(completed) || completed < started) {
    throw new Error('complete manifest requires ordered ISO timestamps');
  }
  if (!Array.isArray(manifest.artifacts)) {
    throw new Error('complete manifest requires artifacts');
  }
  for (const artifact of manifest.artifacts) {
    if (
      typeof artifact.kind !== 'string'
      || artifact.kind.trim().length === 0
      || artifact.kind !== artifact.kind.trim()
      || typeof artifact.path !== 'string'
      || artifact.path.trim().length === 0
      || artifact.path !== artifact.path.trim()
      || path.isAbsolute(artifact.path)
      || artifact.path.startsWith('/')
      || artifact.path.includes('\\')
      || artifact.path.split('/').includes('..')
      || path.posix.normalize(artifact.path) !== artifact.path
    ) {
      throw new Error(`manifest artifact must be nonempty, portable, and relative: ${artifact.path}`);
    }
  }
  if (!Array.isArray(manifest.gates) || manifest.gates.length === 0) {
    throw new Error('complete manifest requires at least one gate');
  }
  if (!Array.isArray(manifest.tags) || manifest.tags.length === 0) {
    throw new Error('complete manifest requires tags');
  }
  if (
    !manifest.data
    || typeof manifest.data !== 'object'
    || Array.isArray(manifest.data)
    || manifest.data.outcome !== manifest.stopReason
  ) {
    throw new Error('complete manifest data.outcome must equal stopReason');
  }
  const hasSourceStateTag = manifest.tags.includes(SOURCE_STATE_TAG);
  if (hasSourceStateTag) {
    assertSourceStateSummary(manifest.data.sourceState, manifest.gitCommit);
  } else if (manifest.data.sourceState !== undefined) {
    throw new Error('legacy manifest source state requires its version tag');
  }
}

function assertSourceStateSummary(sourceState, gitCommit) {
  if (!sourceState || typeof sourceState !== 'object' || Array.isArray(sourceState)) {
    throw new Error('complete manifest requires source state');
  }
  const allowedKeys = new Set([
    'schemaVersion',
    'algorithm',
    'treeDigest',
    'fileCount',
    'gitCommit',
    'worktreeDirty',
    'statusDigest',
    'diffAvailable',
    'diffDigest',
    'engine',
  ]);
  if (Object.keys(sourceState).some((key) => !allowedKeys.has(key))) {
    throw new Error('complete manifest source state contains unknown fields');
  }
  if (
    sourceState.schemaVersion !== 1
    || sourceState.algorithm !== 'sha256'
    || !SHA256_PATTERN.test(sourceState.treeDigest)
    || !Number.isSafeInteger(sourceState.fileCount)
    || sourceState.fileCount <= 0
    || sourceState.gitCommit !== gitCommit
    || typeof sourceState.worktreeDirty !== 'boolean'
    || !SHA256_PATTERN.test(sourceState.statusDigest)
    || typeof sourceState.diffAvailable !== 'boolean'
  ) {
    throw new Error('complete manifest source state is invalid');
  }
  if (
    sourceState.diffAvailable
      ? (!sourceState.worktreeDirty || !SHA256_PATTERN.test(sourceState.diffDigest))
      : sourceState.diffDigest !== undefined
  ) {
    throw new Error('complete manifest source state diff metadata is invalid');
  }
  assertCivEngineStateSummary(sourceState.engine);
}

export async function writeValidatedManifest(
  filePath,
  manifest,
  { repoRoot = process.cwd() } = {},
) {
  assertCompleteManifest(manifest);
  await assertArtifactFilesExist(manifest, repoRoot);
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  const persisted = JSON.parse(await fs.readFile(filePath, 'utf8'));
  assertCompleteManifest(persisted);
  await assertArtifactFilesExist(persisted, repoRoot);
  if (!isDeepStrictEqual(persisted, manifest)) {
    throw new Error(`manifest read-back changed content: ${filePath}`);
  }
  return persisted;
}

async function assertArtifactFilesExist(
  manifest,
  repoRoot,
  { allowMissingPaths = [] } = {},
) {
  const allowedMissing = new Set(allowMissingPaths);
  for (const artifact of manifest.artifacts) {
    const absolute = path.resolve(repoRoot, artifact.path);
    const relative = path.relative(path.resolve(repoRoot), absolute);
    if (relative === '..' || relative.startsWith(`..${path.sep}`)) {
      throw new Error(`artifact is outside repository: ${artifact.path}`);
    }
    let stat;
    try {
      stat = await fs.stat(absolute);
    } catch (error) {
      if (error?.code === 'ENOENT' && allowedMissing.has(artifact.path)) {
        continue;
      }
      if (error?.code === 'ENOENT') {
        throw new Error(`artifact does not exist: ${artifact.path}`);
      }
      throw error;
    }
    if (!stat.isFile()) throw new Error(`artifact is not a regular file: ${artifact.path}`);
  }
}

export function repoRelativePath(repoRoot, absolutePath) {
  const relative = path.relative(path.resolve(repoRoot), path.resolve(absolutePath));
  if (
    relative.length === 0
    || relative === '..'
    || relative.startsWith(`..${path.sep}`)
    || path.isAbsolute(relative)
  ) {
    throw new Error(`artifact is outside repository: ${absolutePath}`);
  }
  return relative.split(path.sep).join('/');
}

export function findingClassOf(finding) {
  const value = finding?.data?.class;
  return typeof value === 'string' && value.trim().length > 0
    ? value.trim()
    : null;
}

const recursiveLedger = createRecursiveLedger({
  assertCompleteManifest,
  assertArtifactFilesExist,
});

export const {
  appendManifestPair,
  appendValidatedManifestRow,
  createManifestPairIntent,
  persistManifestPair,
  reconcileManifestPairIntents,
} = recursiveLedger;
