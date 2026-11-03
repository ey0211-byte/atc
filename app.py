import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 고밀도 ATC 레이더 인터페이스 스타일
# ==========================================
st.set_page_config(
    page_title="ATC 관제탑 통합 실시간 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* 앱 전체 어두운 네이비 배경 */
    .stApp {
        background-color: #050811 !important;
        color: #e2e8f0 !important;
    }
    
    /* 컴팩트 가독성 버튼 */
    div.stButton > button {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #475569 !important;
        font-weight: bold !important;
        font-size: 11px !important;
        padding: 3px 5px !important;
        min-height: 26px !important;
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

    /* 파일럿 요구사항 메시지 박스 */
    .msg-box {
        background-color: #0d1527;
        border: 2px solid #38bdf8;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 12px;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
    }
    .msg-title {
        color: #38bdf8;
        font-size: 13px;
        font-weight: bold;
        margin-bottom: 6px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 4px;
    }
    .msg-item {
        font-size: 11px;
        margin-bottom: 4px;
        color: #f1f5f9;
    }

    /* 카드 스타일 */
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

    /* 상세정보 카드 */
    .detail-card {
        background-color: #0f172a;
        border: 1px solid #38bdf8;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }

    /* 활주로 미니 카드 */
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

    .badge-danger { background-color: #dc2626; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-warn { background-color: #d97706; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: white; padding: 1px 4px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 변수 초기화
# ==========================================
RUNWAY_LIST = [f"RWY {i:02d}" for i in range(1, 11)]

AIRPORTS = [
    "RKSI (인천)",
    "RKSS (김포)",
    "RKPK (김해)",
    "RJTT (도쿄)",
    "VHHH (홍콩)",
    "ZBAA (베이징)",
    "KLAX (LA)",
    "EGLL (런던)",
]

REQ_ARR_LIST = [
    ("🚨 [비상] 기내 심장마비 응급 환자 발생! 비상 착륙 요청", "EMERGENCY"),
    ("⚡ [우선] 잔여 연료 저하 경고! 신속 착륙 요청", "PRIORITY"),
    ("💨 [기상] 난기류 조우로 인한 고도 하강 및 착륙 요청", "PRIORITY"),
    ("✅ [정상] 표준 접근 절차 준수 중", "NORMAL"),
]

REQ_DEP_LIST = [
    ("⚡ [우선] 연결편 지연으로 인한 조기 이륙 요청", "PRIORITY"),
    ("👥 [승객] 전 승객 탑승 완료, 신속 이륙 허가 요청", "PRIORITY"),
    ("🔥 [점검] 엔진 정밀 점검 필요로 이륙 순서 연기 요청", "PRIORITY"),
    ("✅ [정상] 지상 유도로 대기 완료", "NORMAL"),
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
if "selected_target" not in st.session_state:
    st.session_state.selected_target = None
if "last_tick_time" not in st.session_state:
    st.session_state.last_tick_time = time.time()
if "last_spawn_time" not in st.session_state:
    st.session_state.last_spawn_time = time.time()


# ==========================================
# 3. 비행기 생성 및 실시간 관제 로직
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
            passengers = random.randint(110, 360)
            origin = random.choice(AIRPORTS)

            if category == "ARR":
                req_text, req_level = random.choice(REQ_ARR_LIST)
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": origin,
                        "fuel": float(random.randint(45, 90)),
                        "distance": float(random.randint(16, 36)),
                        "delay": 0.0,
                        "request": req_text,
                        "req_level": req_level,
                        "status": "착륙 요청 중",
                        "assigned_runway": None,
                    }
                )
            else:
                req_text, req_level = random.choice(REQ_DEP_LIST)
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "DEP",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": "본 공항 관제구역",
                        "fuel": 100.0,
                        "distance": 0.0,
                        "delay": 0.0,
                        "takeoff_timer": 5.0,
                        "request": req_text,
                        "req_level": req_level,
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
    st.session_state.selected_target = None
    now = time.time()
    st.session_state.runways_busy_until = {r: 0.0 for r in RUNWAY_LIST}
    st.session_state.runways_busy_until["EMG-01"] = 0.0
    st.session_state.last_landed_type = {r: None for r in RUNWAY_LIST}
    st.session_state.last_landed_type["EMG-01"] = None
    st.session_state.last_tick_time = now
    st.session_state.last_spawn_time = now
    st.session_state.logs = [
        "🚨 [관제 업무 개시] 실시간 파일럿 교신 및 레이더 타겟 모니터링이 가동되었습니다."
    ]

    for _ in range(8):
        spawn_plane()


def update_realtime_engine():
    """실시간 기름 소모 (5초당 2.5% 소모 = 초당 0.5%)"""
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
                    f"🛬 [{p['callsign']}] {p.get('assigned_runway')} 안전 착륙 완료!"
                )
                if st.session_state.selected_target == p["callsign"]:
                    st.session_state.selected_target = None
                continue

        # 2. 이륙 가속 중
        elif status == "이륙 가속 중":
            p["takeoff_timer"] -= dt
            if p["takeoff_timer"] <= 0:
                st.session_state.tookoff_count += 1
                st.session_state.score += 15
                st.session_state.logs.append(
                    f"🛫 [{p['callsign']}] {p.get('assigned_runway')} 성공적 이륙 완료!"
                )
                if st.session_state.selected_target == p["callsign"]:
                    st.session_state.selected_target = None
                continue

        # 3. 상공 착륙 대기 비행기 (연료 감소)
        elif cat == "ARR":
            p["fuel"] -= 0.5 * dt

            # 🔴 [임무 실패] 단 1대라도 기름 0% 도달 시 게임 오버
            if p["fuel"] <= 0:
                p["fuel"] = 0.0
                st.session_state.game_over = True
                st.session_state.game_over_reason = f"💥 [{p['callsign']}] 비행기의 연료가 0%에 도달하여 추락했습니다! (관제 실패)"
                st.session_state.logs.append(st.session_state.game_over_reason)
                return

        # 4. 지상 이륙 대기 비행기
        elif cat == "DEP":
            p["delay"] += dt

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # 5초마다 신규 비행기 유입 (최대 12대 유지)
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

    if last_type and "대형" in last_type and "대형" not in plane.get("type", ""):
        occupancy_seconds += 3.0
        st.toast(
            f"⚠️ [{target_runway}] 선행 대형기로 인해 활주로 점유 +3초",
            icon="⚠️",
        )

    st.session_state.runways_busy_until[target_runway] = now + occupancy_seconds
    st.session_state.last_landed_type[target_runway] = plane.get("type")
    plane["assigned_runway"] = target_runway

    if plane.get("category") == "ARR":
        plane["status"] = "착륙 접근 중"
        log_msg = f"🛬 [착륙 승인] {callsign} ➔ {target_runway}"
    else:
        plane["status"] = "이륙 가속 중"
        plane["takeoff_timer"] = 5.0
        log_msg = f"🛫 [이륙 승인] {callsign} ➔ {target_runway}"

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
        log_msg = f"🛑 [착륙 거절] {callsign} 상공 대기 궤도 선회 지시"
    else:
        plane["status"] = "지상 대기 중"
        log_msg = f"🛑 [이륙 거절] {callsign} 게이트 대기 지시"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🛑")


def force_clear_runway(runway_name):
    st.session_state.runways_busy_until[runway_name] = 0.0
    log_msg = f"🧹 [강제 비우기] {runway_name} 활주로가 비상 개방되었습니다."
    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🧹")


# ==========================================
# 4. 고품질 레이더 그래픽 렌더링 함수
# ==========================================
def render_high_quality_radar():
    """우측 미니 관제 레이더 스코프 (겹침 방지 및 타겟 타겟팅 링 적용)"""
    fig, ax = plt.subplots(figsize=(4.5, 4.0))
    fig.patch.set_facecolor("#050811")
    ax.set_facecolor("#050811")

    # 활주로 가이드선 및 녹색 활주로 그리기
    ax.axhline(0, color="#1e293b", linestyle="-", linewidth=2.5)

    for i in range(1, 11):
        ax.plot([i, i], [0, -2.5], color="#00ff66", linewidth=4.5, alpha=0.9)
        ax.text(
            i,
            -5.5,
            f"R{i:02d}",
            color="#00ff66",
            fontsize=6.5,
            ha="center",
            fontweight="bold",
        )

    if st.session_state.emg_runway_open:
        ax.plot([11, 11], [0, -2.5], color="#ff3344", linewidth=4.5, alpha=0.9)
        ax.text(
            11,
            -5.5,
            "EMG",
            color="#ff3344",
            fontsize=6.5,
            ha="center",
            fontweight="bold",
        )

    # 레이더 격자 동심선 (10NM ~ 40NM)
    for dist in [10, 20, 30, 40]:
        ax.axhline(
            dist, color="#00f3ff", linestyle="--", linewidth=0.6, alpha=0.25
        )

    # 비행기 표시 및 겹침 방지 오프셋 알고리즘
    for idx, p in enumerate(st.session_state.planes):
        cat = p.get("category", "ARR")
        status = p.get("status", "")
        cs = p.get("callsign", "")
        fuel = p.get("fuel", 50.0)
        dist = p.get("distance", 0.0)
        req_lvl = p.get("req_level", "NORMAL")

        # 활주로 위치 지정
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

        # 색상 선별
        if req_lvl == "EMERGENCY" or fuel <= 20:
            p_color = "#ff3344"
            badge = "🚨"
        elif req_lvl == "PRIORITY":
            p_color = "#ff9900"
            badge = "⚡"
        elif status in ["착륙 접근 중", "이륙 가속 중"]:
            p_color = "#00ff66"
            badge = "✈️"
        else:
            p_color = "#00f3ff"
            badge = "✈️"

        # 글자 겹침 방지 오프셋 계산 (좌우 및 위아래 교차 번갈아 배치)
        x_offset = 0.25 if (idx % 2 == 0) else -1.65
        y_offset = 0.6 if (idx % 3 == 0) else (-0.6 if idx % 3 == 1 else 0.0)

        if cat == "ARR":
            ax.plot(r_x, dist, marker="v", color=p_color, markersize=7)

            # 선택된 비행기 🎯 조준 링 표시
            if st.session_state.selected_target == cs:
                circle = plt.Circle(
                    (r_x, dist),
                    1.8,
                    color="#00f3ff",
                    fill=False,
                    linestyle="-",
                    linewidth=2.0,
                )
                ax.add_patch(circle)
                ax.plot(r_x, dist, marker="o", color="#00f3ff", markersize=10)

            ax.text(
                r_x + x_offset,
                dist + y_offset,
                f"{badge}{cs}\n({fuel:.0f}%)",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
            )

            # 착륙 접근 유도 가이드 라인
            if status == "착륙 접근 중":
                ax.plot(
                    [r_x, r_x],
                    [dist, 0],
                    color=p_color,
                    linestyle=":",
                    linewidth=1.3,
                    alpha=0.85,
                )

        else:
            dep_y = -1.2 if status != "이륙 가속 중" else 6.0
            ax.plot(r_x, dep_y, marker="^", color=p_color, markersize=7)

            if st.session_state.selected_target == cs:
                circle = plt.Circle(
                    (r_x, dep_y),
                    1.8,
                    color="#00f3ff",
                    fill=False,
                    linestyle="-",
                    linewidth=2.0,
                )
                ax.add_patch(circle)

            ax.text(
                r_x + x_offset,
                dep_y + y_offset,
                f"🛫{cs}",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
            )

    max_x = 12 if st.session_state.emg_runway_open else 11
    ax.set_xlim(0, max_x)
    ax.set_ylim(-8, 42)
    ax.axis("off")

    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ==========================================
# 5. 실시간 엔진 업데이트 수행
# ==========================================
update_realtime_engine()


# ==========================================
# 6. 메인 UI 화면 구성
# ==========================================
st.title("⚡ ATC 실시간 대규모 이착륙 통합 관제 시뮬레이터")

# 🔴 [임무 실패 / GAME OVER 화면]
if st.session_state.game_over:
    st.error("💥 [GAME OVER / 관제 실패]")
    st.subheader(st.session_state.game_over_reason)
    st.write(
        f"**최종 기록:** 착륙 성공 {st.session_state.landed_count}대 | 이륙 성공 {st.session_state.tookoff_count}대 | 점수: {st.session_state.score}점"
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
        "👋 오른쪽 레이더에서 타겟 비행기를 선택하면 세부 정보(탑승자 수, 출발지 등)가 표시됩니다."
    )
    if st.button(
        "🚀 비상 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 관제탑 상단 대시보드
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 현재 관제 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("✈️ 총 수용 항공기", f"{len(st.session_state.planes)}대")

    st.divider()

    # 메인 2열 화면 (좌측: 파일럿 요청함 및 관제 조작 / 우측: 레이더 & 세부정보)
    col_left, col_right = st.columns([1.65, 1.15])

    available_runways = RUNWAY_LIST.copy()
    if st.session_state.emg_runway_open:
        available_runways.append("EMG-01")

    # ----------------------------------------------------
    # [좌측] 📡 파일럿 실시간 요구사항 센터 & 착/이륙 제어
    # ----------------------------------------------------
    with col_left:
        # 1. 파일럿 요구사항 실시간 메시지 박스
        st.markdown(
            """
        <div class="msg-box">
            <div class="msg-title">📡 파일럿 실시간 교신 및 긴급 요구사항 수신함</div>
        """,
            unsafe_allow_html=True,
        )

        req_planes = [
            p
            for p in st.session_state.planes
            if p.get("req_level") in ["EMERGENCY", "PRIORITY"]
        ]
        if not req_planes:
            st.markdown(
                '<div class="msg-item">✅ 현재 긴급 요구사항을 보낸 비행기가 없습니다.</div>',
                unsafe_allow_html=True,
            )
        else:
            for rp in req_planes[:3]:
                st.markdown(
                    f'<div class="msg-item"><b>[{rp["callsign"]}]</b> {rp["request"]}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

        # 2. 착륙 및 이륙 비행기 제어 구역
        arr_planes = [
            p for p in st.session_state.planes if p.get("category") == "ARR"
        ]
        dep_planes = [
            p for p in st.session_state.planes if p.get("category") == "DEP"
        ]

        sub_col1, sub_col2 = st.columns(2)

        # 🛬 착륙 요청 비행기
        with sub_col1:
            st.subheader(f"🛬 착륙 관제 ({len(arr_planes)}대)")

            for p in arr_planes:
                status = p.get("status", "착륙 요청 중")
                fuel_val = max(0.0, p.get("fuel", 0.0))

                if p.get("req_level") == "EMERGENCY" or fuel_val <= 20.0:
                    badge = '<span class="badge-danger">🚨 위급</span>'
                elif p.get("req_level") == "PRIORITY":
                    badge = '<span class="badge-warn">⚡ 우선</span>'
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

        # 🛫 이륙 요청 비행기
        with sub_col2:
            st.subheader(f"🛫 이륙 관제 ({len(dep_planes)}대)")

            for p in dep_planes:
                status = p.get("status", "이륙 요청 중")
                delay_sec = int(p.get("delay", 0))

                if p.get("req_level") == "PRIORITY":
                    badge = '<span class="badge-warn">⚡ 우선</span>'
                elif status == "이륙 가속 중":
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
    # [우측] 🎯 미니 레이더 지도 및 선택 항공기 세부 정보
    # ----------------------------------------------------
    with col_right:
        # 1. 타겟 선택 드롭다운
        all_callsigns = [p["callsign"] for p in st.session_state.planes]
        target_options = ["선택 안 함"] + all_callsigns

        selected_cs = st.selectbox(
            "🎯 레이더 타겟 항공기 조회 (선택 시 링 표시)",
            target_options,
            index=(
                target_options.index(st.session_state.selected_target)
                if st.session_state.selected_target in target_options
                else 0
            ),
        )
        st.session_state.selected_target = (
            selected_cs if selected_cs != "선택 안 함" else None
        )

        # 2. 선택된 비행기 상세정보 카드
        if st.session_state.selected_target:
            target_plane = next(
                (
                    p
                    for p in st.session_state.planes
                    if p["callsign"] == st.session_state.selected_target
                ),
                None,
            )
            if target_plane:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <h4 style="margin:0 0 5px 0; color:#38bdf8;">✈️ {target_plane['callsign']} 정보</h4>
                        <div style="font-size:12px; color:#f1f5f9; line-height:1.5;">
                            <b>기종:</b> {target_plane['type']}<br>
                            <b>👥 탑승자 수:</b> {target_plane['passengers']}명<br>
                            <b>📍 출발지:</b> {target_plane['origin']}<br>
                            <b>⛽ 잔여 연료:</b> {target_plane['fuel']:.1f}%<br>
                            <b>💬 파일럿 요청:</b> <span style="color:#f59e0b;">{target_plane['request']}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # 3. 레이더 시각화 렌더링
        st.subheader("📡 관제 레이더 스코프")
        render_high_quality_radar()

        # 4. 활주로 상태 (10개)
        st.subheader("🛣️ 활주로 현황")
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
                "🚨 01E 비상 활주로 추가 개설",
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
        for log in reversed(st.session_state.logs[-5:]):
            st.caption(log)

    # 0.4초 간격 자동 재실행
    time.sleep(0.4)
    st.rerun()
