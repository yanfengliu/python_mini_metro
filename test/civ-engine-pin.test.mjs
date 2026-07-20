import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  CIV_ENGINE_PACKAGE_SPEC,
  CIV_ENGINE_PIN,
  EXPECTED_CIV_ENGINE_COMMIT,
  EXPECTED_CIV_ENGINE_TREE_DIGEST,
  EXPECTED_CIV_ENGINE_VERSION,
  EXPECTED_ROOT_LOCK_DIGEST,
  resolveCivEnginePinRoot,
  validateCivEnginePin,
} from '../scripts/civ-engine-pin.mjs';
import { digestParsedRootLock } from '../scripts/civ-engine-setup-root-contract.mjs';
import {
  assertCivEngineStateAllowed,
  captureCivEngineState,
} from '../scripts/source-provenance-engine.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const expectedPin = {
  schemaVersion: 1,
  packageName: 'civ-engine',
  repositoryUrl: 'https://github.com/yanfengliu/civ-engine.git',
  installPath: '.civ-engine-pin',
  version: '2.2.0',
  commit: 'e0cb614a516c449159a4562c2ac45bd40bffd3df',
  rootLockSha256: '40927f3d860f5b0a8bc1e3360f9ffc0552a2ef4076d671714999effaa72149e5',
  runtimeTreeSha256: '960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891',
};

const baselineTestNames = [
  'source and resolved engine inventories are deterministic and clean at the pin',
  'only relevant source changes affect dirty state and the tree digest',
  'artifact writer records a tracked dirty patch and exposes a stable summary',
  'clean artifact writer omits the patch and refuses to overwrite evidence',
  'same-version modified engine runtime changes its digest and requires override',
  'engine runtime digest canonicalizes platform text line endings',
  'wrong clean engine commit fails closed unless mismatch evidence is allowed',
  'dirty sibling outside dist fails closed and remains fully attributable',
  'start/end comparison catches local or engine mutation with both snapshots',
  'an unavailable resolved engine fails closed even with dirty override',
  'pass and run manifests satisfy engine and repo completeness contracts',
  'new manifests require strict source state while legacy rows remain readable',
  'repo completeness rejects sparse engine-valid manifests',
  'repo completeness rejects invalid outcomes, seeds, and artifact descriptors',
  'candidate selection requires strict verified evidence, routing, and stable class',
  'manifest files and ledgers are validated after read-back',
  'persistence rejects nonexistent artifact paths before writing',
  'manifest-pair transactions serialize concurrent writers and exact retries',
  'durable pair intent reconciles a crash between ledger appends',
  'repoRelativePath returns portable in-repo paths and rejects escape',
  'a stale heartbeat from a live owner is never stolen',
  'a stale lock is recovered only after its owner is dead',
  'an old owner cannot release a successor lock',
  'one reconciliation drains many intents after confirming both ledgers',
  'crash repair retains the intent until both rows are durably confirmed',
  'versioned finalization intent repairs every persistence boundary',
  'versioned finalization serializes concurrent writers and exact retries',
  'pending intent repairs an unterminated final JSONL fragment',
  'reconciliation fails closed for terminated or earlier JSONL corruption',
  'matching checkpoints and exact replay findings become strict verified findings',
  'same finding class with a changed claim does not verify',
  'a checkpoint-vector mismatch is a hard unverified nondeterminism finding',
  'the verifier rejects findings that were born verified',
  'stateDigest changes for every determinism-critical checkpoint family',
  'replay input projection preserves immutable v2 and v3 environment contracts',
  'default recursive pass writes verified evidence and complete ledgers',
  'a missing Python executable appends exactly one attributable failure row',
  'a nonzero child appends exactly one attributable failure row',
  'an unparseable scenario appends exactly one attributable failure row',
  'normal recursive CLI refuses relevant dirty source without override',
  'mid-run source drift records a complete final source patch',
  'public verifier recovers append-only after a failed first attempt',
  'public verifier replays genuine v1 inputs without a reward-contract field',
  'public verifier replays literal v2 inputs at the historical threshold',
];

