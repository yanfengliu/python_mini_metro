import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  appendFile,
  copyFile,
  mkdir,
  readdir,
  readFile,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { CIV_ENGINE_PIN } from '../scripts/civ-engine-pin.mjs';
import {
  buildPin,
  installPinDependencies,
  installRootDependency,
  resolveTrustedGitExecutable,
  resolveTrustedNpmExecutable,
  validateRepositoryContract,
} from '../scripts/civ-engine-setup-operations.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';
import {
  commit,
  git,
  seedEngineRepository,
} from './source-provenance-fixtures.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SETUP_MODULES = [
  'civ-engine-pin.mjs',
  'civ-engine-runtime.mjs',
  'civ-engine-setup-build.mjs',
  'civ-engine-setup-clone.mjs',
  'civ-engine-setup-content.mjs',
  'civ-engine-setup-git-config.mjs',
  'civ-engine-setup-process.mjs',
  'civ-engine-setup-promotion.mjs',
  'civ-engine-setup-root-contract.mjs',
  'civ-engine-setup-safety.mjs',
  'civ-engine-setup-operations.mjs',
  'civ-engine-setup.mjs',
  'node-startup-contract.mjs',
  'source-provenance-engine.mjs',
  'source-provenance-engine-safety.mjs',
  'source-provenance-git-safety.mjs',
];

test('root repair creates only the exact descriptor link without invoking npm', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    const rootSlot = path.join(fixtureRoot, 'node_modules', 'civ-engine');
    await mkdir(pinRoot);
    await writeFile(path.join(pinRoot, 'package.json'), JSON.stringify({
      name: 'civ-engine',
      version: CIV_ENGINE_PIN.version,
    }));
    await installRootDependency({ repoRoot: fixtureRoot, pinRoot, pin });
    assert.doesNotMatch(installRootDependency.toString(), /npm|runProcess|planNpm/i);
    assert.equal(await fsRealpath(rootSlot), await fsRealpath(pinRoot));
    assert.deepEqual(await readdir(path.dirname(rootSlot)), ['civ-engine']);
  });
});

test('root exact-link repair refuses a stale link and preserves its target', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    const nodeModulesRoot = path.join(fixtureRoot, 'node_modules');
    const rootSlot = path.join(nodeModulesRoot, 'civ-engine');
    const externalTarget = path.join(fixtureRoot, 'external-stale-engine');
    const sentinel = path.join(externalTarget, 'sentinel.txt');
    await Promise.all([
      mkdir(pinRoot),
      mkdir(externalTarget),
      mkdir(nodeModulesRoot),
    ]);
    await Promise.all([
      writeFile(path.join(pinRoot, 'package.json'), JSON.stringify({
        name: 'civ-engine',
        version: CIV_ENGINE_PIN.version,
      })),
      writeFile(sentinel, 'external target must survive\n'),
      writeFile(path.join(nodeModulesRoot, '.package-lock.json'), '{}\n'),
    ]);
    await symlink(
      externalTarget,
      rootSlot,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    await assert.rejects(
      installRootDependency({ repoRoot: fixtureRoot, pinRoot, pin }),
      /existing|stale|replace|already/i,
    );
    assert.equal(await readFile(sentinel, 'utf8'), 'external target must survive\n');
    assert.equal(await fsRealpath(rootSlot), await fsRealpath(externalTarget));
  });
});

test('root exact-link repair refuses a physical stale slot without touching its contents', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    const rootSlot = path.join(fixtureRoot, 'node_modules', 'civ-engine');
    const sentinel = path.join(rootSlot, 'sentinel.txt');
    await Promise.all([
      mkdir(pinRoot),
      mkdir(rootSlot, { recursive: true }),
    ]);
    await writeFile(sentinel, 'physical slot must survive\n');
    await assert.rejects(
      installRootDependency({
        repoRoot: fixtureRoot,
        pinRoot,
        pin,
      }),
      /physical.*slot|slot.*link/i,
    );
    assert.equal(await readFile(sentinel, 'utf8'), 'physical slot must survive\n');
  });
});

