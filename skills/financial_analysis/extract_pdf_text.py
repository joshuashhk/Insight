"""
PDF文本提取模块

从年报、中报、招股说明书、募集说明书等PDF文件中提取关键章节文本，输出为Markdown格式。
由于财务数据已从数据库获取，本模块专注于提取定性内容。
"""
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("请安装 pdfplumber: pip install pdfplumber")
    sys.exit(1)


# 年报/中报关键章节（结构相同）
# 公司简介信息已由JSON提供，不再从PDF重复提取
# "主要经营情况"以财务表格为主，与JSON重复，不再提取
ANNUAL_REPORT_SECTIONS = {
    "管理层讨论与分析": {
        "keywords": ["管理层讨论与分析", "经营层讨论与分析"],
        "description": "最重要章节：业务回顾、经营分析、未来展望（含风险因素）",
    },
}

# 银行/证券年报/中报关键章节：财务数据结构特殊，额外提取"主要财务信息"
BANK_SECURITY_ANNUAL_REPORT_SECTIONS = {
    "主要财务信息": {
        "keywords": ["主要财务数据", "主要财务信息", "主要会计数据", "主要财务指标"],
        "description": "核心财务指标：净息差、资本充足率、不良贷款率等行业特有指标",
    },
    "管理层讨论与分析": {
        "keywords": ["管理层讨论与分析", "经营层讨论与分析", "管理层讨论和分析"],
        "description": "最重要章节：业务回顾、经营分析、未来展望（含风险因素）",
    },
}

# 招股说明书关键章节
# "发行人基本情况"与JSON/年报重复（公司概况、股权等），不再提取
# 保留"业务与技术"因为招股书对业务的描述通常比年报更全面详尽
IPO_PROSPECTUS_SECTIONS = {
    "风险因素": {
        "keywords": ["风险因素"],
        "description": "各类风险提示"
    },
    "业务与技术": {
        "keywords": ["业务与技术", "发行人业务"],
        "description": "核心业务描述、竞争优势、行业地位"
    },
    "募集资金运用": {
        "keywords": ["募集资金运用", "未来发展规划"],
        "description": "资金用途和发展规划"
    },
}

# 增发募集说明书关键章节
# "发行人基本情况"与JSON/年报高度重复（公司概况、股权、行业、业务模式），不再提取
# 核心独有内容是"募集资金使用"（项目规划、可行性、效益预测）
SPO_PROSPECTUS_SECTIONS = {
    "募集资金使用": {
        "keywords": ["募集资金使用", "可行性分析"],
        "description": "募集资金用途和可行性分析"
    },
    "风险因素": {
        "keywords": ["风险因素"],
        "description": "发行相关风险"
    },
}

# 可转债募集说明书关键章节
# "发行人基本情况"与JSON/年报重复，不再提取
CONVERTIBLE_BOND_SECTIONS = {
    "风险因素": {
        "keywords": ["风险因素"],
        "description": "各类风险提示"
    },
    "募集资金运用": {
        "keywords": ["募集资金运用", "本次募集资金"],
        "description": "资金用途"
    },
}


