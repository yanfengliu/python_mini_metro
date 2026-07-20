import assert from 'node:assert/strict';
import {
  access,
  appendFile,
  mkdir,
  readFile,
  rename,
  rm,
  symlink,
  unlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { runReadOnlyGit } from '../scripts/civ-engine-setup-process.mjs';
import { auditSourceGitMetadata } from '../scripts/source-provenance-git-safety.mjs';
import {
  assertSourceStateAllowed,
  captureSourceProvenance,
  captureSourceState,
} from '../scripts/source-provenance.mjs';
import { git, sourceOptions, withRepository } from './source-provenance-fixtures.mjs';

const SECRET = 'ROOT_GIT_SECRET_MUST_NOT_LEAK';
const IDENTIFIER_SECRET = 'root-config-identifier-secret';
const DANGEROUS_CONFIGS = [
  ['include.path', `[include]\n\tpath = ../${SECRET}\n`],
  [
    'includeif.path',
    `[includeIf "gitdir:../${SECRET}/"]\n\tpath = ../${SECRET}\n`,
  ],
  ['filter.clean', `[filter "probe"]\n\tclean = ${SECRET}\n`],
  ['filter.smudge', `[filter "probe"]\n\tsmudge = ${SECRET}\n`],
  ['filter.process', `[filter "probe"]\n\tprocess = ${SECRET}\n`],
  ['diff.textconv', `[diff "probe"]\n\ttextconv = ${SECRET}\n`],
  ['diff.command', `[diff "probe"]\n\tcommand = ${SECRET}\n`],
  ['credential.helper', `[credential]\n\thelper = ${SECRET}\n`],
  ['core.hookspath', `[core]\n\thooksPath = ../${SECRET}\n`],
  ['core.fsmonitor', `[core]\n\tfsmonitor = ${SECRET}\n`],
  ['core.worktree', `[core]\n\tworktree = ../${SECRET}\n`],
  ['core.sshcommand', `[core]\n\tsshCommand = ${SECRET}\n`],
  ['core.trustctime', '[core]\n\ttrustCtime = false\n'],
  ['core.checkstat', '[core]\n\tcheckStat = minimal\n'],
  ['core.ignorestat', '[core]\n\tignoreStat = true\n'],
  ['core.attributesfile', `[core]\n\tattributesFile = ../${SECRET}\n`],
  ['core.excludesfile', `[core]\n\texcludesFile = ../${SECRET}\n`],
  [
    'url.insteadof',
    `[url "https://user:${SECRET}@example.invalid/"]\n\tinsteadOf = https://github.com/\n`,
  ],
  [
    'url.pushinsteadof',
    `[url "https://user:${SECRET}@example.invalid/"]\n\tpushInsteadOf = https://github.com/\n`,
  ],
  ['http.extraheader', `[http]\n\textraHeader = Authorization: ${SECRET}\n`],
  ['http.proxy', `[http]\n\tproxy = https://user:${SECRET}@proxy.invalid\n`],
  ['remote.uploadpack', `[remote "origin"]\n\tuploadpack = ${SECRET}\n`],
  ['remote.receivepack', `[remote "origin"]\n\treceivepack = ${SECRET}\n`],
  ['alias.command', `[alias]\n\tprobe = !${SECRET}\n`],
  ['attacker identifier', `[${IDENTIFIER_SECRET}]\n\tshell = ${SECRET}\n`],
  ['difftool.cmd', `[difftool "probe"]\n\tcmd = ${SECRET}\n`],
  ['mergetool.cmd', `[mergetool "probe"]\n\tcmd = ${SECRET}\n`],
  ['gpg.program', `[gpg]\n\tprogram = ${SECRET}\n`],
  ['core.pager', `[core]\n\tpager = ${SECRET}\n`],
];

test('root config audit rejects unsafe entries categorically before Git', async (t) => {
  await withRepository(async (fixtureRoot, engine) => {
    const configPath = path.join(fixtureRoot, '.git', 'config');
    const originalConfig = await readFile(configPath, 'utf8');
    for (const [name, section] of DANGEROUS_CONFIGS) {
      await t.test(name, async () => {
        await writeFile(configPath, `${originalConfig}\n${section}`, 'utf8');
        let gitCalls = 0;
        try {
          await assert.rejects(
            captureSourceState({
              ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
              rootGitRunner() {
                gitCalls += 1;
                throw new Error('root Git executed before filesystem audit');
              },
            }),
            (error) => (
              error?.code === 'ERR_SOURCE_GIT_UNSAFE'
              && error.message === 'source Git metadata rejected: unsafe local Git config'
              && !error.message.includes(SECRET)
              && !error.message.includes(IDENTIFIER_SECRET)
            ),
          );
          assert.equal(gitCalls, 0);
        } finally {
          await writeFile(configPath, originalConfig, 'utf8');
        }
      });
    }
  });
});

test('a real fsmonitor sentinel never executes and config rejection is categorical', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const configPath = path.join(fixtureRoot, '.git', 'config');
    const probePath = path.join(fixtureRoot, 'fsmonitor-probe.mjs');
    const markerPath = path.join(fixtureRoot, 'fsmonitor-ran.txt');
    await writeFile(
      probePath,
      `import { writeFileSync } from 'node:fs';\nwriteFileSync(${JSON.stringify(markerPath)}, ${JSON.stringify(SECRET)});\n`,
      'utf8',
    );
    await appendFile(
      configPath,
      `\n[core]\n\tfsmonitor = node ${portable(probePath)} ${SECRET}\n`,
      'utf8',
    );

    await assert.rejects(
      captureSourceState(
        sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      ),
      (error) => (
        error?.code === 'ERR_SOURCE_GIT_UNSAFE'
        && error.message === 'source Git metadata rejected: unsafe local Git config'
        && !error.message.includes(SECRET)
      ),
    );
    await assert.rejects(access(markerPath), (error) => error?.code === 'ENOENT');
  });
});