test('root exact-link repair preserves every unexpected node_modules entry', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const pinRoot = path.join(fixtureRoot, '.civ-engine-pin');
    const nodeModulesRoot = path.join(fixtureRoot, 'node_modules');
    const rootSlot = path.join(nodeModulesRoot, 'civ-engine');
    const sentinel = path.join(nodeModulesRoot, 'unexpected', 'sentinel.txt');
    await Promise.all([
      mkdir(pinRoot),
      mkdir(path.dirname(sentinel), { recursive: true }),
    ]);
    await writeFile(sentinel, 'unexpected entry must survive\n');
    await assert.rejects(
      installRootDependency({ repoRoot: fixtureRoot, pinRoot, pin }),
      /unexpected.*entry/i,
    );
    assert.equal(await pathExistsForTest(rootSlot), false);
    assert.equal(await readFile(sentinel, 'utf8'), 'unexpected entry must survive\n');
  });
});

test('root contract rejects every unsupported install-affecting package field', async (t) => {
  for (const [field, value] of [
    ['workspaces', ['packages/*']],
    ['optionalDependencies', { hostile: 'https://example.invalid/hostile.tgz' }],
    ['peerDependencies', { hostile: '*' }],
    ['devDependencies', { hostile: '1.0.0' }],
    ['bundledDependencies', ['hostile']],
    ['overrides', { hostile: 'https://example.invalid/hostile.tgz' }],
  ]) {
    await t.test(field, async () => {
      await withSetupRepository(async (fixtureRoot, { pin }) => {
        const packagePath = path.join(fixtureRoot, 'package.json');
        const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
        packageDocument[field] = value;
        await writeFile(packagePath, JSON.stringify(packageDocument, null, 2));
        await assert.rejects(
          validateRepositoryContract({ repoRoot: fixtureRoot, pin }),
          /contract|install|package/i,
        );
      });
    });
  }
});

test('root link creation rejects contract drift before filesystem mutation', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    await validateRepositoryContract({ repoRoot: fixtureRoot, pin });
    const lockPath = path.join(fixtureRoot, 'package-lock.json');
    const lockDocument = JSON.parse(await readFile(lockPath, 'utf8'));
    lockDocument.packages['node_modules/hostile'] = {
      version: '1.0.0',
      resolved: 'https://example.invalid/hostile.tgz',
      integrity: 'sha512-hostile',
    };
    await writeFile(lockPath, JSON.stringify(lockDocument, null, 2));
    const rootSlot = path.join(fixtureRoot, 'node_modules', CIV_ENGINE_PIN.packageName);
    await assert.rejects(
      installRootDependency({
        repoRoot: fixtureRoot,
        pinRoot: path.join(fixtureRoot, '.civ-engine-pin'),
        pin,
      }),
      /lock|graph|contract|non-dev/i,
    );
    assert.equal(await pathExistsForTest(rootSlot), false);
  });
});

test('root contract rejects an unattached dev-only lock entry', async () => {
  await withSetupRepository(async (fixtureRoot, { pin }) => {
    const lockPath = path.join(fixtureRoot, 'package-lock.json');
    const lockDocument = JSON.parse(await readFile(lockPath, 'utf8'));
    lockDocument.packages['node_modules/unattached-hostile-dev'] = {
      version: '1.0.0',
      resolved: 'https://example.invalid/unattached-hostile-dev.tgz',
      integrity: 'sha512-hostile',
      dev: true,
    };
    await writeFile(lockPath, JSON.stringify(lockDocument, null, 2));
    await assert.rejects(
      validateRepositoryContract({ repoRoot: fixtureRoot, pin }),
      /lock|graph|digest|contract/i,
    );
  });
});

test('every npm phase revalidates generated trees before planning or launch', async () => {
  for (const [operation, unsafeTree] of [
    [installPinDependencies, 'node_modules'],
    [buildPin, 'dist'],
  ]) {
    await withSetupRepository(async (fixtureRoot) => {
      const checkoutRoot = path.join(fixtureRoot, 'checkout');
      const externalRoot = path.join(fixtureRoot, 'external');
      const nestedRoot = path.join(checkoutRoot, unsafeTree, 'nested');
      await Promise.all([
        mkdir(nestedRoot, { recursive: true }),
        mkdir(externalRoot),
      ]);
      await symlink(
        externalRoot,
        path.join(nestedRoot, 'escape'),
        process.platform === 'win32' ? 'junction' : 'dir',
      );
      let planned = false;
      let launched = false;
      await assert.rejects(operation({
        checkoutRoot,
        transaction: {},
        planNpm: async () => { planned = true; },
        runProcess: () => { launched = true; },
      }), /physical|link|junction|reparse/i);
      assert.equal(planned, false);
      assert.equal(launched, false);
    });
  }
});

