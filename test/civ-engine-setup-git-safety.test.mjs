import assert from 'node:assert/strict';
import {
  appendFile,
  mkdir,
  readFile,
  rm,
  symlink,
  unlink,
  utimes,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  planGitInvocation,
} from '../scripts/civ-engine-setup-process.mjs';
import {
  assertSafeGeneratedTree,
  auditCheckoutMetadata,
} from '../scripts/civ-engine-setup-safety.mjs';
import {
  FIXED_ORIGIN,
  snapshotByteTree,
  snapshotIndex,
  withDetachedCheckout,
} from './civ-engine-setup-git-fixtures.mjs';

const CONFIG_REJECTIONS = [
  {
    name: 'config include',
    section: '[include]\n\tpath = ../external/config\n',
    pattern: /config.*include|include.*config/i,
  },
  {
    name: 'filesystem monitor',
    section: '[core]\n\tfsmonitor = probe-command\n',
    pattern: /fsmonitor|filesystem monitor/i,
  },
  {
    name: 'hooks path',
    section: '[core]\n\thooksPath = ../external/hooks\n',
    pattern: /hook/i,
  },
  {
    name: 'clean filter command',
    section: '[filter "probe"]\n\tclean = probe-command\n',
    pattern: /filter/i,
  },
  {
    name: 'credential helper',
    section: '[credential]\n\thelper = probe-command\n',
    pattern: /credential/i,
  },
  {
    name: 'worktree redirect',
    section: '[core]\n\tworktree = ../external\n',
    pattern: /worktree/i,
  },
  {
    name: 'remote command redirect',
    section: '[remote "origin"]\n\tuploadpack = probe-command\n',
    pattern: /remote.*command|uploadpack|redirect/i,
  },
];

test('filesystem audit rejects executable or redirecting Git config before Git runs', async (t) => {
  for (const variant of CONFIG_REJECTIONS) {
    await t.test(variant.name, async () => {
      await withDetachedCheckout(async ({ checkoutRoot, commit, gitDir }) => {
        await appendFile(path.join(gitDir, 'config'), `\n${variant.section}`);
        let gitCalls = 0;
        await assert.rejects(
          auditCheckoutMetadata({
            checkoutRoot,
            expectedCommit: commit,
            expectedRepositoryUrl: FIXED_ORIGIN,
            runGit() {
              gitCalls += 1;
              throw new Error('Git ran before its metadata was trusted');
            },
          }),
          variant.pattern,
        );
        assert.equal(gitCalls, 0);
      });
    });
  }
});

test('Git config rejection never reflects attacker-controlled section text', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, gitDir }) => {
    const sentinel = 'credential-sentinel-must-not-appear';
    await appendFile(
      path.join(gitDir, 'config'),
      `\n[url "https://user:${sentinel}@example.invalid/"]\n\tinsteadOf = https://example.invalid/\n`,
    );
    let gitCalls = 0;
    await assert.rejects(
      auditCheckoutMetadata({
        checkoutRoot,
        expectedCommit: commit,
        expectedRepositoryUrl: FIXED_ORIGIN,
        runGit() {
          gitCalls += 1;
          throw new Error('Git ran before its metadata was trusted');
        },
      }),
      (error) => (
        /unexpected local Git config section/i.test(error.message)
        && !error.message.includes(sentinel)
      ),
    );
    assert.equal(gitCalls, 0);
  });
});

test('filesystem audit rejects external object alternates before Git runs', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, externalRoot, gitDir }) => {
    await writeFile(
      path.join(gitDir, 'objects', 'info', 'alternates'),
      `${externalRoot}\n`,
    );
    await assertFilesystemFirstRejection({
      checkoutRoot,
      commit,
      pattern: /alternate/i,
    });
  });
});

test('filesystem audit rejects replace refs before Git runs', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, gitDir }) => {
    const replaceRoot = path.join(gitDir, 'refs', 'replace');
    await mkdir(replaceRoot, { recursive: true });
    await writeFile(path.join(replaceRoot, '0'.repeat(40)), `${commit}\n`);
    await assertFilesystemFirstRejection({
      checkoutRoot,
      commit,
      pattern: /replace/i,
    });
  });
});

test('filesystem audit rejects shallow metadata before Git runs', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, gitDir }) => {
    await writeFile(path.join(gitDir, 'shallow'), `${commit}\n`);
    await assertFilesystemFirstRejection({
      checkoutRoot,
      commit,
      pattern: /shallow/i,
    });
  });
});

