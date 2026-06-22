"""正文提取 / Markdown 生成 / 图片 URL 改写 测试。"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.wechat.cleaner import clean_wechat_content
from opc_foundation.wechat.extractor import extract_main_content
from opc_foundation.wechat.markdown import (
    build_article_markdown,
    html_to_markdown,
    rewrite_html_image_urls,
    rewrite_markdown_image_urls,
)
from opc_foundation.wechat.models import ArticleCandidate


FIXTURES = Path(__file__).parent / "fixtures"


def _article_cand() -> ArticleCandidate:
    return ArticleCandidate(
        source="rss",
        account_name="示例公众号A",
        account_id="example_a",
        title="第一篇测试文章",
        url="http://mp.weixin.qq.com/s/example_a_1",
        canonical_url="http://mp.weixin.qq.com/s/example_a_1",
        published_at="2026-06-22T10:00:00+08:00",
    )


def test_extract_main_content_reads_title_and_body():
    html = (FIXTURES / "sample_wechat_article.html").read_text(encoding="utf-8")
    content = extract_main_content(html)
    assert "第一篇测试文章" in (content.title or "")
    assert "第一段正文" in content.text
    # 图片应该被提取到
    assert any("img1.jpg" in u for u in content.image_urls)


def test_clean_wechat_content_removes_noise():
    html = (FIXTURES / "sample_wechat_article.html").read_text(encoding="utf-8")
    content = extract_main_content(html)
    cleaned = clean_wechat_content(content)
    # 清洗后的正文不应包含"阅读原文"、"扫码关注"等噪声
    assert "阅读原文" not in cleaned.text
    assert "扫码关注" not in cleaned.text
    # 正文保留
    assert "第一段正文" in cleaned.text


def test_markdown_build_has_meta():
    html = (FIXTURES / "sample_wechat_article.html").read_text(encoding="utf-8")
    content = extract_main_content(html)
    cand = _article_cand()
    md = build_article_markdown(cand, content, captured_at="2026-06-22T10:00:00+08:00")
    assert "# 第一篇测试文章" in md or "第一篇测试文章" in md
    assert "示例公众号A" in md
    assert "http://mp.weixin.qq.com/s/example_a_1" in md


def test_markdown_image_rewrite():
    md = "看看这张图片：![](http://example.com/a.jpg)，再看这张：![说明](http://example.com/b.png)"
    rewritten = rewrite_markdown_image_urls(
        md,
        {"http://example.com/a.jpg": "images/a.jpg", "http://example.com/b.png": "images/b.png"},
    )
    assert "images/a.jpg" in rewritten
    assert "images/b.png" in rewritten


def test_html_image_rewrite():
    html = '<p><img src="http://x.com/a.jpg" /><img data-src="http://x.com/b.png" /></p>'
    rewritten = rewrite_html_image_urls(
        html,
        {"http://x.com/a.jpg": "images/a.jpg", "http://x.com/b.png": "images/b.png"},
    )
    assert 'src="images/a.jpg"' in rewritten
    assert 'data-src="images/b.png"' in rewritten


def test_article_with_images_extracts_all_urls():
    html = (FIXTURES / "sample_article_with_images.html").read_text(encoding="utf-8")
    content = extract_main_content(html)
    assert sum(1 for u in content.image_urls if "second.png" in u or "third.gif" in u) >= 2
