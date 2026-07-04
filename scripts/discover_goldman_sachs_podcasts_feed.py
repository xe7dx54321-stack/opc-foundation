#!/usr/bin/env python3
"""
discover_goldman_sachs_podcasts_feed.py
========================================
M3C-5B2: Goldman Sachs Podcasts feed / metadata 专项发现脚本。

目标：
    1. 只处理 goldman_sachs_podcasts
    2. 使用公开 URL，轻量 HTTP 请求
    3. 不使用浏览器运行时（Playwright / Selenium）
    4. 不绕登录 / 付费墙
    5. 输出候选入口清单、真实 episode 候选样本、markdown 报告

允许入口类型（按优先级）：
    - RSS / Atom feed
    - Podcast XML feed
    - sitemap.xml / sitemap index
    - JSON-LD (PodcastEpisode / NewsArticle / CreativeWork)
    - OpenGraph metadata
    - HTML episode links

禁止：
    - 修改 trial_v2 allowlist
    - 修改 TRAE scheduling
    - 配置 production
    - 提交 data/ local/ secrets
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_ID = "goldman_sachs_podcasts"
SOURCE_NAME = "Goldman Sachs Podcasts"
BASE_URL = "https://www.goldmansachs.com"
PODCAST_HUB_URL = "https://www.goldmansachs.com/insights/podcasts"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 20

NAVIGATION_NOISE_KEYWORDS = [
    "subscribe", "apple podcasts", "spotify", "youtube",
    "contact", "privacy", "terms", "newsletter", "sign up",
    "asset & wealth management", "platform solutions",
    "investment banking", "ficc and equities", "transaction banking",
    "gsiam", "marquee", "what we do", "careers", "about us",
    "global site", "select location", "cookie", "accessibility",
]

SERIES_SLUGS = [
    "exchanges",
    "the-markets",
    "top-of-mind",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EntryAttempt:
    entry_type: str
    url: str
    http_status: int | None = None
    content_type: str | None = None
    error: str | None = None
    has_episodes: bool = False
    has_dates: bool = False
    has_descriptions: bool = False
    episode_count: int = 0
    sample_episodes: list[dict] = field(default_factory=list)
    raw_snippet: str = ""


@dataclass
class DiscoveryResult:
    source_id: str
    source_name: str
    timestamp: str
    base_commit: str
    branch: str
    attempts: list[EntryAttempt] = field(default_factory=list)
    final_decision: str = "pending"  # feed_candidate_found | browser_like_backlog | network_or_access_watch
    total_unique_episodes: int = 0
    dated_episode_count: int = 0
    navigation_noise_count: int = 0
    navigation_noise_ratio: float = 0.0
    report_path: str = ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str, allow_redirects: bool = True) -> tuple[int, str, str, str | None]:
    """Return (status, content_type, text, error)."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=allow_redirects,
        )
        content_type = resp.headers.get("Content-Type", "")
        return resp.status_code, content_type, resp.text, None
    except requests.RequestException as exc:
        return None, "", "", str(exc)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_rss_atom(text: str, url: str) -> list[dict]:
    """Parse RSS / Atom / podcast XML feed, return episode candidates."""
    episodes = []
    soup = BeautifulSoup(text, "xml")
    for item in soup.find_all("item"):
        title = item.find("title")
        link = item.find("link")
        pub = item.find("pubDate") or item.find("published")
        desc = item.find("description") or item.find("summary")
        episodes.append({
            "title": title.get_text(strip=True) if title else "",
            "url": (link.get_text(strip=True) if link else link.get("href", "")) if link else "",
            "date": pub.get_text(strip=True) if pub else "",
            "description": desc.get_text(strip=True)[:200] if desc else "",
        })
    for entry in soup.find_all("entry"):
        title = entry.find("title")
        link = entry.find("link")
        pub = entry.find("published") or entry.find("updated")
        desc = entry.find("summary") or entry.find("content")
        episodes.append({
            "title": title.get_text(strip=True) if title else "",
            "url": link.get("href", "") if link else "",
            "date": pub.get_text(strip=True) if pub else "",
            "description": desc.get_text(strip=True)[:200] if desc else "",
        })
    return episodes


