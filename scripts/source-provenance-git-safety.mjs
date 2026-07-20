import fs from 'node:fs/promises';
import path from 'node:path';

const DIRECT_UNSAFE_KEYS = new Set([
  'core.attributesfile',
  'core.checkstat',
  'core.editor',
  'core.excludesfile',
  'core.fsmonitor',
  'core.hookspath',
  'core.ignorestat',
  'core.pager',
  'core.sshcommand',
  'core.trustctime',
  'core.worktree',
  'credential.helper',
  'gpg.program',
  'http.extraheader',
  'http.proxy',
  'include.path',
  'includeif.path',
  'remote.receivepack',
  'remote.uploadpack',
  'sequence.editor',
  'url.insteadof',
  'url.pushinsteadof',
]);
const COMMAND_VARIABLES = new Set([
  'alternaterefscommand',
  'askpass',
  'clean',
  'cmd',
  'command',
  'difffilter',
  'driver',
  'editor',
  'executable',
  'external',
  'fsmonitor',
  'gitproxy',
  'helper',
  'hookspath',
  'pager',
  'process',
  'program',
  'recentobjectshook',
  'receivepack',
  'shell',
  'smudge',
  'sshcommand',
  'textconv',
  'uploadpack',
]);
const FORBIDDEN_METADATA_PATHS = [
  ['objects/info/alternates', 'object alternate'],
  ['objects/info/http-alternates', 'HTTP object alternate'],
  ['info/grafts', 'graft'],
  ['refs/replace', 'replace ref'],
  ['shallow', 'shallow metadata'],
  ['commondir', 'common-directory redirect'],
  ['gitdir', 'Git-directory redirect'],
];
const SOURCE_ROOTS = ['src', 'scripts'];
const ROOT_SOURCE_PATTERNS = [/^package.*\.json$/i, /^requirements.*\.txt$/i];
const GIT_BEHAVIOR_ATTRIBUTES = new Set([
  'binary',
  'crlf',
  'diff',
  'eol',
  'filter',
  'ident',
  'text',
  'working-tree-encoding',
]);

export async function auditSourceGitMetadata(repoRoot) {
  const audit = await auditRepositoryGitMetadata(repoRoot);
  const infoPath = path.join(audit.gitDir, 'info');
  const physicalInfo = await optionalPhysicalDirectory(infoPath, 'local Git info');
  if (physicalInfo) {
    const attributesPath = path.join(infoPath, 'attributes');
    if (await optionalPhysicalFile(
      attributesPath,
      path.join(physicalInfo, 'attributes'),
      'local Git attributes file',
    )) {
      auditAttributes(
        await readSafeText(attributesPath, 'local Git attributes file'),
        '',
      );
    }
  }
  await auditWorktreeAttributes(audit.repoRoot);
  return audit;
}

export async function auditRepositoryGitMetadata(repoRoot) {
  if (typeof repoRoot !== 'string' || !path.isAbsolute(repoRoot)) {
    throw new TypeError('repoRoot must be an absolute path');
  }
  const lexicalRoot = path.resolve(repoRoot);
  const gitPath = path.join(lexicalRoot, '.git');
  const [physicalRoot, physicalGit] = await Promise.all([
    physicalDirectory(lexicalRoot, 'repository root'),
    physicalDirectory(gitPath, 'local .git directory'),
  ]);
  if (!samePath(physicalGit, path.join(physicalRoot, '.git'))) {
    throw unsafeGit('local .git directory must remain inside the repository');
  }
  const configPath = path.join(gitPath, 'config');
  await physicalFile(configPath, path.join(physicalGit, 'config'), 'local Git config');
  const config = await readSafeText(configPath, 'local Git config');
  auditConfig(config);

  const worktreeConfigPath = path.join(gitPath, 'config.worktree');
  if (await optionalPhysicalFile(
    worktreeConfigPath,
    path.join(physicalGit, 'config.worktree'),
    'local worktree Git config',
  )) {
    auditConfig(await readSafeText(worktreeConfigPath, 'local worktree Git config'));
  }

  for (const [relativePath, label] of FORBIDDEN_METADATA_PATHS) {
    if (await pathExists(path.join(gitPath, ...relativePath.split('/')))) {
      throw unsafeGit(`local Git ${label} is not allowed`);
    }
  }

  await assertPhysicalTree(gitPath, 'local Git metadata');
  await Promise.all([
    physicalFile(
      path.join(gitPath, 'HEAD'),
      path.join(physicalGit, 'HEAD'),
      'local Git HEAD',
    ),
    physicalFile(
      path.join(gitPath, 'index'),
      path.join(physicalGit, 'index'),
      'local Git index',
    ),
    physicalDirectory(path.join(gitPath, 'objects'), 'local Git object directory'),
    physicalDirectory(path.join(gitPath, 'refs'), 'local Git refs directory'),
  ]);

  const infoPath = path.join(gitPath, 'info');
  const physicalInfo = await optionalPhysicalDirectory(infoPath, 'local Git info');
  if (physicalInfo) {
    const excludePath = path.join(infoPath, 'exclude');
    await optionalPhysicalFile(
      excludePath,
      path.join(physicalInfo, 'exclude'),
      'local Git exclude file',
    );
  }
  return Object.freeze({
    repoRoot: physicalRoot,
    gitDir: physicalGit,
    configPath: path.join(physicalGit, 'config'),
  });
}

