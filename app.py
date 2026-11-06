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

st.set_page_config(
    page_title="Solar Radiation Explorer",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ORANGE = "#F5A623"
RED = "#FF5A5F"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolarPrediction.csv")
CORR_COLS = ["Radiation", "Temperature", "Pressure", "Humidity", "WindDirection(Degrees)", "Speed"]


# ---------------------------------------------------------------- helpers
def style(fig, height=380):
    """Apply one consistent look to every chart."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10),
        height=height,
        title_font_size=16,
    )
    return fig


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


# ---------------------------------------------------------------- header
st.title("☀️ Solar Radiation Explorer")
st.markdown(
    "Explore how solar radiation changes over time and how it relates to "
    "temperature, humidity, pressure and wind. Use the sidebar to choose a time window."
)

# ---------------------------------------------------------------- data loading
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

min_date = df["DateTime"].min().date()
max_date = df["DateTime"].max().date()
total_days = (max_date - min_date).days + 1

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Controls")
    st.caption("These apply to the 'Over time' tab.")
    start = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
    n_days = st.slider("Days to show", 1, 30, 7)

    st.divider()
    with st.expander("What do the variables mean?"):
        st.markdown(
            "- **Radiation**: solar energy reaching the sensor (W/m²)\n"
            "- **Temperature**: air temperature\n"
            "- **Pressure**: atmospheric pressure\n"
            "- **Humidity**: moisture in the air (%)\n"
            "- **Wind direction**: direction the wind blows from (degrees)\n"
            "- **Speed**: wind speed"
        )

# ---------------------------------------------------------------- summary cards
k1, k2, k3, k4 = st.columns(4)
k1.metric("Peak radiation", f"{df['Radiation'].max():,.0f} W/m²")
k2.metric("Average temperature", f"{df['Temperature'].mean():.1f}")
k3.metric("Readings", f"{len(df):,}")
k4.metric("Period", f"{total_days} days", f"{min_date:%d %b} to {max_date:%d %b %Y}", delta_color="off")

st.write("")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Over time", "🔗 Relationships", "🕐 Daily pattern", "🏆 Best day"]
)

# ------------------------------------------------------------------ tab 1
with tab1:
    start_ts = pd.Timestamp(start)
    window = df[(df["DateTime"] >= start_ts) & (df["DateTime"] < start_ts + pd.Timedelta(days=n_days))]

    if window.empty:
        st.warning("No data in this range. Try another start date in the sidebar.")
    else:
        fig = px.line(
            window,
            x="DateTime",
            y="Radiation",
            title=f"Solar radiation over {n_days} day(s) from {start}",
            labels={"DateTime": "Time", "Radiation": "Radiation (W/m²)"},
        )
        fig.update_traces(line_color=ORANGE)
        st.plotly_chart(style(fig, 420), width="stretch")
        st.caption(
            "Radiation rises after sunrise, peaks around midday and drops at night. "
            "Dips during the day usually mean clouds."
        )

# ------------------------------------------------------------------ tab 2
with tab2:
    corr = df[CORR_COLS].corr()

    st.subheader("Radiation vs weather")
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
        fig.update_traces(marker=dict(size=3, color=ORANGE))
        col_ui.plotly_chart(style(fig, 340), width="stretch")
        col_ui.caption(f"Correlation with radiation: **{corr.loc['Radiation', var]:+.2f}**")

    st.subheader("How everything relates")
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
        st.plotly_chart(style(fig, 460), width="stretch")
        st.caption("Red means two variables rise together, blue means one rises as the other falls.")

    with right:
        st.markdown("**Correlation with radiation**")
        st.dataframe(corr["Radiation"].sort_values(ascending=False).rename("correlation"), width="stretch")

# ------------------------------------------------------------------ tab 3
with tab3:
    hourly = df.groupby("Hour")[["Radiation", "Temperature"]].mean().reset_index()
    peak_hour = int(hourly.loc[hourly["Radiation"].idxmax(), "Hour"])

    st.info(f"On average, radiation is highest at **{peak_hour}:00**.")

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            hourly,
            x="Hour",
            y="Radiation",
            title="Average radiation by hour of day",
            labels={"Radiation": "Mean radiation (W/m²)", "Hour": "Hour of day"},
        )
        fig.update_traces(marker_color=ORANGE)
        fig.update_xaxes(dtick=2)
        st.plotly_chart(style(fig), width="stretch")

    with c2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=hourly["Hour"], y=hourly["Radiation"], name="Radiation",
                mode="lines+markers", line=dict(color=ORANGE),
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=hourly["Hour"], y=hourly["Temperature"], name="Temperature",
                mode="lines+markers", line=dict(color=RED), marker=dict(symbol="square"),
            ),
            secondary_y=True,
        )
        fig.update_layout(
            title="Radiation and temperature by hour of day",
            legend=dict(orientation="h", y=-0.2),
        )
        fig.update_xaxes(title_text="Hour of day", dtick=2)
        fig.update_yaxes(title_text="Mean radiation (W/m²)", secondary_y=False)
        fig.update_yaxes(title_text="Mean temperature", secondary_y=True)
        st.plotly_chart(style(fig), width="stretch")

    st.caption("Temperature usually peaks a little after radiation, because the air takes time to warm up.")

    fig = px.box(
        df,
        x="Hour",
        y="Radiation",
        title="Radiation distribution by hour of day",
        labels={"Radiation": "Radiation (W/m²)", "Hour": "Hour of day"},
    )
    fig.update_traces(marker_color=ORANGE, line_color=ORANGE)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(style(fig, 420), width="stretch")
    st.caption("Each box shows the typical range of radiation for that hour. Dots are unusual readings.")

# ------------------------------------------------------------------ tab 4
with tab4:
    daily = df.groupby("Date")["Radiation"].agg(max_radiation="max", avg_radiation="mean")
    best_date = daily["max_radiation"].idxmax()

    day_df = df[df["Date"] == best_date]
    peak_row = day_df.loc[day_df["Radiation"].idxmax()]

    st.subheader(f"Day with the highest peak radiation: {best_date}")
    m1, m2 = st.columns(2)
    m1.metric("Daily maximum radiation", f"{daily.loc[best_date, 'max_radiation']:.1f} W/m²")
    m2.metric("Daily average radiation", f"{daily.loc[best_date, 'avg_radiation']:.1f} W/m²")

    fig = px.line(
        day_df,
        x="DateTime",
        y="Radiation",
        title=f"Radiation through the day on {best_date}",
        labels={"DateTime": "Time", "Radiation": "Radiation (W/m²)"},
    )
    fig.update_traces(line_color=ORANGE)
    fig.add_trace(
        go.Scatter(
            x=[peak_row["DateTime"]], y=[peak_row["Radiation"]],
            mode="markers", name="Peak",
            marker=dict(size=12, color=RED),
        )
    )
    st.plotly_chart(style(fig, 360), width="stretch")

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
    st.dataframe(daily.nlargest(5, "avg_radiation"), width="stretch")

# ---------------------------------------------------------------- footer
st.divider()
st.caption("Data: SolarPrediction.csv · Built with Streamlit and Plotly · Edit this line to add your team name")