test('checked-in civ-engine pin is exact, frozen, and source-compatible', () => {
  assert.deepEqual(CIV_ENGINE_PIN, expectedPin);
  assert.equal(Object.isFrozen(CIV_ENGINE_PIN), true);
  assert.equal(CIV_ENGINE_PACKAGE_SPEC, 'file:.civ-engine-pin');
  assert.equal(EXPECTED_CIV_ENGINE_VERSION, expectedPin.version);
  assert.equal(EXPECTED_CIV_ENGINE_COMMIT, expectedPin.commit);
  assert.equal(EXPECTED_ROOT_LOCK_DIGEST, expectedPin.rootLockSha256);
  assert.equal(EXPECTED_CIV_ENGINE_TREE_DIGEST, expectedPin.runtimeTreeSha256);
  assert.equal(
    resolveCivEnginePinRoot(repoRoot),
    path.join(repoRoot, '.civ-engine-pin'),
  );
});

test('pin validator rejects every unsafe or ambiguous descriptor dimension', () => {
  const invalidPins = [
    { ...expectedPin, extra: true },
    withoutKey(expectedPin, 'version'),
    withoutKey(expectedPin, 'rootLockSha256'),
    { ...expectedPin, schemaVersion: 2 },
    { ...expectedPin, packageName: 'other-engine' },
    { ...expectedPin, repositoryUrl: 'http://github.com/yanfengliu/civ-engine.git' },
    { ...expectedPin, repositoryUrl: 'https://token@github.com/yanfengliu/civ-engine.git' },
    { ...expectedPin, repositoryUrl: 'https://example.com/yanfengliu/civ-engine.git' },
    { ...expectedPin, repositoryUrl: `${expectedPin.repositoryUrl}?ref=main` },
    { ...expectedPin, version: '2.2' },
    { ...expectedPin, version: 'v2.2.0' },
    { ...expectedPin, version: '2.2.0-01' },
    { ...expectedPin, version: '2.2.0-alpha.01' },
    { ...expectedPin, commit: expectedPin.commit.toUpperCase() },
    { ...expectedPin, commit: expectedPin.commit.slice(1) },
    { ...expectedPin, rootLockSha256: expectedPin.rootLockSha256.toUpperCase() },
    { ...expectedPin, rootLockSha256: expectedPin.rootLockSha256.slice(1) },
    { ...expectedPin, runtimeTreeSha256: expectedPin.runtimeTreeSha256.toUpperCase() },
    { ...expectedPin, runtimeTreeSha256: expectedPin.runtimeTreeSha256.slice(1) },
    { ...expectedPin, installPath: '../civ-engine' },
    { ...expectedPin, installPath: 'nested/../.civ-engine-pin' },
    { ...expectedPin, installPath: 'nested\\civ-engine' },
    { ...expectedPin, installPath: '/tmp/civ-engine' },
    { ...expectedPin, installPath: 'C:/tmp/civ-engine' },
    { ...expectedPin, installPath: '.' },
    { ...expectedPin, installPath: '.civ-engine-pin/' },
    { ...expectedPin, installPath: 'scripts' },
    { ...expectedPin, installPath: '.git' },
    { ...expectedPin, installPath: 'node_modules' },
    { ...expectedPin, installPath: 'output' },
  ];

  for (const candidate of invalidPins) {
    assert.throws(
      () => validateCivEnginePin(candidate),
      { name: 'TypeError' },
      JSON.stringify(candidate),
    );
  }

  const validated = validateCivEnginePin({ ...expectedPin });
  assert.deepEqual(validated, expectedPin);
  assert.equal(Object.isFrozen(validated), true);
});

test('root lock digest is canonical across formatting and object key order', () => {
  const first = JSON.parse('{"packages":{"node_modules/a":{"dev":true,"version":"1.0.0"}},"lockfileVersion":3}');
  const reordered = JSON.parse(`{
    "lockfileVersion": 3,
    "packages": {
      "node_modules/a": {
        "version": "1.0.0",
        "dev": true
      }
    }
  }`);
  assert.equal(digestParsedRootLock(first), digestParsedRootLock(reordered));
  reordered.packages['node_modules/a'].version = '1.0.1';
  assert.notEqual(digestParsedRootLock(first), digestParsedRootLock(reordered));
});

