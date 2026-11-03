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
# 2. 세션 상태 및 실시간 타이머 초기화
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
                        "fuel": float(random.randint(25, 70)),  # 실시간 감소용 float
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
        "🚨 [실시간 관제 개시] 초 단위 기름 감소 엔진 및 임무실패 로직이 적용되었습니다."
    ]

    for _ in range(10):
        spawn_plane()


def update_realtime_engine():
    """실시간 기름 차감 및 게임 오버 판단 핵심 엔진"""
    if not st.session_state.game_started or st.session_state.game_over:
        return

    now = time.time()
    dt = now - st.session_state.last_tick_time
    st.session_state.last_tick_time = now

    remaining_planes = []
    for p in st.session_state.planes:
        cat = p.get("category", "ARR")
        status = p.get("status", "")

        # 1. 착륙 진행 중인 경우
        if status == "착륙 접근 중":
            p["distance"] -= 6.0 * dt  # 초당 6 NM 이동
            if p["distance"] <= 0:
                st.session_state.landed_count += 1
                st.session_state.score += 20
                st.session_state.logs.append(
                    f"🛬 [{p['callsign']}] {p.get('assigned_runway')} 안전 터치다운 완료!"
                )
                continue

        # 2. 이륙 진행 중인 경우
        elif status == "이륙 가속 중":
            p["takeoff_timer"] -= dt
            if p["takeoff_timer"] <= 0:
                st.session_state.tookoff_count += 1
                st.session_state.score += 15
                st.session_state.logs.append(
                    f"🛫 [{p['callsign']}] {p.get('assigned_runway')} 성공적으로 이륙 완료!"
                )
                continue

        # 3. 상공 착륙 대기 비행기 (실시간 기름 감소)
        elif cat == "ARR":
            # 초당 1.2% ~ 2.0% 씩 기름 실시간 감축
            p["fuel"] -= 1.5 * dt

            # 🔴 [임무 실패 조건] 단 1대라도 기름 0% 도달 시 게임 오버
            if p["fuel"] <= 0:
                p["fuel"] = 0.0
                st.session_state.game_over = True
                st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                st.session_state.logs.append(st.session_state.game_over_reason)
                return

        # 4. 지상 이륙 대기 비행기 (지연 시간 증가)
        elif cat == "DEP":
            p["delay"] += dt

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # 4초마다 신규 항공기 스폰 (최대 16대 유지)
    if (
        now - st.session_state.last_spawn_time > 4.0
        and len(st.session_state.planes) < 16
    ):
        spawn_plane()
        st.session_state.last_spawn_time = now


def approve_action(callsign, target_runway):
    now = time.time()
    if st.session_state.runways_busy_until[target_runway] > now:
        st.warning(f"🚫 {target_runway} 활주로는 현재 사용 중입니다!")
        return

    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    last_type = st.session_state.last_landed_type[target_runway]
    occupancy_seconds = 8.0  # 기본 8초 점유

    if last_type == "Heavy(대형)" and plane.get("type") in [
        "Medium(중형)",
        "Light(소형)",
    ]:
        occupancy_seconds += 4.0  # 후류 와류 대기 4초 추가
        st.toast(
            f"⚠️ [{target_runway}] 선행 대형기로 인해 점유시간 +4초", icon="⚠️"
        )

    st.session_state.runways_busy_until[target_runway] = now + occupancy_seconds
    st.session_state.last_landed_type[target_runway] = plane.get("type")
    plane["assigned_runway"] = target_runway

    if plane.get("category") == "ARR":
        plane["status"] = "착륙 접근 중"
        log_msg = f"🛬 [착륙 허가] {callsign} ➔ {target_runway}"
    else:
        plane["status"] = "이륙 가속 중"
        plane["takeoff_timer"] = 5.0
        log_msg = f"🛫 [이륙 허가] {callsign} ➔ {target_runway}"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="📡")


def reject_action(callsign):
    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    if plane.get("category") == "ARR":
        plane["status"] = "상공 대기 중"
        log_msg = f"🛑 [착륙 대기] {callsign} 상공 궤도 선회 지시"
    else:
        plane["status"] = "지상 대기 중"
        log_msg = f"🛑 [이륙 지연] {callsign} 유도로 대기 지시"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🛑")


def force_clear_runway(runway_name):
    st.session_state.runways_busy_until[runway_name] = 0.0
    log_msg = f"🧹 [강제 비우기] {runway_name} 활주로가 비상 개방되었습니다."
    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🧹")


# ==========================================
# 4. 실시간 엔진 업데이트 수행
# ==========================================
update_realtime_engine()


# ==========================================
# 5. 화면 구성 (GAME OVER vs 관제 화면)
# ==========================================
st.title("⚡ ATC 실시간 대규모 이착륙 통합 관제 시뮬레이터")

