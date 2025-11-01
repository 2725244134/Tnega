以下是三个API文档的Markdown格式版本：[1][2][3]

***

## 1. Advanced Search API

### Endpoint
```
GET https://api.twitterapi.io/twitter/tweet/advanced_search
```

### Authorization
需要在请求头中包含API密钥：
```
x-api-key: YOUR_API_KEY
```

### Query Parameters

| 参数 | 类型 | 必需 | 描述 | 示例 |
|------|------|------|------|------|
| `query` | string | ✓ | 搜索查询语句 | `"AI" OR "Twitter" from:elonmusk since:2021-12-31_23:59:59_UTC` |
| `queryType` | string | ✓ | 查询类型 | `Latest` 或 `Top` |
| `cursor` | string | ✗ | 分页游标，首页使用空字符串 `""` | `"DAABCgABGkKFmLYAAAgAAgAAAAIAAA"` |

**queryType 可选值：**
- `Latest` - 最新推文
- `Top` - 热门推文

**高级搜索语法示例：**
更多示例参考：https://github.com/igorbrigadir/twitter-advanced-search

### Response

```json
{
  "tweets": [],
  "has_next_page": true,
  "next_cursor": "string",
  "status": "success",
  "msg": "string"
}
```

**响应字段说明：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `tweets` | array | 推文数组 |
| `has_next_page` | boolean | 是否有下一页 |
| `next_cursor` | string | 下一页游标 |
| `status` | string | 请求状态：`success` 或 `error` |
| `msg` | string | 请求消息（错误时返回错误信息）|

### Python 示例

```python
import requests

url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
headers = {"x-api-key": "YOUR_API_KEY"}

params = {
    "query": "(China parade OR 93阅兵) lang:ar",
    "queryType": "Latest",
    "cursor": ""
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

print(f"找到 {len(data['tweets'])} 条推文")
```

***

## 2. Get Tweet Replies API

### Endpoint
```
GET https://api.twitterapi.io/twitter/tweet/reply
```

### Authorization
需要在请求头中包含API密钥：
```
x-api-key: YOUR_API_KEY
```

### Query Parameters

| 参数 | 类型 | 必需 | 描述 | 示例 |
|------|------|------|------|------|
| `tweetId` | string | ✓ | 推文ID。**必须是原始推文（不能是回复），且应该是线程中的第一条推文** | `1846987139428634858` |
| `sinceTimestamp` | integer | ✗ | 获取此时间戳（Unix秒）之后的回复 | `1672531200` |
| `untilTimestamp` | integer | ✗ | 获取此时间戳（Unix秒）之前的回复 | `1704067200` |
| `cursor` | string | ✗ | 分页游标，首页使用空字符串 `""` | `"DAABCgABGkKFmLYAAAgAAgAAAAIAAA"` |

### Response

```json
{
  "tweets": [],
  "has_more": true,
  "next_cursor": "string",
  "status": "success",
  "msg": "string"
}
```

**响应字段说明：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `tweets` | array | 回复推文数组 |
| `has_more` | boolean | 是否有更多结果。**注意：由于Twitter API不一致性，即使没有更多数据，此字段也可能返回true。后续请求将返回空结果。** |
| `next_cursor` | string | 获取下一页结果的游标 |
| `status` | string | 请求状态：`success` 或 `error` |
| `msg` | string | 请求消息（错误时返回错误信息）|

### Python 示例

```python
import requests

url = "https://api.twitterapi.io/twitter/tweet/reply"
headers = {"x-api-key": "YOUR_API_KEY"}

def get_all_replies(tweet_id):
    all_replies = []
    cursor = ""

    while True:
        params = {
            "tweetId": tweet_id,
            "cursor": cursor
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data["status"] == "success":
            tweets = data.get("tweets", [])
            all_replies.extend(tweets)

            # 检查是否有更多数据
            if not data.get("has_more") or not tweets:
                break

            cursor = data.get("next_cursor", "")
        else:
            print(f"Error: {data['msg']}")
            break

    return all_replies

replies = get_all_replies("1846987139428634858")
print(f"共获取 {len(replies)} 条回复")
```

***

## 3. Get Tweet Thread Context API

### Endpoint
```
GET https://api.twitterapi.io/twitter/tweet/thread_context
```

### Authorization
需要在请求头中包含API密钥：
```
x-api-key: YOUR_API_KEY
```

### Query Parameters

| 参数 | 类型 | 必需 | 描述 | 示例 |
|------|------|------|------|------|
| `tweetId` | string | ✓ | 推文ID。**可以是回复推文或原始推文** | `1846987139428634858` |
| `cursor` | string | ✗ | 分页游标，首页使用空字符串 `""` | `"DAABCgABGkKFmLYAAAgAAgAAAAIAAA"` |

### Response

```json
{
  "tweets": [],
  "has_more": true,
  "next_cursor": "string",
  "status": "success",
  "msg": "string"
}
```

**响应字段说明：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `tweets` | array | 线程推文数组（包含整个对话链） |
| `has_more` | boolean | 是否有更多结果。**注意：由于Twitter API不一致性，即使没有更多数据，此字段也可能返回true。后续请求将返回空结果。** |
| `next_cursor` | string | 获取下一页结果的游标 |
| `status` | string | 请求状态：`success` 或 `error` |
| `msg` | string | 请求消息（错误时返回错误信息）|


这三个API配合使用可以完整地收集Twitter上的讨论数据。[2][3][1]

[1](https://docs.twitterapi.io/api-reference/endpoint/tweet_advanced_search)
[2](https://docs.twitterapi.io/api-reference/endpoint/get_tweet_reply)
[3](https://docs.twitterapi.io/api-reference/endpoint/get_tweet_thread_context)
[4](https://docs.twitterapi.io/api-referen)
