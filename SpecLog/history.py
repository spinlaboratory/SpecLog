"""Incremental SQLite cache for efficient historical monitor queries."""

import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sqlite3


class HistoryCache:
    def __init__(self, database_path):
        self.database_path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS log_rows (
                source_file TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                date_text TEXT NOT NULL,
                time_text TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (source_file, row_number)
            );
            CREATE INDEX IF NOT EXISTS log_rows_timestamp
                ON log_rows(timestamp);
            """
        )
        return connection

    def sync(self, files):
        """Import only files whose size or modification time has changed."""
        with self._connect() as connection:
            for file_path in map(Path, files):
                try:
                    stat = file_path.stat()
                except OSError:
                    continue
                cached = connection.execute(
                    "SELECT size, mtime_ns FROM files WHERE path = ?",
                    (str(file_path),),
                ).fetchone()
                signature = (stat.st_size, stat.st_mtime_ns)
                if cached == signature:
                    continue
                self._replace_file(connection, file_path, signature)

    def prune(self, existing_files):
        """Remove cached rows for log files that no longer exist."""
        existing = {str(Path(path)) for path in existing_files}
        with self._connect() as connection:
            cached = connection.execute("SELECT path FROM files").fetchall()
            for (path,) in cached:
                if path not in existing:
                    connection.execute(
                        "DELETE FROM log_rows WHERE source_file = ?", (path,)
                    )
                    connection.execute("DELETE FROM files WHERE path = ?", (path,))

    def _replace_file(self, connection, file_path, signature):
        path_string = str(file_path)
        rows = []
        with file_path.open("r", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
            if not header:
                return
            header = [name.strip() for name in header]
            for row_number, values in enumerate(reader, start=1):
                payload = {
                    name: value.strip()
                    for name, value in zip(header, values)
                }
                date_text = payload.get("Date")
                time_text = payload.get("Time")
                if not date_text or not time_text:
                    continue
                try:
                    timestamp = int(
                        (
                            datetime.strptime(
                                f"{date_text} {time_text}",
                                "%Y-%m-%d %H:%M:%S",
                            )
                            - datetime(1970, 1, 1)
                        ).total_seconds()
                    )
                except ValueError:
                    continue
                rows.append(
                    (
                        path_string,
                        row_number,
                        timestamp,
                        date_text,
                        time_text,
                        json.dumps(payload, separators=(",", ":")),
                    )
                )

        connection.execute("DELETE FROM log_rows WHERE source_file = ?", (path_string,))
        connection.executemany(
            """INSERT INTO log_rows
               (source_file, row_number, timestamp, date_text, time_text, payload)
               VALUES (?, ?, ?, ?, ?, ?)""",
            rows,
        )
        connection.execute(
            """INSERT INTO files(path, size, mtime_ns) VALUES (?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET
                   size=excluded.size, mtime_ns=excluded.mtime_ns""",
            (path_string, *signature),
        )

    def query(self, start=None, end=None, max_points=4000):
        clauses = []
        parameters = []
        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(start)
        if end is not None:
            clauses.append("timestamp <= ?")
            parameters.append(end)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT timestamp, date_text, time_text, payload "
            f"FROM log_rows {where} ORDER BY timestamp"
        )

        with self._connect() as connection:
            count = connection.execute(
                f"SELECT COUNT(*) FROM log_rows {where}", parameters
            ).fetchone()[0]
            cursor = connection.execute(sql, parameters)
            if count <= max_points:
                return [self._decode(row) for row in cursor]

            bucket_size = max(1, math.ceil(count / max(1, max_points // 2)))
            result = []
            bucket = []
            for row in cursor:
                bucket.append(self._decode(row))
                if len(bucket) >= bucket_size:
                    result.extend(self._bucket_envelope(bucket))
                    bucket = []
            if bucket:
                result.extend(self._bucket_envelope(bucket))
            return result

    @staticmethod
    def _decode(row):
        timestamp, date_text, time_text, payload = row
        return timestamp, date_text, time_text, json.loads(payload)

    @staticmethod
    def _bucket_envelope(rows):
        """Return two synthetic rows retaining each field's min/max."""
        if len(rows) <= 2:
            return rows
        numeric = {}
        text = {}
        for _timestamp, _date, _time, payload in rows:
            for name, value in payload.items():
                if name in {"Date", "Time"} or value == "nan":
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    text[name] = value
                else:
                    numeric.setdefault(name, []).append(number)

        first = rows[0]
        last = rows[-1]
        minimum = dict(text)
        maximum = dict(text)
        for name, values in numeric.items():
            minimum[name] = min(values)
            maximum[name] = max(values)
        minimum.update({"Date": first[1], "Time": first[2]})
        maximum.update({"Date": last[1], "Time": last[2]})
        return [
            (first[0], first[1], first[2], minimum),
            (last[0], last[1], last[2], maximum),
        ]
