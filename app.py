"""Contact center staffing and cost calculator.

Streamlit app that estimates the team and cost of a single service
queue, with scenario comparison. Run with:

    streamlit run app.py
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.demand import validate_demand
from src.model import (
    capacity_contacts,
    interval_cost,
    required_agents,
    traffic_intensity,
)

st.set_page_config(
    page_title="Contact center staffing and cost calculator",
    page_icon="📊",
    layout="wide",
)

COLORS = {
    "Base scenario": "#4C78A8",
    "Productivity (lower AHT)": "#F58518",
    "Automation (hypothesis)": "#54A24B",
}


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    return pd.read_csv("data/sample_demand.csv")


def size_intervals(
    df: pd.DataFrame,
    aht_seconds: float,
    target_sl: float,
    target_wait_seconds: float,
    interval_seconds: float,
    hourly_cost: float,
    volume_factor: float = 1.0,
    aht_factor: float = 1.0,
) -> pd.DataFrame:
    """Size each interval and return one row per period."""
    rows = []
    for _, row in df.iterrows():
        contacts = float(row["contacts"]) * volume_factor
        aht = aht_seconds * aht_factor
        traffic = traffic_intensity(contacts, aht, interval_seconds)
        agents = required_agents(traffic, aht, target_sl, target_wait_seconds)
        rows.append(
            {
                "period": row["period"],
                "contacts": round(contacts, 1),
                "traffic_erlangs": round(traffic, 2),
                "agents": agents,
                "capacity": round(
                    capacity_contacts(agents, aht, interval_seconds), 1
                ),
                "cost": interval_cost(agents, hourly_cost, interval_seconds),
            }
        )
    return pd.DataFrame(rows)


def chart_demand_vs_capacity(base: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=base["period"], y=base["contacts"], name="Demand (contacts)")
    fig.add_scatter(
        x=base["period"],
        y=base["capacity"],
        name="Theoretical maximum capacity with the staffed team",
        mode="lines+markers",
        line=dict(color="#F58518"),
    )
    fig.update_layout(
        title="Demand vs theoretical maximum capacity per interval (base scenario)",
        xaxis_title="Period",
        yaxis_title="Contacts",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=70),
    )
    return fig


def chart_agents(results: dict[str, pd.DataFrame]) -> go.Figure:
    fig = go.Figure()
    for name, df in results.items():
        fig.add_scatter(
            x=df["period"],
            y=df["agents"],
            name=name,
            mode="lines+markers",
            line=dict(color=COLORS.get(name)),
        )
    fig.update_layout(
        title="Agents needed per interval, by scenario",
        xaxis_title="Period",
        yaxis_title="Agents",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=70),
    )
    return fig


def chart_costs(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=summary["scenario"],
        y=summary["total_cost"],
        name="Total daily cost",
        marker_color=[COLORS.get(c) for c in summary["scenario"]],
        text=summary["total_cost"].map(lambda v: f"{v:,.2f}"),
        textposition="outside",
    )
    fig.update_layout(
        title="Total staffing cost for the day, by scenario",
        yaxis_title="Cost (same currency as the hourly cost you entered)",
        showlegend=False,
        margin=dict(t=70),
    )
    return fig


# ----------------------------- Interface -----------------------------

st.title("Contact center staffing and cost calculator")
st.caption(
    "Estimates staffing and cost for one service queue, using "
    "the assumptions stated in 'Assumptions and limits'."
)

with st.sidebar:
    st.header("Parameters")
    hourly_cost = st.number_input(
        "Hourly cost per agent",
        min_value=0.0,
        value=25.0,
        step=1.0,
        help="Salary + benefits + overhead, per hour. The currency is whichever you use here.",
    )
    aht_seconds = st.number_input(
        "Average handle time (AHT), in seconds",
        min_value=1,
        value=300,
        step=10,
    )
    target_sl_pct = st.slider(
        "Service-level target (%)",
        min_value=50,
        max_value=99,
        value=80,
        help="Fraction of contacts answered within the target wait time.",
    )
    target_wait = st.number_input(
        "Target wait time (seconds)", min_value=0, value=20, step=5
    )
    interval_min = st.selectbox(
        "Length of each CSV interval (minutes)", [15, 30, 60], index=1
    )
    st.divider()
    st.header("Comparison scenarios")
    aht_reduction_pct = st.slider(
        "Productivity: AHT reduction (%)", 0, 50, 10,
        help="Hypothesis of process improvement or training.",
    )
    volume_reduction_pct = st.slider(
        "Automation: volume reduction (%)", 0, 50, 15,
        help=(
            "HYPOTHESIS: assumes an automation removes that fraction of "
            "contacts from the queue. It is not measured or guaranteed savings."
        ),
    )

upload = st.file_uploader(
    "Demand CSV (columns: period, contacts)", type=["csv"]
)

try:
    if upload is not None:
        df_demand = validate_demand(pd.read_csv(upload))
        source = "your CSV"
    else:
        df_demand = validate_demand(load_sample_data())
        source = "sample data (fictional, in data/sample_demand.csv)"
except ValueError as e:
    st.error(f"Problem with the CSV: {e}")
    st.stop()

st.write(f"Data source: **{source}** · {len(df_demand)} intervals of {interval_min} min.")

interval_seconds = interval_min * 60
target_sl = target_sl_pct / 100.0

scenarios = {
    "Base scenario": dict(volume_factor=1.0, aht_factor=1.0),
    "Productivity (lower AHT)": dict(
        volume_factor=1.0, aht_factor=1.0 - aht_reduction_pct / 100.0
    ),
    "Automation (hypothesis)": dict(
        volume_factor=1.0 - volume_reduction_pct / 100.0, aht_factor=1.0
    ),
}

try:
    results = {
        name: size_intervals(
            df_demand,
            aht_seconds=aht_seconds,
            target_sl=target_sl,
            target_wait_seconds=target_wait,
            interval_seconds=interval_seconds,
            hourly_cost=hourly_cost,
            **factors,
        )
        for name, factors in scenarios.items()
    }
except ValueError as e:
    st.error(f"Could not size the team: {e}")
    st.stop()

summary = pd.DataFrame(
    [
        {
            "scenario": name,
            "total_cost": df["cost"].sum(),
            "agent_hours": (df["agents"] * interval_seconds / 3600).sum(),
            "peak_agents": int(df["agents"].max()),
        }
        for name, df in results.items()
    ]
)

col1, col2, col3 = st.columns(3)
base = summary.iloc[0]
col1.metric("Total cost (base)", f"{base['total_cost']:,.2f}")
col2.metric("Peak agents (base)", int(base["peak_agents"]))
col3.metric("Agent-hours (base)", f"{base['agent_hours']:,.1f}")

st.plotly_chart(chart_demand_vs_capacity(results["Base scenario"]), width="stretch")
st.plotly_chart(chart_agents(results), width="stretch")
st.plotly_chart(chart_costs(summary), width="stretch")

with st.expander("See detailed table by scenario"):
    for name, df in results.items():
        st.subheader(name)
        st.dataframe(df)

st.divider()
st.subheader("Model assumptions and limits")
st.markdown(
    """
The numbers above hold under these assumptions (Erlang C model):

- **Single queue** with identical agents, all dedicated only to that queue.
- **Random contact arrivals** and variable handle times
  (Poisson/exponential distributions, the standard for this kind of queue).
- **No abandonment**: the model assumes every contact waits until it is
  answered. Queues with abandonment require a model that accounts for it; estimates can differ.
- **No breaks or unavailability** (shrinkage): in practice, the hired
  team needs to be larger than the calculated one, to cover breaks,
  absences and training. That adjustment varies by operation; add it on
  top of the model result for your own team's reality.
- **No multiple channels** (phone + chat + email together) and no
  priorities between contacts.
- The **automation scenario is a hypothesis** about volume, to test
  sensitivity. It is not measured or proven savings.

Use the result as an estimate to compare scenarios and support decisions,
not as a guaranteed forecast. Validate against real operational data
before hiring or letting people go.
"""
)


st.divider()
st.caption("By [dmcataneo](https://github.com/dmcataneo) · "
           "[Source code](https://github.com/dmcataneo/contact-center-staffing-calculator)")
