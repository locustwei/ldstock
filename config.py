"""配置管理模块 - 管理DeepSeek API Key和数据刷新间隔"""
import json
import os
from typing import Optional


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "deepseek_api_key": "",
    "deepseek_base_url": "https://api.deepseek.com",
    "refresh_interval": 10,  # 秒
    "monitor_stocks": [],     # 监控的股票代码列表
}


class Config:
    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._data: dict = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        """从JSON文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for k in self._data:
                        if k in saved:
                            self._data[k] = saved[k]
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def save(self) -> None:
        """保存配置到JSON文件"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    @property
    def deepseek_api_key(self) -> str:
        return self._data.get("deepseek_api_key", "")

    @deepseek_api_key.setter
    def deepseek_api_key(self, value: str) -> None:
        self._data["deepseek_api_key"] = value
        self.save()

    @property
    def deepseek_base_url(self) -> str:
        return self._data.get("deepseek_base_url", "https://api.deepseek.com")

    @deepseek_base_url.setter
    def deepseek_base_url(self, value: str) -> None:
        self._data["deepseek_base_url"] = value
        self.save()

    @property
    def refresh_interval(self) -> int:
        return self._data.get("refresh_interval", 10)

    @refresh_interval.setter
    def refresh_interval(self, value: int) -> None:
        self._data["refresh_interval"] = max(3, int(value))
        self.save()

    @property
    def monitor_stocks(self) -> any:
        return self._data.get("monitor_stocks", [])

    @monitor_stocks.setter
    def monitor_stocks(self, value: any) -> None:
        self._data["monitor_stocks"] = value
        self.save()

    @property
    def has_api_key(self) -> bool:
        return bool(self._data.get("deepseek_api_key", ""))