test('root Git failures are categorical and never reflect invalid config values', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const secret = 'ROOT_CONFIG_SECRET_91CE';
    await appendFile(
      path.join(fixtureRoot, '.git', 'config'),
      `\n[core]\n\trepositoryFormatVersion = 1\n`
      + `[extensions]\n\tobjectFormat = ${secret}\n`,
      'utf8',
    );
    await assert.rejects(
      captureSourceState(
        sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      ),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_PROCESS'
        && Number.isInteger(error.status)
        && /^Git read failed \(\d+\)$/.test(error.message)
        && !error.message.includes(secret)
      ),
    );
  });
});

test('root Git ignores repo-derived and ambient HOME/XDG config and attributes', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const homePath = path.join(fixtureRoot, '.git-read-home');
    const xdgPath = path.join(fixtureRoot, '.ambient-xdg');
    const markerPath = path.join(fixtureRoot, 'global-filter-ran.txt');
    const probePath = path.join(fixtureRoot, 'global-filter-probe.mjs');
    await Promise.all([
      mkdir(path.join(homePath, '.config', 'git'), { recursive: true }),
      mkdir(path.join(xdgPath, 'git'), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(
        probePath,
        `import { writeFileSync } from 'node:fs';\nwriteFileSync(${JSON.stringify(markerPath)}, 'ran');\nprocess.stdin.resume();\n`,
        'utf8',
      ),
      writeFile(
        path.join(homePath, '.config', 'git', 'attributes'),
        '* filter=probe\n',
        'utf8',
      ),
      writeFile(
        path.join(xdgPath, 'git', 'attributes'),
        '* filter=probe\n',
        'utf8',
      ),
      writeFile(
        path.join(xdgPath, 'git', 'config'),
        `[filter "probe"]\n\tclean = node ${portable(probePath)}\n`,
        'utf8',
      ),
    ]);
    await writeFile(
      path.join(homePath, 'gitconfig'),
      `[filter "probe"]\n\tclean = node ${portable(probePath)}\n`,
      'utf8',
    );

    const captured = await captureSourceState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      rootGitRunner(options) {
        return runReadOnlyGit({
          ...options,
          inheritedEnv: {
            ...process.env,
            HOME: homePath,
            USERPROFILE: homePath,
            XDG_CONFIG_HOME: xdgPath,
            GIT_CONFIG_GLOBAL: path.join(homePath, 'gitconfig'),
          },
        });
      },
    });
    assert.equal(captured.worktreeDirty, false);
    await assert.rejects(access(markerPath), (error) => error?.code === 'ENOENT');
  });
});

test('root audit rejects a linked-worktree git file before injected Git runs', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const gitPath = path.join(fixtureRoot, '.git');
    const retainedGitPath = path.join(fixtureRoot, '.git-retained');
    await rename(gitPath, retainedGitPath);
    await writeFile(gitPath, `gitdir: ../${SECRET}\n`, 'utf8');
    let gitCalls = 0;
    try {
      await assert.rejects(
        captureSourceState({
          ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
          rootGitRunner() {
            gitCalls += 1;
            throw new Error('root Git executed before filesystem audit');
          },
        }),
        (error) => (
          error?.code === 'ERR_SOURCE_GIT_UNSAFE'
          && /physical.*\.git|\.git.*directory/i.test(error.message)
          && !error.message.includes(SECRET)
        ),
      );
      assert.equal(gitCalls, 0);
    } finally {
      await rm(gitPath, { force: true });
      await rename(retainedGitPath, gitPath);
    }
  });
});

