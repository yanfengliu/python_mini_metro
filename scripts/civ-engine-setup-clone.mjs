import fs from 'node:fs/promises';
import path from 'node:path';

import { CIV_ENGINE_PIN } from './civ-engine-pin.mjs';
import {
  planGitInvocation,
  resolveTrustedGitExecutable,
  runSetupProcess,
} from './civ-engine-setup-process.mjs';
import { auditCheckoutMetadata } from './civ-engine-setup-safety.mjs';

export async function clonePinnedRepository({
  repoRoot,
  repositoryUrl,
  commit,
  destination,
  transaction,
  resolveGit = resolveTrustedGitExecutable,
  runProcess = runSetupProcess,
  auditCheckout = auditCheckoutMetadata,
}) {
  await assertFixedCloneRequest({
    repoRoot,
    repositoryUrl,
    commit,
    destination,
    transaction,
  });
  const gitExecutable = await resolveGit();
  const shared = {
    gitExecutable,
    inheritedEnv: trustedGitEnvironment(gitExecutable),
    homeDir: transaction.homePath,
    tempDir: transaction.tempPath,
    gitCeilingDirectories: transaction.parentPath,
  };
  runProcess(planGitInvocation({
    ...shared,
    repoRoot: transaction.parentPath,
    args: [
      'clone',
      '--no-checkout',
      '--no-tags',
      '--origin=origin',
      `--template=${transaction.templatePath}`,
      CIV_ENGINE_PIN.repositoryUrl,
      transaction.checkoutPath,
    ],
  }), { phase: 'fixed civ-engine clone' });

  await auditCheckout({
    checkoutRoot: transaction.checkoutPath,
    expectedCommit: CIV_ENGINE_PIN.commit,
    expectedRepositoryUrl: CIV_ENGINE_PIN.repositoryUrl,
    checkoutMode: 'pre-checkout',
  });

  runProcess(planGitInvocation({
    ...shared,
    repoRoot: transaction.checkoutPath,
    args: ['checkout', '--detach', CIV_ENGINE_PIN.commit],
  }), { phase: 'detached civ-engine checkout' });

  return auditCheckout({
    checkoutRoot: transaction.checkoutPath,
    expectedCommit: CIV_ENGINE_PIN.commit,
    expectedRepositoryUrl: CIV_ENGINE_PIN.repositoryUrl,
    checkoutMode: 'detached',
  });
}

async function assertFixedCloneRequest({
  repoRoot,
  repositoryUrl,
  commit,
  destination,
  transaction,
}) {
  if (
    !transaction
    || repositoryUrl !== CIV_ENGINE_PIN.repositoryUrl
    || commit !== CIV_ENGINE_PIN.commit
    || !samePath(repoRoot, transaction.repoRoot)
    || !samePath(destination, transaction.checkoutPath)
    || !isStrictlyInside(transaction.parentPath, destination)
    || await pathExists(destination)
  ) {
    throw refused('clone request is not the fixed descriptor transaction');
  }
  await Promise.all([
    assertPhysicalDirectory(transaction.parentPath, 'setup transaction'),
    assertPhysicalDirectory(transaction.homePath, 'setup home'),
    assertPhysicalDirectory(transaction.tempPath, 'setup temporary directory'),
    assertEmptyPhysicalDirectory(transaction.templatePath, 'Git template'),
  ]);
}

async function assertEmptyPhysicalDirectory(candidate, label) {
  await assertPhysicalDirectory(candidate, label);
  if ((await fs.readdir(candidate)).length !== 0) {
    throw refused(`${label} must be empty`);
  }
}

async function assertPhysicalDirectory(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([fs.lstat(resolved), fs.realpath(resolved)]);
  } catch {
    throw refused(`${label} is unavailable`);
  }
  if (!metadata.isDirectory() || metadata.isSymbolicLink() || !samePath(resolved, physical)) {
    throw refused(`${label} must be a physical directory`);
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

function trustedGitEnvironment(gitExecutable) {
  return {
    SystemRoot: process.env.SystemRoot,
    PATH: path.dirname(gitExecutable),
  };
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function isStrictlyInside(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return Boolean(relative && !path.isAbsolute(relative) && !relative.startsWith(`..${path.sep}`));
}

function refused(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_REFUSED' });
}
