"""
公告下载器

下载重要公司文件：
- 最近三年年报和中报
- 招股说明书（首发和增发）
- 可转债募集说明书

支持的数据源：
- 理杏仁API: 获取公告列表
- 巨潮资讯(cninfo): 下载PDF文件（支持上交所和深交所）
"""
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sources.structured.financial import LixingerClient
from sources.unstructured.announcements.cninfo import CninfoClient


class AnnouncementDownloader:
    """公告下载器"""

    def __init__(self, stock_code: str, years: int = 3):
        self.stock_code = stock_code
        self.years = years
        self.client = LixingerClient()
        self.cninfo = CninfoClient()

        # 计算时间范围（API限制最多10年）
        self.end_date = datetime.now().strftime("%Y-%m-%d")
        self.start_date = (datetime.now() - timedelta(days=10 * 365)).strftime("%Y-%m-%d")

    def fetch_announcements(self) -> List[Dict]:
        """获取公告列表（一次性获取所有公告，最多10年）"""
        try:
            data = self.client.query(
                "cn/company/announcement",
                stockCode=self.stock_code,
                startDate=self.start_date,
                endDate=self.end_date
            )
            return data
        except Exception as e:
            print(f"获取公告失败: {e}")
            return []

    def filter_important_announcements(self, announcements: List[Dict]) -> Dict[str, List[Dict]]:
        """筛选重要公告"""
        result = {
            "annual_reports": [],       # 年报
            "semi_annual_reports": [],  # 中报
            "prospectus": [],           # 招股说明书
            "spo_prospectus": [],       # 增发募集说明书
            "convertible_bonds": [],    # 可转债募集说明书
        }

        # 计算3年前的日期 - 所有公告都限制在最近3年
        three_years_ago = (datetime.now() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        for ann in announcements:
            link_text = ann.get("linkText", "")
            types = ann.get("types", [])
            date = ann.get("date", "")[:10]

            # 跳过摘要、更正、取消、英文版、审计报告、督导报告、说明会通知、问询函等
            if any(skip in link_text for skip in ["摘要", "更正", "取消", "英文", "已取消", "附录", "披露", "审计", "会计师", "督导", "提示性公告", "更新", "说明会", "问询", "补充", "监事会", "工作函", "书面确认意见"]):
                continue

            # 跳过未来日期（API可能返回预期数据）
            if date > today:
                continue

            # 所有公告都限制在最近3年
            if date < three_years_ago:
                continue

            # 年报（只要A股主报告，排除H股/港股）
            if "fs" in types or "fs_full" in types:
                if ("年度报告" in link_text or "年报" in link_text) and "半年" not in link_text:
                    if "季度" not in link_text and "H股" not in link_text and not re.search(r'港股(?!份)', link_text):
                        result["annual_reports"].append(ann)

            # 中报（排除H股/港股）
            if "fs" in types or "fs_full" in types:
                if ("半年度报告" in link_text or "半年报" in link_text) and "H股" not in link_text and not re.search(r'港股(?!份)', link_text):
                    result["semi_annual_reports"].append(ann)

            # 招股说明书（只要A股招股说明书，排除意向书和H股）
            if "ipo" in types:
                if "招股说明书" in link_text and "意向" not in link_text and "H股" not in link_text and "保险" not in link_text:
                    result["prospectus"].append(ann)

            # 增发募集说明书（收集所有，后续筛选最终稿）
            if "spo" in types:
                if "募集说明书" in link_text:
                    result["spo_prospectus"].append(ann)

            # 可转债募集说明书（收集所有，后续筛选最终稿）
            if "c_b" in types:
                if "募集说明书" in link_text:
                    result["convertible_bonds"].append(ann)

        # 去重并按日期排序
        for key in result:
            seen_urls = set()
            unique_list = []
            for ann in result[key]:
                url = ann.get("linkUrl", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_list.append(ann)
            result[key] = sorted(unique_list, key=lambda x: x.get("date", ""), reverse=True)

        # 年报：同年份只保留修订版，有修订版时去掉原版
        by_year: Dict[str, List[Dict]] = {}
        for ann in result["annual_reports"]:
            year_match = re.search(r'(\d{4})年', ann.get("linkText", ""))
            year = year_match.group(1) if year_match else ""
            by_year.setdefault(year, []).append(ann)

        deduped_annual = []
        for _, year_anns in by_year.items():
            revised = [a for a in year_anns if "修订版" in a.get("linkText", "")]
            deduped_annual.append(revised[0] if revised else year_anns[0])
        result["annual_reports"] = sorted(deduped_annual, key=lambda x: x.get("date", ""), reverse=True)

        # 中报：只保留最新一期，且对应年份无年报时才保留
        annual_years = set()
        for ann in result["annual_reports"]:
            year_match = re.search(r'(\d{4})年', ann.get("linkText", ""))
            if year_match:
                annual_years.add(year_match.group(1))
        if result["semi_annual_reports"]:
            latest = result["semi_annual_reports"][0]  # 已按日期倒序
            year_match = re.search(r'(\d{4})年', latest.get("linkText", ""))
            latest_year = year_match.group(1) if year_match else None
            if latest_year and latest_year not in annual_years:
                result["semi_annual_reports"] = [latest]
            else:
                result["semi_annual_reports"] = []

        # 对募集说明书类公告，只保留每次募资的最终稿
        result["spo_prospectus"] = self._filter_final_prospectus(result["spo_prospectus"])
        result["convertible_bonds"] = self._filter_final_prospectus(result["convertible_bonds"])

        return result

    def _filter_final_prospectus(self, announcements: List[Dict]) -> List[Dict]:
        """
        筛选募集说明书的最终稿
        优先级：注册稿 > 无标注版本 > 申报稿
        同一次募资只保留最新的最终稿

        注意：同一个募资项目可能跨多年（如2023年申报，2025年注册），
        通过标题中的年度标识识别同一项目
        """
        if not announcements:
            return []

        # 按募资年度分组（标题中提到的年度，如"2023年度向特定对象发行"）
        by_fundraise_year = {}
        for ann in announcements:
            link_text = ann.get("linkText", "")

            # 提取募资年度标识（如"2023年度"）
            year_match = re.search(r'(\d{4})年度', link_text)
            if year_match:
                fundraise_year = year_match.group(1)
            else:
                # 如果标题中没有年度标识，使用公告日期年份
                date = ann.get("date", "")[:10]
                fundraise_year = date[:4]

            if fundraise_year not in by_fundraise_year:
                by_fundraise_year[fundraise_year] = []
            by_fundraise_year[fundraise_year].append(ann)

        # 每个募资项目只保留最终稿
        final_list = []
        for year, anns in by_fundraise_year.items():
            # 按优先级排序：注册稿 > 无标注 > 申报稿
            def get_priority(ann):
                text = ann.get("linkText", "")
                if "注册稿" in text:
                    return 0  # 最高优先级 - 已完成注册
                elif "申报稿" in text:
                    return 2  # 最低优先级 - 刚申报
                else:
                    return 1  # 中间优先级（可能是正式稿或修订稿）

            # 先按优先级，再按日期排序（最新的在前）
            sorted_anns = sorted(anns, key=lambda x: (get_priority(x), -int(x.get("date", "")[:10].replace("-", ""))))

            # 只有当最终稿是注册稿或无标注版本时才保留
            if sorted_anns:
                best = sorted_anns[0]
                # 如果最好的只是申报稿，说明这个项目还没完成，跳过
                if "申报稿" not in best.get("linkText", ""):
                    final_list.append(best)

        # 按日期排序返回
        return sorted(final_list, key=lambda x: x.get("date", ""), reverse=True)

    def download_file(self, url: str, save_path: Path, timeout: int = 20,
                      title: str = None, date: str = None, category: str = None) -> bool:
        """
        下载文件 - 支持多种下载源

        对于上交所文件，自动尝试从巨潮资讯下载（无反爬保护）
        """
        try:
            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查URL来源
            is_sse_url = "sse.com.cn" in url  # 上交所有反爬保护

            if is_sse_url:
                # 尝试从巨潮资讯获取替代URL
                cninfo_url = self._get_cninfo_url(title, date, category)
                if cninfo_url:
                    print(f"    使用cninfo替代下载...")
                    for attempt in range(3):
                        if self._download_with_curl(cninfo_url, save_path, timeout, category):
                            return True
                        if attempt < 2:
                            print(f"    重试 {attempt + 2}/3...")
                            time.sleep(2)
                    print(f"    cninfo下载失败，标记为手动下载")
                else:
                    print(f"    cninfo未找到匹配，标记为手动下载")
                return False

            # 直接用curl下载（适用于深交所、cninfo等其他站点）
            for attempt in range(3):
                if self._download_with_curl(url, save_path, timeout, category):
                    return True
                if attempt < 2:
                    print(f"    重试 {attempt + 2}/3...")
                    time.sleep(2)

            # 深交所等下载失败时，尝试从cninfo获取备用URL
            print(f"    原始URL下载失败，尝试cninfo备用...")
            cninfo_url = self._get_cninfo_url(title, date, category)
            if cninfo_url:
                for attempt in range(3):
                    if self._download_with_curl(cninfo_url, save_path, timeout, category):
                        return True
                    if attempt < 2:
                        print(f"    cninfo重试 {attempt + 2}/3...")
                        time.sleep(2)

            return False

        except Exception as e:
            print(f"    下载异常: {e}")
            if save_path.exists():
                save_path.unlink()
            return False

    def _get_cninfo_url(self, title: str, date: str, category: str) -> Optional[str]:
        """从巨潮资讯获取PDF URL"""
        if not title:
            return None

        # 招股说明书 - 使用专门的搜索方法
        if "招股说明书" in title and "意向" not in title:
            return self.cninfo.search_prospectus(self.stock_code, doc_type="ipo")

        # 可转债募集说明书 - 使用专门的搜索方法
        if "可转换公司债券募集说明书" in title or "可转债募集说明书" in title:
            return self.cninfo.search_prospectus(self.stock_code, doc_type="convertible")

        # 增发募集说明书 - 使用专门的搜索方法
        if "募集说明书" in title and "可转" not in title:
            return self.cninfo.search_prospectus(self.stock_code, doc_type="spo")

        # 年报和中报 - 使用关键词匹配
        keywords = []
        cat = category

        if ("年度报告" in title or "年报" in title) and "半年" not in title:
            # 年报: 仅用年份匹配，category过滤已限定为年报类；
            # 不加"年度报告"或"年报"关键词，因为两者互不为子串
            year_match = re.search(r'(\d{4})', title)
            if year_match:
                keywords.append(year_match.group(1))
            cat = "annual_report"
        elif "半年度报告" in title:
            # 中报: 提取年份
            year_match = re.search(r'(\d{4})年', title)
            if year_match:
                keywords.append(year_match.group(1))
            keywords.append("半年度报告")
            cat = "semi_annual_report"
        else:
            # 其他类型：使用前10个字符
            keywords.append(title[:10])

        # 如果标题包含"全文"且不含"摘要"，添加"全文"关键词以精确匹配
        if "全文" in title and "摘要" not in title:
            keywords.append("全文")

        # 排除"摘要"版本 - 如果原标题不是摘要
        exclude_summary = "摘要" not in title

        # 年报/中报：不传日期，用年份关键词即可唯一定位
        # 原因：巨潮可能在SSE发布日期后很久才有更正版，±30天窗口会漏掉
        cninfo_date = None if cat in ("annual_report", "semi_annual_report") else date

        return self.cninfo.find_matching_announcement(
            stock_code=self.stock_code,
            title_keywords=keywords,
            date=cninfo_date,
            category=cat,
            exclude_summary=exclude_summary
        )

    def _download_with_curl(self, url: str, save_path: Path, timeout: int, category: str = None) -> bool:
        """使用curl下载"""
        try:
            cmd = [
                "curl", "-L", "-s", "-o", str(save_path),
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "-H", "Accept: application/pdf,application/octet-stream,*/*",
                "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
                "-H", "Referer: https://www.sse.com.cn/",
                "--compressed",
                "--connect-timeout", "10",
                "--max-time", str(timeout),
                url
            ]

            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

            if save_path.exists() and self._is_valid_pdf(save_path, category):
                return True

            if save_path.exists():
                save_path.unlink()
            return False

        except Exception:
            if save_path.exists():
                save_path.unlink()
            return False

    def _is_valid_pdf(self, path: Path, category: str = None) -> bool:
        """验证是否为有效PDF文件（检查头部和尾部标记）"""
        # 年报/中报/招股说明书通常较大，提高最小文件大小阈值以过滤误下载的公告
        min_size = {
            "annual_reports": 500000,       # 年报至少500KB
            "semi_annual_reports": 300000,   # 中报至少300KB
            "prospectus": 500000,            # 招股说明书至少500KB
        }.get(category, 100000)
        if not path.exists() or path.stat().st_size < min_size:
            return False
        try:
            with open(path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    return False
                # 检查尾部是否有 %%EOF 标记（截断的PDF不会有）
                f.seek(max(0, path.stat().st_size - 4096))
                tail = f.read()
                return b'%%EOF' in tail
        except Exception:
            return False

    def sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        # 移除非法字符
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # 限制长度
        if len(name) > 100:
            name = name[:100]
        return name.strip()

    def download_announcements(self, output_dir: Path, filtered: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """下载所有筛选后的公告"""
        downloaded = {
            "annual_reports": [],
            "semi_annual_reports": [],
            "prospectus": [],
            "spo_prospectus": [],
            "convertible_bonds": [],
        }

        # 需要手动下载的链接（上交所等有反爬保护的站点）
        manual_links = []

        # 创建子目录
        dirs = {
            "annual_reports": output_dir / "年报",
            "semi_annual_reports": output_dir / "中报",
            "prospectus": output_dir / "招股说明书",
            "spo_prospectus": output_dir / "增发",
            "convertible_bonds": output_dir / "可转债",
        }

        for key, announcements in filtered.items():
            if not announcements:
                continue

            target_dir = dirs[key]
            target_dir.mkdir(parents=True, exist_ok=True)

            for ann in announcements:
                url = ann.get("linkUrl", "")
                link_text = ann.get("linkText", "")
                date = ann.get("date", "")[:10]  # YYYY-MM-DD

                if not url:
                    continue

                # 生成文件名
                filename = f"{date}_{self.sanitize_filename(link_text)}.pdf"
                save_path = target_dir / filename

                # 如果文件已存在，跳过
                if save_path.exists():
                    print(f"  已存在: {filename}")
                    downloaded[key].append(str(save_path))
                    continue

                print(f"  下载: {link_text[:50]}...")
                # 传递标题、日期、类别信息，用于从cninfo查找替代下载源
                if self.download_file(url, save_path, title=link_text, date=date, category=key):
                    downloaded[key].append(str(save_path))
                    print(f"  成功: {filename}")
                else:
                    # 记录需要手动下载的链接
                    manual_links.append({
                        "category": key,
                        "title": link_text,
                        "date": date,
                        "url": url,
                        "save_as": str(save_path),
                    })

                # 避免请求过快（cninfo可能有限流）
                time.sleep(1.0)

        # 如果有需要手动下载的链接，保存到文件
        if manual_links:
            links_file = output_dir / "需手动下载.txt"
            with open(links_file, "w", encoding="utf-8") as f:
                f.write("以下文件需要通过浏览器手动下载（上交所等站点有反爬保护）：\n\n")
                for item in manual_links:
                    f.write(f"【{item['category']}】{item['title']}\n")
                    f.write(f"  日期: {item['date']}\n")
                    f.write(f"  链接: {item['url']}\n")
                    f.write(f"  保存为: {item['save_as']}\n\n")
            print(f"\n{len(manual_links)} 个文件需要手动下载，详见: {links_file}")

        return {"downloaded": downloaded, "manual_links": manual_links}

    def build_memory_summaries(self) -> Dict[str, str]:
        """
        汇总所有文档类型到memory目录

        Returns:
            {文档类型: 摘要文件路径}
        """
        from skills.financial_analysis.build_memory import build_all_memory

        print(f"\n汇总到memory...")
        return build_all_memory(self.stock_code)

    def run(self, output_dir: Path) -> Dict[str, Any]:
        """执行完整的下载流程"""
        print(f"当前日期: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"获取 {self.stock_code} 的公告列表...")

        # 获取公告
        announcements = self.fetch_announcements()
        print(f"共获取 {len(announcements)} 条公告")

        # 筛选重要公告
        filtered = self.filter_important_announcements(announcements)

        total = sum(len(v) for v in filtered.values())
        print(f"筛选出 {total} 条重要公告:")
        for key, items in filtered.items():
            if items:
                print(f"  - {key}: {len(items)} 条")

        # 下载文件
        print(f"\n开始下载到 {output_dir}...")
        result = self.download_announcements(output_dir, filtered)
        downloaded = result["downloaded"]
        manual_links = result["manual_links"]

        # 统计结果
        success_count = sum(len(v) for v in downloaded.values())
        print(f"\n下载完成: {success_count}/{total}")
        if manual_links:
            print(f"需手动下载: {len(manual_links)}")

        # 汇总到memory（直接从PDF提取关键章节）
        memory_files = self.build_memory_summaries()

        return {
            "filtered": filtered,
            "downloaded": downloaded,
            "memory_files": memory_files,
            "manual_links": manual_links,
            "stats": {
                "total_found": len(announcements),
                "total_filtered": total,
                "total_downloaded": success_count,
                "total_memory": len(memory_files),
                "total_manual": len(manual_links),
            }
        }
