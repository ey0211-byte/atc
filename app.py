import random
import pandas as pd
import streamlit as st

# ==========================================
# 1. 고밀도 컴팩트 UI 및 이착륙 구분 스타일
# ==========================================
st.set_page_config(
    page_title="ATC 대규모 이착륙 관제 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* 전체 배경 */
    .stApp {
        background-color: #070a13 !important;
        color: #e2e8f0 !important;
    }

    /* 초고밀도 컴팩트 버튼 */
    div.stButton > button {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #475569 !important;
        font-weight: bold !important;
        font-size: 11px !important;
        padding: 2px 4px !important;
        min-height: 25px !important;
        border-radius: 4px !important;
    }
    div.stButton > button:hover {
        background-color: #334155 !important;
        color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }

    div.stButton > button[kind="primary"] {
        background-color: #dc2626 !important;
        border-color: #ef4444 !important;
    }

    /* 카드 스타일 (착륙: 푸른색 계열 / 이륙: 주황색 계열) */
    .arr-card {
        background-color: #0c192e;
        border: 1px solid #1d4ed8;
        border-radius: 6px;
        padding: 7px;
        margin-bottom: 5px;
    }
    .dep-card {
        background-color: #26170c;
        border: 1px solid #d97706;
        border-radius: 6px;
        padding: 7px;
        margin-bottom: 5px;
    }
    .plane-title-arr { font-size: 12px !important; font-weight: bold; color: #60a5fa; }
    .plane-title-dep { font-size: 12px !important; font-weight: bold; color: #fbbf24; }
    .plane-sub { font-size: 11px !important; color: #cbd5e1; }

    /* 활주로 미니 카드 */
    .runway-card {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 5px;
        text-align: center;
        font-size: 11px;
    }

    /* 프로그레스 바 높이 축소 */
    .stProgress > div > div > div > div { height: 5px !important; }

    /* 배지 고밀도화 */
    .badge-arr { background-color: #2563eb; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-dep { background-color: #d97706; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-danger { background-color: #dc2626; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 초기화 & 구버전 데이터 보정 로직
# ==========================================
RUNWAY_LIST = [f"RWY {i:02d}" for i in range(1, 11)]

if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "planes" not in st.session_state:
    st.session_state.planes = []
if "score" not in st.session_state:
    st.session_state.score = 200
if "turn" not in st.session_state:
    st.session_state.turn = 1
if "landed_count" not in st.session_state:
    st.session_state.landed_count = 0
if "tookoff_count" not in st.session_state:
    st.session_state.tookoff_count = 0
if "emg_runway_open" not in st.session_state:
    st.session_state.emg_runway_open = False
if "runways_busy" not in st.session_state:
    st.session_state.runways_busy = {r: 0 for r in RUNWAY_LIST}
    st.session_state.runways_busy["EMG-01"] = 0
if "last_landed_type" not in st.session_state:
    st.session_state.last_landed_type = {r: None for r in RUNWAY_LIST}
    st.session_state.last_landed_type["EMG-01"] = None
if "logs" not in st.session_state:
    st.session_state.logs = []

# 🔴 [KeyError 방지] 구버전 세션 데이터에 신규 키가 없으면 자동으로 보정
for p in st.session_state.planes:
    if "category" not in p:
        p["category"] = "ARR"
    if "delay" not in p:
        p["delay"] = 0


# ==========================================
# 3. 비행기 생성 및 로직 함수
# ==========================================
def spawn_plane():
    """신규 이착륙 항공기 랜덤 생성"""
    prefixes = [
        "KAL",
        "AAR",
        "JNA",
        "TWB",
        "ABL",
        "ESR",
        "JJA",
        "CPA",
        "ANA",
        "DAL",
        "UAL",
        "BAW",
    ]
    existing_cs = [p["callsign"] for p in st.session_state.planes]

    for _ in range(30):
        cs = f"{random.choice(prefixes)}{random.randint(100, 999)}"
        if cs not in existing_cs:
            category = random.choice(["ARR", "DEP"])
            ac_type = random.choice(
                ["Heavy(대형)", "Medium(중형)", "Light(소형)"]
            )

            if category == "ARR":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "type": ac_type,
                        "fuel": random.randint(18, 65),
                        "distance": random.randint(10, 30),
                        "delay": 0,
                        "status": "착륙 요청 중",
                        "assigned_runway": None,
                    }
                )
            else:
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "DEP",
                        "type": ac_type,
                        "fuel": 100,
                        "distance": 0,
                        "delay": 0,
                        "status": "이륙 요청 중",
                        "assigned_runway": None,
                    }
                )
            break


def init_game():
    """게임 초기화"""
    st.session_state.game_started = True
    st.session_state.planes = []
    st.session_state.score = 200
    st.session_state.turn = 1
    st.session_state.landed_count = 0
    st.session_state.tookoff_count = 0
    st.session_state.emg_runway_open = False
    st.session_state.runways_busy = {r: 0 for r in RUNWAY_LIST}
    st.session_state.runways_busy["EMG-01"] = 0
    st.session_state.last_landed_type = {r: None for r in RUNWAY_LIST}
    st.session_state.last_landed_type["EMG-01"] = None
    st.session_state.logs = [
        "🚨 [관제 업무 개시] 착륙 및 이륙 대규모 종합 관제가 시작되었습니다."
    ]

    for _ in range(12):
        spawn_plane()


def approve_action(callsign,
