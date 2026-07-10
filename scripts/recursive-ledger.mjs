import { randomUUID } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';

import { withLedgerLock } from './recursive-ledger-lock.mjs';

export { withLedgerLock } from './recursive-ledger-lock.mjs';

export function createRecursiveLedger({
  assertCompleteManifest,
  assertArtifactFilesExist,
}) {
  if (
    typeof assertCompleteManifest !== 'function'
    || typeof assertArtifactFilesExist !== 'function'
  ) {
    throw new TypeError('recursive ledger requires manifest and artifact validators');
  }

  async function validateManifest(manifest, repoRoot, options = {}) {
    assertCompleteManifest(manifest);
    await assertArtifactFilesExist(manifest, repoRoot, options);
  }

  async function appendValidatedManifestRow(
    filePath,
    manifest,
    { repoRoot = process.cwd(), lockOptions = {} } = {},
  ) {
    await validateManifest(manifest, repoRoot);
    return withLedgerLock(path.dirname(filePath), async () => {
      const current = await loadLedger(filePath, repoRoot, validateManifest);
      const existing = current.byId.get(manifest.id);
      if (existing) {
        assertSameManifest(existing, manifest, filePath);
        return current.rows;
      }

      await appendRowsDurably(filePath, [manifest]);
      const persisted = await readBackLedger(filePath);
      assertSameManifest(persisted.byId.get(manifest.id), manifest, filePath);
      return persisted.rows;
    }, lockOptions);
  }

  async function appendManifestPair({
    outputRoot,
    runManifest,
    passManifest,
    repoRoot = process.cwd(),
    lockOptions = {},
  }) {
    await createManifestPairIntent({
      outputRoot,
      runManifest,
      passManifest,
      repoRoot,
    });
    await reconcileManifestPairIntents({ outputRoot, repoRoot, lockOptions });
  }

  async function persistManifestPair({
    outputRoot,
    runManifest,
    passManifest,
    runManifestPath,
    passManifestPath,
    repoRoot = process.cwd(),
    lockOptions = {},
    onBoundary,
  }) {
    const targets = {
      runManifestPath: repoRelativeTarget(repoRoot, runManifestPath),
      passManifestPath: repoRelativeTarget(repoRoot, passManifestPath),
    };
    if (targets.runManifestPath === targets.passManifestPath) {
      throw new Error('run/pass manifest targets must be distinct');
    }
    const baseId = manifestPairBaseId(runManifest, passManifest);
    await validateManifest(runManifest, repoRoot, {
      allowMissingPaths: Object.values(targets),
    });
    await validateManifest(passManifest, repoRoot, {
      allowMissingPaths: Object.values(targets),
    });
    const intent = {
      schemaVersion: 2,
      baseId,
      targets,
      runManifest,
      passManifest,
    };
    await writeManifestPairIntent(outputRoot, intent);
    await callBoundary(onBoundary, 'intent', intent);
    await reconcileManifestPairIntents({
      outputRoot,
      repoRoot,
      lockOptions,
      onBoundary,
    });
  }

  async function createManifestPairIntent({
    outputRoot,
    runManifest,
    passManifest,
    repoRoot = process.cwd(),
  }) {
    const baseId = manifestPairBaseId(runManifest, passManifest);
    await validateManifest(runManifest, repoRoot);
    await validateManifest(passManifest, repoRoot);
    return writeManifestPairIntent(outputRoot, {
      schemaVersion: 1,
      baseId,
      runManifest,
      passManifest,
    });
  }

  async function reconcileManifestPairIntents({
    outputRoot,
    repoRoot = process.cwd(),
    lockOptions = {},
    onBoundary,
  }) {
    return withLedgerLock(outputRoot, async () => {
      const intents = await readManifestPairIntents(
        outputRoot,
        repoRoot,
        validateManifest,
      );
      if (intents.length === 0) return 0;

      for (const entry of intents) {
        if (!entry.targets) continue;
        await persistManifestFile(
          entry.targets.runManifestPath,
          entry.intent.runManifest,
          repoRoot,
          validateManifest,
        );
        await callBoundary(onBoundary, 'run-manifest', entry.intent);
      }
      for (const entry of intents) {
        if (!entry.targets) continue;
        await persistManifestFile(
          entry.targets.passManifestPath,
          entry.intent.passManifest,
          repoRoot,
          validateManifest,
        );
        await callBoundary(onBoundary, 'pass-manifest', entry.intent);
      }

      const runPath = path.join(outputRoot, 'ledger.jsonl');
      const passPath = path.join(outputRoot, 'passes.jsonl');
      const runs = await loadLedger(runPath, repoRoot, validateManifest, {
        repairUnterminatedTail: true,
      });
      const passes = await loadLedger(passPath, repoRoot, validateManifest, {
        repairUnterminatedTail: true,
      });
      const missingRuns = [];
      const missingPasses = [];

      for (const { intent } of intents) {
        collectMissingManifest(runs.byId, missingRuns, intent.runManifest, runPath);
        collectMissingManifest(
          passes.byId,
          missingPasses,
          intent.passManifest,
          passPath,
        );
      }

      await appendRowsDurably(runPath, missingRuns);
      await callBoundary(onBoundary, 'run-row');
      await appendRowsDurably(passPath, missingPasses);
      await callBoundary(onBoundary, 'pass-row');

      const confirmedRuns = await readBackLedger(runPath);
      const confirmedPasses = await readBackLedger(passPath);
      for (const entry of intents) {
        const { intent } = entry;
        assertSameManifest(
          confirmedRuns.byId.get(intent.runManifest.id),
          intent.runManifest,
          runPath,
        );
        assertSameManifest(
          confirmedPasses.byId.get(intent.passManifest.id),
          intent.passManifest,
          passPath,
        );
        if (entry.targets) {
          await confirmManifestFile(
            entry.targets.runManifestPath,
            intent.runManifest,
            repoRoot,
            validateManifest,
          );
          await confirmManifestFile(
            entry.targets.passManifestPath,
            intent.passManifest,
            repoRoot,
            validateManifest,
          );
        }
      }

      for (const { intentPath } of intents) await fs.unlink(intentPath);
      return intents.length;
    }, lockOptions);
  }

  return {
    appendManifestPair,
    appendValidatedManifestRow,
    createManifestPairIntent,
    persistManifestPair,
    reconcileManifestPairIntents,
  };
}

