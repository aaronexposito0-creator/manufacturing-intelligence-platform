from __future__ import annotations

from pathlib import Path
import sqlite3
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.kpis import add_row_kpis, calculate_kpis, machine_kpi_frame
from src.insights import generate_insights
from src.scenarios import estimate_constraint_opportunity, simulate_operational_scenario

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "processed" / "manufacturing.db"
APP_VERSION = "2.0"

COLORS = {
    "primary": "#4DA3FF",
    "secondary": "#86C8FF",
    "good": "#46C98B",
    "watch": "#FFB454",
    "critical": "#FF647C",
    "muted": "#8A94A6",
    "grid": "rgba(140,150,170,.14)",
}
STATUS_COLORS = {"Healthy": COLORS["good"], "Watch": COLORS["watch"], "Critical": COLORS["critical"]}

st.set_page_config(
    page_title="Manufacturing Intelligence Platform",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

css_path = ROOT / "assets" / "custom.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    prod = pd.read_sql("SELECT * FROM fact_production", conn, parse_dates=["date"])
    downtime = pd.read_sql("SELECT * FROM fact_downtime", conn, parse_dates=["date"])
    quality = pd.read_sql("SELECT * FROM fact_quality", conn, parse_dates=["date"])
    machines = pd.read_sql("SELECT * FROM dim_machine", conn)
    products = pd.read_sql("SELECT * FROM dim_product", conn)
    conn.close()
    return add_row_kpis(prod), downtime, quality, machines, products


def pct(x: float, decimals: int = 1) -> str:
    return f"{x * 100:.{decimals}f}%"


def euro(x: float, decimals: int = 0) -> str:
    return f"€{x:,.{decimals}f}"


def pp_delta(current: float, previous: float | None) -> str | None:
    if previous is None:
        return None
    diff = current - previous
    if abs(diff) < 0.0005:
        diff = 0.0
    return f"{diff * 100:+.1f} pp"


def pct_delta(current: float, previous: float | None) -> str | None:
    if previous in (None, 0):
        return None
    diff = (current - previous) / abs(previous)
    if abs(diff) < 0.0005:
        diff = 0.0
    return f"{diff * 100:+.1f}%"


def style_figure(fig: go.Figure, height: int = 350, hovermode: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=54, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode=hovermode,
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig


def filter_prod(df: pd.DataFrame, start_date, end_date, machine_ids, product_ids, shifts) -> pd.DataFrame:
    return df[
        (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
        & df["machine_id"].isin(machine_ids)
        & df["product_id"].isin(product_ids)
        & df["shift"].isin(shifts)
    ].copy()


def filter_down(df: pd.DataFrame, start_date, end_date, machine_ids, shifts) -> pd.DataFrame:
    return df[
        (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
        & df["machine_id"].isin(machine_ids)
        & df["shift"].isin(shifts)
    ].copy()


def filter_quality(df: pd.DataFrame, start_date, end_date, machine_ids, product_ids) -> pd.DataFrame:
    return df[
        (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
        & df["machine_id"].isin(machine_ids)
        & df["product_id"].isin(product_ids)
    ].copy()


def aggregate_trend(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    freq = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}[granularity]
    out = (
        df.set_index("date")
        .resample(freq)
        .agg(planned_qty=("planned_qty", "sum"), good_qty=("good_qty", "sum"), scrap_qty=("scrap_qty", "sum"))
        .reset_index()
    )
    return out




def metric_history(df: pd.DataFrame) -> dict[str, list[float]]:
    """Return weekly KPI sequences used by executive metric sparklines."""
    keys = ["oee", "availability", "quality", "schedule_attainment", "unit_cost", "gross_margin_rate"]
    history = {key: [] for key in keys}
    if df.empty:
        return history
    work = df.copy()
    work["week"] = work["date"].dt.to_period("W").dt.start_time
    for _, g in work.groupby("week", sort=True):
        wk = calculate_kpis(g)
        for key in keys:
            history[key].append(float(wk[key]))
    return history

def weighted_scrap_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(["machine_id", "product_id"], as_index=False).agg(scrap_qty=("scrap_qty", "sum"), total_qty=("total_qty", "sum"))
    g["scrap_rate"] = g["scrap_qty"] / g["total_qty"].replace(0, pd.NA)
    return g.pivot(index="machine_id", columns="product_id", values="scrap_rate")


def render_insight_card(ins: dict) -> None:
    severity = ins.get("severity", "info")
    st.markdown(
        f"""
        <div class="insight-card {severity}">
          <div class="insight-top"><span class="severity-dot"></span><b>{ins['title']}</b></div>
          <div class="insight-grid">
            <div><span class="insight-label">IMPACT</span><p>{ins['impact']}</p></div>
            <div><span class="insight-label">LIKELY DRIVER</span><p>{ins['driver']}</p></div>
            <div><span class="insight-label">RECOMMENDED ACTION</span><p>{ins['action']}</p></div>
            <div><span class="insight-label">ESTIMATED OPPORTUNITY</span><p>{ins['opportunity']}</p></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


prod, downtime, quality, machines, products = load_data()

machine_names = machines.set_index("machine_id")["machine_name"].to_dict()
product_names = products.set_index("product_id")["product_name"].to_dict()

# ---------------- Header ----------------
st.markdown(
    f"""
    <div class="hero">
      <div class="hero-main">
        <div class="eyebrow">PORTFOLIO CASE STUDY · INDUSTRIAL ANALYTICS · V{APP_VERSION}</div>
        <h1>Manufacturing Intelligence Platform</h1>
        <p>Decision-support analytics for production, OEE, quality, downtime and manufacturing economics.</p>
        <div class="hero-meta">
          <span>Python</span><span>SQL</span><span>Streamlit</span><span>Plotly</span><span>BI-ready model</span>
        </div>
      </div>
      <div class="synthetic-badge"><b>100% SYNTHETIC DATA</b><br>No employer or customer information</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Sidebar ----------------
st.sidebar.markdown("## Control Center")
st.sidebar.caption("Change scope once; every KPI, chart, insight and scenario updates automatically.")

min_date = prod["date"].min().date()
max_date = prod["date"].max().date()
default_start = max(min_date, max_date - timedelta(days=180))
date_value = st.sidebar.date_input(
    "Analysis window",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_value, tuple) and len(date_value) == 2:
    start_date, end_date = date_value
else:
    start_date, end_date = default_start, max_date

st.sidebar.markdown("### Operational scope")
machine_options = machines["machine_id"].tolist()
product_options = products["product_id"].tolist()
shift_options = sorted(prod["shift"].unique().tolist())
selected_machines = st.sidebar.multiselect(
    "Machines", machine_options, default=machine_options,
    format_func=lambda x: f"{x} · {machine_names.get(x, x)}",
)
selected_products = st.sidebar.multiselect(
    "Products", product_options, default=product_options,
    format_func=lambda x: f"{x} · {product_names.get(x, x)}",
)
selected_shifts = st.sidebar.multiselect("Shifts", shift_options, default=shift_options)
trend_granularity = st.sidebar.selectbox("Trend granularity", ["Weekly", "Daily", "Monthly"], index=0)

if not selected_machines or not selected_products or not selected_shifts:
    st.warning("Select at least one machine, product and shift to analyse the plant.")
    st.stop()

fprod = filter_prod(prod, start_date, end_date, selected_machines, selected_products, selected_shifts)
fdown = filter_down(downtime, start_date, end_date, selected_machines, selected_shifts)
fquality = filter_quality(quality, start_date, end_date, selected_machines, selected_products)

period_days = (end_date - start_date).days + 1
prev_end = start_date - timedelta(days=1)
prev_start = max(min_date, prev_end - timedelta(days=period_days - 1))
previous_prod = filter_prod(prod, prev_start, prev_end, selected_machines, selected_products, selected_shifts) if prev_end >= min_date else pd.DataFrame()

k = calculate_kpis(fprod)
pk = calculate_kpis(previous_prod) if not previous_prod.empty else None
mkdf = machine_kpi_frame(fprod, machines[machines["machine_id"].isin(selected_machines)])
metric_trends = metric_history(fprod)

st.sidebar.markdown("---")
st.sidebar.markdown("### Portfolio context")
st.sidebar.caption("Deterministic synthetic factory · 6 machines · 6 products · reproducible ETL + SQLite warehouse.")
st.sidebar.caption("Designed to demonstrate engineering + analytics + business decision support.")

# ---------------- Plant status ----------------
status_counts = mkdf["status"].value_counts().to_dict() if not mkdf.empty else {}
st.markdown(
    f"""
    <div class="status-strip">
      <div><span class="status-label">PLANT STATUS</span><b>{len(mkdf)} assets in selected scope</b></div>
      <div class="status-pills">
        <span class="pill healthy">● {status_counts.get('Healthy', 0)} Healthy</span>
        <span class="pill watch">● {status_counts.get('Watch', 0)} Watch</span>
        <span class="pill critical">● {status_counts.get('Critical', 0)} Critical</span>
      </div>
      <div class="period-compare">vs previous comparable period: {prev_start.strftime('%d %b')}–{prev_end.strftime('%d %b %Y') if prev_end >= min_date else 'not available'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Navigation ----------------
tab_exec, tab_prod, tab_quality, tab_down, tab_cost, tab_scenario, tab_data = st.tabs([
    "Executive Overview", "Production", "Quality", "Downtime", "Cost & Margin", "Scenario Lab", "Data Explorer"
])

with tab_exec:
    st.markdown("#### Executive scorecard")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("OEE", pct(k["oee"]), pp_delta(k["oee"], pk["oee"] if pk else None), help="Availability × Performance × Quality", chart_data=metric_trends["oee"], chart_type="line", delta_description="vs prior period")
    c2.metric("Availability", pct(k["availability"]), pp_delta(k["availability"], pk["availability"] if pk else None), chart_data=metric_trends["availability"], chart_type="line", delta_description="vs prior period")
    c3.metric("Quality", pct(k["quality"]), pp_delta(k["quality"], pk["quality"] if pk else None), chart_data=metric_trends["quality"], chart_type="line", delta_description="vs prior period")
    c4.metric("Plan attainment", pct(k["schedule_attainment"]), pp_delta(k["schedule_attainment"], pk["schedule_attainment"] if pk else None), chart_data=metric_trends["schedule_attainment"], chart_type="line", delta_description="vs prior period")
    c5.metric("Unit cost", euro(k["unit_cost"], 2), pct_delta(k["unit_cost"], pk["unit_cost"] if pk else None), delta_color="inverse", chart_data=metric_trends["unit_cost"], chart_type="line", delta_description="vs prior period")
    c6.metric("Gross margin", pct(k["gross_margin_rate"]), pp_delta(k["gross_margin_rate"], pk["gross_margin_rate"] if pk else None), chart_data=metric_trends["gross_margin_rate"], chart_type="line", delta_description="vs prior period")

    left, right = st.columns([1.55, 1])
    with left:
        trend = aggregate_trend(fprod, trend_granularity)
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend["date"], y=trend["planned_qty"], mode="lines", name="Plan", line=dict(width=2, dash="dot", color=COLORS["muted"])))
            fig.add_trace(go.Scatter(x=trend["date"], y=trend["good_qty"], mode="lines", name="Good output", line=dict(width=2.6, color=COLORS["primary"]), fill="tozeroy", fillcolor="rgba(77,163,255,.08)"))
            fig.update_layout(title=f"Output vs plan · {trend_granularity.lower()}")
            st.plotly_chart(style_figure(fig, 355, "x unified"), width="stretch")
    with right:
        if not mkdf.empty:
            ordered = mkdf.sort_values("oee", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=ordered["oee"], y=ordered["machine_id"], orientation="h",
                marker_color=[STATUS_COLORS[s] for s in ordered["status"]],
                text=[f"{v:.1%}" for v in ordered["oee"]], textposition="inside", name="OEE",
                hovertemplate="<b>%{y}</b><br>OEE %{x:.1%}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=ordered["target_oee"], y=ordered["machine_id"], mode="markers", name="Target",
                marker=dict(symbol="line-ns-open", size=18, line=dict(width=2), color="#FFFFFF"),
                hovertemplate="Target %{x:.1%}<extra></extra>",
            ))
            fig.update_xaxes(tickformat=".0%", range=[0, max(0.95, float(ordered["target_oee"].max()) + 0.06)])
            fig.update_layout(title="Machine OEE vs target", yaxis_title=None)
            st.plotly_chart(style_figure(fig, 355), width="stretch")

    opp = estimate_constraint_opportunity(fprod, machines)
    st.markdown(
        f"""
        <div class="opportunity-card">
          <div><span class="insight-label">CONSTRAINT RECOVERY OPPORTUNITY</span><h3>{opp['machine_id']} → target OEE {opp['target_oee']:.1%}</h3></div>
          <div class="opportunity-value"><span>≈ +{opp['additional_good_units_month']:,.0f}</span><small>good units / month</small></div>
          <div class="opportunity-value"><span>≈ +€{opp['additional_margin_month']:,.0f}</span><small>gross contribution / month</small></div>
          <div class="opportunity-note">Scenario holds observed performance & quality constant and recovers the availability required to reach the asset target.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Management Insights")
    st.caption("Rule-based and fully traceable: every recommendation is calculated from the current filter context, not generated by an external AI service.")
    for insight in generate_insights(fprod, fdown, machines):
        render_insight_card(insight)

with tab_prod:
    st.markdown("#### Production performance")
    c1, c2, c3, c4, c5 = st.columns(5)
    good_hours = k["run_minutes"] / 60.0
    throughput = k["good_qty"] / good_hours if good_hours else 0.0
    c1.metric("Good units", f"{int(k['good_qty']):,}")
    c2.metric("Plan attainment", pct(k["schedule_attainment"]))
    c3.metric("Performance", pct(k["performance"]))
    c4.metric("Throughput", f"{throughput:,.1f} units/h")
    c5.metric("Energy / good unit", f"{k['energy_per_good_unit']:.2f} kWh")

    monthly = fprod.assign(month=fprod["date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(
        planned_qty=("planned_qty", "sum"), good_qty=("good_qty", "sum"), scrap_qty=("scrap_qty", "sum")
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["good_qty"], name="Good output", marker_color=COLORS["primary"]))
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["scrap_qty"], name="Scrap", marker_color=COLORS["critical"]))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["planned_qty"], name="Plan", mode="lines+markers", line=dict(color=COLORS["muted"], dash="dot")))
    fig.update_layout(title="Monthly production performance", barmode="stack")
    st.plotly_chart(style_figure(fig, 390, "x unified"), width="stretch")

    left, right = st.columns(2)
    with left:
        product_rows = []
        for pid, g in fprod.groupby("product_id"):
            pkpi = calculate_kpis(g)
            product_rows.append({"product_id": pid, "good_qty": pkpi["good_qty"], "attainment": pkpi["schedule_attainment"], "scrap_rate": pkpi["scrap_rate"]})
        pdf = pd.DataFrame(product_rows).sort_values("good_qty", ascending=False)
        fig = px.bar(pdf, x="product_id", y="good_qty", text_auto=",.0f", title="Good output by product")
        fig.update_traces(marker_color=COLORS["secondary"])
        st.plotly_chart(style_figure(fig, 340), width="stretch")
    with right:
        shift_rows = []
        for shift, g in fprod.groupby("shift"):
            sk = calculate_kpis(g)
            shift_rows.append({"shift": shift, "OEE": sk["oee"], "Plan attainment": sk["schedule_attainment"]})
        sdf = pd.DataFrame(shift_rows)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sdf["shift"], y=sdf["OEE"], name="OEE", marker_color=COLORS["primary"], text=[f"{x:.1%}" for x in sdf["OEE"]], textposition="auto"))
        fig.add_trace(go.Scatter(x=sdf["shift"], y=sdf["Plan attainment"], name="Plan attainment", mode="markers+lines", marker=dict(size=10, color=COLORS["watch"])))
        fig.update_yaxes(tickformat=".0%", range=[0, max(1.02, float(sdf[["OEE", "Plan attainment"]].max().max()) + 0.05)])
        fig.update_layout(title="Shift comparison")
        st.plotly_chart(style_figure(fig, 340), width="stretch")

with tab_quality:
    st.markdown("#### Quality intelligence")
    scrap_cost = float(((fprod["production_cost_eur"] / fprod["total_qty"].replace(0, pd.NA)) * fprod["scrap_qty"]).sum()) if not fprod.empty else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality rate", pct(k["quality"]))
    c2.metric("Scrap rate", pct(k["scrap_rate"]))
    c3.metric("Scrap units", f"{int(fprod['scrap_qty'].sum()):,}")
    c4.metric("Estimated scrap cost", euro(scrap_cost))

    left, right = st.columns([1.25, 1])
    with left:
        qby = fquality.groupby("defect_type", as_index=False)["defect_count"].sum().sort_values("defect_count", ascending=False)
        qby = qby[qby["defect_count"] > 0].copy()
        if not qby.empty:
            qby["cum_share"] = qby["defect_count"].cumsum() / qby["defect_count"].sum()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=qby["defect_type"], y=qby["defect_count"], name="Defects", marker_color=COLORS["critical"]), secondary_y=False)
            fig.add_trace(go.Scatter(x=qby["defect_type"], y=qby["cum_share"], name="Cumulative share", mode="lines+markers", line=dict(color=COLORS["watch"])), secondary_y=True)
            fig.update_yaxes(title_text="Defect count", secondary_y=False)
            fig.update_yaxes(title_text="Cumulative", tickformat=".0%", range=[0, 1.08], secondary_y=True)
            fig.update_layout(title="Defect Pareto · 80/20 view")
            st.plotly_chart(style_figure(fig, 390), width="stretch")
    with right:
        heat = weighted_scrap_matrix(fprod)
        if not heat.empty:
            fig = px.imshow(heat, text_auto=".1%", aspect="auto", title="Weighted scrap rate · machine × product", color_continuous_scale="YlOrRd")
            fig.update_coloraxes(colorbar_tickformat=".1%")
            st.plotly_chart(style_figure(fig, 390), width="stretch")

    qtrend = fprod.assign(month=fprod["date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(scrap_qty=("scrap_qty", "sum"), total_qty=("total_qty", "sum"))
    qtrend["scrap_rate"] = qtrend["scrap_qty"] / qtrend["total_qty"].replace(0, pd.NA)
    fig = go.Figure(go.Scatter(x=qtrend["month"], y=qtrend["scrap_rate"], mode="lines+markers", fill="tozeroy", line=dict(color=COLORS["critical"])))
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(title="Scrap-rate trend")
    st.plotly_chart(style_figure(fig, 300, "x unified"), width="stretch")

with tab_down:
    st.markdown("#### Downtime & loss analysis")
    unplanned = fdown[~fdown["planned"].astype(bool)].copy()
    total_down_h = float(fdown["duration_min"].sum() / 60.0)
    unplanned_h = float(unplanned["duration_min"].sum() / 60.0)
    mttr = float(unplanned["duration_min"].mean()) if not unplanned.empty else 0.0
    unplanned_share = unplanned_h / total_down_h if total_down_h else 0.0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total downtime", f"{total_down_h:,.1f} h")
    c2.metric("Unplanned downtime", f"{unplanned_h:,.1f} h")
    c3.metric("Unplanned share", pct(unplanned_share))
    c4.metric("Mean event duration", f"{mttr:.1f} min")
    c5.metric("Downtime events", f"{len(fdown):,}")

    left, right = st.columns([1.25, 1])
    with left:
        reason = unplanned.groupby("reason", as_index=False)["duration_min"].sum().sort_values("duration_min", ascending=False).head(10)
        if not reason.empty:
            reason["cum_share"] = reason["duration_min"].cumsum() / reason["duration_min"].sum()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=reason["reason"], y=reason["duration_min"] / 60.0, name="Hours", marker_color=COLORS["watch"]), secondary_y=False)
            fig.add_trace(go.Scatter(x=reason["reason"], y=reason["cum_share"], name="Cumulative", mode="lines+markers", line=dict(color=COLORS["critical"])), secondary_y=True)
            fig.update_yaxes(title_text="Unplanned hours", secondary_y=False)
            fig.update_yaxes(tickformat=".0%", range=[0, 1.08], secondary_y=True)
            fig.update_layout(title="Unplanned downtime Pareto")
            st.plotly_chart(style_figure(fig, 390), width="stretch")
    with right:
        cat = fdown.groupby(["machine_id", "category"], as_index=False)["duration_min"].sum()
        cat["hours"] = cat["duration_min"] / 60.0
        fig = px.bar(cat, x="machine_id", y="hours", color="category", title="Downtime composition by machine")
        st.plotly_chart(style_figure(fig, 390), width="stretch")

    dtrend = unplanned.assign(week=unplanned["date"].dt.to_period("W").dt.start_time).groupby("week", as_index=False)["duration_min"].sum() if not unplanned.empty else pd.DataFrame()
    if not dtrend.empty:
        dtrend["hours"] = dtrend["duration_min"] / 60.0
        fig = go.Figure(go.Scatter(x=dtrend["week"], y=dtrend["hours"], mode="lines", fill="tozeroy", line=dict(color=COLORS["watch"])))
        fig.update_layout(title="Weekly unplanned downtime")
        st.plotly_chart(style_figure(fig, 300, "x unified"), width="stretch")