class PDFExtractor:
    """PDF文本提取器"""

    def __init__(self, pdf_path: str, fs_type: str = "non_financial"):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        self.fs_type = fs_type
        # 根据文件名和路径判断文档类型
        self.doc_type = self._detect_doc_type()
        self.sections_config = self._get_sections_config()

    def _detect_doc_type(self) -> str:
        """检测文档类型"""
        filename = self.pdf_path.name
        parent_dir = self.pdf_path.parent.name

        # 按优先级检测
        if "可转" in filename or "可转债" in parent_dir:
            return "convertible_bond"
        elif "增发" in parent_dir or ("募集说明书" in filename and "招股" not in filename and "可转" not in filename):
            return "spo_prospectus"
        elif "招股" in filename or "招股说明书" in parent_dir:
            return "ipo_prospectus"
        elif "半年" in filename or "中报" in parent_dir:
            return "semi_annual"
        else:
            return "annual"

    def _get_sections_config(self) -> Dict:
        """获取章节配置"""
        # 银行/证券年报额外提取"主要财务信息"
        is_fin = self.fs_type in ("bank", "security")
        annual_config = BANK_SECURITY_ANNUAL_REPORT_SECTIONS if is_fin else ANNUAL_REPORT_SECTIONS
        configs = {
            "annual": annual_config,
            "semi_annual": annual_config,
            "ipo_prospectus": IPO_PROSPECTUS_SECTIONS,
            "spo_prospectus": SPO_PROSPECTUS_SECTIONS,
            "convertible_bond": CONVERTIBLE_BOND_SECTIONS,
        }
        return configs.get(self.doc_type, annual_config)

    def extract_all_text(self, page_range: Optional[Tuple[int, int]] = None) -> str:
        """
        提取全部文本，输出为Markdown格式

        Args:
            page_range: 页码范围 (start, end)，从0开始，end不包含

        Returns:
            Markdown格式的文本内容
        """
        texts = []
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)

            if page_range:
                start, end = page_range
                end = min(end, total_pages)
            else:
                start, end = 0, total_pages

            print(f"提取页面 {start+1} - {end} / {total_pages}")

            for i in range(start, end):
                page = pdf.pages[i]
                text = page.extract_text()
                if text:
                    # 清理噪声：页眉、页码
                    text = self._clean_page_text(text)
                    if text.strip():
                        texts.append(text)

        return "\n\n".join(texts)

    @staticmethod
    def _clean_page_text(text: str) -> str:
        """清理PDF提取文本中的噪声"""
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # 跳过页码行（如 "18 / 254"、"22/254"、"1-1-14"）
            if re.match(r'^\d+\s*/\s*\d+$', stripped):
                continue
            if re.match(r'^\d+-\d+-\d+$', stripped):
                continue
            # 跳过年报/中报页眉（如 "乐鑫信息科技（上海）股份有限公司2024年年度报告"）
            if re.match(r'^.{2,20}(股份有限公司|集团).{0,10}\d{4}年.{0,6}(年度|半年度)?报告$', stripped):
                continue
            # 跳过募集说明书页眉（如 "乐鑫信息科技（上海）股份有限公司 募集说明书（注册稿）"）
            if re.match(r'^.{2,20}(股份有限公司|集团)\s*募集说明书', stripped):
                continue
            # 跳过招股说明书页眉
            if re.match(r'^.{2,20}(股份有限公司|集团)\s*招股说明书', stripped):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def extract_toc(self) -> List[Dict]:
        """
        提取目录（通常在前20页）

        Returns:
            目录条目列表 [{"title": str, "page": int}, ...]
        """
        toc_entries = []
        # 匹配格式: 第X节/第X章/第X部分 标题 ... 页码
        toc_pattern = re.compile(r'(第[一二三四五六七八九十百]+[节章部]\s*[^\.\s…\d]+?)[\.\s…]+(\d+)')

        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i in range(min(20, len(pdf.pages))):
                text = pdf.pages[i].extract_text() or ""
                # 合并跨行的页码（如 "... 1\n0" → "... 10"）
                # 仅当合并后数字不超过总页数时才合并，避免误合页脚页码
                lines = text.split('\n')
                merged_lines = []
                for line in lines:
                    if merged_lines and re.match(r'^\d$', line.strip()):
                        candidate = merged_lines[-1] + line.strip()
                        last_num = re.search(r'(\d+)$', candidate)
                        if last_num and int(last_num.group(1)) <= total_pages:
                            merged_lines[-1] = candidate
                        else:
                            merged_lines.append(line)
                    else:
                        merged_lines.append(line)
                text = '\n'.join(merged_lines)
                matches = toc_pattern.findall(text)
                for title, page_num in matches:
                    title_clean = re.sub(r'\s+', ' ', title.strip())
                    # 去重
                    if not any(e["title"] == title_clean for e in toc_entries):
                        toc_entries.append({
                            "title": title_clean,
                            "page": int(page_num)
                        })

        return toc_entries

    def extract_toc_text(self) -> str:
        """
        提取目录并格式化为可读文本

        Returns:
            格式化的目录文本
        """
        toc = self.extract_toc()
        if not toc:
            return ""

        lines = []
        for entry in toc:
            # 格式: 第X节 标题 ... 页码
            lines.append(f"{entry['title']}... {entry['page']}")

        return "\n".join(lines)

    def extract_for_memory(self) -> Dict[str, any]:
        """
        提取目录和关键章节，供memory汇总使用

        Returns:
            {
                "toc": str,  # 格式化的目录文本
                "sections": {章节名: 内容}
            }
        """
        return {
            "toc": self.extract_toc_text(),
            "sections": self.extract_key_sections()
        }

    def find_section_by_toc(self, keywords: List[str]) -> Optional[Tuple[int, int]]:
        """
        通过目录查找章节页码范围

        Args:
            keywords: 章节标题关键词列表（任一匹配即可）

        Returns:
            (start_page, end_page) 页码（从0开始，end不包含）
        """
        toc = self.extract_toc()
        if not toc:
            return None

        # 查找匹配的章节
        target_idx = None
        for i, entry in enumerate(toc):
            for kw in keywords:
                if kw in entry["title"]:
                    target_idx = i
                    break
            if target_idx is not None:
                break

        if target_idx is None:
            return None

        start_page = toc[target_idx]["page"] - 1  # 转为0索引

        # 校验起始页码是否合理（不超过总页数）
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
        if start_page >= total_pages:
            return None  # 目录页码异常，回退到关键词搜索

        # 结束页为下一章节的开始页
        if target_idx + 1 < len(toc):
            end_page = toc[target_idx + 1]["page"]
            # 如果结束页码也异常，使用默认范围
            if end_page > total_pages:
                end_page = min(start_page + 50, total_pages)
        else:
            end_page = min(start_page + 50, total_pages)

        return (start_page, end_page)

    def find_section_pages(self, section_name: str) -> Optional[Tuple[int, int]]:
        """
        查找章节的页码范围

        Args:
            section_name: 章节名称

        Returns:
            (start_page, end_page) 或 None
        """
        if section_name not in self.sections_config:
            print(f"未知章节: {section_name}")
            return None

        config = self.sections_config[section_name]
        keywords = config.get("keywords", [section_name])

        # 优先通过目录查找
        result = self.find_section_by_toc(keywords)
        if result:
            return result

        # Fallback: 逐页搜索关键词（跳过前5页目录区域）
        with pdfplumber.open(self.pdf_path) as pdf:
            start_page = None
            for i, page in enumerate(pdf.pages):
                if i < 5:
                    continue
                text = page.extract_text() or ""
                for kw in keywords:
                    if kw in text and "第" in text and ("节" in text or "章" in text):
                        start_page = i
                        break
                if start_page is not None:
                    break

            if start_page is not None:
                return (start_page, min(start_page + 50, len(pdf.pages)))

        return None

    def extract_section(self, section_name: str) -> Optional[str]:
        """
        提取指定章节的文本

        Args:
            section_name: 章节名称

        Returns:
            Markdown格式的章节文本 或 None
        """
        page_range = self.find_section_pages(section_name)
        if page_range is None:
            print(f"未找到章节: {section_name}")
            return None

        print(f"章节 '{section_name}' 位于页面 {page_range[0]+1} - {page_range[1]}")
        text = self.extract_all_text(page_range)

        # 按配置跳过子章节（如"主要经营情况"以财务表格为主，与JSON重复）
        config = self.sections_config.get(section_name, {})
        skip_kws = config.get("skip_keywords", [])
        resume_kws = config.get("resume_keywords", [])
        if skip_kws and resume_kws and text:
            text = self._skip_subsection(text, skip_kws, resume_kws)

        return text

    @staticmethod
    def _skip_subsection(text: str, skip_keywords: List[str], resume_keywords: List[str]) -> str:
        """
        从文本中跳过指定子章节

        找到skip_keywords所在行作为跳过起点，resume_keywords所在行作为恢复点。
        """
        lines = text.split("\n")
        skip_start = None
        skip_end = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if skip_start is None:
                for kw in skip_keywords:
                    if kw in stripped:
                        skip_start = i
                        break
            elif skip_end is None:
                for kw in resume_keywords:
                    if kw in stripped:
                        skip_end = i
                        break

        if skip_start is not None and skip_end is not None:
            skipped = skip_end - skip_start
            kept = lines[:skip_start] + [f"\n[已跳过「主要经营情况」{skipped}行，财务数据详见公司信息.json]\n"] + lines[skip_end:]
            return "\n".join(kept)

        return text

    def extract_key_sections(self) -> Dict[str, str]:
        """
        提取所有关键章节

        Returns:
            {章节名: Markdown文本内容}
        """
        result = {}
        for section_name in self.sections_config:
            print(f"\n提取: {section_name}...")
            text = self.extract_section(section_name)
            if text:
                result[section_name] = text
        return result

    def save_markdown(self, text: str, section_name: str, output_path: Optional[str] = None) -> str:
        """
        保存为Markdown文件

        Args:
            text: 要保存的文本
            section_name: 章节名称（用于生成标题）
            output_path: 输出路径

        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_path = self.pdf_path.with_suffix('.md')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 添加Markdown标题
        pdf_name = self.pdf_path.stem
        header = f"# {section_name}\n\n**来源:** {pdf_name}\n\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header + text)

        print(f"已保存到: {output_path}")
        return str(output_path)


def extract_pdf(pdf_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    提取PDF关键章节的便捷函数

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录（默认在PDF同目录下创建md子目录）

    Returns:
        {章节名: 输出文件路径}
    """
    extractor = PDFExtractor(pdf_path)

    print(f"文档类型: {extractor.doc_type}")

    # 确定输出目录（默认与PDF同目录）
    if output_dir is None:
        output_dir = Path(pdf_path).parent
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 提取关键章节
    sections = extractor.extract_key_sections()

    # 保存文件
    saved_files = {}
    base_name = Path(pdf_path).stem

    for section_name, text in sections.items():
        output_path = output_dir / f"{base_name}_{section_name}.md"
        extractor.save_markdown(text, section_name, output_path)
        saved_files[section_name] = str(output_path)

    return saved_files


