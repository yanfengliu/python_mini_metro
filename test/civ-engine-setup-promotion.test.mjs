import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { promotePin } from '../scripts/civ-engine-setup-operations.mjs';
import { createSetupTransaction } from '../scripts/civ-engine-setup-safety.mjs';
import { withSetupRepository } from './civ-engine-setup-fixtures.mjs';

test('promotion loses an atomic destination-claim race without touching either tree', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    let winnerIdentity = null;
    let injected = false;
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'mkdir') return target[property];
        return async (candidate, options) => {
          if (!injected && samePath(candidate, destination)) {
            injected = true;
            await fs.mkdir(destination);
            winnerIdentity = identity(await fs.lstat(destination, { bigint: true }));
          }
          return fs.mkdir(candidate, options);
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: racingFileSystem,
      }),
      (error) => error?.code === 'ERR_CIV_ENGINE_SETUP_REFUSED',
    );

    assert.equal(injected, true);
    assert.deepEqual(
      identity(await fs.lstat(destination, { bigint: true })),
      winnerIdentity,
    );
    assert.deepEqual(await fs.readdir(destination), []);
    assert.equal(
      await fs.readFile(path.join(transaction.checkoutPath, 'sentinel.txt'), 'utf8'),
      'authenticated source\n',
    );
  });
});

test('POSIX rename can replace an empty destination created after an absence check', {
  skip: process.platform === 'win32' ? 'POSIX rename semantics' : false,
}, async () => {
  await withSetupRepository(async (repoRoot) => {
    const source = path.join(repoRoot, 'rename-source');
    const destination = path.join(repoRoot, 'rename-destination');
    await fs.mkdir(source);
    await fs.writeFile(path.join(source, 'sentinel.txt'), 'source\n');
    await assert.rejects(fs.lstat(destination), { code: 'ENOENT' });
    await fs.mkdir(destination);
    const winnerIdentity = identity(await fs.lstat(destination, { bigint: true }));

    await fs.rename(source, destination);

    assert.notDeepEqual(
      identity(await fs.lstat(destination, { bigint: true })),
      winnerIdentity,
    );
    assert.equal(await fs.readFile(path.join(destination, 'sentinel.txt'), 'utf8'), 'source\n');
  });
});

test('claimed publication leaves only a transaction-side claim record', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');

    await promotePin({ source: transaction.checkoutPath, destination, transaction });

    assert.deepEqual((await fs.readdir(destination)).sort(), ['nested', 'sentinel.txt']);
    assert.equal(await fs.readFile(path.join(destination, 'sentinel.txt'), 'utf8'), 'authenticated source\n');
    assert.equal(await fs.readFile(path.join(destination, 'nested', 'value.txt'), 'utf8'), 'nested\n');
    assert.deepEqual(
      (await fs.readdir(transaction.checkoutPath)).sort(),
      ['nested', 'sentinel.txt'],
    );
    assert.deepEqual((await fs.readdir(destination)).sort(), ['nested', 'sentinel.txt']);
    const claim = await readPromotionClaim(transaction);
    assert.equal(claim.token, transaction.token);
    assert.deepEqual(
      claim.destinationIdentity,
      identity(await fs.lstat(destination, { bigint: true })),
    );
  });
});

test('per-file publication loses an injected race without clobbering the winner', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const winnerPath = path.join(destination, 'sentinel.txt');
    let injected = false;
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'copyFile') return target[property];
        return async (sourcePath, targetPath, flags) => {
          if (!injected && samePath(targetPath, winnerPath)) {
            injected = true;
            await fs.writeFile(winnerPath, 'winner\n', { flag: 'wx' });
          }
          return fs.copyFile(sourcePath, targetPath, flags);
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: racingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
        && error.preserveSetupTransaction === true
      ),
    );

    assert.equal(injected, true);
    assert.equal(await fs.readFile(winnerPath, 'utf8'), 'winner\n');
    assert.equal((await readPromotionClaim(transaction)).token, transaction.token);
    assert.deepEqual((await fs.readdir(transaction.checkoutPath)).sort(), ['nested', 'sentinel.txt']);
    assert.equal(await fs.readFile(path.join(transaction.checkoutPath, 'sentinel.txt'), 'utf8'), 'authenticated source\n');
  });
});

