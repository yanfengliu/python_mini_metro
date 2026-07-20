import assert from 'node:assert/strict';
import {
  access,
  appendFile,
  copyFile,
  mkdir,
  readFile,
  realpath,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { runReadOnlyGit } from '../scripts/civ-engine-setup-process.mjs';
import {
  assertSourceStateAllowed,
  captureSourceState,
} from '../scripts/source-provenance.mjs';
import {
  assertCivEngineStateAllowed,
  assertCivEngineStateSummary,
  captureCivEngineState,
} from '../scripts/source-provenance-engine.mjs';
import {
  commit,
  copyProvenanceModules,
  git,
  normalize,
  runCopiedCapture,
  seedEngineRepository,
  sourceOptions,
  withRepository,
} from './source-provenance-fixtures.mjs';

test('a wrong physical engine root is non-overridable and fully attributable', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await writeFile(
      path.join(engine.root, 'package.json'),
      JSON.stringify({
        name: 'civ-engine',
        version: '9.9.9',
        type: 'module',
        exports: { '.': { import: './dist/index.js' } },
      }, null, 2),
      'utf8',
    );
    git(engine.root, ['add', 'package.json']);
    commit(engine.root, 'wrong version');
    const options = {
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      expectedEnginePackageRoot: path.join(fixtureRoot, '.civ-engine-pin'),
    };

    const changed = await captureSourceState(options);
    assert.equal(changed.engine.available, true);
    assert.equal(changed.engine.locationMatches, false);
    assert.equal(changed.engine.versionMatches, false);
    assert.equal(changed.engine.commitMatches, false);
    assert.equal(changed.engine.runtimeMatches, false);
    for (const allowDirty of [false, true]) {
      assert.throws(
        () => assertSourceStateAllowed(changed, { allowDirty }),
        (error) => (
          error?.code === 'ERR_CIV_ENGINE_PROVENANCE'
          && /resolved package root/.test(error.message)
          && /version 9\.9\.9 does not match 2\.2\.0/.test(error.message)
          && error.message.includes(changed.engine.gitCommit)
          && error.message.includes(engine.commit)
          && error.message.includes(changed.engine.treeDigest)
          && error.message.includes(engine.treeDigest)
        ),
      );
    }
    assert.throws(
      () => assertCivEngineStateAllowed(changed.engine.summary),
      /fresh civ-engine capture/i,
    );
    const forged = {
      ...changed.engine,
      expectedPackageRootPhysical: true,
      locationMatches: true,
    };
    assert.throws(
      () => assertCivEngineStateAllowed(forged, { allowDirty: true }),
      /fresh civ-engine capture/i,
    );
    assert.throws(() => {
      changed.engine.expectedPackageRootPhysical = true;
    }, TypeError);
    assert.throws(() => {
      changed.engine.locationMatches = true;
    }, TypeError);
    assert.throws(
      () => assertCivEngineStateAllowed(changed.engine, { allowDirty: true }),
      (error) => error?.code === 'ERR_CIV_ENGINE_PROVENANCE' && /cannot be overridden/.test(error.message),
    );
  });
});

test('the configured pin root must be a physical in-repo directory', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await symlink(engine.root, path.join(fixtureRoot, '.civ-engine-pin'), 'junction');
    const captured = await captureCivEngineState({
      repoRoot: fixtureRoot,
      enginePackageRoot: 'node_modules/civ-engine',
      expectedEngineCommit: engine.commit,
      expectedEngineTreeDigest: engine.treeDigest,
    });

    assert.equal(captured.available, true);
    assert.equal(captured.expectedPackageRootPhysical, false);
    assert.equal(captured.locationMatches, false);
    assert.equal(
      captured.localExpectedPackageRoot,
      normalize(path.join(fixtureRoot, '.civ-engine-pin')),
    );
    assert.equal(
      captured.localResolvedExpectedPackageRoot,
      normalize(await realpath(engine.root)),
    );
    for (const allowDirty of [false, true]) {
      assert.throws(
        () => assertCivEngineStateAllowed(captured, { allowDirty }),
        (error) => (
          error?.code === 'ERR_CIV_ENGINE_PROVENANCE'
          && /pinned root .* is not a physical in-repository directory/.test(error.message)
          && /cannot be overridden/.test(error.message)
        ),
      );
    }
  });
});

