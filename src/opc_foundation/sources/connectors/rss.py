"""RSS connector via feedparser – hardened for robustness."""
from __future__ import annotations

import time
from typing import Any

import feedparser
import httpx

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ...web.url_validator import validate_url, URLValidationError
from ..source_schema import FetchResult, SourceDefinition, SourceQuery


class RssConnector:
    """Fetch entries from an RSS/Atom feed."""

    connector_id = "rss"

    def __init__(self, timeout: int = 15, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        """从 RSS/Atom feed 拉取条目并转为 RawSignal。

        小白解读：这个函数先下载 RSS 源（一个 XML 格式的文件），然后用
        feedparser 解析出每条文章的标题、摘要、链接，最后转成统一的
        RawSignal 格式返回。下载失败会自动重试（最多 max_retries 次）。

        参数:
            query: 查询参数，包含 url 或 metadata.feed_url
            source: 数据源定义，包含 source_id、source_name 等
            context: 运行上下文

        返回:
            FetchResult: 包含 raw_signals 列表、errors、warnings
        """
        errors: list[str] = []
        warnings: list[str] = []
        raw_signals: list[RawSignal] = []
        now = utcnow_iso()

        feed_url = (
            query.url
            or source.base_url
            or query.metadata.get("feed_url")
        )
        if not feed_url:
            warnings.append("RSS connector: no feed_url provided – returning empty result")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                warnings=warnings,
                fetched_at=now,
            )

        # 校验 feed URL 安全性（SSRF 防护）
        try:
            validate_url(feed_url)
        except URLValidationError as exc:
            errors.append(f"RSS feed URL validation failed: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
            )

        # 下载 feed 内容，带 retry（仅对网络错误和 429/5xx 重试）
        feed_content: bytes | None = None
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                    resp = client.get(feed_url)
                    resp.raise_for_status()
                    feed_content = resp.content
                break  # 下载成功，跳出重试循环
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # 429 (Too Many Requests) 和 5xx (Server Error) 值得重试
                if status == 429 or status >= 500:
                    last_exc = exc
                    if attempt < self._max_retries:
                        time.sleep(1.5 ** attempt)  # 指数退避
                        continue
                # 4xx (非 429) 不重试，直接报错
                errors.append(f"RSS fetch HTTP error {status}: {feed_url}")
                return FetchResult(
                    source_id=source.source_id,
                    connector=self.connector_id,
                    errors=errors,
                    warnings=warnings,
                    fetched_at=now,
                )
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(1.5 ** attempt)  # 指数退避
                    continue
                # 重试耗尽，报错返回
                errors.append(f"RSS fetch error after {self._max_retries + 1} attempts: {exc}")
                return FetchResult(
                    source_id=source.source_id,
                    connector=self.connector_id,
                    errors=errors,
                    warnings=warnings,
                    fetched_at=now,
                )

        if feed_content is None:
            # 理论上不会走到这里，但防御性编程
            errors.append(f"RSS fetch failed: {last_exc or 'unknown error'}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
            )

        try:
            parsed = feedparser.parse(feed_content)
            if parsed.get("bozo"):
                bozo_exc = parsed.get("bozo_exception")
                if bozo_exc:
                    warnings.append(f"RSS bozo warning: {bozo_exc}")
            if not parsed.get("entries"):
                if parsed.get("bozo"):
                    errors.append(f"RSS feed parse failed (no entries): {feed_url}")
                # Empty feed is not a failure
        except Exception as exc:
            errors.append(f"RSS parse error: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
            )

        feed_title: str = parsed.get("feed", {}).get("title") or source.source_name or ""
        entries = list(parsed.get("entries", []))[: query.max_items]

        for entry in entries:
            title = entry.get("title") or ""
            # Fallback chain: summary -> description -> title
            summary = (
                entry.get("summary")
                or entry.get("description")
                or title
            )
            link = entry.get("link") or ""
            published = entry.get("published") or entry.get("updated") or ""
            text = f"{title}\n\n{summary}".strip() if summary else (title or link)

            # source_note acts as fallback when link is missing
            source_note = feed_url if not link else None

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=feed_title or source.source_name,
                source_url=link or None,
                source_note=source_note,
                title=title or None,
                raw_text=text,
                published_at=published or None,
                fetched_at=now,
                collection_query=query.query,
                collector=self.connector_id,
                url_hash=hash_url(link) if link else None,
                content_hash=hash_text(text),
                metadata={"feed_url": feed_url},
            )
            raw_signals.append(sig)

        return FetchResult(
            source_id=source.source_id,
            connector=self.connector_id,
            raw_signals=raw_signals,
            errors=errors,
            warnings=warnings,
            fetched_at=now,
        )