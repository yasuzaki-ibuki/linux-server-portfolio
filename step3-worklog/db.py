import sqlite3
from pathlib import Path

# データベースファイルの場所(このファイルと同じフォルダの data/worklog.db)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "worklog.db"

# テーブル(表)の設計図
SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('障害', '作業', '改善')),
    title       TEXT NOT NULL,
    event       TEXT,
    impact      TEXT,
    cause       TEXT,
    action      TEXT,
    prevention  TEXT,
    status      TEXT NOT NULL DEFAULT '対応中' CHECK (status IN ('対応中', '完了')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_conn():
    """データベースに接続する"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 列名で値を取り出せるようにする
    return conn


def init_db():
    """データベースとテーブルを作る(すでにあれば何もしない)"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
