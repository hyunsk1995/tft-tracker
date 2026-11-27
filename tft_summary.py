import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import re

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

# ---------- 설정 ----------
HEADLESS = False
HISTORY_FILE = Path("tft_history.json")
LATEST_CSV = Path("tft_4v4_latest.csv")
KAKAO_TXT = Path("tft_kakao_summary.txt")
DEBUG_DIR = Path("tft_debug")

TIE_THRESHOLD = 200    # 두 팀 남은 LP 합 차이가 이 값 이하면 무승부 멘트
UNRANKED_POINTS = 0    # 언랭크 = 아이언 4 0LP와 동일

# 목표 표기: "M 0", "M 200", "D4 0", "E4 50"
PLAYERS = [
    {"name": "김현성", "riot_id": "샤코무조건밴함#KR1", "team": "A팀", "goal": "M 0"},
    {"name": "허종원", "riot_id": "허조이#KR1", "team": "A팀", "goal": "E4 0"},
    {"name": "최민교", "riot_id": "밍링링#KR930", "team": "A팀", "goal": "E4 0"},
    {"name": "김명진", "riot_id": "밝은보배#KR1", "team": "A팀", "goal": "P4 0"},
    {"name": "안훈규", "riot_id": "ORaNGE TUNNEL#KR1", "team": "B팀", "goal": "D4 0"},
    {"name": "이민훈", "riot_id": "protein shake#0215", "team": "B팀", "goal": "E4 0"},
    {"name": "이서희", "riot_id": "수퍼 말차 워터#KR1", "team": "B팀", "goal": "E4 0"},
    {"name": "최요하", "riot_id": "97463520del#KR1", "team": "B팀", "goal": "P4 0"},
]

TAUNT_BEHIND = [
    "{team}, 혹시 지금 여유 부리는 중이신가요? 😏 분발 좀 해주셔야 할 것 같은데요~",
    "{team}, 남은 LP 보니까 아직 갈 길이 머네요. 설마 벌써 포기하신 건 아니죠? 🙂",
    "{team}, 상대 팀 등 보이시죠? 저희 기다리고 있을게요~ 천천히 오셔도 됩니다 👋",
    "{team}, 지금 점수로는 좀 많이 불안해 보입니다. 분발하세요, 분발! 😤",
]
TAUNT_TIE = "두 팀 막상막하네요. 누가 먼저 무너질지 기대됩니다 🍿"

# ---------- 티어 상수 ----------
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
ROMAN_TO_DIV = {"IV": "4", "III": "3", "II": "2", "I": "1"}
DIV_OFFSET = {"4": 0, "3": 100, "2": 200, "1": 300}

KO_TIER = {
    "아이언": "IRON", "브론즈": "BRONZE", "실버": "SILVER", "골드": "GOLD",
    "플래티넘": "PLATINUM", "플레티넘": "PLATINUM", "에메랄드": "EMERALD",
    "다이아": "DIAMOND", "다이아몬드": "DIAMOND", "마스터": "MASTER",
    "그랜드마스터": "GRANDMASTER", "챌린저": "CHALLENGER",
}

# 긴 이름을 먼저 둬야 '마스터'가 '그랜드마스터'보다 먼저 매칭되지 않는다
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
GOAL_RE = re.compile(r"^\s*(GM|[IBSGPEDMC])\s*(.*?)\s*$", re.IGNORECASE)

TIER_KO = {
    "IRON": "아이언", "BRONZE": "브론즈", "SILVER": "실버", "GOLD": "골드",
    "PLATINUM": "플래티넘", "EMERALD": "에메랄드", "DIAMOND": "다이아몬드",
    "MASTER": "마스터", "GRANDMASTER": "그랜드마스터", "CHALLENGER": "챌린저",
}

def goal_label(goal: str) -> str:
    """'E4 0' -> '에메랄드', 'M 0' -> '마스터'"""
    m = GOAL_RE.match(goal)
    return TIER_KO[SHORT_TO_TIER[m.group(1).upper()]]

# ---------- 점수 계산 ----------
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


# ---------- 페이지 텍스트 파싱 ----------
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


