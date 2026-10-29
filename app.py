import random
import pandas as pd
import streamlit as st

# ==========================================
# 1. 페이지 및 고대비 가독성 UI 스타일 설정
# ==========================================
st.set_page_config(
    page_title="ATC 활주로 착륙 관제 타이쿤",
    page_icon="🛫",
    layout="wide",
)

# 글자 가독성을 극대화한 고대비 CSS
st.markdown(
    """
    <style>
    /* 전체 배경 및 기본 글자색 */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* 비행기 카드 디자인 (고대비 선명함) */
    .atc-card {
        background-color: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    
    /* 카드 내부 글자 색상 보정 */
    .card-title {
        color: #38bdf8 !important;
        font-size: 22px !important;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .card-info {
        color: #f1f5f9 !important;
        font-size: 16px !important;
        margin-bottom: 10px;
    }
    
    /* 상태 배지 색상 */
    .badge-danger {
        background-color: #ef4444;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
    .badge-warning {
        background-color: #f59e0b;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
    .badge-success {
        background-color: #10b981;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 초기화
# ==========================================
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "planes" not in st.session_state:
    st.session_state.planes = []
if "score" not in st.session_state:
    st.session_state.score = 100
if "turn" not in st.session_state:
    st.session_state.turn = 1
if "landed_count" not in st.session_state:
    st.session_state.landed_count = 0
if "runway_01l_busy" not in st.session_state:
    st.session_state.runway_01l_busy = 0
if "runway_01r_busy" not in st.session_state:
    st.session_state.runway_01r_busy = 0
if "last_landed_type" not in st.session_state:
    st.session_state.last_landed_type = {"01L": None, "01R": None}
if "logs" not in st.session_state:
    st.session_state.logs = []


# ==========================================
# 3. 주요 로직 함수
# ==========================================
def spawn_plane():
    """신규 항공기 생성"""
    callsigns = [
        "KAL001",
        "AAR302",
        "JNA705",
        "TWB104",
        "EZY881",
        "CPA402",
        "ANA911",
        "BAW027",
    ]
    existing_cs = [p["callsign"] for p in st.session_state.planes]
    available_cs = list(set(callsigns) - set(existing_cs))

    if available_cs:
        cs = random.choice(available_cs)
        ac_type = random.choice(["Heavy(대형)", "Medium(중형)", "Light(소형)"])
        fuel = random.randint(35, 85)
        distance = random.randint(15, 35)

        st.session_state.planes.append(
            {
                "callsign": cs,
                "type": ac_type,
                "fuel": fuel,
                "distance": distance,
                "status": "대기 중(Holding)",
                "assigned_runway": None,
            }
        )


def init_game():
    """게임 리셋/초기화"""
    st.session_state.game_started = True
    st.session_state.planes = []
    st.session_state.score = 100
    st.session_state.turn = 1
    st.session_state.landed_count = 0
    st.session_state.runway_01l_busy = 0
    st.session_state.runway_01r_busy = 0
    st.session_state.last_landed_type = {"01L": None, "01R": None}
    st.session_state.logs = ["🛫 관제탑 관제 업무가 시작되었습니다."]

    for _ in range(3):
        spawn_plane()


def process_landing_clearance(callsign, selected_runway):
    """원클릭 착륙 지시 검증 로직"""
    plane = next(
        (p for p in st.session_state.planes if p["callsign"] == callsign), None
    )
    if not plane:
        return

    # 활주로 점유 체크
    runway_timer = (
        st.session_state.runway_01l_busy
        if selected_runway == "01L"
        else st.session_state.runway_01r_busy
    )
    if runway_timer > 0:
        st.warning(
            f"🚫 활주로 {selected_runway}는 현재 점유 중입니다! ({runway_timer}턴 남음)"
        )
        return

    # 후류 와류 체크
    last_type = st.session_state.last_landed_type[selected_runway]
    occupancy_time = 2

    if last_type == "Heavy(대형)" and plane["type"] in [
        "Medium(중형)",
        "Light(소형)",
    ]:
        st.toast(
            "⚠️ [후류 와류 대기] 선행 대형기로 인해 활주로 점유 시간이 1턴 증가합니다.",
            icon="⚠️",
        )
        occupancy_time += 1

    plane["status"] = "착륙 접근 중"
    plane["assigned_runway"] = selected_runway

    if selected_runway == "01L":
        st.session_state.runway_01l_busy = occupancy_time
    else:
        st.session_state.runway_01r_busy = occupancy_time

    st.session_state.last_landed_type[selected_runway] = plane["type"]

    # 가산점 처리
    if plane["fuel"] <= 30:
        st.session_state.score += 25
        log_msg = f"🚨 [비상 착륙 승인] {callsign} -> 활주로 {selected_runway} (+25점)"
    else:
        st.session_state.score += 10
        log_msg = f"✅ [착륙 허가] {callsign} -> 활주로 {selected_runway} (+10점)"

    st.session_state.logs.append(log_msg)
    st.toast(log_msg, icon="📡")


def auto_emergency_control():
    """가장 급한 비행기를 자동 판단하여 착륙시키는 스마트 버튼"""
    waiting = [
        p
        for p in st.session_state.planes
        if p["status"] == "대기 중(Holding)"
    ]
    if not waiting:
        st.toast("대기 중인 항공기가 없습니다!", icon="ℹ️")
        return

    # 연료가 가장 적은 비행기 자동 선택
    target = min(waiting, key=lambda x: x["fuel"])

    # 빈 활주로 자동 선택
    if st.session_state.runway_01l_busy == 0:
        process_landing_clearance(target["callsign"], "01L")
    elif st.session_state.runway_01r_busy == 0:
        process_landing_clearance(target["callsign"], "01R")
    else:
        st.warning("⚠️ 현재 모든 활주로가 사용 중입니다! 잠시 후 시도하세요.")


def next_turn():
    """턴 진행"""
    st.session_state.turn += 1

    if st.session_state.runway_01l_busy > 0:
        st.session_state.runway_01l_busy -= 1
    if st.session_state.runway_01r_busy > 0:
        st.session_state.runway_01r_busy -= 1

    remaining_planes = []
    for p in st.session_state.planes:
        if p["status"] == "착륙 접근 중":
            p["distance"] -= 15
            if p["distance"] <= 0:
                st.session_state.landed_count += 1
                st.session_state.logs.append(
                    f"🛬 [{p['callsign']}] 활주로 {p['assigned_runway']} 안전 착륙 완료!"
                )
                continue
        else:
            p["fuel"] -= random.randint(8, 14)
            p["distance"] -= random.randint(2, 4)

            if p["fuel"] <= 0:
                st.session_state.score -= 30
                st.session_state.logs.append(
                    f"💥 [비상 이탈] {p['callsign']} 연료 고갈로 공역 이탈! (-30점)"
                )
                continue

        remaining_planes.append(p)

    st.session_state.planes = remaining_planes

    if random.random() < 0.6 and len(st.session_state.planes) < 5:
        spawn_plane()
        st.session_state.logs.append("📡 신규 항공기가 공역에 진입했습니다.")


# ==========================================
# 4. 화면 레이아웃
# ==========================================
st.title("🛫 쉬운 공항 활주로 착륙 관제 타이쿤")
st.caption(
    "버튼 하나만 눌러 항공기를 안전하게 착륙시키세요! (자동 추천 기능 지원)"
)

if not st.session_state.game_started:
    st.info("👋 관제 업무를 시작하려면 아래 버튼을 눌러주세요.")
    if st.button("▶️ 관제 업무 시작", type="primary", use_container_width=True):
        init_game()
        st.rerun()

else:
    # 대시보드 상단 정보
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 현재 점수", f"{st.session_state.score}점")
    m2.metric("🛬 착륙 성공", f"{st.session_state.landed_count}대")
    m3.metric("⏳ 진행 시간", f"{st.session_state.turn}턴")
    m4.metric("✈️ 대기 중인 항공기", f"{len(st.session_state.planes)}대")

    st.divider()

    # 상단 자동 관제 및 턴 진행 조작바
    ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])
    with ctrl1:
        if st.button(
            "⚡ [원클릭] 가장 위험한 비행기 자동 착륙 지시",
            type="primary",
            use_container_width=True,
        ):
            auto_emergency_control()
            st.rerun()
    with ctrl2:
        if st.button("⏭️ 다음 시간(Turn) 진행", use_container_width=True):
            next_turn()
            st.rerun()
    with ctrl3:
        if st.button("🔄 처음부터 다시 하기", use_container_width=True):
            init_game()
            st.rerun()

    st.write("")

    # 메인 화면 (좌: 비행기 목록 및 원클릭 버튼, 우: 활주로 상태)
    col_left, col_right = st.columns([1.8, 1])

    with col_left:
        st.subheader("📡 공역 대기 비행기 목록 (원클릭 착륙)")

        if not st.session_state.planes:
            st.success("🎉 현재 상공에 대기 중인 비행기가 없습니다!")
        else:
            for p in st.session_state.planes:
                # 상태 배지 설정
                if p["fuel"] <= 25:
                    badge_html = '<span class="badge-danger">🚨 비상(연료 부족)</span>'
                elif p["fuel"] <= 45:
                    badge_html = '<span class="badge-warning">⚠️ 주의</span>'
                else:
                    badge_html = '<span class="badge-success">✅ 정상</span>'

                # 항공기 카드 출력
                st.markdown(
                    f"""
                    <div class="atc-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="card-title">✈️ {p['callsign']} <span style="font-size:16px; color:#cbd5e1;">({p['type']})</span></div>
                            <div>{badge_html}</div>
                        </div>
                        <div class="card-info">
                            현재 상태: <b>{p['status']}</b> | 남은 거리: <b>{p['distance']} NM</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 연료 바
                st.progress(
                    max(0, min(100, p["fuel"])) / 100,
                    text=f"연료 잔여량: {p['fuel']}%",
                )

                # 카드 바로 아래 [원클릭 착륙 버튼] 배치 (입력할 필요 없음)
                if p["status"] == "대기 중(Holding)":
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(
                            f"🛬 {p['callsign']} -> 01L 착륙",
                            key=f"btn_01l_{p['callsign']}",
                            use_container_width=True,
                        ):
                            process_landing_clearance(p["callsign"], "01L")
                            st.rerun()
                    with b2:
                        if st.button(
                            f"🛬 {p['callsign']} -> 01R 착륙",
                            key=f"btn_01r_{p['callsign']}",
                            use_container_width=True,
                        ):
                            process_landing_clearance(p["callsign"], "01R")
                            st.rerun()
                st.write("")

    with col_right:
        st.subheader("🛣️ 활주로 점유 현황")

        if st.session_state.runway_01l_busy > 0:
            st.error(
                f"🔴 **활주로 01L**\n\n[착륙 진행 중 - {st.session_state.runway_01l_busy}턴 남음]"
            )
        else:
            st.success("🟢 **활주로 01L**\n\n[즉시 착륙 가능]")

        if st.session_state.runway_01r_busy > 0:
            st.error(
                f"🔴 **활주로 01R**\n\n[착륙 진행 중 - {st.session_state.runway_01r_busy}턴 남음]"
            )
        else:
            st.success("🟢 **활주로 01R**\n\n[즉시 착륙 가능]")

        st.divider()

        st.subheader("📜 실시간 관제 기록")
        for log in reversed(st.session_state.logs[-6:]):
            st.caption(log)