test('setup executable identity is independent of an attacker-controlled PATH', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const trustedGit = path.join(fixtureRoot, 'trusted', 'git.exe');
    const attackerGit = path.join(fixtureRoot, 'attacker', 'git.exe');
    const nodePath = path.join(fixtureRoot, 'node-distribution', 'bin', 'node');
    const npmCli = path.join(
      fixtureRoot,
      'node-distribution',
      'lib',
      'node_modules',
      'npm',
      'bin',
      'npm-cli.js',
    );
    await Promise.all([
      mkdir(path.dirname(trustedGit), { recursive: true }),
      mkdir(path.dirname(attackerGit), { recursive: true }),
      mkdir(path.dirname(nodePath), { recursive: true }),
      mkdir(path.dirname(npmCli), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(trustedGit, 'trusted git'),
      writeFile(attackerGit, 'attacker git'),
      writeFile(nodePath, 'trusted node'),
      writeFile(npmCli, 'trusted npm cli'),
    ]);
    assert.equal(
      await resolveTrustedGitExecutable({ candidatePaths: [trustedGit] }),
      trustedGit,
    );
    assert.equal(
      await resolveTrustedNpmExecutable({ platform: 'linux', execPath: nodePath }),
      npmCli,
    );
    const source = await readFile(
      path.join(repoRoot, 'scripts', 'civ-engine-setup-operations.mjs'),
      'utf8',
    );
    assert.doesNotMatch(source, /process\.env\.PATH\b|split\(path\.delimiter\)/);
    assert.doesNotMatch(source, /findPhysicalExecutable/);
    assert.match(source, /fs\.lstat\(candidate, \{ bigint: true \}\)/);
  });
});

test('real verify-only canary attributes content mismatches while strict rejects them', async () => {
  await withVerificationRepository(async ({ fixtureRoot, pinRoot }) => {
    const readmePath = path.join(pinRoot, 'README.md');
    await appendFile(readmePath, 'dirty status\n');
    assert.equal(runCopiedVerification(fixtureRoot, false).ok, false);
    assert.equal(runCopiedVerification(fixtureRoot, true).ok, true);
    git(pinRoot, ['checkout', '--', 'README.md']);

    await writeFile(path.join(pinRoot, 'dist', 'index.js'), 'export const changed = true;\n');
    assert.equal(runCopiedVerification(fixtureRoot, false).ok, false);
    assert.equal(runCopiedVerification(fixtureRoot, true).ok, true);

    await writeFile(path.join(pinRoot, 'dist', 'index.js'), 'export { stateDigest } from "./state-digest.js";\n');
    const packagePath = path.join(pinRoot, 'package.json');
    const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
    packageDocument.version = '2.2.1';
    await writeFile(packagePath, JSON.stringify(packageDocument, null, 2));
    assert.equal(runCopiedVerification(fixtureRoot, false).ok, false);
    assert.equal(runCopiedVerification(fixtureRoot, true).ok, true);
    git(pinRoot, ['checkout', '--', 'package.json']);

    await appendFile(readmePath, 'new detached commit\n');
    git(pinRoot, ['add', 'README.md']);
    commit(pinRoot, 'canary commit mismatch');
    assert.equal(runCopiedVerification(fixtureRoot, false).ok, false);
    assert.equal(runCopiedVerification(fixtureRoot, true).ok, true);
  });
});

test('strict verification rejects and preserves a foreign root dependency entry', async () => {
  await withVerificationRepository(async ({ fixtureRoot }) => {
    const sentinel = path.join(fixtureRoot, 'node_modules', 'unexpected', 'sentinel.txt');
    await mkdir(path.dirname(sentinel));
    await writeFile(sentinel, 'foreign entry must survive\n');
    const result = runCopiedVerification(fixtureRoot, false);
    assert.equal(result.ok, false);
    assert.match(result.message, /unexpected.*entry/i);
    assert.equal(await readFile(sentinel, 'utf8'), 'foreign entry must survive\n');
  });
});

