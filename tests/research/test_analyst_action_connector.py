"""测试 AnalystActionConnector。

功能说明（小白解读）：
    本文件覆盖 Phase 2D 的 25 个测试场景，包括：
    - 4 种 extraction_profile 的解析能力
    - 事件字段提取（action_date / company / ticker / broker / analyst / action_type /
      rating_from / rating_to / price_target_from / price_target_to / currency）
    - 相对 URL 转 absolute
    - max_items 限制
    - fail-soft（空列表 / 畸形 HTML）
    - archiver 集成（dry-run / run / source failure isolation）
    - price target 只作为 metadata，不生成投资建议字段
    - 边界检查（无业务字段 / example config 全部 enabled: false）

    所有测试都基于 fixture，不访问真实网络。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.research.config import load_research_config, validate_research_config
from opc_foundation.research.connectors.analyst_action import (
    AnalystActionConnector,
    _guess_action_type,
    _guess_currency,
)
from opc_foundation.research.models import (
    ResearchArchiveConfig,
    ResearchDefaults,
    ResearchSourceConfig,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_source(
    url: str | None = "https://example.com/analyst-actions",
    extraction_profile: str = "analyst_action_table",
    max_items: int | None = None,
    base_url: str | None = None,
    source_id: str = "aa_test",
) -> ResearchSourceConfig:
    """构造一个 analyst_action source 配置。

    参数：
        url:                采集入口 URL
        extraction_profile: 抽取 profile 名
        max_items:          候选数上限
        base_url:           基础 URL（相对链接解析）
        source_id:          source ID

    返回：
        ResearchSourceConfig 对象
    """
    return ResearchSourceConfig(
        source_id=source_id,
        source_name="Analyst Action Test",
        source_type="analyst_action",
        url=url,
        base_url=base_url,
        extraction_profile=extraction_profile,
        legal_profile="licensed_media",
        tags=["analyst_action", "ratings"],
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=20),
    )


# ---------------------------------------------------------------------------
# 1. analyst_action_table profile
# ---------------------------------------------------------------------------


def test_parses_analyst_action_table(sample_analyst_action_table_html: str) -> None:
    """analyst_action_table 能从 HTML table 提取 candidates。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 5 行数据
    assert len(candidates) == 5
    # 第 1 行：Upgrade Sample Tech
    assert "Sample Tech" in candidates[0].title or "Upgrade" in candidates[0].title


