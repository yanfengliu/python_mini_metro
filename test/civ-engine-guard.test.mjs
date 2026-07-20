import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import * as guardModule from '../scripts/civ-engine-guard.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { dispatchPublicNodeCommand } = guardModule;

test('guard entry point rejects tainted Node startup before dispatch categorically', async () => {
  const cases = [
    {
      nodeOptions: '--import=data:text/javascript,globalThis.secretNodeOptions=true',
      execArgv: [],
    },
    {
      nodeOptions: '',
      execArgv: [
        '--import=data:text/javascript,globalThis.secretExecArgv=true',
      ],
    },
  ];
  const messages = [];

  for (const startup of cases) {
    let dispatched = false;
    await assert.rejects(
      guardModule.runGuardEntryPoint({
        argv: ['test'],
        ...startup,
        dispatch: async () => {
          dispatched = true;
          return { exitCode: 0, signal: null };
        },
      }),
      (error) => {
        messages.push(error?.message);
        return (
          error?.code === 'ERR_CIV_ENGINE_NODE_STARTUP'
          && error.message === 'public Node entry point requires clean startup'
          && (!startup.nodeOptions || !error.message.includes(startup.nodeOptions))
          && startup.execArgv.every((argument) => !error.message.includes(argument))
        );
      },
    );
    assert.equal(dispatched, false);
  }

  assert.deepEqual(new Set(messages), new Set([
    'public Node entry point requires clean startup',
  ]));
  const cleanResult = await guardModule.runGuardEntryPoint({
    argv: ['test'],
    nodeOptions: '',
    execArgv: [],
    dispatch: async ({ argv }) => {
      assert.deepEqual(argv, ['test']);
      return { exitCode: 0, signal: null };
    },
  });
  assert.deepEqual(cleanResult, { exitCode: 0, signal: null });
});

test('guard dispatches fixed Node bodies and forwards only script arguments unchanged', async () => {
  const cases = [
    {
      argv: ['test'],
      bodyArgs: ['--test'],
    },
    {
      argv: ['playtest:verify', 'output/recursive/example'],
      bodyArgs: ['scripts/playtest-verify.mjs', 'output/recursive/example'],
    },
    {
      argv: ['playtest:recursive', '--scenario', 'fixtures/example.json'],
      bodyArgs: [
        'scripts/playtest-recursive.mjs',
        '--scenario',
        'fixtures/example.json',
      ],
    },
  ];

  for (const fixture of cases) {
    const events = [];
    const lease = { token: 'fixture-lease' };
    const result = await dispatchPublicNodeCommand({
      argv: fixture.argv,
      acquire: async (options) => {
        assert.deepEqual(options, { repoRoot });
        events.push({ phase: 'acquire' });
        return lease;
      },
      verify: async (options) => { events.push({ phase: 'verify', options }); },
      spawn: async (plan) => {
        events.push({ phase: 'spawn', plan });
        return { exitCode: 0, signal: null };
      },
      release: async (candidate) => {
        assert.equal(candidate, lease);
        events.push({ phase: 'release' });
      },
    });

    assert.deepEqual(events.map(({ phase }) => phase), [
      'acquire',
      'verify',
      'spawn',
      'release',
    ]);
    assert.equal(events[1].options.allowDirty, false);
    assert.equal(events[1].options.lease, lease);
    assert.equal(events[2].plan.command, process.execPath);
    assert.deepEqual(events[2].plan.args, fixture.bodyArgs);
    assert.equal(events[2].plan.cwd, repoRoot);
    assert.equal(events[2].plan.shell, false);
    assert.deepEqual(result, { exitCode: 0, signal: null });
  }
});

test('test guard rejects every forwarded argument before effects without reflecting it', async () => {
  const cases = [
    ['--import=data:text/javascript,globalThis.secretImportSentinel=true'],
    ['test/secret-file-operand-sentinel.test.mjs'],
    ['--test-name-pattern', 'secret-option-value-sentinel'],
  ];
  const messages = [];

  for (const forwardedArgs of cases) {
    const phases = [];
    await assert.rejects(
      dispatchPublicNodeCommand({
        argv: ['test', ...forwardedArgs],
        acquire: async () => { phases.push('acquire'); },
        verify: async () => { phases.push('verify'); },
        spawn: async () => { phases.push('spawn'); },
        release: async () => { phases.push('release'); },
      }),
      (error) => {
        messages.push(error?.message);
        return (
          error?.code === 'ERR_CIV_ENGINE_GUARD_TEST_ARGS'
          && error.message === 'public test command accepts no arguments'
          && forwardedArgs.every((argument) => !error.message.includes(argument))
        );
      },
    );
    assert.deepEqual(phases, []);
  }

  assert.deepEqual(new Set(messages), new Set([
    'public test command accepts no arguments',
  ]));
});

