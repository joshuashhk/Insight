# Insight

[中文](README.zh-CN.md)

A buy-side equity research system powered by Claude Code. It implements a three-layer progressive research workflow: financial analysis, continuous tracking, and investment insight.

> This is a working research system, not a polished product. It is open-sourced as a reference for how human-AI collaborative research can be structured.

## Core Idea

The most critical investment hypotheses are qualitative — they cannot be derived automatically from data. They require conversation to clarify and stress-test. Financial analysis and tracking gather raw material, but the leap from material to insight only happens through discussion. Discussion is the production step, not an afterthought.

## Quick Start

### 1. Requirements

- Python 3.12+ (`brew install python@3.12`)
- [Claude Code](https://claude.com/claude-code) (core engine, must be installed and logged in)
- macOS

### 2. Clone

```bash
git clone https://github.com/joshuashhk/Insight.git
cd Insight
```

### 3. Install Dependencies

```bash
pip3 install requests python-dotenv pyyaml
```

### 4. Configure API Key

Create a `.env` file in the project root:

```bash
echo "LIXINGER_TOKEN=your_lixinger_api_key" > .env
```

Get your API key from [Lixinger](https://www.lixinger.com/) (a Chinese financial data provider).

### 5. Usage

Launch Claude Code in the project directory and use these commands:

```
/financial-analysis <stock_code>   # Financial analysis (starting point for new stocks)
/continuous-tracking <stock_code>  # Continuous tracking (requires prior financial analysis)
/read-report                       # Read sell-side report (extract insights, update industry notes)
/narrative-review                  # Narrative review (critically examine sell-side narratives)
/investment-insight <stock_code>   # Investment insight (distill research notes into structured analysis)
```

## Project Structure

```
Insight/
├── CLAUDE.md               # Claude Code project instructions
├── notes/                  # Development notes (design decisions)
├── sources/                # Data source modules
│   ├── structured/         # Lixinger API (financials + K-line + valuation)
│   └── unstructured/       # CNINFO (announcement downloads)
├── skills/                 # Analysis skills (each SKILL.md defines the full workflow)
│   ├── financial_analysis/ # Financial statement analysis
│   ├── continuous_tracking/# Continuous tracking
│   ├── read_report/        # Sell-side report reading
│   ├── narrative_review/   # Narrative review
│   ├── investment_insight/ # Investment insight
│   ├── announcement_filter/# Announcement filtering
├── stock/                  # Per-stock data (not in repo)
│   └── {stock_code}/
│       ├── memory/         # Reports and research notes
│       ├── cache/          # Temporary files
│       └── filings/        # Raw PDFs (annual reports, prospectuses, etc.)
├── industry/               # Industry research notes (not in repo)
└── output/                 # Output files (not in repo)
```

## Research Workflow

```
Financial Analysis → Continuous Tracking → (Read Report → Narrative Review) → Discussion → Research Notes → Investment Insight
```

| Stage | Description |
|-------|-------------|
| Financial Analysis | Understand company fundamentals through annual reports, prospectuses, and financial data |
| Continuous Tracking | Incorporate K-line, valuation, announcements, and web search updates |
| Read Report / Narrative Review | Read sell-side reports, extract incremental information, critically examine industry narratives |
| Discussion | Human-AI dialogue to form cognitive consensus |
| Research Notes | Internal working draft of discussion consensus |
| Investment Insight | Distill research notes into structured investment analysis |
