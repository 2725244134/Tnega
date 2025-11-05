# API Key 配置指南

## 🎯 快速开始（3 步完成）

### 步骤 1：复制配置模板

```bash
cd Tnega
cp .env.example .env
```

### 步骤 2：编辑 `.env` 文件

使用任意编辑器打开 `.env` 文件：

```bash
# 使用 vim
vim .env

# 或使用 nano
nano .env

# 或使用 VSCode
code .env
```

### 步骤 3：填入你的 API Key

将文件中的 `your_api_key_here` 替换为真实的 API Key：

```env
# ============================================
# Twitter API 配置
# ============================================

# Twitter API Key (必填)
TWITTER_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxx

# Google API Key (必填，用于 pydantic-ai)
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxx

# 其他配置（可选，使用默认值）
# TWITTER_API_BASE_URL=https://api.twitterapi.io
# HTTP_TIMEOUT=30.0
# MAX_CONCURRENT_REQUESTS=20
```

**完成！** 保存文件后即可运行程序。

---

## 🔑 如何获取 API Key

### Twitter API Key

**来源**：[twitterapi.io](https://twitterapi.io)

**步骤**：
1. 访问 https://twitterapi.io
2. 注册账户并登录
3. 进入 Dashboard
4. 点击 "API Keys" 或 "Get API Key"
5. 复制生成的 API Key（格式：`sk_xxxxxxxxxxxx`）
6. 粘贴到 `.env` 文件的 `TWITTER_API_KEY=` 后面

**价格**：
- 免费版：200 requests/天，QPS = 0.2
- 付费版：$99/月起，20,000 requests/月，QPS = 20

**注意**：
- API Key 以 `sk_` 开头
- 不要分享你的 API Key！
- 免费版 QPS 很低，建议设置 `MAX_CONCURRENT_REQUESTS=1`

---

### Google API Key

**来源**：[Google AI Studio](https://aistudio.google.com/app/apikey) 或 [Google Cloud Console](https://console.cloud.google.com/)

**步骤**：

#### 方法 A：Google AI Studio（推荐新手）
1. 访问 https://aistudio.google.com/app/apikey
2. 登录 Google 账号
3. 点击 "Create API Key"
4. 选择或创建一个 Google Cloud 项目
5.