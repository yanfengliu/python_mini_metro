import assert from 'node:assert/strict';
import { mkdir, readdir } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { CIV_ENGINE_PIN } from '../scripts/civ-engine-pin.mjs';
import { clonePinnedRepository } from '../scripts/civ-engine-setup-clone.mjs';
import {
  auditCheckoutMetadata,
  createSetupTransaction,
} from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';
import {
  FIXED_ORIGIN,
  git,
  withDetachedCheckout,
} from './civ-engine-setup-git-fixtures.mjs';

test('clone is isolated before discovery and audited before exact checkout', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const transaction = await createSetupTransaction({ repoRoot: fixtureRoot });
    const events = [];
    try {
      await clonePinnedRepository({
        repoRoot: fixtureRoot,
        repositoryUrl: CIV_ENGINE_PIN.repositoryUrl,
        commit: CIV_ENGINE_PIN.commit,
        destination: transaction.checkoutPath,
        transaction,
        resolveGit: () => 'C:\\trusted\\git.exe',
        runProcess(plan, { phase }) {
          events.push({ type: 'process', phase, plan });
        },
        auditCheckout: async (input) => {
          events.push({ type: 'audit', input });
        },
      });
    } finally {
      await transactionCleanup(transaction);
    }

    assert.deepEqual(events.map(({ type, phase, input }) => (
      type === 'process' ? phase : input.checkoutMode
    )), [
      'fixed civ-engine clone',
      'pre-checkout',
      'detached civ-engine checkout',
      'detached',
    ]);
    const clonePlan = events[0].plan;
    assert.equal(clonePlan.options.cwd, transaction.parentPath);
    assert.equal(
      clonePlan.options.env.GIT_CEILING_DIRECTORIES,
      transaction.parentPath,
    );
    assert.equal(
      clonePlan.args.includes(`--template=${transaction.templatePath}`),
      true,
    );
    assert.equal(clonePlan.args.includes(CIV_ENGINE_PIN.repositoryUrl), true);
    assert.equal(clonePlan.args.includes(transaction.checkoutPath), true);
    assert.equal(events[1].input.expectedCommit, CIV_ENGINE_PIN.commit);
    assert.deepEqual(events[2].plan.args.slice(-3), [
      'checkout',
      '--detach',
      CIV_ENGINE_PIN.commit,
    ]);
    assert.equal(events[2].plan.args.includes('--force'), false);
    assert.equal(events[3].input.expectedCommit, CIV_ENGINE_PIN.commit);
    assert.equal(events[3].input.expectedRepositoryUrl, CIV_ENGINE_PIN.repositoryUrl);
  });
});

test('real pre-checkout audit proves the descriptor object before checkout', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, fixtureRoot }) => {
    const templateRoot = path.join(fixtureRoot, 'empty-template');
    const cloneRoot = path.join(fixtureRoot, 'unborn-clone');
    await mkdir(templateRoot);
    git(fixtureRoot, [
      'clone',
      '--quiet',
      '--no-checkout',
      '--no-tags',
      `--template=${templateRoot}`,
      checkoutRoot,
      cloneRoot,
    ]);
    git(cloneRoot, ['remote', 'set-url', 'origin', FIXED_ORIGIN]);
    git(cloneRoot, ['config', 'remote.origin.tagOpt', '--no-tags']);

    const audit = await auditCheckoutMetadata({
      checkoutRoot: cloneRoot,
      expectedCommit: commit,
      expectedRepositoryUrl: FIXED_ORIGIN,
      checkoutMode: 'pre-checkout',
    });
    assert.equal(audit.commit, commit);
    assert.deepEqual(await readdir(cloneRoot), ['.git']);
  });
});

async function transactionCleanup(transaction) {
  const { rm } = await import('node:fs/promises');
  await rm(transaction.parentPath, { recursive: true, force: true });
}
