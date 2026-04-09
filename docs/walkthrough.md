# Walkthrough: Researching a Stock from Scratch

[中文](#中文版) | [English](#english)

---

<a id="english"></a>

## English

This walkthrough uses **Foxconn Industrial Internet (601138)** to show the full research workflow. The entire process happens inside Claude Code. Full output files are in [examples/601138/](examples/601138/).

### Step 1: Financial Analysis

```
/financial-analysis 601138
```

**What it does**: Downloads annual reports from CNINFO, fetches financial data via Lixinger API, reads PDF filings, and produces a structured 5-chapter report.

**The 5 chapters and what they focus on**:

| Chapter | Focus | Key design point |
|---------|-------|-----------------|
| 1. Company & Business | Positioning, revenue breakdown, business model, how the company makes money | One-sentence positioning must capture the essence |
| 2. Industry Analysis | Market landscape, competitive dynamics, industry-specific analysis framework | The "analysis framework" anchors all subsequent chapters |
| 3. Core Competitiveness | 2-3 key dimensions from Ch.2's framework, with data | Depth over breadth — only dimensions that matter |
| 4. Financial Analysis | Industry-specific KPIs, profitability, financial health | Led by industry KPIs, not generic ratios |
| 5. Risk Factors | 3-5 material risks, risk evolution, implied risks | Filter out boilerplate, surface what management doesn't say |

Plus a **"Follow-up Priorities"** section — a handoff checklist for continuous tracking.

**Example output** — one-sentence positioning from the 601138 report:

> Foxconn Industrial Internet is one of the world's largest electronic equipment contract manufacturers, with AI servers and high-speed switches as core growth engines — essentially a mega-scale precision manufacturing platform embedded in the supply chains of the world's top tech companies.

**Example output** — implied risk that management didn't disclose:

> **Severe divergence between operating cash flow and profit**: 2025 net profit was 35.3B RMB, but operating cash flow was only 5.2B (ratio: 0.15). Management explains this as "increased stocking for AI servers." But this raises a deeper question: out of 903B in revenue, inventory increased by 65.6B, receivables by 16.2B, payables by 44.1B. The net working capital absorption was ~37.7B. If AI server demand shows any slowdown in 2026, this inventory faces impairment risk.

**What it produces**:
```
stock/601138/
├── memory/
│   ├── 公司信息.json        # Structured data (financials, valuation, shareholders)
│   ├── 年报摘要.md          # Annual report key excerpts
│   └── 财报分析报告.md      # The 5-chapter report
├── cache/
└── filings/年报/            # Downloaded PDFs
```

---

### Step 2: Continuous Tracking

```
/continuous-tracking 601138
```

**What it does**: Fetches recent K-line data, valuation metrics, announcements, runs web searches. Produces a 4-chapter tracking report that focuses on *what the market thinks now*.

**The 4 chapters**:

| Chapter | Focus | Key design point |
|---------|-------|-----------------|
| 1. Price & Valuation | 6-month price action, key levels, current valuation vs. 5-year percentile | Phase-by-phase breakdown, not just numbers |
| 2. Market Information | Hot events, what the market is discussing, narrative shifts | Compare market view against company's own narrative |
| 3. Bull/Bear Debate | 2-4 key debates, each framed as a question | Forces balanced evidence; mandatory "counter-focus" in search phase to combat confirmation bias |
| 4. Catalysts | Confirmed events, potential catalysts, risk events | Actionable timeline |

**Example output** — narrative shift detected:

> Six months ago (at Q3 report), the market narrative was "re-rating from contract manufacturer to AI compute platform." After the November rumor of "Nvidia entering server manufacturing," the narrative shifted to "dependency concerns." The market is now split: sell-side maintains "buy" (12 of 15), but the stock keeps falling — buyers are voting with their feet.

**Example output** — bull/bear debate:

> **Topic: Is FII's position in the AI server value chain rising or being squeezed?**
>
> **Bull**: FII holds 45% assembly share in GB300 (per Digitimes), far ahead of Quanta at 30%. Cloud computing gross margin improved from 3.96% (2022) to 5.73% (2025), indicating growing pricing power.
>
> **Bear**: 6.98% overall gross margin is low-margin contract manufacturing by any measure. Supplier concentration rose from 48% to 58% (2023→2025) — bargaining power is weakening, not strengthening. The 92.5% direct material cost ratio leaves minimal room for self-created value.

**What it adds**:
```
stock/601138/memory/
├── 持续跟踪_20260311.md    # 4-chapter tracking report
└── 时间轴.md                # Event timeline (structured, dated)
stock/601138/cache/
└── 搜索整理_20260311.md    # Annotated search results (facts/opinions/data tagged)
```

---

### Step 3: Discussion

**This is the most important step — and there's no slash command for it.**

After reading the reports, you discuss with Claude. Ask questions, challenge assumptions, explore blind spots. For 601138, the discussion uncovered insights that no amount of data analysis could produce on its own:

- FII's Shanghai-listed entity has only 8 million RMB in fixed assets — it's a pure holding shell. The "company" investors buy is a window into Foxconn's global system, not an independent business.
- The dual foreign-exchange structure makes dividends the *least efficient* way for Foxconn to extract value. Low payout isn't just Foxconn being stingy — the structure makes dividends irrational.
- Counter-intuitively, faster AI growth *accelerates* governance risk rather than diluting it — because it increases overseas asset concentration, triggering regulatory scrutiny from both sides.

These insights came from back-and-forth dialogue, not from any single data source.

---

### Step 4: Research Notes

Discussion insights are saved to research notes — each with a date, status, core insight, reasoning chain, and conclusion:

**Example** (from 601138 research notes):

> **2026-03-11 — Corporate governance and minority shareholder position**
>
> **Status**: ✅ Verified
>
> **Core insight**: A-share investors hold a minority stake in a shell holding company with zero bargaining power.
>
> **Reasoning**:
> 1. FII (Shanghai entity) is a pure holding shell — 8M RMB fixed assets, 64B in long-term equity investments is the entire "asset."
> 2. Control chain: Foxconn (Taiwan, no actual controller) → intermediary shell (HK) → 7-8 offshore shells → FII → Samoa holding → actual factories.
> 3. Foxconn controls operations: factory management, customer relationships, supply chain. FII purchases 23.7B from Foxconn system, leases 1.1B in facilities, pays trademark fees.
> 4. 84.1% voting rights = related-party transactions pass as formality.
> 5. Profit-to-dividend funnel is extremely narrow: 35.3B net profit → 5.2B operating cash flow (OCF/NI=0.15) → 6.6B proposed dividend (18.6% payout).
>
> **Conclusion**: Structurally asymmetric — upside shared 84% by Foxconn, downside amplified for minority shareholders. Should carry significant governance discount (ref: HK spin-off 20-40%, Korean chaebol 30-50%), but the A-share market gives PE 30x / 88th percentile premium — because it's one of few direct plays on AI compute narrative.

Statuses: pending verification / ✅ verified / ❌ refuted / unknown

```
stock/601138/memory/研究笔记.md
```

---

### Step 5: Investment Insight

```
/investment-insight 601138
```

Distills research notes into a structured 5-section analysis. Only verified insights from discussion make it in — pending items are flagged separately.

**The 5 sections**:

| Section | Purpose | Key design point |
|---------|---------|-----------------|
| 1. Core Investment Logic | Company essence, profit driver, moat, key tension | First-principles, not business description |
| 2. Key Judgments | 2-3 pressure-tested conclusions with evidence chains | Each judgment undergoes devil's advocate stress-test before inclusion |
| 3. Unverified Hypotheses | High-impact assumptions not yet confirmed | Each with verification direction and impact assessment |
| 4. Valuation & Checkpoints | Current stance, valuation range, time-bound verification nodes | Specific thresholds, not vague "watch this" |
| 5. Data Sources | Tiered: Tier 1 (official) → Tier 2 (industry) → Tier 3 (reference) | Traceability |

**Example output** — valuation checkpoint:

> 1. **Late April 2026 — FII Q1 Report**: Does OCF/net profit ratio recover above 0.5? If still below 0.3, the "temporary stocking" explanation breaks down.
> 2. **April-May 2026 — Global cloud providers Q1 earnings**: Do 2026 capex guides continue rising? Any reduction signals directly impact the AI compute narrative.
> 3. **May-June 2026 — GB300 capacity peak**: Inflection from ramp to release. If post-peak revenue growth disappoints, 151B inventory faces impairment risk.
> 4. **Ongoing — Foxconn (2317.TW) stock price**: Parent-subsidiary valuation inversion narrowing? If Foxconn strengthens while FII weakens, the market is correcting narrative premium.

```
stock/601138/memory/投资洞察.md
```

---

### Key Principle

The skills gather **raw material**. But the leap from material to insight only happens through **discussion**. The system is designed to support that conversation, not replace it.

### Reference Output

Complete output files from the 601138 analysis:

| File | Description |
|------|-------------|
| [财报分析报告.md](examples/601138/财报分析报告.md) | Financial analysis report (5 chapters) |
| [持续跟踪_20260311.md](examples/601138/持续跟踪_20260311.md) | Continuous tracking report (4 chapters) |
| [研究笔记.md](examples/601138/研究笔记.md) | Research notes (discussion insights) |
| [投资洞察.md](examples/601138/投资洞察.md) | Investment insight (5 sections) |
| [时间轴.md](examples/601138/时间轴.md) | Event timeline |

---

<a id="中文版"></a>

## 中文版

以**工业富联（601138）**为例，展示完整的研究流程。所有操作在 Claude Code 中进行。完整输出文件见 [examples/601138/](examples/601138/)。

### 第一步：财报分析

```
/financial-analysis 601138
```

**做什么**：从巨潮资讯下载年报，从理杏仁获取财务数据，阅读 PDF 原文，生成 5 章结构化分析报告。

**5 章结构与关注点**：

| 章节 | 关注点 | 设计要点 |
|------|--------|---------|
| 1. 公司与业务 | 定位、收入拆解、商业模式、怎么赚钱 | 一句话定位抓住公司本质 |
| 2. 行业分析 | 市场格局、竞争态势、行业分析框架 | "分析框架"锚定后续所有章节方向 |
| 3. 核心竞争力 | 根据第2章框架展开2-3个关键维度 | 深度优先于广度 |
| 4. 财务分析 | 行业特定KPI、盈利能力、财务健康度 | 以行业KPI领衔，不是通用指标 |
| 5. 风险因素 | 3-5个实质性风险、风险变化、隐含风险 | 过滤套话，挖掘管理层没说的 |

加上**"后续跟踪重点"**——向持续跟踪的交接清单。

**示例输出** — 一句话定位：

> 工业富联是全球最大的电子设备代工制造商之一，以AI服务器和高速交换机为核心增长引擎，本质上是一家嵌入全球顶级科技客户供应链的超大规模精密制造平台。

**示例输出** — 管理层未披露的隐含风险：

> **经营现金流与利润的严重背离**：2025年净利润352.86亿元，经营性现金流仅52.38亿元（比率0.15）。管理层以"备货增加"解释。但在9,029亿元营收中，存货增加656亿元、应收增加162亿元、应付增加441亿元，差额净占用约377亿元营运资金。如果AI服务器需求在2026年出现任何放缓，这些备货将面临减值风险。

**产出文件**：
```
stock/601138/
├── memory/
│   ├── 公司信息.json        # 结构化数据（财务、估值、股东）
│   ├── 年报摘要.md          # 年报关键摘录
│   └── 财报分析报告.md      # 5章分析报告
├── cache/
└── filings/年报/            # 下载的 PDF
```

---

### 第二步：持续跟踪

```
/continuous-tracking 601138
```

**做什么**：获取近期 K 线、估值、公告，执行网络搜索。生成 4 章跟踪报告，聚焦"市场当前怎么看"。

**4 章结构**：

| 章节 | 关注点 | 设计要点 |
|------|--------|---------|
| 1. 走势与估值 | 6个月股价分阶段解读、当前估值与5年分位 | 不只是数字，要分阶段叙述 |
| 2. 市场信息 | 热点事件、市场在讨论什么、叙事变化 | 对比市场观点与公司自述 |
| 3. 多空辩论 | 2-4个焦点议题，每个以问句形式呈现 | 强制平衡；搜索阶段有"反向焦点"对抗确认偏误 |
| 4. 近期催化剂 | 确定性事件、潜在催化剂、风险事件 | 可操作的时间表 |

**示例输出** — 叙事变化：

> 6个月前（Q3报告发布时），市场叙事是"从代工厂到AI算力平台的估值重塑"。11月"英伟达下场做服务器"传闻后，叙事转向"依附性隐忧"。当前叙事处于分裂状态：卖方仍在"买入"（15家机构12家买入），但股价持续走低，买方在用脚投票。

**示例输出** — 多空辩论：

> **议题：工业富联在AI服务器价值链中的地位是在提升还是在被挤压？**
>
> **多方**：公司在GB300中占据45%组装份额（据Digitimes），远超广达30%。云计算毛利率从3.96%（2022）持续提升至5.73%（2025），说明话语权在增强。
>
> **空方**：6.98%整体毛利率是低利润率代工水平。供应商集中度从48%升至58%（2023→2025），议价能力在减弱。直接材料成本占营业成本92.5%，自身增值空间极为有限。

**新增产出**：
```
stock/601138/memory/
├── 持续跟踪_20260311.md    # 4章跟踪报告
└── 时间轴.md                # 事件时间轴（结构化、带日期）
stock/601138/cache/
└── 搜索整理_20260311.md    # 标注后的搜索结果（事实/观点/数据分类）
```

---

### 第三步：讨论

**这是最重要的一步——没有对应的命令。**

阅读报告后，和 Claude 讨论。提问、质疑假设、探索盲区。以 601138 为例，讨论揭示了数据分析本身无法产出的认知：

- FII 上海上市主体固定资产仅800万——是纯控股壳。投资者买到的不是一家独立公司，而是鸿海全球体系的一个窗口。
- 双重换汇结构让分红成为鸿海最低效的取钱方式。低派息率不只是不愿分，而是结构上分红不合理。
- 反直觉地，AI增长越快，治理风险越大——因为境外资产集中度上升，中美两边的监管审查都会加剧。

这些认知来自反复对话，不来自任何单一数据源。

---

### 第四步：研究笔记

讨论认知保存到研究笔记——每条带日期、状态、核心认知、推理链、结论：

**示例**（601138 研究笔记）：

> **2026-03-11 公司治理结构与少数股东地位**
>
> **状态**：✅ 已验证
>
> **核心认知**：A股投资者持有的是一个毫无话语权的控股壳公司少数股东权益。
>
> **推理过程**：
> 1. FII（上海上市主体）本身是纯控股壳——固定资产仅800万，无独立经营能力，640亿长期股权投资就是全部"资产"。
> 2. 控制链层层空壳：鸿海精密（台湾，无实际控制人）→ 中坚企业（香港空壳）→ 7-8个境外壳公司分散持股 → FII → 萨摩亚控股公司 → 实际工厂。
> 3. 鸿海体系掌握实际运营控制权：FII从鸿海体系采购236.6亿、租赁厂房设备11.4亿、支付商标使用费——生产要素都不在FII手中。
> 4. 84.1%投票权意味着关联交易审批走程序。
> 5. 利润→现金→分红的漏斗极窄：353亿净利润 → 52亿经营现金流 → 65.5亿拟分红（18.6%）。
>
> **结论**：上行分享有限（鸿海拿走84%好处）、下行风险放大。理应有显著治理折价，但A股给了5年88%分位溢价——因为这是少数能参与AI算力叙事的标的。

条目状态：待验证 / ✅ 已验证 / ❌ 已否定 / 仍未知

```
stock/601138/memory/研究笔记.md
```

---

### 第五步：投资洞察

```
/investment-insight 601138
```

将研究笔记提炼为 5 节结构化投资分析。只有经过讨论验证的认知才能写入——待验证项单独标注。

**5 节结构**：

| 节 | 用途 | 设计要点 |
|-----|------|---------|
| 1. 核心投资逻辑 | 公司本质、盈利驱动、护城河、关键矛盾 | 第一性原理，不是业务描述 |
| 2. 关键判断 | 2-3个经过压力测试的核心结论 | 每个判断经"魔鬼代言人"环节检验后才写入 |
| 3. 待验证假设 | 高影响但未确认的假设 | 标注验证方向和影响程度 |
| 4. 估值与验证节点 | 当前立场、估值区间、带时间的验证节点 | 具体阈值，不是模糊的"关注" |
| 5. 数据来源 | 分层：Tier 1（官方）→ Tier 2（行业）→ Tier 3（参考） | 可追溯 |

**示例输出** — 验证节点：

> 1. **2026年4月底 FII Q1报告**：经营现金流/净利润比率是否回升至0.5以上。若仍低于0.3，"暂时备货"的解释难以为继。
> 2. **2026年4-5月 全球云服务商Q1财报**：2026年capex指引是否继续上调。任何调低信号直接冲击AI算力叙事。
> 3. **2026年5-6月 GB300产能达峰**：产能从爬坡到释放的转折点。若达峰后收入增速不及预期，1,509亿存货面临减值风险。
> 4. **持续观察 鸿海（2317.TW）股价**：母子市值倒挂是否收窄。鸿海走强而FII走弱 = 市场在修正叙事溢价。

```
stock/601138/memory/投资洞察.md
```

---

### 核心原则

技能（财报分析、持续跟踪）搜集**原材料**。但从材料到认知的跃迁只发生在**讨论**中。系统的设计是支持这个对话，而不是替代它。

### 参考输出

601138 分析的完整输出文件：

| 文件 | 说明 |
|------|------|
| [财报分析报告.md](examples/601138/财报分析报告.md) | 财报分析报告（5章） |
| [持续跟踪_20260311.md](examples/601138/持续跟踪_20260311.md) | 持续跟踪报告（4章） |
| [研究笔记.md](examples/601138/研究笔记.md) | 研究笔记（讨论认知） |
| [投资洞察.md](examples/601138/投资洞察.md) | 投资洞察（5节） |
| [时间轴.md](examples/601138/时间轴.md) | 事件时间轴 |