test('strict test and verifier guards reject attributed content mismatch before body effects', async () => {
  for (const argv of [
    ['test'],
    ['playtest:verify', '--allow-dirty'],
  ]) {
    let bodyStarted = false;
    let released = false;
    const lease = { token: 'strict-lease' };
    await assert.rejects(
      dispatchPublicNodeCommand({
        argv,
        acquire: async () => lease,
        verify: async ({ allowDirty }) => {
          assert.equal(allowDirty, false);
          throw provenanceFailure('content');
        },
        spawn: async () => { bodyStarted = true; },
        release: async (candidate) => {
          assert.equal(candidate, lease);
          released = true;
        },
      }),
      (error) => error?.code === 'ERR_CIV_ENGINE_PROVENANCE',
    );
    assert.equal(bodyStarted, false);
    assert.equal(released, true);
  }
});

test('recursive guard derives strict versus canary policy from forwarded arguments', async () => {
  const cases = [
    {
      argv: ['playtest:recursive', '--scenario', 'strict.json'],
      expectedAllowDirty: false,
      bodyStarts: false,
    },
    {
      argv: ['playtest:recursive', '--allow-dirty', '--scenario', 'canary.json'],
      expectedAllowDirty: true,
      bodyStarts: true,
    },
  ];

  for (const fixture of cases) {
    let capturedPlan = null;
    let released = false;
    const lease = { token: 'recursive-lease' };
    const invocation = dispatchPublicNodeCommand({
      argv: fixture.argv,
      acquire: async () => lease,
      verify: async ({ allowDirty }) => {
        assert.equal(allowDirty, fixture.expectedAllowDirty);
        if (!allowDirty) throw provenanceFailure('content');
      },
      spawn: async (plan) => {
        capturedPlan = plan;
        return { exitCode: 0, signal: null };
      },
      release: async (candidate) => {
        assert.equal(candidate, lease);
        released = true;
      },
    });

    if (!fixture.bodyStarts) {
      await assert.rejects(
        invocation,
        (error) => error?.code === 'ERR_CIV_ENGINE_PROVENANCE',
      );
      assert.equal(capturedPlan, null);
      assert.equal(released, true);
      continue;
    }

    await invocation;
    assert.equal(released, true);
    assert.deepEqual(capturedPlan.args, [
      'scripts/playtest-recursive.mjs',
      ...fixture.argv.slice(1),
    ]);
  }
});

