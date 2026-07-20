import { randomUUID } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

import { CIV_ENGINE_PIN } from './civ-engine-pin.mjs';
import { inspectLocalGitConfig } from './civ-engine-setup-git-config.mjs';
import { runReadOnlyGit } from './civ-engine-setup-process.mjs';

const LOCK_NAME = '.civ-engine-setup.lock';
const TRANSACTION_PREFIX = '.civ-engine-setup-';
const OWNER_MARKER = '.setup-owner';

export async function assertNoActiveSetupLock({ repoRoot }) {
  const lockPath = path.join(path.resolve(repoRoot), LOCK_NAME);
  if (await pathExists(lockPath)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_LOCKED', 'civ-engine setup is already active');
  }
}

export async function acquireSetupLock({ repoRoot, token = randomUUID() }) {
  const root = path.resolve(repoRoot);
  const lockPath = path.join(root, LOCK_NAME);
  const contents = ownerDocument(token);
  try {
    await fs.writeFile(lockPath, contents, { encoding: 'utf8', flag: 'wx' });
  } catch (error) {
    if (error?.code === 'EEXIST') {
      throw setupError('ERR_CIV_ENGINE_SETUP_LOCKED', 'civ-engine setup is already active');
    }
    throw error;
  }
  const metadata = await fs.lstat(lockPath, { bigint: true });
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    throw setupError('ERR_CIV_ENGINE_SETUP_OWNERSHIP', 'setup lock is not a physical file');
  }
  return {
    repoRoot: root,
    path: lockPath,
    token,
    identity: fileIdentity(metadata),
  };
}

export async function releaseSetupLock(lock) {
  await assertOwnedFile(lock.path, lock.token, lock.identity, 'setup lock');
  await fs.unlink(lock.path);
}

export async function assertSetupLockOwnership(lock) {
  await assertOwnedFile(lock.path, lock.token, lock.identity, 'setup lock');
  return lock;
}

export async function createSetupTransaction({ repoRoot, token = randomUUID() }) {
  const root = path.resolve(repoRoot);
  const parentPath = await fs.mkdtemp(path.join(root, TRANSACTION_PREFIX));
  const markerPath = path.join(parentPath, OWNER_MARKER);
  const homePath = path.join(parentPath, 'home');
  const tempPath = path.join(parentPath, 'temp');
  const templatePath = path.join(parentPath, 'empty-git-template');
  const npmUserConfigPath = path.join(homePath, 'npm-user.ini');
  const npmGlobalConfigPath = path.join(homePath, 'npm-global.ini');
  await Promise.all([
    fs.mkdir(homePath),
    fs.mkdir(tempPath),
    fs.mkdir(templatePath),
    fs.writeFile(markerPath, ownerDocument(token), { encoding: 'utf8', flag: 'wx' }),
  ]);
  await Promise.all([
    fs.writeFile(npmUserConfigPath, '', { encoding: 'utf8', flag: 'wx' }),
    fs.writeFile(npmGlobalConfigPath, '', { encoding: 'utf8', flag: 'wx' }),
  ]);
  const metadata = await fs.lstat(parentPath, { bigint: true });
  return {
    repoRoot: root,
    parentPath,
    markerPath,
    checkoutPath: path.join(parentPath, 'checkout'),
    homePath,
    tempPath,
    templatePath,
    npmUserConfigPath,
    npmGlobalConfigPath,
    token,
    identity: fileIdentity(metadata),
  };
}

export async function cleanupSetupTransaction(transaction) {
  const parentPath = path.resolve(transaction.parentPath);
  if (!isStrictlyInside(transaction.repoRoot, parentPath)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_OWNERSHIP', 'setup transaction escaped its repository');
  }
  const metadata = await physicalMetadata(parentPath, 'setup transaction');
  if (!metadata.isDirectory() || !sameIdentity(metadata, transaction.identity)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_OWNERSHIP', 'setup transaction identity changed');
  }
  await assertOwnedFile(
    transaction.markerPath,
    transaction.token,
    undefined,
    'setup transaction marker',
  );
  await assertContainedTree(parentPath, parentPath, 'setup transaction');
  await fs.rm(parentPath, { recursive: true, force: false });
}

