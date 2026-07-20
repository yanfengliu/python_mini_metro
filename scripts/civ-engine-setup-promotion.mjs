import fs from 'node:fs/promises';
import path from 'node:path';

const PROMOTION_CLAIM = '.setup-promotion-claim';
export async function publishOwnedDirectory({
  source,
  destination,
  transaction,
  fileSystem = fs,
}) {
  if (!samePath(source, transaction.checkoutPath)) {
    throw refused('promotion source is not the owned setup checkout');
  }
  const sourceMetadata = await fileSystem.lstat(source, { bigint: true });
  if (!sourceMetadata.isDirectory() || sourceMetadata.isSymbolicLink()) {
    throw refused('promotion source is not a physical directory');
  }

  let destinationClaimed = false;
  let claim;
  try {
    try {
      await fileSystem.mkdir(destination, {
        mode: Number(sourceMetadata.mode & 0o777n),
      });
      destinationClaimed = true;
    } catch (error) {
      if (error?.code === 'EEXIST') {
        throw refused('promotion destination is no longer missing');
      }
      throw error;
    }
    const destinationIdentity = await physicalDirectoryIdentity(
      fileSystem,
      destination,
      'promotion destination',
    );
    claim = {
      claimPath: path.join(transaction.parentPath, PROMOTION_CLAIM),
      destination,
      destinationIdentity,
      source,
      token: transaction.token,
    };
    await fileSystem.writeFile(claim.claimPath, claimDocument(claim), {
      encoding: 'utf8',
      flag: 'wx',
    });
    claim.claimIdentity = await physicalFileIdentity(
      fileSystem,
      claim.claimPath,
      'promotion claim record',
    );

    await publishTree({ fileSystem, claim, source, destination });
    await assertEquivalentTree({ fileSystem, claim, source, destination });
    await assertOwnedClaim(fileSystem, claim);
  } catch (error) {
    if (destinationClaimed) throw preservedFailure(error);
    if (error?.code?.startsWith('ERR_CIV_ENGINE_')) throw error;
    throw refused('civ-engine publication failed before ownership was recorded');
  }
}

async function publishTree({ fileSystem, claim, source, destination }) {
  await assertOwnedClaim(fileSystem, claim);
  const names = (await fileSystem.readdir(source)).sort();
  for (const name of names) {
    await assertOwnedClaim(fileSystem, claim);
    const sourcePath = path.join(source, name);
    const destinationPath = path.join(destination, name);
    const metadata = await fileSystem.lstat(sourcePath, { bigint: true });
    if (metadata.isDirectory() && !metadata.isSymbolicLink()) {
      await createDirectory(fileSystem, destinationPath, metadata);
      await publishTree({
        fileSystem,
        claim,
        source: sourcePath,
        destination: destinationPath,
      });
    } else if (metadata.isFile() && !metadata.isSymbolicLink()) {
      await publishFile(fileSystem, sourcePath, destinationPath);
    } else if (metadata.isSymbolicLink()) {
      await publishLink({ fileSystem, claim, sourcePath, destinationPath });
    } else {
      throw refused('promotion source contains an unsupported entry');
    }
  }
}

async function createDirectory(fileSystem, destinationPath, metadata) {
  try {
    await fileSystem.mkdir(destinationPath, { mode: Number(metadata.mode & 0o777n) });
  } catch (error) {
    if (error?.code === 'EEXIST') throw ownershipError('promotion target is no longer missing');
    throw error;
  }
}

async function publishFile(fileSystem, sourcePath, destinationPath) {
  try {
    await fileSystem.copyFile(
      sourcePath,
      destinationPath,
      fileSystem.constants.COPYFILE_EXCL,
    );
  } catch (error) {
    if (error?.code === 'EEXIST') throw ownershipError('promotion target is no longer missing');
    throw error;
  }
}

async function publishLink({ fileSystem, claim, sourcePath, destinationPath }) {
  const sourceTarget = await fileSystem.realpath(sourcePath);
  if (!isInside(claim.source, sourceTarget)) {
    throw refused('promotion source link escapes the owned checkout');
  }
  const destinationTarget = path.join(
    claim.destination,
    path.relative(claim.source, sourceTarget),
  );
  const targetMetadata = await fileSystem.stat(sourcePath);
  const linkType = targetMetadata.isDirectory()
    ? (process.platform === 'win32' ? 'junction' : 'dir')
    : 'file';
  const linkTarget = linkType === 'junction'
    ? destinationTarget
    : path.relative(path.dirname(destinationPath), destinationTarget);
  try {
    await fileSystem.symlink(linkTarget, destinationPath, linkType);
  } catch (error) {
    if (error?.code === 'EEXIST') throw ownershipError('promotion target is no longer missing');
    throw error;
  }
}

