import { readFileSync } from 'node:fs';
import path from 'node:path';

const PIN_KEYS = [
  'commit',
  'installPath',
  'packageName',
  'repositoryUrl',
  'runtimeTreeSha256',
  'schemaVersion',
  'version',
];
const CANONICAL_PACKAGE_NAME = 'civ-engine';
const CANONICAL_REPOSITORY_URL = 'https://github.com/yanfengliu/civ-engine.git';
const CANONICAL_INSTALL_PATH = '.civ-engine-pin';
const COMMIT_PATTERN = /^[0-9a-f]{40}$/;
const RUNTIME_DIGEST_PATTERN = /^[0-9a-f]{64}$/;
const SEMVER_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

export function validateCivEnginePin(candidate) {
  if (
    !candidate
    || typeof candidate !== 'object'
    || Array.isArray(candidate)
    || Object.keys(candidate).sort().join('\0') !== PIN_KEYS.join('\0')
    || candidate.schemaVersion !== 1
    || candidate.packageName !== CANONICAL_PACKAGE_NAME
    || candidate.repositoryUrl !== CANONICAL_REPOSITORY_URL
    || typeof candidate.version !== 'string'
    || !isSemanticVersion(candidate.version)
    || typeof candidate.commit !== 'string'
    || !COMMIT_PATTERN.test(candidate.commit)
    || typeof candidate.runtimeTreeSha256 !== 'string'
    || !RUNTIME_DIGEST_PATTERN.test(candidate.runtimeTreeSha256)
    || candidate.installPath !== CANONICAL_INSTALL_PATH
    || !isPortableInstallPath(candidate.installPath)
  ) {
    throw new TypeError('invalid civ-engine pin descriptor');
  }
  return Object.freeze({
    schemaVersion: candidate.schemaVersion,
    packageName: candidate.packageName,
    repositoryUrl: candidate.repositoryUrl,
    installPath: candidate.installPath,
    version: candidate.version,
    commit: candidate.commit,
    runtimeTreeSha256: candidate.runtimeTreeSha256,
  });
}

export function resolveCivEnginePinRoot(repoRoot, pin = CIV_ENGINE_PIN) {
  if (
    typeof repoRoot !== 'string'
    || repoRoot.length === 0
    || !path.isAbsolute(repoRoot)
  ) {
    throw new TypeError('repoRoot must be an absolute path');
  }
  const validated = validateCivEnginePin(pin);
  const resolvedRepoRoot = path.resolve(repoRoot);
  const resolvedPinRoot = path.resolve(
    resolvedRepoRoot,
    ...validated.installPath.split('/'),
  );
  const relative = path.relative(resolvedRepoRoot, resolvedPinRoot);
  if (
    !relative
    || path.isAbsolute(relative)
    || relative === '..'
    || relative.startsWith(`..${path.sep}`)
  ) {
    throw new TypeError('civ-engine pin root escapes repoRoot');
  }
  return resolvedPinRoot;
}

function isSemanticVersion(candidate) {
  const match = SEMVER_PATTERN.exec(candidate);
  if (!match) return false;
  const prerelease = match[4];
  if (!prerelease) return true;
  return prerelease.split('.').every((identifier) => (
    !/^\d+$/.test(identifier)
    || identifier === '0'
    || !identifier.startsWith('0')
  ));
}

function isPortableInstallPath(candidate) {
  if (
    typeof candidate !== 'string'
    || candidate.length === 0
    || candidate.includes('\\')
    || candidate.includes(':')
    || candidate.startsWith('/')
    || path.posix.isAbsolute(candidate)
    || path.posix.normalize(candidate) !== candidate
  ) {
    return false;
  }
  const segments = candidate.split('/');
  return segments.every((segment) => segment && segment !== '.' && segment !== '..');
}

const pinDocument = JSON.parse(
  readFileSync(new URL('./civ-engine-pin.json', import.meta.url), 'utf8'),
);

export const CIV_ENGINE_PIN = validateCivEnginePin(pinDocument);
export const CIV_ENGINE_PACKAGE_SPEC = `file:${CIV_ENGINE_PIN.installPath}`;
export const EXPECTED_CIV_ENGINE_COMMIT = CIV_ENGINE_PIN.commit;
export const EXPECTED_CIV_ENGINE_VERSION = CIV_ENGINE_PIN.version;
export const EXPECTED_CIV_ENGINE_TREE_DIGEST = CIV_ENGINE_PIN.runtimeTreeSha256;
