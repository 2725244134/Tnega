"""
============================================
推文文本提取与清洗
============================================
从 TweetDiscussionCollection 中提取所有文本并清洗
"""

from pathlib import Path

from loguru import logger

from .models import TweetDiscussionCollection


# ============================================
# 文本提取
# ============================================


def extract_all_texts(collection: TweetDiscussionCollection) -> list[str]:
    """
    从 TweetDiscussionCollection 提取所有推文文本
    
    包括：
    - 种子推文
    - 所有回复
    - 所有 Thread 推文
    
    自动去重（基于文本内容完全相同）
    
    Args:
        collection: 推文讨论采集结果
    
    Returns:
        list[str]: 去重后的推文文本列表
    
    Example:
        >>> result = await collect_tweet_discussions(...)
        >>> texts = extract_all_texts(result)
        >>> print(f"提取了 {len(texts)} 条唯一推文")
    """
    seen_texts = set()
    unique_texts = []
    
    for item in collection.items:
        # ========== 种子推文 ==========
        if item.tweet.text and item.tweet.text not in seen_texts:
            seen_texts.add(item.tweet.text)
            unique_texts.append(item.tweet.text)
        
        # ========== 回复 ==========
        for reply in item.replies:
            if reply.text and reply.text not in seen_texts:
                seen_texts.add(reply.text)
                unique_texts.append(reply.text)
        
        # ========== Thread 上下文 ==========
        for thread_tweet in item.thread_context:
            if thread_tweet.text and thread_tweet.text not in seen_texts:
                seen_texts.add(thread_tweet.text)
                unique_texts.append(thread_tweet.text)
    
    logger.info(f"提取了 {len(unique_texts)} 条唯一推文（去重前: {len(seen_texts)}）")
    return unique_texts


# ============================================
# 文本清洗
# ============================================


def clean_tweet_text(text: str, remove_urls: bool = False, remove_mentions: bool = False, remove_emojis: bool = False) -> str:
    """
    清洗单条推文文本
    
    清洗规则：
    - 去除首尾空白
    - 移除多余的换行符（保留单个换行）
    - 可选：移除 URL 链接
    - 可选：移除 @ 提及
    - 可选：移除 Emoji 表情
    
    Args:
        text: 原始推文文本
        remove_urls: 是否移除 URL 链接（如 https://t.co/xxx）
        remove_mentions: 是否移除 @ 提及（如 @username）
        remove_emojis: 是否移除 Emoji 表情
    
    Returns:
        str: 清洗后的文本
    """
    import re
    
    cleaned = text.strip()
    
    # 移除 URL 链接
    if remove_urls:
        # 匹配 http:// 或 https:// 开头的链接
        cleaned = re.sub(r'https?://\S+', '', cleaned)
    
    # 移除 @ 提及
    if remove_mentions:
        # 匹配 @username 格式（允许字母、数字、下划线）
        cleaned = re.sub(r'@\w+', '', cleaned)
    
    # 移除 Emoji 表情
    if remove_emojis:
        # Unicode Emoji 范围
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "]+",
            flags=re.UNICODE
        )
        cleaned = emoji_pattern.sub('', cleaned)
    
    # 将多个连续换行替换为单个换行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # 去除多余的空格
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # 再次去除首尾空白（清洗后可能产生新的空白）
    cleaned = cleaned.strip()
    
    return cleaned


def clean_all_texts(texts: list[str], remove_urls: bool = False, remove_mentions: bool = False, remove_emojis: bool = False) -> list[str]:
    """
    批量清洗推文文本
    
    Args:
        texts: 原始文本列表
        remove_urls: 是否移除 URL 链接
        remove_mentions: 是否移除 @ 提及
        remove_emojis: 是否移除 Emoji 表情
    
    Returns:
        list[str]: 清洗后的文本列表（过滤掉空文本）
    """
    cleaned = []
    
    for text in texts:
        cleaned_text = clean_tweet_text(text, remove_urls, remove_mentions, remove_emojis)
        
        # 过滤掉空文本或过短的文本
        if cleaned_text and len(cleaned_text) >= 3:
            cleaned.append(cleaned_text)
    
    logger.info(f"清洗完成: {len(cleaned)}/{len(texts)} 条文本保留")
    return cleaned


# ============================================
# 文本导出
# ============================================


