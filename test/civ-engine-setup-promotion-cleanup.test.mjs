import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { promotePin } from '../scripts/civ-engine-setup-operations.mjs';
import { createSetupTransaction } from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('successful publication performs no destructive namespace operation', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const forbidden = [];
    const observingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (!['rename', 'rmdir', 'rm', 'unlink'].includes(property)) return target[property];
        return async (...args) => {
          forbidden.push({ property, args });
          throw new Error(`unexpected destructive operation: ${property}`);
        };
      },
    });

    await promotePin({
      source: transaction.checkoutPath,
      destination,
      transaction,
      fileSystem: observingFileSystem,
    });

    assert.deepEqual(forbidden, []);
    assert.deepEqual((await fs.readdir(destination)).sort(), ['nested', 'sentinel.txt']);
  });
});

test('claim-record failure retains the empty destination without rollback', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const claimPath = path.join(transaction.parentPath, '.setup-promotion-claim');
    const destructive = [];
    const failingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property === 'writeFile') {
          return async (candidate, ...args) => {
            if (samePath(candidate, claimPath)) {
              throw Object.assign(new Error('claim write blocked'), { code: 'EACCES' });
            }
            return fs.writeFile(candidate, ...args);
          };
        }
        if (!['rename', 'rmdir', 'rm', 'unlink'].includes(property)) return target[property];
        return async (...args) => {
          destructive.push({ property, args });
          throw new Error(`unexpected destructive operation: ${property}`);
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: failingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_REFUSED'
        && error.preserveSetupTransaction === true
      ),
    );

    assert.deepEqual(destructive, []);
    assert.deepEqual(await fs.readdir(destination), []);
    assert.equal(await fs.readFile(transaction.markerPath, 'utf8'), '{"token":"promotion-owner"}\n');
  });
});

async function createPromotionSource(repoRoot) {
  const transaction = await createSetupTransaction({ repoRoot, token: 'promotion-owner' });
  await fs.mkdir(path.join(transaction.checkoutPath, 'nested'), { recursive: true });
  await Promise.all([
    fs.writeFile(path.join(transaction.checkoutPath, 'sentinel.txt'), 'authenticated source\n'),
    fs.writeFile(path.join(transaction.checkoutPath, 'nested', 'value.txt'), 'nested\n'),
  ]);
  return transaction;
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}
