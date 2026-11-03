import os

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Solar Radiation Explorer", layout="wide")

DATA_FILE = "SolarPrediction.csv"
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
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(window["DateTime"], window["Radiation"])
        ax.set_xlabel("Time")
        ax.set_ylabel("Radiation (W/m²)")
        ax.set_title(f"Solar radiation over {n_days} day(s) from {start}")
        fig.autofmt_xdate()
        st.pyplot(fig)

# ------------------------------------------------------------------ tab 2
with tab2:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, col in zip(axes, ["Temperature", "Humidity", "Speed"]):
        ax.scatter(df[col], df["Radiation"], s=3, alpha=0.3)
        ax.set_xlabel(col)
        ax.set_ylabel("Radiation")
        ax.set_title(f"Radiation vs {col}")
    fig.tight_layout()
    st.pyplot(fig)

    corr = df[CORR_COLS].corr()
    left, right = st.columns([1, 1])

    with left:
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        fig.colorbar(im, ax=ax, label="Correlation")
        ax.set_xticks(range(len(CORR_COLS)))
        ax.set_xticklabels(CORR_COLS, rotation=90)
        ax.set_yticks(range(len(CORR_COLS)))
        ax.set_yticklabels(CORR_COLS)
        for i in range(len(CORR_COLS)):
            for j in range(len(CORR_COLS)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
        ax.set_title("Correlation heatmap")
        st.pyplot(fig)

    with right:
        st.subheader("Correlation with radiation")
        st.dataframe(corr["Radiation"].sort_values(ascending=False).rename("correlation"))

# ------------------------------------------------------------------ tab 3
with tab3:
    hourly_rad = df.groupby("Hour")["Radiation"].mean()
    hourly_temp = df.groupby("Hour")["Temperature"].mean()

    c1, c2 = st.columns(2)

    with c1:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(hourly_rad.index, hourly_rad.values)
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Mean radiation")
        ax.set_title("Average radiation by hour of day")
        ax.set_xticks(range(0, 24))
        st.pyplot(fig)

    with c2:
        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(hourly_rad.index, hourly_rad.values, color="orange", marker="o")
        ax1.set_xlabel("Hour of day")
        ax1.set_ylabel("Mean radiation (W/m²)", color="orange")
        ax2 = ax1.twinx()
        ax2.plot(hourly_temp.index, hourly_temp.values, color="red", marker="s")
        ax2.set_ylabel("Mean temperature", color="red")
        ax1.set_xticks(range(0, 24))
        ax1.set_title("Radiation and temperature by hour of day")
        st.pyplot(fig)

    hours = sorted(df["Hour"].unique())
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.boxplot([df.loc[df["Hour"] == h, "Radiation"] for h in hours], positions=hours)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Radiation")
    ax.set_title("Radiation distribution by hour of day")
    st.pyplot(fig)

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
