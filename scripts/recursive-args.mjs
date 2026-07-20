export function parseRecursiveArgs(raw) {
  const parsed = {};
  for (let index = 0; index < raw.length; index += 1) {
    const key = raw[index];
    if (key === '--allow-dirty') {
      parsed.allowDirty = true;
      continue;
    }
    if (key !== '--scenario' && key !== '--output-root') {
      throw new Error('unknown argument');
    }
    const value = raw[index + 1];
    if (!value) throw new Error(`missing value for ${key}`);
    parsed[key === '--scenario' ? 'scenario' : 'outputRoot'] = value;
    index += 1;
  }
  return parsed;
}
