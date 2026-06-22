"""从 RSS/Atom feed 读取文章候选。

功能说明（小白解读）：
    本文件负责：
    1. 解析一个 feed（RSS 2.0 / Atom 1.0 都可以）
    2. 把每条 entry 转换成 ArticleCandidate（文章候选对象）
    3. 规范化每条文章的 URL（用于去重 key）
    4. 记录解析失败/空 feed/异常，供上层做 warning 收集

我们直接复用仓库已有依赖：
    - feedparser（业界通用的 feed 解析库）
    - opc_foundation.web.url_utils.canonicalize_url（已有 URL 规范化）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser

from ..web.url_utils import canonicalize_url
from .models import ArticleCandidate, WeChatAccountConfig


# 常见 tracking 参数名（全小写匹配），用于进一步精简 canonical URL
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "ref",
    "ref_src",
    "spm",
    "from",
    "scenes",
    "clicktime",
    "enterid",
    "forceh5",
}


def canonicalize_wechat_url(url: str) -> str:
    """对微信文章 URL 做更严格的规范化。

    规则（按顺序）：
        1. 使用仓库已有 canonicalize_url 做基础处理（去 fragment、小写域名）
        2. 移除常见 tracking 参数（utm_*、fbclid、gclid 等）
        3. 对剩余 query 参数按 key 排序，保证等价 URL 得到相同字符串

    参数：
        url: 原始 URL

    返回：
        规范化后的 URL 字符串
    """

    base = canonicalize_url(url or "")
    try:
        parsed = urlparse(base)
        # 过滤掉 tracking 参数
        qs = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in _TRACKING_PARAMS]
        qs.sort(key=lambda kv: kv[0])
        new_query = urlencode(qs)
        norm = parsed._replace(query=new_query)
        return urlunparse(norm)
    except Exception:
        return base


class FeedParseResult:
    """一次 feed 解析的结果。"""

    def __init__(
        self,
        account: WeChatAccountConfig,
        candidates: list[ArticleCandidate] | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        feed_title: str | None = None,
    ) -> None:
        self.account = account
        self.candidates: list[ArticleCandidate] = candidates or []
        self.warnings: list[str] = warnings or []
        self.errors: list[str] = errors or []
        self.feed_title = feed_title


def _sanitize_string(value: Any, default: str = "") -> str:
    """把 feedparser 返回的杂项字段安全转成字符串。"""

    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    # feedparser 有时返回自定义对象（如 FeedParserDict）
    try:
        return str(value).strip()
    except Exception:
        return default


def _extract_summary(entry: dict[str, Any]) -> str | None:
    """从 entry 中尽力提取一个摘要字符串。"""

    for key in ("summary", "description", "subtitle", "content"):
        raw = entry.get(key)
        if not raw:
            continue
        # feedparser 的 content 字段可能是列表，每项有 value
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    text = _sanitize_string(item.get("value"))
                    if text:
                        return text
                else:
                    text = _sanitize_string(raw)
                    if text:
                        return text
        else:
            text = _sanitize_string(raw)
            if text:
                return text
    return None


def _extract_image_url(entry: dict[str, Any]) -> str | None:
    """尽力从 entry 中找到封面图 URL。"""

    # 1) 显式字段
    for key in ("image", "logo", "icon", "enclosure"):
        val = entry.get(key)
        if isinstance(val, dict):
            url = _sanitize_string(val.get("href") or val.get("url"))
            if url:
                return url
        if isinstance(val, str) and val.strip().startswith(("http://", "https://")):
            return val.strip()
    # 2) enclosures 列表（可能有图片）
    encs = entry.get("enclosures") or []
    if isinstance(encs, list):
        for enc in encs:
            if isinstance(enc, dict):
                href = _sanitize_string(enc.get("href") or enc.get("url"))
                t = (_sanitize_string(enc.get("type")) or "").lower()
                if href and ("image" in t or not t):
                    return href
    return None


def _entry_to_candidate(
    entry: dict[str, Any],
    account: WeChatAccountConfig,
) -> ArticleCandidate | None:
    """把一条 feed entry 转成 ArticleCandidate；关键字段缺失时返回 None。"""

    title = _sanitize_string(entry.get("title"))
    # 优先使用 link，其次 guid/id
    url = (
        _sanitize_string(entry.get("link"))
        or _sanitize_string(entry.get("id"))
        or ""
    )
    if not title or not url:
        return None

    published = (
        _sanitize_string(entry.get("published"))
        or _sanitize_string(entry.get("updated"))
        or _sanitize_string(entry.get("pubDate"))
        or None
    )
    author = _sanitize_string(entry.get("author") or entry.get("dc_creator")) or None
    summary = _extract_summary(entry)
    cover_url = _extract_image_url(entry)

    canonical = canonicalize_wechat_url(url)

    return ArticleCandidate(
        source=f"{account.source_type}:{account.feed_url or account.account_name}",
        account_name=account.account_name,
        account_id=account.account_id,
        title=title,
        url=url,
        canonical_url=canonical,
        published_at=published,
        author=author or None,
        digest=summary or None,
        cover_url=cover_url,
        raw_entry={k: (str(v) if not isinstance(v, (dict, list, str, int, float, bool)) else v)
                   for k, v in entry.items()},
    )


def fetch_feed_candidates(
    account: WeChatAccountConfig,
    max_articles: int = 20,
    feed_content: str | bytes | None = None,
) -> FeedParseResult:
    """从一个账号配置读取 feed 并生成 ArticleCandidate 列表。

    参数：
        account:        账号配置（必须提供 feed_url 或由 feed_content 直接提供内容）
        max_articles:   最多返回多少条候选文章
        feed_content:   可选。如果提供，直接用它解析 feed（不做 HTTP 请求，方便测试）

    返回：
        FeedParseResult，包含候选列表、警告、错误
    """

    result = FeedParseResult(account=account)

    if not account.enabled:
        result.warnings.append(f"账号 [{account.account_name}] 已禁用，跳过")
        return result

    try:
        if feed_content is not None:
            parsed = feedparser.parse(feed_content)
        else:
            if not account.feed_url:
                result.errors.append(
                    f"账号 [{account.account_name}] 未配置 feed_url，无法读取 feed"
                )
                return result
            parsed = feedparser.parse(account.feed_url)
    except Exception as exc:
        result.errors.append(f"账号 [{account.account_name}] feed 解析异常: {exc}")
        return result

    # bozo 是解析警告级别，非 0 但有 entries 时仍可继续
    if parsed.get("bozo") and not parsed.get("entries"):
        result.errors.append(
            f"账号 [{account.account_name}] feed 解析失败（bozo={parsed.get('bozo')}，"
            f"无有效条目）: {parsed.get('bozo_exception')}"
        )
        return result

    if parsed.get("bozo"):
        result.warnings.append(
            f"账号 [{account.account_name}] feed 解析有警告: {parsed.get('bozo_exception')}"
        )

    feed_info = parsed.get("feed") or {}
    result.feed_title = _sanitize_string(feed_info.get("title")) or None

    entries = list(parsed.get("entries") or [])
    for entry in entries[:max_articles]:
        try:
            cand = _entry_to_candidate(entry, account)
            if cand:
                result.candidates.append(cand)
        except Exception as exc:
            result.warnings.append(
                f"账号 [{account.account_name}] 一条 entry 解析失败: {exc}"
            )
            continue

    return result


def fetch_feed_candidates_from_file(
    account: WeChatAccountConfig,
    feed_file: str | Path,
    max_articles: int = 20,
) -> FeedParseResult:
    """从本地 feed XML 文件读取候选（测试用）。"""

    with open(feed_file, "rb") as fh:
        return fetch_feed_candidates(account, max_articles=max_articles, feed_content=fh.read())
