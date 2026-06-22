"""测试 OfficialPublicResearchConnector。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.research.connectors.official_public import (
    OfficialPublicResearchConnector,
)
from opc_foundation.research.models import (
    ResearchArchiveConfig,
    ResearchDefaults,
    ResearchSourceConfig,
)


def _make_source(
    url: str | None = "https://example.com/research",
    extraction_profile: str = "generic_article_list",
    max_items: int | None = None,
    base_url: str | None = None,
) -> ResearchSourceConfig:
    """构造一个 official_public_research source 配置。"""
    return ResearchSourceConfig(
        source_id="opr_test",
        source_name="Official Public Research Test",
        source_type="official_public_research",
        url=url,
        base_url=base_url,
        extraction_profile=extraction_profile,
        legal_profile="official_public",
        tags=["official", "research"],
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


# ---------------------------------------------------------------------------
# list page -> candidates
# ---------------------------------------------------------------------------


def test_parses_generic_article_list(sample_official_research_list_html: str) -> None:
    """能从 fixture HTML 解析出候选文档。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 里有 5 个 article，但第 5 个无链接应被跳过
    assert len(candidates) == 4
    assert candidates[0].title == "2026 年第一季度宏观经济展望"
    assert candidates[1].title == "新能源行业深度研究"


def test_relative_url_canonicalized(sample_official_research_list_html: str) -> None:
    """相对 URL 应被转成 absolute 并规范化。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source(url="https://example.com/research")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /research/article-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/research/article-1"
    assert candidates[0].canonical_url == "https://example.com/research/article-1"


def test_published_at_extraction(sample_official_research_list_html: str) -> None:
    """能从 <time datetime="..."> 提取发布时间。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "2026-01-15T09:00:00+08:00"
    assert candidates[1].published_at == "2026-01-16T10:30:00+08:00"


def test_summary_extraction(sample_official_research_list_html: str) -> None:
    """能从 class="summary" 提取摘要。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary == "本报告分析 2026 年第一季度宏观经济走势，涵盖 GDP、CPI、就业等核心指标。"


def test_author_extraction(sample_official_research_list_html: str) -> None:
    """能从 class="author" 提取作者。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].author == "研究部 张三"
    # 第 3 篇没有 author
    assert candidates[2].author is None


def test_language_extraction(sample_official_research_list_html: str) -> None:
    """能从 <html lang="..."> 提取语言。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].language == "zh-CN"


def test_inherits_source_tags_and_legal_profile(
    sample_official_research_list_html: str,
) -> None:
    """候选文档继承 source 的 tags 和 legal_profile。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.legal_profile == "official_public"
        assert c.tags == ["official", "research"]
        assert c.source_id == "opr_test"
        assert c.source_type == "official_public_research"


def test_respects_max_items(sample_official_research_list_html: str) -> None:
    """max_items 限制候选数量。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


# ---------------------------------------------------------------------------
# extraction_profile: simple_card_list
# ---------------------------------------------------------------------------


def test_parses_simple_card_list() -> None:
    """simple_card_profile 能从 class 含 card 的元素解析。"""
    html = """
    <html><body>
        <div class="card research-card">
            <h3><a href="/card-article-1">卡片文章一</a></h3>
            <time datetime="2026-01-15T09:00:00+08:00">2026-01-15</time>
            <p class="summary">卡片摘要一</p>
        </div>
        <div class="card">
            <h3><a href="/card-article-2">卡片文章二</a></h3>
            <time datetime="2026-01-16T09:00:00+08:00">2026-01-16</time>
        </div>
    </body></html>
    """
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: html
    )
    source = _make_source(extraction_profile="simple_card_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2
    assert candidates[0].title == "卡片文章一"
    assert candidates[0].summary == "卡片摘要一"


# ---------------------------------------------------------------------------
# extraction_profile: link_list
# ---------------------------------------------------------------------------


def test_parses_link_list() -> None:
    """link_list 列出所有 <a> 链接。"""
    html = """
    <html><body>
        <nav>
            <a href="/home">首页</a>
            <a href="/about">关于</a>
        </nav>
        <main>
            <a href="/research/article-1">研究文章一</a>
            <a href="/research/article-2">研究文章二</a>
            <a href="#anchor">锚点</a>
            <a href="javascript:void(0)">JS 链接</a>
            <a href="mailto:test@example.com">邮箱</a>
        </main>
    </body></html>
    """
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: html
    )
    source = _make_source(extraction_profile="link_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 应跳过 #anchor / javascript: / mailto:
    urls = [c.url for c in candidates]
    assert "https://example.com/research/article-1" in urls
    assert "https://example.com/research/article-2" in urls
    # 不应包含锚点/JS/mailto
    for u in urls:
        assert not u.startswith(("#", "javascript:", "mailto:"))


# ---------------------------------------------------------------------------
# fail-soft
# ---------------------------------------------------------------------------


def test_empty_list_fail_soft(sample_official_research_empty_html: str) -> None:
    """空列表页返回空候选列表，不崩溃。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_empty_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []


