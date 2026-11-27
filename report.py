import html
import random
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from config import PAGES_DIR, POINTS, TAUNT_BEHIND, TAUNT_TIE, TIE_THRESHOLD
from tiers import APEX, GOAL_RE, SHORT_TO_TIER

TEAMS = ["A팀", "B팀"]

ICON_SRC = Path("tier_icons")
ICON_DST = PAGES_DIR / "tier_icons"

CSS = """
:root {
  --bg: #0f1115; --card: #181b22; --line: #2a2f3a;
  --text: #e8eaf0; --muted: #8b93a7;
  --up: #3ddc97; --down: #ff6b6b; --done: #ffd166;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f5f6fa; --card: #ffffff; --line: #e2e5ee;
    --text: #1d2230; --muted: #6b7280;
    --up: #0f9d58; --down: #d93025; --done: #e0a100;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
header h1 { margin: 0 0 4px; font-size: 1.6rem; }
header p { margin: 0; color: var(--muted); font-size: .9rem; }

.layout { display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start; margin-top: 20px; }
.side { position: sticky; top: 16px; }

.summary {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px;
  margin-bottom: 16px; align-items: stretch;
}
.team-box {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
}
.team-box h2 { margin: 0 0 6px; font-size: 1rem; }
.team-box .num { font-size: 1.6rem; font-weight: 700; }
.team-box .sub { color: var(--muted); font-size: .85rem; margin-top: 2px; }
.vs { align-self: center; color: var(--muted); font-weight: 700; }

.verdict {
  text-align: center; background: var(--card); border: 1px dashed var(--line);
  border-radius: 12px; padding: 12px 16px; margin-bottom: 24px;
}

section.team, section.lb-box {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 8px 0 4px; margin-bottom: 20px; overflow: hidden;
}
section.team h2, section.lb-box h2 { margin: 8px 16px 4px; font-size: 1.05rem; }

table { width: 100%; border-collapse: collapse; font-size: .92rem; }
th, td {
  padding: 10px 12px; text-align: center; white-space: nowrap;
  border-top: 1px solid var(--line);
}
th { color: var(--muted); font-weight: 600; font-size: .8rem; }
td.name { text-align: left; font-weight: 600; }
.nick { color: var(--muted); font-size: .8rem; font-weight: 400; }

table.lb { font-size: .84rem; }
table.lb th, table.lb td { padding: 8px 6px; white-space: normal; }
table.lb tr.pending td { color: var(--muted); }

.pts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.pts .team-box { padding: 10px 12px; }
.pts .team-box .num { font-size: 1.3rem; }

.icon { width: 22px; height: 22px; vertical-align: middle; margin-right: 4px; }
.up { color: var(--up); font-weight: 600; }
.down { color: var(--down); font-weight: 600; }
.flat { color: var(--muted); }
.done { color: var(--done); font-weight: 700; }
.err td { color: var(--muted); font-style: italic; }

footer { color: var(--muted); font-size: .8rem; text-align: center; margin-top: 24px; }

@media (max-width: 820px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; }
  .wrap { max-width: 640px; }
  th, td { padding: 8px 6px; font-size: .85rem; }
  .icon { width: 18px; height: 18px; }
}
"""


def esc(s) -> str:
    return html.escape(str(s))


def _sync_icons() -> dict[str, str]:
    """tier_icons 폴더의 webp를 docs/tier_icons로 복사하고, 티어 키 -> 웹 경로 맵을 돌려준다."""
    icons: dict[str, str] = {}
    if not ICON_SRC.exists():
        print(f"⚠ 아이콘 폴더가 없습니다: {ICON_SRC}")
        return icons
    ICON_DST.mkdir(parents=True, exist_ok=True)
    for f in ICON_SRC.iterdir():
        if f.is_file() and f.suffix.lower() == ".webp":
            shutil.copy2(f, ICON_DST / f.name)
            icons[f.stem.lower()] = f"tier_icons/{f.name}"
    return icons


def _icon_html(key: str | None, icons: dict[str, str]) -> str:
    src = icons.get(key) if key else None
    if not src:
        return ""
    return f'<img class="icon" src="{esc(src)}" alt="{esc(key)}">'