# 🔴 [임무 실패 / GAME OVER 화면]
if st.session_state.game_over:
    st.error("💥 [GAME OVER / 임무 실패]")
    st.subheader(st.session_state.game_over_reason)
    st.write(
        f"**최종 관제 성과:** 착륙 성공 {st.session_state.landed_count}대 | 이륙 성공 {st.session_state.tookoff_count}대 | 점수: {st.session_state.score}점"
    )

    if st.button(
        "🔄 관제 업무 다시 도전하기", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

    st.divider()
    st.subheader("📜 최종 관제 교신 로그")
    for log in reversed(st.session_state.logs[-10:]):
        st.caption(log)

elif not st.session_state.game_started:
    st.warning(
        "⚠️ 실시간으로 비행기의 기름이 감소합니다! 연료가 0%가 되면 즉시 임무 실패입니다."
    )
    if st.button(
        "🚀 비상 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 관제탑 상단 요약
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 현재 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("✈️ 상공/지상 비행기", f"{len(st.session_state.planes)}대")

    st.divider()

    c1, c2 = st.columns([2, 1])
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
        if st.button("🔄 리셋", use_container_width=True):
            init_game()
            st.rerun()

    st.write("")

    col_left, col_right = st.columns([2.3, 1])

    available_runways = RUNWAY_LIST.copy()
    if st.session_state.emg_runway_open:
        available_runways.append("EMG-01")

    # ----------------------------------------------------
    # [좌측] 🛬 착륙 비행기 & 🛫 이륙 비행기 실시간 현황판
    # ----------------------------------------------------
    with col_left:
        arr_planes = [
            p for p in st.session_state.planes if p.get("category") == "ARR"
        ]
        dep_planes = [
            p for p in st.session_state.planes if p.get("category") == "DEP"
        ]

        sub_col1, sub_col2 = st.columns(2)

        # 🛬 착륙 요청 비행기 (연료 실시간 표시)
        with sub_col1:
            st.subheader(f"🛬 착륙 관제 ({len(arr_planes)}대)")

            for p in arr_planes:
                status = p.get("status", "착륙 요청 중")
                fuel_val = max(0.0, p.get("fuel", 0.0))

                if fuel_val <= 20.0:
                    badge = '<span class="badge-danger">🚨 연료 위급</span>'
                elif status == "착륙 접근 중":
                    badge = '<span class="badge-success">🛬 접근 중</span>'
                else:
                    badge = '<span class="badge-arr">📡 착륙 요청</span>'

                st.markdown(
                    f"""
                    <div class="arr-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="plane-title-arr">✈️ {p['callsign']} <small>({p.get('type')})</small></span>
                            {badge}
                        </div>
                        <div class="plane-sub">연료: <b style="color:#ef4444;">{fuel_val:.1f}%</b> | 거리: {max(0.0, p.get('distance',0)):.1f}NM</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.progress(
                    fuel_val / 100.0, text=f"실시간 기름: {fuel_val:.1f}%"
                )

                if status in ["착륙 요청 중", "상공 대기 중"]:
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
                            key=f"app_{p['callsign']}",
                            use_container_width=True,
                        ):
                            approve_action(p["callsign"], sel_rwy)
                            st.rerun()
                    with b3:
                        if st.button(
                            "🛑 거절",
                            key=f"rej_{p['callsign']}",
                            use_container_width=True,
                        ):
                            reject_action(p["callsign"])
                            st.rerun()
                st.write("")

        # 🛫 이륙 요청 비행기
        with sub_col2:
            st.subheader(f"🛫 이륙 관제 ({len(dep_planes)}대)")

            for p in dep_planes:
                status = p.get("status", "이륙 요청 중")
                delay_sec = int(p.get("delay", 0))

                if status == "이륙 가속 중":
                    badge = '<span class="badge-success">🛫 이륙 중</span>'
                else:
                    badge = '<span class="badge-dep">📡 이륙 요청</span>'

                st.markdown(
                    f"""
                    <div class="dep-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="plane-title-dep">✈️ {p['callsign']} <small>({p.get('type')})</small></span>
                            {badge}
                        </div>
                        <div class="plane-sub">지상 대기 시간: <b style="color:#f59e0b;">{delay_sec}초 지연</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if status in ["이륙 요청 중", "지상 대기 중"]:
                    b1, b2, b3 = st.columns([1.8, 1, 1])
                    with b1:
                        sel_rwy = st.selectbox(
                            "활주로",
                            available_runways,
                            key=f"sel_dep_{p['callsign']}",
                            label_visibility="collapsed",
                        )
                    with b2:
                        if st.button(
                            "🚀 이륙",
                            key=f"app_{p['callsign']}",
                            use_container_width=True,
                        ):
                            approve_action(p["callsign"], sel_rwy)
                            st.rerun()
                    with b3:
                        if st.button(
                            "🛑 대기",
                            key=f"rej_{p['callsign']}",
                            use_container_width=True,
                        ):
                            reject_action(p["callsign"])
                            st.rerun()
                st.write("")

    # ----------------------------------------------------
    # [우측] 10개 활주로 실시간 타이머
    # ----------------------------------------------------
    with col_right:
        st.subheader("🛣️ 활주로 실시간 상태")

        rwy_display_list = RUNWAY_LIST.copy()
        if st.session_state.emg_runway_open:
            rwy_display_list.append("EMG-01")

        now = time.time()
        rwy_cols = st.columns(2)
        for idx, r_name in enumerate(rwy_display_list):
            busy_until = st.session_state.runways_busy_until.get(r_name, 0.0)
            remaining_sec = max(0.0, busy_until - now)

            with rwy_cols[idx % 2]:
                if remaining_sec > 0:
                    st.markdown(
                        f"""
                        <div class="runway-card" style="border-color:#ef4444; background-color:#2a1215;">
                            <b style="color:#f87171;">🔴 {r_name}</b><br>
                            <span style="color:#fca5a5; font-size:10px;">사용 중 ({remaining_sec:.1f}초)</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"🧹 비우기",
                        key=f"clear_{r_name}",
                        use_container_width=True,
                    ):
                        force_clear_runway(r_name)
                        st.rerun()
                else:
                    st.markdown(
                        f"""
                        <div class="runway-card" style="border-color:#10b981; background-color:#062319;">
                            <b style="color:#34d399;">🟢 {r_name}</b><br>
                            <span style="color:#6ee7b7; font-size:10px;">즉시 사용 가능</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()

        st.subheader("📜 실시간 관제 로그")
        for log in reversed(st.session_state.logs[-8:]):
            st.caption(log)

    # 🔴 [실시간 자동 갱신 루프] 0.3초마다 화면 재실행
    time.sleep(0.3)
    st.rerun()