test('root audit rejects object alternates before injected Git runs', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const alternatesPath = path.join(
      fixtureRoot,
      '.git',
      'objects',
      'info',
      'alternates',
    );
    await writeFile(alternatesPath, `${fixtureRoot}\n`, 'utf8');
    let gitCalls = 0;
    await assert.rejects(
      captureSourceState({
        ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
        rootGitRunner() {
          gitCalls += 1;
          throw new Error('root Git executed before filesystem audit');
        },
      }),
      (error) => (
        error?.code === 'ERR_SOURCE_GIT_UNSAFE'
        && /alternate/i.test(error.message)
      ),
    );
    assert.equal(gitCalls, 0);
  });
});

test('root audit rejects a nested metadata junction without touching its target', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const infoPath = path.join(fixtureRoot, '.git', 'objects', 'info');
    const externalInfo = path.join(fixtureRoot, 'external-git-info');
    const sentinelPath = path.join(externalInfo, 'sentinel.txt');
    await rm(infoPath, { recursive: true, force: true });
    await mkdir(externalInfo, { recursive: true });
    await writeFile(sentinelPath, 'metadata sentinel\n', 'utf8');
    await symlink(externalInfo, infoPath, 'junction');
    let gitCalls = 0;
    try {
      await assert.rejects(
        captureSourceState({
          ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
          rootGitRunner() {
            gitCalls += 1;
            throw new Error('root Git executed before filesystem audit');
          },
        }),
        (error) => (
          error?.code === 'ERR_SOURCE_GIT_UNSAFE'
          && /physical|reparse|junction|link/i.test(error.message)
        ),
      );
      assert.equal(gitCalls, 0);
      assert.equal(await readFile(sentinelPath, 'utf8'), 'metadata sentinel\n');
    } finally {
      await unlink(infoPath);
    }
  });
});

for (const metadataName of ['index', 'HEAD']) {
  test(`root audit requires a physical local Git ${metadataName}`, async () => {
    await withRepository(async (fixtureRoot, engine) => {
      const metadataPath = path.join(fixtureRoot, '.git', metadataName);
      const retainedPath = path.join(fixtureRoot, '.git', `${metadataName}.retained`);
      const externalTarget = path.join(fixtureRoot, `external-${metadataName}`);
      const sentinelPath = path.join(externalTarget, 'sentinel.txt');
      await rename(metadataPath, retainedPath);
      await mkdir(externalTarget);
      await writeFile(sentinelPath, `${metadataName} sentinel\n`, 'utf8');
      await symlink(externalTarget, metadataPath, 'junction');
      let gitCalls = 0;
      try {
        await assert.rejects(
          captureSourceState({
            ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
            rootGitRunner() {
              gitCalls += 1;
              throw new Error('root Git executed before filesystem audit');
            },
          }),
          (error) => (
            error?.code === 'ERR_SOURCE_GIT_UNSAFE'
            && /physical|reparse|junction|link/i.test(error.message)
          ),
        );
        assert.equal(gitCalls, 0);
        assert.equal(
          await readFile(sentinelPath, 'utf8'),
          `${metadataName} sentinel\n`,
        );
      } finally {
        await unlink(metadataPath);
        await rename(retainedPath, metadataPath);
      }
    });
  });
}

for (const [name, relativePath, directory] of [
  ['HTTP object alternate', 'objects/info/http-alternates', false],
  ['graft', 'info/grafts', false],
  ['replace ref', 'refs/replace', true],
  ['shallow metadata', 'shallow', false],
  ['common-directory redirect', 'commondir', false],
  ['Git-directory redirect', 'gitdir', false],
]) {
  test(`root audit rejects ${name} before injected Git runs`, async () => {
    await withRepository(async (fixtureRoot, engine) => {
      const candidate = path.join(fixtureRoot, '.git', ...relativePath.split('/'));
      if (directory) {
        await mkdir(candidate, { recursive: true });
      } else {
        await mkdir(path.dirname(candidate), { recursive: true });
        await writeFile(candidate, `${SECRET}\n`, 'utf8');
      }
      await assertRootAuditBeforeGit(fixtureRoot, engine, new RegExp(name, 'i'));
    });
  });
}

