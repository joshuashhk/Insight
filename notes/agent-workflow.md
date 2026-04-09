# Agent 工作流笔记

## 2026-02-12：DeepWiki MCP + "撕出"模式

来源：[Karpathy tweet](https://x.com/karpathy/status/2021633574089416993) (2026.2.11)

### 核心工作流

Karpathy 用 **DeepWiki MCP + GitHub CLI** 让 Claude 从 torchao 库中提取 fp8 训练实现，得到150行自包含代码，删掉了 torchao 依赖，且运行速度还快3%。

步骤：
1. 让 Agent 通过 DeepWiki MCP 阅读目标库的代码
2. 理解特定功能的实现细节（包括文档中未记载的 tricks）
3. 提取并重写为自包含的最小实现
4. 用测试验证等价性

### "Bacterial Code" 理念

Karpathy 倡导写"细菌代码"：自包含、无依赖、无状态、容易从 repo 中提取。核心观点：**不要下载巨型库再依赖它，让 Agent 读源码后撕出你需要的部分**。

> "Libraries are over, LLMs are the new compiler"

### 实用工具

- **DeepWiki**：把任意 GitHub URL 中的 `github.com` 换成 `deepwiki.com`，即可对该 repo 做 Q&A。直接问代码比查库文档更准确（代码是 source of truth，文档常过时）
- **DeepWiki MCP**：让 Agent（而非人）通过 MCP 访问 DeepWiki，实现自主研究+代码生成的闭环

### 对 Insight 项目的适用性

**直接适用**：
- 遇到外部库问题时，用 DeepWiki 直接问代码而非查文档
- 如果某个依赖只用了小部分功能，可以用"撕出"模式减少依赖

**间接启发**：
- MCP 作为 Agent 工具链的思路——不是人去读信息，而是 Agent 通过 MCP 访问信息源后自主行动
- 我们 skill 工作流中的搜索→整理→分析链条，本质上也是类似的 Agent + 外部信息源模式