test('pin root resolution is explicit, contained, and independent of cwd', () => {
  const firstRoot = path.join(repoRoot, 'first-root');
  const secondRoot = path.join(repoRoot, 'second-root');
  assert.equal(
    resolveCivEnginePinRoot(firstRoot),
    path.join(firstRoot, expectedPin.installPath),
  );
  assert.equal(
    resolveCivEnginePinRoot(secondRoot),
    path.join(secondRoot, expectedPin.installPath),
  );
  assert.throws(
    () => resolveCivEnginePinRoot(repoRoot, {
      ...expectedPin,
      installPath: '../outside',
    }),
    { name: 'TypeError' },
  );
  assert.throws(
    () => resolveCivEnginePinRoot('relative-repository-root'),
    { name: 'TypeError' },
  );

  const moduleUrl = pathToFileURL(path.join(
    repoRoot,
    'scripts',
    'civ-engine-pin.mjs',
  )).href;
  for (const cwd of [path.join(repoRoot, 'scripts'), path.join(repoRoot, 'test')]) {
    const child = spawnSync(process.execPath, [
      '--input-type=module',
      '-e',
      `import { resolveCivEnginePinRoot } from ${JSON.stringify(moduleUrl)}; `
      + `console.log(resolveCivEnginePinRoot(${JSON.stringify(repoRoot)}));`,
    ], {
      cwd,
      encoding: 'utf8',
      shell: false,
    });
    assert.equal(child.status, 0, child.stderr || child.stdout);
    assert.equal(child.stdout.trim(), path.join(repoRoot, expectedPin.installPath));
  }
});

test('package lock npm ignore and CI resolution agree with the descriptor', async () => {
  const [packageText, lockText, npmrc, gitignore, workflow] = await Promise.all([
    readFile(path.join(repoRoot, 'package.json'), 'utf8'),
    readFile(path.join(repoRoot, 'package-lock.json'), 'utf8'),
    readFile(path.join(repoRoot, '.npmrc'), 'utf8'),
    readFile(path.join(repoRoot, '.gitignore'), 'utf8'),
    readFile(path.join(repoRoot, '.github', 'workflows', 'test.yml'), 'utf8'),
  ]);
  const packageDocument = JSON.parse(packageText);
  const lock = JSON.parse(lockText);

  assert.equal(digestParsedRootLock(lock), CIV_ENGINE_PIN.rootLockSha256);

  assert.equal(packageDocument.dependencies[CIV_ENGINE_PIN.packageName], CIV_ENGINE_PACKAGE_SPEC);
  assert.equal(
    packageDocument.scripts['setup:civ-engine'],
    'node scripts/civ-engine-setup.mjs',
  );
  assert.equal(
    packageDocument.scripts.pretest,
    'node scripts/civ-engine-setup.mjs --verify-only',
  );
  assert.equal(
    packageDocument.scripts['preplaytest:verify'],
    'node scripts/civ-engine-setup.mjs --verify-only',
  );
  assert.equal(
    packageDocument.scripts['preplaytest:recursive'],
    'node scripts/civ-engine-setup.mjs --verify-only --allow-dirty',
  );
  assert.equal(packageDocument.scripts.test, 'node scripts/civ-engine-guard.mjs test');
  assert.equal(
    packageDocument.scripts['playtest:verify'],
    'node scripts/civ-engine-guard.mjs playtest:verify',
  );
  assert.equal(
    packageDocument.scripts['playtest:recursive'],
    'node scripts/civ-engine-guard.mjs playtest:recursive',
  );
  assert.equal(lock.packages[''].dependencies[CIV_ENGINE_PIN.packageName], CIV_ENGINE_PACKAGE_SPEC);
  assert.equal(lock.packages[CIV_ENGINE_PIN.installPath].version, CIV_ENGINE_PIN.version);
  assert.deepEqual(lock.packages[`node_modules/${CIV_ENGINE_PIN.packageName}`], {
    resolved: CIV_ENGINE_PIN.installPath,
    link: true,
  });
  assert.doesNotMatch(packageText, /\.\.\/civ-engine/);
  assert.doesNotMatch(lockText, /\.\.\/civ-engine/);
  assert.equal(
    npmrc.replace(/\r\n/g, '\n'),
    'install-links=false\nloglevel=silent\n',
  );
  assert.match(gitignore, /^\/\.civ-engine-pin\/$/m);
  assert.match(gitignore, /^\/\.civ-engine-setup\.lock$/m);
  assert.match(gitignore, /^\/\.civ-engine-setup-\*\/$/m);
  assert.match(workflow, /^permissions:\s*\n  contents: read$/m);
  const workflowSteps = workflow
    .split(/^      - /m)
    .slice(1);
  const checkoutSteps = workflowSteps
    .filter((step) => /^(?:        )?uses: actions\/checkout@/m.test(step));
  assert.equal(checkoutSteps.length, 2);
  for (const checkoutStep of checkoutSteps) {
    assert.match(checkoutStep, /^          persist-credentials: false$/m);
    assert.match(checkoutStep, /^          fetch-depth: 0$/m);
  }
  const buildJob = workflow.slice(
    workflow.indexOf('  build:'),
    workflow.indexOf('  rl-smoke:'),
  );
  const windowsJob = workflow.slice(workflow.indexOf('  rl-smoke:'));
  assert.match(buildJob, /^        run: npm run setup:civ-engine$/m);
  assert.match(buildJob, /^        run: npm test$/m);
  assert.match(buildJob, /^        run: npm run playtest:recursive$/m);
  assert.ok(
    buildJob.indexOf('run: npm run setup:civ-engine')
      < buildJob.indexOf('run: npm test'),
  );
  assert.ok(
    buildJob.indexOf('run: npm test')
      < buildJob.indexOf('run: npm run playtest:recursive'),
  );
  assert.match(windowsJob, /uses: actions\/setup-node@/);
  assert.match(windowsJob, /^        run: npm run setup:civ-engine$/m);
  assert.match(
    windowsJob,
    /^        run: npm run setup:civ-engine -- --verify-only$/m,
  );
  assert.ok(
    windowsJob.indexOf('run: npm run setup:civ-engine')
      < windowsJob.indexOf('run: npm run setup:civ-engine -- --verify-only'),
  );
  assert.doesNotMatch(workflow, /repository: yanfengliu\/civ-engine/);
  assert.doesNotMatch(workflow, /working-directory: .*\.civ-engine-pin/);
  assert.doesNotMatch(workflow, /captureCivEngineState/);
  assert.doesNotMatch(workflow, /^        run: npm ci(?:\s|$)/m);
});

