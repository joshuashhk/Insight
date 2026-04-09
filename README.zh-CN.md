# Insight

[English](README.md)

买方研究用股票分析系统。通过 Claude Code 驱动，实现财报分析、持续跟踪、投资洞察三层递进式研究。

> 这是一个正在使用中的研究系统，不是一个打磨过的产品。开源是为了展示人机协作研究可以如何组织。

## 快速开始

### 1. 环境要求

- Python 3.12+（推荐 `brew install python@3.12`）
- [Claude Code](https://claude.com/claude-code)（核心驱动，需安装并登录）
- macOS

### 2. 克隆仓库

```bash
git clone https://github.com/joshuashhk/Insight.git
cd Insight
```

### 3. 安装依赖

**Python 依赖**：

```bash
pip3 install requests python-dotenv pyyaml
```

### 4. 配置 API Key

在项目根目录创建 `.env` 文件：

```bash
echo "LIXINGER_TOKEN=你的理杏仁API密钥" > .env
```

理杏仁 API 密钥可在 [理杏仁官网](https://www.lixinger.com/) 注册后获取。

### 5. 开始使用

在项目目录下启动 Claude Code，然后使用以下命令：

```
/financial-analysis 股票代码   # 财报分析（新股票研究起点）
/continuous-tracking 股票代码  # 持续跟踪（需先完成财报分析）
/read-report                   # 读研报（提取增量信息，更新行业笔记）
/narrative-review              # 叙事审阅（批判性审阅卖方行业叙事）
/investment-insight 股票代码   # 投资洞察（研究笔记→可发布的投资分析）
```

## 项目结构

```
Insight/
├── CLAUDE.md               # Claude Code 项目指令
├── notes/                  # 开发笔记（设计决策记录）
├── sources/                # 数据源模块
│   ├── structured/         # 理杏仁API（财务+K线+估值）
│   └── unstructured/       # 巨潮资讯（公告下载）
├── skills/                 # 分析技能（各skill的SKILL.md定义完整工作流）
│   ├── financial_analysis/ # 财报分析
│   ├── continuous_tracking/# 持续跟踪
│   ├── read_report/        # 读研报
│   ├── narrative_review/   # 叙事审阅
│   ├── investment_insight/ # 投资洞察
│   ├── announcement_filter/# 公告筛选
├── stock/                  # 个股数据（不在仓库中）
│   └── {股票代码}/
│       ├── memory/         # 报告和研究笔记
│       ├── cache/          # 临时文件
│       └── filings/        # 原始PDF
├── industry/               # 行业研究笔记（不在仓库中）
└── output/                 # 输出文件（不在仓库中）
```

## 研究流程

```
财报分析 → 持续跟踪 → （读研报 → 叙事审阅）→ 讨论 → 研究笔记 → 投资洞察
```

| 环节 | 说明 |
|------|------|
| 财报分析 | 通过年报、招股书、财务数据理解公司基本面 |
| 持续跟踪 | 纳入K线、估值、公告、网络搜索等新增信息 |
| 读研报 / 叙事审阅 | 阅读卖方研报，提取增量信息，批判性审阅行业叙事 |
| 讨论 | Joshua 与 Claude 对话，形成认知共识 |
| 研究笔记 | 讨论共识的内部底稿 |
| 投资洞察 | 将讨论共识整理为结构化的投资分析 |
