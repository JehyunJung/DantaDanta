"""시간봉 히스토리 저장소 — yfinance 초기 적재 + KIS 분봉 실시간 추가."""

import sqlite3
from pathlib import Path

import pandas as pd
from loguru import logger

_DB_PATH = Path("dantadanta_bars.db")
MIN_BARS = 30  # 전략 실행에 필요한 최소 시간봉 수

# KRX 종목 yfinance 티커: 005930 → 005930.KS
def _to_yf_ticker(symbol: str, market: str = "KRX") -> str:
    if market == "KRX":
        return f"{symbol}.KS"
    return symbol  # 해외는 그대로


def warmup_from_yfinance(symbol: str, market: str = "KRX", period: str = "60d") -> int:
    """yfinance로 시간봉 히스토리를 즉시 적재. 이미 충분히 쌓여 있으면 스킵."""
    if bar_count(symbol) >= MIN_BARS:
        return 0
    try:
        import yfinance as yf
        ticker = _to_yf_ticker(symbol, market)
        df = yf.download(ticker, period=period, interval="1h", progress=False, auto_adjust=True)
        if df.empty:
            return 0
        df = df.reset_index()
        # MultiIndex 컬럼 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns={"Datetime": "dt", "Open": "open", "High": "high",
                                 "Low": "low", "Close": "close", "Volume": "volume"})
        df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize(None)
        df = df[["dt", "open", "high", "low", "close", "volume"]].dropna()
        n = save_bars(symbol, df)
        logger.info("yfinance 시간봉 적재 | {} {}개 봉", symbol, n)
        return n
    except Exception as exc:
        logger.warning("yfinance 적재 실패 | {}: {}", symbol, exc)
        return 0


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
