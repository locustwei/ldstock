"""股票行情图 - 用mplfinance打开独立交互窗口"""
import sys
import traceback

import pandas as pd
import mplfinance as mpf
import matplotlib
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

from stock_data import get_kline_data, get_realtime_quotes


def _bars_to_mpf_df(bars: list[dict]) -> pd.DataFrame:
    """将K线数据转为mplfinance格式"""
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame(bars)
    df["Date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
    })
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("Date")


_MPF_STYLE = mpf.make_mpf_style(
    base_mpf_style="charles",
    rc={"font.sans-serif": ["Microsoft YaHei", "SimHei"],
        "axes.unicode_minus": False},
)


def show_stock_chart(code: str, market: int) -> None:
    """用mplfinance打开股票行情图窗口（单窗口，键盘切换视图）"""
    from tdx_client import TdxClient
    try:
        daily = get_kline_data(code, market, "daily", 180)
    except Exception as e:
        print(f"获取 {code} K线数据失败: {e}")
        return
    df_daily = _bars_to_mpf_df(daily)
    if df_daily.empty or len(df_daily) < 2:
        print(f"暂无 {code} 的K线数据")
        return

    df_weekly = df_daily.resample("W-FRI").agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    ).dropna()

    df_monthly = df_daily.resample("ME").agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    ).dropna()

    # ── 实时分时数据 ──
    intra = get_kline_data(code, market, "1min", 240)
    df_intra = _bars_to_mpf_df(intra)

    # 追加最新实时行情作为最后一个点
    if not df_intra.empty:
        try:
            rt = get_realtime_quotes([code])
            if rt:
                now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                last_row = df_intra.iloc[-1]
                new_row = pd.DataFrame([{
                    "Open": rt[0]["price"],
                    "High": max(rt[0]["high"], last_row["High"]),
                    "Low": min(rt[0]["low"], last_row["Low"]),
                    "Close": rt[0]["price"],
                    "Volume": rt[0].get("volume", 0),
                }], index=pd.DatetimeIndex([pd.Timestamp(now)], name="Date"))
                df_intra = pd.concat([df_intra, new_row])
        except Exception:
            pass

    views = []
    if not df_intra.empty and len(df_intra) >= 5:
        views.append(("⏱ 分时", df_intra, "line", (5,), "%H:%M"))
    views.append(("📅 日K", df_daily, "candle", (5, 10, 20), "%m-%d"))
    if len(df_weekly) >= 3:
        views.append(("📆 周K", df_weekly, "candle", (5, 10), "%Y-%m"))
    if len(df_monthly) >= 3:
        views.append(("📊 月K", df_monthly, "candle", (5, 10), "%Y-%m"))

    if not views:
        print(f"暂无 {code} 的图表数据")
        return

    # ── 自定义Qt对话框 ──
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    )
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

    class _ChartDialog(QDialog):
        def __init__(self):
            super().__init__(None)
            self.setWindowTitle(f"📊 {code} 行情图")
            self.setMinimumSize(1000, 650)
            self.resize(1100, 700)
            self._current = 0
            self._init_ui()

        def _init_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(4, 4, 4, 4)

            # Matplotlib 画布
            self._canvas = FigureCanvasQTAgg(plt.figure(figsize=(11, 7)))
            layout.addWidget(self._canvas, 1)

            # 按钮栏
            btn_layout = QHBoxLayout()
            self._btns = []
            for i, (name, *_) in enumerate(views):
                btn = QPushButton(name)
                btn.setCheckable(True)
                btn.setStyleSheet(self._btn_style(False))
                btn.clicked.connect(lambda checked, idx=i: self._draw_view(idx))
                self._btns.append(btn)
                btn_layout.addWidget(btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)

            # 初始绘图
            self._draw_view(0)

        def _btn_style(self, active: bool) -> str:
            if active:
                return (
                    "QPushButton { background:#4a90d9; color:white; border:none; "
                    "border-radius:4px; padding:6px 16px; font-weight:bold; font-size:13px; }"
                )
            return (
                "QPushButton { background:#f0f0f0; color:#333; border:1px solid #ccc; "
                "border-radius:4px; padding:6px 16px; font-size:13px; }"
                "QPushButton:hover { background:#e0e0e0; }"
            )

        def _draw_view(self, idx: int):
            self._current = idx
            name, df, ctype, mav, dtfmt = views[idx]

            # 更新按钮高亮
            for i, btn in enumerate(self._btns):
                btn.setChecked(i == idx)
                btn.setStyleSheet(self._btn_style(i == idx))
            self.setWindowTitle(f"📊 {code}  {name}线")

            # 绘制图表
            fig = self._canvas.figure
            fig.clf()
            gs = fig.add_gridspec(2, 1, height_ratios=[5, 2], hspace=0.12)
            ax = fig.add_subplot(gs[0])
            ax_vol = fig.add_subplot(gs[1])
            mpf.plot(df, type=ctype, volume=ax_vol, mav=mav,
                     style=_MPF_STYLE, xrotation=0, datetime_format=dtfmt,
                     ax=ax, axtitle=f"{code} {name}线",
                     tight_layout=True)
            fig.suptitle(f"{code} 行情图", fontsize=12, fontweight="bold", y=0.98)
            self._canvas.draw()

        def keyPressEvent(self, event):
            from PyQt5.QtCore import Qt as QtCore
            if event.key() == QtCore.Key_Right:
                self._draw_view((self._current + 1) % len(views))
            elif event.key() == QtCore.Key_Left:
                self._draw_view((self._current - 1) % len(views))
            elif event.key() in (QtCore.Key_Escape, QtCore.Key_Q):
                self.close()
            else:
                super().keyPressEvent(event)

    # 显示对话框
    try:
        dialog = _ChartDialog()
        dialog.exec()
    except Exception as e:
        print(f"打开行情图失败: {e}")
        traceback.print_exc()
