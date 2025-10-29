# Tnega: AI-Powered Twitter Data Intelligence System

## 🎯 项目本质

基于 `pydantic-ai` + `tweepy` 构建的 Twitter 数据采集与智能分析系统。核心理念：**将数据采集与智能处理完全解耦**，通过类型安全的 Agent 编排实现复杂业务逻辑。

---

## 📦 架构蓝图

```
src/
├── x_crawl/     # Twitter 数据采集层（纯 I/O，无业务逻辑）
│   └── [待实现] 封装 tweepy API，提供统一的数据获取接口
└── agent/       # AI 智能处理层（纯逻辑，无 I/O）
    └── [待实现] 基于 pydantic-ai 的智能决策与数据处理
```

**设计哲学**：
- `x_crawl` 只负责**获取原始数据**，不做任何解析或决策
- `agent` 只负责**处理结构化数据**，不直接调用 API
- 两者通过 **Pydantic 模型**传递数据，确保类型安全

---

## 🔧 开发环境

- **Python 版本**: 3.14（使用最新语言特性）
- **包管理器**: `uv`（快速依赖解析）
- **核心依赖**:
  - `pydantic-ai>=1.7.0` - 类型安全的 AI agent 框架
  - `tweepy>=4.16.0` - Twitter API v2 客户端
  - `loguru` - 现代化日志框架（替代标准 logging）
  - `pytest` - 测试框架

**启动命令**:
```bash
# 安装依赖
uv sync

# 运行主程序
uv run python main.py

# 运行测试
uv run pytest
```

---

## ✅ 代码规范（强制约束）

### 1. 文件与模块组织
- **每个文件不超过 800 行**（超过则拆分模块）
- **每层目录不超过 8 个文件**（超过则创建子目录）
- **命名规则**:
  - 模块/文件: `snake_case.py`
  - 类: `PascalCase`
  - 函数/变量: `snake_case`

### 2. 类型安全（核心原则）
- **所有公开函数必须标注类型**:
  ```python
  def fetch_tweets(user_id: str, count: int) -> list[Tweet]:
      ...
  ```
- **使用 Pydantic 模型传递复杂数据**（禁止裸 dict）
- **善用 `typing` 模块的高级类型**（`TypeVar`, `Protocol`, `Literal` 等）

### 3. 异步优先
- **所有 I/O 操作必须异步**（`async/await`）
- **Twitter API 调用全部异步实现**（无同步封装）
- **批量 API 调用使用 `asyncio.gather`**
- **禁止同步阻塞**（包括文件 I/O、网络请求等）

### 4. 错误处理与日志
- **不吞异常**（除非有明确的业务理由）
- **API 调用必须处理速率限制**（Twitter API 限额）
- **使用 `loguru` 记录关键操作**:
  ```python
  from loguru import logger
  
  logger.info("开始采集用户时间线: {}", user_id)
  logger.error("API 调用失败: {}", error)
  ```
- **异常传播优于捕获**（让调用者决定如何处理）

### 5. 注释风格
- **中文注释**（面向中文开发者）
- **ASCII 风格分块**（提升可读性）:
  ```python
  # ============================================
  # 数据采集核心逻辑
  # ============================================
  
  async def crawl_timeline(user: str) -> Timeline:
      """
      获取指定用户的时间线数据
      
      Args:
          user: Twitter 用户名（@handle）
      
      Returns:
          结构化的时间线对象
      """
      ...
  ```

---

## 🚫 需避免的「坏味道」

1. **僵化**: 修改 `x_crawl` 不应影响 `agent`，反之亦然
2. **冗余**: 禁止在多处重复 API 调用逻辑（封装成函数）
3. **循环依赖**: `x_crawl` 和 `agent` 绝不能相互导入
4. **数据泥团**: 超过 3 个参数总是一起出现时，封装成 Pydantic 模型
5. **过度抽象**: 优先写简单直接的实现，确认重复后再抽象

---

## 🔐 敏感信息管理

- **所有 API 密钥存放在 `.env`**（已配置 `.gitignore`）
- **禁止在代码中硬编码凭证**
- **使用 `python-dotenv` 或 `pydantic-settings` 加载环境变量**

---

## 🎨 Good Taste 原则（核心美学）

遵循 Linus Torvalds 的代码哲学：

### 消除特殊情况
❌ **坏**:
```python
if tweets:
    for tweet in tweets:
        process(tweet)
else:
    return None
```

✅ **好**:
```python
for tweet in tweets:  # 空列表自然跳过循环
    process(tweet)
```

### 缩进不超过 3 层
❌ **坏**:
```python
async def process():
    if condition1:
        if condition2:
            for item in items:
                if item.valid:
                    # 第 4 层！
```

✅ **好**:
```python
async def process():
    if not condition1 or not condition2:
        return
    
    valid_items = [i for i in items if i.valid]
    for item in valid_items:
        # 仅 2 层缩进
```

### 函数短小精悍
- **单一职责**：一个函数只做一件事
- **20 行警戒线**：超过 20 行立即审视是否可拆分
- **命名即文档**：函数名应清晰表达意图

---

## 🔄 待演进部分（随项目更新）

> ⚠️ 以下章节需在实现代码后补充具体示例

- [ ] **数据模型示例**：补充 `Tweet`, `User`, `Timeline` 等 Pydantic 模型定义
- [ ] **Agent 编排模式**：记录典型的 `pydantic-ai` Agent 使用范式
- [ ] **API 限流策略**：文档化 Twitter API 速率限制的应对方案
- [ ] **测试覆盖规范**：补充 pytest 测试文件组织结构和 Mock 外部 API 的方法

---

## 💡 关键决策记录

| 决策 | 理由 | 影响 |
|------|------|------|
| 使用 Python 3.14 | 获取最新类型系统改进（如 PEP 695 泛型语法） | 需确保运行环境支持 |
| 分离 `x_crawl` 和 `agent` | 解耦数据获取与业务逻辑，便于测试和替换数据源 | 增加一层抽象，但提高可维护性 |
| 强制类型标注 | 利用 Pydantic 和静态分析工具提前发现错误 | 初期编码稍慢，长期收益巨大 |

---

## 📚 参考资料

- [Pydantic AI 官方文档](https://ai.pydantic.dev/)
- [Tweepy Documentation](https://docs.tweepy.org/)
- [Twitter API v2 Reference](https://developer.twitter.com/en/docs/twitter-api)
