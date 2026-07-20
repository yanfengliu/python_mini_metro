export function assertCleanNodeStartup({
  nodeOptions = process.env.NODE_OPTIONS,
  execArgv = process.execArgv,
} = {}) {
  const nodeOptionsClean = nodeOptions === undefined || nodeOptions === '';
  const execArgvClean = Array.isArray(execArgv) && execArgv.length === 0;
  if (nodeOptionsClean && execArgvClean) return;
  throw Object.assign(
    new Error('public Node entry point requires clean startup'),
    { code: 'ERR_CIV_ENGINE_NODE_STARTUP' },
  );
}
