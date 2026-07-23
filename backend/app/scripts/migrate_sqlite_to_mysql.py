from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.database import Base
from app.models import *  # noqa: F401,F403


def mysql_url(host: str, port: int, user: str, password: str, database: str, charset: str) -> str:
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
        f"?charset={charset}&ssl_disabled=true"
    )


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def migrate(sqlite_engine: Engine, mysql_engine: Engine) -> dict[str, int]:
    Base.metadata.create_all(bind=mysql_engine)
    copied: dict[str, int] = {}
    source_inspector = inspect(sqlite_engine)
    source_table_names = set(source_inspector.get_table_names())

    with sqlite_engine.connect() as source, mysql_engine.begin() as target:
        for table in Base.metadata.sorted_tables:
            if table.name not in source_table_names:
                copied[table.name] = 0
                continue

            source_column_names = {column["name"] for column in source_inspector.get_columns(table.name)}
            selectable_columns = [column for column in table.columns if column.name in source_column_names]
            if not selectable_columns:
                copied[table.name] = 0
                continue

            source_rows = [dict(row._mapping) for row in source.execute(select(*selectable_columns)).all()]
            if not source_rows:
                copied[table.name] = 0
                continue

            primary_key_columns = list(table.primary_key.columns)
            existing_keys = set()
            if primary_key_columns:
                primary_key_column = primary_key_columns[0]
                existing_keys = {row[0] for row in target.execute(select(primary_key_column)).all()}

            rows_to_insert = []
            for row in source_rows:
                if primary_key_columns and row[primary_key_columns[0].name] in existing_keys:
                    continue
                rows_to_insert.append(row)

            if rows_to_insert:
                target.execute(table.insert(), rows_to_insert)
            copied[table.name] = len(rows_to_insert)

    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate the local SQLite database into MySQL.")
    parser.add_argument("--sqlite-path", default="quant_simulator.db")
    parser.add_argument("--mysql-url", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="")
    parser.add_argument("--charset", default="utf8mb4")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    source = create_engine(sqlite_url(sqlite_path), connect_args={"check_same_thread": False})
    target_url = args.mysql_url or settings.database_url
    if not target_url.startswith("mysql"):
        if not all([args.host, args.user, args.password, args.database]):
            raise SystemExit("Provide --mysql-url or host/user/password/database arguments for the MySQL target.")
        target_url = mysql_url(args.host, args.port, args.user, args.password, args.database, args.charset)

    target = create_engine(target_url, pool_pre_ping=True)
    copied = migrate(source, target)
    for table_name, count in copied.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
