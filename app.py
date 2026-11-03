import math
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 통합 ATC 관제 대시보드 테마 스타일
# ==========================================
st.set_page_config(
    page_title="Pro Integrated ATC 3D 관제탑 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #030712 !important;
        color: #f1f5f9 !important;
    }
    
    div.stButton > button {
        background-color: #0f172a !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        font-weight: bold !important;
        font-size: 11px !important;
        padding: 3px 6px !important;
        min-height: 26px !important;
        border-radius: 4px !important;
    }
    div.stButton > button:hover {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #b91c1c !important;
        border-color: #ef4444 !important;
    }

    .sector-card {
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 6px;
    }

    .msg-box {
        background-color: #090d16;
        border: 1px solid #0284c7;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }

    .arr-card {
        background-color: #0a1329;
        border: 1px solid #1d4ed8;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 4px;
    }
    .dep-card {
        background-color: #211209;
        border: 1px solid #d97706;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 4px;
    }
    .ground-card {
        background-color: #0f2027;
        border: 1px solid #2c5364;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 4px;
    }
    .enroute-card {
        background-color: #1a0f2e;
        border: 1px solid #6b21a8;
        border-radius: 5px;
        padding: 5px;
        margin-bottom: 4px;
    }

    .gate-box {
        background-color: #0b1329;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px;
        text-align: center;
        font-size: 10px;
        margin-bottom: 4px;
    }

    .stProgress > div > div > div > div { height: 4px !important; }

    .badge-danger { background-color: #dc2626; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-warn { background-color: #d97706; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-info { background-color: #0284c7; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 기본 변수 초기화
# ==========================================
RUNWAY_LIST = [f"RWY {i:02d}" for i in range(1, 11)]
GATES = [f"Gate {i:02d}" for i in range(1, 9)]
CENTERS = [
    "인천 ACC (RKRR)",
    "도쿄 ACC (RJTG)",
    "베이징 ACC (ZBPE)",
    "후쿠오카 ACC (RJDG)",
]

AIRPORTS = [
    "RKSI (인천)",
    "RKSS (김포)",
    "RKPK (김해)",
    "RJTT (도쿄)",
    "VHHH (홍콩)",
    "KLAX (LA)",
]

if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "game_over_reason" not in st.session_state:
    st.session_state.game_over_reason = ""
if "planes" not in st.session_state:
    st.session_state.planes = []
if "score" not in st.session_state:
    st.session_state.score = 250
if "landed_count" not in st.session_state:
    st.session_state.landed_count = 0
if "tookoff_count" not in st.session_state:
    st.session_state.tookoff_count = 0
if "handoff_count" not in st.session_state:
    st.session_state.handoff_count = 0
if "emg_runway_open" not in st.session_state:
    st.session_state.emg_runway_open = False
if "active_sector" not in st.session_state:
    st.session_state.active_sector = "📡 1. 접근/활주로 관제"
if "ai_auto_pilot" not in st.session_state:
    st.session_state.ai_auto_pilot = True
if "runways_busy_until" not in st.session_state:
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
if "gates_occupied" not in st.session_state:
    st.session_state.gates_occupied = {g: None for g in GATES}
if "logs" not in st.session_state:
    st.session_state.logs = []
if "selected_target" not in st.session_state:
    st.session_state.selected_target = None
if "last_tick_time" not in st.session_state:
    st.session_state.last_tick_time = time.time()
if "last_spawn_time" not in st.session_state:
    st.session_state.last_spawn_time = time.time()


# ==========================================
# 3. 신규 비행기 생성 및 상태 세분화
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
                [
                    "B777-300ER (대형)",
                    "A350-900 (대형)",
                    "A320neo (중형)",
                    "B737-MAX8 (소형)",
                ]
            )
            passengers = random.randint(120, 350)
            origin = random.choice(AIRPORTS)

            if category == "ARR":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "phase": "APPROACH",  # APPROACH -> TAXI_TO_GATE -> PARKED
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": origin,
                        "fuel": float(random.randint(50, 90)),
                        "distance": float(random.randint(18, 36)),
                        "delay": 0.0,
                        "status": "접근 관제 요청 중",
                        "assigned_runway": None,
                        "assigned_gate": None,
                        "assigned_center": None,
                    }
                )
            else:
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "DEP",
                        "phase": "AT_GATE",  # AT_GATE -> TAXI_TO_RWY -> RUNWAY_TAKEOFF -> ENROUTE_CLIMB
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": "본 공항 관제구역",
                        "fuel": 100.0,
                        "distance": 0.0,
                        "delay": 0.0,
                        "status": "게이트 푸시백 요청 중",
                        "assigned_runway": None,
                        "assigned_gate": random.choice(GATES),
                        "assigned_center": random.choice(CENTERS),
                    }
                )
            break


