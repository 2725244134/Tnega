# 推文数据导出指南

## 🎯 快速开始

### 基础用法（方案 B：手动调用）

```python
import asyncio
from src.agent.agent import agentx, Deps
from src.agent.export import export_tweets_to_csv

async def main():
    # 1. 初始化 Deps
    deps = Deps()
    
    # 2. 使用 Agent 采集推文
    await agentx.run(
        "采集关于 '93阅兵' 的阿拉伯语推文",
        deps=deps
    )
    
    # 3. 手动导出到 CSV
    result = await export_tweets_to_csv(
        deps=deps,
        filename="my_tweets.csv",
        output_dir="output"
    )
    
    # 4. 检查结果
    if result.success:
        print(f"✓ 导出成功: {result.file_path}")
        print(f"  推文数量: {result.tweet_count}")
        print(f"  文件大小: {result.file_size_bytes} 字节")
    else:
        print(f"✗ 导出失败: {result.error_message}")

asyncio.run(main())
```

---

## 📁 CSV 文件格式

生成的 CSV 文件包含两列：

```csv
tweet_id,text
1,"第一条推文内容"
2,"第二条推文内容，包含""引号""会自动转义"
3,"第三条推文
可能包含换行符"
```

**列说明**：
- `tweet_id`: 自动生成的序号（1, 2, 3, ...）
- `text`: 推文文本内容（自动转义引号和换行符）

**特性**：
- ✅ 自动去重（set 保证唯一性）
- ✅ 排序输出（确保可复现）
- ✅ 异步 I/O（不阻塞）
- ✅ UTF-8 编码（支持多语言）

---

## 🔧 API 参考

### `export_tweets_to_csv()`

```python
async def export_tweets_to_csv(
    deps: Deps,
    filename: str = "tweets.csv",
    output_dir: str = "output",
) -> ExportResult
```

**参数**：
- `deps`: Agent 依赖容器（包含推文文本集合）
- `filename`: 文件名（默认 `tweets.csv`）
- `output_dir`: 输出目录（默认 `output/`，不存在会自动创建）

**返回**：`ExportResult` 对象，包含：
- `success`: bool - 是否成功
- `file_path`: str - 完整文件路径
- `tweet_count`: int - 导出的推文数量
- `file_size_bytes`: int - 文件大小（字节）
- `exported_at`: datetime - 导出时间（UTC）
- `error_message`: str | None - 错误信息（如果失败）

---

## 📚 进阶示例

### 示例 1：自定义文件名（带时间戳）

```python
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"tweets_{timestamp}.csv"

result = await export_tweets_to_csv(
    deps=deps,
    filename=filename,
    output_dir="output/archives"
)
```

### 示例 2：批量导出不同查询

```python
queries = [
    ("93阅兵 lang:ar", "parade_ar.csv"),
    ("China military lang:en", "military_en.csv"),
]

for query, filename in queries:
    deps = Deps()  # 每个查询独立 Deps
    
    await agentx.run(f"采集: {query}", deps=deps)
    
    if deps.fetched_count > 0:
        await export_tweets_to_csv(deps, filename)
```

### 示例 3：错误处理

```python
try:
    result = await export_tweets_to_csv(deps, "tweets.csv")
    
    if not result.success:
        print(f"导出失败: {result.error_message}")
        # 重试或记录日志
        
except Exception as e:
    print(f"致命错误: {e}")
```

### 示例 4：检查导出前状态

```python
if deps.fetched_count == 0:
    print("没有推文数据，跳过导出")
else:
    print(f"准备导出 {deps.fetched_count} 条推文...")
    result = await export_tweets_to_csv(deps, "tweets.csv")
```

---

## 🎨 设计哲学

### 分离关切（Separation of Concerns）

```
Deps (数据状态)
  ↓
export_tweets_to_csv (持久化逻辑)
  ↓
CSV 文件 (外部存储)
```

- **Deps 不知道文件操作**：单一职责，只负责数据存储
- **导出函数独立**：可以在任何地方调用，不依赖 Agent
- **异步 I/O**：符合项目规范，不阻塞事件循环

### Good Taste 原则

✅ **消除特殊情况**：
```python
# ❌ 坏：手动检查空列表
if len(deps.tweet_texts) > 0:
    for text in deps.tweet_texts:
        write(text)

# ✅ 好：for 循环自然处理空集合
for text in sorted(deps.tweet_texts):
    write(text)
```

✅ **类型安全**：
```python
# 返回结构化对象，不是裸 dict
result: ExportResult = await export_tweets_to_csv(...)
print(result.tweet_count)  # IDE