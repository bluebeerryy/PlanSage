# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import openai

# ✅ 페이지 설정
st.set_page_config(page_title="PlanSage", layout="wide")

# ✅ 디자인 테마 삽입
st.markdown("""
    <style>
        body {
            background-color: #FFF8F0;
            font-family: 'Segoe UI', sans-serif;
        }
        .main {
            background-color: #FFF3E0;
            padding: 2rem;
            border-radius: 16px;
        }
        h1, h2, h3 {
            font-family: 'Georgia', serif;
            color: #4E342E;
        }
        .stButton>button {
            background-color: #FFCC80;
            color: black;
            border-radius: 12px;
            padding: 0.5em 1.5em;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #FFB74D;
        }
        .stDataFrame {
            background-color: #FFFDE7;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ✅ 사이드바 메뉴
st.sidebar.title("🧭 PlanSage 메뉴")
page = st.sidebar.selectbox("원하는 기능을 선택하세요:", ["📊 Smart Meeting", "🔮 운세 챗봇"])

# ✅ 세션 상태 초기화
if "todo_list" not in st.session_state:
    st.session_state.todo_list = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "calendar_data" not in st.session_state:
    st.session_state.calendar_data = pd.DataFrame(
        "", index=[f"{h}시" for h in range(8, 21)], columns=["월", "화", "수", "목", "금"]
    )
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

# -------------------------------
# 📊 Smart Meeting 페이지
# -------------------------------
if page == "📊 Smart Meeting":
    st.markdown("<h1 style='text-align: center;'>🧠 PlanSage</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: gray;'>당신의 하루를 똑똑하게 계획해 드릴게요</h3>", unsafe_allow_html=True)
    st.markdown("---")

    st.write("PlanSage는 Google Calendar 없이도 일정, 습관, 피로도를 기반으로 계획을 도와줍니다.")

    # 📋 To-Do 입력
    st.header("📋 해야 할 일 추가")
    with st.form(key="todo_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_name = st.text_input("과제/할 일 이름")
            due_date = st.date_input("마감일", datetime.date.today())
        with col2:
            estimated_time = st.number_input("예상 소요 시간 (시간 단위)", min_value=0.5, step=0.5)
            priority = st.selectbox("우선순위", ["높음", "중간", "낮음"])
        submitted = st.form_submit_button("➕ 추가하기")

    if submitted:
        st.session_state.todo_list.append({
            "과제명": task_name,
            "마감일": due_date,
            "소요시간": estimated_time,
            "우선순위": priority
        })
        st.success(f"'{task_name}' 추가 완료!")

    if st.session_state.todo_list:
        st.subheader("🗂 현재 해야 할 일 목록")
        todo_df = pd.DataFrame(st.session_state.todo_list)
        st.dataframe(todo_df)

    # 🔋 피로도 입력
    st.header("🔋 오늘의 컨디션 입력")
    col1, col2 = st.columns(2)
    with col1:
        sleep_hours = st.slider("어젯밤 수면 시간 (시간)", 0, 12, 7)
        mood = st.selectbox("현재 기분 상태", ["좋음 😀", "보통 😐", "나쁨 😩"])
    with col2:
        st.markdown("### 📊 예측된 피로도")
        fatigue_score = 10 - sleep_hours
        if mood == "좋음 😀":
            fatigue_score -= 1
        elif mood == "나쁨 😩":
            fatigue_score += 1
        fatigue_score = max(1, min(10, fatigue_score))
        if fatigue_score <= 3:
            st.success(f"🟢 낮은 피로도 (점수: {fatigue_score}/10)")
        elif fatigue_score <= 6:
            st.warning(f"🟡 중간 피로도 (점수: {fatigue_score}/10)")
        else:
            st.error(f"🔴 높은 피로도 (점수: {fatigue_score}/10)")

    # ✅ 일정 추천 알고리즘
    def recommend_schedule(fatigue_score):
        time_slots = [f"{h}시" for h in range(8, 21)]
        days = ["월", "화", "수", "목", "금"]
        recs = []

        for day in days:
            for hour in time_slots:
                if st.session_state.calendar_data.loc[hour, day] == "":
                    base_score = 10
                    hour_int = int(hour.replace("시", ""))
                    if 10 <= hour_int <= 12:
                        time_weight = 2
                    elif 14 <= hour_int <= 15:
                        time_weight = 1
                    else:
                        time_weight = -1
                    fatigue_penalty = fatigue_score
                    total_score = base_score + time_weight - fatigue_penalty
                    recs.append({
                        "요일": day,
                        "시간": hour,
                        "추천점수": total_score
                    })

        sorted_recs = sorted(recs, key=lambda x: x["추천점수"], reverse=True)
        return sorted_recs[:5]

    st.header("🔍 AI 추천 일정 시간대")
    if st.button("🧠 추천 시간대 보기"):
        st.session_state.recommendations = recommend_schedule(fatigue_score)

    if st.session_state.recommendations:
        st.subheader("✅ 추천 일정 리스트")
        st.dataframe(pd.DataFrame(st.session_state.recommendations))

        selected = st.selectbox("🗓 위 일정 중 하나를 선택해 캘린더에 추가하세요:", [f"{r['요일']} {r['시간']}" for r in st.session_state.recommendations])
        if st.button("📌 선택한 일정 등록"):
            sel_day, sel_hour = selected.split()
            task_name_for_schedule = st.session_state.todo_list[-1]["과제명"] if st.session_state.todo_list else "AI 추천 일정"
            st.session_state.calendar_data.loc[sel_hour, sel_day] = task_name_for_schedule
            st.success(f"✅ {sel_day} {sel_hour}에 '{task_name_for_schedule}' 일정이 추가되었습니다!")

        st.header("📅 주간 캘린더 보기")
        st.dataframe(st.session_state.calendar_data, height=400)

# 🔮 운세 챗봇은 변경 없음
