# 数据模型使用指南

## 📦 模型概览

本项目基于 Twitter API v2 的响应结构，使用 Pydantic 定义了完整的类型安全数据模型。

### 核心实体

```python
from src.x_crawl import User, Tweet, Media
```

- **`User`**: Twitter 用户对象（包含粉丝数、认证状态等）
- **`Tweet`**: 推文对象（文本、互动数据、元信息）
- **`Media`**: 媒体附件（图片、视频、GIF）

### 业务容器

```python
from src.x_crawl import Timeline, SearchResults, UserProfile
```

- **`Timeline`**: 时间线容器（推文列表 + 用户映射 + 分页信息）
- **`SearchResults`**: 搜索结果容器（支持分页令牌）
- **`UserProfile`**: 用户档案（用户信息 + 最近推文）

---

## ✅ 使用示例

### 1. 创建用户对象

```python
from datetime import datetime, timezone
from src.x_crawl import User

user = User(
    id="12",
    username="jack",
    name="Jack Dorsey",
    verified=True,
    followers_count=6_000_000,
    created_at=datetime(2006, 3, 21, tzinfo=timezone.utc),
)

print(user.username)  # "jack"
print(user.followers_count)  # 6000000
```

### 2. 创建推文对象

```python
from src.x_crawl import Tweet

tweet = Tweet(
    id="20",
    text="just setting up my twttr",
    author_id="12",
    created_at=datetime(2006, 3, 21, 20, 50, 14, tzinfo=timezone.utc),
    like_count=250_000,
    retweet_count=150_000,
    lang="en",
)
```

### 3. 构建时间线

```python
from src.x_crawl import Timeline, Tweet, User

# 创建推文列表
tweets = [
    Tweet(id="100", text="Hello World", author_id="1", created_at=datetime.now(timezone.utc)),
    Tweet(id="101", text="Second tweet", author_id="1", created_at=datetime.now(timezone.utc)),
]

# 创建用户映射
users = {
    "1": User(id="1", username="alice", name="Alice"),
}

# 构建时间线
timeline = Timeline(
    tweets=tweets,
    users=users,
    newest_id="101",
    oldest_id="100",
    result_count=2,
)

# 访问数据
for tweet in timeline.tweets:
    author = timeline.users[tweet.author_id]
    print(f"@{author.username}: {tweet.text}")
```

### 4. JSON 序列化

```python
# 导出为 dict
data = tweet.model_dump()
# {'id': '20', 'text': 'just setting up my twttr', ...}

# 导出为 JSON 字符串
json_str = tweet.model_dump_json(indent=2)

# 从 dict 解析
tweet = Tweet(**data)

# 从 JSON 解析
tweet = Tweet.model_validate_json(json_str)
```

---

## 🎨 设计原则（Good Taste）

### 1. 消除特殊情况

所有 `Optional` 字段都有默认值 `None`，避免强制传参：

```python
# ❌ 坏：必须传所有可选字段
user = User(id="1", username="a", name="A", verified=None, followers_count=None, ...)

# ✅ 好：只传必需字段
user = User(id="1", username="a", name="A")
```

### 2. 类型安全

所有字段都有明确的类型标注，Mypy/Pylance 可以静态检查：

```python
tweet.like_count: Optional[int]  # 类型检查器知道这可能是 None
timeline.tweets: list[Tweet]     # 不是 list[dict]！
```

### 3. 字段验证

使用 Pydantic 的 `Field` 约束确保数据有效性：

```python
username: str = Field(min_length=1, max_length=15)  # 长度限制
followers_count: Optional[int] = Field(ge=0)       # 非负数
```

---

## 🧪 运行测试

```bash
# 运行所有测试
uv run pytest tests/test_models.py -v

# 快速验证（直接执行）
uv run python tests/test_models.py
```

---

## 📊 模型统计

- **核心实体**: 3 个（User, Tweet, Media）
- **业务容器**: 4 个（Timeline, SearchResults, UserProfile, TweetWithIncludes）
- **总字段数**: 40+ 个（全部带类型标注和文档）
- **代码行数**: 412 行（包含详细注释）
- **测试覆盖**: 6 个测试用例

---

## 📚 API 参考

完整的字段说明请参考：
- Twitter API v2 文档: https://developer.twitter.com/en/docs/twitter-api
- 项目源码: `src/x_crawl/models.py`