def _rank_key(short_rank: str) -> str | None:
    """'M 120' -> 'master', 'UR 0' -> 'unranked', '조회실패' -> None"""
    m = re.match(r"([A-Z]+)", short_rank)
    if not m:
        return None
    code = m.group(1)
    if code == "UR":
        return "unranked"
    tier = SHORT_TO_TIER.get(code)
    return tier.lower() if tier else None


def _goal_key(goal: str) -> str:
    """'E4 0' -> 'emerald'"""
    m = GOAL_RE.match(goal)
    return SHORT_TO_TIER[m.group(1).upper()].lower()


def _fmt(tier: str, div: str | None, lp: str) -> str:
    """('EMERALD', '4', '80') -> 'Emerald 4 80 LP', ('MASTER', None, '0') -> 'Master 0 LP'"""
    name = tier.title()
    if tier in APEX or not div:
        return f"{name} {lp} LP"
    return f"{name} {div} {lp} LP"


def _rank_text(short_rank: str) -> str:
    """'E4 80' -> 'Emerald 4 80 LP', 'UR 0' -> 'Unranked'"""
    m = re.match(r"^(UR|[A-Z]+)(\d)?\s+(\d+)$", short_rank)
    if not m:
        return short_rank
    code, div, lp = m.groups()
    if code == "UR":
        return "Unranked"
    tier = SHORT_TO_TIER.get(code)
    if tier is None:
        return short_rank
    return _fmt(tier, div, lp)


def _goal_text(goal: str) -> str:
    """'E4 0' -> 'Emerald 4 0 LP', 'M 0' -> 'Master 0 LP'"""
    m = GOAL_RE.match(goal)
    tier = SHORT_TO_TIER[m.group(1).upper()]
    nums = re.findall(r"\d+", m.group(2))
    if tier in APEX:
        return _fmt(tier, None, nums[0] if nums else "0")
    div = nums[0] if nums else None
    lp = nums[1] if len(nums) > 1 else "0"
    return _fmt(tier, div, lp)


def _team_stats(rows: list[dict], team: str) -> dict:
    team_rows = [r for r in rows if r["팀"] == team]
    return {
        "rows": team_rows,
        "rem": sum(r["남은LP"] for r in team_rows if r["남은LP"] is not None),
        "chg": sum(0 if r["변화LP"] is None else r["변화LP"] for r in team_rows),
        "done": sum(1 for r in team_rows if r["남은LP"] == 0),
        "total": len(team_rows),
    }


def _change_html(chg: int) -> str:
    cls = "up" if chg > 0 else "down" if chg < 0 else "flat"
    return f'<span class="{cls}">{chg:+d} LP</span>'


def _player_row(r: dict, icons: dict[str, str]) -> str:
    name_cell = f'{esc(r["이름"])}<br><span class="nick">{esc(r["닉네임"])}</span>'

    if r["오류"]:
        return (
            f'<tr class="err"><td class="name">{name_cell}</td>'
            f'<td colspan="4">조회 실패 · {esc(r["오류"])}</td></tr>'
        )

    chg = 0 if r["변화LP"] is None else r["변화LP"]
    rem = r["남은LP"]
    if rem == 0:
        rem_html = '<span class="done">달성 🏆</span>'
    elif rem is None:
        rem_html = "-"
    else:
        rem_html = f"{rem} LP"

    rank_cell = _icon_html(_rank_key(r["현재랭크"]), icons) + esc(_rank_text(r["현재랭크"]))
    goal_cell = _icon_html(_goal_key(r["목표"]), icons) + esc(_goal_text(r["목표"]))

    return (
        f'<tr><td class="name">{name_cell}</td>'
        f'<td>{rank_cell}</td>'
        f'<td>{_change_html(chg)}</td>'
        f'<td>{goal_cell}</td>'
        f'<td>{rem_html}</td></tr>'
    )


def _team_section(team: str, s: dict, icons: dict[str, str]) -> str:
    body = "".join(_player_row(r, icons) for r in s["rows"])
    title = f"{esc(team)} · 남은 합 {s['rem']} LP"
    return (
        f'<section class="team"><h2>{title}</h2>'
        f'<table><tr><th>이름</th><th>랭크</th><th>변화</th><th>목표</th>'
        f'<th>남은 LP</th></tr>{body}</table></section>'
    )


