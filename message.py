import random

from config import TAUNT_BEHIND, TAUNT_TIE, TIE_THRESHOLD
from tiers import goal_label


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