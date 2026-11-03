import math
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 초고대비 순백색(White) 폰트 & Pro ATC 스타일
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

    /* 모든 텍스트 글자색 흰색 강제 고정 */
    p, span, div, label, h1, h2, h3, h4, h5, h6, caption {
        color: #ffffff !important;
    }

    /* 스트림릿 버튼 강제 스타일 (글자색 100% 흰색 유지) */
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

    /* 메시지 박스 */
    .msg-box {
        background-color: #090d16;
        border: 1px solid #0284c7;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }
    .msg-title {
        color: #38bdf8 !important;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 4px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 2px;
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

    /* 게이트 현황 박스 */
    .gate-box {
        background-color: #0b1329;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 5px;
        text-align: center;
        font-size: 10px;
        margin-bottom: 4px;
    }

    .stProgress > div > div > div > div { height: 4px !important; }

    .badge-danger { background-color: #dc2626; color: #ffffff !important; padding: 1px 4px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-warn { background-color: #d97706; color: #ffffff !important; padding: 1px 4px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: #ffffff !important; padding: 1px 4px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 기본 데이터 초기화
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


# ==========================================
# 3. 비행기 스폰 및 로직
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

            if category == "ARR":
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "phase": "APPROACH",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": random.choice(AIRPORTS),
                        "fuel": float(random.randint(50, 90)),
                        "distance": float(random.randint(18, 36)),
                        "delay": 0.0,
                        "status": "접근 요청 중",
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
    st.session_state.logs = [
        "🚨 [통합 관제 개시] 섹터별 실시간 전용 레이더 및 선명한 가독성 모드가 가동됩니다."
    ]

    for _ in range(8):
        spawn_plane()


# ==========================================
# 4. 실시간 엔진 및 AI 보조 관제
# ==========================================
def run_ai_auto_controller(now):
    if not st.session_state.ai_auto_pilot:
        return

    # 1. 접근/활주로 AI 관제 (연료 부족 비행기 착륙 지원)
    for p in st.session_state.planes:
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
                        st.session_state.logs.append(
                            f"🤖 [AI 착륙 승인] {p['callsign']} ➔ {r} (연료 긴급)"
                        )
                        break

        # 2. 지상 관제 AI 지원 (게이트 자동 유도)
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

        # 3. 항로 관제 AI 지원 (자동 이양)
        elif (
            p["phase"] == "ENROUTE_CLIMB"
            and p["status"] == "관제권 이양(Handoff) 요청"
        ):
            p["status"] = "관제 이양 완료"
            st.session_state.handoff_count += 1
            st.session_state.score += 15
            st.session_state.logs.append(
                f"🤖 [AI 항로 관제] {p['callsign']} ➔ {p['assigned_center']} 이양 완료"
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
                    st.session_state.logs.append(
                        f"🛬 [{p['callsign']}] 활주로 착륙 완료! (지상 관제 이관)"
                    )
            else:
                p["fuel"] -= 0.5 * dt
                if p["fuel"] <= 0:
                    st.session_state.game_over = True
                    st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                    st.session_state.logs.append(
                        st.session_state.game_over_reason
                    )
                    return

        # B. 지상 이동 단계
        elif phase == "TAXI_TO_GATE":
            if status == "게이트 이동 중":
                p["delay"] += dt
                if p["delay"] >= 5.0:
                    p["phase"] = "PARKED"
                    p["status"] = "게이트 주기 완료"
                    st.session_state.score += 20
                    st.session_state.logs.append(
                        f"🅿️ [{p['callsign']}] {p['assigned_gate']} 주기 완료!"
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
                    st.session_state.logs.append(
                        f"🛫 [{p['callsign']}] 이륙 성공! (항로 관제 이관)"
                    )

        # C. 항로 이양 단계
        elif phase == "ENROUTE_CLIMB":
            if status == "관제 이양 완료":
                continue
            p["altitude"] = p.get("altitude", 14000) + int(1000 * dt)

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes
    run_ai_auto_controller(now)

    if (
        now - st.session_state.last_spawn_time > 5.0
        and len(st.session_state.planes) < 12
    ):
        spawn_plane()
        st.session_state.last_spawn_time = now


# ==========================================
# 5. 📡 섹터별 3가지 전용 레이더 시각화 렌더러
# ==========================================
def render_sector_specific_radar():
    """선택된 섹터에 따라 완전히 다른 디자인의 레이더 화면 출력"""
    sector = st.session_state.active_sector

    fig, ax = plt.subplots(figsize=(5.2, 4.8), dpi=130)
    fig.patch.set_facecolor("#030712")
    ax.set_facecolor("#030712")

    # ----------------------------------------------------
    # TYPE 1: 📡 [접근/활주로 관제 레이더] (활주로 + 접근 궤도)
    # ----------------------------------------------------
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

        # 접근 중인 비행기 표기
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

    # ----------------------------------------------------
    # TYPE 2: 🚜 [지상/게이트 ASDE 레이더] (활주로X -> 터미널 + 게이트 + 유도로)
    # ----------------------------------------------------
    elif "2. 지상" in sector:
        ax.set_title(
            "[ASDE Ground Movement Radar Scope]",
            color="#38bdf8",
            fontsize=8,
            fontweight="bold",
        )

        # 터미널 건물 그리기
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

        # Gate 01 ~ 08 표시 (터미널 아래쪽)
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

        # 유도로 (Taxiways A & B)
        ax.axhline(-6, color="#eab308", linestyle="-.", linewidth=1.5)
        ax.text(0.5, -5.5, "TAXIWAY A", color="#eab308", fontsize=6)

        ax.axhline(-10, color="#eab308", linestyle="-.", linewidth=1.5)
        ax.text(0.5, -9.5, "TAXIWAY B", color="#eab308", fontsize=6)

        # 지상 이동 비행기 표기
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

    # ----------------------------------------------------
    # TYPE 3: ☁️ [항로/하늘 ACC 레이더] (지상/활주로 없음 -> 고고도 하늘 공역)
    # ----------------------------------------------------
    else:
        ax.set_title(
            "[En-Route Area Control Radar (RKRR Sector)]",
            color="#a855f7",
            fontsize=8,
            fontweight="bold",
        )

        # 대공역 반경 동심원 (50NM, 100NM, 150NM)
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

        # 웨이포인트(Waypoints) 표기
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

        # 고고도 항로 상승/이양 비행기 표기
        for p in st.session_state.planes:
            if p.get("phase") == "ENROUTE_CLIMB":
                cs = p["callsign"]
                alt = p.get("altitude", 14000)
                r_x = (abs(hash(cs)) % 8) + 1.5
                r_y = (abs(hash(cs * 2)) % 25) + 8

                ax.plot(r_x, r_y, marker="^", color="#a855f7", markersize=9)
                ax.plot(
                    [r_x, r_x + 1],
                    [r_y, r_y + 1],
                    color="#a855f7",
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
                        edgecolor="#a855f7",
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
        "👋 상단 라디오 버튼으로 섹터를 바꾸면 관제 레이더 화면도 함께 실시간 전환됩니다."
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
    m5.metric("✈️ 관리 항공기", f"{len(st.session_state.planes)}대")

    # 관제 구역 선택 바 & AI 옵션
    bar_c1, bar_c2 = st.columns([3, 1])
    with bar_c1:
        st.session_state.active_sector = st.radio(
            "📍 관제 구역 선택 (선택 시 레이더 자동 변경)",
            [
                "📡 1. 접근/활주로 관제",
                "🚜 2. 지상/게이트 관제",
                "☁️ 3. 항로/하늘 관제",
            ],
            horizontal=True,
        )
    with bar_c2:
        st.session_state.ai_auto_pilot = st.toggle(
            "🤖 AI 자동 관제 지원", value=st.session_state.ai_auto_pilot
        )

    st.divider()

    col_left, col_mid, col_right = st.columns([1.2, 1.1, 0.9])

    # ----------------------------------------------------
    # [좌측 열] 활성 섹터별 조작 제어 패널
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
                                "🚜 게이트 이동",
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
            st.caption(f"🛫 게이트 푸시백 요청 ({len(at_gate_list)}대)")
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
                        st.rerun()

        # SECTOR 3: 항로 / 하늘 관제
        else:
            st.subheader("☁️ 항로/하늘 관제 섹터")

            enroute_list = [
                p
                for p in st.session_state.planes
                if p.get("phase") == "ENROUTE_CLIMB"
            ]
            st.caption(f"📡 고고도 항로 관제 이양 대기 ({len(enroute_list)}대)")

            for p in enroute_list:
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
                    st.session_state.logs.append(
                        f"📡 [{p['callsign']}] {p['assigned_center']} 이양 완료!"
                    )
                    st.rerun()

    # ----------------------------------------------------
    # [중앙 열] 📡 섹터 맞춤형 실시간 레이더 화면
    # ----------------------------------------------------
    with col_mid:
        st.subheader("📡 섹터 맞춤형 실시간 레이더")
        render_sector_specific_radar()

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
