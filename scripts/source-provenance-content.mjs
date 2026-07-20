import { createHash } from 'node:crypto';
import {
  readFile,
  readdir,
} from 'node:fs/promises';
import path from 'node:path';

export const SOURCE_TREE_ROOTS = Object.freeze(['src', 'scripts']);
export const SOURCE_ROOT_FILE_PATTERNS = Object.freeze([
  /^package.*\.json$/,
  /^requirements.*\.txt$/,
]);
export const SOURCE_GIT_PATHSPECS = Object.freeze([
  ':(top)src',
  ':(top)scripts',
  ':(top,glob)package*.json',
  ':(top,glob)requirements*.txt',
]);

const CACHE_DIRECTORIES = new Set([
  '.mypy_cache',
  '.pytest_cache',
  '.ruff_cache',
  '.tox',
  '.venv',
  '__pycache__',
  'node_modules',
]);
const CACHE_FILE_PATTERNS = [/\.py[co]$/, /^\.DS_Store$/];
const HEAD_FILE_MODES = new Set(['100644', '100755']);

export async function inventoryRelevantSourceFiles(repoRoot) {
  const relativePaths = [];
  for (const root of SOURCE_TREE_ROOTS) {
    await walkFiles(repoRoot, root, relativePaths);
  }
  const rootEntries = await readdir(repoRoot, { withFileTypes: true });
  for (const entry of rootEntries) {
    if (!SOURCE_ROOT_FILE_PATTERNS.some((pattern) => pattern.test(entry.name))) {
      continue;
    }
    if (!entry.isFile()) throw unsafeSourcePath(entry.name);
    relativePaths.push(entry.name);
  }
  relativePaths.sort(compareText);
  const snapshots = new Map();
  const files = await Promise.all(relativePaths.map(async (relativePath) => {
    const contents = await readFile(path.join(
      repoRoot,
      ...relativePath.split('/'),
    ));
    snapshots.set(relativePath, contents);
    return {
      path: relativePath,
      bytes: contents.byteLength,
      sha256: createHash('sha256').update(contents).digest('hex'),
    };
  }));
  return { files, snapshots };
}

export async function crosscheckRelevantWorkingBytes({
  inventory,
  status,
  trackedPaths,
  readGit,
}) {
  const objectFormat = (await readGit([
    'rev-parse',
    '--show-object-format',
  ])).trim();
  if (!['sha1', 'sha256'].includes(objectFormat)) {
    throw unsafeContent('unsupported Git object format');
  }
  const headTree = parseHeadTree(await readGit([
    'ls-tree',
    '-r',
    '-z',
    '--full-tree',
    'HEAD',
  ]), objectFormat);
  const reconciled = status.map((entry) => ({ ...entry }));
  const coveredPaths = new Set(reconciled.flatMap((entry) => (
    [entry.path, entry.originalPath].filter(Boolean)
  )));

  for (const [relativePath, contents] of inventory.snapshots) {
    const headEntry = headTree.get(relativePath);
    if (!headEntry) {
      if (!coveredPaths.has(relativePath)) {
        reconciled.push({
          code: trackedPaths.has(relativePath) ? 'A ' : '??',
          path: relativePath,
        });
      }
      continue;
    }
    if (
      !coveredPaths.has(relativePath)
      && !matchesHeadBlob(contents, headEntry.oid, objectFormat)
    ) {
      reconciled.push({ code: ' M', path: relativePath });
    }
  }

  for (const relativePath of headTree.keys()) {
    if (
      !inventory.snapshots.has(relativePath)
      && !coveredPaths.has(relativePath)
    ) {
      reconciled.push({
        code: trackedPaths.has(relativePath) ? ' D' : 'D ',
        path: relativePath,
      });
    }
  }
  return reconciled.sort((left, right) => compareText(
    `${left.path}\0${left.originalPath ?? ''}\0${left.code}`,
    `${right.path}\0${right.originalPath ?? ''}\0${right.code}`,
  ));
}

