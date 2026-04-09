"""
理杏仁API客户端

注意事项：
- 每分钟最大请求1000次，超过返回429
- headers必须包含 Accept-Encoding: gzip
- 内置重试机制处理网络问题

参考: https://github.com/qiansen1386/lixinger-openapi
"""
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# 加载.env文件
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


class RateLimitError(Exception):
    """请求频率超限"""
    pass


class LixingerClient:
    """理杏仁开放API客户端"""

    BASE_URL = "https://open.lixinger.com/api"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒

    def __init__(self, token: Optional[str] = None):
        """
        初始化客户端

        Args:
            token: API Token，如不提供则从环境变量 LIXINGER_TOKEN 读取
        """
        self.token = token or os.getenv("LIXINGER_TOKEN")
        if not self.token:
            raise ValueError("需要提供token或设置环境变量 LIXINGER_TOKEN")

    def _post(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        """
        发送POST请求（使用curl绕过SSL兼容问题）

        包含重试机制，处理网络问题和429限流
        """
        url = f"{self.BASE_URL}/{endpoint}"
        payload = {"token": self.token, **kwargs}

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            result = subprocess.run(
                [
                    "curl", "-s", "-w", "\n%{http_code}",
                    "--connect-timeout", "10",
                    "--max-time", "30",
                    "-X", "POST", url,
                    "-H", "Content-Type: application/json",
                    "-H", "Accept-Encoding: gzip, deflate",
                    "--compressed",
                    "-d", json.dumps(payload),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=45,
            )

            if result.returncode != 0:
                last_error = RuntimeError(f"请求失败: {result.stderr}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue

            # 解析响应和状态码
            lines = result.stdout.strip().rsplit("\n", 1)
            body = lines[0] if len(lines) > 1 else result.stdout
            status_code = int(lines[-1]) if len(lines) > 1 and lines[-1].isdigit() else 200

            # 处理429限流
            if status_code == 429:
                wait_time = 60  # 等待1分钟
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(wait_time)
                    continue
                raise RateLimitError("请求频率超限(429)，请稍后重试")

            # 处理其他HTTP错误
            if status_code >= 400:
                last_error = RuntimeError(f"HTTP错误: {status_code}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue

            # 解析JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                last_error = RuntimeError(f"JSON解析失败: {e}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue

            if data.get("code") not in (0, None) and data.get("message") != "success":
                raise RuntimeError(f"API错误: {data.get('message')}")

            return data.get("data", [])

        raise last_error or RuntimeError("请求失败，已重试最大次数")

    # ==================== 通用查询 ====================

    def query(self, endpoint: str, **params) -> List[Dict[str, Any]]:
        """
        通用查询接口

        Args:
            endpoint: API端点，支持 "/" 或 "." 分隔
                      如 "cn/company/fs/non_financial" 或 "cn.company.fs.non_financial"
            **params: API参数

        Returns:
            API返回的data字段
        """
        # 支持点号分隔的端点格式
        endpoint = endpoint.replace(".", "/")
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return self._post(endpoint, **params)

    def query_dataframe(self, endpoint: str, **params):
        """
        通用查询接口，返回DataFrame

        Args:
            endpoint: API端点
            **params: API参数

        Returns:
            pandas DataFrame
        """
        if not HAS_PANDAS:
            raise ImportError("需要安装pandas: pip install pandas")

        data = self.query(endpoint, **params)
        return pd.json_normalize(data)

    # ==================== 基础信息 ====================

    def get_company_info(
        self,
        stock_codes: Optional[List[str]] = None,
        fs_table_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        获取公司基础信息

        Args:
            stock_codes: 股票代码列表，如 ["600519", "000001"]
            fs_table_type: 财报类型 (non_financial, bank, insurance, security, other_financial)
        """
        kwargs = {"pageIndex": 0}
        if stock_codes:
            kwargs["stockCodes"] = stock_codes
        if fs_table_type:
            kwargs["fsTableType"] = fs_table_type
        return self._post("cn/company", **kwargs)

    # ==================== 财务报表 ====================

    def get_financial_statements(
        self,
        stock_codes: List[str],
        metrics_list: List[str],
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fs_type: str = "non_financial",
    ) -> List[Dict]:
        """
        获取财务报表数据

        Args:
            stock_codes: 股票代码列表
            metrics_list: 指标列表，如 ["q.ps.toi.t", "q.bs.ar.c_y2y"]
            date: 指定日期 (YYYY-MM-DD) 或 "latest"
            start_date: 起始日期
            end_date: 结束日期
            fs_type: 财报类型

        指标格式: [granularity].[tableName].[fieldName].[expressionCalculateType]
        - granularity: y(年), hy(半年), q(季度)
        - tableName: bs(资产负债表), ps(利润表), cfs(现金流量表), m(财务指标)
        - expressionCalculateType: t(当期), c(单季), ttm, t_y2y(同比), c_c2c(环比)等
        """
        endpoint = f"cn/company/fs/{fs_type}"
        kwargs = {
            "stockCodes": stock_codes,
            "metricsList": metrics_list,
        }
        if date:
            kwargs["date"] = date
        if start_date:
            kwargs["startDate"] = start_date
        if end_date:
            kwargs["endDate"] = end_date

        return self._post(endpoint, **kwargs)

    # ==================== 基本面数据 ====================

    def get_fundamental(
        self,
        stock_codes: List[str],
        metrics_list: List[str],
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fs_type: str = "non_financial",
    ) -> List[Dict]:
        """
        获取基本面数据（估值指标等）

        Args:
            stock_codes: 股票代码列表
            metrics_list: 指标列表，如 ["pe_ttm", "pb", "mc", "dyr"]
            date: 指定日期
            start_date: 起始日期
            end_date: 结束日期
            fs_type: 财报类型

        估值指标: pe_ttm, d_pe_ttm, pb, pb_wo_gw, ps_ttm, dyr, pcf_ttm, ev_ebit_r, ev_ebitda_r, mc, sp等
        估值统计: {指标}.{周期}.{统计类型}，如 pe_ttm.y5.cvpos (5年PE分位)
        """
        endpoint = f"cn/company/fundamental/{fs_type}"
        kwargs = {
            "stockCodes": stock_codes,
            "metricsList": metrics_list,
        }
        if date:
            kwargs["date"] = date
        if start_date:
            kwargs["startDate"] = start_date
        if end_date:
            kwargs["endDate"] = end_date

        return self._post(endpoint, **kwargs)

    # ==================== 便捷方法 ====================

    def get_latest_financials(
        self,
        stock_code: str,
        quarters: int = 8,
    ) -> List[Dict]:
        """
        获取最近N个季度的核心财务数据

        Args:
            stock_code: 股票代码
            quarters: 季度数量，默认8个季度(2年)
        """
        metrics = [
            # 利润表
            "q.ps.toi.t",       # 营业总收入(累计)
            "q.ps.toi.c",       # 营业总收入(单季)
            "q.ps.toi.c_y2y",   # 营业总收入同比
            "q.ps.np.t",        # 净利润(累计)
            "q.ps.np.c",        # 净利润(单季)
            "q.ps.np.c_y2y",    # 净利润同比
            "q.ps.npatoshopc.t",  # 归母净利润(累计)
            "q.ps.npatoshopc.c",  # 归母净利润(单季)
            "q.ps.gp_m.c",      # 毛利率(单季)
            "q.ps.np_s_r.c",    # 净利率(单季)
            # 资产负债表
            "q.bs.ta.t",        # 总资产
            "q.bs.tl.t",        # 总负债
            "q.bs.toe.t",       # 股东权益
            "q.bs.ar.t",        # 应收账款
            "q.bs.i.t",         # 存货
            "q.bs.tl_ta_r.t",   # 资产负债率
            # 现金流量表
            "q.cfs.ncffoa.t",   # 经营现金流净额(累计)
            "q.cfs.ncffoa.c",   # 经营现金流净额(单季)
            # 财务指标
            "q.m.roe.c",        # ROE(单季)
            "q.m.roa.c",        # ROA(单季)
        ]

        return self.get_financial_statements(
            stock_codes=[stock_code],
            metrics_list=metrics,
            date="latest",
        )

    def get_valuation(
        self,
        stock_code: str,
        with_percentile: bool = True,
    ) -> Dict:
        """
        获取估值数据及历史分位

        Args:
            stock_code: 股票代码
            with_percentile: 是否包含历史分位数
        """
        metrics = [
            "pe_ttm", "d_pe_ttm", "pb", "pb_wo_gw", "ps_ttm", "pcf_ttm",
            "dyr", "mc", "ev_ebit_r", "ev_ebitda_r", "sp",
        ]

        if with_percentile:
            for m in ["pe_ttm", "pb", "ps_ttm"]:
                metrics.extend([
                    f"{m}.y5.cvpos",   # 5年分位
                    f"{m}.y5.avgv",    # 5年均值
                    f"{m}.y5.minv",    # 5年最小
                    f"{m}.y5.maxv",    # 5年最大
                ])

        data = self.get_fundamental(
            stock_codes=[stock_code],
            metrics_list=metrics,
            date="latest",
        )

        return data[0] if data else {}

    # ==================== K线数据 ====================

    def get_candlestick(
        self,
        stock_code: str,
        start_date: str,
        end_date: Optional[str] = None,
        adjust_type: str = "lxr_fc_rights",
    ) -> List[Dict]:
        """
        获取K线数据

        Args:
            stock_code: 股票代码
            start_date: 起始日期 (YYYY-MM-DD)，必填，与end_date间隔不超过10年
            end_date: 结束日期 (YYYY-MM-DD)，默认为上周一
            adjust_type: 复权类型
                - ex_rights: 不复权
                - lxr_fc_rights: 理杏仁前复权（默认）
                - fc_rights: 前复权
                - bc_rights: 后复权

        Returns:
            K线数据列表（按日期降序），每条包含:
            date, stockCode, open, close, high, low,
            volume, amount, change, to_r, complexFactor
        """
        kwargs = {
            "stockCode": stock_code,
            "startDate": start_date,
            "type": adjust_type,
        }
        if end_date:
            kwargs["endDate"] = end_date
        return self._post("cn/company/candlestick", **kwargs)

    def get_klines(
        self,
        stock_code: str,
        days: int = 250,
        adjust_type: str = "lxr_fc_rights",
    ) -> List[Dict]:
        """
        便捷方法：获取最近N个交易日的K线数据

        自动计算起始日期（按交易日约占自然日的70%估算）

        Args:
            stock_code: 股票代码
            days: 交易日数量，默认250（约1年）
            adjust_type: 复权类型
        """
        from datetime import datetime, timedelta

        # 交易日约占自然日70%，多取一些确保覆盖
        natural_days = int(days / 0.7) + 10
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=natural_days)).strftime("%Y-%m-%d")

        data = self.get_candlestick(
            stock_code,
            start_date=start_date,
            end_date=end_date,
            adjust_type=adjust_type,
        )
        # 返回最近N条（API返回按日期降序）
        return data[:days]