test('a top-level dist junction cannot escape the engine package root', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const externalDist = `${engine.root}-external-dist`;
    try {
      await mkdir(externalDist, { recursive: true });
      for (const fileName of ['index.js', 'state-digest.js']) {
        await copyFile(
          path.join(engine.root, 'dist', fileName),
          path.join(externalDist, fileName),
        );
      }
      await rm(path.join(engine.root, 'dist'), { recursive: true, force: true });
      await symlink(externalDist, path.join(engine.root, 'dist'), 'junction');

      const captured = await captureCivEngineState(
        sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      );
      assert.equal(captured.available, false);
      assert.equal(
        captured.error,
        'civ-engine runtime layout is unavailable or unsafe',
      );
      for (const allowDirty of [false, true]) {
        assert.throws(
          () => assertCivEngineStateAllowed(captured, { allowDirty }),
          /unavailable/i,
        );
      }
    } finally {
      await rm(externalDist, { recursive: true, force: true });
    }
  });
});

test('a resolved runtime entry mismatch is non-overridable', async () => {
  await withRepository(async (fixtureRoot) => {
    const expectedRoot = path.join(fixtureRoot, '.civ-engine-pin');
    await seedEngineRepository(expectedRoot);
    const packagePath = path.join(expectedRoot, 'package.json');
    const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
    packageDocument.exports['.'] = {
      node: './dist/alternate.js',
      import: './dist/index.js',
    };
    await Promise.all([
      writeFile(packagePath, JSON.stringify(packageDocument, null, 2), 'utf8'),
      writeFile(
        path.join(expectedRoot, 'dist', 'alternate.js'),
        'export const alternate = true;\n',
        'utf8',
      ),
    ]);
    git(expectedRoot, ['add', 'package.json', '-f', 'dist/alternate.js']);
    commit(expectedRoot, 'conditional runtime');
    await mkdir(path.join(fixtureRoot, 'scripts', 'node_modules'), { recursive: true });
    await symlink(
      expectedRoot,
      path.join(fixtureRoot, 'scripts', 'node_modules', 'civ-engine'),
      'junction',
    );
    await copyProvenanceModules(fixtureRoot);

    const { state: captured, policyErrors } = runCopiedCapture(fixtureRoot);
    assert.equal(captured.available, true, JSON.stringify(captured, null, 2));
    assert.equal(captured.locationMatches, true);
    assert.equal(captured.runtimeEntry, 'dist/index.js');
    assert.match(captured.localResolvedRuntimeEntry, /dist\/alternate\.js$/);
    assert.match(captured.localDeclaredRuntimeEntry, /dist\/index\.js$/);
    assert.equal(captured.runtimeEntryMatches, false);
    for (const error of policyErrors) {
      assert.equal(error.code, 'ERR_CIV_ENGINE_PROVENANCE');
      assert.match(error.message, /resolved runtime entry/);
      assert.match(error.message, /cannot be overridden/);
    }
  });
});

test('engine summary validation rejects dishonest match booleans', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const clean = await captureSourceState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    for (const key of ['versionMatches', 'commitMatches', 'runtimeMatches']) {
      const dishonest = structuredClone(clean.engine.summary);
      dishonest[key] = !dishonest[key];
      assert.throws(
        () => assertCivEngineStateSummary(dishonest),
        /invalid available civ-engine provenance summary/,
      );
    }
  });
});

test('default provenance follows nested ESM resolution and rejects its physical root', async () => {
  await withRepository(async (fixtureRoot) => {
    const decoyRoot = `${fixtureRoot}-decoy-engine`;
    try {
      const decoy = await seedEngineRepository(decoyRoot);
      await seedEngineRepository(path.join(fixtureRoot, '.civ-engine-pin'));
      const packagePath = path.join(decoy.root, 'package.json');
      const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
      packageDocument.version = '9.9.9';
      await writeFile(packagePath, JSON.stringify(packageDocument, null, 2), 'utf8');
      git(decoy.root, ['add', 'package.json']);
      commit(decoy.root, 'decoy version');

      await mkdir(path.join(fixtureRoot, 'scripts', 'node_modules'), {
        recursive: true,
      });
      await symlink(
        decoy.root,
        path.join(fixtureRoot, 'scripts', 'node_modules', 'civ-engine'),
        'junction',
      );
      await copyProvenanceModules(fixtureRoot);
      const { state: captured, policyErrors } = runCopiedCapture(fixtureRoot);

      assert.equal(captured.available, true, JSON.stringify(captured, null, 2));
      assert.equal(captured.packageVersion, '9.9.9');
      assert.equal(captured.locationMatches, false);
      assert.equal(
        captured.localResolvedPackageRoot,
        normalize(await realpath(decoy.root)),
      );
      assert.equal(
        captured.localExpectedPackageRoot,
        normalize(path.join(fixtureRoot, '.civ-engine-pin')),
      );
      for (const error of policyErrors) {
        assert.equal(error.code, 'ERR_CIV_ENGINE_PROVENANCE');
        assert.match(error.message, /resolved package root/);
      }
    } finally {
      await rm(decoyRoot, { recursive: true, force: true });
    }
  });
});

test('engine provenance rejects a local filter before its sentinel can execute', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const markerPath = path.join(fixtureRoot, 'pin-filter-ran.txt');
    const probePath = path.join(fixtureRoot, 'pin-filter-probe.mjs');
    const secret = 'PIN_FILTER_SECRET_MUST_NOT_LEAK';
    await writeFile(
      probePath,
      `import { writeFileSync } from 'node:fs';\nwriteFileSync(${JSON.stringify(markerPath)}, ${JSON.stringify(secret)});\n`,
      'utf8',
    );
    await Promise.all([
      appendFile(
        path.join(engine.root, '.git', 'config'),
        `\n[filter "probe"]\n\tclean = node ${normalize(probePath)} ${secret}\n`,
        'utf8',
      ),
      writeFile(path.join(engine.root, '.gitattributes'), '* filter=probe\n', 'utf8'),
    ]);

    const captured = await captureCivEngineState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    assert.equal(captured.available, false);
    assert.equal(captured.error, 'civ-engine Git metadata is unsafe');
    assert.doesNotMatch(captured.error, new RegExp(secret));
    await assert.rejects(access(markerPath), (error) => error?.code === 'ENOENT');
  });
});

test('engine provenance re-audits local config before every Git call', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const secret = 'PIN_REAUDIT_SECRET_MUST_NOT_LEAK';
    let gitCalls = 0;
    const captured = await captureCivEngineState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      async engineGitRunner({ args }) {
        gitCalls += 1;
        assert.equal(args[0], 'status');
        await appendFile(
          path.join(engine.root, '.git', 'config'),
          `\n[filter "probe"]\n\tprocess = ${secret}\n`,
          'utf8',
        );
        return '';
      },
    });

    assert.equal(gitCalls, 1);
    assert.equal(captured.available, false);
    assert.equal(captured.error, 'civ-engine Git metadata is unsafe');
    assert.doesNotMatch(captured.error, new RegExp(secret));
  });
});

test('engine provenance re-audits active info excludes before every Git call', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const secret = 'PIN_EXCLUDE_SECRET_4C21';
    await writeFile(path.join(engine.root, `${secret}.txt`), 'concealed\n', 'utf8');
    let gitCalls = 0;
    const captured = await captureCivEngineState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      async engineGitRunner(options) {
        gitCalls += 1;
        assert.equal(options.args[0], 'status');
        await appendFile(
          path.join(engine.root, '.git', 'info', 'exclude'),
          `\n/${secret}.txt\n`,
          'utf8',
        );
        return runReadOnlyGit(options);
      },
    });
    assert.equal(gitCalls, 1);
    assert.equal(captured.available, false);
    assert.equal(captured.error, 'civ-engine Git metadata is unsafe');
    assert.doesNotMatch(captured.error, new RegExp(secret));
  });
});