with tab_cost:
    st.markdown("#### Manufacturing economics")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", euro(k["revenue"]))
    c2.metric("Production cost", euro(k["production_cost"]))
    c3.metric("Gross margin", euro(k["gross_margin"]))
    c4.metric("Gross margin %", pct(k["gross_margin_rate"]))
    c5.metric("Unit cost", euro(k["unit_cost"], 2))

    monthly = fprod.assign(month=fprod["date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(revenue=("revenue_eur", "sum"), cost=("production_cost_eur", "sum"))
    monthly["margin"] = monthly["revenue"] - monthly["cost"]
    monthly["margin_rate"] = monthly["margin"] / monthly["revenue"].replace(0, pd.NA)
    left, right = st.columns([1.35, 1])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["revenue"], name="Revenue", mode="lines+markers", line=dict(color=COLORS["primary"])))
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["cost"], name="Production cost", mode="lines+markers", line=dict(color=COLORS["watch"])))
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["margin"], name="Gross margin", mode="lines+markers", line=dict(color=COLORS["good"])))
        fig.update_layout(title="Monthly revenue, cost & contribution")
        st.plotly_chart(style_figure(fig, 370, "x unified"), width="stretch")
    with right:
        fig = go.Figure(go.Scatter(x=monthly["month"], y=monthly["margin_rate"], mode="lines+markers", fill="tozeroy", line=dict(color=COLORS["good"])))
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(title="Gross-margin rate")
        st.plotly_chart(style_figure(fig, 370, "x unified"), width="stretch")

    machine_cost = machine_kpi_frame(fprod, machines)
    left, right = st.columns(2)
    with left:
        fig = px.scatter(machine_cost, x="oee", y="unit_cost", size="good_qty", text="machine_id", color="status", color_discrete_map=STATUS_COLORS,
                         title="Efficiency vs unit cost", labels={"oee": "OEE", "unit_cost": "Unit cost (€)"})
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_figure(fig, 350), width="stretch")
        st.caption("Unit cost is product-mix sensitive. Filter to a comparable product set for like-for-like asset analysis.")
    with right:
        product_fin = fprod.groupby("product_id", as_index=False).agg(revenue=("revenue_eur", "sum"), cost=("production_cost_eur", "sum"))
        product_fin["margin_rate"] = (product_fin["revenue"] - product_fin["cost"]) / product_fin["revenue"].replace(0, pd.NA)
        fig = px.bar(product_fin.sort_values("margin_rate"), x="margin_rate", y="product_id", orientation="h", text_auto=".1%", title="Gross-margin rate by product")
        fig.update_xaxes(tickformat=".0%")
        fig.update_traces(marker_color=COLORS["good"])
        st.plotly_chart(style_figure(fig, 350), width="stretch")

