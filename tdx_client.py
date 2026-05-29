"""通达信数据客户端 - 连接池管理"""
from typing import Any, Optional
from tdxpy.hq import TdxHq_API
from tdxpy.constants import TDXParams

# 通达信行情服务器列表
_TDX_HOSTS = [
    ("上海电信主站Z1", "180.153.18.170", 7709),
    ("上海电信主站Z2", "180.153.18.171", 7709),
    ("北京联通主站Z1", "202.108.253.130", 7709),
    ("深圳电信主站Z1", "14.17.75.71", 7709),
    ("上证云成都电信一", "218.6.170.47", 7709),
]


class TdxClient:
    """通达信数据客户端（单例，连接复用）"""

    _instance: Optional["TdxClient"] = None

    def __new__(cls) -> "TdxClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._api: Optional[TdxHq_API] = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """连接到通达信服务器"""
        if self._api:
            try:
                self._api.disconnect()
            except Exception:
                pass

        self._api = TdxHq_API()
        for name, ip, port in _TDX_HOSTS:
            try:
                ret = self._api.connect(ip, port, time_out=3.0)
                if ret:
                    self._connected = True
                    return
            except Exception:
                continue
        self._connected = False

    def ensure_connected(self) -> bool:
        """确保连接可用，断线自动重连"""
        if not self._connected or not self._api:
            self._connect()
        return self._connected

    def get_quotes(self, codes: list[tuple[int, str]]) -> list[dict[str, Any]]:
        """获取实时行情 codes=[(market, code), ...]"""
        if not self.ensure_connected():
            return []
        try:
            result = self._api.get_security_quotes(codes)
            # 转dict
            quotes = []
            for q in result:
                if q and q.get("code"):
                    d = dict(q)
                    # 计算涨跌幅
                    last_close = d.get("last_close", 0) or 0
                    price = d.get("price", 0) or 0
                    if last_close:
                        d["change"] = round(price - last_close, 2)
                        d["change_pct"] = round((price - last_close) / last_close * 100, 2)
                    else:
                        d["change"] = 0.0
                        d["change_pct"] = 0.0
                    quotes.append(d)
            return quotes
        except Exception as e:
            print(f"TDX行情查询失败: {e}")
            self._connected = False
            return []

    def get_bars(self, kline_type: int, market: int, code: str,
                 start: int = 0, count: int = 200) -> list[dict[str, Any]]:
        """获取K线数据"""
        if not self.ensure_connected():
            return []
        try:
            result = self._api.get_security_bars(kline_type, market, code, start, count)
            if result:
                return [dict(b) for b in result if b]
            return []
        except Exception as e:
            print(f"TDX K线查询失败: {e}")
            self._connected = False
            return []

    def get_stock_list(self, market: int) -> list[dict[str, str]]:
        """获取某个市场的股票列表"""
        if not self.ensure_connected():
            return []
        try:
            count = self._api.get_security_count(market)
            stocks = self._api.get_security_list(market, 0)
            result = []
            if stocks:
                for s in stocks:
                    if s and s.get("code"):
                        result.append({
                            "code": s["code"],
                            "name": s.get("name", ""),
                        })
            return result
        except Exception as e:
            print(f"TDX股票列表查询失败: {e}")
            return []

    INDEX_MARKET: dict[str, int] = {
        "000001": TDXParams.MARKET_SH,  # 上证指数
        "000688": TDXParams.MARKET_SH,  # 科创50
        "399001": TDXParams.MARKET_SZ,  # 深证成指
        "399006": TDXParams.MARKET_SZ,  # 创业板指
    }

    @staticmethod
    def is_index(code: str, market: int) -> bool:
        m = TdxClient.INDEX_MARKET.get(code.strip().upper())
        return m is not None and m == market

    @staticmethod
    def market_of(code: str) -> int:
        c = code.strip().upper().replace(".SH", "").replace(".SZ", "")
        if c in TdxClient.INDEX_MARKET:
            return TdxClient.INDEX_MARKET[c]
        if c.startswith('6'):
            return TDXParams.MARKET_SH
        if c.startswith(('000', '002', '300')):
            return TDXParams.MARKET_SZ
        if c.startswith(('8', '4')):
            return TDXParams.MARKET_BJ
        return TDXParams.MARKET_SZ

    @staticmethod
    def is_hk_stock(code: str) -> bool:
        return code.strip().upper().endswith(".HK")
