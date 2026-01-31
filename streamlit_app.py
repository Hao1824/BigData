import streamlit as st
import pandas as pd
# import vaex
from pymongo import MongoClient
import certifi
import altair as alt
import re
from collections import Counter

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Netflix Data Analysis",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Netflix Data Analysis Dashboard")

# =========================
# LOAD DATA FROM MONGODB
# =========================
@st.cache_data
def load_data():
    uri = "mongodb+srv://netflixuser:UserA12345@cluster0.m6si8zu.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri, tlsCAFile=certifi.where())
    db = client["netflix_db"]
    collection = db["movies"]

    cursor = collection.find({}, {"_id": 0, "show_id": 0})
    df = pd.DataFrame(list(cursor))
    client.close()
    return df


df_pandas = load_data()

if df_pandas.empty:
    st.error("❌ Không có dữ liệu trong MongoDB")
    st.stop()

st.success(f"✅ Đã tải {len(df_pandas):,} bản ghi")

# =========================
# PREPROCESS (GIỐNG JUPITER)
# =========================
df_pandas["release_year"] = pd.to_numeric(
    df_pandas["release_year"], errors="coerce"
).fillna(df_pandas["release_year"].median()).astype(int)

df_pandas = df_pandas.fillna("Không xác định")

def parse_duration(duration):
    if isinstance(duration, str):
        nums = re.findall(r"\d+", duration)
        return int(nums[0]) if nums else 0
    return 0

df_pandas["duration_num"] = df_pandas["duration"].apply(parse_duration)

df_vx = vaex.from_pandas(df_pandas)

# =========================
# METRICS
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("🎞️ Tổng nội dung", f"{len(df_vx):,}")
col2.metric("🎬 Movies", int((df_vx.type == "Movie").sum()))
col3.metric("📺 TV Shows", int((df_vx.type == "TV Show").sum()))

st.divider()

# =========================
# CHART 1: TYPE DISTRIBUTION
# =========================
st.subheader("📺 Phân phối loại nội dung")

type_df = (
    df_pandas["type"]
    .value_counts()
    .rename_axis("type")
    .reset_index(name="total")
)


chart_type = (
    alt.Chart(type_df)
    .mark_bar()
    .encode(
        x=alt.X("type:N", title="Loại nội dung"),
        y=alt.Y("total:Q", title="Số lượng"),
        color="type:N",
        tooltip=[
            alt.Tooltip("type:N", title="Loại"),
            alt.Tooltip("total:Q", title="Số lượng")
        ]
    )
)


st.altair_chart(chart_type, use_container_width=True)

# =========================
# CHART 2: RELEASE YEAR
# =========================
st.subheader("📅 Phân bố năm phát hành")

year_df = (
    df_pandas
    .groupby("release_year")
    .size()
    .reset_index(name="total")
)

year_chart = (
    alt.Chart(year_df)
    .mark_bar()
    .encode(
        x=alt.X("release_year:Q", title="Năm phát hành"),
        y=alt.Y("total:Q", title="Số lượng"),
        tooltip=["release_year", "total"]
    )
)

st.altair_chart(year_chart, use_container_width=True)


# =========================
# CHART 3: TOP COUNTRIES
# =========================
st.subheader("🌍 Top quốc gia sản xuất")

all_countries = []
for c in df_pandas["country"]:
    if c != "Không xác định":
        all_countries.extend([x.strip() for x in c.split(",")])

country_df = (
    pd.DataFrame(Counter(all_countries).most_common(10),
                 columns=["country", "count"])
)

country_chart = (
    alt.Chart(country_df)
    .mark_bar()
    .encode(
        y=alt.Y("country:N", sort="-x"),
        x="count:Q",
        tooltip=["country", "count"]
    )
)

st.altair_chart(country_chart, use_container_width=True)
# =========================
# CHART 4: Xu hướng Movie & TV Show theo năm
# =========================
st.subheader("📈 Xu hướng Movie & TV Show theo năm")

trend_df = (
    df_pandas
    .groupby(["release_year", "type"])
    .size()
    .reset_index(name="total")
)

trend_chart = (
    alt.Chart(trend_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("release_year:Q", title="Năm"),
        y=alt.Y("total:Q", title="Số lượng"),
        color="type:N",
        tooltip=["release_year", "type", "total"]
    )
)

st.altair_chart(trend_chart, use_container_width=True)
st.subheader("⏱️ Phân bố thời lượng")

duration_chart = (
    alt.Chart(df_pandas)
    .mark_boxplot()
    .encode(
        x="type:N",
        y=alt.Y("duration_num:Q", title="Thời lượng"),
        color="type:N"
    )
)

st.altair_chart(duration_chart, use_container_width=True)

# =========================
# FILTER & TABLE
# =========================
st.subheader("📋 Dữ liệu chi tiết")

content_type = st.multiselect(
    "Chọn loại nội dung",
    options=df_pandas["type"].unique(),
    default=df_pandas["type"].unique().tolist()
)

filtered_df = df_pandas[df_pandas["type"].isin(content_type)]

st.dataframe(
    filtered_df[
        [
            "title",
            "type",
            "director",
            "country",
            "release_year",
            "rating",
            "duration"
        ]
    ],
    use_container_width=True,
    height=500
)

st.caption("📌 Data được lấy trực tiếp từ MongoDB Atlas")
