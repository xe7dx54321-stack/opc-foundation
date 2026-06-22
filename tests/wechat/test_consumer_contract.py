"""Phase 1.7 归档消费契约测试。

覆盖 20 个场景：
1. reader 能读取 articles.jsonl
2. reader 支持 status 过滤
3. reader 支持 account_name 过滤
4. reader 支持 captured_since / captured_until
5. reader 支持 tag 过滤
6. reader 能读取 markdown
7. reader 遇到坏 JSON 行不会整体失败
8. missing articles.jsonl 返回空列表
9. receipt store 能 mark_consumed
10. receipt store 能 mark_skipped
11. receipt store 能 mark_failed
12. receipt store 对同一 article_id append-only，get_receipt 返回最新
13. 不同 consumer 的 receipt 互不影响
14. list_unconsumed_articles 对不同 consumer 结果不同
15. consumer 名称防路径穿越
16. receipt JSONL ensure_ascii=False，中文不乱码
17. CLI list-articles 可运行
18. CLI list-unconsumed 可运行
19. CLI mark-consumed 可运行
20. 不创建全局 consumed 文件
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from opc_foundation.wechat.cli import app
from opc_foundation.wechat.consumer import (
    ConsumerReceiptStore,
    WeChatArchiveReader,
    list_unconsumed_articles,
)
from opc_foundation.wechat.contracts import ArticleRef, ConsumerReceipt


runner = CliRunner()


# ---------------------------------------------------------------------------
# 测试 fixture：构造一个最小的归档目录
# ---------------------------------------------------------------------------


def _make_article_record(
    article_id: str,
    *,
    title: str = "示例标题",
    account_name: str = "示例公众号",
    status: str = "saved",
    captured_at: str = "2026-06-22T10:00:00+08:00",
    published_at: str | None = "2026-06-21T08:00:00+08:00",
    tags: list[str] | None = None,
    markdown_content: str = "# 示例标题\n\n这是正文。",
) -> dict:
    """构造一条 articles.jsonl 记录及对应文件。"""
    return {
        "article_id": article_id,
        "source": "rss:test",
        "account_name": account_name,
        "account_id": "example_a",
        "title": title,
        "url": f"http://example.com/{article_id}",
        "canonical_url": f"http://example.com/canon/{article_id}",
        "published_at": published_at,
        "captured_at": captured_at,
        "author": "作者",
        "digest": "摘要",
        "content_hash": "abc123",
        "status": status,
        "archive_dir": "",  # 由 _build_archive 填充
        "metadata_path": "",  # 由 _build_archive 填充
        "markdown_path": "",  # 由 _build_archive 填充
        "html_path": "",  # 由 _build_archive 填充
        "cover_image_path": None,
        "image_count": 0,
        "error": None,
        "tags": tags or [],
    }


def _build_archive(
    tmp_path: Path,
    records: list[dict],
    *,
    write_markdown: bool = True,
) -> Path:
    """根据 records 列表在 tmp_path/archive 下构造完整归档目录。

    会创建：
    - index/articles.jsonl
    - articles/<id>/metadata.json
    - articles/<id>/article.md（可选）
    """
    root = tmp_path / "archive"
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "articles.jsonl"

    with open(index_path, "w", encoding="utf-8") as fh:
        for rec in records:
            # 创建文章目录
            art_dir = root / "articles" / rec["article_id"]
            art_dir.mkdir(parents=True, exist_ok=True)

            rec["archive_dir"] = str(art_dir)
            rec["metadata_path"] = str(art_dir / "metadata.json")
            rec["markdown_path"] = str(art_dir / "article.md") if write_markdown else None
            rec["html_path"] = str(art_dir / "article.html")

            # 写 metadata.json
            (art_dir / "metadata.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # 写 article.md
            if write_markdown:
                (art_dir / "article.md").write_text(
                    f"# {rec['title']}\n\n这是正文。",
                    encoding="utf-8",
                )

            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return root


# ---------------------------------------------------------------------------
# 1-8: WeChatArchiveReader 测试
# ---------------------------------------------------------------------------


def test_reader_reads_articles_jsonl(tmp_path: Path):
    """1. reader 能读取 articles.jsonl。"""
    records = [
        _make_article_record("wc_001", title="文章一"),
        _make_article_record("wc_002", title="文章二"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    articles = reader.list_articles()

    assert len(articles) == 2
    assert all(isinstance(a, ArticleRef) for a in articles)
    assert {a.article_id for a in articles} == {"wc_001", "wc_002"}


def test_reader_filters_by_status(tmp_path: Path):
    """2. reader 支持 status 过滤。"""
    records = [
        _make_article_record("wc_001", status="saved"),
        _make_article_record("wc_002", status="failed"),
        _make_article_record("wc_003", status="saved"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    saved = reader.list_articles(status="saved")
    failed = reader.list_articles(status="failed")

    assert len(saved) == 2
    assert len(failed) == 1
    assert failed[0].article_id == "wc_002"


def test_reader_filters_by_account_name(tmp_path: Path):
    """3. reader 支持 account_name 过滤。"""
    records = [
        _make_article_record("wc_001", account_name="公众号A"),
        _make_article_record("wc_002", account_name="公众号B"),
        _make_article_record("wc_003", account_name="公众号A"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    a_articles = reader.list_articles(account_name="公众号A")

    assert len(a_articles) == 2
    assert all(a.account_name == "公众号A" for a in a_articles)


def test_reader_filters_by_captured_date_range(tmp_path: Path):
    """4. reader 支持 captured_since / captured_until。"""
    records = [
        _make_article_record("wc_001", captured_at="2026-06-20T10:00:00+08:00"),
        _make_article_record("wc_002", captured_at="2026-06-22T10:00:00+08:00"),
        _make_article_record("wc_003", captured_at="2026-06-24T10:00:00+08:00"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)

    # since 过滤
    since_22 = reader.list_articles(captured_since="2026-06-22")
    assert {a.article_id for a in since_22} == {"wc_002", "wc_003"}

    # until 过滤
    until_22 = reader.list_articles(captured_until="2026-06-22")
    assert {a.article_id for a in until_22} == {"wc_001", "wc_002"}

    # 区间过滤
    range_22 = reader.list_articles(
        captured_since="2026-06-22", captured_until="2026-06-22"
    )
    assert {a.article_id for a in range_22} == {"wc_002"}


def test_reader_filters_by_tag(tmp_path: Path):
    """5. reader 支持 tag 过滤。"""
    records = [
        _make_article_record("wc_001", tags=["live_smoke", "wechat"]),
        _make_article_record("wc_002", tags=["test"]),
        _make_article_record("wc_003", tags=["wechat"]),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    wechat_articles = reader.list_articles(tag="wechat")

    assert len(wechat_articles) == 2
    assert all("wechat" in a.tags for a in wechat_articles)


def test_reader_reads_markdown(tmp_path: Path):
    """6. reader 能读取 markdown。"""
    records = [_make_article_record("wc_001", title="测试标题")]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    article = reader.get_article("wc_001")
    assert article is not None

    md_text = reader.read_markdown(article)
    assert md_text is not None
    assert "测试标题" in md_text

    # 也支持传 article_id 字符串
    md_text2 = reader.read_markdown("wc_001")
    assert md_text2 == md_text


def test_reader_skips_bad_json_lines(tmp_path: Path):
    """7. reader 遇到坏 JSON 行不会整体失败。"""
    root = tmp_path / "archive"
    index_dir = root / "index"
    index_dir.mkdir(parents=True)
    index_path = index_dir / "articles.jsonl"

    # 写入：1 条好记录 + 1 条坏 JSON + 1 条好记录
    good1 = _make_article_record("wc_001")
    good3 = _make_article_record("wc_003")
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(good1, ensure_ascii=False) + "\n")
        fh.write("{bad json line\n")
        fh.write(json.dumps(good3, ensure_ascii=False) + "\n")

    reader = WeChatArchiveReader(root)
    articles = reader.list_articles()

    # 坏行被跳过，2 条好记录正常返回
    assert len(articles) == 2
    assert {a.article_id for a in articles} == {"wc_001", "wc_003"}


def test_reader_missing_index_returns_empty(tmp_path: Path):
    """8. missing articles.jsonl 返回空列表。"""
    root = tmp_path / "nonexistent_archive"

    reader = WeChatArchiveReader(root)
    articles = reader.list_articles()
    assert articles == []

    # get_article 也返回 None
    assert reader.get_article("wc_xxx") is None

    # read_markdown 也返回 None
    assert reader.read_markdown("wc_xxx") is None


# ---------------------------------------------------------------------------
# 9-12: ConsumerReceiptStore 测试
# ---------------------------------------------------------------------------


def test_receipt_store_mark_consumed(tmp_path: Path):
    """9. receipt store 能 mark_consumed。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store = ConsumerReceiptStore(root, consumer="content_agent")
    reader = WeChatArchiveReader(root)
    article = reader.get_article("wc_001")

    receipt = store.mark_consumed(article, decision="example_decision")

    assert isinstance(receipt, ConsumerReceipt)
    assert receipt.consumer == "content_agent"
    assert receipt.article_id == "wc_001"
    assert receipt.status == "consumed"
    assert receipt.decision == "example_decision"
    assert receipt.canonical_url == article.canonical_url
    assert receipt.content_hash == article.content_hash

    # has_receipt / get_receipt
    assert store.has_receipt("wc_001") is True
    got = store.get_receipt("wc_001")
    assert got is not None
    assert got.status == "consumed"