test('filesystem audit rejects a nested Git metadata junction without touching its target', async () => {
  await withDetachedCheckout(async ({
    checkoutRoot,
    commit,
    externalRoot,
    gitDir,
  }) => {
    const infoPath = path.join(gitDir, 'objects', 'info');
    const externalInfo = path.join(externalRoot, 'git-info');
    await rm(infoPath, { recursive: true, force: true });
    await mkdir(externalInfo, { recursive: true });
    const sentinelPath = path.join(externalInfo, 'sentinel.txt');
    await writeFile(sentinelPath, 'metadata sentinel\n');
    await symlink(externalInfo, infoPath, 'junction');
    try {
      await assertFilesystemFirstRejection({
        checkoutRoot,
        commit,
        pattern: /physical|reparse|junction|link/i,
      });
      assert.equal(await readFile(sentinelPath, 'utf8'), 'metadata sentinel\n');
    } finally {
      await unlink(infoPath);
    }
  });
});

test('Git read plans strip ambient redirection and disable optional locks', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, externalRoot }) => {
    const homeDir = path.join(externalRoot, 'controlled-home');
    const tempDir = path.join(externalRoot, 'controlled-temp');
    await Promise.all([
      mkdir(homeDir, { recursive: true }),
      mkdir(tempDir, { recursive: true }),
    ]);
    const inheritedEnv = {
      PATH: process.env.PATH ?? '',
      SystemRoot: process.env.SystemRoot ?? '',
      GIT_DIR: externalRoot,
      GIT_WORK_TREE: externalRoot,
      GIT_OBJECT_DIRECTORY: externalRoot,
      GIT_ALTERNATE_OBJECT_DIRECTORIES: externalRoot,
      GIT_REPLACE_REF_BASE: 'refs/replace-probe',
      GIT_CONFIG_COUNT: '1',
      GIT_CONFIG_KEY_0: 'core.fsmonitor',
      GIT_CONFIG_VALUE_0: 'probe-command',
      GIT_SSH_COMMAND: 'probe-command',
      GIT_ASKPASS: 'probe-command',
      SSH_AUTH_SOCK: 'probe-secret',
      NODE_OPTIONS: '--require probe-command',
      npm_config_userconfig: 'probe-secret',
      NPM_TOKEN: 'probe-secret',
      AWS_SECRET_ACCESS_KEY: 'probe-secret',
    };
    const plan = planGitInvocation({
      gitExecutable: 'git',
      repoRoot: checkoutRoot,
      args: ['status', '--porcelain=v1', '-z', '--untracked-files=all'],
      inheritedEnv,
      homeDir,
      tempDir,
    });

    assert.equal(plan.command, 'git');
    assert.equal(plan.options.cwd, checkoutRoot);
    assert.equal(plan.options.shell, false);
    assert.equal(plan.options.windowsHide, true);
    assert.equal(plan.args[0], '--no-optional-locks');
    assert.equal(plan.options.env.GIT_OPTIONAL_LOCKS, '0');
    assert.equal(plan.options.env.GIT_TERMINAL_PROMPT, '0');
    assert.equal(plan.options.env.GIT_CONFIG_NOSYSTEM, '1');
    assert.equal(plan.options.env.GIT_ATTR_NOSYSTEM, '1');
    assert.equal(plan.options.env.GIT_NO_REPLACE_OBJECTS, '1');
    assert.equal(plan.options.env.HOME, homeDir);
    assert.equal(plan.options.env.USERPROFILE, homeDir);
    assert.equal(plan.options.env.TMP, tempDir);
    assert.equal(plan.options.env.TEMP, tempDir);
    assert.match(plan.args.join('\0'), /core\.fsmonitor=false/);
    assert.match(plan.args.join('\0'), /credential\.helper=/);
    for (const key of [
      'GIT_DIR',
      'GIT_WORK_TREE',
      'GIT_OBJECT_DIRECTORY',
      'GIT_ALTERNATE_OBJECT_DIRECTORIES',
      'GIT_REPLACE_REF_BASE',
      'GIT_CONFIG_COUNT',
      'GIT_CONFIG_KEY_0',
      'GIT_CONFIG_VALUE_0',
      'GIT_SSH_COMMAND',
      'GIT_ASKPASS',
      'SSH_AUTH_SOCK',
      'NODE_OPTIONS',
      'npm_config_userconfig',
      'NPM_TOKEN',
      'AWS_SECRET_ACCESS_KEY',
    ]) {
      assert.equal(Object.hasOwn(plan.options.env, key), false, key);
    }
    assert.doesNotMatch(JSON.stringify(plan), /probe-secret|probe-command/);
  });
});

test('read-only checkout verification preserves every byte and the Git index timestamp', async () => {
  await withDetachedCheckout(async ({ checkoutRoot, commit, fixtureRoot, gitDir }) => {
    const packagePath = path.join(checkoutRoot, 'package.json');
    const changedTime = new Date(Date.now() - 60_000);
    await utimes(packagePath, changedTime, changedTime);
    const [beforeTree, beforeIndex] = await Promise.all([
      snapshotByteTree(fixtureRoot),
      snapshotIndex(gitDir),
    ]);

    await auditCheckoutMetadata({
      checkoutRoot,
      expectedCommit: commit,
      expectedRepositoryUrl: FIXED_ORIGIN,
    });

    const [afterTree, afterIndex] = await Promise.all([
      snapshotByteTree(fixtureRoot),
      snapshotIndex(gitDir),
    ]);
    assert.deepEqual(afterTree, beforeTree);
    assert.deepEqual(afterIndex, beforeIndex);
  });
});

