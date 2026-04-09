#!/usr/bin/env python3
"""
公司信息导出工具

用法:
    python export_company_info.py <股票代码>

示例:
    python export_company_info.py 688018
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.financial_analysis.fetch_company_data import CompanyDataFetcher
from skills.financial_analysis.generate_json import JsonGenerator


def export_company_info(stock_code: str, years: int = 5) -> str:
    """
    导出公司信息到JSON

    Args:
        stock_code: 股票代码
        years: 数据年限，默认5年

    Returns:
        输出文件路径
    """
    print(f"正在获取 {stock_code} 的数据...")

    # 获取数据
    fetcher = CompanyDataFetcher(stock_code, years=years)
    data = fetcher.fetch_all()

    company_name = data.get("basic_info", {}).get("name", stock_code)
    fs_type = fetcher.fs_type
    print(f"公司名称: {company_name}")
    if fs_type != "non_financial":
        print(f"报表类型: {fs_type}")

    # 生成JSON - 存放到长期记忆模块
    output_dir = PROJECT_ROOT / "stock" / stock_code / "memory"
    output_path = output_dir / "公司信息.json"

    print(f"正在生成JSON...")
    generator = JsonGenerator(data, stock_code, fs_type=fs_type)
    generator.generate(str(output_path))

    print(f"完成! 文件已保存至: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    stock_code = sys.argv[1]
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    output_path = export_company_info(stock_code, years)
    return output_path


if __name__ == "__main__":
    main()
