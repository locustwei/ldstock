"""主窗口 - 左右分栏布局"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter,
    QMessageBox, QLabel, QDialog, QAction,
    QToolBar,
)

from config import Config
from gui.market_monitor import MarketMonitorPanel
from gui.ai_analysis import AiAnalysisPanel
from gui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        super().__init__()
        self._config = Config()
        self._init_ui()
        self._create_menu()
        self._create_toolbar()
        self._create_status_bar()

    def _init_ui(self) -> None:
        self.setWindowTitle("📊 A股/港股 AI 股票分析系统")
        self.setMinimumSize(1400, 800)
        self.resize(1600, 900)

        # 应用全局样式
        self.setStyleSheet("""
            QMainWindow {
                background: #f0f2f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #333;
            }
            QPushButton {
                padding: 6px 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #fff;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #e8e8e8;
                border-color: #aaa;
            }
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #4a90d9;
            }
        """)

        # ── 中间分割器 ──
        self._splitter = QSplitter(Qt.Horizontal)

        # 左侧：行情监控
        self._monitor_panel = MarketMonitorPanel()
        self._splitter.addWidget(self._monitor_panel)

        # 右侧：AI分析
        self._analysis_panel = AiAnalysisPanel()
        self._splitter.addWidget(self._analysis_panel)

        # 设置分割比例 4:6
        self._splitter.setSizes([640, 960])
        self._splitter.setHandleWidth(3)
        self._splitter.setStyleSheet("""
            QSplitter::handle {
                background: #4a90d9;
                width: 3px;
            }
        """)

        self.setCentralWidget(self._splitter)

        # 记录左侧面板宽度，用于恢复
        self._monitor_visible = True
        self._monitor_last_width = 640

        # 连接信号
        self._monitor_panel.stock_count_changed.connect(
            self._on_stock_count_changed)

    def _create_menu(self) -> None:
        menubar = self.menuBar()

        # ── 文件菜单 ──
        file_menu = menubar.addMenu("📁 文件")

        settings_action = QAction("⚙️ 设置...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("❌ 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ── 视图菜单 ──
        view_menu = menubar.addMenu("👁 视图")

        self._toggle_monitor_action = QAction("🙈 隐藏行情监控", self)
        self._toggle_monitor_action.setShortcut("Ctrl+B")
        self._toggle_monitor_action.triggered.connect(self._toggle_monitor)
        view_menu.addAction(self._toggle_monitor_action)

        view_menu.addSeparator()

        refresh_action = QAction("🔄 刷新行情", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_all)
        view_menu.addAction(refresh_action)

        # ── 帮助菜单 ──
        help_menu = menubar.addMenu("❓ 帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _toggle_monitor(self) -> None:
        """切换左侧行情监控面板的显示/隐藏"""
        if self._monitor_visible:
            # 隐藏前记住当前宽度
            sizes = self._splitter.sizes()
            if sizes:
                self._monitor_last_width = sizes[0]
            self._monitor_panel.hide()
            self._monitor_visible = False
            self._toggle_monitor_action.setText("👁 显示行情监控")
        else:
            self._monitor_panel.show()
            self._monitor_visible = True
            self._toggle_monitor_action.setText("🙈 隐藏行情监控")
            # 恢复之前的宽度
            current = self._splitter.sizes()
            if current:
                total = current[0] + (current[1] if len(current) > 1 else 0)
                self._splitter.setSizes([self._monitor_last_width, total - self._monitor_last_width])

    def _create_toolbar(self) -> None:
        """创建顶部工具栏"""
        toolbar = QToolBar("查看")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: #e8eaf6;
                border-bottom: 1px solid #ddd;
                spacing: 4px;
                padding: 2px 8px;
            }
        """)
        toolbar.addAction(self._toggle_monitor_action)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

    def _create_status_bar(self) -> None:
        status = self.statusBar()
        status.setStyleSheet("""
            QStatusBar {
                background: #e8eaf6;
                border-top: 1px solid #ddd;
                padding: 2px 8px;
            }
        """)

        self._stock_count_label = QLabel("📈 监控: 0 只")
        status.addPermanentWidget(self._stock_count_label)

        self._api_status_label = QLabel(
            "✅ API已配置" if self._config.has_api_key
            else "⚠️ 未配置API Key")
        self._api_status_label.setStyleSheet(
            "color: #27ae60;" if self._config.has_api_key
            else "color: #e67e22;")
        status.addPermanentWidget(self._api_status_label)

        self._interval_label = QLabel(
            f"⏱ 刷新: 每{self._config.refresh_interval}秒")
        status.addPermanentWidget(self._interval_label)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            if dialog.settings_changed:
                # 更新状态栏
                self._api_status_label.setText(
                    "✅ API已配置" if self._config.has_api_key
                    else "⚠️ 未配置API Key")
                self._api_status_label.setStyleSheet(
                    "color: #27ae60;" if self._config.has_api_key
                    else "color: #e67e22;")
                self._interval_label.setText(
                    f"⏱ 刷新: 每{self._config.refresh_interval}秒")

                # 通知面板更新
                self._analysis_panel.update_api_key()
                self._monitor_panel.restart_timer()

    def _refresh_all(self) -> None:
        """手动刷新所有数据"""
        refresh_method = getattr(self._monitor_panel, '_refresh_data', None)
        if refresh_method:
            refresh_method()

    def _on_stock_count_changed(self, count: int) -> None:
        self._stock_count_label.setText(f"📈 监控: {count} 只")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 - A股/港股 AI 股票分析系统",
            "<h3>📊 A股/港股 AI 股票分析系统</h3>"
            "<p>基于 DeepSeek + akshare + PyQt6 构建</p>"
            "<p>功能特性：</p>"
            "<ul>"
            "<li>📈 实时A股/港股行情监控</li>"
            "<li>🤖 AI智能股票分析（DeepSeek驱动）</li>"
            "<li>🔄 自动定时刷新数据</li>"
            "<li>📊 技术面+基本面综合分析</li>"
            "</ul>"
            "<p>数据来源: akshare 金融数据库</p>"
            "<p>AI模型: DeepSeek</p>"
        )
