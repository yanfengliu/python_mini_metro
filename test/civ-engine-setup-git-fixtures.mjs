import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  readlink,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const FIXED_ORIGIN = 'https://github.com/yanfengliu/civ-engine.git';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputRoot = path.join(repoRoot, 'output', 'node-tests');

export async function withDetachedCheckout(callback) {
  await mkdir(outputRoot, { recursive: true });
  const fixtureRoot = await mkdtemp(path.join(outputRoot, 'setup-git-safety-'));
  const checkoutRoot = path.join(fixtureRoot, 'checkout');
  const externalRoot = path.join(fixtureRoot, 'external');
  try {
    await Promise.all([
      mkdir(path.join(checkoutRoot, 'src'), { recursive: true }),
      mkdir(path.join(checkoutRoot, 'dist'), { recursive: true }),
      mkdir(path.join(checkoutRoot, 'node_modules'), { recursive: true }),
      mkdir(externalRoot, { recursive: true }),
    ]);
    await Promise.all([
      writeFile(path.join(checkoutRoot, '.gitignore'), 'dist/\nnode_modules/\n'),
      writeFile(path.join(checkoutRoot, 'src', 'index.ts'), 'export const value = 1;\n'),
      writeFile(path.join(checkoutRoot, 'package-lock.json'), '{"lockfileVersion":3}\n'),
      writeFile(path.join(checkoutRoot, 'package.json'), `${JSON.stringify({
        name: 'civ-engine',
        version: '2.2.0',
        type: 'module',
        main: './dist/index.js',
      }, null, 2)}\n`),
      writeFile(path.join(checkoutRoot, 'dist', 'index.js'), 'export const value = 1;\n'),
      writeFile(path.join(externalRoot, 'sentinel.txt'), 'external sentinel\n'),
    ]);
    git(checkoutRoot, ['init', '--quiet']);
    git(checkoutRoot, ['add', '.']);
    git(checkoutRoot, [
      '-c',
      'user.name=Setup Safety Test',
      '-c',
      'user.email=setup-safety@example.invalid',
      'commit',
      '--quiet',
      '-m',
      'fixture checkout',
    ]);
    git(checkoutRoot, ['remote', 'add', 'origin', FIXED_ORIGIN]);
    git(checkoutRoot, ['config', 'remote.origin.tagOpt', '--no-tags']);
    const commit = git(checkoutRoot, ['rev-parse', 'HEAD']).stdout.trim();
    git(checkoutRoot, ['checkout', '--detach', '--quiet', commit]);
    await callback({
      checkoutRoot,
      commit,
      externalRoot,
      fixtureRoot,
      gitDir: path.join(checkoutRoot, '.git'),
    });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
}

export function git(cwd, args) {
  const result = spawnSync('git', args, {
    cwd,
    encoding: 'utf8',
    shell: false,
    windowsHide: true,
  });
  assert.equal(
    result.status,
    0,
    `git ${args.join(' ')} failed: ${result.stderr || result.stdout}`,
  );
  return result;
}

export async function snapshotByteTree(root) {
  const snapshot = [];
  await walk(root, '', snapshot);
  return snapshot;
}

export async function snapshotIndex(gitDir) {
  const indexPath = path.join(gitDir, 'index');
  const [contents, metadata] = await Promise.all([
    readFile(indexPath),
    stat(indexPath, { bigint: true }),
  ]);
  return {
    sha256: sha256(contents),
    size: metadata.size.toString(),
    mtimeNs: metadata.mtimeNs.toString(),
  };
}

async function walk(root, relativeDirectory, snapshot) {
  const directoryPath = relativeDirectory
    ? path.join(root, relativeDirectory)
    : root;
  const entries = await readdir(directoryPath, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name));
  for (const entry of entries) {
    const relativePath = relativeDirectory
      ? path.join(relativeDirectory, entry.name)
      : entry.name;
    const fullPath = path.join(root, relativePath);
    const metadata = await lstat(fullPath);
    if (metadata.isSymbolicLink()) {
      snapshot.push({
        path: portable(relativePath),
        type: 'link',
        target: await readlink(fullPath),
      });
    } else if (metadata.isDirectory()) {
      snapshot.push({ path: portable(relativePath), type: 'directory' });
      await walk(root, relativePath, snapshot);
    } else if (metadata.isFile()) {
      snapshot.push({
        path: portable(relativePath),
        type: 'file',
        bytes: metadata.size,
        sha256: sha256(await readFile(fullPath)),
      });
    } else {
      snapshot.push({ path: portable(relativePath), type: 'other' });
    }
  }
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function portable(value) {
  return value.split(path.sep).join('/');
}
