"""DeepSeek API客户端 - 支持函数调用/MCP工具调用"""
from typing import Optional
from openai import OpenAI

from config import Config


# ── 工具定义（MCP风格） ──────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_realtime_quote",
            "description": "获取一只或多只股票的实时行情数据（包括价格、涨跌幅、成交量等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表，如 ['000001', '600519']，A股不需要后缀，港股需要.HK后缀",
                    }
                },
                "required": ["codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_history",
            "description": "获取股票历史K线数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "股票代码，如 000001, 600519, 00700.HK",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "K线周期：daily=日线, weekly=周线, monthly=月线",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "起始日期，格式 YYYYMMDD",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式 YYYYMMDD",
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_financial",
            "description": "获取股票财务数据摘要",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "股票代码",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_industry_concept",
            "description": "获取一只股票所属的行业板块和概念板块分类（如：白酒、银行、锂电池、人工智能等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "股票代码，如 000001, 600519, 300750",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": "获取大盘指数概况（如上证指数）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_performance",
            "description": "获取热门板块表现排名",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_stock",
            "description": "搜索股票代码或名称",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词：股票代码或名称",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def _call_tool(name: str, args: dict) -> str:
    """执行工具函数并返回结果文本"""
    import stock_data as sd

    tool_map = {
        "get_realtime_quote": lambda: _fmt_quotes(
            sd.get_realtime_quotes(args.get("codes", []))
        ),
        "get_stock_history": lambda: sd.get_stock_history(
            args.get("code", ""),
            args.get("period", "daily"),
            args.get("start_date"),
            args.get("end_date"),
        ),
        "get_stock_financial": lambda: sd.get_stock_financial(
            args.get("code", "")
        ),
        "get_stock_industry_concept": lambda: sd.get_stock_industry_concept(
            args.get("code", "")
        ),
        "get_market_overview": lambda: sd.get_market_overview(),
        "get_sector_performance": lambda: sd.get_sector_performance(),
        "search_stock": lambda: _fmt_search_results(
            sd.search_stock(args.get("query", ""))
        ),
    }
    func = tool_map.get(name)
    if func is None:
        return f"未知工具: {name}"
    try:
        return func()
    except Exception as e:
        return f"执行 {name} 时出错: {e}"


def _fmt_quotes(quotes: list[dict]) -> str:
    if not quotes:
        return "未获取到行情数据，请检查股票代码是否正确"
    lines = ["实时行情数据:"]
    for q in quotes:
        flag = "🔴" if q["change_pct"] < 0 else "🟢" if q["change_pct"] > 0 else "⚪"
        lines.append(
            f"  {flag} {q['code']} {q['name']} ({q['market']}) "
            f"最新: {q['price']:.2f}  "
            f"涨跌: {q['change']:+.2f}  "
            f"涨跌幅: {q['change_pct']:+.2f}%  "
            f"最高: {q['high']:.2f} 最低: {q['low']:.2f}  "
            f"成交量: {q['volume']:.0f} 成交额: {q['amount']:.0f}"
        )
    lines.append(f"更新时间: {quotes[0]['time'] if quotes else ''}")
    return "\n".join(lines)


def _fmt_search_results(results: list[dict]) -> str:
    if not results:
        return "未找到匹配的股票"
    lines = ["搜索结果:"]
    for r in results[:20]:
        lines.append(f"  {r['code']} - {r['name']}")
    return "\n".join(lines)


# ── 对话客户端 ──────────────────────────────────────

class DeepSeekClient:
    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self) -> None:
        cfg = Config()
        key = cfg.deepseek_api_key
        if key:
            self._client = OpenAI(
                api_key=key,
                base_url=cfg.deepseek_base_url,
            )
        else:
            self._client = None

    def update_api_key(self) -> None:
        """更新API Key后重新初始化"""
        self._init_client()

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def chat(self, messages: list[dict], stock_codes: list[str] = None) -> str:
        """
        发送对话消息，支持自动工具调用
        messages: 对话历史
        stock_codes: 用户关注的股票代码列表（用于上下文）
        """
        if not self._client:
            return "请先在设置中配置DeepSeek API Key"

        # 构建系统提示
        system_prompt = self._build_system_prompt(stock_codes)
        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)

        try:
            # 第一轮：获取AI回复（可能包含工具调用）
            response = self._client.chat.completions.create(
                model="deepseek-chat",
                messages=full_messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=4096,
            )

            msg = response.choices[0].message

            # 如果有工具调用
            if msg.tool_calls:
                full_messages.append(msg)
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    import json
                    func_args = json.loads(tc.function.arguments)
                    result = _call_tool(func_name, func_args)
                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                # 第二轮：让AI综合工具结果进行回答
                response2 = self._client.chat.completions.create(
                    model="deepseek-chat",
                    messages=full_messages,
                    temperature=0.7,
                    max_tokens=4096,
                )
                return response2.choices[0].message.content or ""

            return msg.content or ""

        except Exception as e:
            return f"调用DeepSeek API出错: {e}"

    def _build_system_prompt(self, stock_codes: list[str] | None = None) -> str:
        codes_str = ", ".join(stock_codes) if stock_codes else "无"
        return (
            "你是一个专业的股票分析助手。你可以使用提供的工具获取实时行情、历史数据、"
            "财务数据等信息来回答用户的问题。\n\n"
            "使用规则：\n"
            "1. 当用户询问某只股票的情况时，先使用工具获取实时数据和必要的历史数据\n"
            "2. 分析时要结合技术面和基本面，给出客观、专业的判断\n"
            "3. 数据来源于akshare金融数据库\n"
            "4. 如果用户问的是市场整体情况，使用大盘概况和板块表现工具\n"
            "5. 用中文回答，语言简洁明了\n"
            "6. 注意风险提示，不承诺收益\n\n"
            f"当前用户关注的股票代码: {codes_str}\n"
            "你可以根据需要调用工具获取更多数据。如果现有工具无法满足需求，可以告诉用户需要什么样的数据，并提示数据获取方法。"
        )