def test_receipt_store_mark_skipped(tmp_path: Path):
    """10. receipt store 能 mark_skipped。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store = ConsumerReceiptStore(root, consumer="content_agent")
    store.mark_skipped("wc_001", reason="不相关")

    receipt = store.get_receipt("wc_001")
    assert receipt is not None
    assert receipt.status == "skipped"
    assert receipt.reason == "不相关"


def test_receipt_store_mark_failed(tmp_path: Path):
    """11. receipt store 能 mark_failed。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store = ConsumerReceiptStore(root, consumer="content_agent")
    store.mark_failed("wc_001", reason="处理异常")

    receipt = store.get_receipt("wc_001")
    assert receipt is not None
    assert receipt.status == "failed"
    assert receipt.reason == "处理异常"


def test_receipt_store_append_only_returns_latest(tmp_path: Path):
    """12. receipt store 对同一 article_id append-only，get_receipt 返回最新。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store = ConsumerReceiptStore(root, consumer="content_agent")

    # 三次 mark，状态变化
    store.mark_consumed("wc_001", decision="first")
    store.mark_failed("wc_001", reason="retry failed")
    store.mark_consumed("wc_001", decision="final")

    # list_receipts 返回全部 3 条
    all_receipts = store.list_receipts()
    assert len(all_receipts) == 3

    # get_receipt 返回最新一条
    latest = store.get_receipt("wc_001")
    assert latest is not None
    assert latest.status == "consumed"
    assert latest.decision == "final"


# ---------------------------------------------------------------------------
# 13-14: per-consumer 隔离测试
# ---------------------------------------------------------------------------


def test_receipt_store_consumer_isolation(tmp_path: Path):
    """13. 不同 consumer 的 receipt 互不影响。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store_a = ConsumerReceiptStore(root, consumer="content_agent")
    store_b = ConsumerReceiptStore(root, consumer="demand_radar")

    # content_agent 标记 consumed
    store_a.mark_consumed("wc_001", decision="selected_for_topic")

    # content_agent 有回执
    assert store_a.has_receipt("wc_001") is True

    # demand_radar 没有回执（隔离）
    assert store_b.has_receipt("wc_001") is False
    assert store_b.get_receipt("wc_001") is None

    # demand_radar 也可以独立标记
    store_b.mark_skipped("wc_001", reason="no_demand_signal")
    assert store_b.has_receipt("wc_001") is True
    assert store_b.get_receipt("wc_001").status == "skipped"

    # content_agent 的回执不受影响
    assert store_a.get_receipt("wc_001").status == "consumed"


