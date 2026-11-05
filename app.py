import math
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 고대비 순백색(White) 폰트 & Pro ATC 스타일
# ==========================================
st.set_page_config(
    page_title="Pro Integrated ATC 3D 관제탑 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* 전체 앱 배경 */
    .stApp {
        background-color: #030712 !important;
        color: #ffffff !important;
    }

    /* 모든 텍스트 글자색 순백색 강제 고정 */
    p, span, div, label, h1, h2, h3, h4, h5, h6, caption {
        color: #ffffff !important;
    }

    /* 스트림릿 버튼 스타일 */
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
        color: #ffffff !important;
    }

    /* 카드 스타일 */
    .arr-card {
        background-color: #0a1329;
        border: 1px solid #1d4ed8;
        border-radius: 5px;
        padding: 6px;
        margin-bottom: 4px;
        color: #ffffff !important;
    }
    .dep-card {
        background-color: #211209;
        border: 1px solid #d97706;
        border-radius: 5px;
        padding: 6px;
        margin-bottom: 4px;
        color: #ffffff !important;
    }
    .ground-card {
        background-color: #0f2027;
        border: 1px solid #2c5364;
        border-radius: 5px;
        padding: 6px;
        margin-bottom: 4px;
        color: #ffffff !important;
    }
    .enroute-card {
        background-color: #1a0f2e;
        border: 1px solid #6b21a8;
        border-radius: 5px;
        padding: 6px;
        margin-bottom: 4px;
        color: #ffffff !important;
    }

    .info-card {
        background-color: #0b1329;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 5px;
        text-align: center;
        font-size: 10px;
        margin-bottom: 4px;
    }

    .stProgress > div > div > div > div { height: 4px !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 데이터 초기화
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
WAYPOINTS = [
    ("KIMPO", 2, 32),
    ("BANYU", 5, 25),
    ("EON", 8, 35),
    ("GANGWON", 9, 18),
    ("SEOUL", 4, 12),
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
if "last_tick_time" not in st.session_state:
    st.session_state.last_tick_time = time.time()
if "last_spawn_time" not in st.session_state:
    st.session_state.last_spawn_time = time.time()


def add_log(sector_code, text):
    st.session_state.logs.append({"sector": sector_code, "text": text})


# ==========================================
# 3. 비행기 생성 및 로직
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

    for _ in range(50):
        cs = f"{random.choice(prefixes)}{random.randint(100, 999)}"
        if cs not in existing_cs:
            category = random.choice(["ARR", "DEP", "ENROUTE"])
            ac_type = random.choice(
                [
                    "B777-300ER (대형)",
                    "A350-900 (대형)",
                    "A320neo (중형)",
                    "B737-MAX8 (소형)",
                ]
            )
            passengers = random.randint(120, 350)

            if category == "ARR":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "phase": "APPROACH",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": random.choice(AIRPORTS),
                        "fuel": float(random.randint(55, 95)),
                        "distance": float(random.randint(18, 40)),
                        "delay": 0.0,
                        "status": "접근 요청 중",
                        "assigned_runway": None,
                        "assigned_gate": None,
                        "assigned_center": None,
                    }
                )
            elif category == "DEP":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "DEP",
                        "phase": "AT_GATE",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": "본 공항 관제구역",
                        "fuel": 100.0,
                        "distance": 0.0,
                        "delay": 0.0,
                        "takeoff_timer": 5.0,
                        "status": "푸시백 요청 중",
                        "assigned_runway": None,
                        "assigned_gate": random.choice(GATES),
                        "assigned_center": random.choice(CENTERS),
                    }
                )
            else:
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ENROUTE",
                        "phase": "ENROUTE_INBOUND",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": random.choice(AIRPORTS),
                        "fuel": float(random.randint(60, 95)),
                        "altitude": random.randint(24000, 32000),
                        "delay": 0.0,
                        "status": "접근구역 이양 대기",
                        "assigned_runway": None,
                        "assigned_gate": None,
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
    now = time.time()
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
    st.session_state.gates_occupied = {g: None for g in GATES}
    st.session_state.last_tick_time = now
    st.session_state.last_spawn_time = now
    st.session_state.logs = []
    add_log(
        "ALL",
        "🚨 [통합 관제 개시] 관리 항공기 정원이 대폭 확장되어 밀집 관제가 가동됩니다.",
    )

    # 초기 생성 항공기 수: 16대
    for _ in range(16):
        spawn_plane()


