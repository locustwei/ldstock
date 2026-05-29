#!/usr/bin/env python3
"""
A股/港股 AI 股票分析系统
基于 DeepSeek + akshare + PyQt5 构建
"""
import sys
import os

# 高DPI支持：必须在 QApplication 创建之前设置
if "QT_AUTO_SCREEN_SCALE_FACTOR" not in os.environ:
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
if "QT_ENABLE_HIGHDPI_SCALING" not in os.environ:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
# 可选：指定自定义缩放因子
# os.environ["QT_SCALE_FACTOR"] = "1.25"

# Matplotlib Qt5Agg 后端：必须在任何 matplotlib 导入前设置
if "MPLBACKEND" not in os.environ:
    os.environ["MPLBACKEND"] = "Qt5Agg"

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from gui.main_window import MainWindow


def main() -> None:
    # 启用高DPI属性（必须在 QApplication 创建前调用）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("A股/港股 AI 股票分析系统")

    # 设置中文字体（使用系统默认字体的适当字号）
    font = QFont()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