def save_texts_to_txt(
    texts: list[str],
    output_path: Path | str,
    format_style: str = "numbered",
) -> None:
    """
    将文本保存为 TXT 文件
    
    Args:
        texts: 文本列表
        output_path: 输出文件路径
        format_style: 格式风格
            - "numbered": 带编号 [1] text...
            - "separated": 用分隔线分隔
            - "plain": 纯文本，每行一条
    
    Example:
        >>> texts = extract_all_texts(result)
        >>> save_texts_to_txt(texts, "data/93阅兵_推文.txt")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        if format_style == "numbered":
            # [1] text
            # [2] text
            for i, text in enumerate(texts, 1):
                f.write(f"[{i}] {text}\n\n")
        
        elif format_style == "separated":
            # === 推文 1 ===
            # text
            # === 推文 2 ===
            for i, text in enumerate(texts, 1):
                f.write(f"{'=' * 60}\n")
                f.write(f"推文 {i}\n")
                f.write(f"{'=' * 60}\n")
                f.write(f"{text}\n\n")
        
        else:  # plain
            # text1
            # text2
            for text in texts:
                f.write(f"{text}\n")
    
    logger.success(f"已保存 {len(texts)} 条推文到: {output_path}")


def save_texts_to_csv(
    texts: list[str],
    output_path: Path | str,
) -> None:
    """
    将文本保存为简单 CSV 文件（仅文本内容）
    
    列：序号, 推文内容, 字符数
    
    Args:
        texts: 文本列表
        output_path: 输出文件路径
    
    Example:
        >>> texts = extract_all_texts(result)
        >>> save_texts_to_csv(texts, "data/93阅兵_推文_简单版.csv")
    """
    import csv
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig for Excel
        writer = csv.writer(f)
        
        # 写入表头
        writer.writerow(["序号", "推文内容", "字符数"])
        
        # 写入数据
        for i, text in enumerate(texts, 1):
            writer.writerow([i, text, len(text)])
    
    logger.success(f"已保存 {len(texts)} 条推文到: {output_path}")


def save_collection_to_csv(
    collection: TweetDiscussionCollection,
    output_path: Path | str,
    clean_text: bool = True,
) -> None:
    """
    将 TweetDiscussionCollection 保存为完整 CSV 文件（包含元数据）
    
    列：序号, 推文内容, 来源类型, 作者名称, 发布时间, 点赞数, 转发数, 回复数, 字符数
    
    Args:
        collection: 推文讨论采集结果
        output_path: 输出文件路径
        clean_text: 是否清洗文本（移除 URL、@提及、Emoji）
    
    Example:
        >>> result = await collect_tweet_discussions(...)
        >>> save_collection_to_csv(result, "data/93阅兵_完整数据.csv")
    """
    import csv
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 准备数据行
    rows = []
    
    for item in collection.items:
        # ========== 种子推文 ==========
        text = item.tweet.text
        if clean_text:
            text = clean_tweet_text(text, remove_urls=True, remove_mentions=True, remove_emojis=True)
        
        if text and len(text) >= 3:  # 过滤空文本
            rows.append({
                "推文内容": text,
                "来源类型": "种子推文",
                "作者名称": item.tweet.author_name or "Unknown",
                "发布时间": item.tweet.created_at.strftime("%Y-%m-%d %H:%M"),
                "点赞数": item.tweet.like_count,
                "转发数": item.tweet.retweet_count,
                "回复数": item.tweet.reply_count,
                "字符数": len(text),
            })
        
        # ========== 回复 ==========
        for reply in item.replies:
            text = reply.text
            if clean_text:
                text = clean_tweet_text(text, remove_urls=True, remove_mentions=True, remove_emojis=True)
            
            if text and len(text) >= 3:
                rows.append({
                    "推文内容": text,
                    "来源类型": "回复",
                    "作者名称": reply.author_name or "Unknown",
                    "发布时间": reply.created_at.strftime("%Y-%m-%d %H:%M"),
                    "点赞数": reply.like_count,
                    "转发数": reply.retweet_count,
                    "回复数": reply.reply_count,
                    "字符数": len(text),
                })
        
        # ========== Thread 上下文 ==========
        for thread_tweet in item.thread_context:
            text = thread_tweet.text
            if clean_text:
                text = clean_tweet_text(text, remove_urls=True, remove_mentions=True, remove_emojis=True)
            
            if text and len(text) >= 3:
                rows.append({
                    "推文内容": text,
                    "来源类型": "Thread",
                    "作者名称": thread_tweet.author_name or "Unknown",
                    "发布时间": thread_tweet.created_at.strftime("%Y-%m-%d %H:%M"),
                    "点赞数": thread_tweet.like_count,
                    "转发数": thread_tweet.retweet_count,
                    "回复数": thread_tweet.reply_count,
                    "字符数": len(text),
                })
    
    # 写入 CSV
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        # 定义列顺序
        fieldnames = ["序号", "推文内容", "来源类型", "作者名称", "发布时间", "点赞数", "转发数", "回复数", "字符数"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # 写入表头
        writer.writeheader()
        
        # 写入数据（添加序号）
        for i, row in enumerate(rows, 1):
            row["序号"] = i
            writer.writerow(row)
    
    logger.success(f"已保存 {len(rows)} 条推文到: {output_path}")
    logger.info(f"  - 种子推文: {sum(1 for r in rows if r['来源类型'] == '种子推文')} 条")
    logger.info(f"  - 回复: {sum(1 for r in rows if r['来源类型'] == '回复')} 条")
    logger.info(f"  - Thread: {sum(1 for r in rows if r['来源类型'] == 'Thread')} 条")


# ============================================
# 一站式处理函数
# ============================================


def export_texts_from_collection(
    collection: TweetDiscussionCollection,
    output_path: Path | str,
    file_format: str = "txt",
    txt_style: str = "numbered",
    clean: bool = True,
    csv_mode: str = "simple",
) -> list[str]:
    """
    一站式：从 TweetDiscussionCollection 提取、清洗、导出文本
    
    Args:
        collection: 推文讨论采集结果
        output_path: 输出文件路径
        file_format: 文件格式 ("txt" 或 "csv")
        txt_style: TXT 格式风格（仅当 file_format="txt" 时有效）
            - "numbered": 带编号
            - "separated": 分隔线
            - "plain": 纯文本
        clean: 是否清洗文本（移除 URL、@提及、Emoji）
        csv_mode: CSV 导出模式（仅当 file_format="csv" 时有效）
            - "simple": 简单版（序号+内容+字符数）
            - "full": 完整版（包含来源类型、作者、时间、互动数据）
    
    Returns:
        list[str]: 提取的文本列表（供进一步处理）
    
    Example:
        >>> result = await collect_tweet_discussions(...)
        >>> 
        >>> # 导出为完整 CSV（推荐）
        >>> export_texts_from_collection(
        ...     result,
        ...     "data/93阅兵_推文.csv",
        ...     file_format="csv",
        ...     csv_mode="full"
        ... )
        >>> 
        >>> # 导出为带编号的 TXT
        >>> texts = export_texts_from_collection(
        ...     result,
        ...     "data/93阅兵_推文.txt",
        ...     file_format="txt",
        ...     txt_style="numbered"
        ... )
    """
    logger.info("=" * 60)
    logger.info("开始提取推文文本")
    logger.info("=" * 60)
    
    # 导出文件
    if file_format == "csv":
        if csv_mode == "full":
            # 完整版 CSV（包含元数据）
            save_collection_to_csv(collection, output_path, clean_text=clean)
            # 返回提取的文本列表
            texts = extract_all_texts(collection)
            if clean:
                texts = clean_all_texts(texts, remove_urls=True, remove_mentions=True, remove_emojis=True)
        else:
            # 简单版 CSV（仅文本）
            texts = extract_all_texts(collection)
            if clean:
                texts = clean_all_texts(texts, remove_urls=True, remove_mentions=True, remove_emojis=True)
            save_texts_to_csv(texts, output_path)
    else:  # txt
        texts = extract_all_texts(collection)
        if clean:
            texts = clean_all_texts(texts, remove_urls=True, remove_mentions=True, remove_emojis=True)
        save_texts_to_txt(texts, output_path, format_style=txt_style)
    
    logger.info("=" * 60)
    logger.success(f"✅ 完成！共导出 {len(texts) if 'texts' in locals() else 0} 条推文")
    logger.info("=" * 60)
    
    return texts if 'texts' in locals() else []