export async function classifySetupState({
  repoRoot,
  pinRoot,
  expectedCommit = CIV_ENGINE_PIN.commit,
  expectedRepositoryUrl = CIV_ENGINE_PIN.repositoryUrl,
  allowDirty = false,
  runGit,
}) {
  const root = path.resolve(repoRoot);
  const candidate = path.resolve(pinRoot);
  if (!isStrictlyInside(root, candidate)) {
    throw unsafe('civ-engine destination escapes the repository');
  }
  let metadata;
  try {
    metadata = await fs.lstat(candidate);
  } catch (error) {
    if (error?.code === 'ENOENT') return { kind: 'missing' };
    throw error;
  }
  if (!metadata.isDirectory() || metadata.isSymbolicLink()) {
    throw unsafe('civ-engine destination must be a physical directory');
  }
  const physical = await fs.realpath(candidate);
  if (!samePath(candidate, physical)) {
    throw unsafe('civ-engine destination must not be a link or junction');
  }
  try {
    const audit = await auditCheckoutMetadata({
      checkoutRoot: candidate,
      expectedCommit,
      expectedRepositoryUrl,
      allowDirty,
      ...(runGit ? { runGit } : {}),
    });
    return { kind: 'exact', audit };
  } catch (error) {
    if (error?.code === 'ERR_CIV_ENGINE_SETUP_MISMATCH') {
      return { kind: 'suspicious', reason: error.message };
    }
    throw error;
  }
}

export function classifyRootDependencyRepair({
  repoRoot,
  expectedPinRoot,
  requestedPackagePath,
  resolvedPackageRoot,
}) {
  const root = path.resolve(repoRoot);
  const rootSlot = path.join(root, 'node_modules', CIV_ENGINE_PIN.packageName);
  if (!samePath(requestedPackagePath, rootSlot)) {
    throw setupError(
      'ERR_CIV_ENGINE_RESOLUTION_SHADOW',
      'civ-engine resolved through an unexpected dependency slot',
    );
  }
  return resolvedPackageRoot && samePath(resolvedPackageRoot, expectedPinRoot)
    ? { kind: 'exact' }
    : { kind: 'repairable' };
}

export async function auditCheckoutMetadata({
  checkoutRoot,
  expectedCommit,
  expectedRepositoryUrl,
  allowDirty = false,
  checkoutMode = 'detached',
  runGit = runReadOnlyGit,
}) {
  const {
    root,
    gitRoot,
    configuredOrigin,
    headIdentity,
  } = await auditCheckoutMetadataFilesystem({
    checkoutRoot,
    expectedCommit,
    expectedRepositoryUrl,
    allowDirty,
    checkoutMode,
  });
  const invoke = (args, allowedStatuses) => runGit({
    repoRoot: root,
    args,
    ...(allowedStatuses ? { allowedStatuses } : {}),
  });
  if (checkoutMode === 'pre-checkout') {
    const [topLevel, commonDirectory, commit] = await Promise.all([
      invoke(['rev-parse', '--show-toplevel']),
      invoke(['rev-parse', '--git-common-dir']),
      invoke(['rev-parse', `${expectedCommit}^{commit}`]),
    ]);
    if (!samePath(topLevel.trim(), root)) throw mismatch('Git top level was redirected');
    const resolvedCommon = path.resolve(root, commonDirectory.trim());
    if (!samePath(resolvedCommon, gitRoot)) throw mismatch('Git common directory was redirected');
    if (commit.trim() !== expectedCommit) {
      throw mismatch('civ-engine descriptor commit object is unavailable');
    }
    return { checkoutRoot: root, commit: expectedCommit, repositoryUrl: configuredOrigin };
  }
  const [topLevel, commonDirectory, commit, symbolicRef, status] = await Promise.all([
    invoke(['rev-parse', '--show-toplevel']),
    invoke(['rev-parse', '--git-common-dir']),
    invoke(['rev-parse', 'HEAD']),
    invoke(['symbolic-ref', '-q', 'HEAD'], [0, 1]),
    invoke(['status', '--porcelain=v1', '-z', '--untracked-files=all']),
  ]);
  if (!samePath(topLevel.trim(), root)) throw mismatch('Git top level was redirected');
  const resolvedCommon = path.resolve(root, commonDirectory.trim());
  if (!samePath(resolvedCommon, gitRoot)) throw mismatch('Git common directory was redirected');
  if (commit.trim() !== headIdentity) throw mismatch('Git commit identity changed');
  if (!allowDirty && commit.trim() !== expectedCommit) {
    throw mismatch('Git commit does not match the descriptor');
  }
  if (symbolicRef.trim()) throw mismatch('civ-engine checkout must be detached');
  if (!allowDirty && status.length !== 0) throw mismatch('civ-engine checkout is dirty');
  return { checkoutRoot: root, commit: expectedCommit, repositoryUrl: configuredOrigin };
}