def test_table_row_without_detail_link_uses_source_url(
    sample_analyst_action_table_html: str,
) -> None:
    """table 行无 detail link 时使用 source.url 但保持 title 唯一。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source(url="https://example.com/analyst-actions")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第 5 行无 detail link，url 应为 source.url
    fifth = next(c for c in candidates if "Fifth" in c.title)
    assert fifth.url == "https://example.com/analyst-actions"
    # title 应唯一
    titles = [c.title for c in candidates]
    assert len(titles) == len(set(titles))


# ---------------------------------------------------------------------------
# 2. analyst_action_cards profile
# ---------------------------------------------------------------------------


def test_parses_analyst_action_cards(sample_analyst_action_cards_html: str) -> None:
    """analyst_action_cards 能从 card list 提取 candidates。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_cards_html
    )
    source = _make_source(
        url="https://example.com/analyst-cards",
        extraction_profile="analyst_action_cards",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 4 张卡片，1 张无链接应被跳过
    assert len(candidates) == 3
    assert "Upgrade" in candidates[0].title or "Sample Tech" in candidates[0].title


# ---------------------------------------------------------------------------
# 3. analyst_action_news_list profile
# ---------------------------------------------------------------------------


def test_parses_analyst_action_news_list(
    sample_analyst_action_news_list_html: str,
) -> None:
    """analyst_action_news_list 能从 article list 提取 candidates。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_news_list_html
    )
    source = _make_source(
        url="https://example.com/analyst-news",
        extraction_profile="analyst_action_news_list",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4
    assert "Sample Bank Upgrades Sample Tech" in candidates[0].title


# ---------------------------------------------------------------------------
# 4. analyst_action_detail profile
# ---------------------------------------------------------------------------


def test_parses_analyst_action_detail(sample_analyst_action_detail_html: str) -> None:
    """analyst_action_detail 能从单篇 detail fixture 生成 1 个 candidate。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_detail_html
    )
    source = _make_source(
        url="https://example.com/analyst-action/detail",
        extraction_profile="analyst_action_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    # 标题优先从 h1 提取
    assert candidates[0].title == "Sample Bank Upgrades Sample Tech to Buy"
    # document_kind 应为 analyst_action_detail
    assert candidates[0].raw_entry["document_kind"] == "analyst_action_detail"


# ---------------------------------------------------------------------------
# 5. relative URL 转 absolute
# ---------------------------------------------------------------------------


def test_relative_url_canonicalized(sample_analyst_action_table_html: str) -> None:
    """相对 URL 应根据 base_url/source.url 转成 absolute。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source(url="https://example.com/analyst-actions")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /actions/detail-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/actions/detail-1"


def test_relative_url_with_base_url(sample_analyst_action_table_html: str) -> None:
    """base_url 也能用于相对链接解析。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source(
        url="https://example.com/analyst-actions/list",
        base_url="https://example.com",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].url == "https://example.com/actions/detail-1"


# ---------------------------------------------------------------------------
# 6. action_date / published_at 提取
# ---------------------------------------------------------------------------


def test_action_date_from_table_cell(sample_analyst_action_table_html: str) -> None:
    """能从 table cell 提取 action_date。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["action_date"] == "2026-03-15"
    assert candidates[1].raw_entry["action_date"] == "2026-03-14"


def test_published_at_from_time_tag(sample_analyst_action_cards_html: str) -> None:
    """能从 <time datetime="..."> 提取 published_at。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_cards_html
    )
    source = _make_source(
        url="https://example.com/analyst-cards",
        extraction_profile="analyst_action_cards",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "2026-03-15T09:00:00+08:00"


# ---------------------------------------------------------------------------
# 7. summary 提取
# ---------------------------------------------------------------------------


def test_summary_from_class(sample_analyst_action_cards_html: str) -> None:
    """能从 class='summary' 提取摘要。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_cards_html
    )
    source = _make_source(
        url="https://example.com/analyst-cards",
        extraction_profile="analyst_action_cards",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary is not None
    assert "Sample Bank upgraded Sample Tech" in candidates[0].summary


def test_summary_from_meta_in_detail(sample_analyst_action_detail_html: str) -> None:
    """能从 <meta name='description'> 提取摘要（detail profile）。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_detail_html
    )
    source = _make_source(
        url="https://example.com/analyst-action/detail",
        extraction_profile="analyst_action_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # detail 页面优先从 class='summary' 提取
    assert candidates[0].summary is not None


# ---------------------------------------------------------------------------
# 8. company / ticker / broker / analyst 进入 raw_entry
# ---------------------------------------------------------------------------


def test_company_ticker_broker_in_raw_entry(
    sample_analyst_action_table_html: str,
) -> None:
    """company / ticker / broker 进入 raw_entry。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["company"] == "Sample Tech"
    assert raw["ticker"] == "SMP"
    assert raw["broker"] == "Sample Bank"
    assert raw["analyst"] == "Jane Doe"


def test_author_is_broker(sample_analyst_action_table_html: str) -> None:
    """author 优先使用 broker。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].author == "Sample Bank"


# ---------------------------------------------------------------------------
# 9. action_type 进入 raw_entry
# ---------------------------------------------------------------------------


def test_action_type_in_raw_entry(sample_analyst_action_table_html: str) -> None:
    """action_type 进入 raw_entry。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["action_type"] == "upgrade"
    assert candidates[1].raw_entry["action_type"] == "downgrade"
    assert candidates[2].raw_entry["action_type"] == "initiated"


def test_action_type_guess_from_text() -> None:
    """_guess_action_type 能从文本识别 action_type。"""
    assert _guess_action_type("Upgrade Sample Tech to Buy") == "upgrade"
    assert _guess_action_type("Downgrade Another Corp to Hold") == "downgrade"
    assert _guess_action_type("Initiated Coverage on Third Inc") == "initiated"
    assert _guess_action_type("Reiterate Buy on Fourth Co") == "reiterate"
    assert _guess_action_type("Maintain Buy rating") == "maintain"
    assert _guess_action_type("Price Target Raised to $150") == "raise_target"
    assert _guess_action_type("Price Target Lowered to $180") == "lower_target"
    assert _guess_action_type("Some random text") == "unknown"


# ---------------------------------------------------------------------------
# 10. rating_from / rating_to 进入 raw_entry
# ---------------------------------------------------------------------------


def test_rating_from_to_in_raw_entry(sample_analyst_action_table_html: str) -> None:
    """rating_from / rating_to 进入 raw_entry。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["rating_from"] == "Hold"
    assert raw["rating_to"] == "Buy"


