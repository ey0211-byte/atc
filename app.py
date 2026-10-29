import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. 페이지 및 관제탑 다크 테마 UI 설정
# ==========================================
st.set_page_config(
    page_title="ATC 활주로 착륙 관제 타이쿤",
    page_icon="🛫",
    layout="wide",
)

# 다크 모드 및 관제 레이더 스타일 커스텀 CSS
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1021;
        color: #e0e6ed;
    }
    .atc-card {
        background-color: #161f38;
        border: 1px solid #2a3a60;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .status-emergency {
        color: #ff4d4d;
        font-weight: bold;
    }
    .status-warning {
        color: #ffa500;
        font-weight: bold;
    }
    .status-safe {
        color: #00e676;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 세션 상태 초기화 (State Management)
# ==========================================
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "planes" not in st.session_state:
    st.session_state.planes = []
if "score" not in st.session_state:
    st.session_state.score = 0
if "turn" not in st.session_state:
    st.session_state.turn = 1
if "landed_count" not in st.session_state:
    st.session_state.landed_count = 0
if "runway_01l_busy" not in st.session_state:
    st.session_state.runway_01l_busy = 0  # 0이면 사용 가능, >0 이면 점유 중
if "runway_01r_busy" not in st.session_state:
    st.session_state.runway_01r_busy = 0
if "last_landed_type" not in st.session_state:
    st.session_state.last_landed_type = {"01L": None, "01R": None}
if "logs" not in st.session_state:
    st.session_state.logs = []


# ==========================================
# 3. 비행기 생성 및 데이터 관리 함수
# ==========================================
def spawn_plane():
    """신규 항공기 생성 함수"""
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
        ac_type = random.choice(
            ["Heavy(B777)", "Medium(A320)", "Light(B737)"]
        )
        fuel = random.randint(30, 80)  # 연료 30% ~ 80%
        distance = random.randint(15, 40)  # 거리 (NM)

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
    """게임 초기화 함수"""
    st.session_state.game_started = True
    st.session_state.planes = []
    st.session_state.score = 100
    st.session_state.turn = 1
    st.session_state.landed_count = 0
    st.session_state.runway_01l_busy = 0
    st.session_state.runway_01r_busy = 0
    st.session_state.last_landed_type = {"01L": None, "01R": None}
    st.session_state.logs = ["🛫 관제탑 운영이 시작되었습니다."]

    # 초기 비행기 3대 생성
    for _ in range(3):
        spawn_plane()


# ==========================================
# 4. 멀티체크 관제 로직 (Multi-check Logic)
# ==========================================
def process_landing_clearance(callsign, selected_runway):
    """착륙 허가 멀티체크 검증 함수"""
    try:
        # 1차 검증: 대상 항공기 존재 유무
        plane = next(
            (p for p in st.session_state.planes if p["callsign"] == callsign),
            None,
        )
        if not plane:
            st.error("❌ 오류: 해당 비행기를 공역에서 찾을 수 없습니다.")
            return

        # 2차 검증: 이미 착륙 중인 비행기인지 확인
        if plane["status"] == "착륙 중(Final Approach)":
            st.warning(
                f"⚠️ [{callsign}] 이미 착륙 접근 중인 항공기입니다."
            )
            return

        # 3차 검증: 해당 활주로 점유 상태 확인
        runway_timer = (
            st.session_state.runway_01l_busy
            if selected_runway == "01L"
            else st.session_state.runway_01r_busy
        )
        if runway_timer > 0:
            st.error(
                f"🚫 [활주로 점유 중] 활주로 {selected_runway}는 현재 사용할 수 없습니다. (남은 점유 시간: {runway_timer}턴)"
            )
            return

        # 4차 검증: 후류 와류(Wake Turbulence) 안전거리 체크
        last_type = st.session_state.last_landed_type[selected_runway]
        occupancy_time = 2  # 기본 활주로 점유 시간 (2턴)

        if last_type == "Heavy(B777)" and plane["type"] in [
            "Medium(A320)",
            "Light(B737)",
        ]:
            st.toast(
                f"⚠️ [후류 와류 경고] 선행 대형기(Heavy)로 인해 활주로 대기 시간이 1턴 증가합니다.",
                icon="⚠️",
            )
            occupancy_time += 1  # 후류 와류로 인한 대기시간 증가

        # 검증 통과 후 명령 적용
        plane["status"] = "착륙 중(Final Approach)"
        plane["assigned_runway"] = selected_runway

        if selected_runway == "01L":
            st.session_state.runway_01l_busy = occupancy_time
        else:
            st.session_state.runway_01r_busy = occupancy_time

        st.session_state.last_landed_type[selected_runway] = plane["type"]

        # 점수 계산 (연료 위급 상황에서 적절히 승인했으면 가산점)
        if plane["fuel"] <= 25:
            st.session_state.score += 25
            log_msg = f"🚨 [비상 착륙 승인] {callsign}을(를) 활주로 {selected_runway}로 보냈습니다. (+25점)"
        else:
            st.session_state.score += 10
            log_msg = f"✅ [착륙 허가] {callsign}을(를) 활주로 {selected_runway}로 보냈습니다. (+10점)"

        st.session_state.logs.append(log_msg)
        st.toast(log_msg, icon="📡")

    except Exception as e:
        st.error(f"관제 지시 처리 중 예외 발생: {e}")


def next_turn():
    """시간(Turn) 진행 및 데이터 업데이트 알고리즘"""
    try:
        st.session_state.turn += 1

        # 활주로 타이머 감소
        if st.session_state.runway_01l_busy > 0:
            st.session_state.runway_01l_busy -= 1
        if st.session_state.runway_01r_busy > 0:
            st.session_state.runway_01r_busy -= 1

        remaining_planes = []
        for p in st.session_state.planes:
            # 착륙 진행 중인 비행기 처리
            if p["status"] == "착륙 중(Final Approach)":
                p["distance"] -= 15
                if p["distance"] <= 0:
                    st.session_state.landed_count += 1
                    st.session_state.logs.append(
                        f"🛬 [{p['callsign']}] 활주로 {p['assigned_runway']}에 성공적으로 착륙했습니다."
                    )
                    continue  # 공역에서 제거

            # 대기 중인 비행기 연료 및 거리 소모
            else:
                p["fuel"] -= random.randint(8, 15)  # 턴당 연료 소모
                p["distance"] -= random.randint(2, 5)

                # 연료 고갈 시 강제 비상 회항(감점 처리)
                if p["fuel"] <= 0:
                    st.session_state.score -= 30
                    st.session_state.logs.append(
                        f"💥 [비상 상황] {p['callsign']}이(가) 연료 고갈로 공역을 이탈했습니다! (-30점)"
                    )
                    continue

            remaining_planes.append(p)

        st.session_state.planes = remaining_planes

        # 확률적으로 신규 항공기 공역 진입
        if random.random() < 0.6 and len(st.session_state.planes) < 6:
            spawn_plane()
            st.session_state.logs.append("📡 신규 항공기가 공역에 진입했습니다.")

        st.rerun()

    except Exception as e:
        st.error(f"턴 진행 과정에서 오류가 발생했습니다: {e}")


# ==========================================
# 5. UI 메인 레이아웃 구성
# ==========================================
st.title("🛫 공항 활주로 착륙 순서 배정 타이쿤")
st.caption(
    "실시간 연료 상태, 후류 와류 간격, 활주로 점유 현황을 동시 체크하여 안전한 관제를 수행하세요!"
)

# 게임 시작 전 화면
if not st.session_state.game_started:
    st.info(
        "👋 항공교통관제사님 환영합니다! 아래 버튼을 눌러 관제 업무를 개시하세요."
    )
    if st.button("▶️ 관제 업무 시작", type="primary", use_container_width=True):
        init_game()
        st.rerun()

else:
    # 대시보드 상단 메트릭
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 현재 관제 점수", f"{st.session_state.score}점")
    m2.metric("🛬 성공적인 착륙", f"{st.session_state.landed_count}대")
    m3.metric("⏳ 경과 시간(Turn)", f"{st.session_state.turn}턴")
    m4.metric("✈️ 공역 내 항공기", f"{len(st.session_state.planes)}대")

    st.divider()

    # 메인 화면 2개 컬럼 분할
    col_left, col_right = st.columns([1.6, 1.2])

    # --------------------------------------------------
    # [좌측] 공역 현황 모니터링 및 연료 게이지 UI
    # --------------------------------------------------
    with col_left:
        st.subheader("📡 공역 모니터링 (Airspace Status)")

        if not st.session_state.planes:
            st.success("🎉 현재 공역에 대기 중인 비행기가 없습니다.")
        else:
            for p in st.session_state.planes:
                # 연료 상태에 따른 색상 구분
                if p["fuel"] <= 20:
                    fuel_color = "status-emergency"
                    badge = "🚨 비상(CRITICAL)"
                elif p["fuel"] <= 40:
                    fuel_color = "status-warning"
                    badge = "⚠️ 주의(LOW)"
                else:
                    fuel_color = "status-safe"
                    badge = "✅ 정상(NORMAL)"

                with st.container():
                    st.markdown(
                        f"""
                    <div class="atc-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4 style="margin:0; color:#00e676;">✈️ {p['callsign']} <span style="font-size:14px; color:#aaa;">({p['type']})</span></h4>
                            <span class="{fuel_color}">{badge}</span>
                        </div>
                        <p style="margin: 5px 0;">상태: <b>{p['status']}</b> | 거리: {p['distance']} NM</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    # 연료 프로그레스 바
                    st.progress(
                        max(0, min(100, p["fuel"])) / 100,
                        text=f"잔여 연료: {p['fuel']}%",
                    )

    # --------------------------------------------------
    # [우측] 활주로 점유 상태 및 관제 명령 패널
    # --------------------------------------------------
    with col_right:
        st.subheader("🕹️ 활주로 및 관제 지시 패널")

        # 활주로 점유 현황 표시
        r1, r2 = st.columns(2)
        with r1:
            if st.session_state.runway_01l_busy > 0:
                st.error(
                    f"🔴 활주로 01L\n\n[점유 중 - {st.session_state.runway_01l_busy}턴 남음]"
                )
            else:
                st.success("🟢 활주로 01L\n\n[사용 가능]" )
        with r2:
            if st.session_state.runway_01r_busy > 0:
                st.error(
                    f"🔴 활주로 01R\n\n[점유 중 - {st.session_state.runway_01r_busy}턴 남음]"
                )
            else:
                st.success("🟢 활주로 01R\n\n[사용 가능]" )

        st.write("---")

        # 관제 지시 폼
        if st.session_state.planes:
            target_plane = st.selectbox(
                "1️⃣ 관제할 비행기 선택",
                [p["callsign"] for p in st.session_state.planes],
            )
            target_runway = st.radio(
                "2️⃣ 착륙 활주로 선택", ["01L", "01R"], horizontal=True
            )

            if st.button("📡 착륙 허가 발송", type="primary", use_container_width=True):
                process_landing_clearance(target_plane, target_runway)
                st.rerun()

        else:
            st.info("관제할 비행기가 없습니다.")

        st.write("---")
        # 시간 진행 버튼
        if st.button("⏭️ 다음 시간(Turn) 진행", use_container_width=True):
            next_turn()

        if st.button("🔄 게임 리셋", use_container_width=True):
            init_game()
            st.rerun()

    # --------------------------------------------------
    # 하단: 관제 교신 및 실행 로그
    # --------------------------------------------------
    st.divider()
    with st.expander("📜 관제 교신 실시간 기록 (ATC Log Stream)", expanded=True):
        for log in reversed(st.session_state.logs):
            st.write(log)
