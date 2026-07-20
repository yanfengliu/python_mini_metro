const ALLOWED_CORE_KEYS = new Set([
  'repositoryformatversion',
  'filemode',
  'bare',
  'logallrefupdates',
  'symlinks',
  'ignorecase',
]);

export function inspectLocalGitConfig(config) {
  let section = '';
  const origins = [];
  const fetches = [];
  const tagOptions = [];
  const branches = new Map();
  for (const rawLine of config.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || line.startsWith(';')) continue;
    if (line.startsWith('[')) {
      section = line.toLowerCase();
      inspectSection(section);
      continue;
    }
    const separator = line.indexOf('=');
    const key = (separator < 0 ? line : line.slice(0, separator)).trim().toLowerCase();
    const value = (separator < 0 ? '' : line.slice(separator + 1)).trim();
    if (section === '[core]') {
      inspectCoreKey(key);
    } else if (section === '[remote "origin"]') {
      inspectRemoteKey({ key, value, origins, fetches, tagOptions });
    } else if (section.startsWith('[branch ')) {
      inspectBranchKey({ section, key, value, branches });
    } else {
      throw unsafe('local Git setting has no trusted section');
    }
  }
  if (origins.length !== 1) throw mismatch('civ-engine checkout must have one origin URL');
  if (
    fetches.length !== 1
    || fetches[0] !== '+refs/heads/*:refs/remotes/origin/*'
  ) {
    throw unsafe('civ-engine origin fetch mapping is not canonical');
  }
  if (tagOptions.length > 1 || tagOptions.some((value) => value !== '--no-tags')) {
    throw unsafe('civ-engine origin tag policy is not canonical');
  }
  for (const values of branches.values()) {
    if (
      values.remote !== 'origin'
      || !/^refs\/heads\/[A-Za-z0-9._/-]+$/.test(values.merge ?? '')
      || values.merge.includes('..')
    ) {
      throw unsafe('local Git branch metadata is not canonical');
    }
  }
  return origins[0];
}

function inspectSection(section) {
  if (/^\[(include|includeif)\b/.test(section)) throw unsafe('Git config include is not allowed');
  if (/^\[filter\b/.test(section)) throw unsafe('Git filter commands are not allowed');
  if (/^\[credential\b/.test(section)) throw unsafe('Git credential helpers are not allowed');
  if (
    section !== '[core]'
    && section !== '[remote "origin"]'
    && !/^\[branch "[^"\r\n]+"\]$/.test(section)
  ) {
    throw unsafe('unexpected local Git config section');
  }
}

function inspectCoreKey(key) {
  const dangerous = {
    fsmonitor: 'filesystem monitor',
    hookspath: 'hooks path',
    worktree: 'worktree redirect',
    sshcommand: 'SSH command',
  };
  if (Object.hasOwn(dangerous, key)) {
    throw unsafe(`Git ${dangerous[key]} is not allowed`);
  }
  if (!ALLOWED_CORE_KEYS.has(key)) throw unsafe('unexpected local Git core setting');
}

function inspectRemoteKey({ key, value, origins, fetches, tagOptions }) {
  if (['uploadpack', 'receivepack'].includes(key)) {
    throw unsafe('Git remote command redirect is not allowed');
  }
  if (key === 'url') origins.push(value);
  else if (key === 'fetch') fetches.push(value);
  else if (key === 'tagopt') tagOptions.push(value);
  else throw unsafe('unexpected local Git remote setting');
}

function inspectBranchKey({ section, key, value, branches }) {
  if (!['remote', 'merge'].includes(key)) {
    throw unsafe('unexpected local Git branch setting');
  }
  const values = branches.get(section) ?? {};
  if (Object.hasOwn(values, key)) throw unsafe('duplicate local Git branch setting');
  values[key] = value;
  branches.set(section, values);
}

function unsafe(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_UNSAFE' });
}

function mismatch(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_MISMATCH' });
}