for (const [name, relativePath] of [
  ['info attributes', '.git/info/attributes'],
  ['root attributes', '.gitattributes'],
  ['nested attributes', 'src/.gitattributes'],
]) {
  test(`root audit rejects ${name} that can alter relevant inspection`, async () => {
    await withRepository(async (fixtureRoot, engine) => {
      const candidate = path.join(fixtureRoot, ...relativePath.split('/'));
      await writeFile(candidate, `src/** filter=${SECRET}\n`, 'utf8');
      await assertRootAuditBeforeGit(fixtureRoot, engine, /attributes/i);
    });
  });
}

test('ordinary local origin branch user and core config remains accepted', async () => {
  await withRepository(async (fixtureRoot) => {
    const configPath = path.join(fixtureRoot, '.git', 'config');
    await appendFile(
      configPath,
      '\n[user]\n\tname = Local User\n\temail = local@example.invalid\n'
      + '[remote "origin"]\n\turl = https://github.com/example/project.git\n'
      + '\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
      + '[branch "main"]\n\tremote = origin\n\tmerge = refs/heads/main\n',
      'utf8',
    );
    await assert.doesNotReject(() => auditSourceGitMetadata(fixtureRoot));
  });
});

for (const indexFlag of ['assume-unchanged', 'skip-worktree']) {
  test(`${indexFlag} cannot conceal a modified relevant source file`, async () => {
    await withRepository(async (fixtureRoot, engine) => {
      const sourcePath = path.join(fixtureRoot, 'src', 'app.py');
      const original = await readFile(sourcePath, 'utf8');
      git(fixtureRoot, ['update-index', `--${indexFlag}`, 'src/app.py']);
      await writeFile(sourcePath, `${original}# concealed mutation\n`, 'utf8');
      try {
        await assert.rejects(
          captureSourceState(
            sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
          ),
          (error) => (
            error?.code === 'ERR_SOURCE_GIT_UNSAFE'
            && error.message.includes(indexFlag)
            && error.message.includes('src/app.py')
          ),
        );
      } finally {
        git(fixtureRoot, ['update-index', `--no-${indexFlag}`, 'src/app.py']);
      }
    });
  });
}

test('info exclude cannot hide an untracked relevant file from strict provenance', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const hiddenPath = path.join(fixtureRoot, 'src', 'hidden.py');
    await appendFile(
      path.join(fixtureRoot, '.git', 'info', 'exclude'),
      '\n/src/hidden.py\n',
      'utf8',
    );
    await writeFile(hiddenPath, 'HIDDEN = True\n', 'utf8');

    const captured = await captureSourceProvenance(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    assert.equal(captured.sourceState.worktreeDirty, true);
    assert.ok(captured.sourceState.files.some((entry) => (
      entry.path === 'src/hidden.py'
    )));
    assert.ok(captured.sourceState.status.some((entry) => (
      entry.code === '??' && entry.path === 'src/hidden.py'
    )));
    assert.match(captured.sourceDiff, /\+HIDDEN = True/);
    assert.throws(
      () => assertSourceStateAllowed(captured.sourceState),
      /src\/hidden\.py/,
    );
    assert.doesNotThrow(() => assertSourceStateAllowed(
      captured.sourceState,
      { allowDirty: true },
    ));
  });
});

test('declared .agents and output exclusions do not dirty relevant source', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const options = sourceOptions(fixtureRoot, engine.commit, engine.treeDigest);
    const clean = await captureSourceState(options);
    await Promise.all([
      mkdir(path.join(fixtureRoot, '.agents'), { recursive: true }),
      mkdir(path.join(fixtureRoot, 'output'), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(path.join(fixtureRoot, '.agents', 'local.txt'), SECRET, 'utf8'),
      writeFile(path.join(fixtureRoot, 'output', 'local.txt'), SECRET, 'utf8'),
    ]);

    const excluded = await captureSourceState(options);
    assert.equal(excluded.worktreeDirty, false);
    assert.equal(excluded.treeDigest, clean.treeDigest);
    assert.deepEqual(excluded.status, []);
  });
});

test('tracked and untracked diff paths both disable text conversion', async () => {
  const source = await readFile(
    new URL('../scripts/source-provenance.mjs', import.meta.url),
    'utf8',
  );
  assert.equal([...source.matchAll(/'--no-textconv'/g)].length, 2);
});

function portable(value) {
  return value.split(path.sep).join('/');
}

async function assertRootAuditBeforeGit(fixtureRoot, engine, pattern) {
  let gitCalls = 0;
  await assert.rejects(
    captureSourceState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      rootGitRunner() {
        gitCalls += 1;
        throw new Error('root Git executed before filesystem audit');
      },
    }),
    (error) => (
      error?.code === 'ERR_SOURCE_GIT_UNSAFE'
      && pattern.test(error.message)
      && !error.message.includes(SECRET)
    ),
  );
  assert.equal(gitCalls, 0);
}
