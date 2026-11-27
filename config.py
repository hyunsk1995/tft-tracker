from pathlib import Path

HEADLESS = False
HISTORY_FILE = Path("tft_history.json")
LATEST_CSV = Path("tft_4v4_latest.csv")
KAKAO_TXT = Path("tft_kakao_summary.txt")
DEBUG_DIR = Path("tft_debug")
PAGES_DIR = Path("docs")

TIE_THRESHOLD = 200   # 두 팀 남은 LP 합 차이가 이 값 이하면 무승부 멘트
UNRANKED_POINTS = 0   # 언랭크 = 아이언 4 0LP와 동일

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

ACHIEVE_FILE = Path("tft_achievements.json")   # 달성 순서 기록
POINTS = [8, 7, 6, 5, 4, 3, 2, 1]              # 1등~8등 점수