export async function auditCheckoutMetadataFilesystem({
  checkoutRoot,
  expectedCommit,
  expectedRepositoryUrl,
  allowDirty = false,
  checkoutMode = 'detached',
}) {
  if (!['pre-checkout', 'detached'].includes(checkoutMode)) {
    throw setupError('ERR_CIV_ENGINE_SETUP_REFUSED', 'unsupported checkout audit mode');
  }
  const root = path.resolve(checkoutRoot);
  await assertPhysicalDirectory(root, 'checkout');
  const gitRoot = path.join(root, '.git');
  await assertPhysicalDirectory(gitRoot, 'Git metadata');
  await assertPhysicalTree(gitRoot, 'Git metadata');

  for (const [relativePath, label] of [
    ['objects/info/alternates', 'object alternate'],
    ['info/grafts', 'graft'],
    ['refs/replace', 'replace ref'],
    ['shallow', 'shallow metadata'],
    ['commondir', 'common-directory redirect'],
    ['gitdir', 'Git-directory redirect'],
    ['config.worktree', 'worktree configuration'],
  ]) {
    if (await pathExists(path.join(gitRoot, ...relativePath.split('/')))) {
      throw unsafe(`Git ${label} is not allowed`);
    }
  }

  const configPath = path.join(gitRoot, 'config');
  const headPath = path.join(gitRoot, 'HEAD');
  await Promise.all([
    assertPhysicalFile(configPath, 'Git config'),
    assertPhysicalFile(headPath, 'Git HEAD'),
  ]);
  const [config, head] = await Promise.all([
    fs.readFile(configPath, 'utf8'),
    fs.readFile(headPath, 'utf8'),
  ]);
  const configuredOrigin = inspectLocalGitConfig(config);
  if (configuredOrigin !== expectedRepositoryUrl) {
    throw mismatch('civ-engine remote origin does not match the descriptor');
  }
  const headIdentity = head.trim();
  if (checkoutMode === 'detached') {
    if (!/^[0-9a-f]{40,64}$/.test(headIdentity)) {
      throw mismatch('civ-engine checkout must have a detached HEAD');
    }
    if (!allowDirty && expectedCommit && headIdentity !== expectedCommit) {
      throw mismatch('civ-engine checkout is not at the detached descriptor commit');
    }
  } else if (
    !/^[0-9a-f]{40,64}$/.test(headIdentity)
    && !/^ref: refs\/heads\/[A-Za-z0-9._/-]+$/.test(headIdentity)
  ) {
    throw mismatch('civ-engine clone has an invalid pre-checkout HEAD');
  }
  if (checkoutMode === 'pre-checkout') {
    if (!/^[0-9a-f]{40,64}$/.test(expectedCommit ?? '')) {
      throw setupError('ERR_CIV_ENGINE_SETUP_REFUSED', 'pre-checkout audit requires an exact commit');
    }
    await assertSafePreCheckoutMetadata(gitRoot);
  }
  return { root, gitRoot, configuredOrigin, headIdentity };
}

async function assertSafePreCheckoutMetadata(gitRoot) {
  if (await pathExists(path.join(gitRoot, 'info', 'attributes'))) {
    throw unsafe('Git attributes metadata is not allowed before checkout');
  }
  const hooksRoot = path.join(gitRoot, 'hooks');
  if (await pathExists(hooksRoot)) {
    await assertPhysicalDirectory(hooksRoot, 'Git hooks');
    if ((await fs.readdir(hooksRoot)).length !== 0) {
      throw unsafe('Git hooks must be empty before checkout');
    }
  }
}

export async function assertSafeGeneratedTree({ ownerRoot, treeRoot, label }) {
  const owner = path.resolve(ownerRoot);
  const candidate = path.resolve(treeRoot);
  if (!isStrictlyInside(owner, candidate)) throw unsafe(`${label} escapes its owner`);
  if (!await pathExists(candidate)) return;
  await assertPhysicalDirectory(owner, `${label} owner`);
  await assertContainedTree(candidate, candidate, label);
}

async function assertContainedTree(boundaryRoot, treeRoot, label) {
  const boundary = path.resolve(boundaryRoot);
  const root = path.resolve(treeRoot);
  await assertPhysicalDirectory(root, label);
  await inspectContainedNode(boundary, root, label, new Set());
}

