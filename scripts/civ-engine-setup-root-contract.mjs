import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

import {
  CIV_ENGINE_PACKAGE_SPEC,
  CIV_ENGINE_PIN,
} from './civ-engine-pin.mjs';

const PACKAGE_KEYS = new Set([
  'dependencies',
  'engines',
  'name',
  'private',
  'scripts',
  'type',
  'version',
]);
const LOCK_KEYS = new Set([
  'lockfileVersion',
  'name',
  'packages',
  'requires',
  'version',
]);
const ROOT_LOCK_KEYS = new Set(['dependencies', 'engines', 'name', 'version']);
const PIN_LOCK_KEYS = new Set([
  'devDependencies',
  'engines',
  'license',
  'name',
  'version',
]);
const LINK_LOCK_KEYS = new Set(['link', 'resolved']);

export async function validateRootInstallContract({ repoRoot, pin = CIV_ENGINE_PIN }) {
  const root = path.resolve(repoRoot);
  await assertPhysicalDirectory(root, 'repository root');
  const [packageDocument, lockDocument, npmrc] = await Promise.all([
    readPhysicalJson(path.join(root, 'package.json'), 'package.json'),
    readPhysicalJson(path.join(root, 'package-lock.json'), 'package-lock.json'),
    readPhysicalText(path.join(root, '.npmrc'), '.npmrc'),
  ]);
  validatePackageDocument(packageDocument, pin);
  if (digestParsedRootLock(lockDocument) !== pin.rootLockSha256) {
    throw contractError('root lock canonical digest does not match the descriptor');
  }
  validateLockDocument(lockDocument, packageDocument, pin);
  if (npmrc !== 'install-links=false\nloglevel=silent\n') {
    throw contractError('root npm configuration is not the exact install contract');
  }
  return { packageDocument, lockDocument };
}

export function digestParsedRootLock(document) {
  return createHash('sha256')
    .update(canonicalJson(document), 'utf8')
    .digest('hex');
}

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
    .join(',')}}`;
}

function validatePackageDocument(document, pin) {
  assertRecord(document, 'package document');
  assertOnlyKeys(document, PACKAGE_KEYS, 'package document');
  if (
    document.private !== true
    || document.type !== 'module'
    || typeof document.name !== 'string'
    || document.name.length === 0
  ) {
    throw contractError('package identity is outside the root install contract');
  }
  assertExactPinDependency(document.dependencies, pin, 'package dependencies');
  if (document.scripts !== undefined) {
    assertRecord(document.scripts, 'package scripts');
    for (const key of Object.keys(document.scripts)) {
      if (isInstallLifecycle(key) || typeof document.scripts[key] !== 'string') {
        throw contractError('package scripts contain an install lifecycle');
      }
    }
  }
}

function validateLockDocument(document, packageDocument, pin) {
  assertRecord(document, 'lock document');
  assertOnlyKeys(document, LOCK_KEYS, 'lock document');
  if (
    document.lockfileVersion !== 3
    || document.requires !== true
    || document.name !== packageDocument.name
  ) {
    throw contractError('lock metadata is outside the root install contract');
  }
  if (
    packageDocument.version !== undefined
    && document.version !== packageDocument.version
  ) {
    throw contractError('lock version does not match package.json');
  }
  assertRecord(document.packages, 'lock package graph');

  const rootLock = document.packages[''];
  const pinLock = document.packages[pin.installPath];
  const installedLock = document.packages[`node_modules/${pin.packageName}`];
  assertRecord(rootLock, 'root lock entry');
  assertRecord(pinLock, 'pinned package lock entry');
  assertRecord(installedLock, 'installed link lock entry');
  assertOnlyKeys(rootLock, ROOT_LOCK_KEYS, 'root lock entry');
  assertOnlyKeys(pinLock, PIN_LOCK_KEYS, 'pinned package lock entry');
  assertOnlyKeys(installedLock, LINK_LOCK_KEYS, 'installed link lock entry');
  assertExactPinDependency(rootLock.dependencies, pin, 'root lock dependencies');
  if (
    (rootLock.name !== undefined && rootLock.name !== packageDocument.name)
    || (rootLock.version !== undefined && rootLock.version !== packageDocument.version)
    || pinLock.name !== pin.packageName
    || pinLock.version !== pin.version
    || installedLock.resolved !== pin.installPath
    || installedLock.link !== true
  ) {
    throw contractError('pinned lock entries do not match the descriptor');
  }

  for (const [packagePath, entry] of Object.entries(document.packages)) {
    if (['', pin.installPath, `node_modules/${pin.packageName}`].includes(packagePath)) {
      continue;
    }
    if (!isNodeModulesPath(packagePath)) {
      throw contractError('lock graph contains an unexpected local package');
    }
    assertRecord(entry, 'lock graph entry');
    if (entry.dev !== true || entry.link === true || entry.inBundle === true) {
      throw contractError('lock graph contains an unexpected non-dev package');
    }
  }
}

function assertExactPinDependency(dependencies, pin, label) {
  assertRecord(dependencies, label);
  const keys = Object.keys(dependencies);
  if (
    keys.length !== 1
    || keys[0] !== pin.packageName
    || dependencies[pin.packageName] !== CIV_ENGINE_PACKAGE_SPEC
  ) {
    throw contractError(`${label} do not match the descriptor`);
  }
}

function assertOnlyKeys(record, allowed, label) {
  if (Object.keys(record).some((key) => !allowed.has(key))) {
    throw contractError(`${label} contains an unsupported install field`);
  }
}

function assertRecord(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw contractError(`${label} must be an object`);
  }
}

function isInstallLifecycle(key) {
  return /^(?:pre|post)?(?:install|prepare|publish|pack|shrinkwrap|dependencies)$/i.test(key);
}

function isNodeModulesPath(candidate) {
  if (!candidate.startsWith('node_modules/') || candidate.includes('\\')) return false;
  const normalized = path.posix.normalize(candidate);
  return normalized === candidate && !candidate.split('/').includes('..');
}

async function readPhysicalJson(candidate, label) {
  try {
    return JSON.parse(await readPhysicalText(candidate, label));
  } catch (error) {
    if (error?.code?.startsWith('ERR_CIV_ENGINE_')) throw error;
    throw contractError(`${label} is not valid JSON`);
  }
}

async function readPhysicalText(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([fs.lstat(resolved), fs.realpath(resolved)]);
  } catch {
    throw contractError(`${label} is unavailable`);
  }
  if (!metadata.isFile() || metadata.isSymbolicLink() || !samePath(resolved, physical)) {
    throw contractError(`${label} must be a physical file`);
  }
  return fs.readFile(resolved, 'utf8');
}

async function assertPhysicalDirectory(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([fs.lstat(resolved), fs.realpath(resolved)]);
  } catch {
    throw contractError(`${label} is unavailable`);
  }
  if (!metadata.isDirectory() || metadata.isSymbolicLink() || !samePath(resolved, physical)) {
    throw contractError(`${label} must be a physical directory`);
  }
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function contractError(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_CONTRACT' });
}
