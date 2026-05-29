"""行情监控面板 - 左侧区域"""
from typing import Any
from datetime import datetime
from tdxpy.constants import TDXParams

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QDialog,
    QListWidget, QListWidgetItem, QAbstractItemView,
)

from config import Config
from stock_data import get_realtime_quotes, is_a_stock, search_stock
from gui.stock_search_dialog import StockSearchDialog
from gui.stock_chart import show_stock_chart
from tdx_client import TdxClient

# 默认大盘指数
_DEFAULT_INDICES = [
    {"code": "000001", "name": "上证指数", "market": TDXParams.MARKET_SH},
    {"code": "399001", "name": "深证成指", "market": TDXParams.MARKET_SZ},
    {"code": "000688", "name": "科创50", "market": TDXParams.MARKET_SH},
    {"code": "399006", "name": "创业板指", "market": TDXParams.MARKET_SZ}
]
# 沪深 300：sh000300
# 中证 500：sh000905

class MarketMonitorPanel(QWidget):
    """行情监控面板"""

    stock_count_changed = pyqtSignal(int)

    COLUMNS = ["代码", "名称", "市场", "最新价", "涨跌幅%", "涨跌额", "最高", "最低", "成交量", "成交额"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = Config()
        self._stock_list: list[dict] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_data)
        self._init_ui()
        self._load_saved_stocks()
        self._start_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── 标题 ──
        title = QLabel("📈 行情监控")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        # ── 添加股票区域 ──
        add_group = QGroupBox("添加股票")
        add_layout = QHBoxLayout(add_group)

        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("输入股票代码，如 000001,600519,00700.HK")
        self._code_input.returnPressed.connect(self._add_stock)
        add_layout.addWidget(self._code_input, 1)

        self._add_btn = QPushButton("添加")
        self._add_btn.clicked.connect(self._add_stock)
        add_layout.addWidget(self._add_btn)

        self._search_btn = QPushButton("🔍 股票选择")
        self._search_btn.setStyleSheet(
            "background: #4a90d9; color: white; border: none; "
            "padding: 6px 14px; border-radius: 4px; font-weight: bold;")
        self._search_btn.clicked.connect(self._open_stock_search)
        add_layout.addWidget(self._search_btn)

        self._remove_btn = QPushButton("删除选中")
        self._remove_btn.clicked.connect(self._remove_selected)
        add_layout.addWidget(self._remove_btn)

        layout.addWidget(add_group)

        # ── 行情数据表格 ──
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #eee;
            }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section {
                background: #4a90d9;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:alternate { background: #f9f9f9; }
            QTableWidget::item:selected {
                background: #c1d9f0;
                color: #0a1e3a;
            }
        """)
        self._table.cellDoubleClicked.connect(self._on_table_dbl_click)
        layout.addWidget(self._table, 1)

        # ── 状态信息 ──
        status_layout = QHBoxLayout()
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_layout.addWidget(self._status_label, 1)

        self._refresh_now_btn = QPushButton("🔄 立即刷新")
        self._refresh_now_btn.clicked.connect(self._refresh_data)
        status_layout.addWidget(self._refresh_now_btn)

        layout.addLayout(status_layout)

    def _in_list(self, code: str, market: int = None) -> bool:
        return any(info["code"] == code and info.get("market") == market for info in self._stock_list)

    def _add_stock(self) -> None:
        text = self._code_input.text().strip()
        if not text:
            return

        # 支持逗号、空格、分号分隔多个代码
        import re
        codes = re.split(r'[,;\s]+', text)
        codes = [c.strip().upper() for c in codes if c.strip()]

        added = 0
        for code in codes:
            if not is_a_stock(code):
                continue
            market = TdxClient.market_of(code)
            # 检查是否已存在（去重）
            if self._in_list(code, market):
                continue
            results = search_stock(code)
            name = code
            if results:
                for r in results:
                    if r["code"] == code:
                        name = r['name']
                        break
            self._stock_list.append({"code": code, "name": name, "market": market})
            added += 1

        if added > 0:
            self._code_input.clear()
            self._save_stock_list()
            self._refresh_data()

    def _open_stock_search(self) -> None:
        """打开股票搜索选择对话框"""
        dialog = StockSearchDialog(self)
        if dialog.exec() == QDialog.Accepted:
            added = 0
            for s in dialog.selected_stocks:
                code = s["code"].strip().upper()
                market = TdxClient.market_of(code)
                if any(info["code"] == code and info.get("market") == market for info in self._stock_list):
                    continue
                display = f"{code} - {s['name']}"
                self._stock_list.append({"code": code, "name": display, "market": market})
                added += 1

            if added > 0:
                self._save_stock_list()
                self._refresh_data()

    def _remove_selected(self) -> None:
        rows = sorted(set(item.row() for item in self._table.selectedItems()), reverse=True)
        for row in rows:
            code_item = self._table.item(row, 0)
            if code_item is None:
                continue
            code = code_item.text().strip()
            # 按显示代码匹配删除
            to_del = [info for info in self._stock_list if info["code"] == code]
            for info in to_del:
                self._stock_list.remove(info)
            self._table.removeRow(row)
        self._save_stock_list()
        self._refresh_data()

    def _load_saved_stocks(self) -> None:
        codes = self._config.monitor_stocks
        if codes:
            self._stock_list = codes
        else:
            # 首次启动，添加默认大盘指数（带市场前缀）
            self._stock_list = _DEFAULT_INDICES
            self._save_stock_list()
        self._refresh_data()

    def _save_stock_list(self) -> None:
        self._config.monitor_stocks = self._stock_list
        self.stock_count_changed.emit(len(self._stock_list))

    def _start_timer(self) -> None:
        interval = self._config.refresh_interval * 1000
        self._timer.start(interval)

    def restart_timer(self) -> None:
        """刷新间隔更改后重启定时器"""
        self._timer.stop()
        self._start_timer()

    def _refresh_data(self) -> None:
        codes = []
        for info in self._stock_list:
            sub_dict = [info["market"], info["code"]]
            codes.append(sub_dict)

        if not codes:
            self._status_label.setText("暂无监控股票，请添加")
            return

        self._status_label.setText(f"🔄 刷新中... ({datetime.now().strftime('%H:%M:%S')})")
        self._refresh_now_btn.setEnabled(False)

        # 提取代码列表传给数据层（数据层用 market_of 判断市场）
        quotes = get_realtime_quotes(codes)
        # 补全名称
        for q in quotes:
            if not q.get("name"):
                c = q.get("code", "")
                for info in self._stock_list:
                    if info["code"] == c and info["market"] == q.get("market", 0):
                        q["name"] = info["name"]
                        break
        self._populate_table(quotes)

        self._status_label.setText(
            f"✅ 已更新 {len(quotes)} 只股票 ({datetime.now().strftime('%H:%M:%S')})  "
            f"下次刷新: 每{self._config.refresh_interval}秒"
        )
        self._refresh_now_btn.setEnabled(True)

    def _populate_table(self, quotes: list[dict[str, Any]]) -> None:
        self._table.setRowCount(len(quotes))

        for row, q in enumerate(quotes):
            items_data = [
                (q.get("code", ""), None),
                (q.get("name", ""), None),
                (
                    "上海" if q.get("market", 0) == TDXParams.MARKET_SH else "深圳" if q.get("market", 0) == TDXParams.MARKET_SZ else "北京" if q.get("market", 0) == TDXParams.MARKET_BJ else "未知",
                    None
                ),
                # (q.get("market", ""), None),
                (f"{q.get('price', 0):.2f}", None),
                (f"{q.get('change_pct', 0):+.2f}%",
                 QColor("#27ae60") if q.get("change_pct", 0) < 0
                 else QColor("#e74c3c") if q.get("change_pct", 0) > 0
                 else None),
                (f"{q.get('change', 0):+.2f}",
                 QColor("#27ae60") if q.get("change", 0) < 0
                 else QColor("#e74c3c") if q.get("change", 0) > 0
                 else None),
                (f"{q.get('high', 0):.2f}", None),
                (f"{q.get('low', 0):.2f}", None),
                (f"{q.get('volume', 0):.0f}", None),
                (f"{q.get('amount', 0):.0f}", None),
            ]

            for col, (text, color) in enumerate(items_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if color:
                    item.setForeground(QBrush(color))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self._table.setItem(row, col, item)

        self._table.resizeColumnsToContents()

    def _on_table_dbl_click(self, row: int, column: int) -> None:
        """双击表格行，打开K线图窗口"""
        item = self._stock_list[row] if row < len(self._stock_list) else None
        if item is None:
            return
        code = item.get("code", "")
        market = item.get("market", 0)
        try:
            show_stock_chart(code, market)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"打开 {code} 行情图失败: {e}")

