@echo off
chcp 65001 >nul
echo ============================================
echo  打包 A股/港股 AI 股票分析系统
echo ============================================

cd /d "%~dp0"

set VENV_PYTHON=e:\Leadow\ds_stock\.venv\Scripts\python.exe

echo 清理上次构建...
rmdir /s /q dist\ds_stock 2>nul
rmdir /s /q build 2>nul
del ds_stock.spec 2>nul

echo.
echo 开始打包...

"%VENV_PYTHON%" -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "ds_stock" ^
    --noconfirm ^
    --clean ^
    --add-data "config.py;." ^
    --add-data "stock_data.py;." ^
    --add-data "deepseek_client.py;." ^
    --add-data "mcp_server.py;." ^
    --add-data "tdx_client.py;." ^
    --add-data "gui;gui" ^
    --hidden-import "PyQt5.sip" ^
    --hidden-import "PyQt5.QtCore" ^
    --hidden-import "PyQt5.QtGui" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --hidden-import "pandas" ^
    --hidden-import "numpy" ^
    --hidden-import "matplotlib" ^
    --hidden-import "mplfinance" ^
    --hidden-import "akshare" ^
    --hidden-import "requests" ^
    --hidden-import "bs4" ^
    --hidden-import "lxml" ^
    --hidden-import "pypinyin" ^
    --hidden-import "tdxpy" ^
    --hidden-import "tdxpy.hq" ^
    --hidden-import "tdxpy.constants" ^
    --hidden-import "openai" ^
    --hidden-import "mcp" ^
    --hidden-import "matplotlib.backends.backend_qt5agg" ^
    --hidden-import "matplotlib.backends.backend_qt5" ^
    --hidden-import "pandas.plotting._matplotlib" ^
    --add-data ".venv\Lib\site-packages\akshare\file_fold;akshare\file_fold" ^
    --collect-submodules "akshare" ^
    --collect-submodules "mplfinance" ^
    main.py

echo.
if exist "dist\ds_stock\ds_stock.exe" (
    echo 打包成功！
    echo 输出目录: dist\ds_stock\
    echo 运行: dist\ds_stock\ds_stock.exe
) else (
    echo 打包失败，请检查错误信息。
)

pause
