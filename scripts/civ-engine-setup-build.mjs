import fs from 'node:fs/promises';
import path from 'node:path';

import { assertSafeGeneratedTree } from './civ-engine-setup-safety.mjs';

export async function planPinnedTypeScriptBuild({
  checkoutRoot,
  compilerPath = path.join(
    checkoutRoot,
    'node_modules',
    'typescript',
    'bin',
    'tsc',
  ),
  execPath = process.execPath,
  homePath,
  tempPath,
  sourceEnv = process.env,
}) {
  const root = path.resolve(checkoutRoot);
  const expectedCompiler = path.join(
    root,
    'node_modules',
    'typescript',
    'bin',
    'tsc',
  );
  const nodeExecutable = path.resolve(execPath);
  const compiler = path.resolve(compilerPath);
  if (!samePath(compiler, expectedCompiler) || !isStrictlyInside(root, compiler)) {
    throw buildIdentityError('TypeScript compiler is not the fixed pin-local CLI');
  }
  await Promise.all([
    assertPhysicalDirectory(root, 'pinned checkout'),
    assertPhysicalDirectory(homePath, 'setup home'),
    assertPhysicalDirectory(tempPath, 'setup temporary directory'),
    assertPhysicalFile(nodeExecutable, 'Node executable'),
    assertPhysicalFile(compiler, 'TypeScript compiler'),
  ]);
  const environment = {
    HOME: path.resolve(homePath),
    USERPROFILE: path.resolve(homePath),
    TEMP: path.resolve(tempPath),
    TMP: path.resolve(tempPath),
    TMPDIR: path.resolve(tempPath),
  };
  if (process.platform === 'win32' && sourceEnv.SystemRoot) {
    environment.SystemRoot = sourceEnv.SystemRoot;
  }
  return {
    command: nodeExecutable,
    args: [compiler, '-p', 'tsconfig.build.json'],
    options: {
      cwd: root,
      env: environment,
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  };
}

export async function removePinnedBuildOutput({ checkoutRoot }) {
  const root = path.resolve(checkoutRoot);
  const distRoot = path.join(root, 'dist');
  await assertSafeGeneratedTree({
    ownerRoot: root,
    treeRoot: distRoot,
    label: 'civ-engine dist',
  });
  if (!await pathExists(distRoot)) return;
  await assertPhysicalDirectory(distRoot, 'civ-engine dist');
  await fs.rm(distRoot, { recursive: true, force: false });
}

async function assertPhysicalDirectory(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([fs.lstat(resolved), fs.realpath(resolved)]);
  } catch {
    throw buildIdentityError(`${label} is unavailable`);
  }
  if (!metadata.isDirectory() || metadata.isSymbolicLink() || !samePath(resolved, physical)) {
    throw buildIdentityError(`${label} must be a physical directory`);
  }
}

async function assertPhysicalFile(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([fs.lstat(resolved), fs.realpath(resolved)]);
  } catch {
    throw buildIdentityError(`${label} is unavailable`);
  }
  if (!metadata.isFile() || metadata.isSymbolicLink() || !samePath(resolved, physical)) {
    throw buildIdentityError(`${label} must be a physical file`);
  }
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
  return Boolean(relative && !path.isAbsolute(relative) && !relative.startsWith(`..${path.sep}`));
}

function buildIdentityError(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_BUILD_IDENTITY' });
}