test('per-directory publication loses an injected race without replacing an empty winner', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const winnerPath = path.join(destination, 'nested');
    let winnerIdentity;
    const racingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'mkdir') return target[property];
        return async (candidate, options) => {
          if (!winnerIdentity && samePath(candidate, winnerPath)) {
            await fs.mkdir(winnerPath);
            winnerIdentity = identity(await fs.lstat(winnerPath, { bigint: true }));
          }
          return fs.mkdir(candidate, options);
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: racingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
        && error.preserveSetupTransaction === true
      ),
    );

    assert.deepEqual(
      identity(await fs.lstat(winnerPath, { bigint: true })),
      winnerIdentity,
    );
    assert.deepEqual(await fs.readdir(winnerPath), []);
    assert.equal(
      await fs.readFile(path.join(transaction.checkoutPath, 'nested', 'value.txt'), 'utf8'),
      'nested\n',
    );
  });
});

test('exclusive copy preserves authenticated bytes and executable mode', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const sourcePath = path.join(transaction.checkoutPath, 'sentinel.txt');
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const destinationPath = path.join(destination, 'sentinel.txt');
    await fs.chmod(sourcePath, 0o744);

    await promotePin({
      source: transaction.checkoutPath,
      destination,
      transaction,
    });

    assert.equal(await fs.readFile(destinationPath, 'utf8'), 'authenticated source\n');
    if (process.platform !== 'win32') {
      const [sourceMode, destinationMode] = await Promise.all([
        fs.stat(sourcePath),
        fs.stat(destinationPath),
      ]);
      assert.equal(destinationMode.mode & 0o777, sourceMode.mode & 0o777);
    }
  });
});

test('source mutation after an exclusive copy cannot alter the published file', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const sourcePath = path.join(transaction.checkoutPath, 'sentinel.txt');
    const destination = path.join(repoRoot, '.civ-engine-pin');
    const destinationPath = path.join(destination, 'sentinel.txt');
    let injected = false;
    const mutatingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'copyFile') return target[property];
        return async (candidate, targetPath, flags) => {
          await fs.copyFile(candidate, targetPath, flags);
          if (!injected && samePath(candidate, sourcePath)) {
            injected = true;
            await fs.writeFile(sourcePath, 'mutated source\n');
          }
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: mutatingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
        && error.preserveSetupTransaction === true
      ),
    );
    assert.equal(injected, true);
    assert.equal(await fs.readFile(destinationPath, 'utf8'), 'authenticated source\n');
    assert.equal(await fs.readFile(sourcePath, 'utf8'), 'mutated source\n');
  });
});

test('publication preserves root and nested directory modes', {
  skip: process.platform === 'win32' ? 'POSIX directory mode semantics' : false,
}, async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    await fs.chmod(transaction.checkoutPath, 0o711);
    await fs.chmod(path.join(transaction.checkoutPath, 'nested'), 0o700);

    await promotePin({ source: transaction.checkoutPath, destination, transaction });

    const [sourceRoot, destinationRoot, sourceNested, destinationNested] = await Promise.all([
      fs.stat(transaction.checkoutPath),
      fs.stat(destination),
      fs.stat(path.join(transaction.checkoutPath, 'nested')),
      fs.stat(path.join(destination, 'nested')),
    ]);
    assert.equal(destinationRoot.mode & 0o777, sourceRoot.mode & 0o777);
    assert.equal(destinationNested.mode & 0o777, sourceNested.mode & 0o777);
  });
});

test('publication detects root and nested directory mode changes', {
  skip: process.platform === 'win32' ? 'POSIX directory mode semantics' : false,
}, async () => {
  for (const relativeTarget of ['', 'nested']) {
    await withSetupRepository(async (repoRoot) => {
      const transaction = await createPromotionSource(repoRoot);
      const destination = path.join(repoRoot, '.civ-engine-pin');
      const sourceTarget = path.join(transaction.checkoutPath, relativeTarget);
      const destinationTarget = path.join(destination, relativeTarget);
      const mutationCall = relativeTarget === '' ? 2 : 3;
      let sourceTargetCalls = 0;
      const tamperingFileSystem = new Proxy(fs, {
        get(target, property) {
          if (property !== 'lstat') return target[property];
          return async (candidate, options) => {
            if (samePath(candidate, sourceTarget)) {
              sourceTargetCalls += 1;
              if (sourceTargetCalls === mutationCall) {
                const sourceMode = (await fs.lstat(sourceTarget)).mode & 0o777;
                await fs.chmod(destinationTarget, sourceMode === 0o700 ? 0o755 : 0o700);
              }
            }
            return fs.lstat(candidate, options);
          };
        },
      });

      await assert.rejects(
        promotePin({
          source: transaction.checkoutPath,
          destination,
          transaction,
          fileSystem: tamperingFileSystem,
        }),
        (error) => (
          error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
          && error.preserveSetupTransaction === true
        ),
      );
      assert.equal(sourceTargetCalls >= mutationCall, true);
      assert.equal((await readPromotionClaim(transaction)).token, transaction.token);
    });
  }
});