with tab_scenario:
    st.markdown("#### Scenario Lab · operational what-if")
    st.caption("Use observed production economics to quantify a controlled improvement scenario. This is a deterministic decision model, not a demand forecast.")
    scenario_machine = st.selectbox(
        "Asset to improve",
        selected_machines,
        index=selected_machines.index(str(mkdf.iloc[0]["machine_id"])) if not mkdf.empty and str(mkdf.iloc[0]["machine_id"]) in selected_machines else 0,
        format_func=lambda x: f"{x} · {machine_names.get(x, x)}",
    )
    sm = fprod[fprod["machine_id"] == scenario_machine].copy()
    sk = calculate_kpis(sm)

    s1, s2, s3 = st.columns(3)
    availability_gain = s1.slider("Availability improvement", 0.0, 20.0, 5.0, 0.5, format="+%.1f pp")
    performance_gain = s2.slider("Performance improvement", 0.0, 8.0, 2.0, 0.5, format="+%.1f pp")
    max_scrap_gain = min(3.0, round(sk["scrap_rate"] * 100, 1))
    scrap_reduction = s3.slider("Scrap-rate reduction", 0.0, float(max_scrap_gain), min(0.5, float(max_scrap_gain)), 0.1, format="-%.1f pp")

    scenario = simulate_operational_scenario(sm, availability_gain, performance_gain, scrap_reduction)
    days = max(1, (end_date - start_date).days + 1)
    annual_factor = 365.25 / days

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OEE", pct(scenario["scenario_oee"]), f"{(scenario['scenario_oee'] - scenario['current_oee']) * 100:+.1f} pp")
    c2.metric("Additional good units", f"{scenario['additional_good_units']:,.0f}")
    c3.metric("Revenue opportunity", euro(scenario["additional_revenue"]))
    c4.metric("Gross contribution", euro(scenario["additional_gross_margin"]))

    left, right = st.columns([1, 1.15])
    with left:
        comp = pd.DataFrame({
            "Component": ["Availability", "Performance", "Quality", "OEE"],
            "Current": [sk["availability"], sk["performance"], sk["quality"], sk["oee"]],
            "Scenario": [scenario["scenario_availability"], scenario["scenario_performance"], scenario["scenario_quality"], scenario["scenario_oee"]],
        })
        fig = go.Figure()
        fig.add_trace(go.Bar(x=comp["Component"], y=comp["Current"], name="Current", marker_color=COLORS["muted"]))
        fig.add_trace(go.Bar(x=comp["Component"], y=comp["Scenario"], name="Scenario", marker_color=COLORS["good"]))
        fig.update_yaxes(tickformat=".0%", range=[0, 1.02])
        fig.update_layout(title=f"{scenario_machine} · current vs scenario", barmode="group")
        st.plotly_chart(style_figure(fig, 360), width="stretch")
    with right:
        st.markdown(
            f"""
            <div class="scenario-summary">
              <span class="insight-label">ANNUALISED RUN-RATE IF THIS WINDOW IS REPRESENTATIVE</span>
              <div class="scenario-big">≈ {scenario['additional_good_units'] * annual_factor:,.0f} additional good units / year</div>
              <div class="scenario-big">≈ €{scenario['additional_gross_margin'] * annual_factor:,.0f} additional gross contribution / year</div>
              <p>The scenario keeps the same production plan and product mix. It improves only the selected A/P/Q levers and values extra output using observed revenue and gross contribution per good unit.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Model assumptions & limitations"):
            st.markdown(
                """
                - Fixed planned production minutes and product mix.
                - No change in demand, selling price or downstream capacity.
                - Availability, performance and quality changes are independent scenario inputs.
                - Incremental gross contribution uses the observed contribution per good unit; it is not a full finance forecast.
                - Use this as decision-support sizing, not as a guaranteed savings claim.
                """
            )

with tab_data:
    st.markdown("#### Data Explorer · trace every KPI to row-level evidence")
    st.caption("A dashboard should be auditable. The tables below expose the filtered source rows used by the current analysis.")
    prod_tab, down_tab, q_tab = st.tabs(["Production orders", "Downtime events", "Quality checks"])
    with prod_tab:
        display_cols = ["order_id", "date", "shift", "machine_id", "product_id", "planned_qty", "good_qty", "scrap_qty", "availability", "performance", "quality", "oee", "unit_cost_eur", "revenue_eur"]
        st.dataframe(fprod[display_cols].sort_values("date", ascending=False), width="stretch", height=470)
        st.download_button("Download production CSV", fprod.to_csv(index=False).encode("utf-8"), "production_filtered.csv", "text/csv")
    with down_tab:
        st.dataframe(fdown.sort_values("date", ascending=False), width="stretch", height=470)
        st.download_button("Download downtime CSV", fdown.to_csv(index=False).encode("utf-8"), "downtime_filtered.csv", "text/csv")
    with q_tab:
        st.dataframe(fquality.sort_values("date", ascending=False), width="stretch", height=470)
        st.download_button("Download quality CSV", fquality.to_csv(index=False).encode("utf-8"), "quality_filtered.csv", "text/csv")

    with st.expander("KPI definitions & modelling notes"):
        st.markdown(
            """
            **OEE = Availability × Performance × Quality**  
            **Availability** = Run Time / Planned Production Time  
            **Performance** = (Ideal Cycle Time × Total Count) / Run Time  
            **Quality** = Good Count / Total Count  
            **Plan attainment** = Good Count / Planned Quantity  
            **Unit cost** = Production Cost / Good Count  
            **Gross margin rate** = (Revenue − Production Cost) / Revenue

            Ratios are recomputed from additive components at the selected filter level. The application never averages row-level OEE percentages.
            """
        )

st.markdown("---")
st.markdown(
    """
    <div class="footer-line">
      <span><b>Built by Aarón Expósito</b> · Engineering + Data & Business Analytics</span>
      <span>CSV → Python ETL → SQLite star schema → SQL KPI layer → Streamlit decision app</span>
    </div>
    """,
    unsafe_allow_html=True,
)
