import json
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 설정을 넓은 화면(wide) 모드로 지정
st.set_page_config(
    page_title="2026년 전국 고령화 단계구분도", page_layout="wide"
)

st.title("2026년 전국 시군구별 고령화율 단계구분도")


@st.cache_data
def load_data():
    # 1. 인구 데이터 로드 및 전처리
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url)

    # 2026년 데이터 필터링
    df_2026 = df[df["연도"] == 2026].copy()

    # 동 '코드'의 앞 5자리를 시군구 코드로 추출 (문자열로 변환)
    df_2026["코드_str"] = df_2026["코드"].astype(str).str.zfill(8)
    df_2026["sigungu_code"] = df_2026["코드_str"].str[:5]

    # '계_'로 시작하는 모든 열 식별
    total_cols = [c for c in df_2026.columns if c.startswith("계_")]

    # '계_65세'부터 '계_100세 이상'까지의 열 식별
    # 나이 숫자를 추출하여 65세 이상만 필터링
    old_cols = []
    for c in total_cols:
        age_str = c.replace("계_", "").replace("세 이상", "").replace("세", "")
        if age_str.isdigit() and int(age_str) >= 65:
            old_cols.append(c)

    # 행별 전체 인구 및 65세 이상 인구 계산
    df_2026["전체인구"] = df_2026[total_cols].sum(axis=1)
    df_2026["고령인구"] = df_2026[old_cols].sum(axis=1)

    # 시군구 코드(5자리) 단위로 그룹화하여 합산
    df_grouped = (
        df_2026.groupby("sigungu_code")[["전체인구", "고령인구"]]
        .sum()
        .reset_index()
    )

    # 고령화율(%) 계산
    df_grouped["고령화율"] = np.where(
        df_grouped["전체인구"] > 0,
        (df_grouped["고령인구"] / df_grouped["전체인구"]) * 100,
        0,
    )

    # 2. GeoJSON 데이터 로드
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    geojson_data = response.json()

    return df_grouped, geojson_data


# 데이터 불러오기
df_sigungu, sigungu_geojson = load_data()

# Plotly Choropleth (단계구분도) 생성
fig = px.choropleth(
    df_sigungu,
    geojson=sigungu_geojson,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    hover_data={"sigungu_code": False, "고령화율": ":.2f%"},
    labels={"고령화율": "고령화율 (%)"},
)

# GeoJSON의 '시군구' 속성을 hovertext로 지정
for feature in sigungu_geojson["features"]:
    code = feature["properties"]["코드"]
    name = feature["properties"]["시군구"]
    sido = feature["properties"]["시도"]

    # 해당 코드의 행을 찾아 hovertext 업데이트
    mask = df_sigungu["sigungu_code"] == code
    if mask.any():
        rate = df_sigungu.loc[mask, "고령화율"].values[0]
        df_sigungu.loc[mask, "hover_text"] = f"{sido} {name}<br>고령화율: {rate:.2f}%"

# hovertemplate 설정 (시군구 이름과 고령화율 표시)
fig.update_traces(
    hovertext=df_sigungu["hover_text"], hovertemplate="%{hovertext}<extra></extra>"
)

# 지도 배경/타일 제거 및 투명 레이아웃 적용
fig.update_geos(fitbounds="locations", visible=False)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    height=700,
)

st.plotly_chart(fig, use_container_width=True)