def init_game():
    st.session_state.game_started = True
    st.session_state.game_over = False
    st.session_state.game_over_reason = ""
    st.session_state.planes = []
    st.session_state.score = 250
    st.session_state.landed_count = 0
    st.session_state.tookoff_count = 0
    st.session_state.handoff_count = 0
    st.session_state.emg_runway_open = False
    st.session_state.selected_target = None
    now = time.time()
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
    st.session_state.gates_occupied = {g: None for g in GATES}
    st.session_state.last_tick_time = now
    st.session_state.last_spawn_time = now
    st.session_state.logs = [
        "🚨 [통합 관제 개시] 3대 관제 섹터 및 AI 실시간 자동 지원이 동작합니다."
    ]

    for _ in range(8):
        spawn_plane()


# ==========================================
# 4. 실시간 엔진 및 AI 자동 관제 알고리즘
# ==========================================
def run_ai_auto_controller(now):
    """플레이어가 조종하지 않는 구역을 AI 관제사가 자동으로 보조"""
    if not st.session_state.ai_auto_pilot:
        return

    # 1. 접근/활주로 AI 관제 지원 (비상/연료 부족 비행기 자동 착륙 승인)
    for p in st.session_state.planes:
        if p["phase"] == "APPROACH" and p["status"] in [
            "접근 관제 요청 중",
            "상공 대기 중",
        ]:
            if p["fuel"] <= 35.0:
                # 비어있는 활주로 탐색
                for r in RUNWAY_LIST:
                    if st.session_state.runways_busy_until[r] <= now:
                        p["status"] = "착륙 접근 중"
                        p["assigned_runway"] = r
                        st.session_state.runways_busy_until[r] = now + 7.0
                        st.session_state.logs.append(
                            f"🤖 [AI 자동 착륙] {p['callsign']} ➔ {r} (연료 긴급 처리)"
                        )
                        break

        # 2. 지상 관제 AI 지원 (착륙 후 게이트 자동 배정)
        elif p["phase"] == "TAXI_TO_GATE" and p["status"] == "게이트 배정 대기":
            empty_gates = [
                g
                for g, cs in st.session_state.gates_occupied.items()
                if cs is None
            ]
            if empty_gates:
                target_g = empty_gates[0]
                p["assigned_gate"] = target_g
                p["status"] = "게이트 이동 중"
                st.session_state.gates_occupied[target_g] = p["callsign"]
                st.session_state.logs.append(
                    f"🤖 [AI 지상 관제] {p['callsign']} ➔ {target_g} 이동 지시"
                )

        # 3. 항로 관제 AI 지원 (상승 완료 비행기 자동 교신 이양)
        elif (
            p["phase"] == "ENROUTE_CLIMB"
            and p["status"] == "관제권 이양(Handoff) 요청"
        ):
            p["status"] = "관제 이양 완료"
            st.session_state.handoff_count += 1
            st.session_state.score += 15
            st.session_state.logs.append(
                f"🤖 [AI 항로 관제] {p['callsign']} ➔ {p['assigned_center']} 성공적 이양"
            )