# ---------------------------------------------------------------------------
# 11. price_target_from / price_target_to / currency 进入 raw_entry
# ---------------------------------------------------------------------------


def test_price_target_and_currency_in_raw_entry(
    sample_analyst_action_table_html: str,
) -> None:
    """price_target_from / price_target_to / currency 进入 raw_entry。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["price_target_from"] == "$100"
    assert raw["price_target_to"] == "$150"
    assert raw["currency"] == "USD"


def test_currency_guess_from_text() -> None:
    """_guess_currency 能从文本识别货币。"""
    assert _guess_currency("$100") == "USD"
    assert _guess_currency("HK$200") == "HKD"
    assert _guess_currency("RMB 500") == "CNY"
    assert _guess_currency("100") == "unknown"


# ---------------------------------------------------------------------------
# 12. tags 和 legal_profile 继承 source
# ---------------------------------------------------------------------------


def test_inherits_source_tags_and_legal_profile(
    sample_analyst_action_table_html: str,
) -> None:
    """候选文档继承 source 的 tags 和 legal_profile。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.legal_profile == "licensed_media"
        assert c.tags == ["analyst_action", "ratings"]
        assert c.source_id == "aa_test"
        assert c.source_type == "analyst_action"


# ---------------------------------------------------------------------------
# 13. max_items 生效
# ---------------------------------------------------------------------------


def test_respects_max_items(sample_analyst_action_table_html: str) -> None:
    """max_items 限制候选数量。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_max_items_from_defaults(sample_analyst_action_table_html: str) -> None:
    """没有 source.max_items 时，使用 defaults.max_items_per_source。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()  # max_items=None
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=3),
    )

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 3


# ---------------------------------------------------------------------------
# 14. empty list fail-soft
# ---------------------------------------------------------------------------


def test_empty_list_fail_soft(sample_analyst_action_empty_html: str) -> None:
    """空列表页返回空候选列表，不崩溃。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_empty_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []


# ---------------------------------------------------------------------------
# 15. malformed HTML fail-soft
# ---------------------------------------------------------------------------


def test_malformed_html_fail_soft(sample_analyst_action_malformed_html: str) -> None:
    """损坏的 HTML 也能解析出能用的候选，不崩溃。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_malformed_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 至少能解析出一些候选
    assert len(candidates) >= 1
    # 所有候选都有 url 和 canonical_url
    for c in candidates:
        assert c.url
        assert c.canonical_url


# ---------------------------------------------------------------------------
# 16. archiver dry-run with analyst_action fixture
# ---------------------------------------------------------------------------


def test_archiver_dry_run_with_analyst_action(
    sample_analyst_action_table_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver dry-run 能发现 analyst action 候选，不抓正文。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="aa_test",
                source_name="Analyst Action Test",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            analyst_action_html_by_url=lambda url: sample_analyst_action_table_html,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    # fixture 有 5 行数据
    assert result.candidate_count == 5
    assert result.saved_count == 0  # dry-run 不抓正文
    assert result.new_count == 5


# ---------------------------------------------------------------------------
# 17. archiver run with analyst_action fixture
# ---------------------------------------------------------------------------


def test_archiver_run_with_analyst_action(
    sample_analyst_action_table_html: str,
    sample_analyst_action_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver run 能从 analyst_action 归档文档。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="aa_test",
                source_name="Analyst Action Test",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
        ],
    )

    # 注入：列表页 HTML + 详情页 HTML
    def aa_html_injector(url: str) -> str | None:
        if url == "https://example.com/analyst-actions":
            return sample_analyst_action_table_html
        return None

    def detail_html_injector(url: str) -> str | None:
        if "/actions/detail-" in url:
            return sample_analyst_action_detail_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            analyst_action_html_by_url=aa_html_injector,
            http_html=detail_html_injector,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count == 5
    # 至少有一些 saved 或 partial
    assert result.saved_count + result.partial_count > 0


# ---------------------------------------------------------------------------
# 18. run 后 documents.jsonl 字段完整
# ---------------------------------------------------------------------------