async function inspectContainedNode(boundary, candidate, label, visited) {
  const metadata = await fs.lstat(candidate);
  if (metadata.isSymbolicLink()) {
    let target;
    try {
      target = await fs.realpath(candidate);
    } catch {
      throw unsafe(`${label} contains a broken link or junction`);
    }
    if (!isStrictlyInside(boundary, target)) {
      throw unsafe(`${label} contains a link, junction, or reparse escape`);
    }
    return inspectContainedNode(boundary, target, label, visited);
  }
  if (metadata.isFile()) return;
  if (!metadata.isDirectory()) throw unsafe(`${label} contains a non-physical entry`);
  const physical = await fs.realpath(candidate);
  if (!samePath(candidate, physical)) {
    throw unsafe(`${label} contains a junction or reparse escape`);
  }
  const visitedPath = canonicalTraversalPath(physical);
  if (visited.has(visitedPath)) return;
  visited.add(visitedPath);
  const entries = await fs.readdir(candidate);
  for (const name of entries) {
    await inspectContainedNode(boundary, path.join(candidate, name), label, visited);
  }
}

function canonicalTraversalPath(candidate) {
  const normalized = path.normalize(path.resolve(candidate));
  return process.platform === 'win32' ? normalized.toLowerCase() : normalized;
}

async function assertPhysicalTree(treeRoot, label) {
  const rootMetadata = await physicalMetadata(treeRoot, label);
  if (!rootMetadata.isDirectory()) throw unsafe(`${label} must be a physical directory`);
  const entries = await fs.readdir(treeRoot, { withFileTypes: true });
  for (const entry of entries) {
    const entryPath = path.join(treeRoot, entry.name);
    const metadata = await fs.lstat(entryPath);
    if (metadata.isSymbolicLink()) {
      throw unsafe(`${label} contains a link, junction, or reparse escape`);
    }
    if (metadata.isDirectory()) await assertPhysicalTree(entryPath, label);
    else if (!metadata.isFile()) throw unsafe(`${label} contains a non-physical entry`);
  }
}

async function assertPhysicalDirectory(candidate, label) {
  const metadata = await physicalMetadata(candidate, label);
  if (!metadata.isDirectory()) throw unsafe(`${label} must be a physical directory`);
}

async function assertPhysicalFile(candidate, label) {
  const metadata = await physicalMetadata(candidate, label);
  if (!metadata.isFile()) throw unsafe(`${label} must be a physical file`);
}

async function physicalMetadata(candidate, label) {
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.lstat(candidate, { bigint: true }),
      fs.realpath(candidate),
    ]);
  } catch (error) {
    if (error?.code === 'ENOENT') throw unsafe(`${label} is missing`);
    throw error;
  }
  if (metadata.isSymbolicLink() || !samePath(candidate, physical)) {
    throw unsafe(`${label} must be physical, not a link, junction, or reparse point`);
  }
  return metadata;
}

async function assertOwnedFile(candidate, token, identity, label) {
  let metadata;
  let contents;
  try {
    [metadata, contents] = await Promise.all([
      fs.lstat(candidate, { bigint: true }),
      fs.readFile(candidate, 'utf8'),
    ]);
  } catch {
    throw setupError('ERR_CIV_ENGINE_SETUP_OWNERSHIP', `${label} ownership cannot be proven`);
  }
  if (
    !metadata.isFile()
    || metadata.isSymbolicLink()
    || (identity && !sameIdentity(metadata, identity))
    || contents !== ownerDocument(token)
  ) {
    throw setupError('ERR_CIV_ENGINE_SETUP_OWNERSHIP', `${label} ownership changed`);
  }
}

function ownerDocument(token) {
  return `${JSON.stringify({ token })}\n`;
}

function fileIdentity(metadata) {
  return { dev: metadata.dev.toString(), ino: metadata.ino.toString() };
}

function sameIdentity(metadata, identity) {
  return identity
    && metadata.dev.toString() === identity.dev
    && metadata.ino.toString() === identity.ino;
}

async function pathExists(candidate) {
  try {
    await fs.lstat(candidate);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function isStrictlyInside(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return Boolean(relative && !path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

function unsafe(message) {
  return setupError('ERR_CIV_ENGINE_SETUP_UNSAFE', message);
}

function mismatch(message) {
  return setupError('ERR_CIV_ENGINE_SETUP_MISMATCH', message);
}

function setupError(code, message) {
  return Object.assign(new Error(message), { code });
}
