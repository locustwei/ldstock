# 📊 A股/港股 AI 股票分析系统

基于 **DeepSeek + akshare + PyQt6 + MCP** 构建的股票分析桌面应用。

## 功能特性

- **📈 实时行情监控** — 添加A股/港股股票代码，自动获取实时行情，定时刷新
- **🤖 AI智能分析** — 选择股票，提出问题，DeepSeek自动从akshare获取数据并分析
- **⚙️ 灵活配置** — 自定义DeepSeek API Key、数据刷新间隔

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 DeepSeek API Key

前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并获取 API Key。

### 3. 运行

```bash
python main.py
```

启动后，通过 **文件 → 设置** 配置你的 API Key。

## 项目结构

```
ds_stock/
├── main.py                  # 程序入口
├── config.py                # 配置管理（API Key、刷新间隔）
├── stock_data.py            # akshare数据获取模块
├── deepseek_client.py       # DeepSeek API客户端（含函数调用）
├── mcp_server.py            # MCP服务器（可选独立运行）
├── gui/
│   ├── __init__.py
│   ├── main_window.py       # 主窗口（左右分栏）
│   ├── market_monitor.py    # 左侧行情监控面板
│   ├── ai_analysis.py       # 右侧AI分析面板
│   └── settings_dialog.py   # 设置对话框
├── config.json              # 自动生成的配置文件
└── requirements.txt         # 依赖清单
```

## 使用说明

### 行情监控（左侧）
1. 在输入框中输入股票代码，点击"添加"
2. 支持 A 股代码（如 `000001`、`600519`、`300750`）+ 港股代码（如 `00700.HK`、`09988.HK`）
3. 支持批量添加，用逗号或空格分隔
4. 数据自动定时刷新，也可点击"立即刷新"

### AI分析（右侧）
1. 从左侧同步监控列表，或手动输入股票代码
2. 在输入框中输入问题，点击"发送"
3. 支持快捷问题模板
4. DeepSeek 会自动调用工具获取实时数据后进行分析回答

### 设置
- **文件 → 设置** 或 `Ctrl+,`
- 配置 DeepSeek API Key
- 自定义数据刷新间隔（3-300秒）

## MCP 服务器

支持独立运行 MCP 服务器：

```bash
# stdio模式
python -c "from mcp_server import run_stdio; run_stdio()"

# SSE模式（HTTP服务）
python -c "from mcp_server import run_sse; run_sse()"
```

## 数据来源

所有行情数据通过 [akshare](https://github.com/akfamily/akshare) 获取，感谢 akfamily 的开源贡献。

## 风险提示

⚠️ 本系统仅提供数据展示和分析参考，不构成任何投资建议。股市有风险，投资需谨慎。
