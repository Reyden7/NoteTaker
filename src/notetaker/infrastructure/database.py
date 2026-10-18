"""Transactional migrations and consistent backups before upgrading existing data."""
import sqlite3
from pathlib import Path

MIGRATIONS = {1: [
    "CREATE TABLE session (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE job (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES session(id), kind TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','cancelled','interrupted')), error_code TEXT)",
], 2: [
    "ALTER TABLE session ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE session ADD COLUMN archived INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE session ADD COLUMN revision INTEGER NOT NULL DEFAULT 0",
    "CREATE TABLE audio_take(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES session(id),kind TEXT NOT NULL,path TEXT NOT NULL,status TEXT NOT NULL,sha256 TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE speaker(id TEXT NOT NULL,session_id TEXT NOT NULL REFERENCES session(id),label TEXT NOT NULL,PRIMARY KEY(session_id,id))",
    "CREATE TABLE utterance(id TEXT NOT NULL,session_id TEXT NOT NULL REFERENCES session(id),speaker_id TEXT,start_ms INTEGER NOT NULL,end_ms INTEGER NOT NULL,text TEXT NOT NULL,uncertain INTEGER NOT NULL DEFAULT 1,source_json TEXT NOT NULL,PRIMARY KEY(session_id,id))",
    "CREATE TABLE manual_record(session_id TEXT PRIMARY KEY REFERENCES session(id),votes_json TEXT NOT NULL DEFAULT '[]',decisions_json TEXT NOT NULL DEFAULT '[]')",
    "CREATE TABLE draft_minutes(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES session(id),revision INTEGER NOT NULL,content_json TEXT NOT NULL,review_json TEXT,context_sha256 TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE export(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES session(id),draft_id TEXT NOT NULL REFERENCES draft_minutes(id),format TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE edit_history(id INTEGER PRIMARY KEY,session_id TEXT NOT NULL REFERENCES session(id),kind TEXT NOT NULL,content_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX utterance_session_time ON utterance(session_id,start_ms)",
    "CREATE INDEX draft_session ON draft_minutes(session_id,revision)",
], 3: ["ALTER TABLE audio_take ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"], 4: [
    "CREATE TABLE directory_person(id TEXT PRIMARY KEY,first_name TEXT NOT NULL,last_name TEXT NOT NULL,position TEXT NOT NULL DEFAULT '',municipality TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),revision INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE directory_history(id INTEGER PRIMARY KEY,person_id TEXT NOT NULL REFERENCES directory_person(id),action TEXT NOT NULL,content_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE session_participant(session_id TEXT NOT NULL REFERENCES session(id),person_id TEXT NOT NULL REFERENCES directory_person(id),snapshot_json TEXT NOT NULL,attendance TEXT NOT NULL CHECK(attendance IN ('unconfirmed','present','absent','excused','represented')),session_role TEXT NOT NULL DEFAULT '',proxy_to_person_id TEXT,proxy_note TEXT NOT NULL DEFAULT '',sort_order INTEGER NOT NULL,PRIMARY KEY(session_id,person_id),FOREIGN KEY(session_id,proxy_to_person_id) REFERENCES session_participant(session_id,person_id) DEFERRABLE INITIALLY DEFERRED)",
]}

def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if 0 < version < max(MIGRATIONS):
            import uuid
            backups = path.parent / 'migration-backups'
            backups.mkdir(exist_ok=True)
            target = backups / f'{path.stem}-v{version}-before-v{max(MIGRATIONS)}-{uuid.uuid4().hex}.sqlite3'
            backup_database(connection, target)
            with sqlite3.connect(target) as saved:
                if saved.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise RuntimeError('MIGRATION_BACKUP_INVALID')
        migrate(connection)
    except BaseException:
        connection.close()
        raise
    return connection

def migrate(connection, migrations=None):
    migrations = MIGRATIONS if migrations is None else migrations
    connection.execute("BEGIN IMMEDIATE")
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > max(migrations, default=0):
            raise ValueError("DATABASE_NEWER_THAN_APPLICATION")
        for target, statements in sorted(migrations.items()):
            if target > version:
                for statement in statements:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version={int(target)}")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise

def recover_jobs(connection):
    """Only interrupted jobs become retryable; never repeat completed jobs/exports."""
    with connection:
        count = connection.execute("UPDATE job SET status='interrupted',error_code='PROCESS_INTERRUPTED' WHERE status='running'").rowcount
    return count

def backup_database(connection, destination: Path):
    if destination.exists():
        raise FileExistsError(destination)
    with sqlite3.connect(destination) as target:
        connection.backup(target)
