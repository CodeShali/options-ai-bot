"""
Streamlit web dashboard for TARA — performance overview and system status.
Auto-refreshes every 30 seconds via st_autorefresh.
"""

import sys
from pathlib import Path

# Allow imports from the v2 package root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from db.database import (
    get_all_time_pnl,
    get_open_trades,
    get_performance_stats,
    get_state,
    get_trade_history,
    get_weekly_pnl,
    get_weekly_trade_count,
    init_db,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TARA Options Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-refresh every 30 seconds
st_autorefresh(interval=30_000, key="dashboard_refresh")

init_db()

# ── Sidebar — system status ───────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ System Status")

    mode    = get_state("trading_mode") or "paper"
    auto    = get_state("auto_trade") or "false"
    paused  = get_state("scanning_paused") or "false"
    weekly  = get_weekly_trade_count()
    wpnl    = get_weekly_pnl()

    mode_color   = "🔴" if mode == "live" else "📝"
    auto_icon    = "✅" if auto == "true" else "⏸"
    scan_icon    = "⛔" if paused == "true" else "🟢"

    st.metric("Trading Mode",  f"{mode_color} {mode.upper()}")
    st.metric("Auto-Trade",    f"{auto_icon} {'ON' if auto == 'true' else 'OFF'}")
    st.metric("Scanning",      f"{scan_icon} {'PAUSED' if paused == 'true' else 'ACTIVE'}")

    st.divider()
    st.metric("Trades This Week", f"{weekly} / 3")
    st.metric("Weekly P&L",       f"${wpnl:+.2f}")

    st.divider()
    st.caption("Auto-refreshes every 30 s")

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 TARA Options Bot — Dashboard")

# ── Top metrics row ───────────────────────────────────────────────────────────

stats   = get_performance_stats()
total   = get_all_time_pnl()
wr      = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
rr      = abs(stats["avg_win"] / stats["avg_loss"]) if stats["avg_loss"] != 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("All-Time P&L",  f"${total:+.2f}")
c2.metric("Weekly P&L",    f"${wpnl:+.2f}")
c3.metric("Win Rate",      f"{wr:.0f}%")
c4.metric("Total Trades",  stats["total"])
c5.metric("Avg R/R",       f"{rr:.2f}x")

st.divider()

# ── Open positions ────────────────────────────────────────────────────────────

st.subheader("Open Positions")
open_trades = get_open_trades()
if open_trades:
    df_open = pd.DataFrame(open_trades)
    display_cols = [c for c in ["symbol", "option_type", "strike", "expiry", "entry_price", "contracts", "entry_time"] if c in df_open.columns]
    st.dataframe(df_open[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("No open positions.")

# ── Charts row ────────────────────────────────────────────────────────────────

st.subheader("Performance Charts")
col_left, col_right = st.columns(2)

history = get_trade_history(limit=100)

with col_left:
    st.markdown("**Cumulative P&L**")
    if history:
        closed = [t for t in history if t.get("status") != "open" and t.get("pnl") is not None]
        if closed:
            df_hist = pd.DataFrame(closed)
            df_hist = df_hist.sort_values("exit_time")
            df_hist["cumulative_pnl"] = df_hist["pnl"].cumsum()
            fig = px.line(
                df_hist,
                x="exit_time",
                y="cumulative_pnl",
                labels={"exit_time": "Date", "cumulative_pnl": "P&L ($)"},
                color_discrete_sequence=["#00cc96"],
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No closed trades yet.")
    else:
        st.info("No trade history.")

with col_right:
    st.markdown("**Win / Loss Breakdown**")
    if stats["total"] > 0:
        fig2 = go.Figure(go.Pie(
            labels=["Wins", "Losses"],
            values=[stats["wins"], stats["losses"]],
            marker_colors=["#00cc96", "#ef553b"],
            hole=0.45,
            textinfo="label+percent",
        ))
        fig2.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=280, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No trade data yet.")

# ── Trade history table ───────────────────────────────────────────────────────

st.subheader("Recent Trades (last 20)")
if history:
    df_trades = pd.DataFrame(history[:20])

    def _row_icon(row):
        if row.get("status") == "open":
            return "⏳"
        return "✅" if (row.get("pnl") or 0) > 0 else "❌"

    df_trades.insert(0, "", df_trades.apply(_row_icon, axis=1))

    show_cols = [c for c in ["", "symbol", "option_type", "strike", "expiry", "entry_price", "exit_price", "pnl", "pnl_pct", "exit_reason", "entry_time", "exit_time"] if c in df_trades.columns]

    if "pnl_pct" in df_trades.columns:
        df_trades["pnl_pct"] = df_trades["pnl_pct"].apply(
            lambda v: f"{v:+.1f}%" if v is not None else ""
        )
    if "pnl" in df_trades.columns:
        df_trades["pnl"] = df_trades["pnl"].apply(
            lambda v: f"${v:+.2f}" if v is not None else ""
        )

    st.dataframe(df_trades[show_cols], use_container_width=True, hide_index=True)
else:
    st.info("No trade history yet.")

# ── P&L per-symbol bar chart ──────────────────────────────────────────────────

if history:
    closed = [t for t in history if t.get("pnl") is not None and t.get("status") != "open"]
    if closed:
        st.subheader("P&L by Symbol")
        df_sym = (
            pd.DataFrame(closed)
            .groupby("symbol", as_index=False)["pnl"]
            .sum()
            .sort_values("pnl", ascending=False)
        )
        colors = ["#00cc96" if v >= 0 else "#ef553b" for v in df_sym["pnl"]]
        fig3 = go.Figure(go.Bar(
            x=df_sym["symbol"],
            y=df_sym["pnl"],
            marker_color=colors,
            text=df_sym["pnl"].apply(lambda v: f"${v:+.2f}"),
            textposition="outside",
        ))
        fig3.update_layout(
            yaxis_title="P&L ($)",
            margin=dict(l=0, r=0, t=20, b=0),
            height=280,
        )
        st.plotly_chart(fig3, use_container_width=True)
