import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const MAX_OUTPUT_BYTES = 1024 * 1024;

export function buildSetupEnvironment({
  platform = process.platform,
  sourceEnv = process.env,
  homePath,
  tempPath,
  gitGlobalConfigPath = platformPath(platform).join(homePath, 'gitconfig'),
  npmUserConfigPath = platformPath(platform).join(homePath, 'npm-user.ini'),
  npmGlobalConfigPath = platformPath(platform).join(homePath, 'npm-global.ini'),
  pathValue = '',
  gitCeilingDirectories,
}) {
  const environment = {
    HOME: homePath,
    USERPROFILE: homePath,
    TEMP: tempPath,
    TMP: tempPath,
    TMPDIR: tempPath,
    PATH: pathValue,
    npm_config_userconfig: npmUserConfigPath,
    npm_config_globalconfig: npmGlobalConfigPath,
    npm_config_cache: platformPath(platform).join(tempPath, 'npm-cache'),
    GIT_ATTR_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: gitGlobalConfigPath,
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_TERMINAL_PROMPT: '0',
    GIT_OPTIONAL_LOCKS: '0',
    GIT_NO_REPLACE_OBJECTS: '1',
    GCM_INTERACTIVE: 'Never',
  };
  if (platform === 'win32') {
    if (sourceEnv.SystemRoot) environment.SystemRoot = sourceEnv.SystemRoot;
  }
  if (gitCeilingDirectories !== undefined) {
    environment.GIT_CEILING_DIRECTORIES = gitCeilingDirectories;
  }
  return environment;
}

