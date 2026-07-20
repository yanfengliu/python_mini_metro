import fs from 'node:fs/promises';
import path from 'node:path';

import { auditRepositoryGitMetadata } from './source-provenance-git-safety.mjs';

const FIXED_ROOT_ATTRIBUTES = '* text=auto\n';
const EXCLUDED_DIRECTORY_NAMES = new Set([
  '.git',
  '.git-read-home',
  'dist',
  'node_modules',
]);

export async function auditEngineGitMetadata(engineRoot) {
  const audit = await auditRepositoryGitMetadata(engineRoot);
  const rootAttributes = await readOptionalPhysicalText(
    path.join(audit.repoRoot, '.gitattributes'),
  );
  if (
    rootAttributes !== null
    && rootAttributes.replaceAll('\r\n', '\n') !== FIXED_ROOT_ATTRIBUTES
  ) {
    throw unsafeEngineGitMetadata();
  }

  const infoAttributes = await readOptionalPhysicalText(
    path.join(audit.gitDir, 'info', 'attributes'),
  );
  if (infoAttributes !== null && hasActiveAttributeLine(infoAttributes)) {
    throw unsafeEngineGitMetadata();
  }
  const infoExclude = await readOptionalPhysicalText(
    path.join(audit.gitDir, 'info', 'exclude'),
  );
  if (infoExclude !== null && hasActiveAttributeLine(infoExclude)) {
    throw unsafeEngineGitMetadata();
  }

  await auditNestedAttributes(audit.repoRoot, true);
  return audit;
}

export function safeCivEngineUnavailableReason(phase, error) {
  if (error?.code === 'ERR_SOURCE_GIT_UNSAFE') {
    return 'civ-engine Git metadata is unsafe';
  }
  if (error?.code === 'ERR_CIV_ENGINE_SETUP_PROCESS') {
    return Number.isInteger(error.status)
      ? `civ-engine Git inspection failed (${error.status})`
      : 'civ-engine Git inspection failed';
  }
  switch (phase) {
    case 'package resolution':
      return 'civ-engine package resolution failed';
    case 'package metadata':
      return 'civ-engine package metadata is unavailable or invalid';
    case 'runtime layout':
      return 'civ-engine runtime layout is unavailable or unsafe';
    case 'runtime inventory':
      return 'civ-engine runtime inventory failed';
    case 'Git inspection':
      return 'civ-engine Git inspection failed';
    default:
      return 'civ-engine provenance capture failed';
  }
}

async function auditNestedAttributes(directoryPath, isRoot = false) {
  const entries = await fs.readdir(directoryPath, { withFileTypes: true });
  for (const entry of entries) {
    if (isRoot && entry.name === '.gitattributes') continue;
    if (entry.name === '.gitattributes') {
      const attributes = await readOptionalPhysicalText(
        path.join(directoryPath, entry.name),
      );
      if (attributes !== null && hasActiveAttributeLine(attributes)) {
        throw unsafeEngineGitMetadata();
      }
      continue;
    }
    if (!entry.isDirectory() || EXCLUDED_DIRECTORY_NAMES.has(entry.name)) continue;
    const childPath = path.join(directoryPath, entry.name);
    if (!await isPhysicalDirectory(childPath)) continue;
    await auditNestedAttributes(childPath);
  }
}

async function readOptionalPhysicalText(candidate) {
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.lstat(candidate),
      fs.realpath(candidate),
    ]);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw unsafeEngineGitMetadata();
  }
  if (
    !metadata.isFile()
    || metadata.isSymbolicLink()
    || !samePath(candidate, physical)
  ) {
    throw unsafeEngineGitMetadata();
  }
  let contents;
  try {
    contents = await fs.readFile(candidate, 'utf8');
  } catch {
    throw unsafeEngineGitMetadata();
  }
  if (contents.includes('\0') || contents.includes('\uFFFD')) {
    throw unsafeEngineGitMetadata();
  }
  return contents;
}

async function isPhysicalDirectory(candidate) {
  try {
    const [metadata, physical] = await Promise.all([
      fs.lstat(candidate),
      fs.realpath(candidate),
    ]);
    return metadata.isDirectory()
      && !metadata.isSymbolicLink()
      && samePath(candidate, physical);
  } catch {
    throw unsafeEngineGitMetadata();
  }
}

function hasActiveAttributeLine(contents) {
  return contents.split(/\r?\n/).some((line) => {
    const candidate = line.trim();
    return candidate && !candidate.startsWith('#');
  });
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function unsafeEngineGitMetadata() {
  return Object.assign(new Error('civ-engine Git metadata is unsafe'), {
    code: 'ERR_SOURCE_GIT_UNSAFE',
  });
}
