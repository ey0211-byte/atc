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
# 2. 세션 상태 초기화 (10개 활주로 & 이착륙 시스템)
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
            category = random.choice(["ARR", "DEP"])  # 착륙 vs 이륙
            ac_type = random.choice(
                ["Heavy(대형)", "Medium(중형)", "Light(소형)"]
            )

            if category == "ARR":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",  # 도착(착륙)
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
                        "category": "DEP",  # 출발(이륙)
                        "type": ac_type,
                        "fuel": 100,
                        "distance": 0,
                        "delay": 0,  # 지연 턴 수
                        "status": "이륙 요청 중",
                        "assigned_runway": None,
                    }
                )
            break


def init_game():
    """게임 초기화 (시작 시 이착륙 비행기 12대 동시 스폰)"""
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


def approve_action(callsign, target_runway):
    """착륙 또는 이륙 허가 동시 처리"""
    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    if st.session_state.runways_busy[target_runway] > 0:
        st.warning(f"🚫 {target_runway} 활주로는 사용 중입니다!")
        return

    # 후류 와류 시간 체크
    last_type = st.session_state.last_landed_type[target_runway]
    occupancy_time = 2

    if last_type == "Heavy(대형)" and plane["type"] in [
        "Medium(중형)",
        "Light(소형)",
    ]:
        occupancy_time += 1
        st.toast(
            f"⚠️ [{target_runway}] 선행 대형기 영향으로 활주로 점유시간 +1턴",
            icon="⚠️",
        )

    plane["assigned_runway"] = target_runway
    st.session_state.runways_busy[target_runway] = occupancy_time
    st.session_state.last_landed_type[target_runway] = plane["type"]

    if plane["category"] == "ARR":
        plane["status"] = "착륙 접근 중"
        if plane["fuel"] <= 25:
            st.session_state.score += 30
            log_msg = f"🚨 [비상 착륙 승인] {callsign} ➔ {target_runway} (+30점)"
        else:
            st.session_state.score += 10
            log_msg = f"🛬 [착륙 허가] {callsign} ➔ {target_runway} (+10점)"
    else:
        plane["status"] = "이륙 가속 중"
        st.session_state.score += 15
        log_msg = f"🛫 [이륙 허가] {callsign} ➔ {target_runway} (+15점)"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="📡")


def reject_action(callsign):
    """착륙 거절(Holding) 또는 이륙 지연(Gate Wait)"""
    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    if plane["category"] == "ARR":
        plane["status"] = "상공 대기 중(Holding)"
        log_msg = f"🛑 [착륙 거절] {callsign} 상공 대기 궤도 진입"
    else:
        plane["status"] = "지상 대기 중"
        log_msg = f"🛑 [이륙 지연] {callsign} 게이트/유도로 일시 대기"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🛑")


def force_clear_runway(runway_name):
    """활주로 강제 개방"""
    st.session_state.runways_busy[runway_name] = 0
    log_msg = f"🧹 [강제 비우기] {runway_name} 활주로가 비상 개방되었습니다."
    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🧹")


def next_turn():
    """시간 진행 (연료 소모 및 지연 시간 누적)"""
    st.session_state.turn += 1

    # 활주로 타이머 차감
    for r in st.session_state.runways_busy:
        if st.session_state.runways_busy[r] > 0:
            st.session_state.runways_busy[r] -= 1

    remaining_planes = []
    for p in st.session_state.planes:
        # 1. 착륙 진행 중
        if p["status"] == "착륙 접근 중":
            p["distance"] -= 15
            if p["distance"] <= 0:
                st.session_state.landed_count += 1
                st.session_state.logs.append(
                    f"🛬 [{p['callsign']}] {p['assigned_runway']} 안전 착륙 완료!"
                )
                continue

        # 2. 이륙 진행 중
        elif p["status"] == "이륙 가속 중":
            st.session_state.tookoff_count += 1
            st.session_state.logs.append(
                f"🛫 [{p['callsign']}] {p['assigned_runway']} 성공적 이륙 및 공역 이탈!"
            )
            continue

        # 3. 착륙 대기 비행기 (연료 차감)
        elif p["category"] == "ARR":
            p["fuel"] -= random.randint(10, 18)
            p["distance"] -= random.randint(1, 3)

            if p["fuel"] <= 0:
                st.session_state.score -= 50
                st.session_state.logs.append(
                    f"💥 [연료 고갈] {p['callsign']} 착륙 실패 및 회항! (-50점)"
                )
                continue

        # 4. 이륙 대기 비행기 (지연 시간 누적)
        elif p["category"] == "DEP":
            p["delay"] += 1
            if p["delay"] >= 4:
                st.session_state.score -= 10
                st.session_state.logs.append(
                    f"⏰ [출발 지연 페널티] {p['callsign']} 4턴 이상 지연 중! (-10점)"
                )

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # 비행기 신규 유입 (최대 18대 유지를 목표)
    while len(st.session_state.planes) < 16 and random.random() < 0.8:
        spawn_plane()


