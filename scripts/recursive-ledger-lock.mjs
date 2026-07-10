import { randomUUID } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

const LOCK_DIRECTORY = '.ledger-lock';
const OWNER_FILE = 'owner.json';
const DEFAULT_WAIT_TIMEOUT_MS = 30_000;
const DEFAULT_STALE_AFTER_MS = 300_000;
const DEFAULT_HEARTBEAT_INTERVAL_MS = 30_000;
const DEFAULT_RETRY_DELAY_MS = 25;

export async function withLedgerLock(outputRoot, callback, options = {}) {
  const settings = normalizeLockOptions(options);
  await fs.mkdir(outputRoot, { recursive: true });
  const lockDirectory = path.join(outputRoot, LOCK_DIRECTORY);
  const ownerPath = path.join(lockDirectory, OWNER_FILE);
  const token = options.token ?? randomUUID();
  const owner = {
    schemaVersion: 1,
    pid: options.pid ?? process.pid,
    token,
    acquiredAt: new Date(settings.now()).toISOString(),
  };
  const deadline = settings.now() + settings.waitTimeoutMs;

  while (true) {
    try {
      await createLockDirectory(lockDirectory, ownerPath, owner);
      break;
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      const observed = await inspectLock(lockDirectory, ownerPath);
      if (!observed) continue;
      const stale = settings.now() - observed.heartbeatMs > settings.staleAfterMs;
      if (stale && !(await ownerIsAlive(observed.owner, settings))) {
        if (await retireStaleLock(lockDirectory, observed, settings)) continue;
      }
      if (settings.now() >= deadline) {
        throw new Error('timed out waiting for ledger lock');
      }
      await settings.sleep(settings.retryDelayMs);
    }
  }

  let heartbeatError = null;
  let heartbeatTail = Promise.resolve();
  const heartbeat = () => {
    const operation = heartbeatTail.then(async () => {
      if (!(await ownsLock(ownerPath, token))) {
        throw new Error('lost ledger lock ownership');
      }
      const timestamp = new Date(settings.now());
      await fs.utimes(ownerPath, timestamp, timestamp);
    });
    heartbeatTail = operation.catch((error) => {
      heartbeatError ??= error;
    });
    return operation;
  };
  const cancelHeartbeat = settings.scheduleHeartbeat(
    heartbeat,
    settings.heartbeatIntervalMs,
  );

  let result;
  let callbackError = null;
  try {
    result = await callback({ token, pid: owner.pid, heartbeat });
  } catch (error) {
    callbackError = error;
  }
  cancelHeartbeat();
  await heartbeatTail;
  const retainedOwnership = await ownsLock(ownerPath, token);
  await releaseLock(lockDirectory, ownerPath, token);

  if (callbackError) throw callbackError;
  if (heartbeatError || !retainedOwnership) {
    throw heartbeatError ?? new Error('lost ledger lock ownership');
  }
  return result;
}

function normalizeLockOptions(options) {
  const staleAfterMs = options.staleAfterMs ?? DEFAULT_STALE_AFTER_MS;
  const heartbeatIntervalMs = options.heartbeatIntervalMs
    ?? Math.min(DEFAULT_HEARTBEAT_INTERVAL_MS, Math.max(1, staleAfterMs / 3));
  const settings = {
    heartbeatIntervalMs,
    isProcessAlive: options.isProcessAlive ?? defaultIsProcessAlive,
    now: options.now ?? Date.now,
    retryDelayMs: options.retryDelayMs ?? DEFAULT_RETRY_DELAY_MS,
    scheduleHeartbeat: options.scheduleHeartbeat ?? defaultScheduleHeartbeat,
    sleep: options.sleep ?? defaultSleep,
    staleAfterMs,
    waitTimeoutMs: options.waitTimeoutMs ?? DEFAULT_WAIT_TIMEOUT_MS,
  };
  for (const key of [
    'heartbeatIntervalMs',
    'retryDelayMs',
    'staleAfterMs',
    'waitTimeoutMs',
  ]) {
    if (!Number.isFinite(settings[key]) || settings[key] < 0) {
      throw new TypeError(`ledger lock ${key} must be non-negative`);
    }
  }
  return settings;
}

async function createLockDirectory(lockDirectory, ownerPath, owner) {
  await fs.mkdir(lockDirectory);
  try {
    const handle = await fs.open(ownerPath, 'wx');
    try {
      await handle.writeFile(`${JSON.stringify(owner)}\n`, 'utf8');
      await handle.sync();
    } finally {
      await handle.close();
    }
  } catch (error) {
    await fs.rm(lockDirectory, { recursive: true, force: true });
    throw error;
  }
}

async function inspectLock(lockDirectory, ownerPath) {
  let directoryStat;
  try {
    directoryStat = await fs.stat(lockDirectory);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
  try {
    const [text, ownerStat] = await Promise.all([
      fs.readFile(ownerPath, 'utf8'),
      fs.stat(ownerPath),
    ]);
    return { owner: JSON.parse(text), heartbeatMs: ownerStat.mtimeMs };
  } catch (error) {
    if (error?.code !== 'ENOENT' && !(error instanceof SyntaxError)) throw error;
    return { owner: null, heartbeatMs: directoryStat.mtimeMs };
  }
}

async function ownerIsAlive(owner, settings) {
  if (!Number.isSafeInteger(owner?.pid) || owner.pid <= 0) return false;
  return Boolean(await settings.isProcessAlive(owner.pid));
}

async function retireStaleLock(lockDirectory, observed, settings) {
  const ownerPath = path.join(lockDirectory, OWNER_FILE);
  const current = await inspectLock(lockDirectory, ownerPath);
  if (!current) return false;
  if (!sameLockIdentity(current, observed)) return false;
  if (settings.now() - current.heartbeatMs <= settings.staleAfterMs) return false;
  if (await ownerIsAlive(current.owner, settings)) return false;

  const retired = `${lockDirectory}.stale-${randomUUID()}`;
  try {
    await fs.rename(lockDirectory, retired);
  } catch (error) {
    if (error?.code === 'ENOENT' || error?.code === 'EEXIST') return false;
    throw error;
  }
  const moved = await inspectLock(retired, path.join(retired, OWNER_FILE));
  if (!moved) return false;
  if (!sameLockIdentity(moved, observed)) {
    await fs.rename(retired, lockDirectory).catch(() => {});
    return false;
  }
  await fs.rm(retired, { recursive: true, force: true });
  return true;
}

function sameLockIdentity(left, right) {
  if (typeof left.owner?.token === 'string' || typeof right.owner?.token === 'string') {
    return left.owner?.token === right.owner?.token;
  }
  return left.heartbeatMs === right.heartbeatMs;
}

async function ownsLock(ownerPath, token) {
  try {
    const owner = JSON.parse(await fs.readFile(ownerPath, 'utf8'));
    return owner?.token === token;
  } catch (error) {
    if (error?.code === 'ENOENT' || error instanceof SyntaxError) return false;
    throw error;
  }
}

async function releaseLock(lockDirectory, ownerPath, token) {
  if (!(await ownsLock(ownerPath, token))) return false;
  try {
    await fs.unlink(ownerPath);
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
  try {
    await fs.rmdir(lockDirectory);
  } catch (error) {
    if (error?.code === 'ENOENT') return true;
    if (error?.code === 'ENOTEMPTY' || error?.code === 'EEXIST') return false;
    throw error;
  }
  return true;
}

function defaultIsProcessAlive(pid) {
  if (pid === process.pid) return true;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (error?.code === 'ESRCH') return false;
    return true;
  }
}

function defaultScheduleHeartbeat(callback, intervalMs) {
  const interval = setInterval(() => {
    callback().catch(() => {});
  }, intervalMs);
  interval.unref?.();
  return () => clearInterval(interval);
}

function defaultSleep(delayMs) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, delayMs));
}
