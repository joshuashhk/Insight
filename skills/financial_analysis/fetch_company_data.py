"""
公司数据获取模块

从理杏仁API获取公司完整信息，用于生成财报分析报告。
自动识别公司类型（非金融/银行/保险/证券/其它金融），使用对应的报表端点和科目。
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sources.structured.financial import LixingerClient
from skills.financial_analysis.generate_json import FS_TYPE_FIELDS, fields_to_metrics


def get_date_range(years: int = 5) -> tuple[str, str]:
    """获取时间范围（最近N年）"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    return start_date, end_date


class CompanyDataFetcher:
    """公司数据获取器"""

    def __init__(self, stock_code: str, years: int = 10):
        self.stock_code = stock_code
        self.years = years
        self.client = LixingerClient()
        self.start_date, self.end_date = get_date_range(years)
        self.fs_type = self._detect_fs_type()

    def _detect_fs_type(self) -> str:
        """自动识别公司财报类型"""
        data = self.client.query(
            "cn/company",
            stockCodes=[self.stock_code],
            pageIndex=0
        )
        if data:
            fs_type = data[0].get("fsTableType", "non_financial")
            if fs_type in FS_TYPE_FIELDS:
                return fs_type
        return "non_financial"

    def _get_metrics(self, statement_index: int) -> List[str]:
        """获取指定报表的指标列表（0=BS, 1=PS, 2=CFS）"""
        fields = FS_TYPE_FIELDS.get(self.fs_type, FS_TYPE_FIELDS["non_financial"])
        return fields_to_metrics(fields[statement_index])

    # ==================== Sheet 1: 基础信息 ====================

    def fetch_basic_info(self) -> Dict[str, Any]:
        """获取基础信息"""
        data = self.client.query(
            "cn/company",
            stockCodes=[self.stock_code],
            pageIndex=0
        )
        return data[0] if data else {}

    def fetch_indices(self) -> List[Dict]:
        """获取所属指数"""
        return self.client.query(
            "cn/company/indices",
            stockCode=self.stock_code
        )

    # ==================== Sheet 2: 公司概况 ====================

    def fetch_profile(self) -> Dict[str, Any]:
        """获取公司概况"""
        data = self.client.query(
            "cn/company/profile",
            stockCodes=[self.stock_code]
        )
        return data[0] if data else {}

    def fetch_industries(self) -> List[Dict]:
        """获取所属行业"""
        return self.client.query(
            "cn/company/industries",
            stockCode=self.stock_code
        )

    def fetch_shareholders(self) -> List[Dict]:
        """获取前十大股东（最新一期）"""
        return self.client.query(
            "cn/company/majority-shareholders",
            stockCode=self.stock_code,
            startDate=self.start_date,
            endDate=self.end_date,
            limit=10
        )

    # ==================== Sheet 3-5: 财务报表 ====================

    def fetch_balance_sheet(self) -> List[Dict]:
        """获取资产负债表（季度数据）"""
        return self.client.get_financial_statements(
            stock_codes=[self.stock_code],
            metrics_list=self._get_metrics(0),
            start_date=self.start_date,
            end_date=self.end_date,
            fs_type=self.fs_type,
        )

    def fetch_income_statement(self) -> List[Dict]:
        """获取利润表（季度数据）"""
        return self.client.get_financial_statements(
            stock_codes=[self.stock_code],
            metrics_list=self._get_metrics(1),
            start_date=self.start_date,
            end_date=self.end_date,
            fs_type=self.fs_type,
        )

    def fetch_cash_flow(self) -> List[Dict]:
        """获取现金流量表（季度数据）"""
        return self.client.get_financial_statements(
            stock_codes=[self.stock_code],
            metrics_list=self._get_metrics(2),
            start_date=self.start_date,
            end_date=self.end_date,
            fs_type=self.fs_type,
        )

    # ==================== Sheet 6: 营收与经营 ====================

    def fetch_revenue_constitution(self) -> List[Dict]:
        """获取营收构成"""
        return self.client.query(
            "cn/company/operation-revenue-constitution",
            stockCode=self.stock_code,
            startDate=self.start_date,
            endDate=self.end_date
        )

    def fetch_operating_data(self) -> List[Dict]:
        """获取经营数据"""
        return self.client.query(
            "cn/company/operating-data",
            stockCode=self.stock_code,
            startDate=self.start_date,
            endDate=self.end_date
        )

    # ==================== Sheet 7: 监管信息 ====================

    def fetch_measures(self) -> List[Dict]:
        """获取监管措施"""
        return self.client.query(
            "cn/company/measures",
            stockCode=self.stock_code,
            startDate=self.start_date,
            endDate=self.end_date
        )

    def fetch_inquiry(self) -> List[Dict]:
        """获取问询函"""
        return self.client.query(
            "cn/company/inquiry",
            stockCode=self.stock_code,
            startDate=self.start_date,
            endDate=self.end_date
        )

    # ==================== Sheet 8: 基本面数据 ====================

    def fetch_fundamental(self) -> List[Dict]:
        """获取基本面数据（股息率、估值等，按日频返回）"""
        return self.client.get_fundamental(
            stock_codes=[self.stock_code],
            metrics_list=["dyr", "pe_ttm", "pb", "mc"],
            start_date=self.start_date,
            end_date=self.end_date,
            fs_type=self.fs_type,
        )

    # ==================== 汇总获取 ====================

    def fetch_all(self) -> Dict[str, Any]:
        """获取所有数据"""
        return {
            # Sheet 1
            "basic_info": self.fetch_basic_info(),
            "indices": self.fetch_indices(),
            # Sheet 2
            "profile": self.fetch_profile(),
            "industries": self.fetch_industries(),
            "shareholders": self.fetch_shareholders(),
            # Sheet 3-5
            "balance_sheet": self.fetch_balance_sheet(),
            "income_statement": self.fetch_income_statement(),
            "cash_flow": self.fetch_cash_flow(),
            # Sheet 6
            "revenue_constitution": self.fetch_revenue_constitution(),
            "operating_data": self.fetch_operating_data(),
            # Sheet 7
            "measures": self.fetch_measures(),
            "inquiry": self.fetch_inquiry(),
            # Sheet 8
            "fundamental": self.fetch_fundamental(),
        }