# ==========================================
# 4. 메인 화면 레이아웃 (이착륙 이원화)
# ==========================================
st.title("✈️ ATC 대규모 이착륙 통합 관제 시뮬레이터")

if not st.session_state.game_started:
    st.warning(
        "⚠️ 착륙하려는 비행기의 연료와 이륙하려는 비행기의 지연 시간을 동시에 관제해야 합니다!"
    )
    if st.button(
        "🚀 비상 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 대시보드 상단 요약
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📊 현재 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("⏳ 경과 시간", f"{st.session_state.turn}턴")
    m5.metric("✈️ 총 관리 항공기", f"{len(st.session_state.planes)}대")

    st.divider()

    # 상단 버튼 제어 바
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        if not st.session_state.emg_runway_open:
            if st.button(
                "🚨 [비상] 01E 비상 활주로 추가 개설",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.emg_runway_open = True
                st.session_state.logs.append(
                    "🚨 [비상 활주로] EMG-01 활주로가 개설되었습니다!"
                )
                st.rerun()
        else:
            st.success("🚨 비상 활주로(EMG-01) 가동 중")

    with c2:
        if st.button(
            "⏭️ 다음 Turn 진행 (시간 흐름)",
            type="primary",
            use_container_width=True,
        ):
            next_turn()
            st.rerun()
    with c3:
        if st.button("🔄 리셋", use_container_width=True):
            init_game()
            st.rerun()

    st.write("")

    # 메인 구역 (좌측: 이착륙 2열 관제판 / 우측: 활주로 10개)
    col_left, col_right = st.columns([2.3, 1])

    available_runways = RUNWAY_LIST.copy()
    if st.session_state.emg_runway_open:
        available_runways.append("EMG-01")

    # ----------------------------------------------------
    # [좌측] 🛬 착륙 비행기 & 🛫 이륙 비행기 2열 분할 관제
    # ----------------------------------------------------
    with col_left:
        arr_planes = [
            p for p in st.session_state.planes if p["category"] == "ARR"
        ]
        dep_planes = [
            p for p in st.session_state.planes if p["category"] == "DEP"
        ]

        sub_col1, sub_col2 = st.columns(2)

        # 🛬 1열: 착륙 대기 비행기 (ARR)
        with sub_col1:
            st.subheader(f"🛬 착륙 요청 ({len(arr_planes)}대)")

            for p in arr_planes:
                if p["status"] == "착륙 요청 중":
                    badge = '<span class="badge-danger">📡 착륙 요청</span>'
                elif p["status"] == "상공 대기 중(Holding)":
                    badge = '<span class="badge-arr">🛑 상공 대기</span>'
                else:
                    badge = '<span class="badge-success">🛬 접근 중</span>'

                st.markdown(
                    f"""
                    <div class="arr-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="plane-title-arr">✈️ {p['callsign']} <small>({p['type']})</small></span>
                            {badge}
                        </div>
                        <div class="plane-sub">연료: <b>{p['fuel']}%</b> | 거리: {p['distance']}NM</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.progress(
                    max(0, min(100, p["fuel"])) / 100,
                    text=f"연료: {p['fuel']}%",
                )

                if p["status"] in ["착륙 요청 중", "상공 대기 중(Holding)"]:
                    b1, b2, b3 = st.columns([1.8, 1, 1])
                    with b1:
                        sel_rwy = st.selectbox(
                            "활주로",
                            available_runways,
                            key=f"sel_arr_{p['callsign']}",
                            label_visibility="collapsed",
                        )
                    with b2:
                        if st.button(
                            "✅ 착륙",
                            key=f"app_{
