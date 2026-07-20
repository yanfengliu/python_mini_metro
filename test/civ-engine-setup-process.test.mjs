import assert from 'node:assert/strict';
import {
  mkdir,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  buildSetupEnvironment,
  planGitInvocation,
  planNpmInvocation,
  resolveTrustedNpmExecutable,
} from '../scripts/civ-engine-setup-process.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('child environment is an allowlist and carries no caller credentials', () => {
  const sentinel = 'must-not-reach-child';
  const environment = buildSetupEnvironment({
    platform: 'win32',
    sourceEnv: {
      PATH: `caller-path-${sentinel}`,
      SystemRoot: 'C:\\Windows',
      PATHEXT: '.EXE;.CMD',
      ComSpec: `C:\\attacker-${sentinel}\\cmd.exe`,
      AWS_ACCESS_KEY_ID: sentinel,
      GOOGLE_APPLICATION_CREDENTIALS: sentinel,
      GITHUB_TOKEN: sentinel,
      NODE_AUTH_TOKEN: sentinel,
      NODE_OPTIONS: `--require=${sentinel}`,
      SSH_AUTH_SOCK: sentinel,
      HTTPS_PROXY: `https://user:${sentinel}@proxy.invalid`,
      npm_config_registry: `https://${sentinel}.invalid`,
      npm_lifecycle_event: sentinel,
      HOME: `C:\\ambient-home-${sentinel}`,
      USERPROFILE: `C:\\ambient-profile-${sentinel}`,
      XDG_CONFIG_HOME: `C:\\ambient-xdg-${sentinel}`,
      GIT_DIR: sentinel,
      GIT_ATTR_NOSYSTEM: sentinel,
      GIT_CONFIG_GLOBAL: sentinel,
      GIT_CONFIG_COUNT: '1',
    },
    homePath: 'C:\\controlled\\home',
    tempPath: 'C:\\controlled\\temp',
    npmUserConfigPath: 'C:\\controlled\\npm-user.ini',
    npmGlobalConfigPath: 'C:\\controlled\\npm-global.ini',
    pathValue: 'C:\\trusted-bin',
  });

  assert.equal(environment.HOME, 'C:\\controlled\\home');
  assert.equal(environment.USERPROFILE, 'C:\\controlled\\home');
  assert.equal(environment.TEMP, 'C:\\controlled\\temp');
  assert.equal(environment.TMP, 'C:\\controlled\\temp');
  assert.equal(environment.PATH, 'C:\\trusted-bin');
  assert.equal(Object.hasOwn(environment, 'PATHEXT'), false);
  assert.equal(environment.SystemRoot, 'C:\\Windows');
  assert.equal(environment.npm_config_userconfig, 'C:\\controlled\\npm-user.ini');
  assert.equal(environment.npm_config_globalconfig, 'C:\\controlled\\npm-global.ini');
  assert.equal(environment.GIT_ATTR_NOSYSTEM, '1');
  assert.equal(environment.GIT_CONFIG_GLOBAL, 'C:\\controlled\\home\\gitconfig');
  assert.equal(environment.GIT_CONFIG_NOSYSTEM, '1');
  assert.equal(environment.GIT_TERMINAL_PROMPT, '0');
  assert.equal(environment.GIT_OPTIONAL_LOCKS, '0');
  assert.equal(JSON.stringify(environment).includes(sentinel), false);

  const allowed = new Set([
    'GCM_INTERACTIVE',
    'GIT_ATTR_NOSYSTEM',
    'GIT_CONFIG_GLOBAL',
    'GIT_CONFIG_NOSYSTEM',
    'GIT_NO_REPLACE_OBJECTS',
    'GIT_OPTIONAL_LOCKS',
    'GIT_TERMINAL_PROMPT',
    'HOME',
    'PATH',
    'SystemRoot',
    'TEMP',
    'TMP',
    'TMPDIR',
    'USERPROFILE',
    'npm_config_cache',
    'npm_config_globalconfig',
    'npm_config_userconfig',
  ]);
  for (const key of Object.keys(environment)) {
    assert.equal(allowed.has(key), true, `unexpected child environment key: ${key}`);
  }
});

