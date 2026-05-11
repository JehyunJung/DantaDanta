"""봇 전역 상태 — 일시정지 플래그."""

_paused: bool = False


def is_paused() -> bool:
    return _paused


def set_paused(value: bool) -> None:
    global _paused
    _paused = value
