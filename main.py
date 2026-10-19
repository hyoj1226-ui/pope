import json
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# [필수] Streamlit 설정은 최상단에 배치 (TypeError 방지)
st.set_page_config(page_title="전국 연령대별 인구 비율 단계구분도", layout="wide")

st.title("전국 시군구별 인구 지표 단계구분도")


@st.cache_data
def load_data():
    # 1. 인구 데이터 로드
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url)

    # 코드 열 문자열(8자리) 변환
    df["코드_str"] = df["코드"].astype(str).str.zfill(8)
    df["sigungu_code"] = df["코드_str"].str[:5]

    # 행정구역 개편 코드 변경 (강원 42->51, 전북 45->52, 군위군 47720->27720)
    def update_code(code):
        if code == "47720":
            return "27720"
        elif code.startswith("42"):
            return "51" + code[2:]
        elif code.startswith("45"):
            return "52" + code[2:]
        return code

    df["sigungu_code"] = df["sigungu_code"].apply(update_code)

    # 인구 연령대 컬럼 분류
    total_cols = [c for c in df.columns if c.startswith("계_")]

    elderly_cols = []
    youth_cols = []

    for c in total_cols:
        age_str = c.replace("계_", "").replace("세 이상", "").replace("세", "")
        if age_str.isdigit():
            age = int(age_str)
            if age >= 65:
                elderly_cols.append(c)
            elif age <= 14:
                youth_cols.append(c)

    # 행별 합계 계산
    df["전체인구"] = df[total_cols].sum(axis=1)
    df["고령인구"] = df[elderly_cols].sum(axis=1)
    df["유소년인구"] = df[youth_cols].sum(axis=1)

    # 시군구 및 연도별 집계
    df_grouped = (
        df.groupby(["연도", "sigungu_code"])[["전체인구", "고령인구", "유소년인구"]]
        .sum()
        .reset_index()
    )

    # 비율 계산 (%)
    df_grouped["고령화율"] = np.where(
        df_grouped["전체인구"] > 0,
        (df_grouped["고령인구"] / df_grouped["전체인구"]) * 100,
        0,
    )
    df_grouped["유소년비율"] = np.where(
        df_grouped["전체인구"] > 0,
        (df_grouped["유소년인구"] / df_grouped["전체인구"]) * 100,
        0,
    )

    # 2. GeoJSON 데이터 로드
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    geojson_data = response.json()

    return df_grouped, geojson_data


# 데이터 불러오기
df_all, sigungu_geojson = load_data()

# 지점 정보 맵핑 사전 (GeoJSON 기준 코드 -> 시도, 시군구 이름)
geo_info = {}
for f in sigungu_geojson["features"]:
    props = f["properties"]
    geo_info[props["코드"]] = {
        "sido": props.get("시도", ""),
        "sigungu": props.get("시군구", ""),
    }

# 사이드바 / 컨트롤러 영역
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.5, 1.5, 2])

with col_ctrl1:
    indicator = st.selectbox(
        "지표 선택", ["고령화율 (65세 이상)", "유소년 비율 (0~14세)"]
    )

with col_ctrl2:
    sido_list = ["전국"] + sorted(
        list(set([v["sido"] for v in geo_info.values() if v["sido"]]))
    )
    selected_sido = st.selectbox("지역(시도) 선택", sido_list)

with col_ctrl3:
    available_years = sorted(df_all["연도"].unique())
    selected_year = st.slider(
        "연도 선택",
        min_value=int(min(available_years)),
        max_value=int(max(available_years)),
        value=int(max(available_years)),
    )

# 지표 변수명 및 범주 설정
if indicator == "고령화율 (65세 이상)":
    val_col = "고령화율"
    bins = [-1, 19, 23, 28, 38, 100]
    labels = ["19% 미만", "19% ~ 23%", "23% ~ 28%", "28% ~ 38%", "38% 이상"]
    color_map = {
        "19% 미만": "#fef0d9",
        "19% ~ 23%": "#fdcc8a",
        "23% ~ 28%": "#fc8d59",
        "28% ~ 38%": "#e34a33",
        "38% 이상": "#b30000",
    }
