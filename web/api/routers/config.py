"""앱 설정 API."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from web.api.database import get_session
from web.api.models import AppConfig

router = APIRouter(prefix="/api/config", tags=["config"])

_DEFAULTS: dict[str, str] = {
    # ── 예산 ──────────────────────────────────────────────
    "budget_limit":        "1000000",  # 총 투자 한도(원)
    "max_position_ratio":  "0.2",      # 종목당 최대 비율

    # ── 스윙 트레이딩 (30분 사이클) ─────────────────────
    "swing_sl_rate":       "3.0",      # 손절 %
    "swing_tp_rate":       "7.0",     # 익절 %
    "news_enabled":        "true",     # 뉴스 감성 필터 사용
    "news_threshold":      "-0.3",     # 매수 보류 기준 감성 점수

    # ── 스캘핑 ────────────────────────────────────────────
    "scalping_enabled":    "false",
    "scalp_sl_rate":       "0.5",
    "scalp_tp_rate":       "1.0",
    "scalp_max_hold":      "30",
    "scalp_max_pos":       "3",
    "scalp_invest":        "500000",
}

_BOOL_KEYS = {"scalping_enabled", "news_enabled"}


def get_config(session: Session) -> dict:
    rows = session.exec(select(AppConfig)).all()
    cfg = dict(_DEFAULTS)
    cfg.update({r.key: r.value for r in rows})
    return cfg


def set_config_value(session: Session, key: str, value: str) -> None:
    row = session.get(AppConfig, key)
    if row:
        row.value = value
    else:
        row = AppConfig(key=key, value=value)
        session.add(row)
    session.commit()


def _serialize(cfg: dict) -> dict:
    return {
        # 예산
        "budget_limit":       int(cfg["budget_limit"]),
        "max_position_ratio": float(cfg["max_position_ratio"]),
        # 스윙
        "swing_sl_rate":      float(cfg["swing_sl_rate"]),
        "swing_tp_rate":      float(cfg["swing_tp_rate"]),
        "news_enabled":       cfg["news_enabled"] == "true",
        "news_threshold":     float(cfg["news_threshold"]),
        # 스캘핑
        "scalping_enabled":   cfg["scalping_enabled"] == "true",
        "scalp_sl_rate":      float(cfg["scalp_sl_rate"]),
        "scalp_tp_rate":      float(cfg["scalp_tp_rate"]),
        "scalp_max_hold":     int(cfg["scalp_max_hold"]),
        "scalp_max_pos":      int(cfg["scalp_max_pos"]),
        "scalp_invest":       int(cfg["scalp_invest"]),
    }


@router.get("")
def read_config(session: Session = Depends(get_session)):
    return _serialize(get_config(session))


@router.patch("")
def update_config(body: dict, session: Session = Depends(get_session)):
    allowed = set(_DEFAULTS.keys())
    for key, value in body.items():
        if key not in allowed:
            continue
        if key in _BOOL_KEYS:
            set_config_value(session, key, "true" if value else "false")
        else:
            set_config_value(session, key, str(value))
    return _serialize(get_config(session))