def test_list_unconsumed_articles_per_consumer(tmp_path: Path):
    """14. list_unconsumed_articles 对不同 consumer 结果不同。"""
    records = [
        _make_article_record("wc_001"),
        _make_article_record("wc_002"),
        _make_article_record("wc_003"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    store_a = ConsumerReceiptStore(root, consumer="content_agent")
    store_b = ConsumerReceiptStore(root, consumer="demand_radar")

    # content_agent 消费 wc_001
    store_a.mark_consumed("wc_001")

    # content_agent 的未消费列表：wc_002, wc_003
    unconsumed_a = list_unconsumed_articles(reader, store_a)
    assert {a.article_id for a in unconsumed_a} == {"wc_002", "wc_003"}

    # demand_radar 的未消费列表：全部 3 篇（隔离）
    unconsumed_b = list_unconsumed_articles(reader, store_b)
    assert {a.article_id for a in unconsumed_b} == {"wc_001", "wc_002", "wc_003"}


# ---------------------------------------------------------------------------
# 15-16: 安全与编码测试
# ---------------------------------------------------------------------------


def test_consumer_name_prevents_path_traversal(tmp_path: Path):
    """15. consumer 名称防路径穿越。"""
    root = tmp_path / "archive"
    root.mkdir()

    # 各种非法名称都应抛出 ValueError
    bad_names = [
        "../etc/passwd",
        "..",
        "/etc/passwd",
        "Content Agent",  # 大写空格
        "消费者",  # 中文
        "",
        "a" * 100,  # 过长
        ".hidden",
        "name.with.dot",
    ]
    for name in bad_names:
        with pytest.raises(ValueError):
            ConsumerReceiptStore(root, consumer=name)

    # 合法名称不抛异常
    good_names = ["content_agent", "demand_radar", "investment-agent-1", "bot123"]
    for name in good_names:
        store = ConsumerReceiptStore(root, consumer=name)
        assert store.consumer == name


def test_receipt_jsonl_ensure_ascii_false(tmp_path: Path):
    """16. receipt JSONL ensure_ascii=False，中文不乱码。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])

    store = ConsumerReceiptStore(root, consumer="content_agent")
    store.mark_consumed(
        "wc_001",
        reason="这是中文原因",
        decision="中文decision",
        metadata={"key": "中文value"},
    )

    # 直接读文件，确认中文不乱码
    receipts_path = root / "state" / "consumers" / "content_agent.receipts.jsonl"
    assert receipts_path.exists()
    raw_text = receipts_path.read_text(encoding="utf-8")
    assert "这是中文原因" in raw_text
    assert "中文decision" in raw_text
    assert "中文value" in raw_text

    # 确认没有 \u 转义
    assert "\\u" not in raw_text


# ---------------------------------------------------------------------------
# 17-19: CLI 测试
# ---------------------------------------------------------------------------


def test_cli_list_articles(tmp_path: Path):
    """17. CLI list-articles 可运行。"""
    records = [
        _make_article_record("wc_001", title="文章一", status="saved"),
        _make_article_record("wc_002", title="文章二", status="saved"),
    ]
    root = _build_archive(tmp_path, records)

    result = runner.invoke(
        app,
        ["list-articles", "--archive-root", str(root), "--limit", "10"],
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "共 2 篇文章" in result.stdout
    assert "wc_001" in result.stdout
    assert "wc_002" in result.stdout


def test_cli_list_unconsumed(tmp_path: Path):
    """18. CLI list-unconsumed 可运行。"""
    records = [
        _make_article_record("wc_001"),
        _make_article_record("wc_002"),
    ]
    root = _build_archive(tmp_path, records)

    # 先标记 wc_001 为已消费
    store = ConsumerReceiptStore(root, consumer="content_agent")
    store.mark_consumed("wc_001")

    result = runner.invoke(
        app,
        [
            "list-unconsumed",
            "--archive-root", str(root),
            "--consumer", "content_agent",
            "--limit", "10",
        ],
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "共 1 篇未消费文章" in result.stdout
    assert "wc_002" in result.stdout
    assert "wc_001" not in result.stdout


def test_cli_mark_consumed(tmp_path: Path):
    """19. CLI mark-consumed 可运行。"""
    records = [_make_article_record("wc_001")]
    root = _build_archive(tmp_path, records)

    result = runner.invoke(
        app,
        [
            "mark-consumed",
            "--archive-root", str(root),
            "--consumer", "content_agent",
            "--article-id", "wc_001",
            "--decision", "example_decision",
        ],
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "已写入回执" in result.stdout
    assert "content_agent" in result.stdout
    assert "wc_001" in result.stdout

    # 验证文件确实写入
    receipts_path = root / "state" / "consumers" / "content_agent.receipts.jsonl"
    assert receipts_path.exists()
    data = json.loads(receipts_path.read_text(encoding="utf-8").strip())
    assert data["consumer"] == "content_agent"
    assert data["article_id"] == "wc_001"
    assert data["status"] == "consumed"
    assert data["decision"] == "example_decision"


# ---------------------------------------------------------------------------
# 20: 不创建全局 consumed 文件
# ---------------------------------------------------------------------------


def test_no_global_consumed_file(tmp_path: Path):
    """20. 不创建全局 consumed 文件。"""
    records = [
        _make_article_record("wc_001"),
        _make_article_record("wc_002"),
    ]
    root = _build_archive(tmp_path, records)

    # 两个 consumer 分别消费
    store_a = ConsumerReceiptStore(root, consumer="content_agent")
    store_b = ConsumerReceiptStore(root, consumer="demand_radar")
    store_a.mark_consumed("wc_001")
    store_b.mark_consumed("wc_002")

    # 不应该存在全局 consumed 文件
    consumers_dir = root / "state" / "consumers"
    assert consumers_dir.exists()

    # 只应该有 per-consumer 文件
    files = list(consumers_dir.iterdir())
    file_names = {f.name for f in files}
    assert "content_agent.receipts.jsonl" in file_names
    assert "demand_radar.receipts.jsonl" in file_names
    # 不应该有全局文件
    assert "consumed.jsonl" not in file_names
    assert "consumed.json" not in file_names
    assert "all_consumers.jsonl" not in file_names

    # 也不应该在 archive_root 根目录有 consumed 文件
    assert not (root / "consumed.jsonl").exists()
    assert not (root / "consumed.json").exists()
    assert not (root / "state" / "consumed.jsonl").exists()


# ---------------------------------------------------------------------------
# 补充：get_article / read_metadata / raw_metadata 测试
# ---------------------------------------------------------------------------


def test_reader_get_article_by_id(tmp_path: Path):
    """补充：get_article 按 article_id 查找。"""
    records = [
        _make_article_record("wc_001", title="文章一"),
        _make_article_record("wc_002", title="文章二"),
    ]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    found = reader.get_article("wc_002")
    assert found is not None
    assert found.title == "文章二"

    not_found = reader.get_article("wc_999")
    assert not_found is None


def test_reader_read_metadata(tmp_path: Path):
    """补充：read_metadata 返回完整 metadata dict。"""
    records = [_make_article_record("wc_001", title="测试")]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    metadata = reader.read_metadata("wc_001")
    assert metadata is not None
    assert metadata["article_id"] == "wc_001"
    assert metadata["title"] == "测试"


def test_article_ref_raw_metadata_preserved(tmp_path: Path):
    """补充：ArticleRef.raw_metadata 保留完整原始 dict。"""
    records = [_make_article_record("wc_001", title="测试")]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    articles = reader.list_articles()
    assert len(articles) == 1

    a = articles[0]
    assert a.raw_metadata["article_id"] == "wc_001"
    assert a.raw_metadata["title"] == "测试"
    # raw_metadata 应该包含全部字段
    assert "url" in a.raw_metadata
    assert "canonical_url" in a.raw_metadata


def test_article_ref_is_frozen(tmp_path: Path):
    """补充：ArticleRef 是 frozen dataclass，不可变。"""
    records = [_make_article_record("wc_001")]
    root = _build_archive(tmp_path, records)

    reader = WeChatArchiveReader(root)
    a = reader.list_articles()[0]

    # 尝试修改应抛出 FrozenInstanceError
    with pytest.raises(Exception):
        a.title = "modified"  # type: ignore[misc]


def test_invalid_receipt_status_raises(tmp_path: Path):
    """补充：非法 status 抛出 ValueError。"""
    root = _build_archive(tmp_path, [_make_article_record("wc_001")])
    store = ConsumerReceiptStore(root, consumer="content_agent")

    with pytest.raises(ValueError):
        store._append_receipt("wc_001", status="invalid_status")