# ==========================================
# 4. 실시간 엔진 및 AI 보조 관제
# ==========================================
def run_ai_auto_controller(now):
    if not st.session_state.ai_auto_pilot:
        return

    for p in st.session_state.planes:
        # 1. 접근 관제 AI 보조
        if p["phase"] == "APPROACH" and p["status"] in [
            "접근 요청 중",
            "상공 대기 중",
        ]:
            if p["fuel"] <= 35.0:
                for r in RUNWAY_LIST:
                    if st.session_state.runways_busy_until[r] <= now:
                        p["status"] = "착륙 접근 중"
                        p["assigned_runway"] = r
                        st.session_state.runways_busy_until[r] = now + 7.0
                        add_log(
                            "APPROACH",
                            f"🤖 [AI 착륙 승인] {p['callsign']} ➔ {r} (연료 긴급)",
                        )
                        break

        # 2. 지상 관제 AI 보조
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
                add_log(
                    "GROUND",
                    f"🤖 [AI 지상 관제] {p['callsign']} ➔ {target_g} 이동 지시",
                )

        # 3. 항로 관제 AI 보조
        elif (
            p["phase"] == "ENROUTE_CLIMB"
            and p["status"] == "관제권 이양(Handoff) 요청"
        ):
            p["status"] = "관제 이양 완료"
            st.session_state.handoff_count += 1
            st.session_state.score += 15
            add_log(
                "ENROUTE",
                f"🤖 [AI 항로 관제] {p['callsign']} ➔ {p['assigned_center']} 이양 완료",
            )


def update_realtime_engine():
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
                    add_log(
                        "APPROACH",
                        f"🛬 [{p['callsign']}] 활주로 터치다운 완료 (지상 관제 이관)",
                    )
            else:
                p["fuel"] -= 0.5 * dt
                if p["fuel"] <= 0:
                    st.session_state.game_over = True
                    st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                    add_log("ALL", st.session_state.game_over_reason)
                    return

        # B. 지상 이동 단계
        elif phase == "TAXI_TO_GATE":
            if status == "게이트 이동 중":
                p["delay"] += dt
                if p["delay"] >= 5.0:
                    p["phase"] = "PARKED"
                    p["status"] = "게이트 주기 완료"
                    st.session_state.score += 20
                    add_log(
                        "GROUND",
                        f"🅿️ [{p['callsign']}] {p['assigned_gate']} 주기 완료",
                    )
                    continue

        elif phase == "AT_GATE":
            p["delay"] += dt

        elif phase == "TAXI_TO_RWY":
            p["delay"] += dt
            if p["delay"] >= 5.0:
                p["phase"] = "READY_TAKEOFF"
                p["status"] = "이륙 허가 대기 중"

        elif phase == "READY_TAKEOFF":
            if status == "이륙 가속 중":
                p["takeoff_timer"] = p.get("takeoff_timer", 5.0) - dt
                if p["takeoff_timer"] <= 0:
                    st.session_state.tookoff_count += 1
                    p["phase"] = "ENROUTE_CLIMB"
                    p["status"] = "관제권 이양(Handoff) 요청"
                    p["altitude"] = 14000
                    add_log(
                        "APPROACH",
                        f"🛫 [{p['callsign']}] 이륙 성공 (항로 관제 이관)",
                    )

        # C. 항로 이양 단계
        elif phase in ["ENROUTE_CLIMB", "ENROUTE_INBOUND"]:
            if status in ["관제 이양 완료", "접근관제 이관 완료"]:
                continue
            if phase == "ENROUTE_CLIMB":
                p["altitude"] = p.get("altitude", 14000) + int(1000 * dt)

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes
    run_ai_auto_controller(now)

    # 최대 수용 항공기 수: 24대, 스폰 주기: 3초
    if (
        now - st.session_state.last_spawn_time > 3.0
        and len(st.session_state.planes) < 24
    ):
        spawn_plane()
        st.session_state.last_spawn_time = now


