"""
Memory汇总模块

将filings目录下提取的PDF关键章节汇总到memory目录，作为长期记忆供分析使用。
"""
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.financial_analysis.extract_pdf_text import PDFExtractor


# 文档类型到摘要文件名的映射
DOC_TYPE_MAP = {
    "年报": "年报摘要.md",
    "中报": "中报摘要.md",
    "招股说明书": "招股说明书摘要.md",
    "增发": "增发摘要.md",
    "可转债": "可转债摘要.md",
}

# 文档类型到显示名称的映射
DOC_TYPE_DISPLAY = {
    "年报": "年度报告",
    "中报": "半年度报告",
    "招股说明书": "招股说明书",
    "增发": "增发募集说明书",
    "可转债": "可转债募集说明书",
}


def extract_year_from_filename(filename: str) -> str:
    """
    从文件名提取报告年度

    Args:
        filename: PDF文件名，如 "2025-03-22_乐鑫科技2024年年度报告.pdf"

    Returns:
        年度字符串，如 "2024"
    """
    # 匹配 XXXX年 格式
    match = re.search(r'(\d{4})年', filename)
    if match:
        return match.group(1)

    # 匹配文件名开头的日期 YYYY-MM-DD
    match = re.search(r'^(\d{4})-\d{2}-\d{2}', filename)
    if match:
        return match.group(1)

    return "未知"


