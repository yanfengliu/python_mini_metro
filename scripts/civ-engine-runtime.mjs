import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HASH_ALGORITHM = 'sha256';
const TEXT_RUNTIME_EXTENSIONS = new Set(['.js', '.json', '.map', '.ts']);

export function resolveInstalledCivEngine(packageName) {
  const packageDocumentUrl = import.meta.resolve(`${packageName}/package.json`);
  const runtimeUrl = import.meta.resolve(packageName);
  const packageDocumentPath = fileURLToPath(packageDocumentUrl);
  return {
    packageRoot: path.dirname(packageDocumentPath),
    runtimePath: fileURLToPath(runtimeUrl),
  };
}

export function resolveFromRepoRoot(repoRoot, candidate, label) {
  if (typeof candidate !== 'string' || candidate.length === 0) {
    throw new TypeError(`${label} must be a nonempty path`);
  }
  return path.isAbsolute(candidate)
    ? path.resolve(candidate)
    : path.resolve(repoRoot, candidate);
}

export async function inspectExpectedPackageRoot({
  repoRoot,
  expectedPackageRoot,
  requireContained,
}) {
  const configured = path.resolve(expectedPackageRoot);
  try {
    const [entry, resolved, resolvedParent, resolvedRepoRoot] = await Promise.all([
      fs.lstat(configured),
      fs.realpath(configured),
      fs.realpath(path.dirname(configured)),
      fs.realpath(repoRoot),
    ]);
    const physicalLocation = path.join(resolvedParent, path.basename(configured));
    const contained = isStrictlyInside(resolvedRepoRoot, resolved);
    return {
      resolved,
      physical: (
        entry.isDirectory()
        && !entry.isSymbolicLink()
        && samePath(resolved, physicalLocation)
        && (!requireContained || contained)
      ),
    };
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error;
    return { resolved: configured, physical: false };
  }
}

export function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

export function isStrictlyInside(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return Boolean(
    relative
    && !path.isAbsolute(relative)
    && relative !== '..'
    && !relative.startsWith(`..${path.sep}`)
  );
}

export async function assertPhysicalDirectory(packageRoot, relativeDirectory) {
  const directoryPath = path.join(packageRoot, relativeDirectory);
  const [entry, resolved] = await Promise.all([
    fs.lstat(directoryPath),
    fs.realpath(directoryPath),
  ]);
  if (
    !entry.isDirectory()
    || entry.isSymbolicLink()
    || !samePath(directoryPath, resolved)
    || !isStrictlyInside(packageRoot, resolved)
  ) {
    throw new Error(`civ-engine ${relativeDirectory} must be a physical directory`);
  }
}

export function resolveRuntimeEntry(packageDocument) {
  const rootExport = packageDocument.exports?.['.'];
  let candidate = typeof rootExport === 'string' ? rootExport : rootExport?.import;
  if (candidate && typeof candidate === 'object') candidate = candidate.default;
  candidate ??= packageDocument.main;
  if (typeof candidate !== 'string' || !candidate.startsWith('./dist/')) {
    throw new Error('civ-engine package must expose an imported dist runtime');
  }
  const normalized = path.posix.normalize(candidate.slice(2));
  if (normalized.startsWith('../') || path.posix.isAbsolute(normalized)) {
    throw new Error('civ-engine runtime entry escapes its package root');
  }
  return normalized;
}

export async function inventoryRuntimeFiles(packageRoot) {
  const relativePaths = ['package.json'];
  await walkDist(packageRoot, 'dist', relativePaths);
  relativePaths.sort(compareText);
  return Promise.all(relativePaths.map(async (relativePath) => {
    const rawContents = await fs.readFile(
      path.join(packageRoot, ...relativePath.split('/')),
    );
    const contents = canonicalRuntimeContents(relativePath, rawContents);
    return {
      path: relativePath,
      bytes: contents.byteLength,
      sha256: createHash(HASH_ALGORITHM).update(contents).digest('hex'),
    };
  }));
}

export function normalizePath(candidate) {
  return candidate.split(path.sep).join('/');
}

function canonicalRuntimeContents(relativePath, contents) {
  if (!TEXT_RUNTIME_EXTENSIONS.has(path.extname(relativePath).toLowerCase())) {
    return contents;
  }
  return Buffer.from(contents.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
}

async function walkDist(packageRoot, relativeDirectory, results) {
  const entries = await fs.readdir(path.join(packageRoot, relativeDirectory), {
    withFileTypes: true,
  });
  entries.sort((left, right) => compareText(left.name, right.name));
  for (const entry of entries) {
    const relativePath = normalizePath(path.join(relativeDirectory, entry.name));
    if (entry.isDirectory()) {
      await walkDist(packageRoot, relativePath, results);
    } else if (entry.isFile()) {
      results.push(relativePath);
    } else {
      throw new Error(`unsupported civ-engine dist entry: ${relativePath}`);
    }
  }
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}
