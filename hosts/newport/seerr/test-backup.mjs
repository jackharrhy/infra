import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { test } from 'node:test';

const script = new URL('./backup.mjs', import.meta.url);

test('online backup includes committed WAL data and settings', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'seerr-backup-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const config = join(root, 'config');
  const output = join(root, 'backups');
  mkdirSync(join(config, 'db'), { recursive: true });
  const settings = { main: { applicationTitle: 'Fixture' } };
  writeFileSync(join(config, 'settings.json'), JSON.stringify(settings));
  const db = new DatabaseSync(join(config, 'db', 'db.sqlite3'));
  db.exec('PRAGMA journal_mode=WAL; PRAGMA wal_autocheckpoint=0; CREATE TABLE users(id INTEGER); INSERT INTO users VALUES(7)');
  const result = spawnSync(process.execPath, [script.pathname], {
    env: { ...process.env, SEERR_CONFIG_FOLDER: config, SEERR_BACKUP_FOLDER: output },
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  const published = readdirSync(output).filter(name => !name.startsWith('.'));
  assert.equal(published.length, 1);
  const snapshot = join(output, published[0]);
  const restored = new DatabaseSync(join(snapshot, 'db', 'db.sqlite3'), { readOnly: true });
  assert.equal(restored.prepare('PRAGMA integrity_check').get().integrity_check, 'ok');
  assert.equal(restored.prepare('SELECT id FROM users').get().id, 7);
  assert.deepEqual(JSON.parse(readFileSync(join(snapshot, 'settings.json'))), settings);
  restored.close();
  db.close();
});

test('daily checks reuse a successful recent backup', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'seerr-daily-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const config = join(root, 'config');
  const output = join(root, 'backups');
  mkdirSync(join(config, 'db'), { recursive: true });
  writeFileSync(join(config, 'settings.json'), '{}');
  const db = new DatabaseSync(join(config, 'db', 'db.sqlite3'));
  db.exec('CREATE TABLE users(id INTEGER)');
  db.close();
  const options = { env: { ...process.env, SEERR_CONFIG_FOLDER: config, SEERR_BACKUP_FOLDER: output }, encoding: 'utf8' };
  assert.equal(spawnSync(process.execPath, [script.pathname], options).status, 0);
  assert.equal(spawnSync(process.execPath, [script.pathname, 'daily'], options).status, 0);
  assert.equal(readdirSync(output).filter(name => !name.startsWith('.')).length, 1);
});
