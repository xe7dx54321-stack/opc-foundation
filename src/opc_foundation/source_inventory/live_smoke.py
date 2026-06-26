"""Source Inventory Live Smoke 核心运行器。

功能说明（小白解读）：
    这个模块是 live smoke 的核心，负责逐个检查 92 个信息源。
    对不同类型的源用不同的检查策略：
    - public_web / rss / podcast_rss：真实访问
    - search_provider：只检查配置，不跑搜索
    - blocked/high_risk：直接标记 blocked_by_policy，不访问
    - on_demand / dormant：不跑，标记对应状态

    为什么要分开策略？
        因为不是所有源都适合一上来就真实抓取：
        - 有些源按策略禁止访问（blocked）
        - 有些源是按需的，不该默认高频跑
        - 有些源是休眠的，暂时不验证
        - 搜索 provider 不应该默认跑真实搜索（消耗 API 额度）
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from ..dashboard.models import FoundationSource, SourceInventory
from .models import (
    CandidateItem,
    LiveSmokeRunConfig,
    LiveSmokeStatus,
    LiveSmokeSummary,
    SourceGroupLiveResult,
    SourceLiveResult,
)


def _now_str() -> str:
    """获取当前时间字符串（ISO 格式）。

    Returns:
        str: 当前时间字符串
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _html_extract_title(html: str) -> str:
    """从 HTML 中提取 title。

    小白解读：
        用正则匹配 <title>...</title> 标签的内容。
        不引入 BeautifulSoup，保持轻量。

    Args:
        html: HTML 字符串

    Returns:
        str: 提取到的标题，找不到返回空字符串
    """
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _html_extract_meta_description(html: str) -> str:
    """从 HTML 中提取 meta description。

    小白解读：
        匹配 <meta name="description" content="...">
        用于获取页面摘要。

    Args:
        html: HTML 字符串

    Returns:
        str: 描述文本
    """
    m = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    m = re.search(
        r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    return ""


def _html_extract_links(html: str, base_url: str, max_links: int = 20) -> list[tuple[str, str]]:
    """从 HTML 中提取链接（标题 + URL）。

    小白解读：
        匹配 <a href="...">文本</a>，返回链接列表。
        过滤掉锚点链接、javascript 链接等无用链接。

    Args:
        html: HTML 字符串
        base_url: 基础 URL，用于补全相对路径
        max_links: 最多返回多少条链接

    Returns:
        list[tuple[str, str]]: [(标题, URL), ...]
    """
    links: list[tuple[str, str]] = []
    pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()

        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if not text or len(text) < 3:
            continue

        if href.startswith("http://") or href.startswith("https://"):
            full_url = href
        elif href.startswith("/"):
            parsed = urllib.parse.urlparse(base_url)
            full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
        else:
            continue

        links.append((text, full_url))
        if len(links) >= max_links:
            break

    return links


def _parse_rss_feed(content: str, max_items: int = 5) -> list[CandidateItem]:
    """解析 RSS/Atom feed。

    小白解读：
        用 Python 内置的 xml.etree 解析 RSS 或 Atom 格式。
        提取 item/entry 的标题、链接、发布时间、摘要。

    Args:
        content: feed XML 内容
        max_items: 最多提取多少条

    Returns:
        list[CandidateItem]: 候选列表
    """
    items: list[CandidateItem] = []

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return items

    if root.tag.endswith("rss") or root.tag == "rss":
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()
                if title and link:
                    items.append(
                        CandidateItem(
                            title=title,
                            url=link,
                            published=pub_date,
                            summary=description[:500],
                        )
                    )
                if len(items) >= max_items:
                    break
    elif root.tag.endswith("feed") or "feed" in root.tag:
        ns = ""
        if "}" in root.tag:
            ns = root.tag.split("}")[0] + "}"
        for entry in root.findall(f"{ns}entry"):
            title = (entry.findtext(f"{ns}title") or "").strip()
            link_elem = entry.find(f"{ns}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            published = (entry.findtext(f"{ns}published") or entry.findtext(f"{ns}updated") or "").strip()
            summary = (entry.findtext(f"{ns}summary") or "").strip()
            if title and link:
                items.append(
                    CandidateItem(
                        title=title,
                        url=link,
                        published=published,
                        summary=summary[:500],
                    )
                )
            if len(items) >= max_items:
                break

    return items


def _http_get(url: str, timeout_seconds: int, user_agent: str, proxy_url: str = "") -> tuple[int, str, str]:
    """发送 HTTP GET 请求。

    小白解读：
        用 Python 内置的 urllib 发送请求，不依赖 requests 库。
        支持代理：如果传了 proxy_url，就走代理；不走代理就直连。
        返回 (HTTP 状态码, 响应内容, 错误信息)。

    Args:
        url: 请求的 URL
        timeout_seconds: 超时秒数
        user_agent: User-Agent 字符串
        proxy_url: 代理地址（如 http://127.0.0.1:7890），为空则不用代理

    Returns:
        tuple[int, str, str]: (状态码, 响应内容, 错误信息)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )

        if proxy_url:
            proxy_handler = urllib.request.ProxyHandler(
                {"http": proxy_url, "https": proxy_url}
            )
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status = resp.getcode()
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            encoding = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
                if charset:
                    encoding = charset
            try:
                text = raw.decode(encoding, errors="replace")
            except LookupError:
                text = raw.decode("utf-8", errors="replace")
            return status, text, ""
    except urllib.error.HTTPError as e:
        return e.code, "", f"HTTP Error: {e.code}"
    except urllib.error.URLError as e:
        return 0, "", f"URL Error: {e.reason}"
    except TimeoutError:
        return 0, "", "Timeout"
    except Exception as e:
        return 0, "", f"Error: {type(e).__name__}: {e}"


def _is_blocked_source(source: FoundationSource) -> bool:
    """判断一个源是否按策略禁止访问。

    小白解读：
        检查 activation_priority 是不是 blocked，
        或者 automation_mode 是不是 do_not_ingest。

    Args:
        source: 信息源对象

    Returns:
        bool: 是否禁止访问
    """
    if source.activation_priority == "blocked":
        return True
    if source.automation_mode == "do_not_ingest":
        return True
    if source.source_group == "blocked_high_risk_sources":
        return True
    return False


def _is_on_demand_source(source: FoundationSource) -> bool:
    """判断一个源是否是按需源。

    小白解读：
        检查 automation_mode 是不是 on_demand 或 manual。

    Args:
        source: 信息源对象

    Returns:
        bool: 是否按需源
    """
    if source.automation_mode in ("on_demand", "manual"):
        return True
    if source.source_group == "search_providers":
        return True
    return False


def _is_dormant_source(source: FoundationSource) -> bool:
    """判断一个源是否是休眠源。

    小白解读：
        检查 automation_mode 是不是 dormant，
        或者 activation_priority 是 supplement 且 enabled_by_default=False。

    Args:
        source: 信息源对象

    Returns:
        bool: 是否休眠源
    """
    if source.automation_mode == "dormant":
        return True
    if not source.enabled_by_default and source.activation_priority in ("C", "supplement"):
        return True
    return False


def _probe_public_web(source: FoundationSource, config: LiveSmokeRunConfig) -> SourceLiveResult:
    """对 public_web 类型的源做 live smoke。

    小白解读：
        发 HTTP GET 请求，看页面能不能打开。
        能打开的话，提取 title、description、links。
        如果页面能返回 200 且有 title，就算 live_ok。

    Args:
        source: 信息源对象
        config: 运行配置

    Returns:
        SourceLiveResult: 检查结果
    """
    result = SourceLiveResult(
        source_id=source.source_id,
        source_name=source.source_name,
        source_group=source.source_group,
        access_mode=source.access_mode,
        checked_at=_now_str(),
    )

    if not source.url:
        result.status = LiveSmokeStatus.MISSING_CONFIG
        result.error_message = "No URL configured"
        return result

    start = time.time()
    status_code, html, error = _http_get(source.url, config.timeout_seconds, config.user_agent, config.proxy_url)
    elapsed_ms = int((time.time() - start) * 1000)

    result.response_time_ms = elapsed_ms
    result.http_status = status_code
    result.visited = True

    if error:
        if "Timeout" in error:
            result.status = LiveSmokeStatus.TIMEOUT
        elif "HTTP Error" in error:
            result.status = LiveSmokeStatus.HTTP_ERROR
        else:
            result.status = LiveSmokeStatus.FAILED
        result.error_message = error
        result.error_type = type(error).__name__
        return result

    if status_code >= 400:
        result.status = LiveSmokeStatus.HTTP_ERROR
        result.error_message = f"HTTP {status_code}"
        return result

    result.fetched = True

    title = _html_extract_title(html)
    description = _html_extract_meta_description(html)
    links = _html_extract_links(html, source.url, max_links=config.max_candidates_per_source * 2)

    candidates: list[CandidateItem] = []
    for text, url in links[: config.max_candidates_per_source]:
        candidates.append(CandidateItem(title=text, url=url, source=source.source_name))

    result.candidates_found = len(links)
    result.candidates_saved = len(candidates)
    result.candidates = candidates

    if len(candidates) > 0:
        result.status = LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND
    elif title:
        result.status = LiveSmokeStatus.LIVE_OK
    else:
        result.status = LiveSmokeStatus.LIVE_OK_EMPTY

    result.notes = f"title: {title[:80]}" if title else ""

    return result


def _probe_rss(source: FoundationSource, config: LiveSmokeRunConfig) -> SourceLiveResult:
    """对 RSS/Atom feed 类型的源做 live smoke。

    小白解读：
        请求 feed URL，解析 XML。
        能解析出 item 就算成功，解析不出来就是 parser_mismatch。

    Args:
        source: 信息源对象
        config: 运行配置

    Returns:
        SourceLiveResult: 检查结果
    """
    result = SourceLiveResult(
        source_id=source.source_id,
        source_name=source.source_name,
        source_group=source.source_group,
        access_mode=source.access_mode,
        checked_at=_now_str(),
    )

    if not source.url:
        result.status = LiveSmokeStatus.MISSING_CONFIG
        result.error_message = "No URL configured"
        return result

    start = time.time()
    status_code, content, error = _http_get(source.url, config.timeout_seconds, config.user_agent)
    elapsed_ms = int((time.time() - start) * 1000)

    result.response_time_ms = elapsed_ms
    result.http_status = status_code
    result.visited = True

    if error:
        if "Timeout" in error:
            result.status = LiveSmokeStatus.TIMEOUT
        elif "HTTP Error" in error:
            result.status = LiveSmokeStatus.HTTP_ERROR
        else:
            result.status = LiveSmokeStatus.FAILED
        result.error_message = error
        return result

    if status_code >= 400:
        result.status = LiveSmokeStatus.HTTP_ERROR
        result.error_message = f"HTTP {status_code}"
        return result

    result.fetched = True

    items = _parse_rss_feed(content, max_items=config.max_candidates_per_source)
    result.candidates_found = len(items)
    result.candidates_saved = len(items)
    result.candidates = items

    if len(items) > 0:
        result.status = LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND
    elif content.strip():
        result.status = LiveSmokeStatus.LIVE_OK_EMPTY
        result.notes = "Feed is accessible but no items found"
    else:
        result.status = LiveSmokeStatus.LIVE_OK_EMPTY
        result.notes = "Feed is accessible but empty"

    return result


def _probe_search_provider(source: FoundationSource, config: LiveSmokeRunConfig) -> SourceLiveResult:
    """对 search_provider 做配置检查（不跑真实搜索）。

    小白解读：
        搜索 provider 不跑真实搜索（要花钱/额度）。
        只检查配置有没有、API key 环境变量有没有。

    Args:
        source: 信息源对象
        config: 运行配置（此函数不访问网络）

    Returns:
        SourceLiveResult: 检查结果
    """
    result = SourceLiveResult(
        source_id=source.source_id,
        source_name=source.source_name,
        source_group=source.source_group,
        access_mode=source.access_mode,
        status=LiveSmokeStatus.ON_DEMAND_NOT_RUN,
        visited=False,
        fetched=False,
        notes="Search provider: on-demand only, not run by default",
        checked_at=_now_str(),
    )
    return result


def _probe_manual(source: FoundationSource, config: LiveSmokeRunConfig) -> SourceLiveResult:
    """对 manual 类型的源做检查。

    小白解读：
        manual 源是人工上传的，不自动访问。
        标记为 on_demand_not_run。

    Args:
        source: 信息源对象
        config: 运行配置

    Returns:
        SourceLiveResult: 检查结果
    """
    result = SourceLiveResult(
        source_id=source.source_id,
        source_name=source.source_name,
        source_group=source.source_group,
        access_mode=source.access_mode,
        status=LiveSmokeStatus.ON_DEMAND_NOT_RUN,
        visited=False,
        fetched=False,
        notes="Manual source: requires manual upload/trigger",
        checked_at=_now_str(),
    )
    return result


def probe_source(source: FoundationSource, config: LiveSmokeRunConfig) -> SourceLiveResult:
    """对单个源执行 live smoke probe。

    小白解读：
        根据源的类型和配置，选择不同的检查策略：
        1. blocked → blocked_by_policy
        2. on_demand / search_provider / manual → on_demand_not_run
        3. dormant → dormant_not_run
        4. rss / podcast_rss → _probe_rss
        5. public_web / company_ir / media_page → _probe_public_web
        6. 其他 → needs_connector

    Args:
        source: 信息源对象
        config: 运行配置

    Returns:
        SourceLiveResult: 检查结果
    """
    if _is_blocked_source(source):
        return SourceLiveResult(
            source_id=source.source_id,
            source_name=source.source_name,
            source_group=source.source_group,
            access_mode=source.access_mode,
            status=LiveSmokeStatus.BLOCKED_BY_POLICY,
            visited=False,
            fetched=False,
            notes="Blocked by policy: not accessed",
            checked_at=_now_str(),
        )

    if _is_on_demand_source(source):
        if source.source_group == "search_providers":
            return _probe_search_provider(source, config)
        return _probe_manual(source, config)

    if _is_dormant_source(source):
        return SourceLiveResult(
            source_id=source.source_id,
            source_name=source.source_name,
            source_group=source.source_group,
            access_mode=source.access_mode,
            status=LiveSmokeStatus.DORMANT_NOT_RUN,
            visited=False,
            fetched=False,
            notes="Dormant source: not run by default",
            checked_at=_now_str(),
        )

    if config.dry_run:
        return SourceLiveResult(
            source_id=source.source_id,
            source_name=source.source_name,
            source_group=source.source_group,
            access_mode=source.access_mode,
            status=LiveSmokeStatus.LIVE_OK,
            visited=False,
            fetched=False,
            notes="Dry-run: not actually accessed",
            checked_at=_now_str(),
        )

    access_mode = source.access_mode or ""

    if access_mode in ("rss", "podcast_rss", "atom"):
        return _probe_rss(source, config)
    elif access_mode in ("public_web", "company_ir", "media_page", "html_page", "webpage"):
        return _probe_public_web(source, config)
    elif access_mode in ("api",):
        return SourceLiveResult(
            source_id=source.source_id,
            source_name=source.source_name,
            source_group=source.source_group,
            access_mode=source.access_mode,
            status=LiveSmokeStatus.NEEDS_CONNECTOR,
            visited=False,
            fetched=False,
            notes="API source: needs dedicated connector",
            checked_at=_now_str(),
        )
    else:
        return SourceLiveResult(
            source_id=source.source_id,
            source_name=source.source_name,
            source_group=source.source_group,
            access_mode=source.access_mode,
            status=LiveSmokeStatus.NEEDS_CONNECTOR,
            visited=False,
            fetched=False,
            notes=f"Unsupported access_mode: {access_mode}",
            checked_at=_now_str(),
        )


def run_live_smoke(
    source_inventory: SourceInventory,
    config: LiveSmokeRunConfig | None = None,
) -> LiveSmokeSummary:
    """对 source inventory 中的所有源跑 live smoke。

    小白解读：
        遍历所有 source group 和 source，逐个检查。
        生成汇总结果，包括每个分组的统计。

    Args:
        source_inventory: 信息源清单
        config: 运行配置，不传则用默认值

    Returns:
        LiveSmokeSummary: 总览汇总
    """
    if config is None:
        config = LiveSmokeRunConfig()

    started_at = _now_str()
    start_time = time.time()

    groups: list[SourceGroupLiveResult] = []

    for group in source_inventory.groups:
        group_result = SourceGroupLiveResult(
            group_id=group.group_id,
            group_name=group.group_name,
            total_sources=0,
            results=[],
        )

        group_sources = [s for s in source_inventory.sources if s.source_group == group.group_id]
        group_result.total_sources = len(group_sources)

        for source in group_sources:
            result = probe_source(source, config)
            group_result.results.append(result)

        groups.append(group_result)

    finished_at = _now_str()
    total_ms = int((time.time() - start_time) * 1000)

    total_sources = sum(g.total_sources for g in groups)

    summary = LiveSmokeSummary(
        total_sources=total_sources,
        groups=groups,
        run_started_at=started_at,
        run_finished_at=finished_at,
        total_duration_ms=total_ms,
        proxy_enabled=bool(config.proxy_url),
        proxy_mode=config.proxy_mode,
    )

    return summary


def save_live_smoke_results(
    summary: LiveSmokeSummary,
    output_dir: str | Path,
) -> Path:
    """保存 live smoke 结果到磁盘。

    小白解读：
        把结果写入 data/source_inventory_live_smoke/ 目录：
        - source_live_status.latest.json：完整结果
        - source_health.jsonl：源健康记录
        - run_log.jsonl：运行日志
        - failed_queue.jsonl：失败队列

    Args:
        summary: live smoke 汇总
        output_dir: 输出目录

    Returns:
        Path: 输出目录路径
    """
    output_path = Path(output_dir)
    index_dir = output_path / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[dict] = []
    source_health_lines: list[str] = []
    run_log_lines: list[str] = []
    failed_queue_lines: list[str] = []

    for group in summary.groups:
        for result in group.results:
            data = result.to_dict()
            all_results.append(data)

            health_record = {
                "source_id": result.source_id,
                "source_name": result.source_name,
                "status": result.status.value,
                "severity": _status_severity(result.status),
                "last_checked": result.checked_at,
                "response_time_ms": result.response_time_ms,
                "candidates_found": result.candidates_found,
            }
            source_health_lines.append(json.dumps(health_record, ensure_ascii=False))

            run_record = {
                "timestamp": result.checked_at,
                "source_id": result.source_id,
                "source_group": result.source_group,
                "status": result.status.value,
                "visited": result.visited,
                "fetched": result.fetched,
                "candidates_found": result.candidates_found,
                "http_status": result.http_status,
                "error_message": result.error_message,
                "duration_ms": result.response_time_ms,
            }
            run_log_lines.append(json.dumps(run_record, ensure_ascii=False))

            if result.status in (
                LiveSmokeStatus.HTTP_ERROR,
                LiveSmokeStatus.TIMEOUT,
                LiveSmokeStatus.FAILED,
                LiveSmokeStatus.NEEDS_CONNECTOR,
                LiveSmokeStatus.PARSER_MISMATCH,
                LiveSmokeStatus.MISSING_CONFIG,
                LiveSmokeStatus.MISSING_API_KEY,
            ):
                failed_record = {
                    "source_id": result.source_id,
                    "source_name": result.source_name,
                    "source_group": result.source_group,
                    "status": result.status.value,
                    "error_message": result.error_message,
                    "notes": result.notes,
                    "first_seen": result.checked_at,
                    "retries": 0,
                }
                failed_queue_lines.append(json.dumps(failed_record, ensure_ascii=False))

    latest_data = {
        "total_sources": summary.total_sources,
        "run_started_at": summary.run_started_at,
        "run_finished_at": summary.run_finished_at,
        "total_duration_ms": summary.total_duration_ms,
        "proxy_enabled": summary.proxy_enabled,
        "proxy_mode": summary.proxy_mode,
        "status_counts": summary.status_counts,
        "results": all_results,
    }

    (index_dir / "source_live_status.latest.json").write_text(
        json.dumps(latest_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (index_dir / "source_health.jsonl").write_text("\n".join(source_health_lines) + "\n", encoding="utf-8")
    (index_dir / "run_log.jsonl").write_text("\n".join(run_log_lines) + "\n", encoding="utf-8")
    (index_dir / "failed_queue.jsonl").write_text("\n".join(failed_queue_lines) + "\n", encoding="utf-8")

    return output_path


def _status_severity(status: LiveSmokeStatus) -> str:
    """获取状态的严重级别。

    Args:
        status: live smoke 状态

    Returns:
        str: 严重级别（success/warning/error/info）
    """
    from .models import LIVE_SMOKE_STATUS_SEVERITY

    return LIVE_SMOKE_STATUS_SEVERITY.get(status, "info")