def _team_box(team: str, s: dict) -> str:
    sub = f"변화 {s['chg']:+d} LP · 달성 {s['done']}/{s['total']}"
    return (
        f'<div class="team-box"><h2>{esc(team)}</h2>'
        f'<div class="num">{s["rem"]} LP</div>'
        f'<div class="sub">남은 합 · {sub}</div></div>'
    )


def _verdict(a_rem: int, b_rem: int) -> str:
    if abs(a_rem - b_rem) <= TIE_THRESHOLD:
        return esc(TAUNT_TIE)
    behind = "A팀" if a_rem > b_rem else "B팀"
    return esc(random.choice(TAUNT_BEHIND).format(team=behind))


def _lb_row(rank: str, r: dict, when: str, pts: int) -> str:
    cls = ' class="pending"' if when == "미달성" else ""
    return (
        f'<tr{cls}><td>{rank}</td>'
        f'<td class="name">{esc(r["이름"])}<br><span class="nick">{esc(r["팀"])}</span></td>'
        f'<td>{esc(when)}</td><td><b>{pts}</b></td></tr>'
    )


def _leaderboard(rows: list[dict], ach: dict[str, str]) -> str:
    # 달성 시각 오름차순 (같은 시각이면 rows 순서 유지)
    achieved = sorted((r for r in rows if r["이름"] in ach), key=lambda r: ach[r["이름"]])
    pending = [r for r in rows if r["이름"] not in ach]

    points = {t: 0 for t in TEAMS}
    body: list[str] = []
    for i, r in enumerate(achieved, start=1):
        pts = POINTS[i - 1] if i <= len(POINTS) else 0
        points[r["팀"]] = points.get(r["팀"], 0) + pts
        body.append(_lb_row(str(i), r, ach[r["이름"]], pts))
    for r in pending:
        body.append(_lb_row("-", r, "미달성", 0))

    body_html = "".join(body)
    table = (
        f'<table class="lb"><tr><th>순위</th><th>이름</th><th>달성일자</th><th>점수</th></tr>'
        f'{body_html}</table>'
    )
    pts_html = "".join(
        f'<div class="team-box"><h2>{esc(t)}</h2><div class="num">{points[t]}점</div></div>'
        for t in TEAMS
    )
    return (
        f'<section class="lb-box"><h2>달성 순서</h2>{table}</section>'
        f'<div class="pts">{pts_html}</div>'
    )


def build_html(rows: list[dict], achievements: dict[str, str]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    icons = _sync_icons()
    stats = {t: _team_stats(rows, t) for t in TEAMS}
    a, b = stats["A팀"], stats["B팀"]

    summary = (
        f'<div class="summary">{_team_box("A팀", a)}'
        f'<div class="vs">VS</div>{_team_box("B팀", b)}</div>'
    )
    verdict = f'<div class="verdict">{_verdict(a["rem"], b["rem"])}</div>'
    sections = "".join(_team_section(t, stats[t], icons) for t in TEAMS)
    main_html = f"{summary}{verdict}{sections}"
    side_html = _leaderboard(rows, achievements)

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TFT 4대4 현황</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
<h1>TFT 4대4 현황</h1>
<p>마지막 갱신 {now} · 변화는 어제 기록 기준</p>
</header>
<div class="layout">
<div class="main">{main_html}</div>
<aside class="side">{side_html}</aside>
</div>
<footer>데이터 출처: lolchess.gg · 자동 생성</footer>
</div>
</body>
</html>"""

    PAGES_DIR.mkdir(exist_ok=True)
    (PAGES_DIR / "index.html").write_text(page, encoding="utf-8")


def publish_to_pages() -> None:
    subprocess.run(["git", "add", str(PAGES_DIR)], check=True)
    # returncode 0 = 스테이징된 변경 없음
    no_change = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0
    if no_change:
        print("웹페이지 변경 없음, push 생략")
        return
    subprocess.run(["git", "commit", "-m", f"update {datetime.now():%Y-%m-%d %H:%M}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("웹페이지 업로드 완료")