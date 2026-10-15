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
# GitHub의 blob 주소 대신 raw 파일 주소를 사용합니다.
DATA_URL = "https://raw.githubusercontent.com/hyoj1226-ui/pope/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_data():
    # zip 압축 파일의 첫 번째 CSV를 자동으로 판다스가 읽어옵니다.
    df = pd.read_csv(DATA_URL, compression='zip')
    
    # '연도' 열이 존재하면 가장 최신 연도 데이터만 필터링합니다.
    if '연도' in df.columns:
        latest_year = df['연도'].max()
        df = df[df['연도'] == latest_year].copy()
    
    return df

with st.spinner("데이터를 불러오는 중입니다... 잠시만 기다려주세요! ☕"):
    df = load_data()

# -----------------------------------------------------------------------------
# 3. 나이 라벨(0세 ~ 100세 이상) 순서 리스트 생성
# -----------------------------------------------------------------------------
# 0세부터 99세까지 + '100세 이상'
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

# -----------------------------------------------------------------------------
# 4. 지역 선택 드롭다운 UI (시도 -> 시군구 -> 동)
# -----------------------------------------------------------------------------
st.markdown("### 📍 지역을 선택해 주세요")

col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df['시도'].dropna().unique())
    selected_sido = st.selectbox("시·도", sido_list)

# 선택한 시도에 해당하는 시군구 목록
df_sido = df[df['시도'] == selected_sido]

with col2:
    sigungu_list = sorted(df_sido['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("시·군·구", sigungu_list)

# 선택한 시군구에 해당하는 동 목록
df_sigungu = df_sido[df_sido['시군구'] == selected_sigungu]

with col3:
    dong_list = sorted(df_sigungu['동'].dropna().unique())
    selected_dong = st.selectbox("읍·면·동", dong_list)

# 최종 선택된 지역의 1개 행 추출
selected_row = df_sigungu[df_sigungu['동'] == selected_dong].iloc[0]

# -----------------------------------------------------------------------------
# 5. 선택 지역의 남/여 나이별 인구수 추출 및 가공
# -----------------------------------------------------------------------------
male_pop = []
female_pop = []

for age in age_labels:
    m_col = f"남_{age}"
    f_col = f"여_{age}"
    
    # 해당 열의 값이 없거나 NaN인 경우 0으로 처리
    m_val = selected_row[m_col] if m_col in selected_row and pd.notna(selected_row[m_col]) else 0
    f_val = selected_row[f_col] if f_col in selected_row and pd.notna(selected_row[f_col]) else 0
    
    male_pop.append(m_val)
    female_pop.append(f_val)

# 피라미드 표현을 위해 남성 인구수는 음수(-)로 변환
male_pop_neg = [-val for val in male_pop]

# -----------------------------------------------------------------------------
# 6. Plotly 가로 막대그래프(인구 피라미드) 생성
# -----------------------------------------------------------------------------
fig = go.Figure()

# 남성 막대 (왼쪽, 따뜻한 톤의 코랄/네이비 계열 표현을 위한 감성 색상 지정)
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    marker=dict(color='#5B82A6'),      # 따뜻한 차분한 푸른색
    hovertext=[f"남성 {age}: {val:,}명" for age, val in zip(age_labels, male_pop)],
    hoverinfo='text'
))

# 여성 막대 (오른쪽)
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여성',
    orientation='h',
    marker=dict(color='#E07A5F'),      # 따뜻한 코랄/살구색
    hovertext=[f"여성 {age}: {val:,}명" for age, val in zip(age_labels, female_pop)],
    hoverinfo='text'
))

# -----------------------------------------------------------------------------
# 7. 레이아웃 설정 (세로축 순서 고정 및 한국어 라벨 적용)
# -----------------------------------------------------------------------------
# 전체 최대 인구수를 구해서 x축 범위를 좌우 대칭으로 설정
max_val = max(max(male_pop), max(female_pop)) * 1.1 if max(male_pop) > 0 or max(female_pop) > 0 else 100

fig.update_layout(
    title=dict(
        text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}]</b> 연령별 인구 피라미드",
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
    # x축: 음수로 표현된 값을 양수 라벨로 보이도록 설정
    xaxis=dict(
        range=[-max_val, max_val],
        title="인구수 (명)",
        tickformat="s",
        # 축 눈금 표시 시 절대값으로 보여주기
        tickvals=[-int(max_val*0.8), -int(max_val*0.4), 0, int(max_val*0.4), int(max_val*0.8)],
        ticktext=[f"{abs(int(max_val*0.8)):,}", f"{abs(int(max_val*0.4)):,}", "0", f"{int(max_val*0.4):,}", f"{int(max_val*0.8):,}"]
    ),
    # y축: 카테고리 순서를 명시적으로 고정 (0세가 맨 아래, 100세 이상이 맨 위)
    yaxis=dict(
        title="연령",
        type='category',
        categoryorder='array',
        categoryarray=age_labels,  # 0세부터 100세 이상 순서의 배열 그대로 고정
        dtick=10                  # 10세 간격으로 눈금 라벨 표시
    ),
    height=750,
    margin=dict(l=60, r=40, t=80, b=50)
)

# -----------------------------------------------------------------------------
# 8. 화면에 그래프 출력
# -----------------------------------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

st.info("💡 **Tip:** 그래프 위에 마우스를 올리면 각 연령별 정확한 인구수를 확인할 수 있습니다.")