async function writeManifestPairIntent(outputRoot, intent) {
  const directory = path.join(outputRoot, 'ledger-intents');
  await fs.mkdir(directory, { recursive: true });
  const intentPath = path.join(directory, `${intent.baseId}.json`);
  await writeJsonNoReplace(intentPath, intent, `manifest-pair intent conflict for ${intent.baseId}`);
  return intentPath;
}

async function readManifestPairIntents(outputRoot, repoRoot, validateManifest) {
  const directory = path.join(outputRoot, 'ledger-intents');
  await fs.mkdir(directory, { recursive: true });
  const names = (await fs.readdir(directory))
    .filter((name) => name.endsWith('.json'))
    .sort();
  const intents = [];
  for (const name of names) {
    const intentPath = path.join(directory, name);
    const intent = JSON.parse(await fs.readFile(intentPath, 'utf8'));
    if (
      ![1, 2].includes(intent.schemaVersion)
      || intent.baseId !== name.slice(0, -5)
      || manifestPairBaseId(intent.runManifest, intent.passManifest) !== intent.baseId
    ) {
      throw new Error(`invalid manifest-pair intent: ${name}`);
    }
    let targets = null;
    if (intent.schemaVersion === 2) {
      targets = validateIntentTargets(intent.targets, repoRoot, name);
      await validateManifest(intent.runManifest, repoRoot, {
        allowMissingPaths: Object.values(intent.targets),
      });
      await validateManifest(intent.passManifest, repoRoot, {
        allowMissingPaths: Object.values(intent.targets),
      });
    } else {
      await validateManifest(intent.runManifest, repoRoot);
      await validateManifest(intent.passManifest, repoRoot);
    }
    intents.push({ intent, intentPath, targets });
  }
  return intents;
}

function validateIntentTargets(targets, repoRoot, name) {
  if (
    !targets
    || typeof targets !== 'object'
    || Array.isArray(targets)
    || Object.keys(targets).sort().join(',') !== 'passManifestPath,runManifestPath'
  ) {
    throw new Error(`invalid manifest-pair intent targets: ${name}`);
  }
  const resolved = {
    runManifestPath: resolveIntentTarget(repoRoot, targets.runManifestPath),
    passManifestPath: resolveIntentTarget(repoRoot, targets.passManifestPath),
  };
  if (resolved.runManifestPath === resolved.passManifestPath) {
    throw new Error(`invalid manifest-pair intent targets: ${name}`);
  }
  return resolved;
}

async function persistManifestFile(
  filePath,
  manifest,
  repoRoot,
  validateManifest,
) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await writeJsonNoReplace(
    filePath,
    manifest,
    `manifest file conflict for ${manifest.id}: ${filePath}`,
  );
  await confirmManifestFile(filePath, manifest, repoRoot, validateManifest);
}

async function confirmManifestFile(
  filePath,
  expected,
  repoRoot,
  validateManifest,
) {
  const persisted = JSON.parse(await fs.readFile(filePath, 'utf8'));
  if (!isDeepStrictEqual(persisted, expected)) {
    throw new Error(`manifest file conflict for ${expected.id}: ${filePath}`);
  }
  await validateManifest(persisted, repoRoot);
}

