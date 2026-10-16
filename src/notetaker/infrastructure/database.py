"""First migration only. Full session editing is phase 1."""
import sqlite3
from pathlib import Path

MIGRATIONS = {1: [
    "CREATE TABLE session (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE job (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES session(id), kind TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','cancelled','interrupted')), error_code TEXT)",
]}

def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    try:
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
