import { existsSync } from 'node:fs';
import { DatabaseSync, backup } from 'node:sqlite';
import { chmod, mkdir, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const config = process.env.SEERR_CONFIG_FOLDER || '/app/config';
const destination = process.env.SEERR_BACKUP_FOLDER || '/backups';
process.umask(0o077);
const managed = process.argv[2] !== 'manual';
const defaultHelper = existsSync('/opt/infra-backup-retention.sh') ? '/opt/infra-backup-retention.sh' : join(destination, '.infra-backup-retention.sh');
const retention = (...args) => execFileSync('sh', [process.env.INFRA_BACKUP_HELPER || defaultHelper, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] }).trim();
const marker = join(destination, '.last-success');
if (process.argv[2] === 'daily') {
  try {
    const lastSuccess = Number(await readFile(marker, 'utf8'));
    if (lastSuccess > 0 && Date.now() - lastSuccess < 86_400_000) process.exit(0);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}
const name = `${new Date().toISOString().replaceAll(':', '-')}-${randomUUID()}`;
const temporary = join(destination, `.${name}.incomplete`);

await mkdir(temporary, { recursive: true, mode: 0o700 });
try {
  await mkdir(join(temporary, 'db'), { mode: 0o700 });
  const databases = (await readdir(join(config, 'db')))
    .filter(file => /\.(sqlite3?|db)$/.test(file));
  if (!databases.length) throw new Error('No Seerr databases found');

  for (const file of databases) {
    const source = new DatabaseSync(join(config, 'db', file), { readOnly: true });
    const target = join(temporary, 'db', file);
    try {
      await backup(source, target);
    } finally {
      source.close();
    }
    await chmod(target, 0o600);
    const check = new DatabaseSync(target, { readOnly: true });
    try {
      if (check.prepare('PRAGMA integrity_check').get().integrity_check !== 'ok')
        throw new Error('Backup integrity check failed');
    } finally {
      check.close();
    }
  }
  const settings = await readFile(join(config, 'settings.json'));
  JSON.parse(settings);
  await writeFile(join(temporary, 'settings.json'), settings, { mode: 0o600 });
  const digest = managed ? retention('hash', temporary) : '';
  const previous = managed ? retention('reuse', destination, digest) : '';
  if (previous) {
    await rm(temporary, { recursive: true });
    console.log('Fresh Seerr snapshot matches verified previous publication');
  } else {
    await rename(temporary, join(destination, name));
    if (managed) retention('complete', destination, name, digest);
  }
  await writeFile(marker, String(Date.now()), { mode: 0o600 });
  console.log(`Seerr backup complete: ${previous || name}`);
} finally {
  await rm(temporary, { recursive: true, force: true });
}
