"""AI股票分析面板 - 右侧区域"""
import re

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QComboBox, QGroupBox,
    QMessageBox,
)

from config import Config
from deepseek_client import DeepSeekClient


# 正则：匹配股票代码（A股6位数字，港股5位数字+.HK）
_STOCK_CODE_RE = re.compile(r'\b(\d{6}|\d{5}\.HK)\b')


def _extract_codes(text: str) -> list[str]:
    """从文本中提取股票代码，去重并按出现顺序返回"""
    seen = set()
    codes = []
    for m in _STOCK_CODE_RE.finditer(text):
        code = m.group(1).upper()
        if not code.endswith('.HK') and not re.match(r'^\d{6}$', code):
            continue
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


class AiWorker(QThread):
    """后台AI分析工作线程"""
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client: DeepSeekClient,
                 messages: list[dict],
                 stock_codes: list[str]) -> None:
        super().__init__()
        self._client = client
        self._messages = messages
        self._stock_codes = stock_codes

    def run(self) -> None:
        try:
            result = self._client.chat(self._messages, self._stock_codes)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AiAnalysisPanel(QWidget):
    """AI股票分析面板"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = Config()
        self._client = DeepSeekClient()
        self._worker: AiWorker | None = None
        self._history: list[dict] = []  # 对话历史
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── 标题 ──
        title = QLabel("🤖 AI 股票分析")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        # ── 提示文字 ──
        hint = QLabel("💡 在问题中直接输入股票代码即可，例如：<i>分析 000001 的走势</i>")
        hint.setStyleSheet("color: #666; font-size: 12px; padding: 2px 4px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ── 聊天区域 ──
        chat_group = QGroupBox("对话分析")
        chat_layout = QVBoxLayout(chat_group)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                background: #ffffff;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        chat_layout.addWidget(self._chat_display, 1)

        # 提示模板
        template_layout = QHBoxLayout()
        self._template_combo = QComboBox()
        self._template_combo.addItems([
            "自定义问题...",
            "分析 000001 的技术面",
            "分析 600519 的基本面",
            "600519 近期走势如何？有什么投资建议？",
            "比较 000001 和 600519 的优劣",
            "总结 000001,600519,300750 的最新市场表现",
        ])
        self._template_combo.currentTextChanged.connect(self._on_template_changed)
        template_layout.addWidget(QLabel("快捷问题:"))
        template_layout.addWidget(self._template_combo, 1)
        chat_layout.addLayout(template_layout)

        # 输入区域
        input_layout = QHBoxLayout()
        self._question_input = QTextEdit()
        self._question_input.setPlaceholderText("输入问题，直接在文字中包含股票代码，如：分析 000001 的走势")
        self._question_input.setMaximumHeight(60)
        self._question_input.setStyleSheet(
            "border: 1px solid #ddd; border-radius: 4px; padding: 6px;")
        input_layout.addWidget(self._question_input, 1)

        self._send_btn = QPushButton("🚀 发送")
        self._send_btn.clicked.connect(self._send_question)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #357abd; }
            QPushButton:disabled { background: #aaa; }
        """)
        input_layout.addWidget(self._send_btn)

        self._clear_btn = QPushButton("🗑 清空")
        self._clear_btn.clicked.connect(self._clear_chat)
        input_layout.addWidget(self._clear_btn)

        chat_layout.addLayout(input_layout)

        layout.addWidget(chat_group, 1)

        # 初始提示
        self._append_message("系统",
            "👋 欢迎使用AI股票分析！在输入框中直接输入包含股票代码的问题即可。<br>"
            "例如：<i>分析 000001 的走势</i> 或 <i>比较 600519 和 000858</i>")

    def _on_template_changed(self, text: str) -> None:
        if text != "自定义问题...":
            self._question_input.setText(text)

    def _send_question(self) -> None:
        question = self._question_input.toPlainText().strip()
        if not question:
            QMessageBox.warning(self, "提示", "请输入问题")
            return

        # 从问题中提取股票代码
        codes = _extract_codes(question)
        if not codes:
            QMessageBox.warning(self, "提示", "请在问题中包含股票代码，例如：<i>分析 000001 的走势</i>")
            return

        if not self._client.is_ready:
            QMessageBox.warning(self, "提示", "请先在设置中配置DeepSeek API Key")
            return

        # 显示用户消息
        stock_str = ", ".join(codes)
        self._append_message("用户", f"{question}\n\n📊 涉及股票: {stock_str}")
        self._question_input.clear()
        self._send_btn.setEnabled(False)
        self._template_combo.setCurrentIndex(0)

        # 保存到对话历史
        self._history.append({
            "role": "user",
            "content": f"请分析股票 [{stock_str}] 的问题: {question}"
        })

        # 启动后台线程
        self._worker = AiWorker(
            self._client,
            list(self._history),
            codes,
        )
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: str) -> None:
        self._append_message("AI分析师", result)
        self._history.append({"role": "assistant", "content": result})
        self._send_btn.setEnabled(True)

    def _on_error(self, error: str) -> None:
        self._append_message("系统", f"❌ 出错了: {error}")
        self._send_btn.setEnabled(True)

    def _append_message(self, sender: str, content: str) -> None:
        # HTML转义用户内容中的特殊字符
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br>")

        if sender == "用户":
            html = (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0;">'
                '<tr><td style="background-color:#e8f0fe; color:#1a237e; '
                'padding:10px 14px; border-radius:8px; '
                'border-left:4px solid #5c6bc0; line-height:1.6;">'
                '<div style="font-size:12px; color:#5c6bc0; margin-bottom:4px; '
                'font-weight:bold;">\U0001F9D1 你</div>'
                + safe + '</td></tr></table>'
            )
        elif sender == "AI分析师":
            html = (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0;">'
                '<tr><td style="background-color:#fff8e1; color:#4e342e; '
                'padding:10px 14px; border-radius:8px; '
                'border-left:4px solid #ff8f00; line-height:1.6;">'
                '<div style="font-size:12px; color:#ff8f00; margin-bottom:4px; '
                'font-weight:bold;">\U0001F916 AI 分析师</div>'
                + safe + '</td></tr></table>'
            )
        else:
            html = (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0;">'
                '<tr><td style="background-color:#f5f5f5; color:#616161; '
                'padding:6px 14px; border-radius:8px; '
                'border-left:4px solid #bdbdbd; line-height:1.6; font-size:12px;">'
                '\u2139\uFE0F ' + safe + '</td></tr></table>'
            )

        cursor = self._chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        cursor.insertHtml('<br>')
        self._chat_display.setTextCursor(cursor)

    def _clear_chat(self) -> None:
        self._chat_display.clear()
        self._history.clear()
        self._append_message("系统", "👋 对话已清空，可以开始新的分析。")

    def update_api_key(self) -> None:
        """API Key变更后重新初始化客户端"""
        self._client.update_api_key()
