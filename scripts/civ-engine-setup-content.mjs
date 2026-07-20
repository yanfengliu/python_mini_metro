import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

import { CIV_ENGINE_PIN } from './civ-engine-pin.mjs';
import { runReadOnlyGit } from './civ-engine-setup-process.mjs';
import {
  assertSafeGeneratedTree,
  auditCheckoutMetadataFilesystem,
} from './civ-engine-setup-safety.mjs';

const GENERATED_ROOTS = new Set(['dist', 'node_modules']);
const SAFE_BLOB_MODES = new Set(['100644', '100755']);

export async function authenticateCheckoutContent(options) {
  assertAuthenticationOptions(options, 'strict');
  return authenticateContent({ ...options, allowTrackedChanges: false });
}

export async function authenticateDirtyCanaryCheckoutShape(options) {
  assertAuthenticationOptions(options, 'dirty-canary');
  return authenticateContent({ ...options, allowTrackedChanges: true });
}

async function authenticateContent({
  checkoutRoot,
  expectedCommit,
  expectedRepositoryUrl = CIV_ENGINE_PIN.repositoryUrl,
  allowTrackedChanges,
  runGit = runReadOnlyGit,
}) {
  const root = path.resolve(checkoutRoot);
  await rejectLocalNpmConfig(root);
  await rejectInfoExcludePatterns(root);
  await Promise.all([...GENERATED_ROOTS].map((name) => assertSafeGeneratedTree({
    ownerRoot: root,
    treeRoot: path.join(root, name),
    label: `civ-engine ${name}`,
  })));

  const invoke = async (args) => {
    await auditCheckoutMetadataFilesystem({
      checkoutRoot: root,
      expectedCommit,
      expectedRepositoryUrl,
      allowDirty: allowTrackedChanges,
      checkoutMode: 'detached',
    });
    return runGit({ repoRoot: root, args });
  };
  const indexOutput = await invoke(['ls-files', '-v', '-z']);
  const treeOutput = await invoke(['ls-tree', '-r', '-z', '--full-tree', 'HEAD']);
  rejectIndexConcealment(indexOutput);
  const tracked = parseHeadTree(treeOutput);
  const normalizeText = await validateAttributePolicy(root, tracked);
  await authenticateWorkingTree(root, tracked, {
    allowTrackedChanges,
    normalizeText,
  });
}

function assertAuthenticationOptions(options, mode) {
  if (!options || typeof options !== 'object' || Array.isArray(options)) {
    throw contentError('checkout authentication options are invalid');
  }
  const allowed = new Set([
    'checkoutRoot',
    'expectedCommit',
    'expectedRepositoryUrl',
    'runGit',
  ]);
  if (Object.keys(options).some((key) => !allowed.has(key))) {
    throw contentError(`${mode} checkout authentication received an unsupported option`);
  }
  if (mode === 'strict' && !/^[0-9a-f]{40,64}$/.test(options.expectedCommit ?? '')) {
    throw contentError('strict checkout authentication requires an exact commit');
  }
}

async function rejectLocalNpmConfig(root) {
  if (await pathExists(path.join(root, '.npmrc'))) {
    throw contentError('pin-local npm config is not allowed');
  }
}

async function rejectInfoExcludePatterns(root) {
  const excludePath = path.join(root, '.git', 'info', 'exclude');
  if (!await pathExists(excludePath)) return;
  await assertPhysicalFile(excludePath, 'Git info exclude');
  const lines = (await fs.readFile(excludePath, 'utf8')).split(/\r?\n/);
  if (lines.some((line) => line.trim() && !line.trimStart().startsWith('#'))) {
    throw contentError('Git info exclude patterns are not allowed');
  }
}

function rejectIndexConcealment(output) {
  for (const record of output.split('\0')) {
    if (!record) continue;
    if (record.length < 3 || record[1] !== ' ' || record[0] !== 'H') {
      throw contentError('Git index concealment flags are not allowed');
    }
  }
}

function parseHeadTree(output) {
  const tracked = new Map();
  for (const record of output.split('\0')) {
    if (!record) continue;
    const tab = record.indexOf('\t');
    const header = tab < 0 ? [] : record.slice(0, tab).split(' ');
    const relativePath = tab < 0 ? '' : record.slice(tab + 1);
    if (
      header.length !== 3
      || header[1] !== 'blob'
      || !SAFE_BLOB_MODES.has(header[0])
      || !/^[0-9a-f]{40,64}$/.test(header[2])
      || !safeRelativePath(relativePath)
      || generatedPath(relativePath)
      || tracked.has(relativePath)
    ) {
      throw contentError('HEAD contains an unsupported checkout entry');
    }
    tracked.set(relativePath, { mode: header[0], objectId: header[2] });
  }
  if (tracked.size === 0) throw contentError('HEAD checkout tree is empty');
  return tracked;
}