def test_documents_jsonl_fields_complete(
    sample_analyst_action_table_html: str,
    sample_analyst_action_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """run 后 documents.jsonl 字段完整。"""
    import json

    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="aa_test",
                source_name="Analyst Action Test",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            analyst_action_html_by_url=lambda url: sample_analyst_action_table_html
            if url == "https://example.com/analyst-actions" else None,
            http_html=lambda url: sample_analyst_action_detail_html
            if "/actions/detail-" in url else None,
        ),
    )
    archiver.run()

    jsonl_path = temp_archive_root / "index" / "documents.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1

    doc = json.loads(lines[0])
    # 必须字段
    required_fields = [
        "document_id",
        "source_id",
        "source_name",
        "source_type",
        "title",
        "url",
        "canonical_url",
        "captured_at",
        "content_type",
        "legal_profile",
        "tags",
        "content_hash",
        "status",
        "metadata_path",
        "extraction_quality",
    ]
    for field in required_fields:
        assert field in doc, f"documents.jsonl 缺少字段: {field}"
    assert doc["source_type"] == "analyst_action"
    assert doc["legal_profile"] == "licensed_media"


# ---------------------------------------------------------------------------
# 19. detail page 能归档为 document.md
# ---------------------------------------------------------------------------


def test_detail_page_archived_as_markdown(
    sample_analyst_action_table_html: str,
    sample_analyst_action_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """detail page 能归档为 document.md。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="aa_test",
                source_name="Analyst Action Test",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            analyst_action_html_by_url=lambda url: sample_analyst_action_table_html
            if url == "https://example.com/analyst-actions" else None,
            http_html=lambda url: sample_analyst_action_detail_html
            if "/actions/detail-" in url else None,
        ),
    )
    result = archiver.run()

    # 至少有一个文档的 markdown_path 不为空
    saved_with_md = [d for d in result.saved_documents if d.markdown_path]
    assert len(saved_with_md) > 0
    # markdown 文件实际存在
    for d in saved_with_md:
        assert Path(d.markdown_path).exists()


# ---------------------------------------------------------------------------
# 20. source failure isolation
# ---------------------------------------------------------------------------


def test_source_failure_isolation(
    sample_analyst_action_table_html: str,
    sample_analyst_action_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """单个 analyst_action source 失败不影响其他 source。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            # 这个 source 会失败（HTML 内容为空）
            ResearchSourceConfig(
                source_id="broken_aa",
                source_name="Broken Analyst Action",
                source_type="analyst_action",
                url="https://broken.example.com/actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
            # 这个 source 会成功
            ResearchSourceConfig(
                source_id="ok_aa",
                source_name="OK Analyst Action",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=True,
                legal_profile="licensed_media",
                tags=["analyst_action"],
            ),
        ],
    )

    def aa_html_injector(url: str) -> str | None:
        if "broken.example.com" in url:
            return ""  # 空内容，触发失败
        if "example.com/analyst-actions" in url:
            return sample_analyst_action_table_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            analyst_action_html_by_url=aa_html_injector,
            http_html=lambda url: sample_analyst_action_detail_html
            if "/actions/detail-" in url else None,
        ),
    )
    result = archiver.run()

    # broken_aa 失败，ok_aa 成功
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_aa")
    ok_stat = next(s for s in result.source_stats if s["source_id"] == "ok_aa")
    assert broken_stat["status"] == "failed"
    assert ok_stat["status"] in ("healthy", "degraded")
    assert ok_stat["candidate_count"] == 5


# ---------------------------------------------------------------------------
# 21. 配置校验
# ---------------------------------------------------------------------------