def extract_date_from_filename(filename: str) -> str:
    """
    从文件名提取发布日期

    Args:
        filename: PDF文件名

    Returns:
        日期字符串 YYYY-MM-DD 或空字符串
    """
    match = re.search(r'^(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return ""


def _filter_final_prospectus_files(pdf_files: List[Path]) -> List[Path]:
    """
    增发/可转债募集说明书去重：同一次募资只保留最终版。
    优先级：注册稿 > 修订稿 > 无标注 > 申报稿。
    同一次募资的不同阶段可能跨年（如2024年度申报，2025年注册），
    所以先按"XXXX年度"分组，无年度标识的归入最近的已有分组。
    """
    if len(pdf_files) <= 1:
        return pdf_files

    def _priority(f: Path) -> int:
        name = f.name
        if "注册稿" in name:
            return 0
        elif "修订稿" in name:
            return 1
        elif "申报稿" in name:
            return 3
        return 2  # 无标注

    # 第一轮：提取有明确年度标识的
    by_fundraise = {}
    unkeyed = []
    for f in pdf_files:
        year_match = re.search(r'(\d{4})年度', f.name)
        if year_match:
            key = year_match.group(1)
            by_fundraise.setdefault(key, []).append(f)
        else:
            unkeyed.append(f)

    # 第二轮：无年度标识的归入已有分组（同一次募资的注册稿标题常省略年度）
    for f in unkeyed:
        if by_fundraise:
            # 归入最近的分组（按年份倒序取第一个）
            latest_key = max(by_fundraise.keys())
            by_fundraise[latest_key].append(f)
        else:
            # 没有任何已有分组，用发布日期年份
            key = extract_year_from_filename(f.name)
            by_fundraise.setdefault(key, []).append(f)

    # 每组只保留最终版
    result = []
    for key, files in by_fundraise.items():
        best = min(files, key=_priority)
        if len(files) > 1:
            print(f"\n募集说明书去重({key}): {len(files)} 份 → 保留 {best.name}")
        result.append(best)

    result.sort(key=lambda p: p.name, reverse=True)
    return result


def build_memory_summary(stock_code: str, doc_type: str) -> Optional[str]:
    """
    汇总某类文档到memory摘要

    Args:
        stock_code: 股票代码
        doc_type: 文档类型 (年报/中报/招股说明书/增发/可转债)

    Returns:
        生成的摘要文件路径，如果没有PDF则返回None
    """
    if doc_type not in DOC_TYPE_MAP:
        print(f"未知文档类型: {doc_type}")
        return None

    project_root = Path(__file__).parent.parent.parent
    filings_dir = project_root / "stock" / stock_code / "filings" / doc_type
    memory_dir = project_root / "stock" / stock_code / "memory"

    if not filings_dir.exists():
        return None

    # 获取所有PDF文件
    pdf_files = list(filings_dir.glob("*.pdf"))
    if not pdf_files:
        return None

    # 按文件名日期倒序排列（最新的在前）
    pdf_files.sort(key=lambda p: p.name, reverse=True)

    # 年报只保留最新3份，避免摘要随公告积累而无限增长
    if doc_type == "年报" and len(pdf_files) > 3:
        skipped = pdf_files[3:]
        pdf_files = pdf_files[:3]
        print(f"\n年报限制: 保留最新 3 份，跳过 {len(skipped)} 份较早年报")

    # 中报去重：年报已覆盖同年上半年内容，只保留尚无对应年报的中报
    if doc_type == "中报":
        annual_dir = project_root / "stock" / stock_code / "filings" / "年报"
        annual_years = set()
        if annual_dir.exists():
            for f in annual_dir.glob("*.pdf"):
                y = extract_year_from_filename(f.name)
                if y != "未知":
                    annual_years.add(y)
        before = len(pdf_files)
        pdf_files = [f for f in pdf_files if extract_year_from_filename(f.name) not in annual_years]
        skipped = before - len(pdf_files)
        if skipped > 0:
            print(f"\n中报去重: 跳过 {skipped} 份（对应年报已存在），保留 {len(pdf_files)} 份")
        if not pdf_files:
            print(f"\n所有中报均已被年报覆盖，跳过生成")
            return None

    # 增发/可转债去重：同一次募资可能有申报稿、修订稿、注册稿，只保留最终版
    if doc_type in ("增发", "可转债"):
        pdf_files = _filter_final_prospectus_files(pdf_files)

    print(f"\n汇总 {doc_type}: 找到 {len(pdf_files)} 个文件")

    # 读取公司报表类型（用于银行/证券特殊章节提取）
    fs_type = "non_financial"
    company_json = project_root / "stock" / stock_code / "memory" / "公司信息.json"
    if company_json.exists():
        import json
        try:
            with open(company_json, encoding="utf-8") as f:
                company_data = json.load(f)
            fs_type = company_data.get("报表类型", "non_financial")
        except Exception:
            pass

    # 构建摘要内容
    lines = []
    display_name = DOC_TYPE_DISPLAY.get(doc_type, doc_type)
    lines.append(f"# {display_name}摘要\n")

    # 文件索引表格
    lines.append("## 文件索引\n")
    lines.append("| 年度 | 发布日期 | 文件 |")
    lines.append("|------|----------|------|")

    for pdf_path in pdf_files:
        year = extract_year_from_filename(pdf_path.name)
        date = extract_date_from_filename(pdf_path.name)
        # 使用相对路径
        rel_path = f"../filings/{doc_type}/{pdf_path.name}"
        # 简化显示名称
        display = pdf_path.stem.split("_", 1)[-1] if "_" in pdf_path.stem else pdf_path.stem
        lines.append(f"| {year} | {date} | [{display}]({rel_path}) |")

    lines.append("")
    lines.append("---\n")

    # 处理每个PDF
    for pdf_path in pdf_files:
        print(f"  处理: {pdf_path.name}")

        year = extract_year_from_filename(pdf_path.name)
        lines.append(f"## {year}年{display_name}\n")
        lines.append(f"**文件:** {pdf_path.name}\n")

        try:
            extractor = PDFExtractor(str(pdf_path), fs_type=fs_type)
            data = extractor.extract_for_memory()

            # 原文目录
            if data["toc"]:
                lines.append("### 原文目录\n")
                lines.append("```")
                lines.append(data["toc"])
                lines.append("```\n")

            # 关键章节
            for section_name, content in data["sections"].items():
                lines.append(f"### {section_name}\n")
                lines.append(content)
                lines.append("")

        except Exception as e:
            lines.append(f"*提取失败: {e}*\n")
            print(f"    提取失败: {e}")

        lines.append("---\n")

    # 写入文件
    memory_dir.mkdir(parents=True, exist_ok=True)
    output_path = memory_dir / DOC_TYPE_MAP[doc_type]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  已保存: {output_path}")
    return str(output_path)


def build_all_memory(stock_code: str) -> Dict[str, str]:
    """
    汇总所有类型的文档到memory

    Args:
        stock_code: 股票代码

    Returns:
        {文档类型: 摘要文件路径}
    """
    results = {}

    for doc_type in DOC_TYPE_MAP.keys():
        result = build_memory_summary(stock_code, doc_type)
        if result:
            results[doc_type] = result

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python build_memory.py <股票代码> [文档类型]")
        print()
        print("文档类型: 年报、中报、招股说明书、增发、可转债")
        print("不指定文档类型则汇总所有类型")
        print()
        print("示例:")
        print("  python build_memory.py 688018")
        print("  python build_memory.py 688018 年报")
        sys.exit(1)

    stock_code = sys.argv[1]

    if len(sys.argv) > 2:
        doc_type = sys.argv[2]
        result = build_memory_summary(stock_code, doc_type)
        if result:
            print(f"\n完成: {result}")
        else:
            print(f"\n未找到 {doc_type} 文件")
    else:
        results = build_all_memory(stock_code)
        print(f"\n=== 汇总完成 ===")
        for doc_type, path in results.items():
            print(f"  {doc_type}: {Path(path).name}")
