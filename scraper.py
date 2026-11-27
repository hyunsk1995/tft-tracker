import re
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import DEBUG_DIR
from parser import RANK_RE, find_solo_rank


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