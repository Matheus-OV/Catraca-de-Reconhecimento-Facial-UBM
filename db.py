"""Módulo de persistência local utilizando SQLite3 nativo do Python.

Substitui a dependência externa do PostgreSQL por um banco de dados local
(`reconhecimento.db`) inicializado automaticamente na partida da aplicação.
"""

from __future__ import annotations

import base64
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("RF_DB_PATH", str(BASE_DIR / "reconhecimento.db")))


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Gerencia a conexão com o banco SQLite local."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Cria as tabelas `people` e `detections` caso ainda não existam."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                embedding BLOB NOT NULL,
                photo BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_name TEXT,
                faces_count INTEGER NOT NULL,
                recognized_names TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


def add_person(name: str, embedding_bytes: bytes, photo_bytes: bytes) -> int:
    """Insere uma nova pessoa cadastrada e retorna seu ID."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO people (name, embedding, photo) VALUES (?, ?, ?)",
            (name.strip(), embedding_bytes, photo_bytes),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def get_all_people() -> list[dict[str, Any]]:
    """Retorna todas as pessoas cadastradas com nome, embedding e foto em base64."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, embedding, photo, created_at FROM people ORDER BY name ASC"
        )
        rows = cur.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            photo_b64 = (
                base64.b64encode(row["photo"]).decode("utf-8")
                if row["photo"]
                else ""
            )
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "embedding": row["embedding"],
                    "photo_b64": photo_b64,
                    "created_at": row["created_at"],
                }
            )
        return result


def delete_person(person_id: int) -> bool:
    """Remove uma pessoa pelo ID. Retorna True se algum registro foi removido."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM people WHERE id = ?", (person_id,))
        conn.commit()
        return cur.rowcount > 0


def save_detection(
    image_name: str, faces_count: int, recognized_names: list[str]
) -> int:
    """Registra um evento de detecção/reconhecimento no histórico."""
    init_db()
    names_str = ", ".join(recognized_names) if recognized_names else "Nenhum"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO detections (image_name, faces_count, recognized_names) VALUES (?, ?, ?)",
            (image_name, int(faces_count), names_str),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def list_detections(limit: int = 50) -> list[dict[str, Any]]:
    """Retorna os registros mais recentes de detecções."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, image_name, faces_count, recognized_names, created_at
            FROM detections
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
