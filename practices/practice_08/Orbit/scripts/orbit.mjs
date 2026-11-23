import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, realpathSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
process.chdir(root);
const windows = process.platform === 'win32';
const python = join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
const cache = join(root, '.cache');
const env = {
  ...process.env,
  npm_config_cache: join(cache, 'npm'),
  PIP_CACHE_DIR: join(cache, 'pip'),
  PLAYWRIGHT_BROWSERS_PATH: join(cache, 'chromium'),
  PLAYWRIGHT_SKIP_BROWSER_GC: '1',
  PYTHONDONTWRITEBYTECODE: '1',
  TEMP: join(cache, 'tmp'),
  TMP: join(cache, 'tmp'),
  TMPDIR: join(cache, 'tmp'),
};
mkdirSync(env.TEMP, { recursive: true });

function checked(exe, args, options = {}) {
  const result = spawnSync(exe, args, { stdio: 'inherit', env, ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(exe + ' exited with ' + result.status);
}

const node = process.execPath;
const playwright = 'node_modules/@playwright/test/cli.js';
const vite = 'node_modules/vite/bin/vite.js';
const mode = process.argv[2];

if (mode === 'setup') {
  const npm = process.env.npm_execpath;
  checked(node, [npm, 'ci']);
  checked(windows ? 'python' : 'python3', ['-m', 'venv', '.venv']);
  checked(python, ['-m', 'pip', 'install', '-r', 'server/requirements.txt']);
  checked(node, [playwright, 'install', 'chromium']);
} else if (mode === 'seed') {
  checked(python, ['-m', 'server.seed', ...process.argv.slice(3)]);
} else if (mode === 'import-schedule') {
  checked(python, ['-m', 'server.import_schedule']);
} else if (mode === 'test-client') {
  const temporary = mkdtempSync(join(cache, 'test-db-'));
  try {
    checked(node, [playwright, 'test', ...process.argv.slice(3)], {
      env: { ...env, ORBIT_TEST_RUN: '1', ORBIT_DB: join(temporary, 'orbit.sqlite3') },
    });
  } finally {
    if (dirname(realpathSync(temporary)) !== join(realpathSync(root), '.cache')) {
      throw new Error('Temporary test database escaped the Orbit cache directory.');
    }
    rmSync(temporary, { recursive: true, force: true });
  }
} else if (mode === 'dev') {
  const test = env.ORBIT_TEST_RUN === '1';
  const apiPort = test ? (env.ORBIT_TEST_API_PORT ?? '8108') : '8000';
  const webPort = test ? (env.ORBIT_TEST_WEB_PORT ?? '5188') : '5173';
  const options = { stdio: 'inherit', env: { ...env, ORBIT_API_PORT: apiPort } };
  const children = [
    spawn(python, ['-m', 'uvicorn', 'server.main:app', '--host', '127.0.0.1', '--port', apiPort], options),
    spawn(node, [vite, '--host', '127.0.0.1', '--port', webPort, '--strictPort'], options),
  ];
  let stopping = false;
  function stop(code) {
    if (stopping) return;
    stopping = true;
    for (const child of children) child.kill();
    process.exitCode = code;
  }
  for (const child of children) {
    child.on('error', (error) => { console.error(error); stop(1); });
    child.on('exit', (code) => stop(code ?? 1));
  }
  process.on('SIGINT', () => stop(0));
  process.on('SIGTERM', () => stop(0));
} else {
  throw new Error('Unknown Orbit command: ' + mode);
}
