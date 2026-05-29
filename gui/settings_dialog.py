"""设置对话框 - 配置DeepSeek API Key和刷新间隔"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QGroupBox,
    QFormLayout, QMessageBox, QDialogButtonBox,
)

from config import Config


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._config = Config()
        self._changed = False
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── DeepSeek API设置 ──
        api_group = QGroupBox("🤖 DeepSeek API 设置")
        api_form = QFormLayout(api_group)

        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("输入你的DeepSeek API Key")
        self._api_key_input.setEchoMode(QLineEdit.Password)
        api_form.addRow("API Key:", self._api_key_input)

        self._show_key_btn = QPushButton("👁 显示")
        self._show_key_btn.setMaximumWidth(100)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        api_form.addRow("", self._show_key_btn)

        self._base_url_input = QLineEdit()
        self._base_url_input.setPlaceholderText("https://api.deepseek.com")
        api_form.addRow("Base URL:", self._base_url_input)

        layout.addWidget(api_group)

        # ── 刷新设置 ──
        refresh_group = QGroupBox("⏱ 数据刷新设置")
        refresh_form = QFormLayout(refresh_group)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(3, 300)
        self._interval_spin.setValue(10)
        self._interval_spin.setSuffix(" 秒")
        self._interval_spin.setToolTip("行情数据自动刷新间隔（3-300秒）")
        refresh_form.addRow("刷新间隔:", self._interval_spin)

        layout.addWidget(refresh_group)

        # ── 状态信息 ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

        # ── 按钮 ──
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("💾 保存", QDialogButtonBox.AcceptRole)
        save_btn.clicked.connect(self._save_settings)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.RejectRole)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self) -> None:
        key = self._config.deepseek_api_key
        if key:
            self._api_key_input.setText(key)
            self._status_label.setText("✅ API Key 已配置")
            self._status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
        else:
            self._status_label.setText("⚠️ 未配置 API Key，AI分析功能不可用")
            self._status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

        self._base_url_input.setText(self._config.deepseek_base_url)
        self._interval_spin.setValue(self._config.refresh_interval)

    def _toggle_key_visibility(self) -> None:
        if self._api_key_input.echoMode() == QLineEdit.Password:
            self._api_key_input.setEchoMode(QLineEdit.Normal)
            self._show_key_btn.setText("🙈 隐藏")
        else:
            self._api_key_input.setEchoMode(QLineEdit.Password)
            self._show_key_btn.setText("👁 显示")

    def _save_settings(self) -> None:
        api_key = self._api_key_input.text().strip()
        base_url = self._base_url_input.text().strip() or "https://api.deepseek.com"
        interval = self._interval_spin.value()

        if not api_key:
            ret = QMessageBox.question(
                self, "确认",
                "API Key 为空，AI分析功能将不可用。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        old_key = self._config.deepseek_api_key
        old_interval = self._config.refresh_interval

        self._config.deepseek_api_key = api_key
        self._config.deepseek_base_url = base_url
        self._config.refresh_interval = interval

        self._changed = (api_key != old_key or interval != old_interval)
        self.accept()

    @property
    def settings_changed(self) -> bool:
        return self._changed

    @property
    def api_key_changed(self) -> bool:
        return self._config.deepseek_api_key != ""