export function isRelevantSourcePath(candidate) {
  const normalized = normalizeRepoPath(candidate);
  if (isExcludedSourcePath(normalized)) return false;
  if (SOURCE_TREE_ROOTS.some((root) => (
    normalized === root || normalized.startsWith(`${root}/`)
  ))) return true;
  return !normalized.includes('/')
    && SOURCE_ROOT_FILE_PATTERNS.some((pattern) => pattern.test(normalized));
}

export function isExcludedSourcePath(candidate) {
  const parts = normalizeRepoPath(candidate).split('/');
  if (parts.some((part) => CACHE_DIRECTORIES.has(part))) return true;
  return CACHE_FILE_PATTERNS.some((pattern) => pattern.test(parts.at(-1)));
}

export function normalizeRepoPath(candidate) {
  return candidate.split(path.sep).join('/');
}

async function walkFiles(repoRoot, relativeDirectory, results) {
  let entries;
  try {
    entries = await readdir(path.join(repoRoot, relativeDirectory), {
      withFileTypes: true,
    });
  } catch (error) {
    if (error?.code === 'ENOENT') return;
    throw error;
  }
  entries.sort((left, right) => compareText(left.name, right.name));
  for (const entry of entries) {
    const relativePath = normalizeRepoPath(path.join(
      relativeDirectory,
      entry.name,
    ));
    if (isExcludedSourcePath(relativePath)) continue;
    if (entry.isDirectory()) {
      await walkFiles(repoRoot, relativePath, results);
    } else if (entry.isFile()) {
      results.push(relativePath);
    } else {
      throw unsafeSourcePath(relativePath);
    }
  }
}

function parseHeadTree(output, objectFormat) {
  const tree = new Map();
  const oidLength = objectFormat === 'sha1' ? 40 : 64;
  for (const record of output.split('\0')) {
    if (!record) continue;
    const separator = record.indexOf('\t');
    const fields = record.slice(0, separator).split(' ');
    const relativePath = normalizeRepoPath(record.slice(separator + 1));
    if (separator < 0 || fields.length !== 3) {
      throw unsafeContent('unexpected relevant HEAD tree entry');
    }
    if (!isRelevantSourcePath(relativePath)) continue;
    if (
      fields[1] !== 'blob'
      || !HEAD_FILE_MODES.has(fields[0])
      || !new RegExp(`^[0-9a-f]{${oidLength}}$`).test(fields[2])
      || tree.has(relativePath)
    ) throw unsafeContent('unexpected relevant HEAD tree entry');
    tree.set(relativePath, { mode: fields[0], oid: fields[2] });
  }
  return tree;
}

function matchesHeadBlob(contents, expectedOid, objectFormat) {
  if (gitBlobOid(contents, objectFormat) === expectedOid) return true;
  const canonical = canonicalCrlf(contents);
  return canonical !== null && gitBlobOid(canonical, objectFormat) === expectedOid;
}

function gitBlobOid(contents, objectFormat) {
  return createHash(objectFormat)
    .update(`blob ${contents.byteLength}\0`)
    .update(contents)
    .digest('hex');
}

function canonicalCrlf(contents) {
  if (!contents.includes(13) || contents.includes(0)) return null;
  const bytes = [];
  for (let index = 0; index < contents.length; index += 1) {
    if (contents[index] !== 13) {
      bytes.push(contents[index]);
      continue;
    }
    if (contents[index + 1] !== 10) return null;
    bytes.push(10);
    index += 1;
  }
  return Buffer.from(bytes);
}

function unsafeSourcePath(relativePath) {
  return Object.assign(
    new Error(`relevant source path must be a physical file or directory: ${relativePath}`),
    { code: 'ERR_SOURCE_GIT_UNSAFE' },
  );
}

function unsafeContent(message) {
  return Object.assign(new Error(`source HEAD crosscheck rejected: ${message}`), {
    code: 'ERR_SOURCE_GIT_UNSAFE',
  });
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}
