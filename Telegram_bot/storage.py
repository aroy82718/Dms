"""Small async-compatible SQLite document store used by the Telegram bot.

The original bot used MongoDB documents. This adapter intentionally exposes the
small subset of Motor's collection API used by the bot so the user-facing
flows remain unchanged while local and Railway deployments use one SQLite file.
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
from typing import Any, AsyncIterator


def _get_path(document: dict[str, Any], path: str) -> Any:
    value: Any = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _set_path(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = document
    for part in parts[:-1]:
        if not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        actual = _get_path(document, key)
        if isinstance(expected, dict):
            for operator, operand in expected.items():
                if operator == "$gt" and not (actual is not None and actual > operand):
                    return False
                if operator == "$gte" and not (actual is not None and actual >= operand):
                    return False
                if operator == "$lt" and not (actual is not None and actual < operand):
                    return False
                if operator == "$lte" and not (actual is not None and actual <= operand):
                    return False
                if operator == "$in" and actual not in operand:
                    return False
        elif actual != expected:
            return False
    return True


def _apply_update(document: dict[str, Any], update: dict[str, Any]) -> None:
    for operator, values in update.items():
        if operator == "$set":
            for path, value in values.items():
                _set_path(document, path, copy.deepcopy(value))
        elif operator == "$inc":
            for path, amount in values.items():
                current = _get_path(document, path)
                _set_path(document, path, (current or 0) + amount)
        elif operator == "$push":
            for path, value in values.items():
                current = _get_path(document, path)
                if not isinstance(current, list):
                    current = []
                    _set_path(document, path, current)
                current.append(copy.deepcopy(value))
        elif operator == "$addToSet":
            for path, value in values.items():
                current = _get_path(document, path)
                if not isinstance(current, list):
                    current = []
                    _set_path(document, path, current)
                if value not in current:
                    current.append(copy.deepcopy(value))
        else:
            raise ValueError(f"Unsupported SQLite document update operator: {operator}")


class SQLiteCursor:
    def __init__(self, documents: list[dict[str, Any]]):
        self.documents = documents

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        if length is None:
            return copy.deepcopy(self.documents)
        return copy.deepcopy(self.documents[:length])

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict[str, Any]]:
        for document in self.documents:
            yield copy.deepcopy(document)


class SQLiteCollection:
    def __init__(self, connection: sqlite3.Connection, name: str):
        self.connection = connection
        self.name = name

    def _load_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT document FROM documents WHERE collection = ?", (self.name,)
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _save(self, document: dict[str, Any]) -> None:
        key = str(document["_id"])
        self.connection.execute(
            """
            INSERT INTO documents(collection, document_id, document)
            VALUES (?, ?, ?)
            ON CONFLICT(collection, document_id)
            DO UPDATE SET document = excluded.document
            """,
            (self.name, key, json.dumps(document, separators=(",", ":"))),
        )
        self.connection.commit()

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for document in self._load_all():
            if _matches(document, query):
                return copy.deepcopy(document)
        return None

    async def insert_one(self, document: dict[str, Any]) -> None:
        self._save(copy.deepcopy(document))

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> None:
        document = await self.find_one(query)
        if document is None:
            if not upsert:
                return
            document = {
                key: copy.deepcopy(value)
                for key, value in query.items()
                if not isinstance(value, dict)
            }
            if "_id" not in document:
                raise ValueError("SQLite upsert requires an _id")
        _apply_update(document, update)
        self._save(document)

    async def count_documents(self, query: dict[str, Any]) -> int:
        return sum(1 for document in self._load_all() if _matches(document, query))

    def find(self, query: dict[str, Any]) -> SQLiteCursor:
        return SQLiteCursor(
            [document for document in self._load_all() if _matches(document, query)]
        )

    def aggregate(self, pipeline: list[dict[str, Any]]) -> SQLiteCursor:
        documents = self._load_all()
        for stage in pipeline:
            if "$match" in stage:
                documents = [
                    document
                    for document in documents
                    if _matches(document, stage["$match"])
                ]
            elif "$sort" in stage:
                for field, direction in reversed(list(stage["$sort"].items())):
                    documents.sort(
                        key=lambda document: _get_path(document, field) or 0,
                        reverse=direction < 0,
                    )
            elif "$limit" in stage:
                documents = documents[: stage["$limit"]]
        return SQLiteCursor(documents)


class SQLiteStore:
    def __init__(self, path: str):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                collection TEXT NOT NULL,
                document_id TEXT NOT NULL,
                document TEXT NOT NULL,
                PRIMARY KEY (collection, document_id)
            )
            """
        )
        self.connection.commit()

    def collection(self, name: str) -> SQLiteCollection:
        return SQLiteCollection(self.connection, name)

    def close(self) -> None:
        self.connection.close()