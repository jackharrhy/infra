import { Database } from 'bun:sqlite';
import { mkdirSync, chmodSync, renameSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

process.umask(0o077);
const source = process.env.DB_PATH ?? '/data/lists.db';
const directory = process.env.LISTS_BACKUP_DIR ?? '/backups';
const name = `lists-${new Date().toISOString().replaceAll(':', '-')}-${crypto.randomUUID()}.sqlite`;
const temporary = join(directory, `${name}.partial`);
const final = join(directory, name);
let database;
let snapshot;
try {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  database = new Database(source, { readonly: true, strict: true });
  database.exec('PRAGMA busy_timeout=5000');
  database.query('VACUUM INTO ?').run(temporary);
  database.close();
  database = undefined;
  chmodSync(temporary, 0o600);
  snapshot = new Database(temporary, { readonly: true, strict: true });
  const integrity = snapshot.query('PRAGMA integrity_check').all();
  if (integrity.length !== 1 || Object.values(integrity[0])[0] !== 'ok') throw new Error('Snapshot integrity failed');
  if (snapshot.query('PRAGMA foreign_key_check').all().length) throw new Error('Snapshot foreign keys failed');
  snapshot.close();
  snapshot = undefined;
  renameSync(temporary, final);
  console.log(JSON.stringify({ status: 'verified', backup: final }));
} catch (error) {
  try { snapshot?.close(); } catch {}
  try { database?.close(); } catch {}
  try { unlinkSync(temporary); } catch {}
  console.error('Lists pre-update backup failed; update must remain blocked.');
  process.exitCode = 75;
}
