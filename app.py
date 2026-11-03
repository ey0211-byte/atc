import math
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 초고밀도 Pro ATC 대시보드 테마 스타일
# ==========================================
st.set_page_config(
    page_title="Pro ATC 관제탑 실시간 통합 시뮬레이터",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* 전체 배경: 프로 관제탑 어두운 네이비 */
    .stApp {
        background-color: #030712 !important;
        color: #f1f5f9 !important;
    }
    
    /* 컴팩트 고대비 버튼 */
    div.stButton > button {
        background-color: #0f172a !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        font-weight: bold !important;
        font-size: 11px !important;
        padding: 2px 4px !important;
        min-height: 24px !important;
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

    /* 파일럿 요구사항 박스 */
    .msg-box {
        background-color: #090d16;
        border: 1px solid #0284c7;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }
    .msg-title {
        color: #38bdf8;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 4px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 2px;
    }
    .msg-item {
        font-size: 10.5px;
        margin-bottom: 3px;
        color: #e2e8f0;
    }

    /* 카드 스타일 */
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
    .plane-title-arr { font-size: 11.5px !important; font-weight: bold; color: #60a5fa; }
    .plane-title-dep { font-size: 11.5px !important; font-weight: bold; color: #fbbf24; }
    .plane-sub { font-size: 10.5px !important; color: #cbd5e1; }

    /* 상세정보 카드 */
    .detail-card {
        background-color: #0b1329;
        border: 1px solid #38bdf8;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }

    /* 활주로 카드 */
    .runway-card {
        background-color: #090d16;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 3px;
        margin-bottom: 3px;
        text-align: center;
        font-size: 10px;
    }
    .stProgress > div > div > div > div { height: 4px !important; }

    .badge-danger { background-color: #dc2626; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-warn { background-color: #d97706; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-success { background-color: #16a34a; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-arr { background-color: #2563eb; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    .badge-dep { background-color: #b45309; color: white; padding: 1px 3px; font-size: 9.5px; border-radius: 3px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 및 기본 변수
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
    ("🚨 [비상] 기내 응급 환자 발생! 우선 착륙 요청", "EMERGENCY"),
    ("⚡ [우선] 잔여 연료 저하 경고! 신속 착륙 요청", "PRIORITY"),
    ("💨 [기상] 난기류 조우로 인한 고도 하강 요청", "PRIORITY"),
    ("✅ [정상] 표준 접근 절차 진행 중", "NORMAL"),
]

REQ_DEP_LIST = [
    ("⚡ [우선] 연결편 지연으로 인한 조기 이륙 요청", "PRIORITY"),
    ("👥 [승객] 승객 탑승 완료, 이륙 허가 요청", "PRIORITY"),
    ("🔥 [점검] 엔진 정밀 점검으로 이륙 연기 요청", "PRIORITY"),
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
# 3. 비행기 생성 및 실시간 엔진
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
                req_text, req_level = random.choice(REQ_ARR_LIST)
                st.session_state.planes.append(
                    {
                        "callsign": cs,
                        "category": "ARR",
                        "type": ac_type,
                        "passengers": passengers,
                        "origin": origin,
                        "fuel": float(random.randint(45, 90)),
                        "distance": float(random.randint(18, 36)),
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
        "🚨 [관제 업무 개시] Pro ATC 3열 대시보드 레이더 시스템이 작동합니다."
    ]

    for _ in range(8):
        spawn_plane()


def update_realtime_engine():
    """실시간 기름 소모 엔진 (5초당 2.5% = 초당 0.5% 차감)"""
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
                    f"🛫 [{p['callsign']}] {p.get('assigned_runway')} 이륙 상승 완료!"
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
                st.session_state.game_over_reason = f"💥 [{p['callsign']}] 항공기의 연료가 0%가 되어 추락했습니다! (관제 실패)"
                st.session_state.logs.append(st.session_state.game_over_reason)
                return

        # 4. 지상 이륙 대기 비행기
        elif cat == "DEP":
            p["delay"] += dt

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    # 5초마다 신규 항공기 진입 (최대 11대 유지)
    if (
        now - st.session_state.last_spawn_time > 5.0
        and len(st.session_state.planes) < 11
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
            f"⚠️ [{target_runway}] 선행 대형기 와류 영향으로 점유시간 +3초",
            icon="⚠️",
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
        log_msg = f"🛑 [착륙 거절] {callsign} 상공 홀딩 궤도 진입"
    else:
        plane["status"] = "지상 대기 중"
        log_msg = f"🛑 [이륙 거절] {callsign} 유도로 일시 대기"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🛑")


def force_clear_runway(runway_name):
    st.session_state.runways_busy_until[runway_name] = 0.0
    log_msg = f"🧹 [강제 비우기] {runway_name} 활주로가 비상 개방되었습니다."
    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="🧹")


# ==========================================
# 4. Pro ATC 고화질 관제 레이더 스코프
# ==========================================
def render_pro_radar_scope():
    """실제 관제탑 네온 패널 스타일의 고화질(DPI 130) 레이더 스코프"""
    fig, ax = plt.subplots(figsize=(5.2, 5.0), dpi=130)
    fig.patch.set_facecolor("#030712")
    ax.set_facecolor("#030712")

    # 1. 방위각 레이더 방사선 (Heading Spokes)
    for angle in [30, 60, 120, 150]:
        rad = math.radians(angle)
        x_end = 45 * math.cos(rad)
        ax.plot(
            [0, x_end],
            [0, 45],
            color="#1e293b",
            linestyle=":",
            linewidth=0.7,
            alpha=0.6,
        )
        ax.plot(
            [0, -x_end],
            [0, 45],
            color="#1e293b",
            linestyle=":",
            linewidth=0.7,
            alpha=0.6,
        )

    # 2. 레이더 동심 거리선 (10NM, 20NM, 30NM, 40NM)
    for dist in [10, 20, 30, 40]:
        ax.axhline(
            dist, color="#0284c7", linestyle="--", linewidth=0.7, alpha=0.35
        )
        ax.text(
            0.3,
            dist + 0.5,
            f"{dist}NM",
            color="#0284c7",
            fontsize=6,
            alpha=0.6,
            fontweight="bold",
        )

    # 3. 활주로 바닥 및 활주로 선 정밀 표기
    ax.axhline(0, color="#334155", linestyle="-", linewidth=2.0)

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

    if st.session_state.emg_runway_open:
        ax.plot([11, 11], [0, -3.0], color="#ff3344", linewidth=4.0, alpha=0.9)
        ax.text(
            11,
            -6.5,
            "EMG",
            color="#ff3344",
            fontsize=6.5,
            ha="center",
            fontweight="bold",
        )

    # 4. 항공기 블립(Blip) 및 데이터 블록 (리더 라인 적용)
    for idx, p in enumerate(st.session_state.planes):
        cat = p.get("category", "ARR")
        status = p.get("status", "")
        cs = p.get("callsign", "")
        fuel = p.get("fuel", 50.0)
        dist = p.get("distance", 0.0)
        req_lvl = p.get("req_level", "NORMAL")

        # 활주로 위치 계산
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

        # 네온 색상 스키마
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

        # 지능형 겹침 방지 오프셋
        x_off = 0.8 if (idx % 2 == 0) else -2.2
        y_off = 1.2 if (idx % 3 == 0) else (-1.2 if idx % 3 == 1 else 0.0)

        if cat == "ARR":
            # 블립 파수선
            ax.plot(
                r_x,
                dist,
                marker="v",
                color=p_color,
                markersize=8,
                markeredgecolor="white",
                markeredgewidth=0.5,
            )

            # 🎯 선택된 타겟 크로스헤어 박스 (Crosshair Target Reticle)
            if st.session_state.selected_target == cs:
                rect = plt.Rectangle(
                    (r_x - 0.7, dist - 1.2),
                    1.4,
                    2.4,
                    color="#00f3ff",
                    fill=False,
                    linewidth=1.8,
                    linestyle="-",
                )
                ax.add_patch(rect)
                ax.plot(
                    [r_x - 1.2, r_x + 1.2],
                    [dist, dist],
                    color="#00f3ff",
                    linewidth=0.8,
                )
                ax.plot(
                    [r_x, r_x],
                    [dist - 1.8, dist + 1.8],
                    color="#00f3ff",
                    linewidth=0.8,
                )

            # 리더 라인 (데이터 블록 연결 선)
            ax.plot(
                [r_x, r_x + x_off * 0.5],
                [dist, dist + y_off * 0.5],
                color=p_color,
                linewidth=0.8,
                alpha=0.7,
            )

            # 데이터 블록 텍스트
            ax.text(
                r_x + x_off,
                dist + y_off,
                f"{badge}{cs}\nFL{int(dist*10):03d} | {fuel:.0f}%",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="#030712",
                    edgecolor=p_color,
                    alpha=0.7,
                    lw=0.5,
                ),
            )

            # 착륙 접근 유도선
            if status == "착륙 접근 중":
                ax.plot(
                    [r_x, r_x],
                    [dist, 0],
                    color=p_color,
                    linestyle=":",
                    linewidth=1.4,
                    alpha=0.9,
                )

        else:
            dep_y = -1.5 if status != "이륙 가속 중" else 7.0
            ax.plot(
                r_x,
                dep_y,
                marker="^",
                color=p_color,
                markersize=8,
                markeredgecolor="white",
                markeredgewidth=0.5,
            )

            if st.session_state.selected_target == cs:
                rect = plt.Rectangle(
                    (r_x - 0.7, dep_y - 1.2),
                    1.4,
                    2.4,
                    color="#00f3ff",
                    fill=False,
                    linewidth=1.8,
                )
                ax.add_patch(rect)

            ax.text(
                r_x + x_off,
                dep_y + y_off,
                f"🛫{cs}\nDEP-REQ",
                color=p_color,
                fontsize=6.5,
                fontweight="bold",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="#030712",
                    edgecolor=p_color,
                    alpha=0.7,
                    lw=0.5,
                ),
            )

    max_x = 12 if st.session_state.emg_runway_open else 11
    ax.set_xlim(0, max_x)
    ax.set_ylim(-9, 44)
    ax.axis("off")

    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ==========================================
# 5. 실시간 엔진 업데이트
# ==========================================
update_realtime_engine()


# ==========================================
# 6. 한눈에 들어오는 3열 메인 대시보드 레이아웃
# ==========================================
st.title("⚡ Pro ATC 실시간 대규모 통합 관제탑 대시보드")

# 🔴 [임무 실패 / GAME OVER 화면]
if st.session_state.game_over:
    st.error("💥 [GAME OVER / 관제 실패]")
    st.subheader(st.session_state.game_over_reason)
    st.write(
        f"**최종 기록:** 착륙 성공 {st.session_state.landed_count}대 | 이륙 성공 {st.session_state.tookoff_count}대 | 최종 점수: {st.session_state.score}점"
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
    st.info(
        "👋 3열 대시보드로 구성되어 스크롤 없이 한눈에 레이더, 활주로, 파일럿 요청을 제어할 수 있습니다."
    )
    if st.button(
        "🚀 비상 관제 업무 개시", type="primary", use_container_width=True
    ):
        init_game()
        st.rerun()

else:
    # 관제탑 최상단 요약 현황판
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 현재 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("🛫 이륙 성공", f"{st.session_state.tookoff_count}대")
    m4.metric("✈️ 수용 항공기", f"{len(st.session_state.planes)}대")

    st.divider()

    # 3열 완벽 재배열 레이아웃 (좌: 파일럿 교신&관제버튼 / 중: 네온 레이더 / 우: 활주로&타겟카드)
    col1, col2, col3 = st.columns([1.1, 1.25, 0.95])

    available_runways = RUNWAY_LIST.copy()
    if st.session_state.emg_runway_open:
        available_runways.append("EMG-01")

    # ----------------------------------------------------
    # [1열] 📡 파일럿 긴급 요청 수신함 & 🛬 착/이륙 지시 패널
    # ----------------------------------------------------
    with col1:
        # 파일럿 메시지 박스
        st.markdown(
            """
        <div class="msg-box">
            <div class="msg-title">📡 파일럿 교신 및 요구사항 수신함</div>
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

        # 비행기 원클릭 지시 구역
        arr_planes = [
            p for p in st.session_state.planes if p.get("category") == "ARR"
        ]
        dep_planes = [
            p for p in st.session_state.planes if p.get("category") == "DEP"
        ]

        sub1, sub2 = st.columns(2)

        # 착륙 요청
        with sub1:
            st.caption(f"🛬 착륙 요청 ({len(arr_planes)}대)")
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
                            <span class="plane-title-arr">✈️ {p['callsign']}</span>
                            {badge}
                        </div>
                        <div class="plane-sub">연료: <b style="color:#ef4444;">{fuel_val:.1f}%</b> | {max(0.0, p.get('distance',0)):.1f}NM</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.progress(
                    fuel_val / 100.0, text=f"연료: {fuel_val:.1f}%"
                )

                if status in ["착륙 요청 중", "상공 대기 중"]:
                    b1, b2, b3 = st.columns([1.5, 1, 1])
                    with b1:
                        sel_rwy = st.selectbox(
                            "활주로",
                            available_runways,
                            key=f"sel_arr_{p['callsign']}",
                            label_visibility="collapsed",
                        )
                    with b2:
                        if st.button(
                            "✅",
                            key=f"app_{p['callsign']}",
                            use_container_width=True,
                        ):
                            approve_action(p["callsign"], sel_rwy)
                            st.rerun()
                    with b3:
                        if st.button(
                            "🛑",
                            key=f"rej_{p['callsign']}",
                            use_container_width=True,
                        ):
                            reject_action(p["callsign"])
                            st.rerun()
                st.write("")

        # 이륙 요청
        with sub2:
            st.caption(f"🛫 이륙 요청 ({len(dep_planes)}대)")
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
                            <span class="plane-title-dep">✈️ {p['callsign']}</span>
                            {badge}
                        </div>
                        <div class="plane-sub">대기: <b style="color:#f59e0b;">{delay_sec}초 지연</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if status in ["이륙 요청 중", "지상 대기 중"]:
                    b1, b2, b3 = st.columns([1.5, 1, 1])
                    with b1:
                        sel_rwy = st.selectbox(
                            "활주로",
                            available_runways,
                            key=f"sel_dep_{p['callsign']}",
                            label_visibility="collapsed",
                        )
                    with b2:
                        if st.button(
                            "🚀",
                            key=f"app_{p['callsign']}",
                            use_container_width=True,
                        ):
                            approve_action(p["callsign"], sel_rwy)
                            st.rerun()
                    with b3:
                        if st.button(
                            "🛑",
                            key=f"rej_{p['callsign']}",
                            use_container_width=True,
                        ):
                            reject_action(p["callsign"])
                            st.rerun()
                st.write("")

    # ----------------------------------------------------
    # [2열 - 중앙] 📡 메인 Pro ATC 관제 레이더 스코프
    # ----------------------------------------------------
    with col2:
        st.subheader("📡 메인 관제 레이더 스코프")
        render_pro_radar_scope()

    # ----------------------------------------------------
    # [3열 - 우측] 🎯 타겟 세부정보 & 🛣️ 10개 활주로 현황
    # ----------------------------------------------------
    with col3:
        # 타겟 선택 드롭다운
        all_callsigns = [p["callsign"] for p in st.session_state.planes]
        target_options = ["선택 안 함"] + all_callsigns

        selected_cs = st.selectbox(
            "🎯 타겟 비행기 조회 (선택 시 링 표시)",
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

        # 선택 비행기 상세정보
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
                        <h5 style="margin:0 0 4px 0; color:#38bdf8;">✈️ {target_plane['callsign']} 상세정보</h5>
                        <div style="font-size:11px; color:#f1f5f9; line-height:1.4;">
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

        # 활주로 10개 현황
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
                        f"🧹",
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
        st.caption("📜 실시간 관제 교신 로그")
        for log in reversed(st.session_state.logs[-5:]):
            st.caption(log)

    # 0.4초 간격 자동 재실행
    time.sleep(0.4)
    st.rerun()