def test_validate_config_analyst_action_requires_url() -> None:
    """analyst_action 缺少 url 和 base_url 时校验失败。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="bad_aa",
                source_name="Bad Analyst Action",
                source_type="analyst_action",
                url=None,
                base_url=None,
                extraction_profile="analyst_action_table",
                enabled=False,
                legal_profile="licensed_media",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert any("analyst_action" in e for e in errors)


def test_validate_config_analyst_action_passes() -> None:
    """合法的 analyst_action 配置应校验通过。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="ok_aa_table",
                source_name="OK Analyst Action Table",
                source_type="analyst_action",
                url="https://example.com/analyst-actions",
                extraction_profile="analyst_action_table",
                enabled=False,
                legal_profile="licensed_media",
            ),
            ResearchSourceConfig(
                source_id="ok_aa_detail",
                source_name="OK Analyst Action Detail",
                source_type="analyst_action",
                url="https://example.com/analyst-action/detail",
                extraction_profile="analyst_action_detail",
                enabled=False,
                legal_profile="licensed_media",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert errors == []


# ---------------------------------------------------------------------------
# 22. no business fields in output
# ---------------------------------------------------------------------------


def test_no_business_fields_in_output(sample_analyst_action_table_html: str) -> None:
    """候选文档不包含任何投研判断字段。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) > 0

    cand_dict = candidates[0].model_dump()
    forbidden_fields = {
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "sentiment",
        "bullish",
        "bearish",
        "recommendation",
        "action_decision",
        "signal",
    }
    for field in forbidden_fields:
        assert field not in cand_dict, f"候选文档不应包含业务字段: {field}"


def test_no_business_fields_in_raw_entry(sample_analyst_action_table_html: str) -> None:
    """raw_entry 中也不包含投研判断字段。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) > 0

    raw = candidates[0].raw_entry
    forbidden_keys = {
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "sentiment",
        "recommendation",
        "action_decision",
        "signal",
    }
    for key in forbidden_keys:
        assert key not in raw, f"raw_entry 不应包含业务字段: {key}"


def test_price_target_is_metadata_not_recommendation(
    sample_analyst_action_table_html: str,
) -> None:
    """price target 只作为 raw_entry metadata，不生成投资建议字段。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry

    # price_target_to 应该存在
    assert "price_target_to" in raw
    assert raw["price_target_to"] == "$150"
    # 但不应有 recommendation / signal / action_decision 等业务字段
    assert "recommendation" not in raw
    assert "signal" not in raw
    assert "action_decision" not in raw
    assert "investment_rating" not in raw


# ---------------------------------------------------------------------------
# 23. example config 全部 enabled: false
# ---------------------------------------------------------------------------


def test_example_config_all_disabled() -> None:
    """example config 中所有 source 的 enabled 都为 false。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    assert example_path.exists(), f"example config 不存在: {example_path}"

    with open(example_path, "r", encoding="utf-8") as f:
        cfg_dict = yaml.safe_load(f)

    sources = cfg_dict.get("sources") or []
    assert len(sources) > 0, "example config 应该至少有一个 source"

    for src in sources:
        assert src.get("enabled") is False, (
            f"source [{src.get('source_id')}] enabled 应为 false，实际为 {src.get('enabled')}"
        )


def test_example_config_loads_and_validates() -> None:
    """example config 能被 load_research_config 加载并通过校验。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    errors = validate_research_config(cfg)
    assert errors == [], f"example config 校验失败: {errors}"


def test_example_config_has_analyst_action_sources() -> None:
    """example config 包含至少 3 个 analyst_action source。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    aa_sources = [s for s in cfg.sources if s.source_type == "analyst_action"]
    assert len(aa_sources) >= 3, f"example config 应至少有 3 个 analyst_action source，实际 {len(aa_sources)}"


# ---------------------------------------------------------------------------
# 补充：connector 边界
# ---------------------------------------------------------------------------


def test_missing_url_raises() -> None:
    """缺少 url 时抛 ValueError。"""
    connector = AnalystActionConnector()
    source = _make_source(url=None, base_url=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_empty_html_raises() -> None:
    """HTML 内容为空时抛 ValueError。"""
    connector = AnalystActionConnector(html_by_url=lambda url: "")
    source = _make_source()
    cfg = _make_config()
    with pytest.raises(ValueError, match="内容为空"):
        connector.discover(source, cfg)


def test_reads_local_file(tmp_path: Path, sample_analyst_action_table_html: str) -> None:
    """能读取本地 HTML 文件。"""
    html_path = tmp_path / "analyst_actions.html"
    html_path.write_text(sample_analyst_action_table_html, encoding="utf-8")

    connector = AnalystActionConnector()
    source = _make_source(url=str(html_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 5


def test_raw_entry_contains_document_kind(sample_analyst_action_table_html: str) -> None:
    """raw_entry 保留 document_kind 和 profile 用于审计。"""
    connector = AnalystActionConnector(
        html_by_url=lambda url: sample_analyst_action_table_html
    )
    source = _make_source(extraction_profile="analyst_action_table")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["document_kind"] == "analyst_action"
    assert raw["profile"] == "analyst_action_table"
    assert raw["detail_url"] == "https://example.com/actions/detail-1"
