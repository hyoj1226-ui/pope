import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 스타일 정의 (따뜻한 톤)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption("읍·면·동 단위의 연령별 남녀 인구 분포를 따뜻한 시선으로 살펴봅니다.")

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 (캐싱을 이용해 앱 속도 최적화)
# -----------------------------------------------------------------------------
DATA_URL = "https://raw.githubusercontent.com/hyoj1226-ui/pope/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, compression='zip')
    
    # '연도' 열이 존재하면 가장 최신 연도 데이터만 필터링
    if '연도' in df.columns:
        latest_year = df['연도'].max()
        df = df[df['연도'] == latest_year].copy()
    
    return df

with st.spinner("데이터를 불러오는 중입니다... 잠시만 기다려주세요! ☕"):
    df = load_data()

# -----------------------------------------------------------------------------
# 3. 나이 라벨(0세 ~ 100세 이상) 순서 리스트 생성
# -----------------------------------------------------------------------------
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

# -----------------------------------------------------------------------------
# 4. 지역 선택 드롭다운 UI (시도 -> 시군구 -> 동)
# -----------------------------------------------------------------------------
st.markdown("### 📍 지역을 선택해 주세요")

col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df['시도'].dropna().unique())
    selected_sido = st.selectbox("시·도", sido_list)

df_sido = df[df['시도'] == selected_sido]

with col2:
    sigungu_list = sorted(df_sido['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("시·군·구", sigungu_list)

df_sigungu = df_sido[df_sido['시군구'] == selected_sigungu]

with col3:
    dong_list = sorted(df_sigungu['동'].dropna().unique())
    selected_dong = st.selectbox("읍·면·동", dong_list)

# 선택된 지역의 행 데이터 가져오기
selected_row = df_sigungu[df_sigungu['동'] == selected_dong].iloc[0]

# -----------------------------------------------------------------------------
# 5. 연령별/성별 인구수 추출 및 지표 계산
# -----------------------------------------------------------------------------
male_pop = []
female_pop = []

for age in age_labels:
    m_col = f"남_{age}"
    f_col = f"여_{age}"
    
    m_val = selected_row[m_col] if m_col in selected_row and pd.notna(selected_row[m_col]) else 0
    f_val = selected_row[f_col] if f_col in selected_row and pd.notna(selected_row[f_col]) else 0
    
    male_pop.append(int(m_val))
    female_pop.append(int(f_val))

# 주요 통계 지표 계산
total_pop = sum(male_pop) + sum(female_pop)

# 연령 수치화 (0~99세는 숫자, 100세 이상은 100세로 단순 계산)
age_numbers = list(range(100)) + [100]

# 평균 연령 계산
if total_pop > 0:
    weighted_sum = sum(age_num * (m + f) for age_num, m, f in zip(age_numbers, male_pop, female_pop))
    avg_age = weighted_sum / total_pop
    
    # 유소년(0~14세) 및 고령(65세 이상) 인구수 계산
    youth_pop = sum(m + f for age_num, m, f in zip(age_numbers, male_pop, female_pop) if age_num <= 14)
    elderly_pop = sum(m + f for age_num, m, f in zip(age_numbers, male_pop, female_pop) if age_num >= 65)
    
    aging_rate = (elderly_pop / total_pop) * 100
    youth_rate = (youth_pop / total_pop) * 100
else:
    avg_age = 0.0
    aging_rate = 0.0
    youth_rate = 0.0

# -----------------------------------------------------------------------------
# 6. 상단 지표 카드 3개 표시 (총인구, 평균연령, 고령화율)
# -----------------------------------------------------------------------------
st.markdown("---")
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.metric(label="👥 총인구", value=f"{total_pop:,}명")

with m_col2:
    st.metric(label="🎂 평균연령", value=f"{avg_age:.1f}세")

with m_col3:
    # 고령화율이 20% 이상이면 라벨 옆에 🚨 주의 표시 추가
    aging_label = "👵 고령화율 (65세+)"
    if aging_rate >= 20.0:
        aging_label += " 🚨"
    st.metric(label=aging_label, value=f"{aging_rate:.1f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. Plotly 가로 막대그래프(인구 피라미드) 생성
# -----------------------------------------------------------------------------
# 남성 인구수는 피라미드 형태를 위해 음수(-) 변환
male_pop_neg = [-val for val in male_pop]

fig = go.Figure()

# 남성 막대
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    marker=dict(color='#5B82A6'),
    hovertext=[f"남성 {age}: {val:,}명" for age, val in zip(age_labels, male_pop)],
    hoverinfo='text'
))

# 여성 막대
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여성',
    orientation='h',
    marker=dict(color='#E07A5F'),
    hovertext=[f"여성 {age}: {val:,}명" for age, val in zip(age_labels, female_pop)],
    hoverinfo='text'
))

# X축 범위 대칭 설정을 위한 최대값
max_val = max(max(male_pop), max(female_pop)) * 1.1 if total_pop > 0 else 100

fig
