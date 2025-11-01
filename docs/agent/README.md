# Agent 文档索引

> **Tnega Agent 层完整文档** - 让 AI 自动优化 Twitter 搜索，采集大量相关推文

---

## 📚 文档导航

### 🎯 [Agent 架构设计](./AGENT_DESIGN.md) ⭐ **核心文档**

**适合**：想要全面了解 Agent 工作原理的开发者

**内容**：
- 核心理念：为什么需要 Agent？
- 架构设计：组件、工作流程、数据流
- 终止条件：何时停止迭代
- 去重策略：如何处理重复推文
- 技术实现：pydantic-ai 配置、状态管理
- 成功指标：如何评价 Agent 性能

**阅读时间**：15 分钟

---

### 🔧 [Tool 接口文档](./TOOL_REFERENCE.md)

**适合**：需要理解 Agent 如何与 x_crawl 交互的开发者

**内容**：
- `collect_tweets` 工具的完整定义
- 输入参数说明（query、max_tweets）
- 返回数据结构（CollectionResult）
- 内部实现逻辑
- 错误处理和性能考虑
- 单元测试示例

**阅读时间**：10 分钟

---

### 💬 [System Prompt 设计](./SYSTEM_PROMPT.md)

**适合**：想要优化 Agent 能力或理解其决策逻辑的开发者

**内容**：
- 完整的 System Prompt 文本
- Twitter 高级搜索语法详解
- 迭代优化策略（推文少/重复多/不相关时怎么办）
- 终止条件和判断逻辑
- 最佳实践和工作流程示例
- Prompt 设计原则和优化技巧

**阅读时间**：20 分钟

---

### 📖 [使用示例与最佳实践](./USAGE_EXAMPLES.md) ⭐ **新手入门**

**适合**：想要快速上手使用 Agent 的用户和开发者

**内容**：
- 快速开始（5 分钟入门）
- 基础示例（基本搜索、时间范围、目标数量）
- 高级配置（自定义参数、指定模型）
- 典型场景（舆情分析、对比研究、批量采集）
- 常见问题（速度慢、推文不相关、重复率高）
- 最佳实践（清晰描述需求、合理设置目标）

**阅读时间**：15 分钟

---

## 🚀 快速开始（3 分钟）

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置 API Key

在 `.env` 中配置：
```bash
TWITTER_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_key_here  # Gemini API
```

### 3. 运行第一个示例

```python
from src.agent import TweetCollectorAgent

agent = TweetCollectorAgent()
result = await agent.run("找阿拉伯地区对中国 93 阅兵的讨论")

print(f"找到 {result.total_tweets} 条推文")
print(f"保存路径: {result.output_path}")
```

**完整示例**: 见 [使用示例](./USAGE_EXAMPLES.md#快速开始)

---

## 📖 推荐阅读路径

### 路径 1: 快速上手（用户视角）

```
1. 使用示例 - 快速开始           (5 min)
2. 使用示例 - 基础示例           (10 min)
3. 使用示例 - 常见问题           (5 min)
```

**总耗时**: 20 分钟  
**适合**: 想要快速使用 Agent 的用户

---

### 路径 2: 深入理解（开发者视角）

```
1. Agent 架构设计               (15 min)
2. Tool 接口文档                (10 min)
3. System Prompt 设计           (20 min)
4. 使用示例 - 典型场景           (10 min)
```

**总耗时**: 55 分钟  
**适合**: 需要修改或扩展 Agent 的开发者

---

### 路径 3: Prompt 优化（AI 工程师视角）

```
1. Agent 架构设计 - 核心理念     (5 min)
2. System Prompt 设计 - 完整版   (15 min)
3. System Prompt - 优化策略      (10 min)
4. 使用示例 - 调试和测试         (5 min)
```

**总耗时**: 35 分钟  
**适合**: 想要优化 Agent 决策能力的 AI 工程师

---

## 🎯 核心概念速查

### Agent 的目标

让 AI 自动优化 Twitter 搜索 query，找到**尽可能多**的**相关**推文。

### 工作方式

```
用户输入自然语言
  ↓
Agent 设计初始 query
  ↓
调用 collect_tweets 工具
  ↓
看到结果（推文数、示例文本）
  ↓
判断：是否需要优化？
  ├─ 是 → 调整 query → 再次调用工具
  └─ 否 → 返回结果
```

### 终止条件

1. 达到目标数量（默认 2000 条）
2. 连续 3 次新增 < 10 条
3. 尝试超过 10 次（报错）

### 核心优势

- ✅ **自动化**：无需手动调整 query
- ✅ **智能化**：根据结果自适应优化
- ✅ **去重**：自动处理重复推文
- ✅ **容错**：部分失败不影响整体

---

## 🔗 相关文档

### 项目整体文档

- [项目 README](../../README.md)
- [开发规范](../../AGENTS.md)
- [x_crawl API 文档](../x_crawl_api.md)
- [实现总结](../IMPLEMENTATION_SUMMARY.md)

### 外部资源

- [Twitter 高级搜索语法](https://github.com/igorbrigadir/twitter-advanced-search)
- [pydantic-ai 官方文档](https://ai.pydantic.dev/)
- [Gemini API 文档](https://ai.google.dev/docs)

---

## 📊 文档统计

| 文档 | 行数 | 字数 | 阅读时间 |
|------|-----|------|----------|
| Agent 架构设计 | 450+ | 8000+ | 15 min |
| Tool 接口文档 | 400+ | 7000+ | 10 min |
| System Prompt 设计 | 550+ | 10000+ | 20 min |
| 使用示例 | 500+ | 8500+ | 15 min |
| **总计** | **1900+** | **33500+** | **60 min** |

---

## ❓ 还有疑问？

### 常见问题

**Q: Agent 采集速度慢怎么办？**  
A: 见 [使用示例 - 常见问题 Q2](./USAGE_EXAMPLES.md#q2-采集速度慢)

**Q: 如何提高推文相关性？**  
A: 见 [使用示例 - 最佳实践](./USAGE_EXAMPLES.md#最佳实践)

**Q: Agent 的决策逻辑是什么？**  
A: 见 [System Prompt - 优化策略](./SYSTEM_PROMPT.md#优化策略)

**Q: 如何自定义 Agent 行为？**  
A: 见 [使用示例 - 高级配置](./USAGE_EXAMPLES.md#高级配置)

---

## 🚧 项目状态

- **当前阶段**: 设计完成 ✅
- **下一步**: 实现代码
- **预计完成**: 2025-11-02

---

## 📝 更新日志

### 2025-11-01
- ✅ 完成 Agent 架构设计文档
- ✅ 完成 Tool 接口文档
- ✅ 完成 System Prompt 设计
- ✅ 完成使用示例文档
- ✅ 创建文档索引

### 待办事项
- [ ] 实现 Agent 核心代码
- [ ] 实现 Tool 函数
- [ ] 编写单元测试
- [ ] 端到端测试
- [ ] 性能优化

---

**最后更新**: 2025-11-01  
**维护者**: Tnega Team  
**反馈**: 如有问题或建议，请提交 Issue