async function auditWorktreeAttributes(repoRoot) {
  const rootAttributes = path.join(repoRoot, '.gitattributes');
  if (await optionalPhysicalFile(
    rootAttributes,
    path.join(repoRoot, '.gitattributes'),
    'root attributes file',
  )) {
    auditAttributes(await readSafeText(rootAttributes, 'root attributes file'), '');
  }
  for (const sourceRoot of SOURCE_ROOTS) {
    const candidate = path.join(repoRoot, sourceRoot);
    if (!await pathExists(candidate)) continue;
    await auditNestedAttributes(candidate, sourceRoot);
  }
}

async function auditNestedAttributes(directoryPath, relativeDirectory) {
  await physicalDirectory(directoryPath, 'relevant source directory');
  const entries = await fs.readdir(directoryPath, { withFileTypes: true });
  for (const entry of entries) {
    const candidate = path.join(directoryPath, entry.name);
    const relativePath = path.posix.join(relativeDirectory, entry.name);
    if (entry.isDirectory()) {
      await auditNestedAttributes(candidate, relativePath);
    } else if (entry.name === '.gitattributes') {
      await physicalFile(candidate, candidate, 'relevant attributes file');
      auditAttributes(
        await readSafeText(candidate, 'relevant attributes file'),
        relativeDirectory,
      );
    }
  }
}

function auditAttributes(contents, relativeDirectory) {
  if (contents.includes('\0') || contents.includes('\uFFFD')) {
    throw unsafeGit('local Git attributes are not valid text');
  }
  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const fields = line.split(/\s+/);
    if (fields.length < 2 || fields[0].includes('\\') || fields[0].startsWith('"')) {
      throw unsafeGit('unsupported local Git attributes syntax');
    }
    const pattern = fields[0];
    const behaviorChanging = fields.slice(1).some((attribute) => (
      GIT_BEHAVIOR_ATTRIBUTES.has(attributeName(attribute))
    ));
    if (!behaviorChanging) continue;
    if (pattern.startsWith('[attr]') || attributePatternCanReachSource(
      pattern,
      relativeDirectory,
    )) {
      throw unsafeGit('local Git attributes may alter relevant source inspection');
    }
  }
}

function attributeName(attribute) {
  return attribute.replace(/^[-!]/, '').split('=', 1)[0].toLowerCase();
}

