import random
import time
import matplotlib.pyplot as plt
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
        padding: 6px;
        margin-bottom: 4px;
    }
    .dep-card {
        background-color: #26170c;
        border: 1px solid #d97706;
        border-radius: 6px;
        padding: 6px;
        margin-bottom: 4px;
    }
    .plane-title-arr { font-size: 12px !important; font-weight: bold; color: #60a5fa; }
    .plane-title-dep { font-size: 12px !important; font-weight: bold; color: #fbbf24; }
    .plane-sub { font-size: 11px !important; color: #cbd5e1; }

    .runway-card {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 5px;
        padding: 4px;
        margin-bottom: 4px;
        text-align: center;
        font-size: 10px;
    }
    .stProgress > div > div > div > div { height: 4px !important; }

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
                        "fuel": float(random.randint(45, 90)),
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
        "🚨 [관제 업무 개시] 실시간 속도(5초당 약 2.5% 기름 소모)가 적용되었습니다."
    ]

    for _ in range(8):
        spawn_plane()


def update_realtime_engine():
    """실시간 기름 차감 엔진 (속도 조절: 초당 0.5% 차감 = 5초당 2.5% 차감)"""
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
            p["distance"] -= 5.0 * dt
            if p["distance"] <= 0:
                st.session_state.landed_count += 1
                st.session_state.score += 20
                st.session_state.logs.append(
                    f"🛬 [{p['callsign']}] {p.get('assigned_runway')} 터치다운 성공!"
                )
                continue

        # 2. 이륙 가속 중
        elif status == "이륙 가속 중":
            p["takeoff_timer"] -= dt
            if p["takeoff_timer"] <= 0:
                st.session_state.tookoff_count += 1
                st.session_state.score += 15
                st.session_state.logs.append(
                    f"🛫 [{p['callsign']}] {p.get('assigned_runway')} 이륙 완료!"
                )
                continue

        # 3. 상공 착륙 대기 비행기 (초당 0.5% 감소 ➔ 5초당 2.5% 감소)
        elif cat == "ARR":
            p["fuel"] -= 0.5 * dt

            # 🔴 [임무 실패 조건] 단 1대라도 기름 0% 도달 시 게임 오버
            if p["fuel"] <= 0:
                p["fuel"] = 0.0
                st.session_state.game_over = True
                st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                st.session_state.logs.append(st.session_state.game_over_reason)
                return

        # 4. 지상 이륙 대기 비행기
        elif cat == "DEP":
            p["delay"] += dt

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # 5초마다 신규 항공기 스폰 (최대 12대 유지)
    if (
        now - st.session_state.last_spawn_time > 5.0
        and len(st.session_state.planes) < 12
    ):
        spawn_plane()
        st.session_state.last_spawn_time = now


def approve_action(callsign, target_runway):
    now = time.time()
    if st.session_state.runways_busy_until[target_runway] > now:
        st.warning(f"🚫 {target_runway} 활주로는 사용 중입니다!")
        return

    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    last_type = st.session_state.last_landed_type[target_runway]
    occupancy_seconds = 7.0

    if last_type == "Heavy(대형)" and plane.get("type") in [
        "Medium(중형)",
        "Light(소형)",
    ]:
        occupancy_seconds += 3.0
        st.toast(
            f"⚠️ [{target_runway}] 선행 대형기로 인해 점유시간 +3초", icon="⚠️"
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


def render_mini_radar():
    """우측 옆면에 조그만 레이더 지도(Mini Radar Scope) 생성"""
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    fig.patch.set_facecolor("#070a13")
    ax.set_facecolor("#070a13")

    # 활주로 기준선 및 활주로 녹색 선 그리기
    ax.axhline(0, color="#334155", linestyle="-", linewidth=2)

    for i in range(1, 11):
        ax.plot([i, i], [0, -2], color="#10b981", linewidth=4)
        ax.text(
            i,
            -5,
            f"R{i:02d}",
            color="#10b981",
            fontsize=6,
            ha="center",
            fontweight="bold",
        )

    if st.session_state.emg_runway_open:
        ax.plot([11, 11], [0, -2], color="#ef4444", linewidth=4)
        ax.text(
            11,
            -5,
            "EMG",
            color="#ef4444",
            fontsize=6,
            ha="center",
            fontweight="bold",
        )

    # 레이더 동심 거리선
    for dist in [10, 20, 30, 40]:
        ax.axhline(
            dist, color="#1e293b", linestyle="--", linewidth=0.8, alpha=0.7
        )

    # 비행기 표시
    for p in st.session_state.planes:
        cat = p.get("category", "ARR")
        status = p.get("status", "")
        cs = p.get("callsign", "")
        fuel = p.get("fuel", 50.0)
        dist = p.get("distance", 0.0)

        rwy_str = p.get("assigned_runway")
        if rwy_str and "RWY" in rwy_str:
            try:
                r_x = int(rwy_str.replace("RWY ", ""))
            except:
                r_x = (abs(hash(cs)) % 10) + 1
        elif rwy_str == "EMG-01":
            r_x = 11
        else:
            r_x = (abs(hash(cs)) % 10) + 1

        if cat == "ARR":
            if fuel <= 20:
                p_color = "#ef4444"
            elif status == "착륙 접근 중":
                p_color = "#10b981"
            else:
                p_color = "#38bdf8"

            ax.plot(r_x, dist, marker="v", color=p_color, markersize=6)
            ax.text(
                r_x + 0.15,
                dist,
                f"✈️{cs}\n({fuel:.0f}%)",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
            )

            if status == "착륙 접근 중":
                ax.plot(
                    [r_x, r_x],
                    [dist, 0],
                    color=p_color,
                    linestyle=":",
                    linewidth=1.2,
                    alpha=0.8,
                )

        else:
            p_color = "#f59e0b"
            dep_y = -1 if status != "이륙 가속 중" else 5
            ax.plot(r_x, dep_y, marker="^", color=p_color, markersize=6)
            ax.text(
                r_x + 0.15,
                dep_y,
                f"🛫{cs}",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
            )

    max_x = 12 if st.session_state.emg_runway_open else 11
    ax.set_xlim(0, max_x)
    ax.set_ylim(-7, 42)
    ax.axis("off")

    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ==========================================
# 4. 실시간 엔진 업데이트
# ==========================================
update_realtime_engine()


# ==========================================
# 5. 메인 레이아웃 (좌: 관제 조작 / 우: 미니 지도 및 활주로)
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
        "⚠️ 5초당 약 2.5%의 기름이 소모됩니다. 오른쪽 미니맵을 확인하며 관제하세요!"
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

    col_left, col_right = st.columns([1.7, 1.1])

    available_runways = RUNWAY_LIST.copy()
    if st.session_state.emg_runway_open:
        available_runways.append("EMG-01")

    # ----------------------------------------------------
    # [좌측] 🛬 착륙 비행기 & 🛫 이륙 비행기 제어 버튼 구역
    # ----------------------------------------------------
    with col_left:
        arr_planes = [
            p for p in st.session_state.planes if p.get("category") == "ARR"
        ]
        dep_planes = [
            p for p in st.session_state.planes if p.get("category") == "DEP"
        ]

        sub_col1, sub_col2 = st.columns(2)

        # 🛬 착륙 비행기
        with sub_col1:
            st.subheader(f"🛬 착륙 관제 ({len(arr_planes)}대)")

            for p in arr_planes:
                status = p.get("status", "착륙 요청 중")
                fuel_val = max(0.0, p.get("fuel", 0.0))

                if fuel_val <= 20.0:
                    badge = '<span class="badge-danger">🚨 위급</span>'
                elif status == "착륙 접근 중":
                    badge = '<span class="badge-success">🛬 접근 중</span>'
                else:
                    badge = '<span class="badge-arr">📡 요청</span>'

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
                    fuel_val / 100.0, text=f"연료: {fuel_val:.1f}%"
                )

                if status in ["착륙 요청 중", "상공 대기 중"]:
                    b1, b2, b3 = st.columns([1.6, 1, 1])
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

        # 🛫 이륙 비행기
        with sub_col2:
            st.subheader(f"🛫 이륙 관제 ({len(dep_planes)}대)")

            for p in dep_planes:
                status = p.get("status", "이륙 요청 중")
                delay_sec = int(p.get("delay", 0))

                if status == "이륙 가속 중":
                    badge = '<span class="badge-success">🛫 이륙 중</span>'
                else:
                    badge = '<span class="badge-dep">📡 요청</span>'

                st.markdown(
                    f"""
                    <div class="dep-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="plane-title-dep">✈️ {p['callsign']} <small>({p.get('type')})</small></span>
                            {badge}
                        </div>
                        <div class="plane-sub">대기시간: <b style="color:#f59e0b;">{delay_sec}초 지연</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if status in ["이륙 요청 중", "지상 대기 중"]:
                    b1, b2, b3 = st.columns([1.6, 1, 1])
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
    # [우측] 📡 실시간 미니 레이더 지도 & 활주로 현황
    # ----------------------------------------------------
    with col_right:
        st.subheader("📡 실시간 미니 관제 레이더")
        render_mini_radar()

        st.subheader("🛣️ 활주로 상태 (10개)")
        now = time.time()
        rwy_cols = st.columns(2)
        for idx, r_name in enumerate(available_runways):
            busy_until = st.session_state.runways_busy_until.get(r_name, 0.0)
            remaining_sec = max(0.0, busy_until - now)

            with rwy_cols[idx % 2]:
                if remaining_sec > 0:
                    st.markdown(
                        f"""
                        <div class="runway-card" style="border-color:#ef4444; background-color:#2a1215;">
                            <b style="color:#f87171;">🔴 {r_name}</b> ({remaining_sec:.1f}초)
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
                            <b style="color:#34d399;">🟢 {r_name}</b> (가능)
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.write("")
        if not st.session_state.emg_runway_open:
            if st.button(
                "🚨 01E 비상 활주로 개설",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.emg_runway_open = True
                st.session_state.logs.append(
                    "🚨 [비상 활주로] EMG-01 활주로가 개설되었습니다!"
                )
                st.rerun()

        st.divider()
        st.caption("📜 관제 실시간 교신 로그")
        for log in reversed(st.session_state.logs[-6:]):
            st.caption(log)

    # 0.4초 간격 자동 재실행
    time.sleep(0.4)
    st.rerun()
