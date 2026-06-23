"""Research Source Foundation 的主流程编排。

功能说明（小白解读）：
    ResearchArchiver 把 config / connector / fetcher / extractor / dedupe / storage
    串起来，提供三个主入口：
        1. dry_run()       只发现候选，不抓正文，不写 documents.jsonl
        2. run()           完整执行：发现 → 去重 → 抓取 → 抽取 → 归档 → 日报
        3. retry_failed()  读取 failed_queue.jsonl，重试 retryable 条目

    单 source 失败不影响其他 source（fail-soft）。
    单文档失败不抛异常，记入 failed_queue。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..run.time_utils import utcnow_iso
from .connectors import get_connector
from .dedupe import ResearchSeenStore, document_id_for
from .extractor import extract_html_document
from .fetcher import fetch_url
from .models import (
    DocumentCandidate,
    ExtractedResearchContent,
    FailedDocument,
    NormalizedDocument,
    ResearchArchiveConfig,
    ResearchRunResult,
    SourceHealth,
)
from .reports import build_research_daily_report, daily_report_filename
from .storage import (
    append_failed_document,
    append_run_log,
    append_source_health,
    archive_document,
    load_failed_queue,
    overwrite_source_health,
    write_latest_documents,
    write_report,
)


# ---------------------------------------------------------------------------
# 测试注入点
# ---------------------------------------------------------------------------


HttpHtmlInjector = Callable[[str], str | None]
# 签名：接受 url，返回预先准备好的 HTML 字符串。返回 None 表示走真实 HTTP。


# ---------------------------------------------------------------------------
# 标准化 error_type 分类（Phase 2F）
# ---------------------------------------------------------------------------


# 合法的 error_type 取值
ERROR_TYPES = {
    "config_error",
    "connector_error",
    "fetch_error",
    "parse_error",
    "extract_error",
    "storage_error",
    "empty_source",
    "unsupported_source_type",
    "unknown_error",
}


def classify_error(error_msg: str | None) -> str | None:
    """根据错误信息推断标准化 error_type。

    参数：
        error_msg: 原始错误信息

    返回：
        error_type 字符串；无错误返回 None

    小白解读：
        只做关键词匹配，不做语义判断。
        用于让 failed_queue 和 source_health 更可诊断。
    """
    if not error_msg:
        return None
    lower = error_msg.lower()
    if "unsupported source_type" in lower:
        return "unsupported_source_type"
    if "config" in lower and "error" in lower:
        return "config_error"
    if "connector 异常" in lower or "connector error" in lower:
        return "connector_error"
    if "抓取失败" in lower or "fetch" in lower or "http" in lower or "timeout" in lower:
        return "fetch_error"
    if "解析" in lower or "parse" in lower or "beautifulsoup" in lower:
        return "parse_error"
    if "正文抽取" in lower or "extract" in lower:
        return "extract_error"
    if "写入" in lower or "storage" in lower or "io" in lower:
        return "storage_error"
    if "内容为空" in lower or "empty" in lower:
        return "empty_source"
    return "unknown_error"


@dataclass
class ResearchInjectors:
    """测试用的注入点。生产环境一般全是 None。

    字段：
        http_html:  按 URL 注入 HTML，跳过真实 HTTP 抓取
        now_str:    注入当前时间函数（默认用 utcnow_iso）
        feed_content_by_url: 按 feed_url 注入 RSS 内容（用于 RSS connector 测试）
        list_html_by_url:    按 list page URL 注入列表页 HTML（用于 official_public_research 测试）
        podcast_html_by_url: 按 URL 注入 podcast HTML/XML（用于 podcast_transcript 测试）
        conference_html_by_url: 按 URL 注入 conference HTML（用于 conference_transcript 测试）
        analyst_action_html_by_url: 按 URL 注入 analyst action HTML（用于 analyst_action 测试）
        media_mention_html_by_url: 按 URL 注入 media mention HTML（用于 media_mention 测试）
    """
    http_html: HttpHtmlInjector | None = None
    now_str: Callable[[], str] | None = None
    feed_content_by_url: Callable[[str], str | None] | None = None
    list_html_by_url: Callable[[str], str | None] | None = None
    podcast_html_by_url: Callable[[str], str | None] | None = None
    conference_html_by_url: Callable[[str], str | None] | None = None
    analyst_action_html_by_url: Callable[[str], str | None] | None = None
    media_mention_html_by_url: Callable[[str], str | None] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class ResearchArchiver:
    """Research Source Foundation 的主流程。"""

    def __init__(
        self,
        config: ResearchArchiveConfig,
        injectors: ResearchInjectors | None = None,
    ) -> None:
        """初始化 Archiver。

        参数：
            config:    ResearchArchiveConfig
            injectors: 测试注入点（生产为 None）
        """
        self.config = config
        self.injectors = injectors or ResearchInjectors()
        self.root = Path(config.archive_root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _now(self) -> str:
        """获取当前 UTC ISO 时间（支持注入）。"""
        if self.injectors.now_str:
            return self.injectors.now_str()
        return utcnow_iso()

    def _state_dir(self) -> Path:
        """获取 state 目录，不存在则创建。"""
        p = self.root / "state"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _index_dir(self) -> Path:
        """获取 index 目录，不存在则创建。"""
        p = self.root / "index"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _reports_dir(self) -> Path:
        """获取 reports 目录，不存在则创建。"""
        p = self.root / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _seen_store(self) -> ResearchSeenStore:
        """创建 SeenStore。"""
        return ResearchSeenStore(self._state_dir() / "seen.sqlite")

    def _enabled_sources(self) -> list[Any]:
        """返回 enabled=True 的 source 列表。"""
        return [s for s in self.config.sources if s.enabled]

    def _max_items_for(self, source: Any) -> int:
        """获取 source 的 max_items（优先 source 自身，其次 defaults）。"""
        if source.max_items is not None:
            return source.max_items
        return self.config.defaults.max_items_per_source

    def _discover_candidates(
        self,
        source: Any,
    ) -> tuple[list[DocumentCandidate], str | None]:
        """从一个 source 发现候选文档。

        返回：
            (candidates, error)
            error 非 None 表示该 source 整体失败（如 feed 不可达）。
        """
        connector = get_connector(source.source_type)
        if connector is None:
            return [], f"unsupported source_type: {source.source_type}"

        # RSS connector 支持注入 feed 内容
        if source.source_type == "rss_feed" and self.injectors.feed_content_by_url:
            from .connectors.rss import RSSConnector

            connector = RSSConnector(
                feed_content_by_url=self.injectors.feed_content_by_url
            )

        # official_public_research connector 支持注入列表页 HTML
        if source.source_type == "official_public_research" and self.injectors.list_html_by_url:
            from .connectors.official_public import OfficialPublicResearchConnector

            connector = OfficialPublicResearchConnector(
                list_html_by_url=self.injectors.list_html_by_url
            )

        # podcast_transcript connector 支持注入 HTML/XML
        if source.source_type == "podcast_transcript" and self.injectors.podcast_html_by_url:
            from .connectors.podcast_transcript import PodcastTranscriptConnector

            connector = PodcastTranscriptConnector(
                html_by_url=self.injectors.podcast_html_by_url
            )

        # conference_transcript connector 支持注入 HTML
        if source.source_type == "conference_transcript" and self.injectors.conference_html_by_url:
            from .connectors.conference_transcript import ConferenceTranscriptConnector

            connector = ConferenceTranscriptConnector(
                html_by_url=self.injectors.conference_html_by_url
            )

        # analyst_action connector 支持注入 HTML
        if source.source_type == "analyst_action" and self.injectors.analyst_action_html_by_url:
            from .connectors.analyst_action import AnalystActionConnector

            connector = AnalystActionConnector(
                html_by_url=self.injectors.analyst_action_html_by_url
            )

        # media_mention connector 支持注入 HTML
        if source.source_type == "media_mention" and self.injectors.media_mention_html_by_url:
            from .connectors.media_mention import MediaMentionConnector

            connector = MediaMentionConnector(
                html_by_url=self.injectors.media_mention_html_by_url
            )

        try:
            candidates = connector.discover(source, self.config)
        except Exception as exc:
            return [], f"connector 异常: {exc}"

        # 应用 max_items
        max_items = self._max_items_for(source)
        if max_items and len(candidates) > max_items:
            candidates = candidates[:max_items]
        return candidates, None

    # ------------------------------------------------------------------
    # 单文档处理
    # ------------------------------------------------------------------

    def _archive_one(
        self,
        candidate: DocumentCandidate,
        seen_store: ResearchSeenStore,
        run_started_at: str,
    ) -> NormalizedDocument:
        """处理一篇候选文档，返回 NormalizedDocument。

        失败时返回 status=failed 的 NormalizedDocument，不抛异常。
        """
        # 1) 抓取 HTML（wechat_archive 类型跳过，直接用 raw_entry）
        if candidate.source_type == "wechat_archive":
            return self._archive_wechat_candidate(candidate, run_started_at)

        # manual_url / rss_feed 需要抓正文
        injected_html: str | None = None
        if self.injectors.http_html:
            try:
                injected_html = self.injectors.http_html(candidate.url)
            except Exception:
                injected_html = None

        fetch_result = fetch_url(
            candidate.url,
            timeout=self.config.defaults.fetch_timeout_seconds,
            user_agent=self.config.defaults.user_agent,
            html_content=injected_html,
        )

        if not fetch_result.ok:
            return self._build_failed_document(
                candidate,
                run_started_at,
                error=fetch_result.error or "抓取失败",
                raw_html="",
            )

        # 2) 抽取正文
        try:
            extracted = extract_html_document(fetch_result.html, fetch_result.final_url)
        except Exception as exc:
            extracted = ExtractedResearchContent(
                html=fetch_result.html,
                text="",
                extraction_quality="empty",
            )
            # 抽取失败但保留 HTML，记为 partial
            return self._archive_candidate(
                candidate=candidate,
                extracted=extracted,
                raw_html=fetch_result.html,
                captured_at=run_started_at,
                status="partial",
                error=f"正文抽取异常: {exc}",
            )

        # 3) 判定状态
        status = "saved"
        error: str | None = None
        if extracted.extraction_quality in ("empty",):
            status = "partial"
            error = "正文抽取为空"
        elif extracted.extraction_quality == "low":
            status = "partial"
            error = "正文抽取质量较低"

        # 4) 归档
        return self._archive_candidate(
            candidate=candidate,
            extracted=extracted,
            raw_html=fetch_result.html,
            captured_at=run_started_at,
            status=status,
            error=error,
        )

    def _archive_wechat_candidate(
        self,
        candidate: DocumentCandidate,
        run_started_at: str,
    ) -> NormalizedDocument:
        """处理 wechat_archive 类型的候选：不重新抓取，直接复用原始归档路径。

        Phase 1 行为：
            - 不重新抓微信
            - 不下载图片
            - markdown_path / html_path 指向原始 wechat archive 路径
            - status = saved
        """
        from .dedupe import document_id_for
        from .storage import compute_content_hash

        doc_id = document_id_for(candidate)
        title = candidate.title or "（无标题）"
        # 用 summary 或 raw_entry 里的字段作为正文
        text = candidate.summary or candidate.raw_entry.get("digest") or ""
        content_hash = compute_content_hash(text or title)

        # 复用原始 wechat archive 路径
        wechat_md = candidate.raw_entry.get("markdown_path")
        wechat_html = candidate.raw_entry.get("html_path")
        wechat_meta = candidate.raw_entry.get("metadata_path")

        # 在 research archive 下也写一份 metadata.json（指向原始路径）
        from .storage import document_directory, _atomic_write
        import json

        doc_dir = document_directory(
            self.config.archive_root,
            candidate.published_at,
            candidate.source_name,
            title,
        )
        doc_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = doc_dir / "metadata.json"
        metadata = {
            "document_id": doc_id,
            "source_id": candidate.source_id,
            "source_name": candidate.source_name,
            "source_type": candidate.source_type,
            "title": title,
            "url": candidate.url,
            "canonical_url": candidate.canonical_url,
            "published_at": candidate.published_at,
            "captured_at": run_started_at,
            "author": candidate.author,
            "summary": candidate.summary,
            "language": candidate.language,
            "legal_profile": candidate.legal_profile,
            "tags": list(candidate.tags),
            "content_hash": content_hash,
            "status": "saved",
            "extraction_quality": "medium",
            "error": None,
            "markdown_path": wechat_md,
            "html_path": wechat_html,
            "raw_path": None,
            "metadata_path": str(metadata_path),
            "wechat_original_metadata_path": wechat_meta,
            "wechat_archive_dir": candidate.raw_entry.get("wechat_archive_dir"),
            "raw_entry": candidate.raw_entry,
        }
        _atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))

        doc = NormalizedDocument(
            document_id=doc_id,
            source_id=candidate.source_id,
            source_name=candidate.source_name,
            source_type=candidate.source_type,
            title=title,
            url=candidate.url,
            canonical_url=candidate.canonical_url,
            published_at=candidate.published_at,
            captured_at=run_started_at,
            updated_at=None,
            author=candidate.author,
            summary=candidate.summary,
            language=candidate.language,
            content_type="article",
            legal_profile=candidate.legal_profile,
            tags=list(candidate.tags),
            content_hash=content_hash,
            status="saved",
            markdown_path=wechat_md,
            html_path=wechat_html,
            raw_path=None,
            metadata_path=str(metadata_path),
            attachments=[],
            extraction_quality="medium",
            error=None,
        )

        # 追加写 documents.jsonl
        from .storage import append_jsonl
        append_jsonl(self._index_dir() / "documents.jsonl", doc.model_dump(exclude_none=True))
        return doc

    def _archive_candidate(
        self,
        candidate: DocumentCandidate,
        extracted: ExtractedResearchContent,
        raw_html: str,
        captured_at: str,
        status: str,
        error: str | None,
    ) -> NormalizedDocument:
        """调用 storage.archive_document 归档一篇普通候选。"""
        return archive_document(
            candidate=candidate,
            extracted=extracted,
            config=self.config,
            raw_html=raw_html,
            captured_at=captured_at,
            status=status,
            error=error,
        )

    def _build_failed_document(
        self,
        candidate: DocumentCandidate,
        captured_at: str,
        error: str,
        raw_html: str = "",
    ) -> NormalizedDocument:
        """构造一篇 failed 文档（不写文件，仅返回对象）。"""
        from .dedupe import document_id_for
        from .storage import compute_content_hash

        doc_id = document_id_for(candidate)
        return NormalizedDocument(
            document_id=doc_id,
            source_id=candidate.source_id,
            source_name=candidate.source_name,
            source_type=candidate.source_type,
            title=candidate.title,
            url=candidate.url,
            canonical_url=candidate.canonical_url,
            published_at=candidate.published_at,
            captured_at=captured_at,
            updated_at=None,
            author=candidate.author,
            summary=candidate.summary,
            language=candidate.language,
            content_type="article",
            legal_profile=candidate.legal_profile,
            tags=list(candidate.tags),
            content_hash=compute_content_hash(raw_html or candidate.title),
            status="failed",
            markdown_path=None,
            html_path=None,
            raw_path=None,
            metadata_path="",
            attachments=[],
            extraction_quality="empty",
            error=error,
        )

    # ------------------------------------------------------------------
    # dry-run
    # ------------------------------------------------------------------

    def dry_run(self) -> ResearchRunResult:
        """试运行：只发现候选，不抓正文，不写 documents.jsonl。

        返回：
            ResearchRunResult
        """
        started_at = self._now()
        run_id = "dry_" + uuid.uuid4().hex[:12]
        state_dir = self._state_dir()
        seen_store = self._seen_store()

        source_stats: list[dict[str, Any]] = []
        source_health_records: list[dict[str, Any]] = []
        warnings: list[str] = []

        total_candidates = 0
        total_new = 0
        total_duplicate = 0
        total_skipped = 0

        for source in self._enabled_sources():
            candidates, err = self._discover_candidates(source)
            cand_count = len(candidates)
            total_candidates += cand_count

            new_count = 0
            dup_count = 0
            for cand in candidates:
                try:
                    if seen_store.has_seen(cand):
                        dup_count += 1
                    else:
                        new_count += 1
                except Exception:
                    new_count += 1

            total_new += new_count
            total_duplicate += dup_count

            err_type = classify_error(err)
            status = "healthy"
            if err:
                status = "failed"
                warnings.append(f"source [{source.source_name}] 发现失败: {err}")
                total_skipped += cand_count
            elif cand_count == 0:
                status = "degraded"
                err_type = "empty_source"

            stat = {
                "source_id": source.source_id,
                "source_name": source.source_name,
                "source_type": source.source_type,
                "enabled": True,
                "candidate_count": cand_count,
                "new_count": new_count,
                "duplicate_count": dup_count,
                "saved_count": 0,
                "partial_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "status": status,
                "error_type": err_type,
                "error": err,
            }
            source_stats.append(stat)

            source_health_records.append({
                "source_id": source.source_id,
                "source_name": source.source_name,
                "source_type": source.source_type,
                "checked_at": started_at,
                "status": status,
                "last_success_at": None if err else started_at,
                "last_failure_at": started_at if err else None,
                "consecutive_failures": 1 if err else 0,
                "last_error": err,
                "last_error_type": err_type,
                "candidate_count_last_run": cand_count,
                "new_count_last_run": new_count,
                "saved_count_last_run": 0,
                "partial_count_last_run": 0,
                "failed_count_last_run": 0,
                "duplicate_count_last_run": dup_count,
                "skipped_count_last_run": 0,
                "last_run_id": run_id,
                "last_report_path": None,
            })

        seen_store.close()
        finished_at = self._now()

        result = ResearchRunResult(
            run_id=run_id,
            mode="dry_run",
            archive_root=str(self.root),
            started_at=started_at,
            finished_at=finished_at,
            source_count=len(self.config.sources),
            enabled_source_count=len(self._enabled_sources()),
            candidate_count=total_candidates,
            new_count=total_new,
            saved_count=0,
            partial_count=0,
            failed_count=0,
            duplicate_count=total_duplicate,
            skipped_count=total_skipped,
            source_stats=source_stats,
            saved_documents=[],
            failed_documents=[],
            source_health=source_health_records,
            warnings=warnings,
            report_path=None,
            exit_code=0,
        )

        # 写 run_log summary
        append_run_log(self.root, _run_summary_entry(result))
        # 写 source_health
        overwrite_source_health(self.root, source_health_records)

        # 写 dry-run 报告
        report_text = build_research_daily_report(result)
        report_name = daily_report_filename(started_at[:10]).replace(".md", "_dryrun.md")
        report_path = write_report(self.root, report_name, report_text)
        result.report_path = str(report_path)

        return result

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    def run(self) -> ResearchRunResult:
        """完整运行：发现 → 去重 → 抓取 → 抽取 → 归档 → 日报。

        返回：
            ResearchRunResult
        """
        started_at = self._now()
        run_id = "run_" + uuid.uuid4().hex[:12]
        state_dir = self._state_dir()
        seen_store = self._seen_store()

        source_stats: list[dict[str, Any]] = []
        source_health_records: list[dict[str, Any]] = []
        warnings: list[str] = []

        total_candidates = 0
        total_new = 0
        total_saved = 0
        total_partial = 0
        total_failed = 0
        total_duplicate = 0
        total_skipped = 0

        all_saved_documents: list[NormalizedDocument] = []
        all_failed_documents: list[FailedDocument] = []

        for source in self._enabled_sources():
            candidates, err = self._discover_candidates(source)
            cand_count = len(candidates)
            total_candidates += cand_count

            saved_count = 0
            partial_count = 0
            failed_count = 0
            dup_count = 0
            skipped_count = 0
            source_error: str | None = err
            source_error_type: str | None = classify_error(err)

            if err:
                warnings.append(f"source [{source.source_name}] 发现失败: {err}")
                total_skipped += cand_count
                skipped_count = cand_count
            else:
                for cand in candidates:
                    try:
                        if seen_store.has_seen(cand):
                            dup_count += 1
                            total_duplicate += 1
                            continue
                    except Exception:
                        # seen store 异常不阻塞，按新文档处理
                        pass

                    total_new += 1
                    try:
                        doc = self._archive_one(cand, seen_store, started_at)
                    except Exception as exc:
                        doc = self._build_failed_document(
                            cand, started_at, error=f"归档异常: {exc}"
                        )

                    # 更新 seen store（saved/partial/duplicate 才算"已见过"）
                    if doc.status in ("saved", "partial", "duplicate"):
                        try:
                            seen_store.mark_seen(doc, now_str=started_at)
                        except Exception:
                            pass

                    if doc.status == "saved":
                        saved_count += 1
                        total_saved += 1
                        all_saved_documents.append(doc)
                    elif doc.status == "partial":
                        partial_count += 1
                        total_partial += 1
                        all_saved_documents.append(doc)
                    else:
                        failed_count += 1
                        total_failed += 1
                        # 根据失败原因分类 error_type
                        doc_err_type = classify_error(doc.error) or "unknown_error"
                        failed_doc = FailedDocument(
                            source_id=cand.source_id,
                            source_name=cand.source_name,
                            source_type=cand.source_type,
                            title=cand.title,
                            url=cand.url,
                            canonical_url=cand.canonical_url,
                            failed_at=started_at,
                            error=doc.error or "未知错误",
                            error_type=doc_err_type,
                            retryable=True,
                            retry_count=0,
                            run_id=run_id,
                            raw_entry=cand.raw_entry,
                        )
                        all_failed_documents.append(failed_doc)
                        append_failed_document(self.root, failed_doc)

            # source 级别状态
            if source_error:
                status = "failed"
            elif failed_count > 0 and saved_count == 0:
                status = "failed"
                if source_error_type is None:
                    source_error_type = "unknown_error"
            elif failed_count > 0 or partial_count > 0 or cand_count == 0:
                status = "degraded"
                if source_error_type is None and cand_count == 0:
                    source_error_type = "empty_source"
            else:
                status = "healthy"

            source_stats.append({
                "source_id": source.source_id,
                "source_name": source.source_name,
                "source_type": source.source_type,
                "enabled": True,
                "candidate_count": cand_count,
                "new_count": cand_count - dup_count,
                "saved_count": saved_count,
                "partial_count": partial_count,
                "failed_count": failed_count,
                "duplicate_count": dup_count,
                "skipped_count": skipped_count,
                "status": status,
                "error_type": source_error_type,
                "error": source_error,
            })

            source_health_records.append({
                "source_id": source.source_id,
                "source_name": source.source_name,
                "source_type": source.source_type,
                "checked_at": started_at,
                "status": status,
                "last_success_at": started_at if status in ("healthy", "degraded") else None,
                "last_failure_at": started_at if status == "failed" else None,
                "consecutive_failures": 1 if status == "failed" else 0,
                "last_error": source_error,
                "last_error_type": source_error_type,
                "candidate_count_last_run": cand_count,
                "new_count_last_run": cand_count - dup_count,
                "saved_count_last_run": saved_count,
                "partial_count_last_run": partial_count,
                "failed_count_last_run": failed_count,
                "duplicate_count_last_run": dup_count,
                "skipped_count_last_run": skipped_count,
                "last_run_id": run_id,
                "last_report_path": None,
            })

        seen_store.close()
        finished_at = self._now()

        # 写 documents.latest.jsonl（本次 saved/partial）
        write_latest_documents(self.root, all_saved_documents)

        # 写 source_health
        overwrite_source_health(self.root, source_health_records)

        # 计算 exit code
        exit_code = _compute_exit_code(
            total_saved=total_saved,
            total_partial=total_partial,
            total_failed=total_failed,
        )

        result = ResearchRunResult(
            run_id=run_id,
            mode="run",
            archive_root=str(self.root),
            started_at=started_at,
            finished_at=finished_at,
            source_count=len(self.config.sources),
            enabled_source_count=len(self._enabled_sources()),
            candidate_count=total_candidates,
            new_count=total_new,
            saved_count=total_saved,
            partial_count=total_partial,
            failed_count=total_failed,
            duplicate_count=total_duplicate,
            skipped_count=total_skipped,
            source_stats=source_stats,
            saved_documents=all_saved_documents,
            failed_documents=all_failed_documents,
            source_health=source_health_records,
            warnings=warnings,
            report_path=None,
            exit_code=exit_code,
        )

        # 写 run_log summary
        append_run_log(self.root, _run_summary_entry(result))

        # 写日报
        report_text = build_research_daily_report(result)
        report_path = write_report(
            self.root,
            daily_report_filename(started_at[:10]),
            report_text,
        )
        result.report_path = str(report_path)

        return result

    # ------------------------------------------------------------------
    # retry-failed
    # ------------------------------------------------------------------

    def retry_failed(self) -> ResearchRunResult:
        """重试 failed_queue.jsonl 中的 retryable 条目。

        返回：
            ResearchRunResult
        """
        started_at = self._now()
        run_id = "retry_" + uuid.uuid4().hex[:12]
        state_dir = self._state_dir()
        seen_store = self._seen_store()

        failed_list = load_failed_queue(self.root)
        retryable = [f for f in failed_list if f.retryable]

        if not retryable:
            finished_at = self._now()
            result = ResearchRunResult(
                run_id=run_id,
                mode="retry_failed",
                archive_root=str(self.root),
                started_at=started_at,
                finished_at=finished_at,
                source_count=0,
                enabled_source_count=0,
                candidate_count=0,
                new_count=0,
                saved_count=0,
                partial_count=0,
                failed_count=0,
                duplicate_count=0,
                skipped_count=0,
                source_stats=[],
                saved_documents=[],
                failed_documents=[],
                source_health=[],
                warnings=["failed_queue 为空或无可重试条目"],
                report_path=None,
                exit_code=0,
            )
            append_run_log(self.root, _run_summary_entry(result))
            seen_store.close()
            return result

        # 把每个失败条目转成 DocumentCandidate
        candidates: list[DocumentCandidate] = []
        for f in retryable:
            cand = DocumentCandidate(
                source_id=f.source_id,
                source_name=f.source_name,
                source_type=f.source_type,
                title=f.title or f.url,
                url=f.url,
                canonical_url=f.canonical_url,
                published_at=None,
                author=None,
                summary=None,
                legal_profile="unknown",
                tags=[],
                raw_entry=f.raw_entry or {},
            )
            candidates.append(cand)

        saved_documents: list[NormalizedDocument] = []
        new_failed: list[FailedDocument] = []
        total_saved = 0
        total_partial = 0
        total_failed = 0

        for cand in candidates:
            try:
                doc = self._archive_one(cand, seen_store, started_at)
            except Exception as exc:
                doc = self._build_failed_document(cand, started_at, error=f"重试异常: {exc}")

            if doc.status in ("saved", "partial"):
                try:
                    seen_store.mark_seen(doc, now_str=started_at)
                except Exception:
                    pass

            if doc.status == "saved":
                total_saved += 1
                saved_documents.append(doc)
            elif doc.status == "partial":
                total_partial += 1
                saved_documents.append(doc)
            else:
                total_failed += 1
                doc_err_type = classify_error(doc.error) or "unknown_error"
                new_failed.append(FailedDocument(
                    source_id=cand.source_id,
                    source_name=cand.source_name,
                    source_type=cand.source_type,
                    title=cand.title,
                    url=cand.url,
                    canonical_url=cand.canonical_url,
                    failed_at=started_at,
                    error=doc.error or "重试失败",
                    error_type=doc_err_type,
                    retryable=True,
                    retry_count=1,
                    run_id=run_id,
                    raw_entry=cand.raw_entry,
                ))

        seen_store.close()

        # 重写 failed_queue：移除已重试的条目，追加新失败
        _rewrite_failed_queue(self.root, retryable, new_failed)

        # 写 documents.latest.jsonl
        write_latest_documents(self.root, saved_documents)

        finished_at = self._now()
        exit_code = _compute_exit_code(
            total_saved=total_saved,
            total_partial=total_partial,
            total_failed=total_failed,
        )

        result = ResearchRunResult(
            run_id=run_id,
            mode="retry_failed",
            archive_root=str(self.root),
            started_at=started_at,
            finished_at=finished_at,
            source_count=0,
            enabled_source_count=0,
            candidate_count=len(candidates),
            new_count=len(candidates),
            saved_count=total_saved,
            partial_count=total_partial,
            failed_count=total_failed,
            duplicate_count=0,
            skipped_count=0,
            source_stats=[],
            saved_documents=saved_documents,
            failed_documents=new_failed,
            source_health=[],
            warnings=[],
            report_path=None,
            exit_code=exit_code,
        )

        append_run_log(self.root, _run_summary_entry(result))

        # 写 retry 报告
        report_text = build_research_daily_report(result)
        report_path = write_report(
            self.root,
            daily_report_filename(started_at[:10]).replace(".md", "_retry.md"),
            report_text,
        )
        result.report_path = str(report_path)

        return result


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _compute_exit_code(total_saved: int, total_partial: int, total_failed: int) -> int:
    """根据运行结果计算 exit code。

    规则：
        0 = 全部成功
        2 = 部分失败
        3 = 全部失败
    """
    if total_failed > 0 and total_saved == 0 and total_partial == 0:
        return 3
    if total_failed > 0:
        return 2
    return 0


def _run_summary_entry(result: ResearchRunResult) -> dict[str, Any]:
    """构造 run_log.jsonl 的 run_summary 记录。

    Phase 2F 增强：
        - 新增 archive_root 字段
        - 新增 source_stats 字段（包含每个 source 的运行统计）
        - 新增 warnings 字段
    """
    return {
        "entry_type": "run_summary",
        "run_id": result.run_id,
        "mode": result.mode,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "archive_root": result.archive_root,
        "source_count": result.source_count,
        "enabled_source_count": result.enabled_source_count,
        "candidate_count": result.candidate_count,
        "new_count": result.new_count,
        "saved_count": result.saved_count,
        "partial_count": result.partial_count,
        "failed_count": result.failed_count,
        "duplicate_count": result.duplicate_count,
        "skipped_count": result.skipped_count,
        "exit_code": result.exit_code,
        "source_stats": result.source_stats,
        "warnings": result.warnings,
        "report_path": result.report_path,
    }


def _rewrite_failed_queue(
    archive_root: Path,
    retried: list[FailedDocument],
    new_failed: list[FailedDocument],
) -> None:
    """重写 failed_queue.jsonl：移除已重试的条目，追加新失败条目。

    参数：
        archive_root: 归档根目录
        retried:      本次重试过的条目
        new_failed:   本次重试后仍然失败的条目
    """
    from .storage import load_jsonl, overwrite_jsonl

    state_dir = archive_root / "state"
    failed_path = state_dir / "failed_queue.jsonl"
    original = load_jsonl(failed_path)

    retried_urls = {f.canonical_url for f in retried}
    kept = [f for f in original if f.get("canonical_url") not in retried_urls]

    # 把 new_failed 转成 dict
    new_records = [f.model_dump(exclude_none=True) for f in new_failed]
    overwrite_jsonl(failed_path, kept + new_records)
