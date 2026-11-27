import subprocess
import sys
import time

import pandas as pd
from playwright.sync_api import sync_playwright

from config import HEADLESS, KAKAO_TXT, LATEST_CSV, PLAYERS
from history import build_row, load_history, load_yesterday_snapshot, save_history
from message import build_kakao_message
from report import build_html, publish_to_pages
from scraper import scrape_player
from tiers import format_short_rank

sys.stdout.reconfigure(encoding="utf-8")


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
            rows.append(build_row(player, found, error, prev_map.get(player["name"])))
            time.sleep(1.5)

        browser.close()

    save_history(history, rows)
    pd.DataFrame(rows).to_csv(LATEST_CSV, index=False, encoding="utf-8-sig")

    msg = build_kakao_message(rows)
    KAKAO_TXT.write_text(msg, encoding="utf-8")

    build_html(rows)
    try:
        publish_to_pages()
    except subprocess.CalledProcessError as e:
        print(f"웹페이지 업로드 실패: {e}")

    print("\n--- 카카오톡 복사용 ---")
    print(msg)
    print("---------------------")
    print(f"저장 완료: {KAKAO_TXT}, {LATEST_CSV}")


if __name__ == "__main__":
    main()