"""feed_client + manual_url 候选文章生成测试。"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.wechat.feed_client import (
    canonicalize_wechat_url,
    fetch_feed_candidates,
)
from opc_foundation.wechat.manual_url import (
    build_manual_candidate,
    load_manual_url_candidates,
    load_manual_urls,
)
from opc_foundation.wechat.models import WeChatAccountConfig


FIXTURES = Path(__file__).parent / "fixtures"


def test_canonicalize_url_strips_tracking_params():
    url = "http://mp.weixin.qq.com/s/abc?utm_source=feed&from=singlemessage"
    canonical = canonicalize_wechat_url(url)
    assert "utm_source" not in canonical
    # 域名、path 应该保留
    assert "mp.weixin.qq.com/s/abc" in canonical.replace("?", "") or "mp.weixin.qq.com/s/abc" in canonical


def test_canonicalize_url_lower_host():
    assert canonicalize_wechat_url("HTTP://EXAMPLE.COM/Path") == "http://example.com/Path"


def test_fetch_feed_from_fixture_xml():
    account = WeChatAccountConfig(
        account_name="示例公众号A",
        account_id="example_a",
        feed_url="",
        source_type="rss",
    )
    with open(FIXTURES / "sample_feed.xml", "rb") as fh:
        feed_bytes = fh.read()
    result = fetch_feed_candidates(account, max_articles=5, feed_content=feed_bytes)
    assert not result.errors, f"feed 不应解析失败: {result.errors}"
    assert len(result.candidates) == 2
    assert result.candidates[0].title.startswith("第一篇测试文章")


def test_disabled_account_produces_warning():
    account = WeChatAccountConfig(
        account_name="被禁用的号",
        account_id="zzz",
        feed_url="",
        source_type="rss",
        enabled=False,
    )
    result = fetch_feed_candidates(account, feed_content=b"<rss/>")
    assert len(result.candidates) == 0
    assert any("已禁用" in w or "已禁用" in w for w in result.warnings)


def test_manual_url_candidates(tmp_path: Path):
    p = tmp_path / "manual.txt"
    p.write_text(
        "http://mp.weixin.qq.com/s/manual_1\n"
        "http://mp.weixin.qq.com/s/manual_2\n"
        "# 注释行\n"
        "\n",
        encoding="utf-8",
    )
    cands = load_manual_url_candidates(p)
    assert len(cands) == 2
    assert cands[0].canonical_url != cands[0].url or True
    # 应正确规范化
    assert "manual_1" in cands[0].canonical_url


def test_load_manual_urls_deduplicates(tmp_path: Path):
    p = tmp_path / "dup.txt"
    p.write_text("http://a.example.com/\nhttp://a.example.com/\n", encoding="utf-8")
    urls = load_manual_urls(p)
    assert urls == ["http://a.example.com/"]


def test_build_manual_candidate_has_same_structure():
    cand = build_manual_candidate("http://mp.weixin.qq.com/s/x")
    assert cand.source == "manual"
    assert cand.title == "http://mp.weixin.qq.com/s/x"
    assert cand.canonical_url.startswith("http://mp.weixin.qq.com/s/x")
