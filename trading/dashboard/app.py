"""
TradingClaw Dashboard — Streamlit web UI.
Shows active strategies, backtests, P&L, logs, and chat interface.
"""

import os
import json
import glob
import datetime
import pandas as pd
import streamlit as st
from pathlib import Path

# Paths
WORKSPACE = Path("trading/workspace")
STRATEGIES_DIR = WORKSPACE / "strategies"
LOG_DIR = Path("trading/logs")
DATA_DIR = Path("trading/data")

st.set_page_config(
    page_title="TradingClaw Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    st.title("TradingClaw Dashboard")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Chat", "Strategies", "Backtest", "Live Trading", "Logs", "Settings"],
    )

    if page == "Chat":
        render_chat()
    elif page == "Strategies":
        render_strategies()
    elif page == "Backtest":
        render_backtest()
    elif page == "Live Trading":
        render_live_trading()
    elif page == "Logs":
        render_logs()
    elif page == "Settings":
        render_settings()


def render_chat():
    """Chat interface with Claude trading agent."""
    st.header("Chat with TradingClaw")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask TradingClaw anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from trading.prompts.claude_integration import chat
                    response, history = chat(
                        prompt,
                        st.session_state.conversation_history,
                    )
                    st.session_state.conversation_history = history
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {e}\n\nMake sure ANTHROPIC_API_KEY is set in trading/.env"
                    st.error(error_msg)

    # Quick action buttons
    st.divider()
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Create RSI+EMA Strategy"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Create a 4h BTC strategy with RSI + EMA crossover, test 8 variants on BTC+ETH+SOL"
            })
            st.rerun()

    with col2:
        if st.button("Fetch BTC/ETH/SOL Data"):
            with st.spinner("Fetching data..."):
                try:
                    from trading.engine.data_fetcher import fetch_multi_asset
                    results = fetch_multi_asset()
                    st.success(f"Fetched data for: {list(results.keys())}")
                except Exception as e:
                    st.error(f"Error fetching data: {e}")

    with col3:
        if st.button("Show Latest Results"):
            results = load_latest_results()
            if results:
                st.json(results)
            else:
                st.info("No backtest results found yet.")


def render_strategies():
    """Show and manage strategies."""
    st.header("Strategies")

    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    strategy_files = sorted(glob.glob(str(STRATEGIES_DIR / "*.json")))

    if not strategy_files:
        st.info("No strategies created yet. Use the Chat to create one.")
        return

    for filepath in strategy_files:
        with open(filepath) as f:
            strategy = json.load(f)

        with st.expander(f"{strategy.get('name', 'unnamed')} — {strategy.get('timeframe', '?')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Direction:** {strategy.get('direction', 'long')}")
                st.write(f"**Indicators:** {len(strategy.get('indicators', []))}")
                st.write(f"**Description:** {strategy.get('description', 'N/A')}")
            with col2:
                st.json(strategy)

            # Actions
            bcol1, bcol2, bcol3 = st.columns(3)
            with bcol1:
                if st.button(f"Backtest {strategy['name']}", key=f"bt_{filepath}"):
                    run_backtest_ui(strategy)
            with bcol2:
                if st.button(f"Pine Script {strategy['name']}", key=f"ps_{filepath}"):
                    generate_pine_ui(strategy)
            with bcol3:
                if st.button(f"Delete {strategy['name']}", key=f"del_{filepath}"):
                    os.remove(filepath)
                    st.rerun()