# ==========================================
# 5. 📡 섹터별 전용 레이더 시각화 렌더러
# ==========================================
def render_sector_specific_radar():
    sector = st.session_state.get("active_sector", "📡 1. 접근/활주로 관제")

    fig, ax = plt.subplots(figsize=(5.2, 4.8), dpi=130)
    fig.patch.set_facecolor("#030712")
    ax.set_facecolor("#030712")

    # 1. 접근/활주로 관제 레이더
    if "1. 접근" in sector:
        for r in [10, 20, 30, 40]:
            ax.axhline(
                r, color="#0284c7", linestyle="--", linewidth=0.6, alpha=0.3
            )
            ax.text(
                0.2,
                r + 0.5,
                f"{r}NM",
                color="#0284c7",
                fontsize=6,
                fontweight="bold",
            )

        ax.axhline(0, color="#334155", linewidth=2.0)
        for i in range(1, 11):
            ax.plot([i, i], [0, -3.0], color="#00ff66", linewidth=4.0, alpha=0.9)
            ax.text(
                i,
                -6.5,
                f"R{i:02d}",
                color="#00ff66",
                fontsize=6.5,
                ha="center",
                fontweight="bold",
            )

        for p in st.session_state.planes:
            if p.get("phase") == "APPROACH":
                cs = p["callsign"]
                fuel = p.get("fuel", 50.0)
                dist = p.get("distance", 0.0)
                r_x = (abs(hash(cs)) % 10) + 1
                p_color = (
                    "#ff3344"
                    if fuel <= 20
                    else ("#00ff66" if p["status"] == "착륙 접근 중" else "#00f3ff")
                )

                ax.plot(r_x, dist, marker="v", color=p_color, markersize=8)
                ax.text(
                    r_x + 0.2,
                    dist,
                    f"✈️{cs}\n({fuel:.0f}%)",
                    color=p_color,
                    fontsize=6.5,
                    fontweight="bold",
                )
                if p["status"] == "착륙 접근 중":
                    ax.plot(
                        [r_x, r_x],
                        [dist, 0],
                        color=p_color,
                        linestyle=":",
                        linewidth=1.2,
                    )

        ax.set_xlim(0, 11)
        ax.set_ylim(-8, 44)

    # 2. 지상/게이트 ASDE 레이더
    elif "2. 지상" in sector:
        ax.set_title(
            "[ASDE Ground Movement Radar Scope]",
            color="#38bdf8",
            fontsize=8,
            fontweight="bold",
        )

        rect = plt.Rectangle(
            (1, 1), 9, 4, facecolor="#1e293b", edgecolor="#0284c7", linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(
            5.5,
            3,
            "MAIN TERMINAL BUILDING",
            color="#38bdf8",
            fontsize=7,
            ha="center",
            fontweight="bold",
        )

        for i in range(1, 9):
            g_name = f"Gate {i:02d}"
            occ = st.session_state.gates_occupied.get(g_name)
            g_color = "#ff3344" if occ else "#00ff66"

            ax.plot([i + 0.6, i + 0.6], [1, -1], color="#334155", linewidth=1.5)
            ax.scatter(i + 0.6, -1, color=g_color, s=40, marker="s")
            ax.text(
                i + 0.6,
                -2.5,
                f"G{i:02d}\n{occ if occ else 'FREE'}",
                color=g_color,
                fontsize=5.5,
                ha="center",
                fontweight="bold",
            )

        ax.axhline(-6, color="#eab308", linestyle="-.", linewidth=1.5)
        ax.text(0.5, -5.5, "TAXIWAY A", color="#eab308", fontsize=6)

        ax.axhline(-10, color="#eab308", linestyle="-.", linewidth=1.5)
        ax.text(0.5, -9.5, "TAXIWAY B", color="#eab308", fontsize=6)

        for p in st.session_state.planes:
            phase = p.get("phase")
            if phase in ["TAXI_TO_GATE", "AT_GATE", "TAXI_TO_RWY"]:
                cs = p["callsign"]
                r_x = (abs(hash(cs)) % 8) + 1.2
                t_y = -6 if phase == "TAXI_TO_GATE" else -10

                ax.plot(
                    r_x,
                    t_y,
                    marker="o",
                    color="#f59e0b",
                    markersize=9,
                    markeredgecolor="white",
                )
                ax.text(
                    r_x,
                    t_y - 1.8,
                    f"🚜{cs}",
                    color="#ffffff",
                    fontsize=6.5,
                    ha="center",
                    fontweight="bold",
                )

        ax.set_xlim(0, 11)
        ax.set_ylim(-13, 7)

    # 3. 항로/하늘 ACC 레이더
    else:
        ax.set_title(
            "[En-Route Area Control Radar (RKRR Sector)]",
            color="#a855f7",
            fontsize=8,
            fontweight="bold",
        )

        for ring in [10, 20, 30]:
            circle = plt.Circle(
                (5.5, 20),
                ring,
                color="#a855f7",
                fill=False,
                linestyle=":",
                linewidth=0.8,
                alpha=0.4,
            )
            ax.add_patch(circle)

        for wp_name, wx, wy in WAYPOINTS:
            ax.scatter(wx, wy, color="#c084fc", marker="D", s=30)
            ax.text(
                wx + 0.3,
                wy,
                f"◆ {wp_name}",
                color="#c084fc",
                fontsize=6.5,
                fontweight="bold",
            )

        for p in st.session_state.planes:
            phase = p.get("phase")
            if phase in ["ENROUTE_CLIMB", "ENROUTE_INBOUND"]:
                cs = p["callsign"]
                alt = p.get("altitude", 24000)
                r_x = (abs(hash(cs)) % 8) + 1.5
                r_y = (abs(hash(cs * 2)) % 25) + 8

                p_marker = "^" if phase == "ENROUTE_CLIMB" else "v"
                p_color = "#a855f7" if phase == "ENROUTE_CLIMB" else "#38bdf8"

                ax.plot(r_x, r_y, marker=p_marker, color=p_color, markersize=9)
                ax.plot(
                    [r_x, r_x + 1],
                    [r_y, r_y + 1],
                    color=p_color,
                    linewidth=1.0,
                )
                ax.text(
                    r_x + 1.2,
                    r_y + 1,
                    f"✈️{cs}\nFL{int(alt/100):03d}",
                    color="#ffffff",
                    fontsize=6.5,
                    fontweight="bold",
                    bbox=dict(
                        boxstyle="round,pad=0.2",
                        facecolor="#030712",
                        edgecolor=p_color,
                        lw=0.5,
                    ),
                )

        ax.set_xlim(-1, 12)
        ax.set_ylim(-2, 42)

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
        "👋 대규모 고밀도 관제 모드가 활성화되었습니다. 상단 탭으로 3개 섹터를 전환하며 관리할 수 있습니다."
    )
    if st.button(
        "🚀 통합 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 대시보드 상단 요약
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📊 현재 관제 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("☁️ 항로 이양 성공", f"{st.session_state.handoff_count}대")
    m5.metric("✈️ 관리 항공기", f"{len(st.session_state.planes)}대 / 24대")

    bar_c1, bar_c2 = st.columns([3, 1])
    with bar_c1:
        st.radio(
            "📍 관제 구역 선택 (선택 시 화면 100% 고정 전환)",
            [
                "📡 1. 접근/활주로 관제",
                "🚜 2. 지상/게이트 관제",
                "☁️ 3. 항로/하늘 관제",
            ],
            key="active_sector",
            horizontal=True,
        )
    with bar_c2:
        st.session_state.ai_auto_pilot = st.toggle(
            "🤖 AI 자동 관제 지원", value=st.session_state.ai_auto_pilot
        )

    st.divider()

    col_left, col_mid, col_right = st.columns([1.2, 1.1, 0.9])
    now = time.time()
    current_sector = st.session_state.active_sector

    # ----------------------------------------------------
    # [좌측 열] 섹터별 조작 제어 패널
    # ----------------------------------------------------
    with col_left:
        # SECTOR 1: 접근 / 활주로 관제
        if "1. 접근" in current_sector:
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

                if status in ["접근 요청 중", "상공 대기 중"]:
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
                                now + 7.0
                            )
                            add_log(
                                "APPROACH",
                                f"🛬 [{p['callsign']}] {sel_rwy} 착륙 접근 허가",
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
                    add_log(
                        "APPROACH",
                        f"🛫 [{p['callsign']}] 활주로 이륙 가속 허가",
                    )
                    st.rerun()

        # SECTOR 2: 지상 / 게이트 관제
        elif "2. 지상" in current_sector:
            st.subheader("🚜 지상/게이트 관제 섹터")

            taxi_gate_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "TAXI_TO_GATE"
            ]
            at_gate_list = [
                p for p in st.session_state.planes if p.get("phase") == "AT_GATE"
            ]
            taxi_rwy_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "TAXI_TO_RWY"
            ]

            st.caption(f"🛬 착륙 후 게이트 이동 지시 ({len(taxi_gate_list)}대)")
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
                                "🚜 게이트 이동",
                                key=f"taxig_{p['callsign']}",
                                use_container_width=True,
                            ):
                                p["assigned_gate"] = sel_g
                                p["status"] = "게이트 이동 중"
                                st.session_state.gates_occupied[sel_g] = p[
                                    "callsign"
                                ]
                                add_log(
                                    "GROUND",
                                    f"🚜 [{p['callsign']}] {sel_g} 유도로 이동 지시",
                                )
                                st.rerun()

            st.divider()
            st.caption(f"🛫 게이트 푸시백 및 활주로 이동 ({len(at_gate_list)}대)")
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
                        "🚜 활주로 이동",
                        key=f"push_{p['callsign']}",
                        use_container_width=True,
                    ):
                        st.session_state.gates_occupied[
                            p["assigned_gate"]
                        ] = None
                        p["phase"] = "TAXI_TO_RWY"
                        p["status"] = "활주로 이동 중"
                        p["assigned_runway"] = sel_rwy
                        add_log(
                            "GROUND",
                            f"🚜 [{p['callsign']}] 푸시백 완료 ➔ {sel_rwy} 이동",
                        )
                        st.rerun()

            if taxi_rwy_list:
                st.caption(
                    f"🚜 유도로 이동 중인 비행기 ({len(taxi_rwy_list)}대)"
                )
                for p in taxi_rwy_list:
                    st.caption(
                        f"🟡 [{p['callsign']}] ➔ {p.get('assigned_runway')} 유도로 이동 중..."
                    )

        # SECTOR 3: 항로 / 하늘 관제
        else:
            st.subheader("☁️ 항로/하늘 관제 섹터")

            enroute_climb_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "ENROUTE_CLIMB"
            ]
            enroute_inbound_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "ENROUTE_INBOUND"
            ]

            st.caption(
                f"📡 상승기 타 ACC 관제소 이양 대기 ({len(enroute_climb_list)}대)"
            )
            for p in enroute_climb_list:
                st.markdown(
                    f"""
                    <div class="enroute-card">
                        <b>✈️ {p['callsign']}</b> | 고도: <b style="color:#a855f7;">FL{int(p.get('altitude',14000)/100)}</b><br>
                        이양 센터: <b>{p['assigned_center']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"📡 {p['assigned_center']} 이양",
                    key=f"hand_{p['callsign']}",
                    use_container_width=True,
                ):
                    p["status"] = "관제 이양 완료"
                    st.session_state.handoff_count += 1
                    st.session_state.score += 15
                    add_log(
                        "ENROUTE",
                        f"📡 [{p['callsign']}] {p['assigned_center']} 이양 완료",
                    )
                    st.rerun()

            st.divider()
            st.caption(
                f"☁️ 영공 진입 항공기 접근구역 이관 ({len(enroute_inbound_list)}대)"
            )
            for p in enroute_inbound_list:
                st.markdown(
                    f"""
                    <div class="arr-card">
                        <b>✈️ {p['callsign']}</b> | 고도: <b style="color:#38bdf8;">FL{int(p.get('altitude',28000)/100)}</b><br>
                        출발지: <b>{p['origin']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"📡 접근 관제구역(Sector 1)으로 이관",
                    key=f"inbound_{p['callsign']}",
                    use_container_width=True,
                ):
                    p["phase"] = "APPROACH"
                    p["status"] = "접근 요청 중"
                    p["distance"] = 35.0
                    add_log(
                        "ENROUTE",
                        f"📡 [{p['callsign']}] 접근 관제구역(Sector 1) 하강 이관 완료",
                    )
                    st.rerun()

    # ----------------------------------------------------
    # [중앙 열] 📡 섹터 전용 레이더 스코프
    # ----------------------------------------------------
    with col_mid:
        st.subheader("📡 섹터 전용 레이더 스코프")
        render_sector_specific_radar()

    # ----------------------------------------------------
    # [우측 열] 🔄 섹터 맞춤형 현황판 & 독립 로그
    # ----------------------------------------------------
    with col_right:
        if "1. 접근" in current_sector:
            st.subheader("🛣️ 활주로 실시간 상태 (10개)")

            disp_rwys = RUNWAY_LIST.copy()
            if st.session_state.emg_runway_open:
                disp_rwys.append("EMG-01")

            rwy_cols = st.columns(2)
            for idx, r_name in enumerate(disp_rwys):
                busy_until = st.session_state.runways_busy_until.get(
                    r_name, 0.0
                )
                remaining_sec = max(0.0, busy_until - now)

                with rwy_cols[idx % 2]:
                    if remaining_sec > 0:
                        st.markdown(
                            f"""
                            <div class="info-card" style="border-color:#ef4444; background-color:#2a1215;">
                                <b style="color:#f87171;">🔴 {r_name}</b><br><small>{remaining_sec:.1f}초 점유</small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button(
                            f"🧹 비우기",
                            key=f"clear_{r_name}",
                            use_container_width=True,
                        ):
                            st.session_state.runways_busy_until[r_name] = 0.0
                            add_log(
                                "APPROACH",
                                f"🧹 [{r_name}] 활주로 강제 비우기 완료",
                            )
                            st.rerun()
                    else:
                        st.markdown(
                            f"""
                            <div class="info-card" style="border-color:#10b981; background-color:#062319;">
                                <b style="color:#34d399;">🟢 {r_name}</b><br><small>즉시 사용 가능</small>
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
                    add_log(
                        "APPROACH",
                        "🚨 [비상 활주로] EMG-01 활주로가 개설되었습니다!",
                    )
                    st.rerun()

        elif "2. 지상" in current_sector:
            st.subheader("🅿️ 게이트 주기 현황 (8개)")
            g_cols = st.columns(2)
            for idx, g_name in enumerate(GATES):
                occ = st.session_state.gates_occupied[g_name]
                with g_cols[idx % 2]:
                    if occ:
                        st.markdown(
                            f"""
                            <div class="info-card" style="border-color:#ef4444; background-color:#2a1215;">
                                <b style="color:#f87171;">🔴 {g_name}</b><br><small>{occ}</small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="info-card" style="border-color:#10b981; background-color:#062319;">
                                <b style="color:#34d399;">🟢 {g_name}</b><br><small>빈 게이트</small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        else:
            st.subheader("📡 인근 ACC 관제센터 채널")
            for center in CENTERS:
                st.markdown(
                    f"""
                    <div class="info-card" style="border-color:#a855f7; background-color:#1a0f2e;">
                        <b style="color:#c084fc;">📡 {center}</b><br><small>VHF 124.50 MHz [정상]</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.caption("◆ 공역 주요 웨이포인트(Fixes)")
            wp_cols = st.columns(2)
            for idx, (wp_name, wx, wy) in enumerate(WAYPOINTS):
                with wp_cols[idx % 2]:
                    st.markdown(
                        f"""
                        <div class="info-card">
                            <b style="color:#38bdf8;">◆ {wp_name}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.caption("📜 섹터 전용 교신 로그")
        sec_code = (
            "APPROACH"
            if "1. 접근" in current_sector
            else ("GROUND" if "2. 지상" in current_sector else "ENROUTE")
        )
        filtered_logs = [
            l["text"]
            for l in st.session_state.logs
            if l.get("sector") in [sec_code, "ALL"]
        ]

        for log_text in reversed(filtered_logs[-5:]):
            st.caption(log_text)

    time.sleep(0.4)
    st.rerun()
