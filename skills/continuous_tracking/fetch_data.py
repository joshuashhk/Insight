#!/usr/bin/env python3
"""
持续跟踪数据获取工具

获取估值、K线、公告等数据，输出格式化结果供报告撰写使用。

用法：
    python3 skills/continuous_tracking/fetch_data.py <股票代码>
    python3 skills/continuous_tracking/fetch_data.py <股票代码> --months 3
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_env():
    """从项目根目录加载.env文件"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = value


load_env()


def _get_lixinger_client():
    """获取理杏仁API客户端"""
    from sources.structured.financial import LixingerClient
    return LixingerClient()


def _fmt_number(value, fmt=".2f"):
    """格式化数值，非数值原样返回"""
    return f"{value:{fmt}}" if isinstance(value, (int, float)) else value


# ============================================================================
# 估值数据
# ============================================================================

def get_current_valuation(stock_code: str) -> dict:
    """获取当前估值数据"""
    try:
        return _get_lixinger_client().get_valuation(stock_code, with_percentile=True)
    except Exception as e:
        print(f"  获取估值数据失败: {e}")
        return {}


def format_valuation_data(valuation: dict) -> str:
    """格式化估值数据为Markdown表格"""
    if not valuation:
        return "估值数据获取失败"

    lines = ["| 指标 | 当前值 | 5年分位 |", "|------|--------|---------|"]

    for label, val_key, pct_key in [
        ("PE(TTM)", "pe_ttm", "pe_ttm.y5.cvpos"),
        ("PB", "pb", "pb.y5.cvpos"),
    ]:
        val = _fmt_number(valuation.get(val_key, "N/A"))
        pct = valuation.get(pct_key, "N/A")
        pct = _fmt_number(pct, ".1%") if isinstance(pct, (int, float)) else pct
        lines.append(f"| {label} | {val} | {pct} |")

    mc = valuation.get("mc", "N/A")
    mc = f"{mc/1e8:.1f}亿" if isinstance(mc, (int, float)) else mc
    lines.append(f"| 市值 | {mc} | - |")

    return "\n".join(lines)


# ============================================================================
# K线数据
# ============================================================================

def get_kline_data(stock_code: str, days: int = 125) -> list:
    """获取近6个月K线数据"""
    try:
        return _get_lixinger_client().get_klines(stock_code, days=days)
    except Exception as e:
        print(f"  获取K线数据失败: {e}")
        return []


def format_kline_data(klines: list) -> str:
    """格式化K线数据：整体统计 + 周K线 + 大幅波动日"""
    if not klines:
        return "K线数据获取失败"

    from datetime import datetime as dt

    klines_asc = sorted(klines, key=lambda x: x["date"])
    first, last = klines_asc[0], klines_asc[-1]
    total_change = (last["close"] - first["close"]) / first["close"] * 100

    max_k = max(klines_asc, key=lambda k: k["high"])
    min_k = min(klines_asc, key=lambda k: k["low"])
    avg_close = sum(k["close"] for k in klines_asc) / len(klines_asc)
    avg_volume = sum(k["volume"] for k in klines_asc) / len(klines_asc)

    lines = [
        "**区间统计（近6个月）**",
        f"- 区间涨跌幅: {total_change:+.2f}%",
        f"- 起始价: {first['close']:.2f} ({first['date'][:10]})",
        f"- 最新价: {last['close']:.2f} ({last['date'][:10]})",
        f"- 最高价: {max_k['high']:.2f} ({max_k['date'][:10]})",
        f"- 最低价: {min_k['low']:.2f} ({min_k['date'][:10]})",
        f"- 区间均价: {avg_close:.2f}",
        f"- 日均成交量: {avg_volume:,.0f}",
        "",
        "**周K线数据**",
        "| 周起始日 | 开盘 | 收盘 | 最高 | 最低 | 周涨跌% | 周成交量 |",
        "|----------|------|------|------|------|---------|----------|",
    ]

    # 按周聚合
    weeks = {}
    for k in klines_asc:
        week_key = dt.strptime(k["date"][:10], "%Y-%m-%d").strftime("%Y-W%V")
        weeks.setdefault(week_key, []).append(k)

    for week_data in weeks.values():
        w_open = week_data[0]["open"]
        w_close = week_data[-1]["close"]
        w_change = (w_close - w_open) / w_open * 100 if w_open else 0
        lines.append(
            f"| {week_data[0]['date'][:10]} | {w_open:.2f} | {w_close:.2f} | "
            f"{max(d['high'] for d in week_data):.2f} | {min(d['low'] for d in week_data):.2f} | "
            f"{w_change:+.2f}% | {sum(d['volume'] for d in week_data):,.0f} |"
        )

    lines.append("")

    # 大幅波动日（|涨跌幅| > 5%）
    big_moves = [k for k in klines_asc if k.get("change") and abs(k["change"]) > 0.05]
    if big_moves:
        lines.extend([
            "**大幅波动交易日（涨跌幅>5%）**",
            "| 日期 | 收盘 | 涨跌幅 | 成交量 |",
            "|------|------|--------|--------|",
        ])
        for k in big_moves:
            lines.append(
                f"| {k['date'][:10]} | {k['close']:.2f} | "
                f"{k['change']*100:+.2f}% | {k['volume']:,.0f} |"
            )
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# 公告数据
# ============================================================================