test('default provenance attests the exact isolated package ESM will execute', async () => {
  const state = await captureCivEngineState({ repoRoot });
  const expectedRoot = normalize(await realpath(resolveCivEnginePinRoot(repoRoot)));
  const expectedRuntime = normalize(await realpath(path.join(
    resolveCivEnginePinRoot(repoRoot),
    'dist',
    'index.js',
  )));

  assert.equal(state.available, true);
  assert.equal(state.locationMatches, true);
  assert.equal(state.runtimeEntryMatches, true);
  assert.equal(state.localExpectedPackageRoot, expectedRoot);
  assert.equal(state.localResolvedPackageRoot, expectedRoot);
  assert.equal(state.localResolvedRuntimeEntry, expectedRuntime);
  assert.equal(state.packageVersion, CIV_ENGINE_PIN.version);
  assert.equal(state.gitCommit, CIV_ENGINE_PIN.commit);
  assert.equal(state.treeDigest, CIV_ENGINE_PIN.runtimeTreeSha256);
  assert.doesNotThrow(() => assertCivEngineStateAllowed(state));
});

test('all 44 pre-GM04 Node contract names remain registered', async () => {
  assert.equal(baselineTestNames.length, 44);
  assert.equal(new Set(baselineTestNames).size, 44);
  const testRoot = path.join(repoRoot, 'test');
  const testFiles = (await readdir(testRoot))
    .filter((name) => name.endsWith('.test.mjs') && name !== 'civ-engine-pin.test.mjs');
  const registered = new Set();
  for (const fileName of testFiles) {
    const source = await readFile(path.join(testRoot, fileName), 'utf8');
    for (const match of source.matchAll(/^test\('([^']+)'/gm)) registered.add(match[1]);
  }
  for (const name of baselineTestNames) {
    assert.equal(registered.has(name), true, `missing baseline Node test: ${name}`);
  }
});

function withoutKey(value, key) {
  const clone = { ...value };
  delete clone[key];
  return clone;
}

function normalize(value) {
  return value.split(path.sep).join('/');
}
