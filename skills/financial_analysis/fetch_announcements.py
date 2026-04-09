"""
公告文件下载模块

下载重要公司文件：
- 最近三年年报和中报
- 招股说明书（首发和增发）
- 可转债募集说明书

支持的数据源：
- 理杏仁API: 获取公告列表
- 巨潮资讯(cninfo): 下载PDF文件（支持上交所和深交所）
"""
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sources.unstructured.announcements import AnnouncementDownloader, CninfoClient


def download_company_documents(stock_code: str, years: int = 3) -> Dict[str, Any]:
    """下载公司重要文件的便捷函数"""
    # 确定输出目录
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "stock" / stock_code / "filings"

    downloader = AnnouncementDownloader(stock_code, years)
    return downloader.run(output_dir)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fetch_announcements.py <股票代码> [年数]")
        print("示例: python fetch_announcements.py 688018 3")
        sys.exit(1)

    stock_code = sys.argv[1]
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    result = download_company_documents(stock_code, years)

    print("\n=== 统计 ===")
    print(f"总公告数: {result['stats']['total_found']}")
    print(f"筛选后: {result['stats']['total_filtered']}")
    print(f"成功下载: {result['stats']['total_downloaded']}")
    print(f"Memory摘要: {result['stats']['total_memory']}")
