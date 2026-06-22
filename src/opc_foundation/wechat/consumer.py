"""微信文章归档消费契约的实现：Archive Reader + Consumer Receipt Store。

功能说明（小白解读）：
    本文件提供两个核心类和一个辅助函数：
    - WeChatArchiveReader: 只读读取归档目录，返回 ArticleRef 列表
    - ConsumerReceiptStore: 每个业务线独立的消费回执存储（per-consumer JSONL）
    - list_unconsumed_articles: 返回某个 consumer 还没消费过的文章

设计原则（与 contracts.py 一致）：
    1. foundation 不做业务判断
    2. 不做全局 consumed（每个 consumer 独立）
    3. Reader 只读，不修改任何归档文件
    4. ReceiptStore append-only，便于审计
    5. consumer 名称安全化，防路径穿越
    6. 坏 JSON 行不导致整体失败（fail-soft）
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..run.time_utils import utcnow_iso
from .contracts import (
    ArticleRef,
    ConsumerReceipt,
    RECEIPT_STATUS_CONSUMED,
    RECEIPT_STATUS_FAILED,
    RECEIPT_STATUS_SKIPPED,
    VALID_RECEIPT_STATUSES,
)


# ---------------------------------------------------------------------------
# consumer 名称安全化
# ---------------------------------------------------------------------------

# 只允许小写字母、数字、下划线、短横线，长度 1-64
_CONSUMER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _validate_consumer_name(consumer: str) -> str:
    """校验并返回安全的 consumer 名称。

    参数：
        consumer: 业务消费者名称（例如 'content_agent'）

    返回值：
        通过校验的 consumer 名称（原样返回）

    异常处理：
        如果名称不合法（含路径穿越字符、为空、过长等），抛出 ValueError

    为什么这么做：
        consumer 名称会直接拼到文件名（如 content_agent.receipts.jsonl），
        必须防止 '../' 或 '/' 等字符导致路径穿越攻击。
    """
    if not consumer or not isinstance(consumer, str):
        raise ValueError("consumer 名称不能为空")
    if not _CONSUMER_NAME_RE.match(consumer):
        raise ValueError(
            f"consumer 名称不合法: {consumer!r}（只允许小写字母、数字、下划线、短横线，"
            "且必须以字母或数字开头，长度 1-64）"
        )
    # 额外防御：禁止 '..' 序列
    if ".." in consumer:
        raise ValueError(f"consumer 名称不能包含 '..': {consumer!r}")
    return consumer


# ---------------------------------------------------------------------------
# WeChatArchiveReader：只读归档读取器
# ---------------------------------------------------------------------------


class WeChatArchiveReader:
    """只读读取微信文章归档目录，返回 ArticleRef 列表。

    使用方式：
        reader = WeChatArchiveReader("./data/wechat_archive")
        articles = reader.list_articles(status="saved", captured_since="2026-06-22")
        article = reader.get_article("wc_xxx")
        md_text = reader.read_markdown(article)

    重要原则：
        - 完全只读：不修改任何归档文件
        - fail-soft：坏 JSON 行跳过，不抛异常
        - 不读取 SQLite seen store（那是 foundation 内部去重用的）
        - 默认读取 archive_root/index/articles.jsonl
    """

    def __init__(self, archive_root: str | Path) -> None:
        """初始化 Reader。

        参数：
            archive_root: 归档根目录路径（包含 index/articles.jsonl）

        异常处理：
            如果目录不存在，不立即报错；list_articles 会返回空列表
            （fail-soft 原则，便于新 archive 还没生成时也能调用）
        """
        self.root = Path(archive_root)
        self._index_path = self.root / "index" / "articles.jsonl"

    # ------------------------------------------------------------------
    # 内部：解析一行 JSON 为 ArticleRef
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_article_ref(data: dict[str, Any]) -> ArticleRef:
        """把 articles.jsonl 的一行 dict 转成 ArticleRef。

        参数：
            data: 从 JSON 解析出来的 dict

        返回值：
            ArticleRef 实例

        异常处理：
            如果关键字段缺失，抛出 KeyError/ValueError，由调用方决定跳过

        设计要点：
            - tags 字段在 articles.jsonl 中可能不存在（旧版本兼容），默认空列表
            - raw_metadata 保留完整原始 dict
        """
        # 必需字段（缺失则视为坏记录）
        article_id = data["article_id"]
        title = data["title"]
        url = data["url"]
        canonical_url = data["canonical_url"]
        captured_at = data["captured_at"]
        status = data.get("status", "saved")
        archive_dir = data.get("archive_dir", "")
        metadata_path = data.get("metadata_path", "")

        return ArticleRef(
            article_id=article_id,
            source=data.get("source", ""),
            account_name=data.get("account_name"),
            account_id=data.get("account_id"),
            title=title,
            url=url,
            canonical_url=canonical_url,
            published_at=data.get("published_at"),
            captured_at=captured_at,
            status=status,
            content_hash=data.get("content_hash", ""),
            archive_dir=archive_dir,
            metadata_path=metadata_path,
            markdown_path=data.get("markdown_path"),
            html_path=data.get("html_path"),
            tags=list(data.get("tags") or []),
            raw_metadata=dict(data),
        )

    # ------------------------------------------------------------------
    # 读取 articles.jsonl
    # ------------------------------------------------------------------

    def _iter_raw_records(self) -> list[dict[str, Any]]:
        """读取 articles.jsonl 所有行，返回 dict 列表。

        返回值：
            成功解析的 dict 列表（坏行被跳过，不抛异常）

        异常处理：
            - 文件不存在：返回空列表
            - 单行 JSON 解析失败：跳过该行，继续读下一行
            - 关键字段缺失：跳过该行
        """
        if not self._index_path.exists():
            return []

        out: list[dict[str, Any]] = []
        try:
            with open(self._index_path, encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        # 坏 JSON 行：跳过，不中断整体读取
                        continue
                    if not isinstance(data, dict):
                        continue
                    # 必需字段检查
                    if not all(
                        k in data for k in ("article_id", "title", "url", "canonical_url", "captured_at")
                    ):
                        continue
                    out.append(data)
        except OSError:
            # 文件读取异常（权限等）：返回已读到的部分
            return out
        return out

    # ------------------------------------------------------------------
    # list_articles：带过滤的列表读取
    # ------------------------------------------------------------------

    def list_articles(
        self,
        status: str | None = None,
        account_name: str | None = None,
        tag: str | None = None,
        captured_since: str | None = None,
        captured_until: str | None = None,
        published_since: str | None = None,
        published_until: str | None = None,
        limit: int | None = None,
    ) -> list[ArticleRef]:
        """读取归档文章列表，支持多种过滤条件。

        参数：
            status:          按状态过滤（saved / partial / duplicate / failed）
            account_name:    按公众号名过滤（精确匹配）
            tag:             按标签过滤（文章 tags 列表中包含该标签）
            captured_since:  captured_at >= 该日期（字符串前缀比较，如 '2026-06-22'）
            captured_until:  captured_at <= 该日期
            published_since: published_at >= 该日期
            published_until: published_at <= 该日期
            limit:           最多返回多少条（None 表示不限制）

        返回值：
            ArticleRef 列表（按 articles.jsonl 中的顺序）

        异常处理：
            - 坏 JSON 行跳过
            - 文件不存在返回空列表
            - 单条记录字段缺失跳过

        日期比较说明：
            使用字符串前缀比较，所以 '2026-06-22' 会匹配 '2026-06-22T10:00:00+08:00'。
            传入的日期字符串应该用 'YYYY-MM-DD' 或 'YYYY-MM-DDTHH:MM:SS' 格式。
        """
        records = self._iter_raw_records()
        out: list[ArticleRef] = []
        for data in records:
            try:
                ref = self._parse_article_ref(data)
            except (KeyError, ValueError, TypeError):
                continue

            # status 过滤
            if status is not None and ref.status != status:
                continue
            # account_name 过滤
            if account_name is not None and ref.account_name != account_name:
                continue
            # tag 过滤
            if tag is not None and tag not in ref.tags:
                continue
            # captured_at 日期范围过滤
            if not _date_in_range(ref.captured_at, captured_since, captured_until):
                continue
            # published_at 日期范围过滤（None 视为不在范围内，除非过滤条件也为 None）
            if not _date_in_range(ref.published_at, published_since, published_until):
                continue

            out.append(ref)
            if limit is not None and len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------
    # get_article：按 article_id 查找
    # ------------------------------------------------------------------

    def get_article(self, article_id: str) -> ArticleRef | None:
        """按 article_id 查找单篇文章。

        参数：
            article_id: 文章唯一 ID

        返回值：
            找到则返回 ArticleRef，否则返回 None

        异常处理：
            - 文件不存在：返回 None
            - 坏 JSON 行：跳过
        """
        records = self._iter_raw_records()
        for data in records:
            if data.get("article_id") == article_id:
                try:
                    return self._parse_article_ref(data)
                except (KeyError, ValueError, TypeError):
                    return None
        return None

    # ------------------------------------------------------------------
    # read_markdown / read_metadata：读取正文与元数据
    # ------------------------------------------------------------------

    def read_markdown(self, article: ArticleRef | str) -> str | None:
        """读取文章的 Markdown 正文。

        参数：
            article: ArticleRef 实例或 article_id 字符串

        返回值：
            Markdown 文本；文件不存在或读取失败返回 None

        异常处理：
            - article_id 找不到：返回 None
            - markdown_path 为 None：返回 None
            - 文件不存在：返回 None
        """
        ref = self._resolve_ref(article)
        if ref is None or ref.markdown_path is None:
            return None
        md_path = Path(ref.markdown_path)
        if not md_path.exists():
            return None
        try:
            return md_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def read_metadata(self, article: ArticleRef | str) -> dict[str, Any] | None:
        """读取文章的完整 metadata.json。

        参数：
            article: ArticleRef 实例或 article_id 字符串

        返回值：
            metadata dict；文件不存在或解析失败返回 None
        """
        ref = self._resolve_ref(article)
        if ref is None or not ref.metadata_path:
            return None
        meta_path = Path(ref.metadata_path)
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _resolve_ref(self, article: ArticleRef | str) -> ArticleRef | None:
        """把 ArticleRef 或 article_id 统一解析为 ArticleRef。"""
        if isinstance(article, ArticleRef):
            return article
        return self.get_article(article)


# ---------------------------------------------------------------------------
# 日期范围过滤辅助函数
# ---------------------------------------------------------------------------


def _date_in_range(
    value: str | None,
    since: str | None,
    until: str | None,
) -> bool:
    """判断日期字符串是否在 [since, until] 范围内。

    参数：
        value: 待判断的日期字符串（如 '2026-06-22T10:00:00+08:00'），可能为 None
        since: 起始日期（前缀，如 '2026-06-22'），None 表示不限制下界
        until: 结束日期（前缀，如 '2026-06-22'），None 表示不限制上界

    返回值：
        True 表示在范围内（或无范围限制）

    设计要点：
        - 使用字符串前缀比较：'2026-06-22' <= '2026-06-22T10:00:00+08:00' <= '2026-06-22'
          需要特殊处理（用 startswith 或扩展 until 到当天末尾）
        - value 为 None 时：如果 since/until 都为 None，返回 True；否则返回 False
    """
    if since is None and until is None:
        return True
    if value is None:
        return False
    # 截取到与 since/until 相同长度做比较
    if since is not None:
        # value 必须以 since 开头或字典序大于 since
        # 例如 since='2026-06-22', value='2026-06-22T10:00:00' 应通过
        # value='2026-06-21T...' 应不通过
        v_prefix = value[: len(since)]
        if v_prefix < since:
            return False
    if until is not None:
        # value 必须以 until 开头或字典序小于等于 until
        # 例如 until='2026-06-22', value='2026-06-22T10:00:00' 应通过
        # value='2026-06-23...' 应不通过
        v_prefix = value[: len(until)]
        if v_prefix > until:
            return False
    return True


# ---------------------------------------------------------------------------
# ConsumerReceiptStore：per-consumer 消费回执存储
# ---------------------------------------------------------------------------


class ConsumerReceiptStore:
    """某个业务线对归档文章的消费回执存储。

    使用方式：
        store = ConsumerReceiptStore("./data/wechat_archive", consumer="content_agent")
        if not store.has_receipt(article.article_id):
            store.mark_consumed(article, decision="example_decision")
        receipt = store.get_receipt(article.article_id)

    重要原则：
        - 每个 consumer 一个独立 JSONL 文件（archive_root/state/consumers/<consumer>.receipts.jsonl）
        - append-only：同一文章多次 mark 保留全部历史，读取时取最后一条
        - status 只允许 consumed / skipped / failed
        - decision / metadata 对 foundation 是 opaque（不解释、不校验）
        - 不修改 articles.jsonl 或 metadata.json
        - 不做全局 consumed
    """

    def __init__(self, archive_root: str | Path, consumer: str) -> None:
        """初始化 ReceiptStore。

        参数：
            archive_root: 归档根目录路径
            consumer:     业务消费者名称（必须通过 _validate_consumer_name 校验）

        异常处理：
            consumer 名称不合法时抛出 ValueError
        """
        self.root = Path(archive_root)
        self.consumer = _validate_consumer_name(consumer)
        # receipts 文件路径：archive_root/state/consumers/<consumer>.receipts.jsonl
        self._receipts_dir = self.root / "state" / "consumers"
        self._receipts_path = self._receipts_dir / f"{self.consumer}.receipts.jsonl"

    # ------------------------------------------------------------------
    # 内部：读取所有 receipts
    # ------------------------------------------------------------------

    def _iter_raw_receipts(self) -> list[dict[str, Any]]:
        """读取 receipts JSONL 所有行，返回 dict 列表。

        返回值：
            成功解析的 dict 列表（坏行跳过）

        异常处理：
            文件不存在返回空列表；坏 JSON 行跳过
        """
        if not self._receipts_path.exists():
            return []
        out: list[dict[str, Any]] = []
        try:
            with open(self._receipts_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(data, dict):
                        out.append(data)
        except OSError:
            return out
        return out

    @staticmethod
    def _dict_to_receipt(data: dict[str, Any]) -> ConsumerReceipt | None:
        """把 dict 转成 ConsumerReceipt，字段缺失返回 None。"""
        try:
            return ConsumerReceipt(
                consumer=data["consumer"],
                article_id=data["article_id"],
                canonical_url=data.get("canonical_url"),
                content_hash=data.get("content_hash"),
                status=data["status"],
                received_at=data["received_at"],
                reason=data.get("reason"),
                decision=data.get("decision"),
                metadata=dict(data.get("metadata") or {}),
            )
        except (KeyError, ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # list_receipts：列出所有回执
    # ------------------------------------------------------------------

    def list_receipts(self) -> list[ConsumerReceipt]:
        """列出该 consumer 的所有回执（按写入顺序）。

        返回值：
            ConsumerReceipt 列表（包含历史记录，可能有多条同一 article_id）
        """
        return [
            r
            for r in (self._dict_to_receipt(d) for d in self._iter_raw_receipts())
            if r is not None
        ]

    # ------------------------------------------------------------------
    # has_receipt / get_receipt：基于"最新"状态判断
    # ------------------------------------------------------------------

    def _latest_receipt_index(self) -> dict[str, ConsumerReceipt]:
        """返回 {article_id: 最新 ConsumerReceipt} 的字典。

        同一 article_id 多次 mark 时，取最后一条作为当前状态。
        """
        latest: dict[str, ConsumerReceipt] = {}
        for receipt in self.list_receipts():
            latest[receipt.article_id] = receipt
        return latest

    def has_receipt(self, article_id: str) -> bool:
        """判断该 consumer 是否对指定文章有回执（任何状态都算）。

        参数：
            article_id: 文章唯一 ID

        返回值：
            True 表示该 consumer 已记录过该文章（consumed/skipped/failed 任一状态）
        """
        return article_id in self._latest_receipt_index()

    def get_receipt(self, article_id: str) -> ConsumerReceipt | None:
        """获取该 consumer 对指定文章的最新回执。

        参数：
            article_id: 文章唯一 ID

        返回值：
            最新 ConsumerReceipt；如果没有回执返回 None
        """
        return self._latest_receipt_index().get(article_id)

    # ------------------------------------------------------------------
    # mark_consumed / mark_skipped / mark_failed
    # ------------------------------------------------------------------

    def _append_receipt(
        self,
        article: ArticleRef | str,
        *,
        status: str,
        canonical_url: str | None = None,
        content_hash: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConsumerReceipt:
        """内部：追加一条回执到 JSONL。

        参数：
            article:       ArticleRef 或 article_id 字符串
            status:        通用状态（必须通过校验）
            canonical_url: 可选，辅助追踪（若 article 是 ArticleRef 且未传则自动取）
            content_hash:  可选，辅助检测内容变化
            decision:      业务判断（opaque）
            reason:        可读原因
            metadata:      业务自定义信息（opaque）

        返回值：
            写入的 ConsumerReceipt 实例

        异常处理：
            status 不合法抛出 ValueError
        """
        if status not in VALID_RECEIPT_STATUSES:
            raise ValueError(
                f"status 不合法: {status!r}（只允许 {sorted(VALID_RECEIPT_STATUSES)}）"
            )

        # 解析 article_id 和辅助字段
        if isinstance(article, ArticleRef):
            article_id = article.article_id
            if canonical_url is None:
                canonical_url = article.canonical_url
            if content_hash is None:
                content_hash = article.content_hash or None
        else:
            article_id = str(article)

        receipt = ConsumerReceipt(
            consumer=self.consumer,
            article_id=article_id,
            canonical_url=canonical_url,
            content_hash=content_hash,
            status=status,
            received_at=utcnow_iso(),
            reason=reason,
            decision=decision,
            metadata=dict(metadata or {}),
        )

        # 写入 JSONL（append-only，UTF-8，ensure_ascii=False）
        self._receipts_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "consumer": receipt.consumer,
                "article_id": receipt.article_id,
                "canonical_url": receipt.canonical_url,
                "content_hash": receipt.content_hash,
                "status": receipt.status,
                "received_at": receipt.received_at,
                "reason": receipt.reason,
                "decision": receipt.decision,
                "metadata": receipt.metadata,
            },
            ensure_ascii=False,
        )
        with open(self._receipts_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        return receipt

    def mark_consumed(
        self,
        article: ArticleRef | str,
        *,
        canonical_url: str | None = None,
        content_hash: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConsumerReceipt:
        """标记一篇文章为已消费（consumed）。

        参数：
            article:       ArticleRef 或 article_id 字符串
            canonical_url: 可选，辅助追踪
            content_hash:  可选，辅助检测内容变化
            decision:      业务判断（opaque，foundation 不解释）
            reason:        可读原因
            metadata:      业务自定义信息（opaque）

        返回值：
            写入的 ConsumerReceipt 实例
        """
        return self._append_receipt(
            article,
            status=RECEIPT_STATUS_CONSUMED,
            canonical_url=canonical_url,
            content_hash=content_hash,
            decision=decision,
            reason=reason,
            metadata=metadata,
        )

    def mark_skipped(
        self,
        article: ArticleRef | str,
        *,
        canonical_url: str | None = None,
        content_hash: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConsumerReceipt:
        """标记一篇文章为已跳过（skipped）。

        语义：consumer 主动决定不处理这篇文章（例如业务线判断不相关）。
        foundation 不解释 decision 字段。
        """
        return self._append_receipt(
            article,
            status=RECEIPT_STATUS_SKIPPED,
            canonical_url=canonical_url,
            content_hash=content_hash,
            decision=decision,
            reason=reason,
            metadata=metadata,
        )

    def mark_failed(
        self,
        article: ArticleRef | str,
        *,
        canonical_url: str | None = None,
        content_hash: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConsumerReceipt:
        """标记一篇文章为消费失败（failed）。

        语义：consumer 尝试处理但失败了（例如下游系统异常）。
        可用于业务线自己的重试逻辑。
        """
        return self._append_receipt(
            article,
            status=RECEIPT_STATUS_FAILED,
            canonical_url=canonical_url,
            content_hash=content_hash,
            decision=decision,
            reason=reason,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# list_unconsumed_articles：返回某 consumer 还没消费过的文章
# ---------------------------------------------------------------------------


def list_unconsumed_articles(
    reader: WeChatArchiveReader,
    receipt_store: ConsumerReceiptStore,
    **filters: Any,
) -> list[ArticleRef]:
    """返回某个 consumer 还没有回执的归档文章。

    参数：
        reader:        WeChatArchiveReader 实例
        receipt_store: ConsumerReceiptStore 实例（决定按哪个 consumer 过滤）
        **filters:     透传给 reader.list_articles 的过滤条件
                       （status / account_name / tag / captured_since 等）

    返回值：
        ArticleRef 列表（该 consumer 还没消费过的文章）

    设计要点：
        - 只按当前 consumer 的 receipt 判断
        - content_agent consume 过，不影响 demand_radar
        - 不做业务判断（不评估文章价值）
        - has_receipt 为 True 的文章（无论 consumed/skipped/failed）都被排除
          如果业务线想重新处理 failed 的文章，可以新建一个 consumer 或
          自行管理（foundation 不强制）
    """
    # 先拿到该 consumer 所有有回执的 article_id
    consumed_ids = set(receipt_store._latest_receipt_index().keys())

    articles = reader.list_articles(**filters)
    return [a for a in articles if a.article_id not in consumed_ids]
