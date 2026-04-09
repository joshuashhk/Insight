"""
巨潮资讯API客户端

用于从巨潮资讯(cninfo.com.cn)获取公告PDF下载链接
支持上交所和深交所股票
"""
import re
import time
import json
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class CninfoClient:
    """巨潮资讯API客户端 - 用于获取PDF下载链接"""

    BASE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    PDF_BASE_URL = "https://static.cninfo.com.cn/"

    # 公告类别映射（用于年报和中报的分类筛选）
    CATEGORIES = {
        "annual_report": "category_ndbg_szsh",      # 年度报告
        "semi_annual_report": "category_bndbg_szsh", # 半年度报告
    }

    def __init__(self):
        self.session_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        self._resolve_flags = self._get_resolve_flags()

    def _get_resolve_flags(self):
        """通过nslookup解析cninfo域名IP，生成curl --resolve参数（绕过系统DNS失效问题）"""
        import subprocess as sp
        flags = []
        for domain, ports in [("www.cninfo.com.cn", [80, 443]), ("static.cninfo.com.cn", [80, 443])]:
            try:
                r = sp.run(["nslookup", domain], capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    if "Address:" in line and "#" not in line:
                        ip = line.split("Address:")[-1].strip()
                        if ip:
                            for port in ports:
                                flags += ["--resolve", f"{domain}:{port}:{ip}"]
                            break
            except Exception:
                pass
        return flags

    def search_announcements(self, stock_code: str, category: str = None,
                            start_date: str = None, end_date: str = None,
                            keyword: str = None) -> List[Dict]:
        """
        搜索公告

        Args:
            stock_code: 股票代码 (如 603929)
            category: 公告类别 (annual_report, semi_annual_report, prospectus)
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            keyword: 搜索关键词

        Returns:
            公告列表，每条包含 announcementId, announcementTitle, adjunctUrl 等
        """
        # 构建分类参数
        cat_param = ""
        if category and category in self.CATEGORIES:
            cat_param = self.CATEGORIES[category]

        # 构建日期范围
        date_range = ""
        if start_date and end_date:
            date_range = f"{start_date}~{end_date}"

        # 判断交易所
        # 6开头为上交所，0/3开头为深交所
        if stock_code.startswith("6"):
            column = "sse"
        else:
            column = "szse"

        # 构建搜索关键词
        # 如果提供了keyword，将其与股票代码组合搜索
        searchkey = stock_code
        if keyword:
            searchkey = f"{stock_code} {keyword}"

        # 构建请求参数
        params = {
            "pageNum": 1,
            "pageSize": 100,
            "tabName": "fulltext",
            "column": column,
            "searchkey": searchkey,
        }
        if cat_param:
            params["category"] = cat_param
        if date_range:
            params["seDate"] = date_range

        # 发送请求（最多重试3次，使用curl确保硬超时）
        data = urllib.parse.urlencode(params)

        for attempt in range(3):
            try:
                result = subprocess.run(
                    [
                        "curl", "-s",
                        "--connect-timeout", "5",
                        "--max-time", "10",
                        *self._resolve_flags,
                        "-X", "POST", self.BASE_URL,
                        "-H", "Content-Type: application/x-www-form-urlencoded",
                        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "-H", "Accept: application/json",
                        "-d", data,
                    ],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"curl failed: {result.stderr}")
                parsed = json.loads(result.stdout)
                announcements = parsed.get("announcements", []) or []
                return announcements
            except Exception as e:
                if attempt < 2:
                    print(f"  cninfo API重试 {attempt + 2}/3...")
                    time.sleep(2)
                else:
                    print(f"  cninfo API查询失败: {e}")
                    return []
        return []

    def get_pdf_url(self, adjunct_url: str) -> str:
        """获取完整的PDF下载URL"""
        if adjunct_url.startswith("http"):
            return adjunct_url
        return self.PDF_BASE_URL + adjunct_url

    def find_matching_announcement(self, stock_code: str, title_keywords: List[str],
                                   date: str = None, category: str = None,
                                   exclude_summary: bool = False) -> Optional[str]:
        """
        根据标题关键词查找匹配的公告，返回PDF URL

        Args:
            stock_code: 股票代码
            title_keywords: 标题必须包含的关键词列表
            date: 公告日期 YYYY-MM-DD（用于精确匹配）
            category: 公告类别
            exclude_summary: 是否排除摘要版本

        Returns:
            匹配的PDF URL，未找到返回None
        """
        # 计算搜索日期范围
        # 对于中报和年报，使用更大的时间范围（可能上交所和巨潮的日期不完全一致）
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                start = (dt - timedelta(days=30)).strftime("%Y-%m-%d")
                end = (dt + timedelta(days=30)).strftime("%Y-%m-%d")
            except ValueError:
                # 如果日期解析失败，使用更大范围
                start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
                end = datetime.now().strftime("%Y-%m-%d")
        else:
            # 没有指定日期，搜索最近3年
            start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")

        # 搜索公告
        announcements = self.search_announcements(
            stock_code=stock_code,
            category=category,
            start_date=start,
            end_date=end
        )

        if not announcements:
            return None

        # 过滤并查找匹配的公告
        candidates = []
        for ann in announcements:
            title = ann.get("announcementTitle", "")
            adjunct_url = ann.get("adjunctUrl", "")

            # 严格过滤：只保留目标股票的公告（防止子公司/关联公司混入）
            sec_code = ann.get("secCode", "")
            if sec_code and sec_code != stock_code:
                continue

            # 排除摘要版本
            if exclude_summary and "摘要" in title:
                continue

            # 排除H股/港股版本和英文版
            if "H股" in title or re.search(r'港股(?!份)', title) or "英文" in title:
                continue

            # 排除非年报本体（标题含年份但不是年报本身）
            if any(ex in title for ex in ["书面确认意见", "审核意见", "督导", "问询", "更正", "补充"]):
                continue

            # 检查所有关键词是否都在标题中
            if all(kw in title for kw in title_keywords):
                ann_time = ann.get("announcementTime", 0)
                ann_date = ""
                if ann_time:
                    ann_date = datetime.fromtimestamp(ann_time / 1000).strftime("%Y-%m-%d")
                candidates.append({
                    "title": title,
                    "url": self.get_pdf_url(adjunct_url),
                    "date": ann_date,
                    "time": ann_time,
                    "exact_date_match": ann_date == date if date else False
                })

        if not candidates:
            return None

        # 排序：精确日期匹配优先，全文版本优先，时间倒序
        # cninfo上年度报告摘要有时不带"摘要"字样，全文版才带"全文"，需优先选全文
        candidates.sort(key=lambda x: (
            0 if x["exact_date_match"] else 1,
            0 if "全文" in x["title"] else 1,
            -x["time"]
        ))

        # 如果有多个候选且标题相同（可能摘要和全文混在一起），用 HEAD 请求比较文件大小
        if len(candidates) > 1:
            first_title = candidates[0]["title"]
            same_title = [c for c in candidates if c["title"] == first_title]
            if len(same_title) > 1:
                best_url, best_size = same_title[0]["url"], -1
                for c in same_title:
                    try:
                        req = urllib.request.Request(c["url"], method="HEAD")
                        req.add_header("User-Agent", "Mozilla/5.0")
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            size = int(resp.headers.get("Content-Length", 0))
                        if size > best_size:
                            best_size, best_url = size, c["url"]
                    except Exception:
                        pass
                return best_url

        return candidates[0]["url"]

    def search_prospectus(self, stock_code: str, doc_type: str = "ipo") -> Optional[str]:
        """
        搜索招股说明书或募集说明书

        Args:
            stock_code: 股票代码
            doc_type: 文档类型
                - "ipo": 首次公开发行招股说明书
                - "spo": 增发/定增募集说明书
                - "convertible": 可转债募集说明书

        Returns:
            PDF URL，未找到返回None
        """
        # 根据类型确定搜索关键词
        if doc_type == "ipo":
            keyword = "招股说明书"
            exclude_keywords = ["提示性公告", "意向书", "摘要", "更正", "修订"]
        elif doc_type == "spo":
            keyword = "募集说明书"
            exclude_keywords = ["提示性公告", "摘要", "更正", "可转换", "可转债"]
        elif doc_type == "convertible":
            keyword = "可转换公司债券募集说明书"
            exclude_keywords = ["提示性公告", "摘要", "更正"]
        else:
            return None

        # 使用关键词搜索
        announcements = self.search_announcements(
            stock_code=stock_code,
            keyword=keyword,
            start_date=(datetime.now() - timedelta(days=365 * 10)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d")
        )

        if not announcements:
            return None

        # 筛选最佳匹配
        # 优先级：注册稿 > 无标注 > 申报稿
        candidates = []
        for ann in announcements:
            title = ann.get("announcementTitle", "")
            adjunct_url = ann.get("adjunctUrl", "")

            # 必须包含主关键词
            if keyword not in title:
                continue

            # 排除不需要的公告
            if any(ex in title for ex in exclude_keywords):
                continue

            # 计算优先级
            if "注册稿" in title:
                priority = 0  # 最高优先级
            elif "申报稿" in title:
                priority = 2  # 最低优先级
            else:
                priority = 1  # 中间优先级（正式稿）

            ann_time = ann.get("announcementTime", 0)
            candidates.append({
                "title": title,
                "url": self.get_pdf_url(adjunct_url),
                "priority": priority,
                "time": ann_time
            })

        if not candidates:
            return None

        # 按优先级排序，同优先级按时间倒序
        candidates.sort(key=lambda x: (x["priority"], -x["time"]))

        return candidates[0]["url"]
