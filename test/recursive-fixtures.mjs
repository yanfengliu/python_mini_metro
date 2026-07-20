import {
  EXPECTED_CIV_ENGINE_COMMIT,
  EXPECTED_CIV_ENGINE_TREE_DIGEST,
  EXPECTED_CIV_ENGINE_VERSION,
} from '../scripts/source-provenance-engine.mjs';

export function sourceStateFixture(overrides = {}) {
  return {
    schemaVersion: 1,
    algorithm: 'sha256',
    treeDigest: 'a'.repeat(64),
    fileCount: 1,
    gitCommit: '11161a54e402c33dd5d08c67d355dc02a5900a0a',
    worktreeDirty: false,
    statusDigest: 'b'.repeat(64),
    diffAvailable: false,
    engine: {
      schemaVersion: 1,
      available: true,
      packageName: 'civ-engine',
      resolvedPackageRoot: '.civ-engine-pin',
      packageVersion: EXPECTED_CIV_ENGINE_VERSION,
      expectedPackageVersion: EXPECTED_CIV_ENGINE_VERSION,
      versionMatches: true,
      runtimeEntry: 'dist/index.js',
      gitCommit: EXPECTED_CIV_ENGINE_COMMIT,
      expectedGitCommit: EXPECTED_CIV_ENGINE_COMMIT,
      commitMatches: true,
      worktreeDirty: false,
      statusDigest: 'c'.repeat(64),
      algorithm: 'sha256',
      treeDigest: EXPECTED_CIV_ENGINE_TREE_DIGEST,
      expectedTreeDigest: EXPECTED_CIV_ENGINE_TREE_DIGEST,
      runtimeMatches: true,
      fileCount: 365,
      error: null,
    },
    ...overrides,
  };
}