function attributePatternCanReachSource(pattern, relativeDirectory) {
  if (relativeDirectory) return true;
  const normalized = pattern.replace(/^\//, '').replaceAll('\\', '/');
  if (
    !normalized
    || normalized.includes('..')
    || normalized.startsWith('!')
  ) return true;
  const firstPart = normalized.split('/', 1)[0];
  if (/[*?\[]/.test(firstPart)) return true;
  const folded = firstPart.toLowerCase();
  if (SOURCE_ROOTS.includes(folded)) return true;
  return !normalized.includes('/')
    && ROOT_SOURCE_PATTERNS.some((candidate) => candidate.test(normalized));
}

function auditConfig(contents) {
  if (contents.includes('\0') || contents.includes('\uFFFD')) {
    throw unsafeConfig();
  }
  let section = null;
  for (const { line, lineNumber } of logicalLines(contents)) {
    const candidate = stripComment(line).trim();
    if (!candidate) continue;
    if (candidate.startsWith('[')) {
      section = parseSection(candidate, lineNumber);
      continue;
    }
    if (!section) throw configSyntax(lineNumber);
    const variable = parseVariable(candidate, lineNumber);
    if (classifyUnsafeKey(section, variable)) throw unsafeConfig();
  }
}

function parseSection(candidate, lineNumber) {
  const match = /^\[\s*([A-Za-z][A-Za-z0-9-]*)(?:\s+"(?:[^"\\]|\\.)*"|\.[^\s\]]+)?\s*\]$/.exec(
    candidate,
  );
  if (!match) throw configSyntax(lineNumber);
  return match[1].toLowerCase();
}

function parseVariable(candidate, lineNumber) {
  const match = /^([A-Za-z][A-Za-z0-9-]*)(?:\s*=\s*[\s\S]*|\s*)$/.exec(
    candidate,
  );
  if (!match) throw configSyntax(lineNumber);
  return match[1].toLowerCase();
}

function classifyUnsafeKey(section, variable) {
  if (section === 'alias') return 'alias.command';
  const key = `${section}.${variable}`;
  if (DIRECT_UNSAFE_KEYS.has(key)) return key;
  if (
    (section === 'filter' && ['clean', 'smudge', 'process'].includes(variable))
    || (section === 'diff' && ['command', 'textconv'].includes(variable))
    || (['difftool', 'mergetool'].includes(section) && variable === 'cmd')
    || (section === 'submodule' && variable === 'update')
    || COMMAND_VARIABLES.has(variable)
  ) {
    return `${section}.${variable}`;
  }
  if (section === 'include' || section === 'includeif') {
    return `${section}.${variable}`;
  }
  if (section === 'url' && ['insteadof', 'pushinsteadof'].includes(variable)) {
    return `${section}.${variable}`;
  }
  return null;
}

function logicalLines(contents) {
  const physicalLines = contents.split(/\r?\n/);
  const lines = [];
  let continued = '';
  let startLine = 1;
  for (let index = 0; index < physicalLines.length; index += 1) {
    const physicalLine = physicalLines[index];
    if (!continued) startLine = index + 1;
    const trailingBackslashes = /\\+$/.exec(physicalLine)?.[0].length ?? 0;
    if (trailingBackslashes % 2 === 1) {
      continued += physicalLine.slice(0, -1);
      continue;
    }
    lines.push({ line: continued + physicalLine, lineNumber: startLine });
    continued = '';
  }
  if (continued) throw configSyntax(startLine);
  return lines;
}

function stripComment(line) {
  let quoted = false;
  let escaped = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (character === '\\' && quoted) {
      escaped = true;
      continue;
    }
    if (character === '"') {
      quoted = !quoted;
      continue;
    }
    if (!quoted && (character === '#' || character === ';')) {
      return line.slice(0, index);
    }
  }
  return line;
}

async function physicalDirectory(candidate, label) {
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.lstat(candidate),
      fs.realpath(candidate),
    ]);
  } catch {
    throw unsafeGit(`${label} is unavailable`);
  }
  if (
    !metadata.isDirectory()
    || metadata.isSymbolicLink()
    || !samePath(candidate, physical)
  ) {
    throw unsafeGit(`${label} must be a physical directory`);
  }
  return physical;
}

async function assertPhysicalTree(treeRoot, label) {
  await physicalDirectory(treeRoot, label);
  const entries = await fs.readdir(treeRoot, { withFileTypes: true });
  for (const entry of entries) {
    const entryPath = path.join(treeRoot, entry.name);
    const metadata = await fs.lstat(entryPath);
    if (metadata.isSymbolicLink()) {
      throw unsafeGit(`${label} contains a link, junction, or reparse point`);
    }
    if (metadata.isDirectory()) {
      await assertPhysicalTree(entryPath, label);
    } else if (!metadata.isFile()) {
      throw unsafeGit(`${label} contains a non-physical entry`);
    }
  }
}

async function physicalFile(candidate, expectedPhysical, label) {
  let metadata;
  let physical;
  try {
    [metadata, physical] = await Promise.all([
      fs.lstat(candidate),
      fs.realpath(candidate),
    ]);
  } catch {
    throw unsafeGit(`${label} is unavailable`);
  }
  if (
    !metadata.isFile()
    || metadata.isSymbolicLink()
    || !samePath(physical, expectedPhysical)
  ) {
    throw unsafeGit(`${label} must be a physical local file`);
  }
  return physical;
}

async function optionalPhysicalDirectory(candidate, label) {
  try {
    await fs.lstat(candidate);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw unsafeGit(`${label} is unavailable`);
  }
  return physicalDirectory(candidate, label);
}

async function optionalPhysicalFile(candidate, expectedPhysical, label) {
  try {
    await fs.lstat(candidate);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw unsafeGit(`${label} is unavailable`);
  }
  return physicalFile(candidate, expectedPhysical, label);
}

async function readSafeText(candidate, label) {
  try {
    return await fs.readFile(candidate, 'utf8');
  } catch {
    throw unsafeGit(`${label} is unreadable`);
  }
}

async function pathExists(candidate) {
  try {
    await fs.lstat(candidate);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw unsafeGit('local Git metadata is unavailable');
  }
}

function configSyntax() {
  return unsafeConfig();
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function unsafeGit(message) {
  return Object.assign(new Error(`source Git metadata rejected: ${message}`), {
    code: 'ERR_SOURCE_GIT_UNSAFE',
  });
}

function unsafeConfig() {
  return unsafeGit('unsafe local Git config');
}
