import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Engineer Alpha Risk Tool", layout="centered")
st.title("Engineer Alpha 风险等级 & 建仓建议（内测）")

# ---------- 核心逻辑：A(风险) + B(建议) ----------
def calc_risk_and_action(df: pd.DataFrame):
    """
    输入: df (含 Close)
    输出: (risk_label, action_label, reason)
    规则(最小版):
      - 趋势: 50日均线 vs 200日均线
      - 回撤: 距离近一年最高点的回撤
      - 波动: 20日收益率标准差(年化近似)
    """
    close = df["Close"]

    # 如果 Close 取出来还是一个 DataFrame（多列/多层），取第一列压成 Series
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = close.dropna()

    ma50 = close.rolling(50).mean().iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1]

    peak_1y = close.tail(252).max()
    dd = (close.iloc[-1] - peak_1y) / peak_1y  # 回撤为负数

    ret = close.pct_change().dropna()
    vol20 = ret.tail(20).std() * np.sqrt(252)

    # --- A：风险等级（先给风险） ---
    score = 0

    # 趋势：ma50>ma200 视为偏强，否则偏弱
    score += 1 if ma50 > ma200 else -1

    # 回撤：越深越危险
    if dd <= -0.35:
        score -= 2
    elif dd <= -0.20:
        score -= 1
    elif dd >= -0.08:
        score += 1

    # 波动：过大视为风险提升
    if vol20 > 0.80:
        score -= 1
    elif vol20 < 0.45:
        score += 1

    if score >= 2:
        risk = "🟢 低风险"
    elif score <= -2:
        risk = "🔴 高风险"
    else:
        risk = "🟡 中等风险"

    # --- B：建仓建议（由 A 映射出来） ---
    if "🟢" in risk:
        action = "✅ 可以开始（分批）"
    elif "🟡" in risk:
        action = "⏸ 等待更好位置 / 小仓试探"
    else:
        action = "❌ 不建议建仓（先观望）"

    reason = f"趋势(ma50 {'>' if ma50>ma200 else '<='} ma200)｜近1年回撤 {dd*100:.1f}%｜波动(年化) {vol20*100:.0f}%"
    return risk, action, reason


# ---------- UI ----------
ticker = st.text_input("输入股票代码", value="MSTR")
run = st.button("计算")

if run:
    with st.spinner("拉取数据并计算中..."):
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)

    if df is None or df.empty or "Close" not in df.columns:
        st.error("数据拉取失败：请检查代码是否正确，或换一个标的再试。")
    else:
        risk, action, reason = calc_risk_and_action(df)

        st.subheader("结果")
        st.write(f"**① 当前风险等级：** {risk}")
        st.write(f"**② 是否适合建仓：** {action}")
        st.write(f"**③ 理由：** {reason}")

        st.subheader("价格走势（近2年）")
        st.line_chart(df["Close"])