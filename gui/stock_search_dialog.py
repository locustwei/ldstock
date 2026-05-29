"""股票搜索选择对话框 - 支持名称/代码/拼音首字母模糊匹配"""
from typing import Any

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)

import akshare as ak
from pypinyin import lazy_pinyin, Style


def _get_pinyin_initials(name: str) -> str:
    """获取中文名称的拼音首字母，如 '平安银行' → 'payh'"""
    try:
        initials = lazy_pinyin(name, style=Style.FIRST_LETTER)
        return "".join(initials).lower()
    except Exception:
        return ""


def _get_full_pinyin(name: str) -> str:
    """获取中文名称的全拼，如 '平安' → 'pingan'"""
    try:
        return "".join(lazy_pinyin(name)).lower()
    except Exception:
        return ""


class StockSearchDialog(QDialog):
    """股票搜索选择对话框"""

    _ALL_STOCKS: list[dict[str, str]] | None = None  # 类级别缓存

    COLUMNS = ["代码", "名称"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔍 选择股票")
        self.setMinimumSize(500, 500)
        self.resize(560, 600)
        self.setModal(True)

        # 选中的股票
        self.selected_stocks: list[dict[str, str]] = []

        self._init_ui()
        self._load_all_stocks()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── 搜索输入 ──
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "输入股票代码、名称或拼音首字母（如 000001、平安银行、payh）")
        self._search_input.setStyleSheet(
            "padding: 8px; font-size: 14px; border: 2px solid #4a90d9; "
            "border-radius: 6px;")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input, 1)
        layout.addLayout(search_layout)

        # ── 结果表格 ──
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #eee;
            }
            QHeaderView::section {
                background: #4a90d9;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:alternate { background: #f9f9f9; }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #1e3a5f;
            }
        """)
        layout.addWidget(self._table, 1)

        # ── 数量提示 ──
        info_layout = QHBoxLayout()
        self._result_count = QLabel("请输入搜索关键词")
        self._result_count.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(self._result_count, 1)
        layout.addLayout(info_layout)

        # ── 按钮 ──
        btn_layout = QHBoxLayout()
        self._select_btn = QPushButton("✅ 添加到监控")
        self._select_btn.setEnabled(False)
        self._select_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9; color: white; border: none;
                border-radius: 4px; padding: 8px 20px; font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #357abd; }
            QPushButton:disabled { background: #aaa; }
        """)
        self._select_btn.clicked.connect(self._confirm_selection)
        btn_layout.addWidget(self._select_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def _load_all_stocks(self) -> None:
        """加载全量股票列表（带缓存）"""
        if StockSearchDialog._ALL_STOCKS is None:
            try:
                df = ak.stock_info_a_code_name()
                StockSearchDialog._ALL_STOCKS = []
                for _, row in df.iterrows():
                    code = str(row["code"])
                    name = str(row["name"])
                    # 预计算拼音索引
                    pinyin_initials = _get_pinyin_initials(name)
                    full_pinyin = _get_full_pinyin(name)
                    StockSearchDialog._ALL_STOCKS.append({
                        "code": code,
                        "name": name,
                        "pinyin": pinyin_initials,
                        "full_pinyin": full_pinyin,
                    })
                self._result_count.setText(
                    f"已加载 {len(StockSearchDialog._ALL_STOCKS)} 只股票，输入关键词搜索")
            except Exception as e:
                self._result_count.setText(f"加载股票列表失败: {e}")
                StockSearchDialog._ALL_STOCKS = []
        else:
            self._result_count.setText(
                f"已加载 {len(StockSearchDialog._ALL_STOCKS)} 只股票，输入关键词搜索")

    def _on_search_changed(self, text: str) -> None:
        """实时搜索"""
        keyword = text.strip().lower()
        if not keyword:
            self._table.setRowCount(0)
            self._result_count.setText("请输入搜索关键词")
            self._select_btn.setEnabled(False)
            return

        stocks = StockSearchDialog._ALL_STOCKS or []
        results = []
        for s in stocks:
            if (keyword in s["code"].lower()
                    or keyword in s["name"]
                    or keyword in s["pinyin"]
                    or keyword in s["full_pinyin"]):
                results.append(s)
                if len(results) >= 50:  # 限制最多显示50条
                    break

        self._populate_results(results)

    def _populate_results(self, results: list[dict]) -> None:
        self._table.setRowCount(len(results))
        for row, s in enumerate(results):
            code_item = QTableWidgetItem(s["code"])
            code_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, code_item)

            name_item = QTableWidgetItem(s["name"])
            self._table.setItem(row, 1, name_item)

            # 存储完整数据
            code_item.setData(Qt.UserRole, s)

        self._result_count.setText(
            f"找到 {len(results)} 只匹配的股票"
            if results else "未找到匹配的股票")
        self._select_btn.setEnabled(len(results) > 0)
        self._table.resizeColumnsToContents()

    def _confirm_selection(self) -> None:
        """确认选择"""
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在表格中选择股票（可多选）")
            return

        self.selected_stocks = []
        for row in sorted(selected_rows):
            item = self._table.item(row, 0)
            if item:
                s = item.data(Qt.UserRole)
                if s:
                    self.selected_stocks.append(s)

        self.accept()