test('real verify-only canary still rejects attached and runtime-identity states', async () => {
  await withVerificationRepository(async ({ fixtureRoot, pinRoot, pin }) => {
    git(pinRoot, ['remote', 'set-url', 'origin', 'https://example.invalid/civ-engine.git']);
    let result = runCopiedVerification(fixtureRoot, true);
    assert.equal(result.ok, false);
    assert.match(result.message, /origin|remote/i);
    git(pinRoot, ['remote', 'set-url', 'origin', CIV_ENGINE_PIN.repositoryUrl]);

    git(pinRoot, ['checkout', '-b', 'unsafe-attached', pin.commit]);
    result = runCopiedVerification(fixtureRoot, true);
    assert.equal(result.ok, false);
    assert.match(result.message, /detached/i);
    git(pinRoot, ['checkout', '--detach', pin.commit]);

    const packagePath = path.join(pinRoot, 'package.json');
    const packageDocument = JSON.parse(await readFile(packagePath, 'utf8'));
    packageDocument.exports['.'] = {
      node: './dist/alternate.js',
      import: './dist/index.js',
    };
    await Promise.all([
      writeFile(packagePath, JSON.stringify(packageDocument, null, 2)),
      writeFile(path.join(pinRoot, 'dist', 'alternate.js'), 'export const alternate = true;\n'),
    ]);
    result = runCopiedVerification(fixtureRoot, true);
    assert.equal(result.ok, false);
    assert.match(result.message, /runtime entry|runtime identity/i);

    git(pinRoot, ['checkout', '--', 'package.json']);
    await rm(path.join(pinRoot, 'dist'), { recursive: true });
    result = runCopiedVerification(fixtureRoot, true);
    assert.equal(result.ok, false);
    assert.match(result.message, /unavailable|missing/i);

    await mkdir(path.join(pinRoot, 'dist'));
    await Promise.all([
      writeFile(
        path.join(pinRoot, 'dist', 'index.js'),
        'export { stateDigest } from "./state-digest.js";\n',
      ),
      writeFile(
        path.join(pinRoot, 'dist', 'state-digest.js'),
        'export const stateDigest = JSON.stringify;\n',
      ),
    ]);

    const decoyRoot = path.join(fixtureRoot, 'decoy-engine');
    await seedEngineRepository(decoyRoot);
    const rootSlot = path.join(fixtureRoot, 'node_modules', 'civ-engine');
    await rm(rootSlot, { recursive: true });
    await symlink(
      decoyRoot,
      rootSlot,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    result = runCopiedVerification(fixtureRoot, true);
    assert.equal(result.ok, false);
    assert.match(result.message, /resolution|dependency|pinned root/i);
  });
});

async function withVerificationRepository(callback) {
  await withSetupRepository(async (fixtureRoot, { pin: fixturePin }) => {
    const pinRoot = path.join(fixtureRoot, CIV_ENGINE_PIN.installPath);
    const engine = await seedEngineRepository(pinRoot);
    git(pinRoot, ['remote', 'add', 'origin', CIV_ENGINE_PIN.repositoryUrl]);
    git(pinRoot, ['checkout', '--detach', engine.commit]);
    const pin = {
      ...fixturePin,
      commit: engine.commit,
      runtimeTreeSha256: engine.treeDigest,
    };
    await mkdir(path.join(fixtureRoot, 'node_modules'));
    await symlink(
      pinRoot,
      path.join(fixtureRoot, 'node_modules', CIV_ENGINE_PIN.packageName),
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    for (const fileName of SETUP_MODULES) {
      await copyFile(
        path.join(repoRoot, 'scripts', fileName),
        path.join(fixtureRoot, 'scripts', fileName),
      );
    }
    await writeFile(
      path.join(fixtureRoot, 'scripts', 'civ-engine-pin.json'),
      `${JSON.stringify(pin, null, 2)}\n`,
    );
    await callback({ fixtureRoot, pinRoot, pin });
  });
}

function runCopiedVerification(fixtureRoot, allowDirty) {
  const moduleUrl = pathToFileURL(path.join(
    fixtureRoot,
    'scripts',
    'civ-engine-setup.mjs',
  )).href;
  const child = spawnSync(process.execPath, [
    '--input-type=module',
    '-e',
    `import { verifyCivEngineSetup } from ${JSON.stringify(moduleUrl)}; `
      + `try { await verifyCivEngineSetup({ repoRoot: ${JSON.stringify(fixtureRoot)}, allowDirty: ${allowDirty} }); `
      + 'console.log(JSON.stringify({ ok: true })); } '
      + 'catch (error) { console.log(JSON.stringify({ ok: false, code: error.code ?? null, message: error.message })); }',
  ], {
    cwd: fixtureRoot,
    encoding: 'utf8',
    shell: false,
    windowsHide: true,
  });
  assert.equal(child.status, 0, child.stderr || child.stdout);
  return JSON.parse(child.stdout);
}

async function fsRealpath(candidate) {
  const { realpath } = await import('node:fs/promises');
  return realpath(candidate);
}

async function pathExistsForTest(candidate) {
  try {
    await fsRealpath(candidate);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}
