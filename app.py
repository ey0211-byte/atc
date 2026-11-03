import random
import time
import pandas as pd
import streamlit as st

# ==========================================
# 1. 고밀도 컴팩트 UI 및 고대비 스타일
# ==========================================
st.set_page_config(
    page_title="ATC 실시간 대규모 관제 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #070a13 !important;
        color: #e2e8f0 !important;
    }
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

    .runway-card {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 5px;
        text-align: center;
        font-size: 11px;
    }
    .stProgress > div > div > div > div { height: 5px !important; }

    .badge-arr { background-color: #2563eb; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-dep { background-color: #d97706; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-danger { background-color: #dc2626; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 타이머 초기화
# ==========================================
RUNWAY_LIST = [f"RWY {i:02d}" for i in range(1, 11)]

if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "game_over_reason" not in st.session_state:
    st.session_state.game_over_reason = ""
if "planes" not in st.session_state:
    st.session_state.planes = []
if "score" not in st.session_state:
    st.session_state.score = 200
if "landed_count" not in st.session_state:
    st.session_state.landed_count = 0
if "tookoff_count" not in st.session_state:
    st.session_state.tookoff_count = 0
if "emg_runway_open" not in st.session_state:
    st.session_state.emg_runway_open = False
if "runways_busy_until" not in st.session_state:
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
if "last_landed_type" not in st.session_state:
    st.session_state.last_landed_type = {r: None for r in RUNWAY_LIST}
    st.session_state.last_landed_type["EMG-01"] = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "last_tick_time" not in st.session_state:
    st.session_state.last_tick_time = time.time()
if "last_spawn_time" not in st.session_state:
    st.session_state.last_spawn_time = time.time()


# ==========================================
# 3. 비행기 생성 및 실시간 엔진 로직
# ==========================================
def spawn_plane():
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
                        "fuel": float(random.randint(35, 80)),
                        "distance": float(random.randint(15, 35)),
                        "delay": 0.0,
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
                        "fuel": 100.0,
                        "distance": 0.0,
                        "delay": 0.0,
                        "takeoff_timer": 5.0,
                        "status": "이륙 요청 중",
                        "assigned_runway": None,
                    }
                )
            break


def init_game():
    st.session_state.game_started = True
    st.session_state.game_over = False
    st.session_state.game_over_reason = ""
    st.session_state.planes = []
    st.session_state.score = 200
    st.session_state.landed_count = 0
    st.session_state.tookoff_count = 0
    st.session_state.emg_runway_open = False
    now = time.time()
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
    st.session_state.last_landed_type = {r: None for r in RUNWAY_LIST}
    st.session_state.last_landed_type["EMG-01"] = None
    st.session_state.last_tick_time = now
    st.session_state.last_spawn_time = now
    st.session_state.logs = [
        "🚨 [관제 업무 개시] 실시간 적정 속도(약 1.6초당 1% 소모)로 기름이 차감됩니다."
    ]

    for _ in range(10):
        spawn_plane()


def update_realtime_engine():
    """실시간 기름 차감 엔진 (속도 완화: 초당 0.6% 차감)"""
    if not st.session_state.game_started or st.session_state.game_over:
        return

    now = time.time()
    dt = now - st.session_state.last_tick_time
    st.session_state.last_tick_time = now

    remaining_planes = []
    for p in st.session_state.planes:
        cat = p.get("category", "ARR")
        status = p.get("status", "")

        # 1. 착륙 접근 중
        if status == "착륙 접근 중":
            p["distance"] -= 5.0 * dt  # 초당 5 NM 이동
            if p["distance"] <= 0:
                st.session_state.landed_count += 1
                st.session_state.score += 20
                st.session_state.logs.append(
                    f"🛬 [{p['callsign']}] {p.get('assigned_runway')} 안전 터치다운 완료!"
                )
                continue

        # 2. 이륙 가속 중
        elif status == "이륙 가속 중":
            p["takeoff_timer"] -= dt
            if p["takeoff_timer"] <= 0:
