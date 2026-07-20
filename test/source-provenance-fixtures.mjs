import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import {
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const testOutputBase = path.join(repoRoot, 'output', 'node-tests');

export async function withRepository(callback) {
  await mkdir(testOutputBase, { recursive: true });
  const fixtureRoot = await mkdtemp(path.join(testOutputBase, 'source-state-'));
  const engineRoot = `${fixtureRoot}-civ-engine`;
  try {
    const engine = await seedEngineRepository(engineRoot);
    await seedRepository(fixtureRoot, engineRoot);
    await callback(fixtureRoot, engine);
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
    await rm(engineRoot, { recursive: true, force: true });
  }
}

export async function seedEngineRepository(engineRoot) {
  await mkdir(path.join(engineRoot, 'dist'), { recursive: true });
  await Promise.all([
    writeFile(path.join(engineRoot, 'package.json'), JSON.stringify({
      name: 'civ-engine',
      version: '2.2.0',
      type: 'module',
      exports: {
        '.': { import: './dist/index.js' },
        './package.json': './package.json',
      },
    }, null, 2), 'utf8'),
    writeFile(
      path.join(engineRoot, 'dist', 'index.js'),
      'export { stateDigest } from "./state-digest.js";\n',
      'utf8',
    ),
    writeFile(
      path.join(engineRoot, 'dist', 'state-digest.js'),
      'export const stateDigest = JSON.stringify;\n',
      'utf8',
    ),
    writeFile(path.join(engineRoot, 'README.md'), 'fixture engine\n', 'utf8'),
    writeFile(path.join(engineRoot, '.gitignore'), 'dist/\n', 'utf8'),
  ]);
  git(engineRoot, ['init', '--quiet']);
  git(engineRoot, ['add', '.']);
  commit(engineRoot, 'fixture engine');
  return {
    root: engineRoot,
    commit: git(engineRoot, ['rev-parse', 'HEAD']).stdout.trim(),
    treeDigest: await runtimeTreeDigest(engineRoot),
  };
}

export function sourceOptions(
  repositoryRoot,
  expectedEngineCommit,
  expectedEngineTreeDigest,
) {
  return {
    repoRoot: repositoryRoot,
    enginePackageRoot: 'node_modules/civ-engine',
    expectedEnginePackageRoot: `${repositoryRoot}-civ-engine`,
    expectedEngineCommit,
    expectedEngineTreeDigest,
  };
}

export async function copyProvenanceModules(fixtureRoot) {
  for (const fileName of [
    'civ-engine-pin.json',
    'civ-engine-pin.mjs',
    'civ-engine-runtime.mjs',
    'civ-engine-setup-process.mjs',
    'source-provenance-engine-safety.mjs',
    'source-provenance-engine.mjs',
    'source-provenance-git-safety.mjs',
  ]) {
    await copyFile(
      path.join(repoRoot, 'scripts', fileName),
      path.join(fixtureRoot, 'scripts', fileName),
    );
  }
}

export function runCopiedCapture(fixtureRoot) {
  const moduleUrl = pathToFileURL(path.join(
    fixtureRoot,
    'scripts',
    'source-provenance-engine.mjs',
  )).href;
  const child = spawnSync(process.execPath, [
    '--input-type=module',
    '-e',
    `import { assertCivEngineStateAllowed, captureCivEngineState } from ${JSON.stringify(moduleUrl)}; `
    + `const state = await captureCivEngineState({ repoRoot: ${JSON.stringify(fixtureRoot)} }); `
    + 'const policyErrors = [false, true].map((allowDirty) => { '
    + 'try { assertCivEngineStateAllowed(state, { allowDirty }); return null; } '
    + 'catch (error) { return { code: error.code ?? null, message: error.message }; } }); '
    + 'console.log(JSON.stringify({ state, policyErrors }));',
  ], {
    cwd: fixtureRoot,
    encoding: 'utf8',
    shell: false,
  });
  assert.equal(child.status, 0, child.stderr || child.stdout);
  return JSON.parse(child.stdout);
}

export function git(cwd, args) {
  const result = spawnSync('git', args, {
    cwd,
    encoding: 'utf8',
    shell: false,
  });
  assert.equal(
    result.status,
    0,
    `git ${args.join(' ')} failed: ${result.stderr || result.stdout}`,
  );
  return result;
}

export function commit(cwd, message) {
  git(cwd, [
    '-c',
    'user.name=Recursive Test',
    '-c',
    'user.email=recursive-test@example.invalid',
    'commit',
    '--quiet',
    '-m',
    message,
  ]);
}

export function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

export function normalize(value) {
  return value.split(path.sep).join('/');
}

async function seedRepository(fixtureRoot, engineRoot) {
  await Promise.all([
    mkdir(path.join(fixtureRoot, 'src', '__pycache__'), { recursive: true }),
    mkdir(path.join(fixtureRoot, 'scripts', '.ruff_cache'), { recursive: true }),
    mkdir(path.join(fixtureRoot, 'test'), { recursive: true }),
  ]);
  await Promise.all([
    writeFile(path.join(fixtureRoot, 'src', 'app.py'), 'print("fixture")\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'src', '__pycache__', 'app.pyc'), 'cache', 'utf8'),
    writeFile(path.join(fixtureRoot, 'scripts', 'drive.mjs'), 'export {};\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'scripts', '.ruff_cache', 'cache'), 'cache', 'utf8'),
    writeFile(path.join(fixtureRoot, 'package.json'), '{}\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'package-lock.json'), '{"lockfileVersion":3}\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'requirements.txt'), 'pygame-ce\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'requirements-dev.txt'), 'ruff\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'README.md'), 'fixture\n', 'utf8'),
    writeFile(path.join(fixtureRoot, 'test', 'ignored.mjs'), 'throw new Error();\n', 'utf8'),
  ]);
  git(fixtureRoot, ['init', '--quiet']);
  git(fixtureRoot, ['add', '.']);
  git(fixtureRoot, [
    '-c',
    'user.name=Recursive Test',
    '-c',
    'user.email=recursive-test@example.invalid',
    'commit',
    '--quiet',
    '-m',
    'fixture',
  ]);
  await mkdir(path.join(fixtureRoot, 'node_modules'), { recursive: true });
  await symlink(
    engineRoot,
    path.join(fixtureRoot, 'node_modules', 'civ-engine'),
    'junction',
  );
}

async function runtimeTreeDigest(engineRoot) {
  const files = await Promise.all([
    'dist/index.js',
    'dist/state-digest.js',
    'package.json',
  ].map(async (relativePath) => {
    const contents = await readFile(path.join(engineRoot, ...relativePath.split('/')));
    return {
      path: relativePath,
      bytes: contents.byteLength,
      sha256: sha256(contents),
    };
  }));
  return sha256(JSON.stringify(files));
}