async function assertEquivalentTree({ fileSystem, claim, source, destination }) {
  await assertOwnedClaim(fileSystem, claim);
  const sourceDirectory = await fileSystem.lstat(source, { bigint: true });
  const destinationDirectory = await fileSystem.lstat(destination, { bigint: true });
  if (
    !sourceDirectory.isDirectory()
    || sourceDirectory.isSymbolicLink()
    || !destinationDirectory.isDirectory()
    || destinationDirectory.isSymbolicLink()
    || Number(sourceDirectory.mode & 0o777n) !== Number(destinationDirectory.mode & 0o777n)
  ) {
    throw ownershipError('published directory type or mode changed');
  }
  const sourceNames = (await fileSystem.readdir(source)).sort();
  const destinationNames = (await fileSystem.readdir(destination)).sort();
  if (!sameNames(sourceNames, destinationNames)) {
    throw ownershipError('published destination does not match the authenticated source');
  }
  for (const name of sourceNames) {
    const sourcePath = path.join(source, name);
    const destinationPath = path.join(destination, name);
    const sourceMetadata = await fileSystem.lstat(sourcePath, { bigint: true });
    const destinationMetadata = await fileSystem.lstat(destinationPath, { bigint: true });
    if (sourceMetadata.isSymbolicLink() || destinationMetadata.isSymbolicLink()) {
      if (!sourceMetadata.isSymbolicLink() || !destinationMetadata.isSymbolicLink()) {
        throw ownershipError('published entry type changed');
      }
      const sourceTarget = await fileSystem.realpath(sourcePath);
      const destinationTarget = await fileSystem.realpath(destinationPath);
      const expectedTarget = path.join(
        claim.destination,
        path.relative(claim.source, sourceTarget),
      );
      if (!isInside(claim.source, sourceTarget) || !samePath(destinationTarget, expectedTarget)) {
        throw ownershipError('published link target changed');
      }
    } else if (sourceMetadata.isDirectory() || destinationMetadata.isDirectory()) {
      if (!sourceMetadata.isDirectory() || !destinationMetadata.isDirectory()) {
        throw ownershipError('published entry type changed');
      }
      await assertEquivalentTree({
        fileSystem,
        claim,
        source: sourcePath,
        destination: destinationPath,
      });
    } else if (sourceMetadata.isFile() && destinationMetadata.isFile()) {
      const sourceBytes = await fileSystem.readFile(sourcePath);
      const destinationBytes = await fileSystem.readFile(destinationPath);
      if (
        !sourceBytes.equals(destinationBytes)
        || Number(sourceMetadata.mode & 0o777n) !== Number(destinationMetadata.mode & 0o777n)
      ) {
        throw ownershipError('published file bytes or mode changed');
      }
    } else {
      throw ownershipError('published entry type changed');
    }
  }
}

async function assertOwnedClaim(fileSystem, claim) {
  const identity = await physicalDirectoryIdentity(
    fileSystem,
    claim.destination,
    'promotion destination',
  );
  const [claimIdentity, claimContents] = await Promise.all([
    physicalFileIdentity(fileSystem, claim.claimPath, 'promotion claim record'),
    fileSystem.readFile(claim.claimPath, 'utf8'),
  ]);
  if (
    !sameIdentity(identity, claim.destinationIdentity)
    || !sameIdentity(claimIdentity, claim.claimIdentity)
    || claimContents !== claimDocument(claim)
  ) {
    throw ownershipError('promotion destination ownership changed');
  }
}

async function physicalDirectoryIdentity(fileSystem, candidate, label) {
  const [metadata, physical] = await Promise.all([
    fileSystem.lstat(candidate, { bigint: true }),
    fileSystem.realpath(candidate),
  ]);
  if (!metadata.isDirectory() || metadata.isSymbolicLink() || !samePath(candidate, physical)) {
    throw ownershipError(`${label} must remain a physical directory`);
  }
  return fileIdentity(metadata);
}

async function physicalFileIdentity(fileSystem, candidate, label) {
  const [metadata, physical] = await Promise.all([
    fileSystem.lstat(candidate, { bigint: true }),
    fileSystem.realpath(candidate),
  ]);
  if (!metadata.isFile() || metadata.isSymbolicLink() || !samePath(candidate, physical)) {
    throw ownershipError(`${label} must remain a physical file`);
  }
  return fileIdentity(metadata);
}

function claimDocument(claim) {
  return `${JSON.stringify({
    destination: path.basename(claim.destination),
    destinationIdentity: claim.destinationIdentity,
    token: claim.token,
  })}\n`;
}

function fileIdentity(metadata) {
  return { dev: metadata.dev.toString(), ino: metadata.ino.toString() };
}

function sameIdentity(left, right) {
  return left.dev === right.dev && left.ino === right.ino;
}

function sameNames(left, right) {
  return left.length === right.length && left.every((name, index) => name === right[index]);
}

function isInside(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return relative !== '' && !relative.startsWith(`..${path.sep}`) && relative !== '..';
}

function samePath(left, right) {
  return path.relative(path.resolve(left), path.resolve(right)) === '';
}

function preservedFailure(error) {
  const failure = error?.code?.startsWith('ERR_CIV_ENGINE_')
    ? error
    : refused('civ-engine publication failed after the final path was claimed');
  failure.preserveSetupTransaction = true;
  return failure;
}

function refused(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_REFUSED' });
}

function ownershipError(message) {
  return Object.assign(new Error(message), { code: 'ERR_CIV_ENGINE_SETUP_OWNERSHIP' });
}