test('child environment derives default paths from the selected platform', () => {
  const windowsEnvironment = buildSetupEnvironment({
    platform: 'win32',
    homePath: 'C:\\controlled\\home',
    tempPath: 'C:\\controlled\\temp',
  });
  assert.equal(
    windowsEnvironment.GIT_CONFIG_GLOBAL,
    'C:\\controlled\\home\\gitconfig',
  );
  assert.equal(
    windowsEnvironment.npm_config_userconfig,
    'C:\\controlled\\home\\npm-user.ini',
  );
  assert.equal(
    windowsEnvironment.npm_config_globalconfig,
    'C:\\controlled\\home\\npm-global.ini',
  );
  assert.equal(
    windowsEnvironment.npm_config_cache,
    'C:\\controlled\\temp\\npm-cache',
  );

  const posixEnvironment = buildSetupEnvironment({
    platform: 'linux',
    homePath: '/controlled/home',
    tempPath: '/controlled/temp',
  });
  assert.equal(posixEnvironment.GIT_CONFIG_GLOBAL, '/controlled/home/gitconfig');
  assert.equal(posixEnvironment.npm_config_userconfig, '/controlled/home/npm-user.ini');
  assert.equal(posixEnvironment.npm_config_globalconfig, '/controlled/home/npm-global.ini');
  assert.equal(posixEnvironment.npm_config_cache, '/controlled/temp/npm-cache');
});

test('Git planner derives isolated home paths from the selected platform', () => {
  const windowsPlan = planGitInvocation({
    gitExecutable: process.execPath,
    repoRoot: process.cwd(),
    args: ['status'],
    homeDir: 'C:\\controlled\\home',
    tempDir: 'C:\\controlled\\temp',
    platform: 'win32',
  });
  assert.equal(
    windowsPlan.options.env.GIT_CONFIG_GLOBAL,
    'C:\\controlled\\home\\gitconfig',
  );
  assert.equal(
    windowsPlan.args.find((argument) => argument.startsWith('core.hooksPath=')),
    'core.hooksPath=C:/controlled/home/hooks-disabled',
  );

  const posixPlan = planGitInvocation({
    gitExecutable: process.execPath,
    repoRoot: process.cwd(),
    args: ['status'],
    homeDir: '/controlled/home',
    tempDir: '/controlled/temp',
    platform: 'linux',
  });
  assert.equal(
    posixPlan.options.env.GIT_CONFIG_GLOBAL,
    '/controlled/home/gitconfig',
  );
  assert.equal(
    posixPlan.args.find((argument) => argument.startsWith('core.hooksPath=')),
    'core.hooksPath=/controlled/home/hooks-disabled',
  );
});

test('default read-only Git plan uses no repository-derived config surface', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const nullDevice = process.platform === 'win32' ? 'NUL' : '/dev/null';
    const plan = planGitInvocation({
      gitExecutable: process.execPath,
      repoRoot: fixtureRoot,
      args: ['status', '--porcelain=v1'],
      inheritedEnv: {
        HOME: 'ambient-home-secret',
        USERPROFILE: 'ambient-profile-secret',
        XDG_CONFIG_HOME: 'ambient-xdg-secret',
        GIT_CONFIG_GLOBAL: 'ambient-global-secret',
      },
    });
    assert.equal(plan.options.env.HOME, nullDevice);
    assert.equal(plan.options.env.USERPROFILE, nullDevice);
    assert.equal(plan.options.env.GIT_CONFIG_GLOBAL, nullDevice);
    assert.equal(plan.options.env.GIT_ATTR_NOSYSTEM, '1');
    assert.equal(Object.hasOwn(plan.options.env, 'XDG_CONFIG_HOME'), false);
    assert.match(plan.args.join('\0'), new RegExp(
      `core\\.hooksPath=${nullDevice.replace('\\', '\\\\')}`,
    ));
    assert.doesNotMatch(JSON.stringify(plan), /\.git-read-home/);
    assert.doesNotMatch(JSON.stringify(plan), /ambient-(?:home|profile|xdg|global)-secret/);
  });
});

