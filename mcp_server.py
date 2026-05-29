"""
MCP (Model Context Protocol) 服务器模块
将akshare数据接口封装为MCP工具，供DeepSeek调用
支持stdio和SSE传输方式
"""
import logging

from mcp.server.fastmcp import FastMCP

import stock_data as sd

logger = logging.getLogger(__name__)

# 创建MCP服务实例
mcp = FastMCP("ds_stock_mcp", instructions="A股/港股股票数据MCP服务")


# ── MCP工具定义 ──────────────────────────────────────

@mcp.tool()
def get_realtime_quote(codes: list[str]) -> str:
    """获取一只或多只股票的实时行情数据

    Args:
        codes: 股票代码列表，如 ["000001", "600519"]，港股需要.HK后缀如 ["00700.HK"]
    """
    quotes = sd.get_realtime_quotes(codes)
    if not quotes:
        return "未获取到行情数据，请检查股票代码是否正确"

    lines = ["📊 实时行情数据:"]
    for q in quotes:
        flag = "🔴" if q["change_pct"] < 0 else "🟢" if q["change_pct"] > 0 else "⚪"
        lines.append(
            f"  {flag} {q['code']} {q['name']} ({q['market']}) "
            f"最新: {q['price']:.2f}  "
            f"涨跌: {q['change']:+.2f}  "
            f"涨跌幅: {q['change_pct']:+.2f}%  "
            f"高: {q['high']:.2f} 低: {q['low']:.2f}  "
            f"量: {q['volume']:.0f} 额: {q['amount']:.0f}"
        )
    lines.append(f"⏰ {quotes[0]['time']}")
    return "\n".join(lines)


@mcp.tool()
def get_stock_history(code: str, period: str = "daily",
                      start_date: str = None, end_date: str = None) -> str:
    """获取股票历史K线数据

    Args:
        code: 股票代码，如 000001, 600519, 00700.HK
        period: K线周期 daily|weekly|monthly
        start_date: 起始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    """
    return sd.get_stock_history(code, period, start_date, end_date)


@mcp.tool()
def get_stock_financial(code: str) -> str:
    """获取股票财务数据摘要

    Args:
        code: 股票代码
    """
    return sd.get_stock_financial(code)


@mcp.tool()
def get_market_overview() -> str:
    """获取大盘指数概况"""
    return sd.get_market_overview()


@mcp.tool()
def get_sector_performance() -> str:
    """获取热门板块表现排名"""
    return sd.get_sector_performance()


@mcp.tool()
def get_stock_industry(code: str) -> str:
    """获取股票所属的行业板块和概念板块

    Args:
        code: 股票代码，如 000001, 600519
    """
    return sd.get_stock_industry_concept(code)


@mcp.tool()
def search_stock(query: str) -> str:
    """搜索股票代码或名称

    Args:
        query: 搜索关键词（股票代码或名称）
    """
    results = sd.search_stock(query)
    if not results:
        return "未找到匹配的股票"
    lines = ["🔍 搜索结果:"]
    for r in results[:20]:
        lines.append(f"  {r['code']} - {r['name']}")
    return "\n".join(lines)


# ── 启动入口 ──────────────────────────────────────────

def run_stdio() -> None:
    """以stdio模式运行MCP服务器（供IDE/CLI集成）"""
    mcp.run(transport="stdio")


def run_sse(host: str = "127.0.0.1", port: int = 8000) -> None:
    """以SSE模式运行MCP服务器（HTTP服务）"""
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    run_stdio()