test('identity mismatch blocks every guarded body even in recursive canary mode', async () => {
  for (const argv of [
    ['test'],
    ['playtest:verify', 'output/recursive/example'],
    ['playtest:recursive'],
    ['playtest:recursive', '--allow-dirty'],
  ]) {
    let bodyStarted = false;
    let released = false;
    const lease = { token: 'identity-lease' };
    await assert.rejects(
      dispatchPublicNodeCommand({
        argv,
        acquire: async () => lease,
        verify: async () => { throw provenanceFailure('identity'); },
        spawn: async () => { bodyStarted = true; },
        release: async (candidate) => {
          assert.equal(candidate, lease);
          released = true;
        },
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_PROVENANCE'
        && /identity/.test(error.message)
      ),
    );
    assert.equal(bodyStarted, false);
    assert.equal(released, true);
  }
});

test('unknown guarded commands fail before verification or process launch', async () => {
  const untrustedCommand = 'secret-command-value';
  let acquired = false;
  let verified = false;
  let bodyStarted = false;
  let released = false;
  await assert.rejects(
    dispatchPublicNodeCommand({
      argv: [untrustedCommand],
      acquire: async () => { acquired = true; },
      verify: async () => { verified = true; },
      spawn: async () => { bodyStarted = true; },
      release: async () => { released = true; },
    }),
    (error) => (
      error?.message === 'unknown public Node command'
      && !error.message.includes(untrustedCommand)
    ),
  );
  assert.equal(acquired, false);
  assert.equal(verified, false);
  assert.equal(bodyStarted, false);
  assert.equal(released, false);
});

test('guard preserves primary and release failures without reflecting diagnostics', async () => {
  const lease = { token: 'combined-failure-lease' };
  const primary = provenanceFailure('secret-primary-detail');
  const recovery = new Error('secret-release-detail');
  recovery.code = 'ERR_CIV_ENGINE_SETUP_OWNERSHIP';
  await assert.rejects(
    dispatchPublicNodeCommand({
      argv: ['test'],
      acquire: async () => lease,
      verify: async () => { throw primary; },
      spawn: async () => ({ exitCode: 0, signal: null }),
      release: async () => { throw recovery; },
    }),
    (error) => (
      error instanceof AggregateError
      && error.code === primary.code
      && error.cause === primary
      && error.errors.includes(primary)
      && error.errors.includes(recovery)
      && !error.message.includes('secret-primary-detail')
      && !error.message.includes('secret-release-detail')
    ),
  );
});

test('recursive guard parses option positions before acquiring the lease', async () => {
  for (const argv of [
    ['playtest:recursive', '--unknown'],
    ['playtest:recursive', '--scenario'],
    ['playtest:recursive', '--output-root'],
  ]) {
    const phases = [];
    await assert.rejects(
      dispatchPublicNodeCommand({
        argv,
        acquire: async () => { phases.push('acquire'); },
        verify: async () => { phases.push('verify'); },
        spawn: async () => { phases.push('spawn'); },
        release: async () => { phases.push('release'); },
      }),
      /unknown argument|missing value/i,
    );
    assert.deepEqual(phases, []);
  }

  const forwardedArgs = [
    '--scenario',
    '--allow-dirty',
    '--output-root',
    'output/canary-name',
  ];
  let capturedAllowDirty = null;
  let capturedBodyArgs = null;
  const lease = { token: 'parser-lease' };
  await dispatchPublicNodeCommand({
    argv: ['playtest:recursive', ...forwardedArgs],
    acquire: async () => lease,
    verify: async ({ allowDirty }) => { capturedAllowDirty = allowDirty; },
    spawn: async ({ args }) => {
      capturedBodyArgs = args;
      return { exitCode: 0, signal: null };
    },
    release: async (candidate) => { assert.equal(candidate, lease); },
  });
  assert.equal(capturedAllowDirty, false);
  assert.deepEqual(capturedBodyArgs, [
    'scripts/playtest-recursive.mjs',
    ...forwardedArgs,
  ]);

  capturedAllowDirty = null;
  await dispatchPublicNodeCommand({
    argv: ['playtest:recursive', '--output-root', '--allow-dirty'],
    acquire: async () => lease,
    verify: async ({ allowDirty }) => { capturedAllowDirty = allowDirty; },
    spawn: async () => ({ exitCode: 0, signal: null }),
    release: async (candidate) => { assert.equal(candidate, lease); },
  });
  assert.equal(capturedAllowDirty, false);
});

test('guard excludes concurrent setup and releases its lease on every later failure', async () => {
  const locked = new Error('fixture setup is active');
  locked.code = 'ERR_CIV_ENGINE_SETUP_LOCKED';
  const excludedPhases = [];
  await assert.rejects(
    dispatchPublicNodeCommand({
      argv: ['test'],
      acquire: async () => {
        excludedPhases.push('acquire');
        throw locked;
      },
      verify: async () => { excludedPhases.push('verify'); },
      spawn: async () => { excludedPhases.push('spawn'); },
      release: async () => { excludedPhases.push('release'); },
    }),
    (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LOCKED',
  );
  assert.deepEqual(excludedPhases, ['acquire']);

  for (const failurePhase of ['verify', 'spawn']) {
    const phases = [];
    const lease = { token: `${failurePhase}-failure-lease` };
    const failure = new Error(`fixture ${failurePhase} failure`);
    await assert.rejects(
      dispatchPublicNodeCommand({
        argv: ['test'],
        acquire: async () => {
          phases.push('acquire');
          return lease;
        },
        verify: async () => {
          phases.push('verify');
          if (failurePhase === 'verify') throw failure;
        },
        spawn: async () => {
          phases.push('spawn');
          throw failure;
        },
        release: async (candidate) => {
          assert.equal(candidate, lease);
          phases.push('release');
        },
      }),
      (error) => error === failure,
    );
    assert.deepEqual(
      phases,
      failurePhase === 'verify'
        ? ['acquire', 'verify', 'release']
        : ['acquire', 'verify', 'spawn', 'release'],
    );
  }

  const childFailurePhases = [];
  const childFailureLease = { token: 'child-failure-lease' };
  const childResult = await dispatchPublicNodeCommand({
    argv: ['test'],
    acquire: async () => {
      childFailurePhases.push('acquire');
      return childFailureLease;
    },
    verify: async () => { childFailurePhases.push('verify'); },
    spawn: async () => {
      childFailurePhases.push('spawn');
      return { exitCode: 7, signal: null };
    },
    release: async (candidate) => {
      assert.equal(candidate, childFailureLease);
      childFailurePhases.push('release');
    },
  });
  assert.deepEqual(childResult, { exitCode: 7, signal: null });
  assert.deepEqual(childFailurePhases, [
    'acquire',
    'verify',
    'spawn',
    'release',
  ]);
});

function provenanceFailure(kind) {
  const error = new Error(`fixture ${kind} mismatch`);
  error.code = 'ERR_CIV_ENGINE_PROVENANCE';
  return error;
}
