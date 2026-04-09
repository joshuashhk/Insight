#!/usr/bin/env python3
"""
近期公告筛选系统 - 理杏仁API版本

功能：
1. 从理杏仁API获取个股近期公告
2. 智能筛选重要公告（基于理杏仁分类标签）
3. 生成结构化摘要到cache目录

用法：
    python3 filter_recent_lixinger.py <股票代码>
    python3 filter_recent_lixinger.py <股票代码> --months 3
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载.env
def load_env():
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

from sources.structured.financial import LixingerClient


# ============================================================================
# 理杏仁公告类型映射
# ============================================================================
# 理杏仁原始分类 -> 我们的重要公告分类
LIXINGER_TYPE_MAPPING = {
    # 业绩类
    "fsfc": ("业绩类", 10),  # 业绩预告

    # 资本运作
    "sa": ("资本运作", 9),   # 配股
    "spo": ("资本运作", 9),  # 增发
    "srp": ("资本运作", 9),  # 回购
    "ipo": ("资本运作", 10), # IPO
    "c_b": ("资本运作", 9),  # 可转换债券

    # 股权激励与解禁
    "so": ("股权激励", 7),   # 解禁/股权激励

    # 股东大会
    "shm": ("股东大会", 6),  # 股东大会

    # 董事会/监事会
    "bm": ("董事会", 5),     # 董事会
    "sm": ("监事会", 4),     # 监事会

    # 权益分派
    "eac": ("分红派息", 7),  # 权益分派

    # 投资者关系 ⭐ 重点
    "irs": ("投资者关系活动", 8),  # 投资者关系

    # 风险提示
    "c_rp": ("风险提示", 8), # 澄清及风险提示
    "i_l": ("监管问询", 9),  # 问询函

    # 股权变更
    "eat": ("股东变动", 7),  # 股权变更
}

# 排除的理杏仁分类（不重要的公告）
EXCLUDE_LIXINGER_TYPES = [
    "fs",      # 财务报表（单独处理）
    "o_d",     # 经营数据（常规更新）
    "b",       # 债券（对股票投资者不重要）
    "other",   # 其它
]

# 排除程序性文件的关键词
EXCLUDE_TITLE_KEYWORDS = [
    "法律意见书", "核查意见", "鉴证报告", "审计报告",
    "保荐书", "律师事务所", "会计师事务所", "验资报告",
    "审核意见", "独立财务顾问", "专项核查"
]


# ============================================================================
# 公告筛选逻辑
# ============================================================================

def classify_announcement_by_lixinger_types(types: List[str]) -> Optional[Tuple[str, int]]:
    """
    根据理杏仁的types字段分类公告

    Args:
        types: 理杏仁API返回的types数组，如 ['irs'], ['srp'], ['bm']

    Returns:
        (类别名称, 优先级) 或 None（不重要的公告）
    """
    if not types:
        return None

    # 找到优先级最高的匹配
    best_match = None
    best_priority = -1

    for type_code in types:
        # 排除不重要的类型
        if type_code in EXCLUDE_LIXINGER_TYPES:
            continue

        # 查找映射
        if type_code in LIXINGER_TYPE_MAPPING:
            category, priority = LIXINGER_TYPE_MAPPING[type_code]
            if priority > best_priority:
                best_match = (category, priority)
                best_priority = priority

    return best_match


def filter_announcements(
    announcements: List[Dict],
    months: int = 6
) -> List[Dict]:
    """
    筛选重要公告

    Args:
        announcements: 理杏仁API返回的公告列表
        months: 时间范围（月数）

    Returns:
        筛选后的重要公告列表
    """
    important_announcements = []

    for ann in announcements:
        title = ann.get("linkText", "")

        # 排除程序性文件
        should_exclude = False
        for keyword in EXCLUDE_TITLE_KEYWORDS:
            if keyword in title:
                should_exclude = True
                break

        if should_exclude:
            continue

        types = ann.get("types", [])
        classification = classify_announcement_by_lixinger_types(types)

        if classification:
            category, priority = classification
            important_announcements.append({
                "date": ann.get("date", "")[:10],  # 只保留日期部分
                "title": title,
                "url": ann.get("linkUrl", ""),
                "types": types,
                "category": category,
                "priority": priority,
            })

    # 按优先级和日期排序
    important_announcements.sort(
        key=lambda x: (-x["priority"], x["date"]),
        reverse=True
    )

    return important_announcements


def generate_markdown_summary(
    stock_code: str,
    company_name: str,
    announcements: List[Dict],
    months: int
) -> str:
    """
    生成Markdown格式摘要

    Args:
        stock_code: 股票代码
        company_name: 公司名称
        announcements: 筛选后的公告列表
        months: 时间范围（月数）

    Returns:
        Markdown格式的摘要字符串
    """
    # 按类别分组
    category_groups = {}
    for ann in announcements:
        category = ann["category"]
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(ann)

    # 生成Markdown
    lines = [
        f"# {company_name} ({stock_code}) 近{months}个月重要公告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**统计周期**: 近{months}个月",
        f"**公告数量**: {len(announcements)}条",
        "",
        "---",
        "",
    ]

    # 按优先级排序类别
    sorted_categories = sorted(
        category_groups.items(),
        key=lambda x: -max(ann["priority"] for ann in x[1])
    )

    for category, anns in sorted_categories:
        lines.append(f"## {category} ({len(anns)}条)")
        lines.append("")

        for ann in anns:
            lines.append(f"### {ann['title']}")
            lines.append(f"**发布日期**: {ann['date']}")
            lines.append(f"**链接**: [{ann['title']}]({ann['url']})")
            lines.append(f"**理杏仁分类**: {', '.join(ann['types'])}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 统计信息
    lines.append("## 📊 统计信息")
    lines.append("")
    lines.append("| 类别 | 数量 | 占比 |")
    lines.append("|------|------|------|")

    total = len(announcements)
    for category, anns in sorted_categories:
        count = len(anns)
        percentage = (count / total * 100) if total > 0 else 0
        lines.append(f"| {category} | {count} | {percentage:.1f}% |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本摘要由系统自动生成，仅供参考*")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="筛选个股近期重要公告（理杏仁API版）")
    parser.add_argument("stock_code", help="股票代码，如 600519")
    parser.add_argument("--months", type=int, default=6, help="时间范围（月数），默认6个月")

    args = parser.parse_args()
    stock_code = args.stock_code
    months = args.months

    print("=" * 60)
    print(f"近期公告筛选 - {stock_code}")
    print("=" * 60)
    print()

    # 初始化理杏仁客户端
    try:
        client = LixingerClient()
    except ValueError as e:
        print(f"❌ 错误: {e}")
        print("请确保设置了环境变量 LIXINGER_TOKEN")
        return 1

    # 获取公司名称
    print(f"正在获取公司信息...")
    company_info = client.get_company_info(stock_codes=[stock_code])
    if not company_info:
        print(f"❌ 错误: 未找到股票代码 {stock_code}")
        return 1

    company_name = company_info[0].get("cnName", stock_code)
    print(f"公司名称: {company_name}")

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)

    print(f"正在获取 {stock_code} 的公告...")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    # 获取公告
    announcements = client.query(
        "cn/company/announcement",
        stockCode=stock_code,
        startDate=start_date.strftime("%Y-%m-%d"),
        endDate=end_date.strftime("%Y-%m-%d")
    )

    print(f"共获取 {len(announcements)} 条公告")

    # 筛选重要公告
    important = filter_announcements(announcements, months)
    print(f"筛选出 {len(important)} 条重要公告")
    print()

    # 生成摘要
    summary = generate_markdown_summary(
        stock_code, company_name, important, months
    )

    # 保存到cache目录
    cache_dir = PROJECT_ROOT / "stock" / stock_code / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    output_file = cache_dir / f"公告摘要_近{months}个月.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print("=" * 60)
    print("✅ 公告摘要已保存")
    print("=" * 60)
    print(f"路径: {output_file}")
    print(f"重要公告数: {len(important)}")
    print()

    # 显示类别分布
    category_counts = {}
    for ann in important:
        category = ann["category"]
        category_counts[category] = category_counts.get(category, 0) + 1

    if category_counts:
        print("类别分布:")
        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"  - {category}: {count}条")

    return 0


if __name__ == "__main__":
    sys.exit(main())
