import time
from datetime import datetime
from pydantic_ai import RunContext
from src.x_crawl import collect_tweet_discussions, create_client, export_texts_from_collection
from .models import CollectorState, CollectionResult

async def collect_tweets_tool(
    ctx: RunContext[CollectorState],
    query: str,
    max_tweets: int = 500,
) -> CollectionResult:
    state = ctx.deps
    state.attempts += 1
    state.queries_tried.append(query)
    if state.collected_at is None:
        state.collected_at = datetime.utcnow()
    start = time.time()
    async with create_client() as client:
        collection = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=max_tweets,
            max_replies_per_tweet=10,
            include_thread=True,
            max_concurrent=10,
        )
    all_tweets = collection.all_tweets
    new_tweets = [t for t in all_tweets if t.id not in state.seen_tweet_ids]
    duplicate_count = len(all_tweets) - len(new_tweets)
    state.seen_tweet_ids.update(t.id for t in new_tweets)
    state.all_tweets.extend(new_tweets)
    output_path = f"data/collections/agent_{state.collected_at.strftime('%Y%m%d_%H%M%S')}.csv"
    export_texts_from_collection(collection, output_path, file_format="csv")
    end = time.time()
    state.duration_seconds = (end - start)
    samples = [t.text[:100] for t in new_tweets[:5]]
    return CollectionResult(
        new_tweet_count=len(new_tweets),
        total_tweet_count=len(state.all_tweets),
        duplicate_count=duplicate_count,
        query=query,
        attempt_number=state.attempts,
        success_rate=collection.success_rate,
        sample_texts=samples,
        has_replies=collection.total_replies > 0,
        has_threads=collection.total_threads > 0,
        output_path=output_path,
        collected_at=state.collected_at,
        duration_seconds=state.duration_seconds,
        queries_tried=list(state.queries_tried),
    )