def update_realtime_engine():
    """실시간 시뮬레이션 물리 및 상태 변경 엔진"""
    if not st.session_state.game_started or st.session_state.game_over:
        return

    now = time.time()
    dt = now - st.session_state.last_tick_time
    st.session_state.last_tick_time = now

    remaining_planes = []
    for p in st.session_state.planes:
        phase = p.get("phase", "APPROACH")
        status = p.get("status", "")

        # A. 착륙 접근 단계
        if phase == "APPROACH":
            if status == "착륙 접근 중":
                p["distance"] -= 5.0 * dt
                if p["distance"] <= 0:
                    st.session_state.landed_count += 1
                    p["phase"] = "TAXI_TO_GATE"
                    p["status"] = "게이트 배정 대기"
                    p["distance"] = 0.0
                    st.session_state.logs.append(
                        f"🛬 [{p['callsign']}] 활주로 착륙 완료! (지상 관제 이관)"
                    )
            else:
                p["fuel"] -= 0.5 * dt  # 5초당 2.5% 소모
                if p["fuel"] <= 0:
                    st.session_state.game_over = True
                    st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                    st.session_state.logs.append(
                        st.session_state.game_over_reason
                    )
                    return

        # B. 지상 유도로 / 게이트 단계
        elif phase == "TAXI_TO_GATE":
            if status == "게이트 이동 중":
                p["delay"] += dt
                if p["delay"] >= 6.0:  # 6초 후 게이트 도착
                    p["phase"] = "PARKED"
                    p["status"] = "게이트 주기 완료"
                    st.session_state.score += 20
                    st.session_state.logs.append(
                        f"🅿️ [{p['callsign']}] {p['assigned_gate']} 안전 주차 완료!"
                    )
                    continue

        elif phase == "AT_GATE":
            p["delay"] += dt

        elif phase == "TAXI_TO_RWY":
            p["delay"] += dt
            if p["delay"] >= 5.0:  # 5초 후 활주로 대기선 도달
                p["phase"] = "READY_TAKEOFF"
                p["status"] = "이륙 허가 대기 중"

        elif phase == "READY_TAKEOFF":
            if status == "이륙 가속 중":
                p["takeoff_timer"] = p.get("takeoff_timer", 5.0) - dt
                if p["takeoff_timer"] <= 0:
                    st.session_state.tookoff_count += 1
                    p["phase"] = "ENROUTE_CLIMB"
                    p["status"] = "관제권 이양(Handoff) 요청"
                    p["altitude"] = 12000
                    st.session_state.logs.append(
                        f"🛫 [{p['callsign']}] 이륙 성공! (항로 관제 이관)"
                    )

        # C. 항로 / 고고도 이양 단계
        elif phase == "ENROUTE_CLIMB":
            if status == "관제 이양 완료":
                continue  # 처리 완료 후 공역 이탈
            p["altitude"] = p.get("altitude", 12000) + int(1000 * dt)

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # AI 자동 관제 수행
    run_ai_auto_controller(now)

    # 신규 비행기 스폰 (5초 간격)
    if (
        now - st.session_state.last_spawn_time > 5.0
        and len(st.session_state.planes) < 12
    ):
        spawn_plane()
        st.session_state.last_spawn_time = now


# ==========================================
# 5. 관제소 레이더 시각화 렌더링
# ==========================================
def render_sector_radar():
    """메인 레이더 스코프"""
    fig, ax = plt.subplots(figsize=(5.2, 4.8), dpi=120)
    fig.patch.set_facecolor("#030712")
    ax.set_facecolor("#030712")

    # 동심원 격자
    for r in [10, 20, 30, 40]:
        ax.axhline(r, color="#0284c7", linestyle="--", linewidth=0.6, alpha=0.3)

    # 활주로
    ax.axhline(0, color="#334155", linewidth=2.0)
    for i in range(1, 11):
        ax.plot([i, i], [0, -3.0], color="#00ff66", linewidth=4.0, alpha=0.9)

    for idx, p in enumerate(st.session_state.planes):
        phase = p.get("phase", "APPROACH")
        cs = p.get("callsign", "")
        fuel = p.get("fuel", 50.0)
        dist = p.get("distance", 0.0)

        r_x = (abs(hash(cs)) % 10) + 1
        p_color = (
            "#ff3344"
            if fuel <= 20
            else ("#00ff66" if "중" in p.get("status", "") else "#00f3ff")
        )

        if phase == "APPROACH":
            ax.plot(r_x, dist, marker="v", color=p_color, markersize=8)
            ax.text(
                r_x + 0.2,
                dist,
                f"{cs}\n({fuel:.0f}%)",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
            )
        elif phase in ["TAXI_TO_GATE", "AT_GATE", "TAXI_TO_RWY"]:
            ax.plot(r_x, -1.5, marker="s", color="#f59e0b", markersize=6)
            ax.text(
                r_x + 0.2,
                -1.5,
                f"{cs}(GND)",
                color="#f59e0b",
                fontsize=6.0,
            )
        elif phase == "ENROUTE_CLIMB":
            alt = p.get("altitude", 15000)
            ax.plot(r_x, 38, marker="^", color="#a855f7", markersize=8)
            ax.text(
                r_x + 0.2,
                38,
                f"{cs}\nFL{int(alt/100)}",
                color="#a855f7",
                fontsize=6.5,
            )

    ax.set_xlim(0, 11)
    ax.set_ylim(-8, 44)
    ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ==========================================