test('npm invocation is shell-free with fixed options on POSIX', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const distributionRoot = path.join(fixtureRoot, 'node-distribution');
    const nodePath = path.join(distributionRoot, 'bin', 'node');
    const npmPath = path.join(
      distributionRoot,
      'lib',
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    await Promise.all([
      mkdir(path.dirname(nodePath), { recursive: true }),
      mkdir(path.dirname(npmPath), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(nodePath, 'fixture node', 'utf8'),
      writeFile(npmPath, 'fixture npm CLI', 'utf8'),
    ]);
    const environment = { HOME: path.join(fixtureRoot, 'home') };
    const plan = await planNpmInvocation({
      platform: 'linux',
      execPath: nodePath,
      npmExecutablePath: npmPath,
      npmArgs: ['ci', '--ignore-scripts'],
      cwd: fixtureRoot,
      env: environment,
    });

    assert.equal(plan.command, nodePath);
    assert.deepEqual(plan.args, [npmPath, 'ci', '--ignore-scripts']);
    assert.equal(plan.options.cwd, fixtureRoot);
    assert.equal(plan.options.env, environment);
    assert.equal(plan.options.shell, false);
    assert.equal(plan.options.windowsHide, true);
    assert.deepEqual(plan.options.stdio, ['ignore', 'pipe', 'pipe']);
  });
});

test('Windows npm uses the physical npm CLI beside the real Node executable', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const distribution = path.join(fixtureRoot, 'node-distribution');
    const nodePath = path.join(distribution, 'node.exe');
    const npmCliPath = path.join(
      distribution,
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    await mkdir(path.dirname(npmCliPath), { recursive: true });
    await Promise.all([
      writeFile(nodePath, 'fixture node', 'utf8'),
      writeFile(npmCliPath, 'fixture npm cli', 'utf8'),
    ]);

    const plan = await planNpmInvocation({
      platform: 'win32',
      execPath: nodePath,
      npmArgs: ['ci', '--omit=dev', '--ignore-scripts'],
      cwd: fixtureRoot,
      env: { HOME: fixtureRoot },
    });
    assert.equal(plan.command, nodePath);
    assert.deepEqual(plan.args, [
      npmCliPath,
      'ci',
      '--omit=dev',
      '--ignore-scripts',
    ]);
    assert.equal(plan.options.shell, false);
    assert.equal(plan.command.endsWith('npm.cmd'), false);
    assert.equal(plan.command.toLowerCase().includes('cmd.exe'), false);

    const outside = path.join(fixtureRoot, 'outside-npm-cli.js');
    await writeFile(outside, 'substituted npm cli', 'utf8');
    await assert.rejects(
      planNpmInvocation({
        platform: 'win32',
        execPath: nodePath,
        npmCliPath: outside,
        npmArgs: ['ci'],
        cwd: fixtureRoot,
        env: {},
      }),
      (error) => error?.code === 'ERR_CIV_ENGINE_NPM_IDENTITY',
    );
  });
});

test(
  'POSIX setup-node npm symlink resolves only to the physical distribution CLI',
  { skip: process.platform === 'win32' },
  async () => {
    await withSetupRepository(async (fixtureRoot) => {
      const distributionRoot = path.join(fixtureRoot, 'node-distribution');
      const nodePath = path.join(distributionRoot, 'bin', 'node');
      const launcherPath = path.join(distributionRoot, 'bin', 'npm');
      const npmCliPath = path.join(
        distributionRoot,
        'lib',
        'node_modules',
        'npm',
        'bin',
        'npm-cli.js',
      );
      await Promise.all([
        mkdir(path.dirname(nodePath), { recursive: true }),
        mkdir(path.dirname(npmCliPath), { recursive: true }),
      ]);
      await Promise.all([
        writeFile(nodePath, 'fixture node'),
        writeFile(npmCliPath, 'fixture npm CLI'),
      ]);
      await symlink('../lib/node_modules/npm/bin/npm-cli.js', launcherPath, 'file');

      assert.equal(
        await resolveTrustedNpmExecutable({ platform: 'linux', execPath: nodePath }),
        launcherPath,
      );
      const plan = await planNpmInvocation({
        platform: 'linux',
        execPath: nodePath,
        npmExecutablePath: launcherPath,
        npmArgs: ['ci'],
        cwd: fixtureRoot,
        env: {},
      });
      assert.equal(plan.command, nodePath);
      assert.deepEqual(plan.args, [npmCliPath, 'ci']);
    });
  },
);