def test_malformed_html_fail_soft(sample_official_research_malformed_html: str) -> None:
    """损坏的 HTML 也能解析出能用的候选，不崩溃。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_malformed_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 至少能解析出 article-1 和 article-2（无 href 的会被跳过）
    titles = [c.title for c in candidates]
    assert "损坏文章一" in titles
    assert "损坏文章二" in titles
    # 无链接 / 空 链接的不应出现
    for c in candidates:
        assert c.url
        assert c.canonical_url


def test_missing_url_raises() -> None:
    """缺少 url 时抛 ValueError。"""
    connector = OfficialPublicResearchConnector()
    source = _make_source(url=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_empty_html_raises() -> None:
    """列表页内容为空时抛 ValueError。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: ""
    )
    source = _make_source()
    cfg = _make_config()
    with pytest.raises(ValueError, match="列表页内容为空"):
        connector.discover(source, cfg)


def test_reads_local_file(tmp_path: Path, sample_official_research_list_html: str) -> None:
    """能读取本地 HTML 文件。"""
    html_path = tmp_path / "list.html"
    html_path.write_text(sample_official_research_list_html, encoding="utf-8")

    connector = OfficialPublicResearchConnector()
    source = _make_source(url=str(html_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4


# ---------------------------------------------------------------------------
# archiver 集成测试
# ---------------------------------------------------------------------------


def test_archiver_run_with_official_public_research(
    sample_official_research_list_html: str,
    sample_official_research_article_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver run 能从 official_public_research 归档文档。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors
    from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="opr_test",
                source_name="Official Public Research Test",
                source_type="official_public_research",
                url="https://example.com/research",
                extraction_profile="generic_article_list",
                enabled=True,
                legal_profile="official_public",
                tags=["official", "research"],
            ),
        ],
    )

    # 注入：列表页 HTML + 详情页 HTML
    def list_html_injector(url: str) -> str | None:
        if "example.com/research" in url:
            return sample_official_research_list_html
        return None

    def article_html_injector(url: str) -> str | None:
        if "article-1" in url:
            return sample_official_research_article_html
        # 其他文章返回简单 HTML
        return "<html><body><article><p>简短正文</p></article></body></html>"

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            list_html_by_url=list_html_injector,
            http_html=article_html_injector,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count == 4
    assert result.saved_count + result.partial_count > 0

    # documents.jsonl 存在且有内容
    jsonl_path = temp_archive_root / "index" / "documents.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1


def test_archiver_dry_run_with_official_public_research(
    sample_official_research_list_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver dry-run 能发现候选，不抓正文。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors
    from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="opr_test",
                source_name="Official Public Research Test",
                source_type="official_public_research",
                url="https://example.com/research",
                extraction_profile="generic_article_list",
                enabled=True,
                legal_profile="official_public",
                tags=["official", "research"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            list_html_by_url=lambda url: sample_official_research_list_html,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    assert result.candidate_count == 4
    assert result.saved_count == 0  # dry-run 不抓正文


def test_source_failure_isolation(
    sample_official_research_list_html: str,
    temp_archive_root: Path,
) -> None:
    """单个 official_public_research source 失败不影响其他 source。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors
    from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            # 这个 source 会失败（列表页内容为空）
            ResearchSourceConfig(
                source_id="broken_opr",
                source_name="Broken OPR",
                source_type="official_public_research",
                url="https://broken.example.com/research",
                extraction_profile="generic_article_list",
                enabled=True,
                legal_profile="official_public",
            ),
            # 这个 source 会成功
            ResearchSourceConfig(
                source_id="ok_opr",
                source_name="OK OPR",
                source_type="official_public_research",
                url="https://example.com/research",
                extraction_profile="generic_article_list",
                enabled=True,
                legal_profile="official_public",
            ),
        ],
    )

    def list_html_injector(url: str) -> str | None:
        if "broken.example.com" in url:
            return ""  # 空内容，触发失败
        if "example.com/research" in url:
            return sample_official_research_list_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            list_html_by_url=list_html_injector,
            http_html=lambda url: "<html><body><article><p>简短正文</p></article></body></html>",
        ),
    )
    result = archiver.run()

    # broken_opr 失败，ok_opr 成功
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_opr")
    ok_stat = next(s for s in result.source_stats if s["source_id"] == "ok_opr")
    assert broken_stat["status"] == "failed"
    assert ok_stat["status"] in ("healthy", "degraded")
    assert ok_stat["candidate_count"] == 4


# ---------------------------------------------------------------------------
# 边界检查：无业务字段
# ---------------------------------------------------------------------------


def test_no_business_fields_in_output(sample_official_research_list_html: str) -> None:
    """候选文档不包含任何投研判断字段。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) > 0

    # 检查候选文档的字段
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
    }
    for field in forbidden_fields:
        assert field not in cand_dict, f"候选文档不应包含业务字段: {field}"


def test_raw_entry_contains_list_url(sample_official_research_list_html: str) -> None:
    """raw_entry 保留 list_url 和 extraction_profile 用于审计。"""
    connector = OfficialPublicResearchConnector(
        list_html_by_url=lambda url: sample_official_research_list_html
    )
    source = _make_source(extraction_profile="generic_article_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["list_url"] == "https://example.com/research"
    assert raw["extraction_profile"] == "generic_article_list"
    assert raw["original_url"] == "/research/article-1"