# 6. 실시간 엔진 업데이트
# ==========================================
update_realtime_engine()


# ==========================================
# 7. 메인 통합 UI 대시보드
# ==========================================
st.title("⚡ Pro Integrated ATC 대규모 통합 관제탑 센터")

if st.session_state.game_over:
    st.error("💥 [GAME OVER / 관제 실패]")
    st.subheader(st.session_state.game_over_reason)
    if st.button("🔄 다시 도전하기", type="primary", use_container_width=True):
        init_game()
        st.rerun()

elif not st.session_state.game_started:
    st.info(
        "👋 상단 탭으로 접근관제, 지상관제, 항로관제 구역을 자유롭게 전환할 수 있습니다."
    )
    if st.button(
        "🚀 통합 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 상단 메트릭 요약
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📊 현재 관제 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("☁️ 항로 이양 성공", f"{st.session_state.handoff_count}대")
    m5.metric("✈️ 관리 항공기", f"{len(st.session_state.planes)}대")

    # 관제 구역 전환 버튼 바 및 AI 옵션
    bar_c1, bar_c2 = st.columns([3, 1])
    with bar_c1:
        st.session_state.active_sector = st.radio(
            "📍 관제 구역 선택 (원클릭 전환)",
            [
                "📡 1. 접근/활주로 관제",
                "🚜 2. 지상/게이트 관제",
                "☁️ 3. 항로/하늘 관제",
            ],
            horizontal=True,
        )
    with bar_c2:
        st.session_state.ai_auto_pilot = st.toggle(
            "🤖 AI 자동 관제 지원 (미주시 구역 보조)",
            value=st.session_state.ai_auto_pilot,
        )

    st.divider()

    col_left, col_mid, col_right = st.columns([1.2, 1.1, 0.9])

    # ----------------------------------------------------
    # [좌측 열] 활성 관제 섹터별 제어 화면 (3개 구역)
    # ----------------------------------------------------
    with col_left:
        # SECTOR 1: 접근 / 활주로 관제
        if "1. 접근" in st.session_state.active_sector:
            st.subheader("📡 접근/활주로 관제 섹터")

            arr_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "APPROACH"
            ]
            ready_dep_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "READY_TAKEOFF"
            ]

            st.caption(f"🛬 착륙 접근 요청 ({len(arr_list)}대)")
            for p in arr_list:
                status = p.get("status", "")
                fuel_val = max(0.0, p.get("fuel", 0.0))

                st.markdown(
                    f"""
                    <div class="arr-card">
                        <b>✈️ {p['callsign']}</b> ({p['type']})<br>
                        연료: <b style="color:#ef4444;">{fuel_val:.1f}%</b> | 거리: {p['distance']:.1f}NM
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if status in ["접근 관제 요청 중", "상공 대기 중"]:
                    b1, b2 = st.columns(2)
                    with b1:
                        sel_rwy = st.selectbox(
                            "활주로",
                            RUNWAY_LIST,
                            key=f"rwy_{p['callsign']}",
                            label_visibility="collapsed",
                        )
                    with b2:
                        if st.button(
                            "✅ 착륙 허가",
                            key=f"land_{p['callsign']}",
                            use_container_width=True,
                        ):
                            p["status"] = "착륙 접근 중"
                            p["assigned_runway"] = sel_rwy
                            st.session_state.runways_busy_until[sel_rwy] = (
                                time.time() + 7.0
                            )
                            st.rerun()

            st.divider()
            st.caption(f"🛫 활주로 이륙 요청 ({len(ready_dep_list)}대)")
            for p in ready_dep_list:
                st.markdown(
                    f"""
                    <div class="dep-card">
                        <b>✈️ {p['callsign']}</b> | 상태: <b>{p['status']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "🚀 이륙 허가",
                    key=f"tkoff_{p['callsign']}",
                    use_container_width=True,
                ):
                    p["status"] = "이륙 가속 중"
                    p["takeoff_timer"] = 5.0
                    st.rerun()

        # SECTOR 2: 지상 / 게이트 관제
        elif "2. 지상" in st.session_state.active_sector:
            st.subheader("🚜 지상/게이트 관제 섹터")

            taxi_gate_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "TAXI_TO_GATE"
            ]
            at_gate_list = [
                p for p in st.session_state.planes if p.get("phase") == "AT_GATE"
            ]

            st.caption(f"🛬 착륙 후 게이트 배정 대기 ({len(taxi_gate_list)}대)")
            for p in taxi_gate_list:
                st.markdown(
                    f"""
                    <div class="ground-card">
                        <b>✈️ {p['callsign']}</b> (활주로 착륙 완료) ➔ 게이트 지시 필요
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if p["status"] == "게이트 배정 대기":
                    empty_gates = [
                        g
                        for g, cs in st.session_state.gates_occupied.items()
                        if cs is None
                    ]
                    if empty_gates:
                        b1, b2 = st.columns(2)
                        with b1:
                            sel_g = st.selectbox(
                                "게이트",
                                empty_gates,
                                key=f"g_{p['callsign']}",
                                label_visibility="collapsed",
                            )
                        with b2:
                            if st.button(
                                "🚜 유도로 이동",
                                key=f"taxig_{p['callsign']}",
                                use_container_width=True,
                            ):
                                p["assigned_gate"] = sel_g
                                p["status"] = "게이트 이동 중"
                                st.session_state.gates_occupied[sel_g] = p[
                                    "callsign"
                                ]
                                st.rerun()

            st.divider()
            st.caption(f"🛫 게이트 출동/푸시백 요청 ({len(at_gate_list)}대)")
            for p in at_gate_list:
                st.markdown(
                    f"""
                    <div class="dep-card">
                        <b>✈️ {p['callsign']}</b> ({p['assigned_gate']} 주기 중)
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                b1, b2 = st.columns(2)
                with b1:
                    sel_rwy = st.selectbox(
                        "활주로",
                        RUNWAY_LIST,
                        key=f"dep_rwy_{p['callsign']}",
                        label_visibility="collapsed",
                    )
                with b2:
                    if st.button(
                        "🚜 활주로 유도",
                        key=f"push_{p['callsign']}",
                        use_container_width=True,
                    ):
                        st.session_state.gates_occupied[
                            p["assigned_gate"]
                        ] = None
                        p["phase"] = "TAXI_TO_RWY"
                        p["status"] = "활주로 이동 중"
                        p["assigned_runway"] = sel_rwy
                        st.rerun()

        # SECTOR 3: 항로 / 하늘 관제
        else:
            st.subheader("☁️ 항로/하늘 관제 섹터 (Area Control)")

            enroute_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "ENROUTE_CLIMB"
            ]
            st.caption(f"📡 고고도 항로 상승 및 관제 이양 대기 ({len(enroute_list)}대)")

            for p in enroute_list:
                st.markdown(
                    f"""
                    <div class="enroute-card">
                        <b>✈️ {p['callsign']}</b> | 고도: <b style="color:#a855f7;">FL{int(p.get('altitude',12000)/100)}</b><br>
                        이양 대상: <b>{p['assigned_center']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"📡 {p['assigned_center']} 관제 이양(Handoff)",
                    key=f"hand_{p['callsign']}",
                    use_container_width=True,
                ):
                    p["status"] = "관제 이양 완료"
                    st.session_state.handoff_count += 1
                    st.session_state.score += 15
                    st.session_state.logs.append(
                        f"📡 [{p['callsign']}] {p['assigned_center']} 성공적 교신 이양 완료!"
                    )
                    st.rerun()

    # ----------------------------------------------------
    # [중앙 열] 📡 실시간 레이더 스코프
    # ----------------------------------------------------
    with col_mid:
        st.subheader("📡 통합 관제 레이더 스코프")
        render_sector_radar()

    # ----------------------------------------------------
    # [우측 열] 🅿️ 게이트 현황 및 교신 로그
    # ----------------------------------------------------
    with col_right:
        st.subheader("🅿️ 게이트 주기 현황 (8개)")
        g_cols = st.columns(2)
        for idx, g_name in enumerate(GATES):
            occ = st.session_state.gates_occupied[g_name]
            with g_cols[idx % 2]:
                if occ:
                    st.markdown(
                        f"""
                        <div class="gate-box" style="border-color:#ef4444; background-color:#2a1215;">
                            <b style="color:#f87171;">🔴 {g_name}</b><br><small>{occ}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="gate-box" style="border-color:#10b981; background-color:#062319;">
                            <b style="color:#34d399;">🟢 {g_name}</b><br><small>빈 게이트</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.caption("📜 실시간 관제 교신 로그")
        for log in reversed(st.session_state.logs[-6:]):
            st.caption(log)

    time.sleep(0.4)
    st.rerun()
