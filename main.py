import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

-----------------------------------------------------------------------------

1. 페이지 기본 설정 및 스타일 정의 (따뜻한 톤)

-----------------------------------------------------------------------------

st.set_page_config(
page_title="동네별 인구 피라미드",
page_icon="👨‍👩‍👧‍👦",
layout="centered"
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption("읍·면·동 단위의 연령별 남녀 인구 분포를 따뜻한 시선으로 살펴봅니다.")

-----------------------------------------------------------------------------

2. 데이터 불러오기 (캐싱을 이용해 앱 속도 최적화)

-----------------------------------------------------------------------------

DATA_URL = "https://raw.githubusercontent.com/hyoj1226-ui/pope/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_data():
df = pd.read_csv(DATA_URL, compression='zip')

# 가장 최신 연도 데이터만 필터링
if '연도' in df.columns:
    latest_year = df['연도'].max()
    df = df[df['연도'] == latest_year].copy()

return df


with st.spinner("데이터를 불러오는 중입니다... 잠시만 기다려주세요! ☕"):
df = load_data()

-----------------------------------------------------------------------------

3. 나이 라벨(0세 ~ 100세 이상) 순서 리스트 및 연령 숫자 배열 생성

-----------------------------------------------------------------------------

age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

평균 연령 계산용 (100세 이상은 보수적으로 100세로 산정)

age_numbers = np.array(list(range(100)) + [100])

-----------------------------------------------------------------------------

4. 지역 선택 드롭다운 UI (시도 -> 시군구 -> 동)

-----------------------------------------------------------------------------

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

선택된 1개 지역 행 데이터

selected_row = df_sigungu[df_sigungu['동'] == selected_dong].iloc[0]

-----------------------------------------------------------------------------

5. 선택 지역의 남/여 나이별 인구수 추출 및 주요 지표 계산

-----------------------------------------------------------------------------

male_pop = []
female_pop = []

for age in age_labels:
m_col = f"남_{age}"
f_col = f"여_{age}"

m_val = selected_row[m_col] if m_col in selected_row and pd.notna(selected_row[m_col]) else 0
f_val = selected_row[f_col] if f_col in selected_row and pd.notna(selected_row[f_col]) else 0

male_pop.append(int(m_val))
female_pop.append(int(f_val))


나이별 남녀 합계 인구 배열

male_pop_arr = np.array(male_pop)
female_pop_arr = np.array(female_pop)
total_pop_by_age = male_pop_arr + female_pop_arr

1) 총 인구

total_population = int(np.sum(total_pop_by_age))

2) 평균 연령 계산

if total_population > 0:
mean_age = np.sum(total_pop_by_age * age_numbers) / total_population
else:
mean_age = 0.0

3) 고령화율(65세 이상 비율) & 유소년 비율(0~14세)

elderly_pop = np.sum(total_pop_by_age[65:])
child_pop = np.sum(total_pop_by_age[:15])

aging_rate = (elderly_pop / total_population * 100) if total_population > 0 else 0.0
child_rate = (child_pop / total_population * 100) if total_population > 0 else 0.0

-----------------------------------------------------------------------------

6. 상단 주요 지표 카드 출력 (3개 나란히)

-----------------------------------------------------------------------------

st.markdown("---")
metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
st.metric(label="👥 총인구", value=f"{total_population:,}명")

with metric_col2:
st.metric(label="🎂 평균연령", value=f"{mean_age:.1f}세")

with metric_col3:
# 고령화율 20% 이상 시 주의 아이콘(🚨) 표시
aging_label = "🚨 고령화율 (65세+)" if aging_rate >= 20.0 else "👵 고령화율 (65세+)"
st.metric(label=aging_label, value=f"{aging_rate:.1f}%")

-----------------------------------------------------------------------------

7. Plotly 가로 막대그래프(인구 피라미드) 생성

-----------------------------------------------------------------------------

male_pop_neg = [-val for val in male_pop]

fig = go.Figure()

남성 막대 (좌측, 따뜻한 톤의 데님 블루)

fig.add_trace(go.Bar(
y=age_labels,
x=male_pop_neg,
name='남성',
orientation='h',
marker=dict(color='#5B82A6'),
hovertext=[f"남성 {age}: {val:,}명" for age, val in zip(age_labels, male_pop)],
hoverinfo='text'
))

여성 막대 (우측, 따뜻한 톤의 코랄)

fig.add_trace(go.Bar(
y=age_labels,
x=female_pop,
name='여성',
orientation='h',
marker=dict(color='#E07A5F'),
hovertext=[f"여성 {age}: {val:,}명" for age, val in zip(age_labels, female_pop)],
hoverinfo='text'
))

x축 범위 대칭 맞춤

max_val = max(max(male_pop), max(female_pop)) * 1.1 if max(male_pop) > 0 or max(female_pop) > 0 else 100

fig.update_layout(
title=dict(
text=f"[{selected_sido} {selected_sigungu} {selected_dong}] 연령별 인구 피라미드",
font=dict(size=18, color="#333333")
),
barmode='relative',
bargap=0.1,
paper_bgcolor='rgba(0,0,0,0)',
plot_bgcolor='rgba(0,0,0,0)',
legend=dict(
title="",
orientation="h",
yanchor="bottom",
y=1.02,
xanchor="right",
x=1
),
xaxis=dict(
range=[-max_val, max_val],
title="인구수 (명)",
tickvals=[-int(max_val0.8), -int(max_val0.4), 0, int(max_val0.4), int(max_val0.8)],
ticktext=[f"{abs(int(max_val0.8)):,}", f"{abs(int(max_val0.4)):,}", "0", f"{int(max_val0.4):,}", f"{int(max_val0.8):,}"]
),
yaxis=dict(
title="연령",
type='category',
categoryorder='array',
categoryarray=age_labels,  # 0세부터 100세 이상 순서 고정
dtick=10
),
height=750,
margin=dict(l=60, r=40, t=80, b=50)
)

st.plotly_chart(fig, use_container_width=True)

-----------------------------------------------------------------------------

8. 피라미드 하단 자동 특징 한 줄 요약

-----------------------------------------------------------------------------

st.markdown("#### 💡 이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?")

유소년(0~14세) 및 고령인구(65세 이상) 비중 비교 설명

if aging_rate >= 20.0:
summary_msg = f"이 동네는 고령화율이 {aging_rate:.1f}%로, 어르신 비중이 높고 초고령사회 기준(20%)을 넘는 지역입니다."
elif child_rate > aging_rate:
summary_msg = f"이 동네는 아이(0~14세, {child_rate:.1f}%) 비중이 어르신(65세 이상, {aging_rate:.1f}%)보다 높은, 활기차고 아이들이 상대적으로 많은 지역입니다."
elif abs(child_rate - aging_rate) <= 3.0:
summary_msg = f"이 동네는 아이(0~14세, {child_rate:.1f}%)와 어르신(65세 이상, {aging_rate:.1f}%) 비중이 비교적 균형을 이루고 있는 지역입니다."
else:
summary_msg = f"이 동네는 어르신(65세 이상, {aging_rate:.1f}%) 비중이 아이(0~14세, {child_rate:.1f}%)보다 높아, 성인 및 어르신층 중심의 지역입니다."

st.info(summary_msg)
