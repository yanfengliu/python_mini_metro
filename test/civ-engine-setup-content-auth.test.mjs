import assert from 'node:assert/strict';
import {
  appendFile,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  buildPin,
  installPinDependencies,
} from '../scripts/civ-engine-setup-operations.mjs';
import { authenticateCheckoutContent } from '../scripts/civ-engine-setup-content.mjs';
import {
  git,
  withDetachedCheckout,
} from './civ-engine-setup-git-fixtures.mjs';

test('npm phases reject assume-unchanged and skip-worktree content concealment', async (t) => {
  for (const [name, flag, operation] of [
    ['assume-unchanged', '--assume-unchanged', installPinDependencies],
    ['skip-worktree', '--skip-worktree', buildPin],
  ]) {
    await t.test(name, async () => {
      await withDetachedCheckout(async ({ checkoutRoot, commit }) => {
        const sourcePath = path.join(checkoutRoot, 'src', 'index.ts');
        git(checkoutRoot, ['update-index', flag, 'src/index.ts']);
        await writeFile(sourcePath, 'export const concealed = true;\n');
        await assertPhaseBlockedBeforeLaunch(
          operation,
          checkoutRoot,
          commit,
          /index|conceal|tracked/i,
        );
      });
    });
  }
});

test('npm phases reject info excludes pin-local npm config and ignored extra files', async (t) => {
  const cases = [
    {
      name: 'info exclude pattern',
      prepare: async ({ checkoutRoot, gitDir }) => {
        await appendFile(path.join(gitDir, 'info', 'exclude'), '\nconcealed.txt\n');
        await writeFile(path.join(checkoutRoot, 'concealed.txt'), 'concealed\n');
      },
      pattern: /exclude/i,
    },
    {
      name: 'pin-local npm config',
      prepare: ({ checkoutRoot }) => writeFile(
        path.join(checkoutRoot, '.npmrc'),
        'registry=https://credential.invalid/\n',
      ),
      pattern: /npm.*config|\.npmrc/i,
    },
    {
      name: 'unexpected ignored file',
      prepare: async ({ checkoutRoot }) => {
        await appendFile(path.join(checkoutRoot, '.gitignore'), 'ignored-extra.txt\n');
        git(checkoutRoot, ['add', '.gitignore']);
        git(checkoutRoot, [
          '-c', 'user.name=Setup Auth Test',
          '-c', 'user.email=setup-auth@example.invalid',
          'commit', '--quiet', '-m', 'ignore fixture file',
        ]);
        git(checkoutRoot, ['checkout', '--detach', '--quiet', 'HEAD']);
        await writeFile(path.join(checkoutRoot, 'ignored-extra.txt'), 'ignored but unsafe\n');
      },
      pattern: /unexpected|untracked|checkout/i,
    },
  ];
  for (const fixture of cases) {
    await t.test(fixture.name, async () => {
      await withDetachedCheckout(async (context) => {
        await fixture.prepare(context);
        await assertPhaseBlockedBeforeLaunch(
          installPinDependencies,
          context.checkoutRoot,
          context.commit,
          fixture.pattern,
        );
      });
    });
  }
});

test('an authenticated checkout reaches the dependency phase planner', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit }) => {
    let launched = false;
    await installPinDependencies({
      checkoutRoot,
      pin: { commit },
      transaction: {},
      planNpm: async () => ({ command: 'fixture', args: [], options: {} }),
      runProcess() { launched = true; },
    });
    assert.equal(launched, true);
  });
});

test('strict authentication cannot be weakened with an option flag', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit }) => {
    await assert.rejects(
      authenticateCheckoutContent({
        checkoutRoot,
        expectedCommit: commit,
        allowTrackedChanges: true,
      }),
      /unsupported option/i,
    );
  });
});

test('raw local Git metadata is re-audited before each content Git call', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, gitDir }) => {
    let gitCalls = 0;
    await assert.rejects(
      authenticateCheckoutContent({
        checkoutRoot,
        expectedCommit: commit,
        runGit: async ({ args }) => {
          gitCalls += 1;
          const output = git(checkoutRoot, args).stdout;
          if (gitCalls === 1) {
            await appendFile(
              path.join(gitDir, 'config'),
              '\n[include]\n\tpath = ../hostile-config\n',
            );
          }
          return output;
        },
      }),
      /config.*include|include.*config/i,
    );
    assert.equal(gitCalls, 1);
  });
});

async function assertPhaseBlockedBeforeLaunch(
  operation,
  checkoutRoot,
  expectedCommit,
  pattern,
) {
  let planned = false;
  let launched = false;
  await assert.rejects(operation({
    checkoutRoot,
    pin: { commit: expectedCommit },
    transaction: {},
    planNpm: async () => {
      planned = true;
      return { command: 'fixture', args: [], options: {} };
    },
    runProcess() { launched = true; },
  }), pattern);
  assert.equal(planned, false);
  assert.equal(launched, false);
}
