import assert from 'node:assert/strict';
import test from 'node:test';

import { parseRecursiveArgs } from '../scripts/recursive-args.mjs';

test('recursive argv parser distinguishes option values from canary flags', () => {
  assert.deepEqual(parseRecursiveArgs([
    '--scenario',
    '--allow-dirty',
    '--output-root',
    'output/value',
  ]), {
    scenario: '--allow-dirty',
    outputRoot: 'output/value',
  });
  assert.deepEqual(parseRecursiveArgs([
    '--output-root',
    '--allow-dirty',
  ]), {
    outputRoot: '--allow-dirty',
  });
  assert.deepEqual(parseRecursiveArgs([
    '--allow-dirty',
    '--scenario',
    'scenario.json',
    '--output-root',
    'output/canary',
  ]), {
    allowDirty: true,
    scenario: 'scenario.json',
    outputRoot: 'output/canary',
  });
});

test('recursive argv parser rejects unknown and missing options deterministically', () => {
  const untrustedArgument = '--secret-argument-value';
  assert.throws(
    () => parseRecursiveArgs([untrustedArgument]),
    (error) => (
      error?.message === 'unknown argument'
      && !error.message.includes(untrustedArgument)
    ),
  );
  for (const raw of [
    ['--scenario'],
    ['--output-root'],
    ['--scenario', ''],
  ]) {
    assert.throws(
      () => parseRecursiveArgs(raw),
      /unknown argument|missing value/i,
    );
  }
});