test('publication snapshots source directory mode before destination mode', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    let sourceReads = 0;
    let sourceSnapshotComplete = false;
    let injected = false;
    const modeChangingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'lstat') return target[property];
        return async (candidate, options) => {
          const verificationSource = samePath(candidate, transaction.checkoutPath)
            && ++sourceReads === 2;
          const injectMode = samePath(candidate, destination)
            && sourceSnapshotComplete
            && !injected;
          const metadata = await fs.lstat(candidate, options);
          if (verificationSource) sourceSnapshotComplete = true;
          if (!injectMode) return metadata;
          injected = true;
          return new Proxy(metadata, {
            get(stat, field) {
              if (field === 'mode') return stat.mode ^ 0o001n;
              const value = Reflect.get(stat, field, stat);
              return typeof value === 'function' ? value.bind(stat) : value;
            },
          });
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: modeChangingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
        && error.message.includes('published directory type or mode changed')
        && error.preserveSetupTransaction === true
      ),
    );
    assert.equal(injected, true);
  });
});

test('contained directory links are remapped and escaping links are refused', async () => {
  await withSetupRepository(async (repoRoot) => {
    const contained = await createPromotionSource(repoRoot);
    const containedTarget = path.join(contained.checkoutPath, 'target-directory');
    const containedLink = path.join(contained.checkoutPath, 'contained-link');
    await fs.mkdir(containedTarget);
    await fs.writeFile(path.join(containedTarget, 'value.txt'), 'contained\n');
    await fs.symlink(
      containedTarget,
      containedLink,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    const destination = path.join(repoRoot, '.civ-engine-pin');

    await promotePin({
      source: contained.checkoutPath,
      destination,
      transaction: contained,
    });

    assert.equal(
      samePath(
        await fs.realpath(path.join(destination, 'contained-link')),
        path.join(destination, 'target-directory'),
      ),
      true,
    );

    const escapeRepo = path.join(repoRoot, 'escape-fixture');
    await fs.mkdir(escapeRepo);
    const escaping = await createPromotionSource(escapeRepo);
    const externalTarget = path.join(escapeRepo, 'external-target');
    await fs.mkdir(externalTarget);
    await fs.writeFile(path.join(externalTarget, 'value.txt'), 'external\n');
    await fs.symlink(
      externalTarget,
      path.join(escaping.checkoutPath, 'escaping-link'),
      process.platform === 'win32' ? 'junction' : 'dir',
    );
    const escapingDestination = path.join(escapeRepo, '.civ-engine-pin');

    await assert.rejects(
      promotePin({
        source: escaping.checkoutPath,
        destination: escapingDestination,
        transaction: escaping,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_REFUSED'
        && error.preserveSetupTransaction === true
      ),
    );
    assert.equal(
      await fs.readFile(path.join(externalTarget, 'value.txt'), 'utf8'),
      'external\n',
    );
    assert.equal((await readPromotionClaim(escaping)).token, escaping.token);
  });
});

test('transaction claim tamper retains both partial publication and source evidence', async () => {
  await withSetupRepository(async (repoRoot) => {
    const transaction = await createPromotionSource(repoRoot);
    const destination = path.join(repoRoot, '.civ-engine-pin');
    let tampered = false;
    const tamperingFileSystem = new Proxy(fs, {
      get(target, property) {
        if (property !== 'copyFile') return target[property];
        return async (sourcePath, targetPath, flags) => {
          if (!tampered) {
            tampered = true;
            await fs.writeFile(
              path.join(transaction.parentPath, '.setup-promotion-claim'),
              '{"token":"replacement"}\n',
            );
          }
          return fs.copyFile(sourcePath, targetPath, flags);
        };
      },
    });

    await assert.rejects(
      promotePin({
        source: transaction.checkoutPath,
        destination,
        transaction,
        fileSystem: tamperingFileSystem,
      }),
      (error) => (
        error?.code === 'ERR_CIV_ENGINE_SETUP_OWNERSHIP'
        && error.preserveSetupTransaction === true
      ),
    );

    assert.equal(
      await fs.readFile(path.join(transaction.parentPath, '.setup-promotion-claim'), 'utf8'),
      '{"token":"replacement"}\n',
    );
    assert.equal(
      await fs.readFile(path.join(transaction.checkoutPath, 'sentinel.txt'), 'utf8'),
      'authenticated source\n',
    );
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

function identity(metadata) {
  return { dev: metadata.dev.toString(), ino: metadata.ino.toString() };
}

async function readPromotionClaim(transaction) {
  return JSON.parse(await fs.readFile(
    path.join(transaction.parentPath, '.setup-promotion-claim'),
    'utf8',
  ));
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}
