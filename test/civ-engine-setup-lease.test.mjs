import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import test from 'node:test';

import {
  acquireCivEngineVerificationLease,
  releaseCivEngineVerificationLease,
  verifyCivEngineSetupUnderLease,
} from '../scripts/civ-engine-setup.mjs';
import {
  acquireSetupLock,
  assertSetupLockOwnership,
  releaseSetupLock,
} from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('verification lease excludes setup and remains owned through verification', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const events = [];
    const operations = leaseOperations(events);
    const lease = await acquireCivEngineVerificationLease({
      repoRoot: fixtureRoot,
      operations,
    });
    assert.deepEqual(Object.keys(lease), ['repoRoot']);
    await assert.rejects(
      acquireSetupLock({ repoRoot: fixtureRoot }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LOCKED',
    );
    await verifyCivEngineSetupUnderLease({
      repoRoot: fixtureRoot,
      allowDirty: true,
      lease,
    });
    assert.deepEqual(events, [
      'acquire',
      'ownership',
      'verify:true',
      'ownership',
    ]);
    await releaseCivEngineVerificationLease(lease);
    assert.deepEqual(events, [
      'acquire',
      'ownership',
      'verify:true',
      'ownership',
      'release',
    ]);
    await assert.rejects(
      verifyCivEngineSetupUnderLease({ repoRoot: fixtureRoot, lease }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LEASE',
    );
  });
});

test('verification lease reasserts ownership after asynchronous verification', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const events = [];
    const operations = leaseOperations(events, {
      mutateOwnershipDuringVerification: true,
    });
    const lease = await acquireCivEngineVerificationLease({
      repoRoot: fixtureRoot,
      operations,
    });

    await assert.rejects(
      verifyCivEngineSetupUnderLease({ repoRoot: fixtureRoot, lease }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP',
    );
    assert.deepEqual(events, [
      'acquire',
      'ownership',
      'verify:false',
      'mutate-ownership',
      'ownership',
    ]);
  });
});

test('verification failure leaves the lease held for explicit release', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    const operations = leaseOperations([], { failVerification: true });
    const lease = await acquireCivEngineVerificationLease({
      repoRoot: fixtureRoot,
      operations,
    });
    await assert.rejects(
      verifyCivEngineSetupUnderLease({ repoRoot: fixtureRoot, lease }),
      /fixture verification failure/,
    );
    await assert.rejects(
      acquireSetupLock({ repoRoot: fixtureRoot }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LOCKED',
    );
    await releaseCivEngineVerificationLease(lease);
  });
});

test('forged or cross-repository leases fail before verification', async () => {
  await withSetupRepository(async (fixtureRoot) => {
    await assert.rejects(
      verifyCivEngineSetupUnderLease({
        repoRoot: fixtureRoot,
        lease: Object.freeze({ repoRoot: fixtureRoot }),
      }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LEASE',
    );
    const operations = leaseOperations([]);
    const lease = await acquireCivEngineVerificationLease({
      repoRoot: fixtureRoot,
      operations,
    });
    try {
      await assert.rejects(
        verifyCivEngineSetupUnderLease({
          repoRoot: `${fixtureRoot}-other`,
          lease,
        }),
        (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_LEASE',
      );
    } finally {
      await releaseCivEngineVerificationLease(lease);
    }
  });
});

function leaseOperations(
  events,
  { failVerification = false, mutateOwnershipDuringVerification = false } = {},
) {
  let acquiredLock;
  return {
    async acquireSetupLock(input) {
      events.push('acquire');
      acquiredLock = await acquireSetupLock(input);
      return acquiredLock;
    },
    async assertSetupLockOwnership(input) {
      events.push('ownership');
      return assertSetupLockOwnership(input);
    },
    async verifyOnly({ allowDirty }) {
      events.push(`verify:${allowDirty}`);
      if (failVerification) throw new Error('fixture verification failure');
      if (mutateOwnershipDuringVerification) {
        await Promise.resolve();
        await writeFile(
          acquiredLock.path,
          '{"token":"replacement-token"}\n',
          'utf8',
        );
        events.push('mutate-ownership');
      }
    },
    async releaseSetupLock(input) {
      events.push('release');
      return releaseSetupLock(input);
    },
  };
}
