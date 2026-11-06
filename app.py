import os
import sys
import plotly.io as pio
pio.templates.default = "plotly_dark"
import streamlit as st
from streamlit.runtime import exists as _runtime_exists

# If this file is run with plain `python app.py` (or the VS Code play button),
# relaunch it through Streamlit instead of crashing.
if not _runtime_exists():
    from streamlit.web import cli as _stcli

    sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
    sys.exit(_stcli.main())

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Solar Radiation Explorer", layout="wide")

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolarPrediction.csv")
CORR_COLS = ["Radiation", "Temperature", "Pressure", "Humidity", "WindDirection(Degrees)", "Speed"]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    dates = df["Data"].str.split().str[0]
    df["DateTime"] = pd.to_datetime(dates + " " + df["Time"])
    df = df.sort_values("DateTime").reset_index(drop=True)
    df["Hour"] = df["DateTime"].dt.hour
    df["Date"] = df["DateTime"].dt.date
    return df


@st.cache_data
def load_from_path(path: str) -> pd.DataFrame:
    return prepare(pd.read_csv(path))


# ---------------------------------------------------------------- data loading
st.title("Solar Radiation Explorer")

df = None
if os.path.exists(DATA_FILE):
    df = load_from_path(DATA_FILE)
else:
    uploaded = st.file_uploader("Upload SolarPrediction.csv", type="csv")
    if uploaded is not None:
        df = prepare(pd.read_csv(uploaded))

if df is None:
    st.info("Add SolarPrediction.csv next to app.py, or upload it above.")
    st.stop()

st.caption(
    f"{len(df):,} readings from {df['DateTime'].min():%d %b %Y} "
    f"to {df['DateTime'].max():%d %b %Y}"
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Over time", "Relationships", "Daily pattern", "Best day"]
)

# ------------------------------------------------------------------ tab 1
with tab1:
    c1, c2 = st.columns(2)
    min_date = df["DateTime"].min().date()
    max_date = df["DateTime"].max().date()
    start = c1.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
    n_days = c2.slider("Days to show", 1, 30, 7)

    start_ts = pd.Timestamp(start)
    window = df[(df["DateTime"] >= start_ts) & (df["DateTime"] < start_ts + pd.Timedelta(days=n_days))]

    if window.empty:
        st.warning("No data in this range.")
    else:
        fig = px.line(
            window,
            x="DateTime",
            y="Radiation",
            title=f"Solar radiation over {n_days} day(s) from {start}",
            labels={"DateTime": "Time", "Radiation": "Radiation (W/m²)"},
        )
        st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ tab 2
with tab2:
    cols = st.columns(3)
    for col_ui, var in zip(cols, ["Temperature", "Humidity", "Speed"]):
        fig = px.scatter(
            df,
            x=var,
            y="Radiation",
            opacity=0.3,
            title=f"Radiation vs {var}",
            labels={"Radiation": "Radiation (W/m²)"},
        )
        fig.update_traces(marker=dict(size=3))
        col_ui.plotly_chart(fig, width="stretch")

    corr = df[CORR_COLS].corr()
    left, right = st.columns([2, 1])

    with left:
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            aspect="auto",
            title="Correlation heatmap",
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Correlation with radiation")
        st.dataframe(corr["Radiation"].sort_values(ascending=False).rename("correlation"))

# ------------------------------------------------------------------ tab 3
with tab3:
    hourly = df.groupby("Hour")[["Radiation", "Temperature"]].mean().reset_index()

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            hourly,
            x="Hour",
            y="Radiation",
            title="Average radiation by hour of day",
            labels={"Radiation": "Mean radiation (W/m²)", "Hour": "Hour of day"},
        )
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, width="stretch")

    with c2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=hourly["Hour"], y=hourly["Radiation"], name="Radiation",
                mode="lines+markers", line=dict(color="orange"),
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=hourly["Hour"], y=hourly["Temperature"], name="Temperature",
                mode="lines+markers", line=dict(color="red"), marker=dict(symbol="square"),
            ),
            secondary_y=True,
        )
        fig.update_layout(title="Radiation and temperature by hour of day")
        fig.update_xaxes(title_text="Hour of day", dtick=1)
        fig.update_yaxes(title_text="Mean radiation (W/m²)", secondary_y=False)
        fig.update_yaxes(title_text="Mean temperature", secondary_y=True)
        st.plotly_chart(fig, width="stretch")

    fig = px.box(
        df,
        x="Hour",
        y="Radiation",
        title="Radiation distribution by hour of day",
        labels={"Radiation": "Radiation (W/m²)", "Hour": "Hour of day"},
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ tab 4
with tab4:
    daily = df.groupby("Date")["Radiation"].agg(max_radiation="max", avg_radiation="mean")
    best_date = daily["max_radiation"].idxmax()

    day_df = df[df["Date"] == best_date]
    peak_row = day_df.loc[day_df["Radiation"].idxmax()]

    st.subheader(f"Day with the highest peak radiation: {best_date}")
    m1, m2 = st.columns(2)
    m1.metric("Daily maximum radiation", f"{daily.loc[best_date, 'max_radiation']:.1f}")
    m2.metric("Daily average radiation", f"{daily.loc[best_date, 'avg_radiation']:.1f}")

    st.markdown("**Weather conditions at the peak**")
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Peak time", f"{peak_row['DateTime']:%H:%M:%S}")
    w2.metric("Temperature", f"{peak_row['Temperature']}")
    w3.metric("Humidity", f"{peak_row['Humidity']}")
    w4.metric("Wind speed", f"{peak_row['Speed']}")

    sunrise = pd.to_datetime(f"{best_date} {peak_row['TimeSunRise']}")
    sunset = pd.to_datetime(f"{best_date} {peak_row['TimeSunSet']}")
    after_sunrise = peak_row["DateTime"] - sunrise
    daylight = sunset - sunrise

    st.markdown("**Peak vs sunrise and sunset**")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Sunrise", f"{sunrise.time()}")
    s2.metric("Sunset", f"{sunset.time()}")
    s3.metric("Peak after sunrise (hours)", f"{after_sunrise.total_seconds() / 3600:.2f}")
    s4.metric("Fraction of daylight elapsed", f"{after_sunrise / daylight:.2f}")

    st.markdown("**Top 5 days by average radiation**")
    st.dataframe(daily.nlargest(5, "avg_radiation"))