test('generated-tree audit rejects nested junctions and preserves their targets', async (t) => {
  for (const label of ['dist', 'node_modules']) {
    await t.test(label, async () => {
      await withDetachedCheckout(async ({ checkoutRoot, externalRoot }) => {
        const treeRoot = path.join(checkoutRoot, label);
        const nestedRoot = path.join(treeRoot, 'physical', 'nested');
        const externalTarget = path.join(externalRoot, `${label}-target`);
        await Promise.all([
          mkdir(nestedRoot, { recursive: true }),
          mkdir(externalTarget, { recursive: true }),
        ]);
        const sentinelPath = path.join(externalTarget, 'sentinel.txt');
        const linkPath = path.join(nestedRoot, 'escape');
        await writeFile(sentinelPath, `${label} sentinel\n`);
        await symlink(externalTarget, linkPath, 'junction');
        try {
          await assert.rejects(
            assertSafeGeneratedTree({
              ownerRoot: checkoutRoot,
              treeRoot,
              label,
            }),
            /physical|reparse|junction|link|escape/i,
          );
          assert.equal(
            await readFile(sentinelPath, 'utf8'),
            `${label} sentinel\n`,
          );
        } finally {
          await unlink(linkPath);
        }
      });
    });
  }
});

test('generated-tree audit permits absent and recursively physical trees', async () => {
  await withDetachedCheckout(async ({ checkoutRoot }) => {
    const absentRoot = path.join(checkoutRoot, 'not-created');
    await assert.doesNotReject(assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: absentRoot,
      label: 'absent generated tree',
    }));
    await assert.doesNotReject(assertSafeGeneratedTree({
      ownerRoot: checkoutRoot,
      treeRoot: path.join(checkoutRoot, 'dist'),
      label: 'dist',
    }));
  });
});

test('generated-tree audit permits links that stay within the owned checkout', async () => {
  await withDetachedCheckout(async ({ checkoutRoot }) => {
    const treeRoot = path.join(checkoutRoot, 'node_modules');
    const targetRoot = path.join(treeRoot, 'physical-package');
    const linkRoot = path.join(treeRoot, 'contained-package-link');
    await mkdir(targetRoot, { recursive: true });
    await writeFile(path.join(targetRoot, 'index.js'), 'export {};\n');
    await symlink(
      targetRoot,
      linkRoot,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    try {
      await assert.doesNotReject(assertSafeGeneratedTree({
        ownerRoot: checkoutRoot,
        treeRoot,
        label: 'node_modules',
      }));
    } finally {
      await unlink(linkRoot);
    }
  });
});

test('generated-tree traversal never relies on filesystem inode uniqueness', async () => {
  const source = await readFile(
    new URL('../scripts/civ-engine-setup-safety.mjs', import.meta.url),
    'utf8',
  );
  const traversal = source.slice(
    source.indexOf('async function inspectContainedNode'),
    source.indexOf('async function assertPhysicalTree'),
  );
  assert.doesNotMatch(traversal, /metadata\.(?:dev|ino)\b/);
  assert.match(traversal, /canonicalTraversalPath\(physical/);
});

test('generated-tree traversal terminates a contained directory-link cycle', async () => {
  await withDetachedCheckout(async ({ checkoutRoot }) => {
    const treeRoot = path.join(checkoutRoot, 'node_modules');
    const packageRoot = path.join(treeRoot, 'physical-package');
    const nestedRoot = path.join(packageRoot, 'nested');
    const cyclePath = path.join(nestedRoot, 'back-to-package');
    await mkdir(nestedRoot, { recursive: true });
    await symlink(
      packageRoot,
      cyclePath,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    try {
      await assert.doesNotReject(assertSafeGeneratedTree({
        ownerRoot: checkoutRoot,
        treeRoot,
        label: 'node_modules',
      }));
    } finally {
      await unlink(cyclePath);
    }
  });
});

async function assertFilesystemFirstRejection({ checkoutRoot, commit, pattern }) {
  let gitCalls = 0;
  await assert.rejects(
    auditCheckoutMetadata({
      checkoutRoot,
      expectedCommit: commit,
      expectedRepositoryUrl: FIXED_ORIGIN,
      runGit() {
        gitCalls += 1;
        throw new Error('Git ran before its metadata was trusted');
      },
    }),
    pattern,
  );
  assert.equal(gitCalls, 0);
}