def parse_json_ld(text: str, url: str) -> list[dict]:
    """Parse JSON-LD script tags for PodcastEpisode / NewsArticle / CreativeWork."""
    episodes = []
    soup = BeautifulSoup(text, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                item_type = item.get("@type", "")
                if isinstance(item_type, list):
                    item_type = item_type[0]
                if item_type in ("PodcastEpisode", "NewsArticle", "Article", "CreativeWork", "PodcastSeries"):
                    episodes.append({
                        "title": item.get("headline", item.get("name", "")),
                        "url": item.get("url", ""),
                        "date": item.get("datePublished", item.get("dateModified", "")),
                        "description": item.get("description", "")[:200],
                        "json_type": item_type,
                    })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return episodes


def parse_opengraph(text: str, url: str) -> list[dict]:
    """Parse OpenGraph meta tags."""
    episodes = []
    soup = BeautifulSoup(text, "html.parser")
    og_title = soup.find("meta", property="og:title")
    og_url = soup.find("meta", property="og:url")
    og_desc = soup.find("meta", property="og:description")
    og_type = soup.find("meta", property="og:type")
    if og_title and og_type:
        episodes.append({
            "title": og_title.get("content", ""),
            "url": og_url.get("content", "") if og_url else url,
            "date": "",
            "description": og_desc.get("content", "")[:200] if og_desc else "",
            "og_type": og_type.get("content", ""),
        })
    return episodes


def parse_html_episode_links(text: str, base_url: str) -> list[dict]:
    """Parse raw HTML for episode-like links with titles and dates."""
    episodes = []
    soup = BeautifulSoup(text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if not title or len(title) < 4:
            continue
        full_url = urljoin(base_url, href)
        if not full_url.startswith("http"):
            continue
        # Look for date near the link
        date = ""
        parent = a.parent
        for _ in range(3):
            if parent:
                text_content = parent.get_text(" ", strip=True)
                date_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b", text_content, re.I)
                if date_match:
                    date = date_match.group(0)
                    break
                date_match = re.search(r"\b\d{4}[/-]\d{2}[/-]\d{2}\b", text_content)
                if date_match:
                    date = date_match.group(0)
                    break
                parent = parent.parent
        episodes.append({
            "title": title,
            "url": full_url,
            "date": date,
            "description": "",
        })
    return episodes


# ---------------------------------------------------------------------------
# Noise filtering
# ---------------------------------------------------------------------------

def is_navigation_noise(candidate: dict) -> bool:
    """Return True if candidate is clearly navigation / marketing noise."""
    title = candidate.get("title", "").lower()
    url = candidate.get("url", "").lower()
    desc = candidate.get("description", "").lower()
    combined = f"{title} {url} {desc}"
    for kw in NAVIGATION_NOISE_KEYWORDS:
        if kw in combined:
            return True
    if len(title) < 5:
        return True
    if title.count(" ") < 1 and not any(c.isdigit() for c in title):
        return True
    return False


def filter_noise(candidates: list[dict]) -> list[dict]:
    return [c for c in candidates if not is_navigation_noise(c)]


# ---------------------------------------------------------------------------
# Discovery logic
# ---------------------------------------------------------------------------

def discover() -> DiscoveryResult:
    result = DiscoveryResult(
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        timestamp=datetime.utcnow().isoformat() + "Z",
        base_commit="796f9e8",
        branch="feature/m3c-5b2-goldman-podcasts-feed-spike",
    )

    all_candidates: list[dict] = []
    feed_links: list[str] = []

    # 1. Podcast hub page (SSR HTML)
    status, ctype, text, err = fetch(PODCAST_HUB_URL)
    hub_attempt = EntryAttempt(
        entry_type="podcast_hub_html",
        url=PODCAST_HUB_URL,
        http_status=status,
        content_type=ctype,
        error=err,
    )
    if status == 200 and text:
        soup = BeautifulSoup(text, "html.parser")
        # Check for RSS / Atom links
        for link in soup.find_all("link", rel=True):
            rel = " ".join(link.get("rel", [])).lower() if isinstance(link.get("rel"), list) else link.get("rel", "").lower()
            if "alternate" in rel and ("rss" in link.get("type", "").lower() or "atom" in link.get("type", "").lower()):
                feed_links.append(urljoin(PODCAST_HUB_URL, link.get("href", "")))
        if feed_links:
            hub_attempt.raw_snippet += f"Found feed links: {feed_links}\n"

        # Parse JSON-LD
        jsonld_eps = parse_json_ld(text, PODCAST_HUB_URL)
        if jsonld_eps:
            hub_attempt.has_episodes = True
            hub_attempt.episode_count = len(jsonld_eps)
            hub_attempt.sample_episodes = jsonld_eps[:5]
            all_candidates.extend(jsonld_eps)

        # Parse OpenGraph
        og_eps = parse_opengraph(text, PODCAST_HUB_URL)
        if og_eps and not hub_attempt.has_episodes:
            hub_attempt.has_descriptions = True
            hub_attempt.sample_episodes = og_eps[:3]

        # Parse HTML episode links
        html_eps = parse_html_episode_links(text, PODCAST_HUB_URL)
        html_eps = filter_noise(html_eps)
        if html_eps:
            hub_attempt.has_episodes = True
            hub_attempt.episode_count = len(html_eps)
            hub_attempt.sample_episodes.extend(html_eps[:5])
            all_candidates.extend(html_eps)

        hub_attempt.raw_snippet += f"HTML link count after noise filter: {len(html_eps)}\n"

    result.attempts.append(hub_attempt)

    # 2. RSS / Atom feed discovery (from feed links found in hub, or well-known paths)
    feed_urls = set(feed_links) if hub_attempt.raw_snippet else set()
    feed_urls.update([
        "https://www.goldmansachs.com/insights/podcasts/rss.xml",
        "https://www.goldmansachs.com/insights/podcasts/feed.xml",
        "https://www.goldmansachs.com/insights/podcasts/podcast.xml",
        "https://www.goldmansachs.com/insights/podcasts.atom",
        "https://www.goldmansachs.com/feed/podcasts",
    ])
    for feed_url in feed_urls:
        status, ctype, text, err = fetch(feed_url)
        feed_attempt = EntryAttempt(
            entry_type="rss_atom_feed",
            url=feed_url,
            http_status=status,
            content_type=ctype,
            error=err,
        )
        if status == 200 and text and ("rss" in ctype.lower() or "xml" in ctype.lower() or "<rss" in text or "<feed" in text):
            eps = parse_rss_atom(text, feed_url)
            eps = filter_noise(eps)
            if eps:
                feed_attempt.has_episodes = True
                feed_attempt.has_dates = any(e.get("date") for e in eps)
                feed_attempt.has_descriptions = any(e.get("description") for e in eps)
                feed_attempt.episode_count = len(eps)
                feed_attempt.sample_episodes = eps[:5]
                all_candidates.extend(eps)
        result.attempts.append(feed_attempt)

    # 3. sitemap.xml / sitemap index
    sitemap_urls = [
        "https://www.goldmansachs.com/sitemap.xml",
        "https://www.goldmansachs.com/sitemap-index.xml",
    ]
    for sm_url in sitemap_urls:
        status, ctype, text, err = fetch(sm_url)
        sm_attempt = EntryAttempt(
            entry_type="sitemap_xml",
            url=sm_url,
            http_status=status,
            content_type=ctype,
            error=err,
        )
        if status == 200 and text and "<urlset" in text:
            soup = BeautifulSoup(text, "xml")
            urls = [loc.get_text(strip=True) for loc in soup.find_all("loc") if loc]
            podcast_urls = [u for u in urls if "/podcasts" in u.lower() or "/podcast" in u.lower()]
            sm_attempt.has_episodes = len(podcast_urls) > 0
            sm_attempt.episode_count = len(podcast_urls)
            sm_attempt.sample_episodes = [{"url": u, "title": u} for u in podcast_urls[:5]]
            sm_attempt.raw_snippet = f"Total URLs: {len(urls)}, Podcast URLs: {len(podcast_urls)}"
        elif status == 200 and text and "<sitemapindex" in text:
            soup = BeautifulSoup(text, "xml")
            urls = [loc.get_text(strip=True) for loc in soup.find_all("loc") if loc]
            sm_attempt.has_episodes = len(urls) > 0
            sm_attempt.episode_count = len(urls)
            sm_attempt.raw_snippet = f"Sitemap index entries: {len(urls)}"
        result.attempts.append(sm_attempt)

    # 4. Series-specific landing pages (SSR check)
    for slug in SERIES_SLUGS:
        series_url = f"{BASE_URL}/insights/podcasts/series/{slug}"
        status, ctype, text, err = fetch(series_url)
        series_attempt = EntryAttempt(
            entry_type=f"series_page_{slug}",
            url=series_url,
            http_status=status,
            content_type=ctype,
            error=err,
        )
        if status == 200 and text:
            jsonld_eps = parse_json_ld(text, series_url)
            html_eps = parse_html_episode_links(text, series_url)
            html_eps = filter_noise(html_eps)
            if jsonld_eps:
                series_attempt.has_episodes = True
                series_attempt.episode_count = len(jsonld_eps)
                series_attempt.sample_episodes = jsonld_eps[:5]
                all_candidates.extend(jsonld_eps)
            elif html_eps:
                series_attempt.has_episodes = True
                series_attempt.episode_count = len(html_eps)
                series_attempt.sample_episodes = html_eps[:5]
                all_candidates.extend(html_eps)
            series_attempt.raw_snippet = f"JSON-LD episodes: {len(jsonld_eps)}, HTML links after filter: {len(html_eps)}"
        result.attempts.append(series_attempt)

    # 5. robots.txt (to discover sitemap or feed hints)
    robots_url = "https://www.goldmansachs.com/robots.txt"
    status, ctype, text, err = fetch(robots_url)
    robots_attempt = EntryAttempt(
        entry_type="robots_txt",
        url=robots_url,
        http_status=status,
        content_type=ctype,
        error=err,
    )
    if status == 200 and text:
        sitemaps = re.findall(r"Sitemap:\s*(.+)", text, re.I)
        robots_attempt.raw_snippet = f"Sitemaps: {sitemaps}"
        robots_attempt.has_episodes = len(sitemaps) > 0
        robots_attempt.episode_count = len(sitemaps)
    result.attempts.append(robots_attempt)

    # -----------------------------------------------------------------------
    # Final scoring
    # -----------------------------------------------------------------------
    # Deduplicate candidates by URL
    seen_urls = set()
    unique_candidates = []
    for c in all_candidates:
        url = c.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_candidates.append(c)

    dated_count = sum(1 for c in unique_candidates if c.get("date"))
    noise_count = sum(1 for c in all_candidates if is_navigation_noise(c))
    total_raw = len(all_candidates)
    nav_ratio = noise_count / total_raw if total_raw > 0 else 0.0

    result.total_unique_episodes = len(unique_candidates)
    result.dated_episode_count = dated_count
    result.navigation_noise_count = noise_count
    result.navigation_noise_ratio = round(nav_ratio, 2)

    # Decision logic
    if result.total_unique_episodes >= 3 and result.dated_episode_count >= 3 and nav_ratio <= 0.4:
        result.final_decision = "feed_candidate_found"
    elif any(a.http_status == 403 for a in result.attempts):
        result.final_decision = "network_or_access_watch"
    else:
        result.final_decision = "browser_like_backlog"

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(result: DiscoveryResult, path: str) -> None:
    lines = []
    lines.append("# M3C-5B2: Goldman Sachs Podcasts Feed / Metadata Discovery Report")
    lines.append("")
    lines.append(f"> **执行时间**: {result.timestamp}")
    lines.append(f"> **Base Commit**: {result.base_commit}")
    lines.append(f"> **Branch**: {result.branch}")
    lines.append(f"> **研究对象**: {result.source_id} only")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 入口发现结果")
    lines.append("")
    lines.append("| entry_type | url | http_status | content_type | episode_count | has_dates | has_desc | 可用 |")
    lines.append("|---|---|---:|---|---:|---:|---:|:---|")
    for a in result.attempts:
        usable = "是" if a.has_episodes else "否"
        status = a.http_status if a.http_status is not None else "ERR"
        lines.append(
            f"| {a.entry_type} | `{a.url}` | {status} | {a.content_type or '-'} | "
            f"{a.episode_count} | {'是' if a.has_dates else '否'} | "
            f"{'是' if a.has_descriptions else '否'} | {usable} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. 真实 Episode 样本")
    lines.append("")
    all_samples = []
    for a in result.attempts:
        all_samples.extend(a.sample_episodes)
    # Deduplicate
    seen = set()
    deduped = []
    for s in all_samples:
        key = s.get("url", s.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            deduped.append(s)
    for i, s in enumerate(deduped[:10], 1):
        lines.append(f"### 样本 {i}")
        _title = s.get("title", "-").replace("|", "\\|")
        lines.append(f"- **Title**: {_title}")
        lines.append(f"- **URL**: {s.get('url', '-')}")
        lines.append(f"- **Date**: {s.get('date', '-')}")
        if s.get("description"):
            _desc = s.get("description", "-").replace("|", "\\|")
            lines.append(f"- **Description**: {_desc}")
        if s.get("json_type"):
            lines.append(f"- **JSON-LD Type**: {s.get('json_type', '-')}")
        if s.get("og_type"):
            lines.append(f"- **OG Type**: {s.get('og_type', '-')}")
        lines.append("")
    if not deduped:
        lines.append("*未找到有效 episode 样本。*")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. 导航噪音 / 无效样本")
    lines.append("")
    noise_samples = [c for c in all_samples if is_navigation_noise(c)]
    if noise_samples:
        for s in noise_samples[:5]:
            lines.append(f"- `{s.get('title', '-')}` → {s.get('url', '-')}")
    else:
        lines.append("*未发现明显导航噪音样本。*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. 统计摘要")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| total_unique_episodes | {result.total_unique_episodes} |")
    lines.append(f"| dated_episode_count | {result.dated_episode_count} |")
    lines.append(f"| navigation_noise_count | {result.navigation_noise_count} |")
    lines.append(f"| navigation_noise_ratio | {result.navigation_noise_ratio} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Final Decision")
    lines.append("")
    lines.append(f"- **final_decision**: `{result.final_decision}`")
    if result.final_decision == "feed_candidate_found":
        lines.append("- **说明**: 找到稳定公开入口，建议进入下一轮 preflight。")
    elif result.final_decision == "browser_like_backlog":
        lines.append("- **说明**: 未找到非浏览器稳定入口，继续保留为 browser_like_backlog。")
    else:
        lines.append("- **说明**: 网络访问受限，需进一步观察。")
    lines.append("")
    _preflight = "是" if result.final_decision == "feed_candidate_found" else "否"
    lines.append("| 检查项 | 结论 |")
    lines.append("|---|---|")
    lines.append(f"| 建议进入下一轮 preflight | {_preflight} |")
    lines.append("| 修改 trial_v2 allowlist | **否** |")
    lines.append("| 修改 TRAE scheduling | **否** |")
    lines.append("| 配置 production | **否** |")
    lines.append("| 提交 data/local/secrets | **否** |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by scripts/discover_goldman_sachs_podcasts_feed.py*")
    lines.append("*M3C-5B2: Goldman Sachs Podcasts feed / metadata spike*")

    Path(path).write_text("\n".join(lines), encoding="utf-8")
    result.report_path = path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="M3C-5B2 Goldman Sachs Podcasts feed discovery")
    parser.add_argument(
        "--report",
        default="docs/foundation_m3c_5b2_goldman_podcasts_feed_spike_report.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    print(f"[{SOURCE_ID}] Starting feed discovery...", file=sys.stderr)
    result = discover()
    generate_report(result, args.report)
    print(f"[{SOURCE_ID}] Discovery complete.", file=sys.stderr)
    print(f"[{SOURCE_ID}] Final decision: {result.final_decision}", file=sys.stderr)
    print(f"[{SOURCE_ID}] Report written to: {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