test('engine Git failures and unavailable summaries never reflect config values', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const secret = 'PIN_CONFIG_SECRET_3A52';
    await appendFile(
      path.join(engine.root, '.git', 'config'),
      `\n[core]\n\trepositoryFormatVersion = 1\n`
      + `[extensions]\n\tobjectFormat = ${secret}\n`,
      'utf8',
    );
    const captured = await captureCivEngineState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    assert.equal(captured.available, false);
    assert.match(captured.error, /^civ-engine Git inspection failed \(\d+\)$/);
    assert.doesNotMatch(captured.error, new RegExp(secret));
  });
});

for (const [name, relativePath] of [
  ['worktree attributes', '.gitattributes'],
  ['info attributes', '.git/info/attributes'],
]) {
  test(`engine provenance rejects behavior-changing ${name} before Git`, async () => {
    await withRepository(async (fixtureRoot, engine) => {
      const secret = 'PIN_ATTRIBUTE_SECRET_7F4D';
      await Promise.all([
        writeFile(
          path.join(engine.root, ...relativePath.split('/')),
          `* filter=${secret}\n`,
          'utf8',
        ),
        appendFile(
          path.join(engine.root, '.git', 'config'),
          `\n[filter "${secret}"]\n\trequired = true\n`,
          'utf8',
        ),
      ]);
      let gitCalls = 0;
      const captured = await captureCivEngineState({
        ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
        engineGitRunner() {
          gitCalls += 1;
          throw new Error(`pin Git reflected ${secret}`);
        },
      });
      assert.equal(gitCalls, 0);
      assert.equal(captured.available, false);
      assert.equal(captured.error, 'civ-engine Git metadata is unsafe');
      assert.doesNotMatch(captured.error, new RegExp(secret));
    });
  });
}

test('engine provenance permits only the fixed root text attribute policy', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    await writeFile(
      path.join(engine.root, '.gitattributes'),
      '* text=auto\n',
      'utf8',
    );
    const captured = await captureCivEngineState(
      sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
    );
    assert.equal(captured.available, true, captured.error);
    assert.equal(captured.worktreeDirty, true);
  });
});

test('engine unavailable summaries categorize arbitrary runner errors', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const secret = 'PIN_RUNNER_SECRET_A614';
    const captured = await captureCivEngineState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      engineGitRunner() {
        throw new Error(`attacker path and ${secret}`);
      },
    });
    assert.equal(captured.available, false);
    assert.equal(captured.error, 'civ-engine Git inspection failed');
    assert.doesNotMatch(captured.error, new RegExp(secret));
  });
});

test('engine Git ignores repo-derived and ambient HOME/XDG config and attributes', async () => {
  await withRepository(async (fixtureRoot, engine) => {
    const homePath = path.join(engine.root, '.git-read-home');
    const xdgPath = path.join(engine.root, '.ambient-xdg');
    const markerPath = path.join(fixtureRoot, 'pin-global-filter-ran.txt');
    const probePath = path.join(fixtureRoot, 'pin-global-filter-probe.mjs');
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
        `[filter "probe"]\n\tclean = node ${normalize(probePath)}\n`,
        'utf8',
      ),
    ]);
    await writeFile(
      path.join(homePath, 'gitconfig'),
      `[filter "probe"]\n\tclean = node ${normalize(probePath)}\n`,
      'utf8',
    );

    const captured = await captureCivEngineState({
      ...sourceOptions(fixtureRoot, engine.commit, engine.treeDigest),
      engineGitRunner(options) {
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
    assert.equal(captured.available, true, captured.error);
    await assert.rejects(access(markerPath), (error) => error?.code === 'ENOENT');
  });
});