LIXINGER_TYPE_MAPPING = {
    "fsfc": ("业绩类", 10),
    "ipo": ("资本运作", 10),
    "spo": ("资本运作", 9),
    "sa": ("资本运作", 9),
    "srp": ("资本运作", 9),
    "c_b": ("资本运作", 9),
    "i_l": ("监管问询", 9),
    "irs": ("投资者关系活动", 8),
    "c_rp": ("风险提示", 8),
    "eac": ("分红派息", 7),
    "eat": ("股东变动", 7),
    "so": ("股权激励", 7),
    "shm": ("股东大会", 6),
    "bm": ("董事会", 5),
    "sm": ("监事会", 4),
}

EXCLUDE_TYPES = ["fs", "o_d", "b", "other"]

EXCLUDE_KEYWORDS = [
    # 中介机构文件
    "法律意见书", "核查意见", "鉴证报告", "审计报告",
    "保荐书", "律师事务所", "会计师事务所", "验资报告",
    "审核意见", "独立财务顾问", "专项核查",
    # 董事会程序性合规声明
    "董事会关于本次交易符合", "董事会关于本次交易构成",
    "董事会关于本次交易履行", "董事会关于本次交易相关主体",
    "董事会关于本次交易前", "董事会关于本次交易是否",
    "董事会关于本次交易信息", "董事会关于本次交易采取",
    "董事会关于本次交易摊薄", "董事会关于评估机构",
    # 制度/规则文件
    "议事规则", "管理办法", "管理制度", "实施细则",
    "工作制度", "行为准则", "行为规范",
    # 其他程序性文件
    "独立董事候选人声明", "独立董事提名人声明",
    "独立董事述职报告", "独立董事独立性",
    "持有人会议规则", "公司章程",
    "会议资料",
    # 募资管理例行披露
    "募集资金存放", "募集资金使用情况",
    "闲置募集资金", "现金管理产品专用",
    "以募集资金等额置换",
    "与预案差异对比",
]

# 从 other/fs 中捞回的重要公告关键词 → (类别, 优先级)
RESCUE_KEYWORDS = [
    ("重大资产重组", "资本运作", 9),
    ("季度报告", "业绩类", 8),
    ("半年度报告", "业绩类", 8),
    ("年度报告", "业绩类", 8),
]


def get_and_format_announcements(stock_code: str, months: int = 6) -> str:
    """获取并格式化近期重要公告"""
    try:
        client = _get_lixinger_client()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)

        announcements = client.query(
            "cn/company/announcement",
            stockCode=stock_code,
            startDate=start_date.strftime("%Y-%m-%d"),
            endDate=end_date.strftime("%Y-%m-%d")
        )

        if not announcements:
            return "暂无重要公告数据"

        # 筛选重要公告
        important = []
        for ann in announcements:
            title = ann.get("linkText", "")

            # 排除程序性文件
            if any(kw in title for kw in EXCLUDE_KEYWORDS):
                continue

            types = ann.get("types", [])
            best_priority = -1
            best_category = None

            for type_code in types:
                if type_code in EXCLUDE_TYPES:
                    continue
                if type_code in LIXINGER_TYPE_MAPPING:
                    category, priority = LIXINGER_TYPE_MAPPING[type_code]
                    if priority > best_priority:
                        best_priority = priority
                        best_category = category

            # 从 other/fs 中按关键词捞回重要公告
            if best_category is None:
                for keyword, category, priority in RESCUE_KEYWORDS:
                    if keyword in title:
                        best_category = category
                        best_priority = priority
                        break

            if best_category:
                important.append({
                    "date": ann.get("date", "")[:10],
                    "title": title,
                    "category": best_category,
                    "priority": best_priority,
                })

        if not important:
            return "近期无重要公告"

        important.sort(key=lambda x: (-x["priority"], x["date"]), reverse=False)

        lines = [f"**近{months}个月重要公告（共{len(important)}条）**", ""]

        by_category = defaultdict(list)
        for ann in important:
            by_category[ann["category"]].append(ann)

        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: -max(a["priority"] for a in x[1])
        )

        for category, anns in sorted_categories:
            lines.append(f"### {category} ({len(anns)}条)")
            lines.append("")
            for ann in anns:
                lines.append(f"- **{ann['date']}**: {ann['title']}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        print(f"  获取公告失败: {e}")
        return "公告数据获取失败"


# ============================================================================
# 主入口
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    stock_code = sys.argv[1]
    months = 6
    if "--months" in sys.argv:
        idx = sys.argv.index("--months")
        if idx + 1 < len(sys.argv):
            months = int(sys.argv[idx + 1])

    # 获取公司名称
    try:
        info = _get_lixinger_client().get_company_info(stock_codes=[stock_code])
        company_name = info[0].get("name", stock_code) if info else stock_code
    except Exception:
        company_name = stock_code

    print(f"{'='*60}")
    print(f"持续跟踪数据获取: {company_name} ({stock_code})")
    print(f"{'='*60}")

    print(f"\n获取当前估值数据...")
    valuation = format_valuation_data(get_current_valuation(stock_code))
    print(valuation)

    print(f"\n获取近{months}个月K线数据...")
    kline = format_kline_data(get_kline_data(stock_code))
    print(kline)

    print(f"\n筛选近{months}个月重要公告...")
    announcements = get_and_format_announcements(stock_code, months=months)
    print(announcements)

    print(f"\n{'='*60}")
    print("数据获取完成")


if __name__ == "__main__":
    main()