export function planGitInvocation({
  gitExecutable,
  repoRoot,
  args,
  inheritedEnv = process.env,
  homeDir,
  tempDir = inheritedEnv.TEMP ?? inheritedEnv.TMP ?? repoRoot,
  platform = process.platform,
  gitCeilingDirectories,
}) {
  const command = gitExecutable ?? resolveTrustedGitExecutable();
  const safeRoot = portable(path.resolve(repoRoot));
  const nullDevice = platform === 'win32' ? 'NUL' : '/dev/null';
  const isolatedHome = homeDir ?? nullDevice;
  const selectedPath = platformPath(platform);
  const gitGlobalConfigPath = homeDir
    ? selectedPath.join(homeDir, 'gitconfig')
    : nullDevice;
  const hooksPath = homeDir
    ? selectedPath.join(homeDir, 'hooks-disabled')
    : nullDevice;
  const environment = buildSetupEnvironment({
    platform,
    sourceEnv: inheritedEnv,
    homePath: isolatedHome,
    tempPath: tempDir,
    gitGlobalConfigPath,
    pathValue: path.isAbsolute(command)
      ? path.dirname(command)
      : inheritedEnv.PATH ?? '',
    ...(gitCeilingDirectories !== undefined ? { gitCeilingDirectories } : {}),
  });
  delete environment.npm_config_userconfig;
  delete environment.npm_config_globalconfig;
  delete environment.npm_config_cache;
  return {
    command,
    args: [
      '--no-optional-locks',
      '-c',
      `safe.directory=${safeRoot}`,
      '-c',
      'core.fsmonitor=false',
      '-c',
      `core.hooksPath=${portable(hooksPath, selectedPath)}`,
      '-c',
      'credential.helper=',
      '-c',
      'diff.external=',
      '-c',
      'protocol.ext.allow=never',
      ...args,
    ],
    options: {
      cwd: path.resolve(repoRoot),
      env: environment,
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  };
}

export function runReadOnlyGit({
  repoRoot,
  args,
  allowedStatuses = [0],
  gitExecutable,
  inheritedEnv = process.env,
  homeDir,
  tempDir,
}) {
  const plan = planGitInvocation({
    gitExecutable,
    repoRoot,
    args,
    inheritedEnv,
    ...(homeDir ? { homeDir } : {}),
    ...(tempDir ? { tempDir } : {}),
  });
  const result = spawnSync(plan.command, plan.args, {
    ...plan.options,
    encoding: 'utf8',
    maxBuffer: MAX_OUTPUT_BYTES,
  });
  if (result.error || !allowedStatuses.includes(result.status)) {
    throw categoricalProcessFailure('Git read', result);
  }
  return result.stdout ?? '';
}

export function resolveTrustedGitExecutable({ candidatePaths } = {}) {
  const candidates = candidatePaths ?? trustedGitCandidates(process.platform);
  for (const candidate of candidates) {
    const resolved = path.resolve(candidate);
    try {
      const metadata = fs.lstatSync(resolved);
      const physical = fs.realpathSync(resolved);
      if (
        metadata.isFile()
        && !metadata.isSymbolicLink()
        && samePath(resolved, physical)
      ) {
        return resolved;
      }
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
  }
  throw Object.assign(new Error('trusted Git executable is unavailable'), {
    code: 'ERR_CIV_ENGINE_GIT_IDENTITY',
  });
}

export async function resolveTrustedNpmExecutable({
  platform = process.platform,
  execPath = process.execPath,
} = {}) {
  await assertPhysicalFile(execPath, 'Node executable');
  if (platform === 'win32') {
    const npmCliPath = path.join(
      path.dirname(path.resolve(execPath)),
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    await assertPhysicalFile(npmCliPath, 'npm CLI');
    return npmCliPath;
  }
  const distributionRoot = path.resolve(path.dirname(execPath), '..');
  const npmCliPath = path.join(
    distributionRoot,
    'lib',
    'node_modules',
    'npm',
    'bin',
    'npm-cli.js',
  );
  await assertPhysicalFile(npmCliPath, 'npm CLI');
  const npmLauncherPath = path.join(distributionRoot, 'bin', 'npm');
  if (!fs.existsSync(npmLauncherPath)) return npmCliPath;
  const launcherTarget = await resolveFileTarget(npmLauncherPath, 'npm launcher');
  if (!samePath(launcherTarget, npmCliPath)) {
    throw identityError('npm launcher does not target the Node distribution npm CLI');
  }
  return npmLauncherPath;
}

export async function planNpmInvocation({
  platform = process.platform,
  execPath = process.execPath,
  npmExecutablePath,
  npmCliPath,
  npmArgs,
  cwd,
  env,
}) {
  let command;
  let args;
  if (platform === 'win32') {
    await assertPhysicalFile(execPath, 'Node executable');
    const expectedCli = path.join(
      path.dirname(path.resolve(execPath)),
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    if (npmCliPath !== undefined && !samePath(npmCliPath, expectedCli)) {
      throw identityError('npm CLI must belong to the Node distribution');
    }
    await assertPhysicalFile(expectedCli, 'npm CLI');
    command = path.resolve(execPath);
    args = [expectedCli, ...npmArgs];
  } else {
    if (!npmExecutablePath) {
      throw identityError('validated npm executable is required');
    }
    await assertPhysicalFile(execPath, 'Node executable');
    const distributionRoot = path.resolve(path.dirname(execPath), '..');
    const expectedCli = path.join(
      distributionRoot,
      'lib',
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    const allowedLauncher = path.join(distributionRoot, 'bin', 'npm');
    const candidate = path.resolve(npmExecutablePath);
    if (!samePath(candidate, expectedCli) && !samePath(candidate, allowedLauncher)) {
      throw identityError('npm executable must belong to the Node distribution');
    }
    await assertPhysicalFile(expectedCli, 'npm CLI');
    const npmTarget = await resolveFileTarget(candidate, 'npm executable');
    if (!samePath(npmTarget, expectedCli)) {
      throw identityError('npm executable does not target the Node distribution npm CLI');
    }
    command = path.resolve(execPath);
    args = [expectedCli, ...npmArgs];
  }
  return {
    command,
    args,
    options: {
      cwd: path.resolve(cwd),
      env,
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  };
}

export function runSetupProcess(plan, {
  phase = 'setup subprocess',
  allowedStatuses = [0],
} = {}) {
  const result = spawnSync(plan.command, plan.args, {
    ...plan.options,
    encoding: 'utf8',
    maxBuffer: MAX_OUTPUT_BYTES,
  });
  if (result.error || !allowedStatuses.includes(result.status)) {
    throw processFailure(phase, result);
  }
  return {
    status: result.status,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
  };
}

async function assertPhysicalFile(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.promises.lstat(resolved),
      fs.promises.realpath(resolved),
    ]);
  } catch {
    throw identityError(`${label} is unavailable`);
  }
  if (
    !metadata.isFile()
    || metadata.isSymbolicLink()
    || !samePath(resolved, physical)
  ) {
    throw identityError(`${label} must be a physical file`);
  }
}

async function resolveFileTarget(candidate, label) {
  const resolved = path.resolve(candidate);
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.promises.lstat(resolved),
      fs.promises.realpath(resolved),
    ]);
  } catch {
    throw identityError(`${label} is unavailable`);
  }
  if (!metadata.isFile() && !metadata.isSymbolicLink()) {
    throw identityError(`${label} must be a file or authenticated file link`);
  }
  await assertPhysicalFile(physical, `${label} target`);
  return physical;
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function trustedGitCandidates(platform) {
  if (platform === 'win32') {
    return [
      'C:\\Program Files\\Git\\cmd\\git.exe',
      'C:\\Program Files\\Git\\bin\\git.exe',
      'C:\\Program Files (x86)\\Git\\cmd\\git.exe',
    ];
  }
  return ['/usr/bin/git', '/usr/local/bin/git', '/opt/homebrew/bin/git'];
}

function portable(value, pathImplementation = path) {
  return value.split(pathImplementation.sep).join('/');
}

function platformPath(platform) {
  return platform === 'win32' ? path.win32 : path.posix;
}

function identityError(message) {
  return Object.assign(new Error(message), {
    code: 'ERR_CIV_ENGINE_NPM_IDENTITY',
  });
}

function processFailure(phase, result) {
  const status = result?.status ?? 'spawn-error';
  const detail = redact(result?.stderr || result?.stdout || result?.error?.message || '');
  return Object.assign(
    new Error(`${phase} failed (${status})${detail ? `: ${detail}` : ''}`),
    { code: 'ERR_CIV_ENGINE_SETUP_PROCESS', status: result?.status ?? null },
  );
}

function categoricalProcessFailure(phase, result) {
  const status = result?.status ?? 'spawn-error';
  return Object.assign(new Error(`${phase} failed (${status})`), {
    code: 'ERR_CIV_ENGINE_SETUP_PROCESS',
    status: result?.status ?? null,
  });
}

function redact(value) {
  return String(value)
    .replace(/https?:\/\/[^\s/@:]+:[^\s/@]+@/gi, 'https://[redacted]@')
    .replace(/(token|password|secret|authorization)\s*[:=]\s*\S+/gi, '$1=[redacted]')
    .trim()
    .slice(0, 4096);
}
