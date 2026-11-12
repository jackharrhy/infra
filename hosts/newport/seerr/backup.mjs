import { DatabaseSync, backup } from 'node:sqlite';
import { chmod, mkdir, readFile, readdir, rename, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { join } from 'node:path';

const config = process.env.SEERR_CONFIG_FOLDER || '/app/config';
const destination = process.env.SEERR_BACKUP_FOLDER || '/backups';
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
await rename(temporary, join(destination, name));
await writeFile(marker, String(Date.now()), { mode: 0o600 });
console.log(`Seerr backup complete: ${name}`);
