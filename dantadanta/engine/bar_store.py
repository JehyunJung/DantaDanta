"""시간봉 히스토리 저장소 — 분봉을 수집해 시간봉으로 적재."""

import sqlite3
from pathlib import Path

import pandas as pd

_DB_PATH = Path("dantadanta_bars.db")
MIN_BARS = 30  # 전략 실행에 필요한 최소 시간봉 수


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hourly_bars (
            symbol TEXT NOT NULL,
            dt     TEXT NOT NULL,
            open   REAL,
            high   REAL,
            low    REAL,
            close  REAL,
            volume REAL,
            PRIMARY KEY (symbol, dt)
        )
    """)
    conn.commit()
    return conn


def save_bars(symbol: str, df: pd.DataFrame) -> int:
    """시간봉 DataFrame을 DB에 upsert. 저장된 행 수 반환."""
    if df.empty:
        return 0
    with _conn() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT OR REPLACE INTO hourly_bars VALUES (?,?,?,?,?,?,?)",
                (symbol, str(row["dt"]), row["open"], row["high"], row["low"], row["close"], row["volume"]),
            )
        conn.commit()
    return len(df)


def load_bars(symbol: str, limit: int = 200) -> pd.DataFrame:
    """저장된 시간봉 로드 (오래된 순)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT dt, open, high, low, close, volume FROM hourly_bars "
            "WHERE symbol=? ORDER BY dt DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def bar_count(symbol: str) -> int:
    """저장된 시간봉 수 반환."""
    with _conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM hourly_bars WHERE symbol=?", (symbol,)
        ).fetchone()[0]
