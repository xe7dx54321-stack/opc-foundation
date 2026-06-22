"""把前面各模块串起来的主逻辑。

功能说明（小白解读）：
    WeChatArchiver 接受一个配置，按以下步骤处理每篇文章：
    1. 读取 feed + 手工 URL（可选），生成候选列表
    2. 用 WeChatSeenStore 去重，跳过已处理成功的文章
    3. 抓取每篇新文章的 HTML
    4. 提取正文（extractor）、清洗（cleaner）
    5. 图片下载（images.py）
    6. 写本地文件（storage.py）
    7. 更新 seen_articles.sqlite / articles.jsonl / run_log.jsonl / failed_queue.jsonl

    可以通过 injectors（http_html_by_url 等）实现对外部 HTTP 的模拟，方便测试。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .cleaner import clean_wechat_content
from .dedupe import WeChatSeenStore, article_id_for
from .extractor import extract_main_content
from .fetcher import fetch_article_html
from .images import download_article_images, download_cover_image
from .manual_url import build_manual_candidate, load_manual_url_candidates
from .markdown import build_article_markdown, rewrite_html_image_urls, rewrite_markdown_image_urls
from .models import (
    AccountRunStats,
    ArchivedArticle,
    ArticleCandidate,
    FailedArticle,
    WeChatArchiveConfig,
    WeChatArchiveRunResult,
)
from .feed_client import fetch_feed_candidates
from .reports import build_daily_capture_report
from .storage import (
    append_jsonl,
    article_directory,
    write_html,
    write_markdown,
    write_metadata,
)
from ..run.time_utils import utcnow_iso


# ---------------------------------------------------------------------------
# 类型别名（方便测试注入）
# ---------------------------------------------------------------------------

HttpHtmlInjector = Callable[[str], str | bytes | None]
# 签名：接受 url，返回预先准备好的 HTML（字符串或 bytes）。返回 None 表示走真实 HTTP。


@dataclass
class ArchiveInjectors:
    """测试用的注入点。生产环境一般全是 None。"""

    http_html: HttpHtmlInjector | None = None
    now_str: Callable[[], str] | None = None
    extra_accounts: list[Any] = field(default_factory=list)  # 额外账号（测试 fixture 注入）


class WeChatArchiver:
    """微信公众号文章归档主流程。"""

    def __init__(
        self,
        config: WeChatArchiveConfig,
        injectors: ArchiveInjectors | None = None,
    ) -> None:
        self.config = config
        self.injectors = injectors or ArchiveInjectors()
        self.root = Path(config.archive_root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _now(self) -> str:
        if self.injectors.now_str:
            return self.injectors.now_str()
        return utcnow_iso()

    def _state_dir(self) -> Path:
        p = self.root / "state"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _index_path(self) -> Path:
        p = self.root / "index"
        p.mkdir(parents=True, exist_ok=True)
        return p / "articles.jsonl"

    def _reports_dir(self) -> Path:
        p = self.root / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _collect_candidates(
        self,
    ) -> tuple[list[ArticleCandidate], list[str]]:
        """收集 feed 与手工 URL 候选，返回 (candidates, warnings)。"""

        candidates: list[ArticleCandidate] = []
        warnings: list[str] = []

        # 1) 每个账号读 feed
        for account in self.config.accounts:
            max_articles = account.max_articles or self.config.defaults.max_articles_per_account or 20
            try:
                feed_result = fetch_feed_candidates(account, max_articles=max_articles)
            except Exception as exc:
                warnings.append(f"账号 [{account.account_name}] feed 解析异常: {exc}")
                continue

            warnings.extend(feed_result.warnings)
            candidates.extend(feed_result.candidates)

        # 2) 手工 URL 文件（如果配置了）
        manual_file = self.config.defaults.manual_urls_file
        if manual_file:
            try:
                path = Path(manual_file)
                if not path.is_absolute():
                    path = self.root / path
                manual_candidates = load_manual_url_candidates(path)
                candidates.extend(manual_candidates)
            except Exception as exc:
                warnings.append(f"手工 URL 文件读取失败: {exc}")

        # 去重（同一 canonical URL 只留第一次出现的）
        seen_canonical: set[str] = set()
        unique_candidates: list[ArticleCandidate] = []
        for cand in candidates:
            if cand.canonical_url in seen_canonical:
                continue
            seen_canonical.add(cand.canonical_url)
            unique_candidates.append(cand)

        return unique_candidates, warnings

    # ------------------------------------------------------------------
    # 单篇文章处理
    # ------------------------------------------------------------------

    def _archive_one(
        self,
        candidate: ArticleCandidate,
        seen_store: WeChatSeenStore,
        article_dir: Path,
        run_started_at: str,
    ) -> ArchivedArticle:
        """处理一篇候选文章，返回处理后的 ArchivedArticle。"""

        article_id = article_id_for(candidate)
        warnings_this: list[str] = []
        error: str | None = None

        # 1) 抓取 HTML
        injected_html: str | bytes | None = None
        if self.injectors.http_html:
            try:
                injected_html = self.injectors.http_html(candidate.url)
            except Exception as exc:
                injected_html = None
                warnings_this.append(f"HTML 注入器异常: {exc}")

        fetch_result = fetch_article_html(
            candidate.url,
            timeout=self.config.defaults.fetch_timeout_seconds,
            user_agent=self.config.defaults.user_agent,
            html_content=injected_html,
        )

        if not fetch_result.ok:
            error = fetch_result.error or "无法抓取文章 HTML"
            partial = ArchivedArticle(
                article_id=article_id,
                source=candidate.source,
                account_name=candidate.account_name,
                account_id=candidate.account_id,
                title=candidate.title,
                url=candidate.url,
                canonical_url=candidate.canonical_url,
                published_at=candidate.published_at,
                captured_at=run_started_at,
                author=candidate.author,
                digest=candidate.digest,
                status="failed",
                archive_dir=str(article_dir),
                metadata_path=str(article_dir / "metadata.json"),
                error=error,
            )
            article_dir.mkdir(parents=True, exist_ok=True)
            write_metadata(
                article_dir / "metadata.json",
                partial.model_dump(mode="json", exclude_none=True),
            )
            return partial

        # 2) 正文提取
        content = extract_main_content(fetch_result.html, url=fetch_result.final_url)
        # 3) 噪声清洗
        rules = {}
        if isinstance(candidate.raw_entry, dict):
            rules = candidate.raw_entry.get("clean_rules") or {}
        content = clean_wechat_content(content, rules=rules)

        status = "saved"
        if not content.text or len(content.text) < 30:
            # 正文很少：可能抓取失败，但仍然保存原始 HTML，记为 partial
            status = "partial"
            error = error or "正文内容为空或非常短"

        # 4) 图片下载（可选）
        image_map: dict[str, str] = {}
        if self.config.defaults.download_images:
            try:
                image_map, img_warnings = download_article_images(
                    content.image_urls or [],
                    article_dir,
                    timeout=self.config.defaults.fetch_timeout_seconds,
                    user_agent=self.config.defaults.user_agent,
                )
                warnings_this.extend(img_warnings)
            except Exception as exc:
                warnings_this.append(f"图片下载异常: {exc}")

        # 封面图
        cover_local: str | None = None
        if self.config.defaults.download_images and (content.cover_url or candidate.cover_url):
            try:
                cover_local, err = download_cover_image(
                    content.cover_url or candidate.cover_url,
                    article_dir,
                    timeout=self.config.defaults.fetch_timeout_seconds,
                    user_agent=self.config.defaults.user_agent,
                )
                if err:
                    warnings_this.append(err)
            except Exception as exc:
                warnings_this.append(f"封面图下载异常: {exc}")

        # 5) 写文件
        article_dir.mkdir(parents=True, exist_ok=True)

        markdown_path: str | None = None
        if self.config.defaults.save_markdown:
            try:
                markdown_text = build_article_markdown(candidate, content, captured_at=run_started_at)
                markdown_text = rewrite_markdown_image_urls(markdown_text, image_map)
                markdown_path = str(article_dir / "article.md")
                write_markdown(markdown_path, markdown_text)
            except Exception as exc:
                warnings_this.append(f"Markdown 写入失败: {exc}")

        html_path: str | None = None
        if self.config.defaults.save_html:
            try:
                final_html = rewrite_html_image_urls(content.html or fetch_result.html, image_map)
                html_path = str(article_dir / "article.html")
                write_html(html_path, final_html)
            except Exception as exc:
                warnings_this.append(f"HTML 写入失败: {exc}")

        # 正文 hash
        content_hash = hashlib.sha256(
            (content.text or "").encode("utf-8")
        ).hexdigest()[:32]

        article = ArchivedArticle(
            article_id=article_id,
            source=candidate.source,
            account_name=candidate.account_name,
            account_id=candidate.account_id,
            title=content.title or candidate.title,
            url=candidate.url,
            canonical_url=candidate.canonical_url,
            published_at=content.publish_time or candidate.published_at,
            captured_at=run_started_at,
            author=content.author or candidate.author,
            digest=content.digest or candidate.digest,
            content_hash=content_hash,
            status=status,
            archive_dir=str(article_dir),
            metadata_path=str(article_dir / "metadata.json"),
            markdown_path=markdown_path,
            html_path=html_path,
            cover_image_path=cover_local,
            image_count=len(image_map),
            error=error or ("; ".join(warnings_this) if warnings_this and status == "partial" else None),
        )

        # 6) 写 metadata.json
        metadata: dict[str, Any] = article.model_dump(mode="json", exclude_none=True)
        metadata["image_urls"] = list(content.image_urls or [])
        if warnings_this:
            metadata["warnings"] = warnings_this
        write_metadata(article_dir / "metadata.json", metadata)
        return article

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run(self) -> WeChatArchiveRunResult:
        """执行一次完整归档流程，返回运行汇总。"""

        started_at = self._now()
        state_dir = self._state_dir()

        seen_store = WeChatSeenStore(state_dir / "seen_articles.sqlite")
        candidates, warnings = self._collect_candidates()

        account_stats: dict[str, AccountRunStats] = {}
        saved_articles: list[ArchivedArticle] = []
        failed_articles: list[FailedArticle] = []
        duplicate_count = 0

        # 预先创建账号统计对象（包括未产出任何候选的账号）
        for acc in self.config.accounts:
            if acc.account_name not in account_stats:
                account_stats[acc.account_name] = AccountRunStats(account_name=acc.account_name)

        # 处理每篇候选
        for candidate in candidates:
            key = candidate.account_name or "未知公众号"
            stats = account_stats.setdefault(key, AccountRunStats(account_name=key))
            stats.candidates += 1

            # 去重：已处理成功的就跳过
            if seen_store.has_seen(candidate):
                stats.duplicate += 1
                duplicate_count += 1
                continue

            stats.new_articles += 1
            article_dir = article_directory(
                self.root,
                candidate.published_at,
                candidate.account_name,
                candidate.title,
            )

            try:
                archived = self._archive_one(
                    candidate,
                    seen_store=seen_store,
                    article_dir=article_dir,
                    run_started_at=started_at,
                )
            except Exception as exc:
                archived = ArchivedArticle(
                    article_id=article_id_for(candidate),
                    source=candidate.source,
                    account_name=candidate.account_name,
                    account_id=candidate.account_id,
                    title=candidate.title,
                    url=candidate.url,
                    canonical_url=candidate.canonical_url,
                    published_at=candidate.published_at,
                    captured_at=started_at,
                    author=candidate.author,
                    digest=candidate.digest,
                    status="failed",
                    archive_dir=str(article_dir),
                    metadata_path=str(article_dir / "metadata.json"),
                    error=f"归档异常: {exc}",
                )

            # 更新统计
            if archived.status == "saved":
                stats.saved += 1
                stats.last_success_at = started_at
            elif archived.status == "partial":
                stats.partial += 1
            else:
                stats.failed += 1

            # 写入 seen_articles.sqlite
            seen_store.mark_seen(archived, now_str=started_at)

            # 写入 articles.jsonl
            append_jsonl(self._index_path(), archived)
            if archived.status == "saved":
                saved_articles.append(archived)

            # 写入 run_log.jsonl（每篇一行）
            append_jsonl(
                state_dir / "run_log.jsonl",
                {
                    "run_started_at": started_at,
                    "article_id": archived.article_id,
                    "title": archived.title,
                    "url": archived.url,
                    "status": archived.status,
                    "archive_dir": archived.archive_dir,
                    "error": archived.error,
                },
            )

            if archived.status == "failed":
                failed = FailedArticle(
                    article_id=archived.article_id,
                    title=archived.title,
                    url=archived.url,
                    canonical_url=archived.canonical_url,
                    source=archived.source,
                    account_name=archived.account_name,
                    account_id=archived.account_id,
                    published_at=archived.published_at,
                    author=archived.author,
                    error=archived.error,
                    failed_at=started_at,
                )
                failed_articles.append(failed)
                append_jsonl(state_dir / "failed_queue.jsonl", failed)

        # 写日报
        ended_at = self._now()
        result = WeChatArchiveRunResult(
            run_id="run_" + started_at.replace(":", "-").replace("T", "_").replace("+", "_"),
            started_at=started_at,
            ended_at=ended_at,
            total_accounts=len(self.config.accounts),
            total_candidates=len(candidates),
            total_new_articles=sum(s.new_articles for s in account_stats.values()),
            total_saved=sum(s.saved for s in account_stats.values()),
            total_partial=sum(s.partial for s in account_stats.values()),
            total_failed=sum(s.failed for s in account_stats.values()),
            total_duplicate=duplicate_count,
            archive_root=str(self.root),
            accounts=list(account_stats.values()),
            saved_articles=saved_articles,
            failed_articles=failed_articles,
            warnings=warnings,
        )

        _write_run_log_summary(result, state_dir, mode="run")

        report_text = build_daily_capture_report(result)
        report_path = self._reports_dir() / f"daily_capture_{started_at[:10]}.md"
        write_markdown(report_path, report_text)
        result.reports = [str(report_path)]

        seen_store.close()
        return result

    # ------------------------------------------------------------------
    # dry-run: 只收集候选并报告，不做正文抓取
    # ------------------------------------------------------------------

    def dry_run(self) -> WeChatArchiveRunResult:
        started_at = self._now()
        state_dir = self._state_dir()
        seen_store = WeChatSeenStore(state_dir / "seen_articles.sqlite")
        candidates, warnings = self._collect_candidates()

        account_stats: dict[str, AccountRunStats] = {}
        for acc in self.config.accounts:
            if acc.account_name not in account_stats:
                account_stats[acc.account_name] = AccountRunStats(account_name=acc.account_name)

        duplicate_count = 0
        for candidate in candidates:
            key = candidate.account_name or "未知公众号"
            stats = account_stats.setdefault(key, AccountRunStats(account_name=key))
            stats.candidates += 1
            if seen_store.has_seen(candidate):
                stats.duplicate += 1
                duplicate_count += 1
            else:
                stats.new_articles += 1

        ended_at = self._now()
        result = WeChatArchiveRunResult(
            run_id="dry_" + started_at.replace(":", "-").replace("T", "_").replace("+", "_"),
            started_at=started_at,
            ended_at=ended_at,
            total_accounts=len(self.config.accounts),
            total_candidates=len(candidates),
            total_new_articles=sum(s.new_articles for s in account_stats.values()),
            total_saved=0,
            total_partial=0,
            total_failed=0,
            total_duplicate=duplicate_count,
            archive_root=str(self.root),
            accounts=list(account_stats.values()),
            warnings=warnings,
        )
        report_text = build_daily_capture_report(result)
        report_path = self._reports_dir() / f"daily_capture_{started_at[:10]}_dryrun.md"
        write_markdown(report_path, report_text)
        result.reports = [str(report_path)]
        _write_run_log_summary(result, state_dir, mode="dry_run")
        seen_store.close()
        return result

    # ------------------------------------------------------------------
    # retry-failed: 读 failed_queue.jsonl，再跑一次
    # ------------------------------------------------------------------

    def retry_failed(self) -> WeChatArchiveRunResult:
        started_at = self._now()
        state_dir = self._state_dir()
        failed_path = state_dir / "failed_queue.jsonl"
        failed_list = _load_failed_queue_safe(failed_path)

        if not failed_list:
            ended_at = self._now()
            result = WeChatArchiveRunResult(
                run_id="retry_" + started_at.replace(":", "-").replace("T", "_").replace("+", "_"),
                started_at=started_at,
                ended_at=ended_at,
                total_accounts=0,
                total_candidates=0,
                total_new_articles=0,
                total_saved=0,
                total_partial=0,
                total_failed=0,
                total_duplicate=0,
                archive_root=str(self.root),
                warnings=["failed_queue 为空，无可重试条目"],
            )
            _write_run_log_summary(result, state_dir, mode="retry_empty")
            return result

        # 重建候选列表（每个失败条目当成一条手工 URL）
        candidates: list[ArticleCandidate] = []
        for f in failed_list:
            try:
                cand = build_manual_candidate(
                    url=f.url,
                    account_name=f.account_name or "手工投喂",
                    account_id=f.account_id,
                )
                # 用原来的标题覆盖（如果还有）
                if f.title and f.title != f.url:
                    cand.title = f.title
                if f.published_at:
                    cand.published_at = f.published_at
                if f.author:
                    cand.author = f.author
                candidates.append(cand)
            except Exception:
                continue

        # 用已存在的流程跑（把 candidates 注入到 archiver 内部）
        # 这里直接复用 run() 前半段思路，避免影响全局账号收集
        seen_store = WeChatSeenStore(state_dir / "seen_articles.sqlite")
        account_stats: dict[str, AccountRunStats] = {}
        saved_articles: list[ArchivedArticle] = []
        new_failed: list[FailedArticle] = []

        for candidate in candidates:
            key = candidate.account_name or "未知公众号"
            stats = account_stats.setdefault(key, AccountRunStats(account_name=key))
            stats.candidates += 1
            stats.new_articles += 1  # 失败条目允许重试，不视为 duplicate

            article_dir = article_directory(
                self.root,
                candidate.published_at,
                candidate.account_name,
                candidate.title,
            )
            try:
                archived = self._archive_one(
                    candidate,
                    seen_store=seen_store,
                    article_dir=article_dir,
                    run_started_at=started_at,
                )
            except Exception as exc:
                archived = ArchivedArticle(
                    article_id=article_id_for(candidate),
                    source=candidate.source,
                    account_name=candidate.account_name,
                    account_id=candidate.account_id,
                    title=candidate.title,
                    url=candidate.url,
                    canonical_url=candidate.canonical_url,
                    published_at=candidate.published_at,
                    captured_at=started_at,
                    author=candidate.author,
                    digest=candidate.digest,
                    status="failed",
                    archive_dir=str(article_dir),
                    metadata_path=str(article_dir / "metadata.json"),
                    error=f"重试异常: {exc}",
                )

            if archived.status == "saved":
                stats.saved += 1
                stats.last_success_at = started_at
                saved_articles.append(archived)
            elif archived.status == "partial":
                stats.partial += 1
            else:
                stats.failed += 1
                new_failed.append(
                    FailedArticle(
                        article_id=archived.article_id,
                        title=archived.title,
                        url=archived.url,
                        canonical_url=archived.canonical_url,
                        source=archived.source,
                        account_name=archived.account_name,
                        account_id=archived.account_id,
                        published_at=archived.published_at,
                        author=archived.author,
                        error=archived.error,
                        failed_at=started_at,
                        retry_count=(f.retry_count or 0) + 1 if hasattr(f, "retry_count") else 1,
                    )
                )

            seen_store.mark_seen(archived, now_str=started_at)
            append_jsonl(self._index_path(), archived)
            append_jsonl(
                state_dir / "run_log.jsonl",
                {
                    "run_started_at": started_at,
                    "article_id": archived.article_id,
                    "title": archived.title,
                    "url": archived.url,
                    "status": archived.status,
                    "archive_dir": archived.archive_dir,
                    "error": archived.error,
                    "retry": True,
                },
            )

        # 更新 failed_queue：先移掉原文件里"重试成功/部分成功"的条目，再追加新失败
        _rewrite_failed_queue(failed_path, new_failed, candidates)

        ended_at = self._now()
        result = WeChatArchiveRunResult(
            run_id="retry_" + started_at.replace(":", "-").replace("T", "_").replace("+", "_"),
            started_at=started_at,
            ended_at=ended_at,
            total_accounts=len(account_stats),
            total_candidates=len(candidates),
            total_new_articles=len(candidates),
            total_saved=sum(s.saved for s in account_stats.values()),
            total_partial=sum(s.partial for s in account_stats.values()),
            total_failed=sum(s.failed for s in account_stats.values()),
            total_duplicate=0,
            archive_root=str(self.root),
            accounts=list(account_stats.values()),
            saved_articles=saved_articles,
            failed_articles=new_failed,
        )
        report = build_daily_capture_report(result)
        report_path = self._reports_dir() / f"daily_capture_{started_at[:10]}_retry.md"
        write_markdown(report_path, report)
        result.reports = [str(report_path)]
        _write_run_log_summary(result, state_dir, mode="retry")
        seen_store.close()
        return result


def _load_failed_queue_safe(path: Path) -> list[FailedArticle]:
    if not path.exists():
        return []
    from .storage import load_failed_queue
    return load_failed_queue(path)


def _rewrite_failed_queue(
    path: Path,
    new_failed: list[FailedArticle],
    candidates: list[ArticleCandidate],
) -> None:
    """保留原 failed_queue 中未被重试的条目，再追加新失败条目。"""

    original = _load_failed_queue_safe(path)
    retry_urls = {c.canonical_url for c in candidates}
    kept = [f for f in original if f.canonical_url not in retry_urls]

    # 先清空再重写（避免旧条目累积）
    if path.exists():
        path.unlink()
    for f in kept + new_failed:
        append_jsonl(path, f)


# ---------------------------------------------------------------------------
# Run-level summary 写入 run_log.jsonl（供审计和报告重建）
# ---------------------------------------------------------------------------


def _run_exit_code(result: WeChatArchiveRunResult) -> int:
    """根据运行结果计算 exit code。"""
    if result.total_failed > 0 and result.total_saved == 0 and result.total_partial == 0:
        return 3
    if result.total_failed > 0:
        return 2
    return 0


def _write_run_log_summary(
    result: WeChatArchiveRunResult,
    state_dir: Path,
    mode: str,
) -> None:
    """在 run_log.jsonl 末尾追加一条 run-level summary 记录。"""
    entry = {
        "entry_type": "run_summary",
        "run_id": result.run_id,
        "mode": mode,
        "started_at": result.started_at,
        "finished_at": result.ended_at,
        "account_count": result.total_accounts,
        "candidate_count": result.total_candidates,
        "new_count": result.total_new_articles,
        "saved_count": result.total_saved,
        "partial_count": result.total_partial,
        "failed_count": result.total_failed,
        "duplicate_count": result.total_duplicate,
        "exit_code": _run_exit_code(result),
    }
    append_jsonl(state_dir / "run_log.jsonl", entry)
