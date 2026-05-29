"""股票数据获取模块 - 基于tdxpy(通达信) + akshare获取A股行情数据"""
import re
from typing import Optional, Any
from datetime import datetime

import akshare as ak
import requests
from bs4 import BeautifulSoup

from tdx_client import TdxClient
from tdxpy.constants import TDXParams


# ── 工具函数 ──────────────────────────────────────────────

def is_a_stock(code: str) -> bool:
    return bool(re.match(r'^\d{6}$', code.strip()))


def is_h_stock(code: str) -> bool:
    return bool(re.match(r'^\d{5}(\.HK)?$', code.strip().upper()))


def normalize_code(code: str) -> str:
    code = code.strip().upper()
    if code.endswith(".HK"):
        return code
    if is_a_stock(code):
        return code
    if is_h_stock(code):
        return code if code.endswith(".HK") else f"{code}.HK"
    return code


# ── 实时行情（tdxpy） ──────────────────────────────

def get_realtime_quotes(codes: list[tuple[int, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    # a_codes = [c.strip().upper() for c in codes if c.strip() and is_a_stock(c)]

    if codes:
        tdx = TdxClient()
        # params = [(TdxClient.market_of(c), c) for c in a_codes]
        quotes = tdx.get_quotes(codes)
        for q in quotes:
            results.append({
                "code": q.get("code", ""), "name": "",
                "market": q.get("market", 0),
                "price": float(q.get("price", 0)),
                "change": float(q.get("change", 0)),
                "change_pct": float(q.get("change_pct", 0)),
                "high": float(q.get("high", 0)),
                "low": float(q.get("low", 0)),
                "open": float(q.get("open", 0)),
                "volume": float(q.get("vol", 0)),
                "amount": float(q.get("amount", 0)),
                "turnover": 0.0,
                "time": str(q.get("servertime", ""))[:8],
            })
    return results


# ── K线数据（tdxpy） ──────────────────────────────

def get_kline_data(code: str, market: int, period: str = "daily",
                   count: int = 180) -> list[dict[str, Any]]:
    # 指数走akshare腾讯接口
    if TdxClient.is_index(code, market):
        return get_index_kline_data(code, period, count)
    pm = {"1min": 8, "5min": 0, "daily": 9, "weekly": 5, "monthly": 6}
    ktype = pm.get(period, 9)
    tdx = TdxClient()
    bars = tdx.get_bars(ktype, market, code, 0, count)
    result = []
    for b in bars:
        y = int(b.get("year", 0) or 0)
        m = int(b.get("month", 0) or 0)
        d = int(b.get("day", 0) or 0)
        h = int(b.get("hour", 0) or 0)
        mi = int(b.get("minute", 0) or 0)
        # 过滤TDX返回的异常数据（指数K线偶有乱码）
        if y < 2000 or y > 2030 or m < 1 or m > 12 or d < 1 or d > 31:
            continue
        ds = f"{y:04d}-{m:02d}-{d:02d} {h:02d}:{mi:02d}"
        result.append({
            "date": ds,
            "open": float(b.get("open", 0)),
            "high": float(b.get("high", 0)),
            "low": float(b.get("low", 0)),
            "close": float(b.get("close", 0)),
            "volume": float(b.get("vol", 0)),
            "amount": float(b.get("amount", 0) or 0),
        })
    return result


def get_index_kline_data(code: str, period: str = "daily",
                         count: int = 180) -> list[dict[str, Any]]:
    """获取指数K线数据（通过akshare腾讯接口）"""
    # 新浪前缀: sh000001, sz399001
    sym = f"sh{code}" if code.startswith("00") else f"sz{code}"
    try:
        import akshare as ak
        if period == "daily":
            df = ak.stock_zh_index_daily_tx(symbol=sym)
        elif period == "weekly":
            df = ak.stock_zh_index_daily_tx(symbol=sym)
            df = df.resample("W-FRI", on="date").agg(
                {"open": "first", "high": "max", "low": "min",
                 "close": "last", "volume": "sum"}
            ).dropna().reset_index()
        elif period == "monthly":
            df = ak.stock_zh_index_daily_tx(symbol=sym)
            df = df.resample("ME", on="date").agg(
                {"open": "first", "high": "max", "low": "min",
                 "close": "last", "volume": "sum"}
            ).dropna().reset_index()
        else:
            return []

        if df is None or df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            dt = row.get("date", "")
            ds = str(dt)[:19] if not isinstance(dt, str) else dt[:19]
            result.append({
                "date": ds,
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": float(row.get("volume", row.get("amount", 0))),
                "amount": float(row.get("amount", 0)),
            })
        return result[-count:]
    except Exception as e:
        print(f"获取指数K线失败: {e}")
        return []


def get_stock_history(code: str, period: str = "daily",
                      start_date=None, end_date=None) -> str:
    try:
        bars = get_kline_data(code, market=TdxClient.market_of(code), period=period, count=60)
        if not bars:
            return f"未获取到 {code} 的历史数据"
        lines = [f"{code} {period} ({len(bars)}条):"]
        for b in bars:
            pct = ((b["close"]-b["open"])/b["open"]*100) if b["open"] else 0
            lines.append(f"  {b['date']} 收:{b['close']:.2f} 高:{b['high']:.2f} "
                         f"低:{b['low']:.2f} 量:{b['volume']:.0f} 涨跌:{pct:+.2f}%")
        return "\n".join(lines)
    except Exception as e:
        return f"获取 {code} 历史数据出错: {e}"


# ── 其他数据（akshare补充） ─────────────────────────

def get_stock_financial(code: str) -> str:
    try:
        s = code.strip().upper().replace(".SH","").replace(".SZ","")
        if ".HK" in s or s.endswith("HK"):
            return "港股财务数据暂不支持"
        df = ak.stock_financial_abstract(symbol=s)
        return df.head(5).to_string(index=False) if df is not None and not df.empty else f"未获取到 {code} 的财务数据"
    except Exception as e:
        return f"获取 {code} 财务数据出错: {e}"


def search_stock(query: str) -> list[dict[str, str]]:
    try:
        df = ak.stock_info_a_code_name()
        m = df[df["code"].str.contains(query,na=False) | df["name"].str.contains(query,na=False)]
        return [{"code": r["code"], "name": r["name"]} for _, r in m.iterrows()]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []


def get_market_overview() -> str:
    try:
        tdx = TdxClient()
        # 上证指数(000001)=上海市场(1), 深证成指(399001)=深圳市场(0), 创业板指(399006)=深圳市场(0)
        qs = tdx.get_quotes([(1,"000001"),(0,"399001"),(0,"399006")])
        ns = {"000001":"上证指数","399001":"深证成指","399006":"创业板指"}
        lines = ["大盘概况:"]
        for q in qs:
            c, pct = q.get("code",""), q.get("change_pct",0)
            lines.append(f"  {'🔴' if pct<0 else '🟢'} {ns.get(c,c)}: {q.get('price',0):.2f} ({pct:+.2f}%)")
        return "\n".join(lines) if len(lines)>1 else "获取大盘数据失败"
    except Exception as e:
        return f"获取大盘数据出错: {e}"


def get_sector_performance() -> str:
    try:
        df = ak.stock_board_industry_name_em()
        if df is not None and not df.empty:
            top = df.head(5)
            return "热门板块TOP5:\n" + "\n".join(f"  {r.get('板块名称','')}: {r.get('涨跌幅','')}%" for _, r in top.iterrows())
        return "获取板块数据失败"
    except Exception as e:
        return f"获取板块数据出错: {e}"


def get_stock_industry_concept(code: str) -> str:
    try:
        raw = code.strip().upper().replace(".SH","").replace(".SZ","")
        if ".HK" in raw: return f"{code} 暂不支持港股"
        r = requests.get(f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpOtherInfo/stockid/{raw}/menu_num/2.phtml",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        r.encoding = "gbk"
        soup = BeautifulSoup(r.text, "html.parser")
        industry, concepts, section = "", [], ""
        for tr in soup.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            line = " ".join(tds)
            if "行业板块" in line: section="industry"; continue
            if "概念板块" in line: section="concept"; continue
            if "所属地域" in line or "备注" in line or not tds or not tds[0]: continue
            v = tds[0]
            if section=="industry" and v not in["点击查看",""]: industry=v
            elif section=="concept" and v not in["点击查看",""]: concepts.append(v)
        seen=set(); uc=[c for c in concepts if not(c in seen or seen.add(c))]
        if not industry and not uc: return f"未获取到 {code} 的板块信息"
        lines=[f"📌 {code} 板块分析"]
        if industry: lines.append(f"\n🏭 {industry}")
        if uc:
            lines.append(f"\n💡 概念板块 ({len(uc)}个):")
            for i in range(0,len(uc),5): lines.append("  "+"  ".join(f"#{c}" for c in uc[i:i+5]))
        return "\n".join(lines)
    except Exception as e:
        return f"获取 {code} 板块信息出错: {e}"