def batch_extract(stock_code: str, doc_type: str = "年报") -> Dict[str, Dict]:
    """
    批量提取某只股票的所有PDF文件

    Args:
        stock_code: 股票代码
        doc_type: 文档类型（年报、中报、招股说明书、增发、可转债等）

    Returns:
        {文件名: {章节名: 文件路径}}
    """
    project_root = Path(__file__).parent.parent.parent
    filings_dir = project_root / "stock" / stock_code / "filings" / doc_type

    if not filings_dir.exists():
        print(f"目录不存在: {filings_dir}")
        return {}

    results = {}
    pdf_files = list(filings_dir.glob("*.pdf"))

    print(f"找到 {len(pdf_files)} 个PDF文件")

    for pdf_path in pdf_files:
        print(f"\n{'='*60}")
        print(f"处理: {pdf_path.name}")
        print('='*60)

        try:
            saved = extract_pdf(str(pdf_path))
            results[pdf_path.name] = saved
        except Exception as e:
            print(f"处理失败: {e}")
            results[pdf_path.name] = {"error": str(e)}

    return results


# 保持向后兼容
extract_annual_report = extract_pdf


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  提取单个PDF:  python extract_pdf_text.py <PDF路径>")
        print("  批量提取:     python extract_pdf_text.py <股票代码> [文档类型]")
        print()
        print("文档类型: 年报、中报、招股说明书、增发、可转债")
        print()
        print("示例:")
        print("  python extract_pdf_text.py stock/688018/filings/年报/xxx.pdf")
        print("  python extract_pdf_text.py 688018 年报")
        print("  python extract_pdf_text.py 301548 招股说明书")
        sys.exit(1)

    arg1 = sys.argv[1]

    # 判断是PDF路径还是股票代码
    if arg1.endswith('.pdf') or '/' in arg1:
        # 单个PDF文件
        result = extract_pdf(arg1)
        print("\n=== 提取完成 ===")
        for section, path in result.items():
            print(f"  {section}: {path}")
    else:
        # 股票代码 - 批量处理
        doc_type = sys.argv[2] if len(sys.argv) > 2 else "年报"
        results = batch_extract(arg1, doc_type)

        print("\n=== 批量提取完成 ===")
        for filename, sections in results.items():
            print(f"\n{filename}:")
            if "error" in sections:
                print(f"  错误: {sections['error']}")
            else:
                for section, path in sections.items():
                    print(f"  {section}: {Path(path).name}")
