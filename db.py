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
# No Vercel o disco é somente leitura (exceto /tmp), então o banco vai para /tmp.
_default_db = "/tmp/reconhecimento.db" if os.getenv("VERCEL") else str(BASE_DIR / "reconhecimento.db")
DB_PATH = Path(os.getenv("RF_DB_PATH", _default_db))

# Situações possíveis da matrícula. Só "ativa" libera o acesso.
SITUACOES = ("ativa", "trancada", "cancelada", "formada")


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Gerencia a conexão com o banco SQLite local."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    """Migração simples: adiciona a coluna em bancos criados por versões antigas."""
    cols = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    """Cria as tabelas `people` e `detections` e aplica as migrações necessárias."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                embedding BLOB NOT NULL,
                photo BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                matricula TEXT,
                situacao TEXT NOT NULL DEFAULT 'ativa',
                consent_at TIMESTAMP
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                decisions TEXT
            );
            """
        )
        # Bancos antigos (sem as colunas novas) são atualizados aqui.
        _add_column_if_missing(cur, "people", "matricula", "TEXT")
        _add_column_if_missing(cur, "people", "situacao", "TEXT NOT NULL DEFAULT 'ativa'")
        _add_column_if_missing(cur, "people", "consent_at", "TIMESTAMP")
        _add_column_if_missing(cur, "detections", "decisions", "TEXT")
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_people_matricula ON people(matricula)"
        )
        conn.commit()


def add_person(
    name: str,
    embedding_bytes: bytes,
    photo_bytes: bytes,
    matricula: str | None = None,
    situacao: str = "ativa",
    consented: bool = False,
) -> int:
    """Insere uma nova pessoa cadastrada e retorna seu ID.

    `consented=True` grava a data/hora do aceite do termo de consentimento (LGPD).
    Lança `sqlite3.IntegrityError` se a matrícula já existir.
    """
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO people (name, embedding, photo, matricula, situacao, consent_at)
            VALUES (?, ?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END)
            """,
            (
                name.strip(),
                embedding_bytes,
                photo_bytes,
                matricula.strip() if matricula else None,
                situacao,
                1 if consented else 0,
            ),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def _row_to_person(row: sqlite3.Row) -> dict[str, Any]:
    photo_b64 = (
        base64.b64encode(row["photo"]).decode("utf-8") if row["photo"] else ""
    )
    return {
        "id": row["id"],
        "name": row["name"],
        "embedding": row["embedding"],
        "photo_b64": photo_b64,
        "created_at": row["created_at"],
        "matricula": row["matricula"],
        "situacao": row["situacao"],
        "consent_at": row["consent_at"],
    }


_PEOPLE_COLUMNS = (
    "id, name, embedding, photo, created_at, matricula, situacao, consent_at"
)


def get_all_people() -> list[dict[str, Any]]:
    """Retorna todas as pessoas cadastradas (inclui embedding e foto em base64)."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {_PEOPLE_COLUMNS} FROM people ORDER BY name ASC")
        return [_row_to_person(row) for row in cur.fetchall()]


def get_person(person_id: int) -> dict[str, Any] | None:
    """Retorna uma pessoa pelo ID, ou None se não existir."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {_PEOPLE_COLUMNS} FROM people WHERE id = ?", (person_id,))
        row = cur.fetchone()
        return _row_to_person(row) if row else None


def update_situacao(person_id: int, situacao: str) -> bool:
    """Altera a situação da matrícula. Retorna True se a pessoa existe."""
    if situacao not in SITUACOES:
        raise ValueError(f"Situação inválida. Use: {', '.join(SITUACOES)}.")
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE people SET situacao = ? WHERE id = ?", (situacao, person_id))
        conn.commit()
        return cur.rowcount > 0


def delete_person(person_id: int) -> bool:
    """Remove uma pessoa pelo ID. Retorna True se algum registro foi removido."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM people WHERE id = ?", (person_id,))
        conn.commit()
        return cur.rowcount > 0


def save_detection(
    image_name: str,
    faces_count: int,
    recognized_names: list[str],
    decisions: list[str] | None = None,
) -> int:
    """Registra um evento de detecção/reconhecimento no histórico.

    `decisions` guarda a decisão de acesso e o motivo de cada rosto,
    por exemplo `["Maria Silva: liberado", "Rosto não cadastrado: negado"]`.
    """
    init_db()
    names_str = ", ".join(recognized_names) if recognized_names else "Nenhum"
    decisions_str = "; ".join(decisions) if decisions else None
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO detections (image_name, faces_count, recognized_names, decisions)
            VALUES (?, ?, ?, ?)
            """,
            (image_name, int(faces_count), names_str, decisions_str),
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
            SELECT id, image_name, faces_count, recognized_names, created_at, decisions
            FROM detections
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