# ---------- 브라우저 조작 ----------
def build_profile_url(riot_id: str) -> str:
    game, tag = riot_id.rsplit("#", 1)
    slug = f"{game.strip()}-{tag.strip()}"
    return f"https://lolchess.gg/profile/kr/{quote(slug)}"


def click_refresh(page) -> None:
    """갱신 버튼이 있으면 눌러서 최신 데이터를 받는다. 없으면 무시."""
    btn = page.get_by_role("button", name=re.compile(r"갱신|새로고침|refresh|update", re.IGNORECASE))
    if btn.count() == 0:
        return
    target = btn.first
    try:
        if not (target.is_visible() and target.is_enabled()):
            return
        target.click()
        page.wait_for_timeout(2000)
    except PlaywrightTimeoutError:
        pass


def wait_for_rank(page, timeout_ms: int = 15000) -> str:
    """랭크 정보가 본문에 나타날 때까지 기다리고 본문 텍스트를 돌려준다."""
    waited = 0
    body = ""
    while waited < timeout_ms:
        body = page.inner_text("body")
        if RANK_RE.search(body):
            return body
        page.wait_for_timeout(1000)
        waited += 1000
    return body


def scrape_player(page, player: dict) -> tuple[tuple | None, str | None]:
    url = build_profile_url(player["riot_id"])
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        click_refresh(page)
        body = wait_for_rank(page)
    except PlaywrightTimeoutError:
        return None, "페이지 로딩 시간 초과"
    except Exception as e:
        return None, f"브라우저 오류: {e}"

    found = find_solo_rank(body)
    if found is None:
        DEBUG_DIR.mkdir(exist_ok=True)
        (DEBUG_DIR / f"{player['name']}.txt").write_text(body, encoding="utf-8")
        return None, "솔로 랭크 파싱 실패 (tft_debug 폴더 확인)"
    return found, None


# ---------- 기록 / 비교 ----------
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


# ---------- 카카오톡 메시지 ----------
def build_kakao_message(rows: list[dict]) -> str:
    out: list[str] = []
    team_sums: dict[str, int] = {}

    for team in ["A팀", "B팀"]:
        out.append(f"[{team}]")
        team_sum = 0
        for r in (r for r in rows if r["팀"] == team):
            if r["오류"]:
                out.append(f"{r['이름']} 조회 실패")
                continue
            chg = 0 if r["변화LP"] is None else r["변화LP"]
            rem = r["남은LP"]
            if rem is not None:
                team_sum += rem
                rem_txt = f"{rem}LP"
            else:
                rem_txt = "-"
            out.append(
                f"{r['이름']} {r['현재랭크']} ({chg:+d}LP), "
                f"{goal_label(r['목표'])}까지 {rem_txt}"
            )
        out.append(f"{team} 남은 합: {team_sum}LP")
        out.append("")
        team_sums[team] = team_sum

    a, b = team_sums["A팀"], team_sums["B팀"]
    if abs(a - b) <= TIE_THRESHOLD:
        out.append(TAUNT_TIE)
    else:
        behind = "A팀" if a > b else "B팀"
        out.append(random.choice(TAUNT_BEHIND).format(team=behind))

    return "\n".join(out).strip()


# ---------- 메인 ----------
def main() -> None:
    history = load_history()
    prev_map = load_yesterday_snapshot(history)
    rows: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for i, player in enumerate(PLAYERS, start=1):
            print(f"[{i}/{len(PLAYERS)}] {player['team']} {player['name']} 조회 중...")
            found, error = scrape_player(page, player)
            if error:
                print(f"   ⚠ {error}")
            else:
                print(f"   ✓ {format_short_rank(*found)}")
            rows.append(build_row(player, found, error, prev_map.get(player["name"])))
            time.sleep(1.5)

        browser.close()

    save_history(history, rows)
    pd.DataFrame(rows).to_csv(LATEST_CSV, index=False, encoding="utf-8-sig")

    msg = build_kakao_message(rows)
    KAKAO_TXT.write_text(msg, encoding="utf-8")

    print("\n--- 카카오톡 복사용 ---")
    print(msg)
    print("---------------------")
    print(f"저장 완료: {KAKAO_TXT}, {LATEST_CSV}")


if __name__ == "__main__":
    main()