import { spawn as nodeSpawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  acquireCivEngineVerificationLease,
  releaseCivEngineVerificationLease,
  verifyCivEngineSetupUnderLease,
} from './civ-engine-setup.mjs';
import { assertCleanNodeStartup } from './node-startup-contract.mjs';
import { parseRecursiveArgs } from './recursive-args.mjs';

const modulePath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(modulePath), '..');

const PUBLIC_COMMANDS = new Map([
  ['test', () => ['--test']],
  ['playtest:verify', (args) => ['scripts/playtest-verify.mjs', ...args]],
  ['playtest:recursive', (args) => ['scripts/playtest-recursive.mjs', ...args]],
]);

function defaultAcquire() {
  return acquireCivEngineVerificationLease({ repoRoot });
}

function defaultVerify({ allowDirty, lease }) {
  return verifyCivEngineSetupUnderLease({ allowDirty, lease, repoRoot });
}

function defaultRelease(lease) {
  return releaseCivEngineVerificationLease(lease);
}

function spawnPublicNode({ command, args, cwd, shell }) {
  return new Promise((resolve, reject) => {
    const child = nodeSpawn(command, args, {
      cwd,
      shell,
      stdio: 'inherit',
      windowsHide: true,
    });

    child.once('error', reject);
    child.once('exit', (exitCode, signal) => {
      resolve({ exitCode, signal });
    });
  });
}

export async function runGuardEntryPoint({
  argv,
  nodeOptions = process.env.NODE_OPTIONS,
  execArgv = process.execArgv,
  dispatch = dispatchPublicNodeCommand,
} = {}) {
  assertCleanNodeStartup({ nodeOptions, execArgv });
  return dispatch({ argv });
}

export async function dispatchPublicNodeCommand({
  argv,
  acquire = defaultAcquire,
  verify = defaultVerify,
  spawn = spawnPublicNode,
  release = defaultRelease,
}) {
  if (!Array.isArray(argv) || typeof argv[0] !== 'string') {
    throw new TypeError('unknown public Node command');
  }

  const [publicCommand, ...forwardedArgs] = argv;
  const buildArgs = PUBLIC_COMMANDS.get(publicCommand);
  if (buildArgs === undefined) {
    throw new Error('unknown public Node command');
  }
  if (publicCommand === 'test' && forwardedArgs.length > 0) {
    throw Object.assign(
      new Error('public test command accepts no arguments'),
      { code: 'ERR_CIV_ENGINE_GUARD_TEST_ARGS' },
    );
  }

  const allowDirty = publicCommand === 'playtest:recursive'
    ? parseRecursiveArgs(forwardedArgs).allowDirty === true
    : false;
  const lease = await acquire({ repoRoot });
  let primaryFailed = false;
  let primaryError;
  try {
    await verify({ allowDirty, lease });
    return await spawn({
      command: process.execPath,
      args: buildArgs(forwardedArgs),
      cwd: repoRoot,
      shell: false,
    });
  } catch (error) {
    primaryFailed = true;
    primaryError = error;
    throw error;
  } finally {
    try {
      await release(lease);
    } catch (releaseError) {
      if (!primaryFailed) throw releaseError;
      const aggregate = new AggregateError(
        [primaryError, releaseError],
        'guarded Node command failed and verification lease recovery was incomplete',
        { cause: primaryError },
      );
      aggregate.code = primaryError?.code ?? 'ERR_CIV_ENGINE_GUARD_RECOVERY';
      throw aggregate;
    }
  }
}

async function main() {
  try {
    const result = await runGuardEntryPoint({ argv: process.argv.slice(2) });
    if (result.signal !== null) {
      try {
        process.kill(process.pid, result.signal);
      } catch {
        process.exitCode = 1;
      }
      return;
    }
    process.exitCode = Number.isInteger(result.exitCode) ? result.exitCode : 1;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[civ-engine-guard] ${message}`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === modulePath) {
  await main();
}