def render_backtest():
    """Backtest runner and results viewer."""
    st.header("Backtesting")

    # Results viewer
    st.subheader("Recent Results")
    result_files = sorted(
        glob.glob(str(WORKSPACE / "backtest_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )

    if not result_files:
        st.info("No backtest results yet. Create and test a strategy first.")
        return

    for filepath in result_files[:10]:
        with open(filepath) as f:
            result = json.load(f)

        name = result.get("strategy_name", "unknown")
        with st.expander(f"{name} — {result.get('timestamp', '?')[:19]}"):
            # Summary metrics
            cols = st.columns(5)
            cols[0].metric("Avg Return", f"{result.get('avg_net_profit_pct', 0):.1f}%")
            cols[1].metric("Avg Max DD", f"{result.get('avg_max_drawdown_pct', 0):.1f}%")
            cols[2].metric("Avg Sharpe", f"{result.get('avg_sharpe_ratio', 0):.3f}")
            cols[3].metric("Avg Win Rate", f"{result.get('avg_win_rate_pct', 0):.1f}%")
            cols[4].metric("Assets Tested", result.get("assets_tested", 0))

            # Per-asset breakdown
            per_asset = result.get("per_asset_results", [])
            if per_asset:
                df = pd.DataFrame(per_asset)
                st.dataframe(df, use_container_width=True)

            # Equity curve
            equity_file = WORKSPACE / f"equity_{name}.csv"
            if equity_file.exists():
                eq_df = pd.read_csv(equity_file, index_col=0, parse_dates=True)
                st.line_chart(eq_df)


def render_live_trading():
    """Live trading controls and monitoring."""
    st.header("Live Trading")

    from trading.live.executor import KillSwitch, ReadOnlyMode

    # Status indicators
    col1, col2 = st.columns(2)
    with col1:
        kill_active = KillSwitch.is_active()
        st.write(f"**Kill Switch:** {'ACTIVE (all trading halted)' if kill_active else 'Inactive'}")
        if kill_active:
            if st.button("Deactivate Kill Switch"):
                KillSwitch.deactivate()
                st.rerun()
        else:
            if st.button("ACTIVATE Kill Switch", type="primary"):
                KillSwitch.activate()
                st.rerun()

    with col2:
        ro_active = ReadOnlyMode.is_active()
        st.write(f"**Read-Only Mode:** {'ACTIVE (simulation only)' if ro_active else 'Inactive'}")
        if ro_active:
            if st.button("Disable Read-Only"):
                ReadOnlyMode.deactivate()
                st.rerun()
        else:
            if st.button("Enable Read-Only Mode"):
                ReadOnlyMode.activate()
                st.rerun()

    st.divider()

    # Active schedules
    st.subheader("Scheduled Strategies")
    schedule_file = WORKSPACE / "schedules.json"
    if schedule_file.exists():
        with open(schedule_file) as f:
            schedules = json.load(f)
        if schedules:
            for s in schedules:
                st.write(
                    f"**{s['strategy_name']}** — {s['symbol']} on {s['exchange']} "
                    f"every {s['interval_hours']}h, amount={s['amount']} "
                    f"({'testnet' if s.get('testnet') else 'MAINNET'})"
                )
        else:
            st.info("No scheduled strategies.")
    else:
        st.info("No scheduled strategies.")

    # Trade history
    st.subheader("Trade History")
    trade_log = LOG_DIR / "trade_history.jsonl"
    if trade_log.exists():
        trades = []
        with open(trade_log) as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
        if trades:
            df = pd.json_normalize([t.get("order", {}) for t in trades])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No trades recorded yet.")
    else:
        st.info("No trade history yet.")


def render_logs():
    """View system logs."""
    st.header("Logs")

    log_files = sorted(glob.glob(str(LOG_DIR / "*.log")))
    if not log_files:
        st.info("No log files yet.")
        return

    selected = st.selectbox("Log file", log_files)
    if selected:
        with open(selected) as f:
            content = f.read()
        st.code(content[-5000:] if len(content) > 5000 else content, language="text")


def render_settings():
    """Settings and configuration."""
    st.header("Settings")

    # API Key status
    st.subheader("API Keys")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    st.write(f"**Anthropic API Key:** {'Set' if api_key else 'NOT SET'}")
    if not api_key:
        st.warning("Set ANTHROPIC_API_KEY in trading/.env to enable Claude integration.")

    hl_key = os.getenv("HYPERLIQUID_SECRET_KEY", "")
    st.write(f"**Hyperliquid Key:** {'Set' if hl_key else 'NOT SET (read-only mode)'}")

    # Model selection
    st.subheader("Model Preferences")
    st.write("- **Complex tasks (strategy design):** Claude Opus 4")
    st.write("- **General tasks (analysis, chat):** Claude Sonnet 4.5")
    st.write("- **Simple tasks (validation):** Claude Haiku 4.5")

    # Data directory
    st.subheader("Data Files")
    data_files = sorted(glob.glob(str(DATA_DIR / "*.csv")))
    if data_files:
        for f in data_files:
            size = os.path.getsize(f) / 1024
            st.write(f"  {Path(f).name} — {size:.1f} KB")
    else:
        st.info("No data files. Fetch data or upload TradingView CSVs to trading/data/")


def run_backtest_ui(strategy):
    """Run a backtest from the UI."""
    data_files = sorted(glob.glob(str(DATA_DIR / "*.csv")))
    if not data_files:
        st.error("No data files found. Fetch data first or upload CSVs to trading/data/")
        return

    with st.spinner("Running backtest..."):
        try:
            from trading.engine.backtest import run_strategy, save_results
            results = run_strategy(strategy, data_files)
            filepath = save_results(results)
            st.success(f"Backtest complete! Results saved to {filepath}")
            st.json(results)
        except Exception as e:
            st.error(f"Backtest failed: {e}")


def generate_pine_ui(strategy):
    """Generate Pine Script from UI."""
    try:
        from trading.pinescript.generator import generate_pine_script, save_pine_script
        script = generate_pine_script(strategy)
        filepath = save_pine_script(strategy)
        st.success(f"Pine Script saved to {filepath}")
        st.code(script, language="javascript")
    except Exception as e:
        st.error(f"Pine Script generation failed: {e}")


def load_latest_results():
    """Load the most recent backtest result."""
    result_files = sorted(
        glob.glob(str(WORKSPACE / "backtest_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )
    if result_files:
        with open(result_files[0]) as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    main()
