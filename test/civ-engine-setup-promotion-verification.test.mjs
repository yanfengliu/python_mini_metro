import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { promotePin } from '../scripts/civ-engine-setup-operations.mjs';
import { createSetupTransaction } from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('child metadata verification observes source before destination', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const sourcePath = path.join(transaction.checkoutPath, 'sentinel.txt');
    const destinationPath = path.join(destination, 'sentinel.txt');
    let metadataChanged = false;
    const race = destinationFirstRace({
      readSource: () => fs.lstat(sourcePath, { bigint: true }),
      readDestination: () => {
        const changedAtObservation = metadataChanged;
        return fs.lstat(destinationPath, { bigint: true }).then((metadata) => (
          changedAtObservation ? withChangedMode(metadata) : metadata
        ));
      },
      mutateDestination: async () => {
        metadataChanged = true;
      },
    });
    let sourceCalls = 0;
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'lstat') return target[property];
        return (candidate, options) => {
          if (samePath(candidate, sourcePath) && ++sourceCalls === 2) {
            return race.readSource();
          }
          if (samePath(candidate, destinationPath)) return race.readDestination();
          return fs.lstat(candidate, options);
        };
      },
    });

    await assertVerificationFailure({
      transaction,
      destination,
      fileSystem: racingFileSystem,
      message: 'published file bytes or mode changed',
    });
    assert.equal(race.injected(), true);
  });
});

test('file-byte verification observes source before destination', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const sourcePath = path.join(transaction.checkoutPath, 'sentinel.txt');
    const destinationPath = path.join(destination, 'sentinel.txt');
    const race = destinationFirstRace({
      readSource: () => fs.readFile(sourcePath),
      readDestination: () => fs.readFile(destinationPath),
      mutateDestination: () => fs.writeFile(destinationPath, 'mutated destination\n'),
    });
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'readFile') return target[property];
        return (candidate, options) => {
          if (samePath(candidate, sourcePath)) return race.readSource();
          if (samePath(candidate, destinationPath)) return race.readDestination();
          return fs.readFile(candidate, options);
        };
      },
    });

    await assertVerificationFailure({
      transaction,
      destination,
      fileSystem: racingFileSystem,
      message: 'published file bytes or mode changed',
    });
    assert.equal(race.injected(), true);
    assert.equal(await fs.readFile(destinationPath, 'utf8'), 'mutated destination\n');
  });
});

test('link-target verification observes source before destination', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const sourceTarget = path.join(transaction.checkoutPath, 'link-target-a');
    const replacementTarget = path.join(transaction.checkoutPath, 'link-target-b');
    const sourcePath = path.join(transaction.checkoutPath, 'zz-verification-link');
    await Promise.all([fs.mkdir(sourceTarget), fs.mkdir(replacementTarget)]);
    await fs.symlink(
      sourceTarget,
      sourcePath,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const destinationPath = path.join(destination, 'zz-verification-link');
    const destinationReplacement = path.join(destination, 'link-target-b');
    const race = destinationFirstRace({
      readSource: () => fs.realpath(sourcePath),
      readDestination: () => fs.realpath(destinationPath),
      mutateDestination: async () => {
        await fs.unlink(destinationPath);
        await fs.symlink(
          destinationReplacement,
          destinationPath,
          process.platform === 'win32' ? 'junction' : 'dir',
        );
      },
    });
    let sourceCalls = 0;
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'realpath') return target[property];
        return (candidate, options) => {
          if (samePath(candidate, sourcePath) && ++sourceCalls === 2) {
            return race.readSource();
          }
          if (samePath(candidate, destinationPath)) return race.readDestination();
          return fs.realpath(candidate, options);
        };
      },
    });

    await assertVerificationFailure({
      transaction,
      destination,
      fileSystem: racingFileSystem,
      message: 'published link target changed',
    });
    assert.equal(race.injected(), true);
    assert.equal(samePath(await fs.realpath(destinationPath), destinationReplacement), true);
  });
});

function destinationFirstRace({ readSource, readDestination, mutateDestination }) {
  let destinationStarted = false;
  let destinationSnapshot;
  let mutationInjected = false;
  return {
    async readSource() {
      await Promise.resolve();
      if (destinationStarted) await destinationSnapshot;
      const sourceSnapshot = await readSource();
      await mutateDestination();
      mutationInjected = true;
      return sourceSnapshot;
    },
    readDestination() {
      destinationStarted = true;
      destinationSnapshot = Promise.resolve(readDestination());
      return destinationSnapshot;
    },
    injected() {
      return mutationInjected;
    },
  };
}

async function assertVerificationFailure({
  transaction,
  destination,
  fileSystem,
  message,
}) {
  await assert.rejects(
    promotePin({
      source: transaction.checkoutPath,
      destination,
      transaction,
      fileSystem,
    }),
    (error) => (
      error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
      && error.message.includes(message)
      && error.preserveSetupTransaction === true
    ),
  );
}

async function createPromotionSource(repoRoot) {
  const transaction = await createSetupTransaction({ repoRoot, token: 'verification-owner' });
  await fs.mkdir(path.join(transaction.checkoutPath, 'nested'), { recursive: true });
  await Promise.all([
    fs.writeFile(path.join(transaction.checkoutPath, 'sentinel.txt'), 'authenticated source\n'),
    fs.writeFile(path.join(transaction.checkoutPath, 'nested', 'value.txt'), 'nested\n'),
  ]);
  return transaction;
}

function withChangedMode(metadata) {
  return new Proxy(metadata, {
    get(stat, field) {
      if (field === 'mode') return stat.mode ^ 0o001n;
      const value = Reflect.get(stat, field, stat);
      return typeof value === 'function' ? value.bind(stat) : value;
    },
  });
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}
