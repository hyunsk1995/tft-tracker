import json
from datetime import datetime

from config import ACHIEVE_FILE


def load_achievements() -> dict[str, str]:
    if not ACHIEVE_FILE.exists():
        return {}
    try:
        return json.loads(ACHIEVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_achievements(rows: list[dict]) -> dict[str, str]:
    """목표(남은 LP 0)에 처음 도달한 사람만 달성 시각을 기록한다. 한 번 기록된 값은 바뀌지 않는다."""
    ach = load_achievements()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    changed = False
    for r in rows:
        if r["오류"] or r["남은LP"] != 0:
            continue
        if r["이름"] in ach:
            continue
        ach[r["이름"]] = now
        changed = True
    if changed:
        ACHIEVE_FILE.write_text(json.dumps(ach, ensure_ascii=False, indent=2), encoding="utf-8")
    return ach