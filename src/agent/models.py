from pydantic import BaseModel, Field
from typing import List, Set, Optional
from datetime import datetime

class CollectorState(BaseModel):
    """Agent 运行时状态（单次运行内共享）"""
    seen_tweet_ids: Set[str] = Field(default_factory=set)
    all_tweets: list = Field(default_factory=list)  # 使用 list[Any]，避免循环依赖
    attempts: int = 0
    queries_tried: List[str] = Field(default_factory=list)
    collected_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

class CollectionResult(BaseModel):
    """采集结果摘要"""
    new_tweet_count: int
    total_tweet_count: int
    duplicate_count: int
    query: str
    attempt_number: int
    success_rate: float
    sample_texts: List[str]
    has_replies: bool = True
    has_threads: bool = True
    output_path: Optional[str] = None
    collected_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    queries_tried: Optional[List[str]] = None
