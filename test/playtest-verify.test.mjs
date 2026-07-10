import assert from 'node:assert/strict';
import test from 'node:test';

import { assertImprovementFinding, stateDigest } from 'civ-engine';

import { compareEvidence } from '../scripts/playtest-verify.mjs';

function finding(overrides = {}) {
  return {
    schemaVersion: 2,
    id: 'path-topology-mismatch-step-0',
    title: 'Observation path topology mismatch',
    severity: 'high',
    category: 'regression',
    observed: 'Structured and array path station order disagree.',
    expected: 'Both observation views describe the same station order.',
    suggestion: 'Keep both observation encodings aligned.',
    area: 'programmatic observation',
    evidence: [{ kind: 'step', step: 0 }],
    verificationStatus: 'unverified',
    nextAction: 'manualFix',
    promotionTarget: 'test',
    disposition: 'candidate',
    data: { class: 'observation-path-topology-mismatch' },
    ...overrides,
  };
}

function transcript(checkpoints) {
  return checkpoints.map((checkpoint, index) => ({
    index,
    name: `op-${index}`,
    action: { type: 'noop' },
    requestedDtMs: 1,
    effectiveDtMs: 1,
    actionOk: true,
    reward: 0,
    done: false,
    checkpoint,
  }));
}

test('matching checkpoints and exact replay findings become strict verified findings', () => {
  const authored = [finding()];
  const comparison = compareEvidence({
    originalTranscript: transcript([{ score: 0 }, { score: 1 }]),
    replayTranscript: transcript([{ score: 0 }, { score: 1 }]),
    originalFindings: authored,
    replayFindings: structuredClone(authored),
    originalRunId: 'run-original',
    replayRunId: 'run-redrive',
  });

  assert.equal(comparison.verification.ok, true);
  assert.equal(comparison.verification.finalStateMatches, true);
  assert.equal(comparison.verification.findingsMatch, true);
  assert.equal(comparison.verifiedFindings.length, 1);
  const verified = comparison.verifiedFindings[0];
  assert.equal(verified.verificationStatus, 'verified');
  assert.equal(verified.verificationMethod, 'replay');
  assert.deepEqual(verified.evidence.at(-1), {
    kind: 'bundle',
    sessionId: 'run-original',
  });
  assert.doesNotThrow(() => assertImprovementFinding(verified, {
    requireVerificationEvidence: true,
  }));
});

test('same finding class with a changed claim does not verify', () => {
  const comparison = compareEvidence({
    originalTranscript: transcript([{ score: 0 }]),
    replayTranscript: transcript([{ score: 0 }]),
    originalFindings: [finding()],
    replayFindings: [finding({ observed: 'A different replay-side claim.' })],
    originalRunId: 'run-original',
    replayRunId: 'run-redrive',
  });

  assert.equal(comparison.verification.ok, false);
  assert.equal(comparison.verification.finalStateMatches, true);
  assert.equal(comparison.verification.findingsMatch, false);
  assert.deepEqual(comparison.verifiedFindings, []);
  assert.equal(comparison.verificationFindings.length, 1);
  assert.equal(
    comparison.verificationFindings[0].data.class,
    'deterministic-replay-mismatch',
  );
  assert.equal(
    comparison.verificationFindings[0].verificationStatus,
    'unverified',
  );
});

test('a checkpoint-vector mismatch is a hard unverified nondeterminism finding', () => {
  const comparison = compareEvidence({
    originalTranscript: transcript([{ score: 0 }, { score: 1 }]),
    replayTranscript: transcript([{ score: 0 }, { score: 2 }]),
    originalFindings: [],
    replayFindings: [],
    originalRunId: 'run-original',
    replayRunId: 'run-redrive',
  });

  assert.equal(comparison.verification.ok, false);
  assert.equal(comparison.verification.finalStateMatches, false);
  assert.equal(comparison.verificationFindings.length, 1);
  assert.doesNotThrow(() => assertImprovementFinding(
    comparison.verificationFindings[0],
    { requireVerificationEvidence: false },
  ));
});

test('the verifier rejects findings that were born verified', () => {
  assert.throws(
    () => compareEvidence({
      originalTranscript: transcript([{ score: 0 }]),
      replayTranscript: transcript([{ score: 0 }]),
      originalFindings: [finding({
        verificationStatus: 'verified',
        verificationMethod: 'replay',
        evidence: [{ kind: 'bundle', sessionId: 'illegally-born-verified' }],
      })],
      replayFindings: [],
      originalRunId: 'run-original',
      replayRunId: 'run-redrive',
    }),
    /born unverified/i,
  );
});

test('stateDigest changes for every determinism-critical checkpoint family', () => {
  const base = {
    environment: { dtMsDefault: 16, lastScore: 0 },
    progression: { score: 0, unlockedNumPaths: 1 },
    spawning: { stations: [{ stepsSinceLastSpawn: 0, intervalSteps: 600 }] },
    travelPlans: [{ passengerIndex: 0, nextStationIndex: 1 }],
    metroMotion: [{ speed: 0.15, stopTimeRemainingMs: 0 }],
    rng: { python: [3, [1, 2]], numpy: ['MT19937', [3, 4]] },
  };
  const mutations = [
    (value) => { value.environment.lastScore = 1; },
    (value) => { value.progression.unlockedNumPaths = 2; },
    (value) => { value.spawning.stations[0].stepsSinceLastSpawn = 1; },
    (value) => { value.travelPlans[0].nextStationIndex = 2; },
    (value) => { value.metroMotion[0].stopTimeRemainingMs = 500; },
    (value) => { value.rng.python[1][0] = 9; },
  ];
  const baseline = stateDigest(base);
  for (const mutate of mutations) {
    const changed = structuredClone(base);
    mutate(changed);
    assert.notEqual(stateDigest(changed), baseline);
  }
});
