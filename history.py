import json
from datetime import datetime, timedelta

from config import HISTORY_FILE
from tiers import format_short_rank, parse_goal, to_total_lp


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def load_yesterday_snapshot(history: list[dict]) -> dict[str, dict]:
    """어제 날짜의 마지막 기록을 기준으로 삼는다. 없으면 빈 dict."""
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    for record in reversed(history):
        if record.get("timestamp", "")[:10] == yesterday:
            return {r["이름"]: r for r in record.get("players", [])}
    return {}


def save_history(history: list[dict], rows: list[dict]) -> None:
    history.append({"timestamp": datetime.now().isoformat(timespec="seconds"), "players": rows})
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def build_row(player: dict, found: tuple | None, error: str | None, prev: dict | None) -> dict:
    goal_total = parse_goal(player["goal"])
    if found:
        tier, div, lp = found
        short = format_short_rank(tier, div, lp)
        total = to_total_lp(tier, div, lp)
    else:
        short, total = "조회실패", None

    remaining = max(0, goal_total - total) if total is not None else None
    prev_total = prev.get("누적점수") if prev else None
    change = total - prev_total if (total is not None and prev_total is not None) else None

    return {
        "팀": player["team"],
        "이름": player["name"],
        "닉네임": player["riot_id"],
        "현재랭크": short,
        "누적점수": total,
        "목표": player["goal"],
        "목표점수": goal_total,
        "남은LP": remaining,
        "변화LP": change,
        "오류": error,
    }