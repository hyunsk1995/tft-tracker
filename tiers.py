import re

from config import UNRANKED_POINTS

# 아이언 0점 시작, 티어당 400점, 디비전당 100점, 마스터 이상은 2800 기준 + LP
TIER_BASE = {
    "IRON": 0, "BRONZE": 400, "SILVER": 800, "GOLD": 1200,
    "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400,
    "MASTER": 2800, "GRANDMASTER": 2800, "CHALLENGER": 2800,
}
APEX = {"MASTER", "GRANDMASTER", "CHALLENGER"}

TIER_SHORT = {
    "IRON": "I", "BRONZE": "B", "SILVER": "S", "GOLD": "G",
    "PLATINUM": "P", "EMERALD": "E", "DIAMOND": "D",
    "MASTER": "M", "GRANDMASTER": "GM", "CHALLENGER": "C",
}
SHORT_TO_TIER = {v: k for k, v in TIER_SHORT.items()}

TIER_KO = {
    "IRON": "아이언", "BRONZE": "브론즈", "SILVER": "실버", "GOLD": "골드",
    "PLATINUM": "플래티넘", "EMERALD": "에메랄드", "DIAMOND": "다이아몬드",
    "MASTER": "마스터", "GRANDMASTER": "그랜드마스터", "CHALLENGER": "챌린저",
}
KO_TIER = {
    "아이언": "IRON", "브론즈": "BRONZE", "실버": "SILVER", "골드": "GOLD",
    "플래티넘": "PLATINUM", "플레티넘": "PLATINUM", "에메랄드": "EMERALD",
    "다이아": "DIAMOND", "다이아몬드": "DIAMOND", "마스터": "MASTER",
    "그랜드마스터": "GRANDMASTER", "챌린저": "CHALLENGER",
}

ROMAN_TO_DIV = {"IV": "4", "III": "3", "II": "2", "I": "1"}
DIV_OFFSET = {"4": 0, "3": 100, "2": 200, "1": 300}

GOAL_RE = re.compile(r"^\s*(GM|[IBSGPEDMC])\s*(.*?)\s*$", re.IGNORECASE)


def to_total_lp(tier: str, div: str | None, lp: int | None) -> int | None:
    if lp is None:
        return None
    if tier == "UNRANKED":
        return UNRANKED_POINTS
    if tier not in TIER_BASE:
        return None
    base = TIER_BASE[tier]
    if tier in APEX:
        return base + lp
    if div is None:
        return None
    d = ROMAN_TO_DIV.get(div.upper(), div)
    if d not in DIV_OFFSET:
        return None
    return base + DIV_OFFSET[d] + lp


def format_short_rank(tier: str, div: str | None, lp: int | None) -> str:
    lp_txt = "?" if lp is None else str(lp)
    if tier == "UNRANKED":
        return f"UR {lp_txt}"
    short = TIER_SHORT.get(tier, "UR")
    if tier in APEX:
        return f"{short} {lp_txt}"
    d = ROMAN_TO_DIV.get(div.upper(), div) if div else "?"
    return f"{short}{d} {lp_txt}"


def parse_goal(goal: str) -> int:
    """'M 0', 'M 200', 'D4 0', 'E4 50' 형태를 누적 점수로 변환"""
    m = GOAL_RE.match(goal)
    if not m:
        raise ValueError(f"목표 형식 오류: {goal!r}")
    tier = SHORT_TO_TIER[m.group(1).upper()]
    rest = m.group(2).strip()

    if tier in APEX:
        lp = int(rest) if rest.isdigit() else 0
        return TIER_BASE[tier] + lp

    dm = re.fullmatch(r"([1-4])\s*(\d+)?", rest)
    if not dm:
        raise ValueError(f"목표 형식 오류: {goal!r} (예: 'D4 0')")
    div = dm.group(1)
    lp = int(dm.group(2) or 0)
    return TIER_BASE[tier] + DIV_OFFSET[div] + lp


def goal_label(goal: str) -> str:
    """'E4 0' -> '에메랄드', 'M 0' -> '마스터'"""
    m = GOAL_RE.match(goal)
    return TIER_KO[SHORT_TO_TIER[m.group(1).upper()]]