# Repository Guidelines

## Project Structure & Module Organization
- Core logic stays in `src/x_crawl/`: `models.py` defines the Pydantic tweet/user/media types, `crawler.py` wraps tweepy’s `AsyncClient`, and `storage.py` outputs JSON or JSONL under `data/`.
- Operational scripts live in `scripts/`—start with `scripts/crawl_china_parade_93.py` for the 93阅兵 topic pipeline—while demos and datasets belong in `examples/` and `data/`.
- Async integration tests and storage checks live in `tests/`; consult `docs/` for API walkthroughs, field definitions, and workflow notes before changing public behavior.

## Build, Test, and Development Commands
- Bootstrap the environment with `uv sync`; it resolves dependencies into the project’s managed virtualenv.
- Run topic crawls through `uv run python scripts/crawl_china_parade_93.py` after exporting `BEARER_TOKEN` (case-insensitive lookup in `.env`).
- Execute automated checks via `uv run pytest`; for faster iteration, scope to a file such as `uv run pytest tests/test_storage.py -q`.

## Coding Style & Naming Conventions
- Follow the existing async-first design: prefer `async def` entry points and await tweepy calls directly.
- Maintain 4-space indentation, type annotations, and snake_case identifiers; reserve PascalCase for Pydantic models and capitalized containers.
- Preserve the logging voice that combines Loguru with concise emoji-prefixed messages (e.g., `logger.info("🚀 TwitterCrawler 初始化完成")`).

## Testing Guidelines
- Tests rely on live X/Twitter APIs; populate `.env` with a valid bearer token before running anything under `tests/` to avoid rate-limit failures.
- Use JSON fixtures sparingly; for offline scenarios, mock `AsyncClient` responses rather than recording real payloads.
- Validate storage tweaks with the existing `save_tweets_json` / `load_tweets_json` helpers before shipping.

## Commit & Pull Request Guidelines
- Write short, imperative commit messages that explain intent (e.g., `Add rate-limit backoff`); keep a consistent language per branch—Chinese or English both appear in history, but avoid mixing within the same thread.
- Reference related issues or task IDs in the body, summarize API-impacting changes, and note credentials or environment prerequisites when relevant.
- Pull requests should include a concise description, screenshots or log excerpts for crawler output when behavior changes, and a summary of which tests were executed.

## Security & Configuration Tips
- Never commit `.env`, access tokens, or raw tweet dumps that include private metadata; store long-term archives in encrypted buckets if needed.
- Refresh bearer tokens periodically and document rotations in PR notes; override `DEFAULT_DATA_DIR` through environment variables instead of hard-coding paths.
- Sanitise shared JSONL samples before publishing by removing user PII and trimming fields not required for analysis.