async function authenticateWorkingTree(root, tracked, options) {
  const { allowTrackedChanges } = options;
  const expectedDirectories = new Set();
  for (const relativePath of tracked.keys()) {
    const segments = relativePath.split('/');
    for (let index = 1; index < segments.length; index += 1) {
      expectedDirectories.add(segments.slice(0, index).join('/'));
    }
  }
  const observed = new Set();
  await walkCheckout(root, '', tracked, expectedDirectories, observed, options);
  if (!allowTrackedChanges) {
    for (const relativePath of tracked.keys()) {
      if (!observed.has(relativePath)) {
        throw contentError('tracked checkout content is missing');
      }
    }
  }
}

async function walkCheckout(
  root,
  relativeDirectory,
  tracked,
  expectedDirectories,
  observed,
  options,
) {
  const directoryPath = relativeDirectory
    ? path.join(root, ...relativeDirectory.split('/'))
    : root;
  const entries = await fs.readdir(directoryPath, { withFileTypes: true });
  for (const entry of entries) {
    const relativePath = relativeDirectory
      ? `${relativeDirectory}/${entry.name}`
      : entry.name;
    if (!relativeDirectory && (entry.name === '.git' || GENERATED_ROOTS.has(entry.name))) {
      continue;
    }
    const candidate = path.join(root, ...relativePath.split('/'));
    const metadata = await fs.lstat(candidate);
    if (metadata.isSymbolicLink()) {
      throw contentError('non-generated checkout entries must be physical');
    }
    if (metadata.isDirectory()) {
      if (!expectedDirectories.has(relativePath)) {
        throw contentError('unexpected non-generated checkout directory');
      }
      await walkCheckout(
        root,
        relativePath,
        tracked,
        expectedDirectories,
        observed,
        options,
      );
      continue;
    }
    if (!metadata.isFile() || !tracked.has(relativePath)) {
      throw contentError('unexpected non-generated checkout file');
    }
    observed.add(relativePath);
    if (!options.allowTrackedChanges) {
      const contents = await fs.readFile(candidate);
      const expected = tracked.get(relativePath).objectId;
      const direct = gitBlobId(contents, expected.length);
      const normalized = options.normalizeText && !contents.includes(0)
        ? gitBlobId(normalizeLineEndings(contents), expected.length)
        : direct;
      if (direct !== expected && normalized !== expected) {
        throw contentError('tracked checkout content does not match HEAD');
      }
    }
  }
}

async function validateAttributePolicy(root, tracked) {
  const attributes = tracked.get('.gitattributes');
  if (!attributes) return false;
  const candidate = path.join(root, '.gitattributes');
  await assertPhysicalFile(candidate, 'Git attributes');
  const contents = await fs.readFile(candidate);
  const normalized = normalizeLineEndings(contents);
  if (
    normalized.toString('utf8') !== '* text=auto\n'
    || gitBlobId(normalized, attributes.objectId.length) !== attributes.objectId
  ) {
    throw contentError('Git attributes policy is not the fixed safe text policy');
  }
  return true;
}

function normalizeLineEndings(contents) {
  return Buffer.from(contents.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
}

function gitBlobId(contents, objectIdLength) {
  const algorithm = objectIdLength === 64 ? 'sha256' : 'sha1';
  const header = Buffer.from(`blob ${contents.byteLength}\0`, 'utf8');
  return createHash(algorithm).update(header).update(contents).digest('hex');
}

async function assertPhysicalFile(candidate, label) {
  const [metadata, physical] = await Promise.all([
    fs.lstat(candidate),
    fs.realpath(candidate),
  ]);
  if (
    !metadata.isFile()
    || metadata.isSymbolicLink()
    || path.relative(path.resolve(candidate), path.resolve(physical)) !== ''
  ) {
    throw contentError(`${label} must be a physical file`);
  }
}

function safeRelativePath(candidate) {
  if (!candidate || candidate.includes('\\') || path.posix.isAbsolute(candidate)) return false;
  const normalized = path.posix.normalize(candidate);
  return normalized === candidate && normalized !== '..' && !normalized.startsWith('../');
}

function generatedPath(candidate) {
  const first = candidate.split('/')[0];
  return GENERATED_ROOTS.has(first);
}

async function pathExists(candidate) {
  try {
    await fs.lstat(candidate);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}

function contentError(message) {
  return Object.assign(new Error(message), {
    code: 'ERR_CIV_ENGINE_CHECKOUT_CONTENT',
  });
}
