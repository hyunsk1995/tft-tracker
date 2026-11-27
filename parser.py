import re

from tiers import APEX, KO_TIER, ROMAN_TO_DIV, TIER_BASE

TIER_PAT = (
    r"그랜드마스터|챌린저|마스터|다이아몬드|다이아|에메랄드|플래티넘|플레티넘"
    r"|골드|실버|브론즈|아이언"
    r"|GRANDMASTER|CHALLENGER|MASTER|DIAMOND|EMERALD|PLATINUM|GOLD|SILVER|BRONZE|IRON"
)
# 예: "Master0 LP", "Unranked0 LP", "다이아몬드 I 81 LP", "EMERALD IV 20 LP"
RANK_RE = re.compile(
    r"(?<![A-Za-z가-힣])(Unranked|" + TIER_PAT + r")"
    r"(?:\s*(IV|III|II|I|[1-4]))?"
    r"\s*(\d{1,4})\s*LP",
    re.IGNORECASE,
)
NON_SOLO_RE = re.compile(
    r"더블\s*업|더블업|double\s*up|하이퍼\s*롤|hyper\s*roll|투기장|arena",
    re.IGNORECASE,
)
SOLO_ANCHOR = "랭크 게임"


def tier_from_text(raw: str) -> str | None:
    up = raw.upper()
    if up == "UNRANKED":
        return "UNRANKED"
    if up in TIER_BASE:
        return up
    return KO_TIER.get(raw)


def find_solo_rank(body_text: str) -> tuple[str, str | None, int] | None:
    """'랭크 게임' 섹션 우선으로 솔로 랭크 (티어, 디비전, LP)를 찾는다."""
    matches = list(RANK_RE.finditer(body_text))
    if not matches:
        return None

    anchor = body_text.find(SOLO_ANCHOR)
    if anchor >= 0:
        ordered = [m for m in matches if m.start() >= anchor] + \
                  [m for m in matches if m.start() < anchor]
    else:
        ordered = matches

    for m in ordered:
        before = body_text[max(0, m.start() - 40):m.start()]
        if NON_SOLO_RE.search(before):
            continue  # 더블 업 등 비솔로 수치

        tier = tier_from_text(m.group(1))
        if tier is None:
            continue

        div_raw = m.group(2)
        div = ROMAN_TO_DIV.get(div_raw.upper(), div_raw) if div_raw else None
        lp = int(m.group(3))

        if tier not in APEX and tier != "UNRANKED" and div is None:
            continue
        return tier, div, lp
    return None