async function writeJsonNoReplace(filePath, value, conflictMessage) {
  const directory = path.dirname(filePath);
  await fs.mkdir(directory, { recursive: true });
  const tempPath = path.join(
    directory,
    `.${path.basename(filePath)}.${process.pid}.${randomUUID()}.tmp`,
  );
  const handle = await fs.open(tempPath, 'wx');
  try {
    try {
      await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, 'utf8');
      await handle.sync();
    } finally {
      await handle.close();
    }
    try {
      await fs.link(tempPath, filePath);
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      const existing = JSON.parse(await fs.readFile(filePath, 'utf8'));
      if (!isDeepStrictEqual(existing, value)) throw new Error(conflictMessage);
    }
  } finally {
    await fs.unlink(tempPath).catch(() => {});
  }
}

async function loadLedger(
  filePath,
  repoRoot,
  validateManifest,
  { repairUnterminatedTail = false } = {},
) {
  const rows = await readLedgerRows(filePath, { repairUnterminatedTail });
  for (const row of rows) await validateManifest(row, repoRoot);
  return indexLedgerRows(rows);
}

async function readBackLedger(filePath) {
  return indexLedgerRows(await readLedgerRows(filePath));
}

function indexLedgerRows(rows) {
  const byId = new Map();
  for (const row of rows) {
    if (byId.has(row.id)) throw new Error(`duplicate ledger manifest ${row.id}`);
    byId.set(row.id, row);
  }
  return { rows, byId };
}

async function readLedgerRows(filePath, { repairUnterminatedTail = false } = {}) {
  let bytes;
  try {
    bytes = await fs.readFile(filePath);
  } catch (error) {
    if (error?.code === 'ENOENT') return [];
    throw error;
  }
  if (bytes.length === 0 || bytes.at(-1) === 0x0a) {
    return parseLedgerRows(bytes.toString('utf8'));
  }
  if (!repairUnterminatedTail) {
    throw new Error(`unterminated JSONL tail: ${filePath}`);
  }
  const prefixLength = bytes.lastIndexOf(0x0a) + 1;
  const prefix = bytes.subarray(0, prefixLength);
  const rows = parseLedgerRows(prefix.toString('utf8'));
  const handle = await fs.open(filePath, 'r+');
  try {
    await handle.truncate(prefixLength);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return rows;
}

function parseLedgerRows(text) {
  return text.split(/\r?\n/).filter(Boolean).map((row) => JSON.parse(row));
}

function collectMissingManifest(byId, missing, manifest, filePath) {
  const existing = byId.get(manifest.id);
  if (existing) {
    assertSameManifest(existing, manifest, filePath);
    return;
  }
  byId.set(manifest.id, manifest);
  missing.push(manifest);
}

function assertSameManifest(persisted, expected, filePath) {
  if (!persisted || !isDeepStrictEqual(persisted, expected)) {
    throw new Error(`ledger manifest conflict for ${expected.id}: ${filePath}`);
  }
}

async function appendRowsDurably(filePath, rows) {
  if (rows.length === 0) return;
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const handle = await fs.open(filePath, 'a');
  try {
    await handle.writeFile(
      rows.map((row) => `${JSON.stringify(row)}\n`).join(''),
      'utf8',
    );
    await handle.sync();
  } finally {
    await handle.close();
  }
}

function repoRelativeTarget(repoRoot, absolutePath) {
  if (typeof absolutePath !== 'string' || absolutePath.length === 0) {
    throw new Error('manifest target path is required');
  }
  const root = path.resolve(repoRoot);
  const target = path.resolve(absolutePath);
  const relative = path.relative(root, target);
  if (
    relative.length === 0
    || relative === '..'
    || relative.startsWith(`..${path.sep}`)
    || path.isAbsolute(relative)
  ) {
    throw new Error(`manifest target is outside repository: ${absolutePath}`);
  }
  return relative.split(path.sep).join('/');
}

function resolveIntentTarget(repoRoot, relativePath) {
  if (
    typeof relativePath !== 'string'
    || relativePath.length === 0
    || path.isAbsolute(relativePath)
    || relativePath.includes('\\')
    || relativePath.split('/').includes('..')
    || path.posix.normalize(relativePath) !== relativePath
  ) {
    throw new Error(`invalid manifest intent target: ${relativePath}`);
  }
  const resolved = path.resolve(repoRoot, ...relativePath.split('/'));
  if (repoRelativeTarget(repoRoot, resolved) !== relativePath) {
    throw new Error(`invalid manifest intent target: ${relativePath}`);
  }
  return resolved;
}

async function callBoundary(onBoundary, stage, intent) {
  if (onBoundary !== undefined && typeof onBoundary !== 'function') {
    throw new TypeError('onBoundary must be a function');
  }
  await onBoundary?.(stage, intent);
}

function manifestPairBaseId(runManifest, passManifest) {
  const runBase = runManifest?.id?.replace(/-run$/, '');
  const passBase = passManifest?.id?.replace(/-pass$/, '');
  if (
    !runBase
    || runBase === runManifest.id
    || runBase !== passBase
    || !/^[A-Za-z0-9._-]+$/.test(runBase)
  ) {
    throw new Error('run/pass manifests must share a safe base id');
  }
  return runBase;
}