else:
    val_col = "유소년비율"
    bins = [-1, 8, 10, 12, 14, 100]
    labels = ["8% 미만", "8% ~ 10%", "10% ~ 12%", "12% ~ 14%", "14% 이상"]
    color_map = {
        "8% 미만": "#f7fbff",
        "8% ~ 10%": "#c6dbef",
        "10% ~ 12%": "#6baed6",
        "12% ~ 14%": "#2171b5",
        "14% 이상": "#08306b",
    }

# 선택된 연도 데이터 필터링 및 이름 부착
df_year = df_all[df_all["연도"] == selected_year].copy()
df_year["시도"] = df_year["sigungu_code"].map(
    lambda x: geo_info.get(x, {}).get("sido", "")
)
df_year["시군구"] = df_year["sigungu_code"].map(
    lambda x: geo_info.get(x, {}).get("sigungu", "")
)

# 시도 필터링
if selected_sido != "전국":
    df_filtered = df_year[df_year["시도"] == selected_sido].copy()
else:
    df_filtered = df_year.copy()

# 지표 구간(범주) 분류
df_filtered["구간"] = pd.cut(
    df_filtered[val_col], bins=bins, labels=labels
)

# 요약 지표 카드 3개
st.markdown("---")
col_m1, col_m2, col_m3 = st.columns(3)

# 전국/해당지역 평균
total_pop_sum = df_filtered["전체인구"].sum()
target_pop_sum = (
    df_filtered["고령인구"].sum()
    if indicator == "고령화율 (65세 이상)"
    else df_filtered["유소년인구"].sum()
)
avg_rate = (target_pop_sum / total_pop_sum * 100) if total_pop_sum > 0 else 0

col_m1.metric(
    label=f"{selected_sido} 평균 {indicator.split()[0]}",
    value=f"{avg_rate:.2f}%",
)

# 최고 시군구
valid_df = df_filtered[df_filtered["시군구"] != ""]
if not valid_df.empty:
    max_row = valid_df.loc[valid_df[val_col].idxmax()]
    min_row = valid_df.loc[valid_df[val_col].idxmin()]

    col_m2.metric(
        label=f"가장 높은 시군구",
        value=f"{max_row[val_col]:.2f}%",
        delta=f"{max_row['시도']} {max_row['시군구']}",
        delta_color="normal",
    )

    col_m3.metric(
        label=f"가장 낮은 시군구",
        value=f"{min_row[val_col]:.2f}%",
        delta=f"{min_row['시도']} {min_row['시군구']}",
        delta_color="inverse",
    )
st.markdown("---")

# Tooltip 텍스트 생성
df_filtered["hover_text"] = df_filtered.apply(
    lambda r: (
        f"{r['시도']} {r['시군구']}<br>{indicator.split()[0]}: {r[val_col]:.2f}%"
        if r["시군구"]
        else f"코드: {r['sigungu_code']}<br>{indicator.split()[0]}: {r[val_col]:.2f}%"
    ),
    axis=1,
)

# GeoJSON 시도 필터링
if selected_sido != "전국":
    filtered_geojson = {
        "type": "FeatureCollection",
        "features": [
            f
            for f in sigungu_geojson["features"]
            if f["properties"].get("시도") == selected_sido
        ],
    }
else:
    filtered_geojson = sigungu_geojson

# Plotly 지도 생성
fig = px.choropleth(
    df_filtered,
    geojson=filtered_geojson,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="구간",
    color_discrete_map=color_map,
    category_orders={"구간": labels},
    hover_name="hover_text",
)

fig.update_traces(hovertemplate="%{hovertext}<extra></extra>")
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin={"r": 0, "t": 10, "l": 0, "b": 0},
    height=680,
    legend_title_text=indicator.split()[0],
)

st.plotly_chart(fig, use_container_width=True)

# 매칭되지 않은 지역 안내 메시지 출력
unmatched_codes = set(df_year["sigungu_code"]) - set(geo_info.keys())
if unmatched_codes:
    st.caption(
        "💡 **안내**: 과거 행정구역 개편이나 코드 미매칭으로 인해 지도 경계에 경계선이 포함되지 않은 일부 지역은 회색으로 나타나거나 표시에서 제외될 수 있습니다."
    )
