"""
Content Validity Auditor Module (M3C-5A4)
==========================================

功能说明（小白解读）：
    这个模块用于审计 21 个 trial_v2 源的内容有效性，
    并支持构建 92 源内容有效性总表。
    它会：
    1. 读取配置文件和 trial_v2 allowlist
    2. 对每个源发送 HTTP 请求
    3. 解析 HTML 页面
    4. 抽取候选内容（如文章链接、新闻标题等）
    5. 判断内容是否有效、相关、近期
    6. 识别噪音页面（登录页、Cookie页、空页面等）
    7. 输出结构化的审计结果
    8. 构建 92 源内容有效性总表（SourceContentMatrixRow）

使用方法：
    from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
    
    auditor = ContentValidityAuditor(
        config_path='configs/foundation_content_validity_audit.example.yaml',
        allowlist_path='configs/foundation_trial_v2_allowlist.example.yaml'
    )
    results = auditor.audit_all_sources()

矩阵构建：
    from opc_foundation.source_inventory.content_validity import build_source_content_validity_matrix
    matrix = build_source_content_validity_matrix(
        inventory_path='data/foundation_source_inventory/index/source_inventory.jsonl',
        allowlist_path='configs/foundation_trial_v2_allowlist.example.yaml',
    )

Author: OPC Foundation
Version: 2.0
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import yaml

# 可选的 HTTP 和 HTML 解析库
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ContentCandidate:
    """
    内容候选项。
    
    Attributes:
        title: 内容标题
        url: 内容链接
        published_at: 发布时间（如果有）
        snippet: 内容摘要
        content_type: 内容类型（news/research/ir/podcast/rating/market_update/unknown）
        relevance: 相关性（high/medium/low）
        freshness: 新鲜度（fresh/stale/unknown）
    """
    title: str = ""
    url: str = ""
    published_at: str = ""
    snippet: str = ""
    content_type: str = "unknown"
    relevance: str = "unknown"
    freshness: str = "unknown"


@dataclass
class ContentAuditResult:
    """
    内容审计结果。
    
    Attributes:
        source_id: 源ID
        source_name: 源名称
        source_group: 源分组
        is_consolidated: 是否为合并源
        member_source_ids: 成员源ID列表
        expected_content_goal: 期望的内容目标
        input_url: 输入的URL
        final_url: 最终URL（跟随重定向后）
        http_status: HTTP状态码
        page_title: 页面标题
        page_language: 页面语言
        technical_status: 技术状态（reachable/failed/watch）
        candidate_count: 候选内容总数
        valid_candidate_count: 有效候选数量
        fresh_candidate_count: 近期候选数量
        relevant_candidate_count: 相关候选数量
        duplicate_candidate_count: 重复候选数量
        noise_flags: 噪音标记列表
        sample_candidates: 示例候选内容列表
        content_score: 内容评分（0-100）
        content_status: 内容状态（content_ready/content_watch/content_reject/technical_only）
        reason: 判定原因
        recommended_action: 推荐动作
    """
    source_id: str = ""
    source_name: str = ""
    source_group: str = ""
    is_consolidated: bool = False
    member_source_ids: list = field(default_factory=list)
    expected_content_goal: str = ""
    input_url: str = ""
    final_url: str = ""
    http_status: int = 0
    page_title: str = ""
    page_language: str = "unknown"
    technical_status: str = "failed"
    candidate_count: int = 0
    valid_candidate_count: int = 0
    fresh_candidate_count: int = 0
    relevant_candidate_count: int = 0
    duplicate_candidate_count: int = 0
    noise_flags: list = field(default_factory=list)
    sample_candidates: list = field(default_factory=list)
    content_score: int = 0
    content_status: str = "technical_only"
    reason: str = ""
    recommended_action: str = "backlog"

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        result = asdict(self)
        result['sample_candidates'] = [asdict(c) if isinstance(c, ContentCandidate) else c for c in self.sample_candidates]
        return result


@dataclass
class SourceContentMatrixRow:
    """
    92 源内容有效性矩阵行。
    
    Attributes:
        source_id: 源ID
        source_name: 源名称
        source_group: 源分组
        source_inventory_count: 源 inventory 数量（固定为 92）
        is_operational_trial_v2: 是否为 operational trial_v2 源
        expected_content_goal: 期望内容目标描述
        current_technical_bucket: 当前技术分桶
        content_validation_scope: 内容验证范围 (deep_audit/matrix_only/excluded/on_demand_only)
        content_validation_status: 内容验证状态 (content_ready/content_watch/content_reject/technical_only/not_audited)
        not_audited_reason: 未审计原因（空字符串如果已审计）
        recommended_next_action: 推荐后续动作 (include_in_trial_v2/watch/reject/backlog/keep_excluded/keep_on_demand/needs_connector)
    """
    source_id: str = ""
    source_name: str = ""
    source_group: str = ""
    source_inventory_count: int = 92
    is_operational_trial_v2: bool = False
    expected_content_goal: str = ""
    current_technical_bucket: str = ""
    content_validation_scope: str = "matrix_only"
    content_validation_status: str = "not_audited"
    not_audited_reason: str = ""
    recommended_next_action: str = "backlog"

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return asdict(self)


# =============================================================================
# 独立函数：噪音检测、内容评分、内容状态分类
# =============================================================================

# 严重噪音集合，匹配到任何一个即直接 reject
_SEVERE_NOISE_FLAGS = {
    "login_page", "paywall", "blocked_page",
    "app_download_page", "empty_page", "garbled_text",
}

# 导航链接噪音排除列表（用于 extract_candidates_from_html）
_NOISE_LINK_PATTERNS = re.compile(
    r'(?i)\b(home|about|contact|careers?|privacy|terms?|cookie|'
    r'subscribe|sign\s*in?|login|help|faq|sitemap|rss|feed|'
    r'investor\s*relations|advertising|legal|disclaimer)\b'
)


def _extract_date_from_text(text: str) -> str:
    """从文本中提取日期字符串。
    支持格式：
    - "Jun 15, 2026"
    - "2026-06-15"
    - "June 29, 2026"
    - "6月29日"
    - "7月1日 22:16"（中文日期+时间）
    - "07-01"（月-日格式）
    - "1小时前"、"5分钟前"、"昨天"（相对时间）
    - "34 min read"（不视为日期，返回空）
    """
    if not text:
        return ""
    
    # 英文月份格式（如 Jun 15, 2026 / June 29, 2026）
    m = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', text)
    if m:
        return m.group(0).rstrip(',')
    # ISO 格式
    m = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if m:
        return m.group(0)
    # 中文格式：X月X日 HH:MM
    m = re.search(r'\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}', text)
    if m:
        return m.group(0)
    # 中文格式：X月X日
    m = re.search(r'\d{1,2}月\d{1,2}日', text)
    if m:
        return m.group(0)
    # 月-日格式：07-01
    m = re.search(r'\b\d{2}-\d{2}\b', text)
    if m:
        return m.group(0)
    # 相对时间：X小时前、X分钟前、昨天
    m = re.search(r'\d+\s*小时前', text)
    if m:
        return m.group(0)
    m = re.search(r'\d+\s*分钟前', text)
    if m:
        return m.group(0)
    m = re.search(r'昨天', text)
    if m:
        return m.group(0)
    m = re.search(r'今天', text)
    if m:
        return m.group(0)
    m = re.search(r'\d{1,2}:\d{2}', text)  # HH:MM
    if m:
        return m.group(0)
    return ""


def classify_noise_flags(page_text: str, page_title: str, http_status: int) -> list[str]:
    """
    检测页面噪音标志。返回标志列表。
    
    Args:
        page_text: 页面正文文本
        page_title: 页面标题
        http_status: HTTP 状态码
        
    Returns:
        噪音标志列表，可能包含：
        login_page, paywall, cookie_only, blocked_page,
        app_download_page, navigation_only, marketing_only,
        empty_page, unrelated_page, garbled_text
    """
    flags = []
    text_lower = page_text.lower()
    title_lower = page_title.lower()

    # --- blocked_page: HTTP 状态码异常 或页面内容明确拒绝访问 ---
    if http_status in (403, 451, 503) or http_status >= 500:
        flags.append("blocked_page")
    blocked_keywords = [
        "access denied", "forbidden", "blocked", "access restricted",
        "service unavailable", "you don't have permission",
    ]
    if any(kw in text_lower for kw in blocked_keywords):
        if "blocked_page" not in flags:
            flags.append("blocked_page")

    # --- login_page: 多个登录相关关键词集中出现 ---
    login_keywords = [
        "sign in", "sign-in", "signin", "log in", "log-in",
        "login", "password", "username", "email address",
        "remember me", "forgot password", "create account",
    ]
    login_hits = sum(1 for kw in login_keywords if kw in text_lower)
    if login_hits >= 3:
        flags.append("login_page")

    # --- paywall: 付费墙/订阅要求 ---
    paywall_keywords = [
        "paywall", "premium", "subscription required",
        "subscribe to continue", "subscribe to read",
        "subscribe now to access", "members only",
        "upgrade to access", "sign up to continue",
        "free trial", "subscribe to unlock",
    ]
    if any(kw in text_lower for kw in paywall_keywords):
        flags.append("paywall")

    # --- cookie_only: cookie consent 占据页面主要内容 ---
    cookie_keywords = [
        "cookie consent", "accept cookies", "cookie policy",
        "manage cookies", "we use cookies", "this site uses cookies",
        "cookie preferences", "gdpr consent",
    ]
    cookie_hits = sum(1 for kw in cookie_keywords if kw in text_lower)
    # 如果 cookie 相关词出现次数 >= 3 且页面有效文本很短
    clean_text = re.sub(r'\s+', ' ', text_lower).strip()
    if cookie_hits >= 3 and len(clean_text) < 500:
        flags.append("cookie_only")

    # --- app_download_page: 引导用户下载 app ---
    app_keywords = [
        "download our app", "download the app", "get the app",
        "app store", "google play", "available on the app store",
        "open in app", "install app", "mobile app",
    ]
    if any(kw in text_lower for kw in app_keywords):
        flags.append("app_download_page")

    # --- navigation_only: 只有导航链接，没有实际内容 ---
    clean_text = re.sub(r'\s+', ' ', text_lower).strip()
    # 如果页面文本很少（< 200 字符），可能是纯导航
    link_count = len(re.findall(r'<a\s', page_text))
    if len(clean_text) < 200 and link_count > 0:
        flags.append("navigation_only")

    # --- marketing_only: 纯产品营销 ---
    marketing_keywords = [
        "pricing", "plans starting at", "free trial",
        "request a demo", "book a demo", "schedule a demo",
        "get started", "try for free", "start free trial",
        "enterprise pricing", "contact sales",
    ]
    marketing_hits = sum(1 for kw in marketing_keywords if kw in text_lower)
    if marketing_hits >= 3:
        flags.append("marketing_only")

    # --- empty_page: 页面文本很少 ---
    if len(clean_text) < 50:
        flags.append("empty_page")

    # --- garbled_text: 乱码或非目标语言检测 ---
    # 检测过多的不可打印字符或连续重复字符
    non_printable = sum(1 for c in page_text if ord(c) < 32 and c not in '\n\r\t')
    if non_printable > len(page_text) * 0.05:
        flags.append("garbled_text")
    # 检测连续重复字符（如 &#xfffd; 乱码模式）
    if re.search(r'(.)\1{10,}', page_text):
        flags.append("garbled_text")
    # 检测大量 unicode 替换字符
    if page_text.count('\ufffd') > 5:
        flags.append("garbled_text")

    # --- unrelated_page: 页面标题与内容严重不匹配 ---
    # 如果标题中有 domain 相关词但正文中没有对应内容
    if title_lower and len(clean_text) > 100:
        title_words = set(re.findall(r'[a-z]{3,}', title_lower))
        if title_words:
            content_words = set(re.findall(r'[a-z]{3,}', clean_text))
            overlap = title_words & content_words
            # 标题关键词在正文中几乎不出现
            if len(title_words) > 2 and len(overlap) == 0:
                flags.append("unrelated_page")

    return flags


def score_content_validity(
    page_match: int,       # 0-25: 页面目标匹配度
    candidate_count: int,  # 0-20: 候选数量
    relevance: int,        # 0-25: 候选相关性
    freshness: int,         # 0-15: 时间/新鲜度
    noise_penalty: int,     # 0 to -25: 噪音惩罚
    structure: int,         # 0-15: 结构化程度
) -> int:
    """
    计算内容有效性分数 0-100。
    
    各维度满分合计：25 + 20 + 25 + 15 + 0 + 15 = 100。
    noise_penalty 为负值，直接叠加后 clamp 到 [0, 100]。
    
    Args:
        page_match: 页面目标匹配度 (0-25)
        candidate_count: 候选数量得分 (0-20)
        relevance: 候选相关性得分 (0-25)
        freshness: 时间/新鲜度得分 (0-15)
        noise_penalty: 噪音惩罚 (0 to -25)
        structure: 结构化程度得分 (0-15)
        
    Returns:
        内容有效性分数 (0-100)
    """
    raw = page_match + candidate_count + relevance + freshness + noise_penalty + structure
    return max(0, min(100, raw))


def classify_content_status(
    content_score: int,
    valid_candidate_count: int,
    noise_flags: list[str],
) -> str:
    """
    根据分数和候选数判定 content_status。
    
    Args:
        content_score: 内容有效性分数 (0-100)
        valid_candidate_count: 有效候选数量
        noise_flags: 噪音标志列表
        
    Returns:
        content_status 字符串:
        content_ready / content_watch / content_reject / technical_only
    """
    # 严重噪音直接 reject
    if any(f in _SEVERE_NOISE_FLAGS for f in noise_flags):
        return "content_reject"

    if content_score >= 70 and valid_candidate_count >= 2:
        return "content_ready"
    if content_score >= 45 and valid_candidate_count >= 1:
        return "content_watch"
    if valid_candidate_count == 0 and content_score > 0:
        return "technical_only"
    return "content_reject"


# =============================================================================
# 独立函数：HTML 候选内容提取
# =============================================================================

# 内容类型与源分组的映射关系
_SOURCE_GROUP_CONTENT_TYPE_MAP = {
    "news_aggregators": "news",
    "investment_banks_research": "research",
    "us_government_economic": "market_update",
    "sec_regulatory": "ir",
    "central_banks": "market_update",
    "think_tanks": "research",
    "industry_associations": "news",
    "stock_exchanges": "market_update",
    "credit_rating_agencies": "rating",
    "podcasts": "podcast",
    "search_providers": "unknown",
    "community_dev_signals": "unknown",
    "blockchain_explorers": "market_update",
}

# =============================================================================
# 源特定选择器映射
# =============================================================================
# 每个源对应 (CSS选择器, 提取类型) 列表
# 当源匹配时，优先使用这些选择器而非通用选择器
_SOURCE_SPECIFIC_SELECTORS: dict[str, list[tuple[str, str]]] = {
    # === Goldman Sachs 系列 ===
    # GS 页面文章卡片是 a.gs-card，内含 .gs-card-eyebrow（分类）和 .gs-card-title（标题）
    # 日期嵌入在链接文本末尾，格式如 "Jun 15, 2026"
    "goldman_sachs_insights": [
        ("a[href*='/insights/articles/']", "gs_article"),
        ("a[href*='/insights/the-markets/']", "gs_article"),
        ("a[href*='/insights/top-of-mind/']", "gs_article"),
    ],
    "goldman_sachs_reports": [
        ("a[href*='/insights/articles/']", "gs_article"),
        ("a[href*='/insights/the-markets/']", "gs_article"),
    ],
    "goldman_sachs_top_of_mind": [
        ("a[href*='/insights/articles/']", "gs_article"),
        ("a[href*='/insights/top-of-mind/']", "gs_article"),
    ],
    "goldman_sachs_research": [
        ("a[href*='/insights/articles/']", "gs_article"),
    ],
    "goldman_sachs_podcasts": [
        ("a.gs-card", "gs_card"),
    ],

    # === JP Morgan ===
    # JP Morgan 使用 li.article-card 包裹文章，h3 为标题
    "jp_morgan": [
        ("li.article-card", "jp_article"),
        ("a.content-headline", "jp_headline"),
    ],

    # === Morgan Stanley ===
    # MS 使用 AEM cmp-storycard 组件
    "morgan_stanley": [
        ("a.cmp-storycard__link", "ms_storycard"),
        ("a.link-selector-4up", "ms_4up"),
    ],

    # === Business Insider ===
    # BI 首页文章链接为相对路径（如 /slug-text-2026-7），不含域名
    # article.tout / feed-list 等均为 JS 渲染，SSR 中不可用
    # 策略：匹配 a[href^='/'] 中标题 >= 20 字符且 URL 含年月日期的文章链接
    "business_insider": [
        ("a[href^='/']", "bi_relative_article"),
    ],

    # === Reuters ===
    # Reuters 使用 media-story-card 组件
    "reuters": [
        ("article.media-story-card", "reuters_article"),
        ("a.media-story-card__heading", "reuters_heading"),
    ],

    # === Merck IR ===
    # Merck 新闻链接格式为 /news/，日期是独立的 <a> 标签在标题之前
    "merck_ir": [
        ("a[href*='/news/']", "merck_news"),
        ("a[href*='/events/']", "merck_events"),
        ("a[href*='/presentations/']", "merck_presentation"),
    ],

    # === 财联社 ===
    # /telegraph 页面纯 JS 渲染，SSR 无内容，改用主页 https://www.cls.cn/
    # 新闻条目结构：div 容器内含 div.c-999（时间，"M月D日 HH:MM"）+ a[href^='/detail/']（新闻链接）
    # 使用容器级选择器提取，一次取出标题+时间
    "cls_cn": [
        ("div.m-b-10.b-b-w-1", "cls_news_container"),
    ],

    # === 格隆汇 ===
    # M3C-5B1.1a: 改用容器级选择器 li.article-li
    # 结构: li.article-li > div.article-li__main > a.detail-left[href="/p/"]
    #       + section.detail-right > section.source-time（含时间如 "36分钟前"）
    "gelonghui": [
        ("li.article-li", "glh_container"),
    ],

    # === 智通财经 ===
    # 新闻条目：div.info-list-item > div.info-item-content > div.info-item-content-title > a
    # 时间：div.info-item-content-operat > span:first-child（"1小时前"/"07-01"）
    # 摘要：div.info-item-content-desc
    "zhitong_caijing": [
        ("div.info-list-item", "ztc_item"),
    ],

    # === Benzinga ===
    "benzinga_analyst_ratings": [
        ("a.analyst-rating-card", "benzinga_rating"),
        ("table.analyst-ratings-table a", "benzinga_table"),
    ],

    # === 中国基金报 ===
    "china_fund_news": [
        ("a[href*='/article/']", "cfn_article"),
    ],
}

# 智通财经导航文本过滤集合
_ZTC_NAV_TEXTS = {
    "推荐", "港股", "美股", "沪深", "要闻", "基金",
    "公告", "新股", "研究", "公司", "ESG", "市场",
}


def extract_candidates_from_html(
    html: str,
    base_url: str,
    max_candidates: int = 5,
    source_group: str = "",
    source_id: str = "",
) -> list[ContentCandidate]:
    """
    从 HTML 中提取候选内容（独立函数，不依赖 ContentValidityAuditor 实例）。
    
    策略：
    0. 如果 source_id 匹配源特定选择器，优先使用源特定选择器提取
    1. 用 BeautifulSoup 解析
    2. 查找文章/新闻/研究链接（<a> 标签 + 周围文本）
    3. 查找列表项（<li> 中的链接）
    4. 排除噪音链接（Home/About/Contact/Careers/Privacy/Terms/Cookie/Subscribe/Sign In/Login）
    5. 提取 title（链接文本或周围 <h> 标签）
    6. 提取 snippet（链接周围的 <p> 文本，截断到 200 字符）
    7. 尝试从 URL 路径或周围文本推断 published_at
    8. 根据 source_group 推断 content_type
    9. 限制到 max_candidates 条
    
    Args:
        html: HTML 字符串
        base_url: 基础 URL（用于补全相对链接）
        max_candidates: 最大候选数量
        source_group: 源分组，用于推断 content_type
        source_id: 源 ID，用于匹配源特定选择器策略
        
    Returns:
        候选内容列表
    """
    if not HAS_BS4:
        logger.warning("BeautifulSoup 不可用，无法提取候选内容")
        return []

    candidates = []
    seen_urls = set()

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"解析 HTML 失败: {e}")
        return []

    # 根据 source_group 推断默认 content_type
    default_content_type = _SOURCE_GROUP_CONTENT_TYPE_MAP.get(source_group, "unknown")

    # =========================================================================
    # 源特定选择器策略：在通用选择器之前尝试
    # =========================================================================
    if source_id and source_id in _SOURCE_SPECIFIC_SELECTORS:
        source_selectors = _SOURCE_SPECIFIC_SELECTORS[source_id]
        source_candidates = []
        source_seen_urls = set()

        for css_selector, extraction_type in source_selectors:
            if len(source_candidates) >= max_candidates:
                break
            elements = soup.select(css_selector)
            for elem in elements:
                if len(source_candidates) >= max_candidates:
                    break
                try:
                    title = ""
                    published_at = ""
                    snippet = ""
                    category = ""

                    if extraction_type in ("gs_card", "gs_article"):
                        # GS 文章卡片（两种策略）
                        if extraction_type == "gs_card":
                            # 旧策略：从 .gs-card-eyebrow/.gs-card-title 提取
                            eyebrow = elem.select_one(".gs-card-eyebrow")
                            title_elem = elem.select_one(".gs-card-title")
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                category = eyebrow.get_text(strip=True) if eyebrow else ""
                                if category:
                                    snippet = f"[{category}] "
                                full_text = elem.get_text(strip=True)
                                published_at = _extract_date_from_text(full_text)
                                snippet += full_text[:200]
                        else:
                            # 新策略：a[href*='/insights/articles/'] 直接从链接文本提取
                            # GS SSR 输出中文章链接文本格式："{Category}{Title}{Date}"
                            # 例如 "EnergyWhy Oil Prices Could 'Grind Lower'...Jun 18, 2026"
                            link_text = elem.get_text(strip=True)
                            published_at = _extract_date_from_text(link_text)
                            title = link_text
                            # 移除末尾日期后，文本剩余部分就是 title（含前缀分类名）
                            if published_at:
                                title = link_text.replace(published_at, '').strip().rstrip(',')
                            snippet = link_text[:200]

                    elif extraction_type == "jp_article":
                        # JP Morgan 文章卡片：li.article-card 内的 h3 是标题
                        h3 = elem.find("h3")
                        if h3:
                            title = h3.get_text(strip=True)
                            full_text = elem.get_text(strip=True)
                            published_at = _infer_published_date(base_url, full_text)
                            # 获取 li 内的描述文本
                            for p in elem.find_all("p", recursive=False):
                                p_text = p.get_text(strip=True)
                                if len(p_text) > len(snippet):
                                    snippet = p_text

                    elif extraction_type == "jp_headline":
                        # JP Morgan 标题链接
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    elif extraction_type == "ms_storycard":
                        # Morgan Stanley storycard
                        h2 = elem.select_one("h2.cmp-title__text")
                        if h2:
                            title = h2.get_text(strip=True)
                        else:
                            title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    elif extraction_type == "ms_4up":
                        # Morgan Stanley 4up 链接
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    elif extraction_type == "bi_relative_article":
                        # Business Insider 文章链接（相对路径匹配）
                        # BI 首页文章为相对路径 /slug-text-YYYY-M，标题在 a 文本中
                        title = elem.get_text(strip=True)
                        href = elem.get("href", "")
                        if not title or len(title) < 20:
                            continue
                        # 跳过分类/标签/静态页面
                        skip_paths = ['/category', '/tag', '/page', '/search', '/author', '/about']
                        if any(href.startswith(sp) for sp in skip_paths):
                            continue
                        # 过滤导航/栏目名称（短文本匹配特定关键词时跳过）
                        nav_keywords = [
                            "subscribe", "newsletter", "sign in", "log in",
                            "privacy", "terms", "careers", "app store",
                            "get the app", "contact", "advertising",
                        ]
                        if any(nk in title.lower() for nk in nav_keywords):
                            continue
                        # 从 URL 路径提取日期（/slug-YYYY-M 或 /YYYY/M/）
                        published_at = _infer_published_date(href, "")
                        snippet = title[:200]
                        # 直接构建候选（已获取 href）
                        if not href or href.startswith('#') or href.startswith('javascript:'):
                            continue
                        full_url = urljoin(base_url, href).split('#')[0]
                        if full_url in source_seen_urls:
                            continue
                        source_seen_urls.add(full_url)
                        if _NOISE_LINK_PATTERNS.search(title):
                            continue
                        # BI 文章直接设为 news 类型（不依赖通用推断）
                        content_type = "news"
                        relevance = "high"
                        freshness = _classify_freshness(published_at) if published_at else "unknown"
                        source_candidates.append(ContentCandidate(
                            title=title,
                            url=full_url,
                            published_at=published_at,
                            snippet=snippet[:200],
                            content_type=content_type,
                            relevance=relevance,
                            freshness=freshness,
                        ))
                        continue

                    elif extraction_type in ("reuters_article", "reuters_heading"):
                        # Reuters 文章卡片
                        if extraction_type == "reuters_article":
                            heading = elem.select_one("a.media-story-card__heading")
                            title = heading.get_text(strip=True) if heading else elem.get_text(strip=True)
                        else:
                            title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    elif extraction_type in ("merck_news", "merck_events", "merck_presentation"):
                        if extraction_type == "merck_news":
                            # Merck 新闻链接：只取链接文本长度 > 15 的
                            link_text = elem.get_text(strip=True)
                            if len(link_text) > 15:
                                title = link_text
                            else:
                                continue
                        else:
                            # Merck 活动/演示文稿链接
                            title = elem.get_text(strip=True)

                        if not title or any(x in title for x in ["Icons /", "See full agenda", "MicrophoneWebcast"]):
                            continue

                        MERCK_NOISE = {
                            "See full agenda", "Icons /", "MicrophoneWebcast",
                            "News releases", "Events & presentations", "Events", "Presentations",
                            "Financial information", "SEC filings", "Stock information",
                            "Investor resources", "Investors overview", "Investors",
                        }
                        if title in MERCK_NOISE:
                            continue
                        if len(title) < 10:
                            continue

                    elif extraction_type == "cls_news_container":
                        # 财联社新闻容器（div.m-b-10.b-b-w-1）
                        # 结构：容器内 div.c-999 有时间（"M月D日 HH:MM"），
                        #       a[href^='/detail/'] 有新闻链接和标题
                        news_link = elem.find("a", attrs={"href": re.compile(r'^/detail/\d+')})
                        if not news_link:
                            continue
                        title = news_link.get_text(strip=True)
                        if not title or len(title) < 8:
                            continue
                        href = news_link.get("href", "")
                        # 在容器内查找时间 div（class 含 c-999）
                        time_div = elem.find("div", class_=re.compile(r'c-999'))
                        published_at = ""
                        if time_div:
                            published_at = time_div.get_text(strip=True)
                        # 过滤噪音（广告、下载、登录）
                        noise_kw = ["APP下载", "登录", "注册", "广告"]
                        if any(nk in title for nk in noise_kw):
                            continue
                        snippet = title[:200]
                        # 直接构建候选（已获取 href）
                        if not href or href.startswith('#') or href.startswith('javascript:'):
                            continue
                        full_url = urljoin(base_url, href).split('#')[0]
                        if full_url in source_seen_urls:
                            continue
                        source_seen_urls.add(full_url)
                        if _NOISE_LINK_PATTERNS.search(title):
                            continue
                        # CLS 财经新闻直接设为 market_update 类型
                        content_type = "market_update"
                        relevance = "high"
                        freshness = _classify_freshness(published_at) if published_at else "unknown"
                        source_candidates.append(ContentCandidate(
                            title=title,
                            url=full_url,
                            published_at=published_at,
                            snippet=snippet[:200],
                            content_type=content_type,
                            relevance=relevance,
                            freshness=freshness,
                        ))
                        continue

                    elif extraction_type in ("glh_article", "glh_container"):
                        # 格隆汇文章
                        # M3C-5B1.1a: glh_container 使用容器级选择器 li.article-li
                        # 结构: li.article-li > div.article-li__main
                        #   > a.detail-left[href="/p/"] (标题链接)
                        #   > section.detail-right > section.source-time (时间)
                        GELONGHUI_NOISE_TITLE = {
                            "登录", "注册", "下载APP", "APP下载", "广告", "隐私政策",
                            "免责声明", "联系我们", "搜索", "行情", "首页", "港股",
                            "美股", "沪深", "基金", "新股", "公告", "专栏", "要闻",
                            "推荐", "快讯", "热股", "龙虎榜", "榜单", "排行",
                            "更多", "查看更多", "点击下载", "立即下载", "APP",
                        }
                        GELONGHUI_NOISE_KEYWORDS = {
                            "登录", "注册", "下载app", "app下载", "广告", "隐私政策",
                            "免责声明", "联系我们", "搜索", "行情", "首页", "推荐",
                            "点击下载", "立即下载", "二维码", "扫码",
                        }

                        if extraction_type == "glh_container":
                            # 容器级提取：从 li.article-li 中提取标题链接和时间
                            # 1. 找标题链接
                            link_elem = elem.select_one("a.detail-left[href*='/p/']") or elem.select_one("a[href*='/p/']")
                            if not link_elem:
                                continue
                            href = link_elem.get("href", "")
                            if not href or href.startswith('#') or href.startswith('javascript:'):
                                continue

                            # 2. 提取标题 — 优先从 section.detail-right > a 获取（更完整）
                            detail_right = elem.select_one("section.detail-right")
                            if detail_right:
                                title = detail_right.find("a")
                                if title:
                                    title = title.get_text(strip=True)
                                else:
                                    title = link_elem.get_text(strip=True)
                            else:
                                title = link_elem.get_text(strip=True)

                            if not title or len(title) < 10:
                                continue
                            if title in GELONGHUI_NOISE_TITLE:
                                continue
                            title_lower = title.lower()
                            if any(nk in title_lower for nk in GELONGHUI_NOISE_KEYWORDS):
                                continue

                            full_url = urljoin(base_url, href).split('#')[0]
                            if full_url in source_seen_urls:
                                continue
                            source_seen_urls.add(full_url)
                            if _NOISE_LINK_PATTERNS.search(title):
                                continue

                            # 3. 提取时间 — 从 section.source-time 中提取
                            published_at = ""
                            source_time_elem = elem.select_one("section.source-time")
                            if source_time_elem:
                                time_text = source_time_elem.get_text(strip=True)
                                # 匹配时间模式：36分钟前, 1小时前, 今天 14:30, 昨天 09:15, 07-03 14:30, 2026-07-03
                                import re as _re
                                time_patterns = [
                                    r'(\d+分钟前)',
                                    r'(\d+小时前)',
                                    r'(今天\s*\d{1,2}:\d{2})',
                                    r'(昨天\s*\d{1,2}:\d{2})',
                                    r'(\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})',
                                    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                                    r'(\d{4}年\d{1,2}月\d{1,2}日)',
                                ]
                                for pat in time_patterns:
                                    m = _re.search(pat, time_text)
                                    if m:
                                        published_at = m.group(1)
                                        break
                                # If relative time found, also try to infer date
                                if published_at and not _re.match(r'\d{4}', published_at):
                                    inferred = _infer_published_date(full_url, title + " " + published_at)
                                    if inferred and inferred != published_at:
                                        published_at = f"{published_at} ({inferred})"
                            else:
                                # Fallback: infer from URL + title
                                published_at = _infer_published_date(full_url, title)

                            snippet = title[:200]
                            content_type = "news"
                            relevance = "high"
                            freshness = _classify_freshness(published_at) if published_at else "unknown"
                            source_candidates.append(ContentCandidate(
                                title=title,
                                url=full_url,
                                published_at=published_at,
                                snippet=snippet,
                                content_type=content_type,
                                relevance=relevance,
                                freshness=freshness,
                            ))
                            continue
                        else:
                            # Legacy glh_article (backward compat)
                            title_elem = elem.find(["h2", "h3", "h4", "h1", "span", "div", "p"])
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                            else:
                                title = elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            if title in GELONGHUI_NOISE_TITLE:
                                continue
                            title_lower = title.lower()
                            if any(nk in title_lower for nk in GELONGHUI_NOISE_KEYWORDS):
                                continue
                            content_type = "news"
                            relevance = "high"
                            href = elem.get("href", "")
                            if not href or href.startswith('#') or href.startswith('javascript:'):
                                continue
                            full_url = urljoin(base_url, href).split('#')[0]
                            if full_url in source_seen_urls:
                                continue
                            source_seen_urls.add(full_url)
                            if _NOISE_LINK_PATTERNS.search(title):
                                continue
                            snippet = title[:200]
                            published_at = _infer_published_date(full_url, title + " " + snippet)
                            freshness = _classify_freshness(published_at) if published_at else "unknown"
                            source_candidates.append(ContentCandidate(
                                title=title,
                                url=full_url,
                                published_at=published_at,
                                snippet=snippet,
                                content_type=content_type,
                                relevance=relevance,
                                freshness=freshness,
                            ))
                            continue

                    elif extraction_type in ("ztc_detail", "ztc_item"):
                        # 智通财经文章
                        if extraction_type == "ztc_item":
                            # 从 div.info-list-item 容器中提取
                            title_el = elem.select_one("div.info-item-content-title a")
                            if not title_el:
                                continue
                            title_span = title_el.select_one("span")
                            title = title_span.get_text(strip=True) if title_span else title_el.get_text(strip=True)
                            # 获取摘要
                            desc_el = elem.select_one("div.info-item-content-desc")
                            snippet = desc_el.get_text(strip=True) if desc_el else ""
                            # 获取时间：div.info-item-content-operat > span:first-child
                            operat_el = elem.select_one("div.info-item-content-operat")
                            if operat_el:
                                time_span = operat_el.find("span")
                                published_at = time_span.get_text(strip=True) if time_span else ""
                            else:
                                published_at = ""
                            # 获取 href
                            href = title_el.get("href", "")
                            if not href or href in source_seen_urls:
                                continue
                            source_seen_urls.add(href)
                            # 构建候选（加入 source_candidates）
                            source_candidates.append(ContentCandidate(
                                title=title,
                                url=urljoin(base_url, href),
                                published_at=published_at,
                                snippet=snippet[:200] if snippet else "",
                                content_type="market_update",
                                relevance="high" if len(title) > 20 else "medium",
                                freshness=_classify_freshness(published_at),
                            ))
                            continue
                        # ztc_detail（旧选择器，兼容）
                        title = elem.get_text(strip=True)
                        if len(title) < 10:
                            continue
                        if title.strip() in _ZTC_NAV_TEXTS:
                            continue

                    elif extraction_type in ("benzinga_rating", "benzinga_table"):
                        # Benzinga 评级/表格链接
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    elif extraction_type == "cfn_article":
                        # 中国基金报文章
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    else:
                        # 未知类型，使用默认提取
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                    # 获取链接 href
                    if extraction_type in ("reuters_article", "jp_article"):
                        # 这些是容器元素，需要从中找 <a> 标签
                        a_tag = elem.find("a")
                        href = a_tag.get("href", "") if a_tag else ""
                    else:
                        href = elem.get("href", "")

                    if not href or href in source_seen_urls:
                        continue

                    # 跳过锚点链接和 JavaScript 链接
                    if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                        continue

                    # 补全相对 URL
                    full_url = urljoin(base_url, href)
                    full_url = full_url.split('#')[0]

                    if full_url in source_seen_urls:
                        continue

                    # 排除噪音链接
                    if _NOISE_LINK_PATTERNS.search(title):
                        continue

                    source_seen_urls.add(full_url)

                    # 如果没有提取到 snippet，尝试从周围 <p> 获取
                    if not snippet:
                        parent = elem.parent
                        if parent:
                            for p in parent.find_all('p', recursive=False):
                                p_text = p.get_text(strip=True)
                                if len(p_text) > len(snippet):
                                    snippet = p_text
                            if not snippet and parent.parent:
                                for p in parent.parent.find_all('p', recursive=False):
                                    p_text = p.get_text(strip=True)
                                    if len(p_text) > len(snippet):
                                        snippet = p_text

                    # 截断 snippet
                    if len(snippet) > 200:
                        snippet = snippet[:200] + "..."

                    # 推断 published_at（如果还没有的话）
                    if not published_at:
                        published_at = _infer_published_date(full_url, title + " " + snippet)

                    # 推断 content_type
                    content_type = _classify_content_type_simple(title + " " + full_url)
                    if content_type == "unknown":
                        content_type = default_content_type

                    # 推断 relevance
                    relevance = "high" if content_type != "unknown" else "medium"

                    # 推断 freshness
                    freshness = "unknown"
                    if published_at:
                        freshness = _classify_freshness(published_at)

                    source_candidates.append(ContentCandidate(
                        title=title,
                        url=full_url,
                        published_at=published_at,
                        snippet=snippet,
                        content_type=content_type,
                        relevance=relevance,
                        freshness=freshness,
                    ))

                except Exception:
                    continue

        # 如果源特定选择器找到了足够候选，直接返回
        if len(source_candidates) >= max_candidates:
            return source_candidates[:max_candidates]
        # 如果源特定选择器找到了一些候选（即使不够），也优先返回
        if source_candidates:
            return source_candidates

    # =========================================================================
    # 通用选择器策略（原始逻辑，未修改）
    # =========================================================================

    # CSS 选择器列表：优先级从高到低
    selectors = [
        'article a[href]',
        '.news a[href]',
        '.article a[href]',
        '.research a[href]',
        '.insights a[href]',
        '.podcast a[href]',
        '.episode a[href]',
        '.post a[href]',
        'li a[href]',
        'h2 a[href]',
        'h3 a[href]',
        'h4 a[href]',
        '.entry-title a[href]',
        '.headline a[href]',
        'a[href^="/"]',
        'a[href^="' + base_url.rstrip('/') + '/"]',
    ]

    for selector in selectors:
        if len(candidates) >= max_candidates:
            break
        elements = soup.select(selector)
        for elem in elements:
            if len(candidates) >= max_candidates:
                break
            try:
                href = elem.get('href', '')
                if not href or href in seen_urls:
                    continue

                # 跳过锚点链接和 JavaScript 链接
                if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                    continue

                # 补全相对 URL
                full_url = urljoin(base_url, href)

                # 去除 fragment
                full_url = full_url.split('#')[0]

                if full_url in seen_urls:
                    continue

                # 提取链接文本
                link_text = elem.get_text(strip=True)
                if not link_text or len(link_text) < 5:
                    continue

                # 排除噪音链接
                if _NOISE_LINK_PATTERNS.search(link_text):
                    continue

                seen_urls.add(full_url)

                # 尝试获取周围 <h> 标签作为 title（优先使用 h 标签）
                title = link_text
                parent = elem.parent
                if parent:
                    heading = parent.find_next(['h1', 'h2', 'h3', 'h4', 'h5'])
                    if heading:
                        heading_text = heading.get_text(strip=True)
                        if len(heading_text) > len(title):
                            title = heading_text

                # 提取 snippet：查找链接周围的 <p> 文本
                snippet = ""
                parent = elem.parent
                if parent:
                    # 先尝试当前父元素内的 <p>
                    for p in parent.find_all('p', recursive=False):
                        p_text = p.get_text(strip=True)
                        if len(p_text) > len(snippet):
                            snippet = p_text
                    # 再尝试兄弟 <p>
                    if not snippet:
                        for sibling in parent.find_next_siblings('p'):
                            p_text = sibling.get_text(strip=True)
                            if p_text:
                                snippet = p_text
                                break
                    # 再尝试爷爷元素的 <p>
                    if not snippet and parent.parent:
                        for p in parent.parent.find_all('p', recursive=False):
                            p_text = p.get_text(strip=True)
                            if len(p_text) > len(snippet):
                                snippet = p_text

                # 截断 snippet 到 200 字符
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."

                # 尝试从 URL 路径或周围文本推断 published_at
                published_at = _infer_published_date(full_url, title + " " + snippet)

                # 根据 title + href 推断 content_type
                content_type = _classify_content_type_simple(title + " " + full_url)
                if content_type == "unknown":
                    content_type = default_content_type

                # 推断 relevance
                relevance = "high" if content_type != "unknown" else "medium"

                # 推断 freshness
                freshness = "unknown"
                if published_at:
                    freshness = _classify_freshness(published_at)

                candidates.append(ContentCandidate(
                    title=title,
                    url=full_url,
                    published_at=published_at,
                    snippet=snippet,
                    content_type=content_type,
                    relevance=relevance,
                    freshness=freshness,
                ))

            except Exception:
                continue

    return candidates


def _infer_published_date(url: str, surrounding_text: str) -> str:
    """
    尝试从 URL 路径或周围文本推断发布日期。
    
    Args:
        url: 内容 URL
        surrounding_text: URL 周围的文本
        
    Returns:
        日期字符串（如 "2024-01-15"），推断失败则返回空字符串
    """
    # 从 URL 路径提取日期（常见格式 /2024/01/15, /2024-01-15, /20240115）
    url_date_patterns = [
        r'/(\d{4})/(\d{1,2})/(\d{1,2})',    # /2024/01/15
        r'/(\d{4})-(\d{1,2})-(\d{1,2})',    # /2024-01-15
        r'/(\d{4})(\d{2})(\d{2})(?!\d)',     # /20240115
        r'-(\d{4})-(\d{1,2})-(\d{1,2})',     # -2024-01-15
        r'_(\d{4})-(\d{1,2})-(\d{1,2})',     # _2024-01-15
        r'-(\d{4})-(\d{1,2})(?=[\-/?]|$)',   # -2024-7（BI: /slug-text-2026-7）
        r'/(\d{4})/(\d{1,2})(?=[\-/?]|$)',    # /2024/7（BI: /YYYY/M/）
    ]
    for pattern in url_date_patterns:
        m = re.search(pattern, url)
        if m:
            try:
                year = m.group(1)
                month = m.group(2) if len(m.groups()) >= 2 else "01"
                day = m.group(3) if len(m.groups()) >= 3 else "01"
                # 校验日期合理性
                y, mo, d = int(year), int(month), int(day)
                if 2000 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y}-{mo:02d}-{d:02d}"
            except (ValueError, TypeError, IndexError):
                continue

    # 从周围文本提取日期（如 "Jan 15, 2024", "January 15, 2024"）
    text_date_patterns = [
        (r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})', '%d %b %Y'),
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{1,2}),?\s+(\d{4})', '%b %d %Y'),
        (r'(\d{4})-(\d{2})-(\d{2})', None),  # 已经是标准格式
    ]
    text_lower = surrounding_text.lower()
    for pattern, _ in text_date_patterns:
        m = re.search(pattern, surrounding_text, re.IGNORECASE)
        if m:
            try:
                return f"{m.group(1)}-{m.group(2):0>2}-{m.group(3):0>2}"
            except (ValueError, TypeError, IndexError):
                continue

    return ""


def _classify_content_type_simple(text: str) -> str:
    """
    简单版内容类型分类（用于独立函数中，不依赖 auditor 实例）。
    
    Args:
        text: 标题 + URL 文本
        
    Returns:
        内容类型字符串
    """
    text_lower = text.lower()
    content_patterns = {
        'news': [r'news', r'article', r'story', r'report', r'breaking', r'press'],
        'research': [r'research', r'insights', r'analyst', r'analysis', r'study', r'white.?paper'],
        'ir': [r'investor', r'press.?release', r'earnings', r'10-?[kq]', r'sec.?filing', r'filing'],
        'podcast': [r'podcast', r'episode', r'audio', r'video', r'broadcast'],
        'rating': [r'rating', r'upgrade', r'downgrade', r'target\s*price', r'initiat(e|ion)'],
        'market_update': [r'market', r'update', r'briefing', r'daily', r'recap', r'weekly'],
    }
    for ctype, patterns in content_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return ctype
    return "unknown"


def _classify_freshness(date_str: str) -> str:
    """
    根据日期字符串判断新鲜度。
    
    支持格式：
    - "2024-01-15" / "20240115"
    - "7月1日 22:16" / "7月1日"（中文日期）
    - "07-01" / "1小时前" / "5分钟前" / "昨天"
    - "14:30"（纯时间，视为 unknown）
    
    Args:
        date_str: 日期字符串
        
    Returns:
        fresh / stale / unknown
    """
    if not date_str:
        return "unknown"
    try:
        # 中文日期格式：M月D日 HH:MM 或 M月D日
        cn_date_match = re.search(r'(\d{1,2})月(\d{1,2})日', date_str)
        if cn_date_match:
            month, day = int(cn_date_match.group(1)), int(cn_date_match.group(2))
            year = datetime.now().year
            try:
                dt = datetime(year, month, day)
                delta = (datetime.now() - dt).days
                if 0 <= delta <= 30:
                    return "fresh"
                elif 0 <= delta <= 365:
                    return "stale"
                elif delta < 0:
                    # 可能是去年12月的文章跨年到今年
                    dt = datetime(year - 1, month, day)
                    delta = (datetime.now() - dt).days
                    if 0 <= delta <= 365:
                        return "stale"
                return "unknown"
            except ValueError:
                pass

        # 相对时间
        if re.search(r'\d+\s*(?:小时|分钟)前|昨天', date_str):
            return "fresh"

        # 纯时间 HH:MM（无法判断日期，返回 unknown）
        if re.match(r'^\d{1,2}:\d{2}$', date_str):
            return "unknown"

        # MM-DD 格式（如 "07-01"），推断为当年
        mmdd_match = re.match(r'^(\d{1,2})-(\d{1,2})$', date_str)
        if mmdd_match:
            month, day = int(mmdd_match.group(1)), int(mmdd_match.group(2))
            year = datetime.now().year
            try:
                dt = datetime(year, month, day)
                delta = (datetime.now() - dt).days
                if 0 <= delta <= 30:
                    return "fresh"
                elif delta < 0:
                    dt = datetime(year - 1, month, day)
                    delta = (datetime.now() - dt).days
                    if 0 <= delta <= 365:
                        return "stale"
                return "unknown"
            except ValueError:
                pass

        # ISO 格式
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        else:
            return "unknown"

        # 计算距今天数
        delta = (datetime.now() - dt).days
        if delta < 0:
            return "unknown"  # 未来日期不合理
        if delta <= 30:
            return "fresh"
        if delta <= 365:
            return "stale"
        return "stale"
    except Exception:
        return "unknown"


# =============================================================================
# Content Validity Auditor（增强版）
# =============================================================================

class ContentValidityAuditor:
    """
    内容有效性审计器。
    
    功能：
    1. 加载配置文件和 trial_v2 allowlist
    2. 对每个源进行内容有效性审计
    3. 输出结构化审计结果
    4. 支持 audit_source_matrix() 做矩阵评估
    """
    
    BROWSER_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # 噪音关键词（用于检测噪音页面）
    NOISE_PATTERNS = {
        'login': [
            r'sign\s*in', r'log\s*in', r'login', r'signin',
            r'account', r'password', r'email', r'username'
        ],
        'cookie': [
            r'cookie', r'consent', r'privacy\s*policy',
            r'accept\s*cookies', r'gdpr', r'ccpa'
        ],
        'navigation': [
            r'^home$', r'^about$', r'^contact$', r'^careers$',
            r'^menu$', r'^subscribe$', r'^search$'
        ],
        'empty': [
            r'no\s*content', r'empty', r'404', r'not\s*found'
        ]
    }
    
    # 内容类型关键词
    CONTENT_TYPE_PATTERNS = {
        'news': [r'news', r'article', r'story', r'report', r'breaking'],
        'research': [r'research', r'insights', r'analyst', r'analysis', r'study'],
        'ir': [r'investor', r'press\s*release', r'earnings', r'event', r'reporting'],
        'podcast': [r'podcast', r'episode', r'audio', r'video', r'broadcast'],
        'rating': [r'rating', r'upgrade', r'downgrade', r'target', r'analyst'],
        'market_update': [r'market', r'update', r'briefing', r'daily', r'recap']
    }
    
    def __init__(
        self,
        config_path: str,
        allowlist_path: str,
        inventory_path: str = None,
        max_candidates: int = 5,
        timeout: int = 20
    ):
        """
        初始化内容审计器。
        
        Args:
            config_path: 配置文件路径
            allowlist_path: trial_v2 allowlist 路径
            inventory_path: source inventory 路径（用于获取 URL）
            max_candidates: 每个源最多抽取的候选数量
            timeout: HTTP 请求超时时间（秒）
        """
        self.config_path = Path(config_path)
        self.allowlist_path = Path(allowlist_path)
        self.inventory_path = Path(inventory_path) if inventory_path else None
        self.max_candidates = max_candidates
        self.timeout = timeout
        
        # 加载配置
        self.config = self._load_config()
        self.thresholds = self.config.get('thresholds', {})
        self.noise_keywords = self.config.get('noise_detection', {})
        
        # 加载 allowlist
        self.allowlist = self._load_allowlist()
        
        # 加载 inventory URL 映射
        self.inventory_url_map = {}
        if self.inventory_path and self.inventory_path.exists():
            self._load_inventory_urls()
        
        # HTTP 客户端
        self.client = None
        
    def _load_config(self) -> dict:
        """加载 YAML 配置。"""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}")
            return {}
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_allowlist(self) -> dict:
        """加载 trial_v2 allowlist。"""
        if not self.allowlist_path.exists():
            logger.warning(f"Allowlist not found: {self.allowlist_path}")
            return {}
        
        with open(self.allowlist_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_inventory_urls(self):
        """从 source inventory 加载 source_id -> url 映射。"""
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            inv = yaml.safe_load(f) or {}
        for src in inv.get('sources', []):
            sid = src.get('source_id', '')
            url = src.get('url', '')
            if sid and url:
                self.inventory_url_map[sid] = url
        logger.info(f"从 inventory 加载了 {len(self.inventory_url_map)} 个 URL 映射")
    
    def _get_source_url(self, source: dict) -> str:
        """获取源的 URL，优先从 source dict，其次从 inventory 映射。"""
        url = source.get('url', '')
        if url:
            return url
        sid = source.get('source_id', '')
        return self.inventory_url_map.get(sid, '')
    
    def _init_http_client(self):
        """初始化 HTTP 客户端。"""
        if not HAS_HTTPX:
            logger.warning("httpx not available, using requests fallback")
            import urllib.request
            self.client = None
            return
            
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={'User-Agent': self.BROWSER_UA}
        )
    
    def _fetch_page(self, url: str) -> tuple[int, str, str]:
        """
        获取页面内容。
        
        Returns:
            (status_code, html_content, final_url)
        """
        if HAS_HTTPX and self.client:
            try:
                response = self.client.get(url)
                return response.status_code, response.text, str(response.url)
            except Exception as e:
                logger.error(f"HTTP error for {url}: {e}")
                return 0, "", url
        else:
            # Fallback to urllib
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': self.BROWSER_UA}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    status = response.status
                    html = response.read().decode('utf-8', errors='ignore')
                    return status, html, url
            except Exception as e:
                logger.error(f"urllib error for {url}: {e}")
                return 0, "", url
    
    def _detect_noise(self, title: str, url: str) -> list:
        """
        检测噪音。
        
        Args:
            title: 页面标题
            url: 页面URL
            
        Returns:
            噪音标记列表
        """
        flags = []
        text = f"{title} {url}".lower()
        
        for noise_type, patterns in self.NOISE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    flags.append(noise_type)
                    break
                    
        return list(set(flags))
    
    def _classify_content_type(self, text: str) -> str:
        """
        分类内容类型。
        
        Args:
            text: 文本内容
            
        Returns:
            内容类型
        """
        text_lower = text.lower()
        
        for content_type, patterns in self.CONTENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return content_type
                    
        return "unknown"
    
    def _extract_candidates(self, html: str, base_url: str) -> list:
        """
        从 HTML 中抽取候选内容（实例方法，保持向后兼容）。
        
        Args:
            html: HTML 内容
            base_url: 基础 URL
            
        Returns:
            候选内容列表
        """
        if not HAS_BS4:
            return []
            
        candidates = []
        seen_urls = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找文章/新闻/链接
            # 优先查找 article, a with href in news sections
            selectors = [
                'article a[href]',
                '.news a[href]',
                '.article a[href]',
                '.research a[href]',
                '.insights a[href]',
                '.podcast a[href]',
                '.episode a[href]',
                '.post a[href]',
                'h2 a[href]',
                'h3 a[href]',
                '.entry-title a[href]',
                '.headline a[href]',
                'a[href^="/"]',
                'a[href^="' + base_url + '"]',
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    try:
                        href = elem.get('href', '')
                        if not href or href in seen_urls:
                            continue
                            
                        # 跳过锚点链接
                        if href.startswith('#') or href.startswith('javascript:'):
                            continue
                            
                        # 补全相对 URL
                        if href.startswith('/'):
                            href = urljoin(base_url, href)
                            
                        seen_urls.add(href)
                        
                        title = elem.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue
                            
                        # 检测噪音
                        noise = self._detect_noise(title, href)
                        if 'login' in noise or 'cookie' in noise:
                            continue
                            
                        # 分类内容类型
                        content_type = self._classify_content_type(title + ' ' + href)
                        
                        candidates.append(ContentCandidate(
                            title=title,
                            url=href,
                            content_type=content_type,
                            relevance='high' if content_type != 'unknown' else 'medium'
                        ))
                        
                        if len(candidates) >= self.max_candidates:
                            return candidates
                            
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting candidates: {e}")
            
        return candidates
    
    def _score_content(self, result: ContentAuditResult) -> int:
        """
        计算内容评分。
        
        Args:
            result: 审计结果
            
        Returns:
            评分（0-100）
        """
        score = 0
        
        # 基础分：有技术可访问
        if result.technical_status == 'reachable':
            score += 10
            
        # 有页面标题
        if result.page_title:
            score += 5
            
        # 有有效候选
        score += min(result.valid_candidate_count * 15, 45)
        
        # 有相关候选
        score += min(result.relevant_candidate_count * 10, 30)
        
        # 有近期候选
        score += min(result.fresh_candidate_count * 5, 10)
        
        # 噪音扣分
        score -= len(result.noise_flags) * 5
        
        return max(0, min(100, score))
    
    def _determine_content_status(self, result: ContentAuditResult) -> tuple[str, str]:
        """
        判定内容状态。
        
        Args:
            result: 审计结果
            
        Returns:
            (content_status, reason)
        """
        # 技术失败
        if result.technical_status == 'failed':
            return 'technical_only', 'Technical access failed'
            
        # 技术可访问但无内容
        if result.candidate_count == 0:
            return 'content_reject', 'No candidates found on page'
            
        # 有噪音
        if 'login' in result.noise_flags:
            return 'content_reject', 'Page is a login/consent page'
            
        if 'cookie' in result.noise_flags and len(result.noise_flags) >= 2:
            return 'content_reject', 'Page is primarily cookie/consent'
            
        # 评分低
        score = result.content_score
        if score < 20:
            return 'content_reject', f'Content score too low ({score})'
            
        # 评分中等
        if score < 50:
            return 'content_watch', f'Content score borderline ({score})'
            
        # 评分良好
        min_valid = self.thresholds.get('content_ready_min_valid_candidates', 2)
        min_relevant = self.thresholds.get('content_ready_min_relevant_candidates', 2)
        
        if result.valid_candidate_count >= min_valid and result.relevant_candidate_count >= min_relevant:
            return 'content_ready', f'Content valid and relevant (score: {score})'
            
        # 勉强合格
        return 'content_watch', f'Insufficient valid candidates (score: {score})'
    
    def _determine_recommended_action(self, status: str, score: int) -> str:
        """
        判定推荐动作。
        
        Args:
            status: 内容状态
            score: 内容评分
            
        Returns:
            推荐动作
        """
        if status == 'content_ready' and score >= 50:
            return 'include_in_trial_v2'
        elif status == 'content_watch':
            return 'watch'
        else:
            return 'backlog'
    
    def audit_source(self, source: dict) -> ContentAuditResult:
        """
        审计单个源（增强版）。
        
        支持 consolidated source（如 goldman_sachs_podcasts），记录 member_source_ids，
        使用 classify_noise_flags() 记录详细的 noise_flags，
        使用 extract_candidates_from_html() 的源特定选择器提取候选。
        使用更完善的 candidate 评估逻辑。

        Args:
            source: 源配置字典
            
        Returns:
            审计结果
        """
        # 确保 HTTP 客户端已初始化
        self._init_http_client()
        
        result = ContentAuditResult(
            source_id=source.get('source_id', ''),
            source_name=source.get('source_name', ''),
            source_group=source.get('group_category', ''),
            is_consolidated=source.get('candidate_type') == 'consolidated',
            member_source_ids=source.get('member_source_ids', []),
            expected_content_goal=source.get('notes', ''),
            input_url=self._get_source_url(source)
        )
        
        # 获取 URL
        url = result.input_url
        if not url:
            result.reason = 'No URL configured'
            result.recommended_action = 'backlog'
            return result
            
        # 抓取页面
        status_code, html, final_url = self._fetch_page(url)
        result.http_status = status_code
        result.final_url = final_url
        
        if status_code == 0:
            result.technical_status = 'failed'
            result.reason = 'HTTP request failed'
            result.recommended_action = 'backlog'
            return result
            
        if status_code >= 400:
            result.technical_status = 'failed'
            result.reason = f'HTTP {status_code}'
            result.recommended_action = 'backlog'
            return result
            
        result.technical_status = 'reachable'
        
        # 解析页面
        if HAS_BS4:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                # 获取标题
                title_tag = soup.find('title')
                if title_tag:
                    result.page_title = title_tag.get_text(strip=True)
                    
                # 检测语言（简单判断）
                text_sample = soup.get_text()[:1000]
                if re.search(r'[\u4e00-\u9fff]', text_sample):
                    result.page_language = 'cn'
                elif re.search(r'[a-z]', text_sample):
                    result.page_language = 'en'
                    
                # 使用增强版噪音检测
                full_page_text = soup.get_text(separator=' ', strip=True)
                result.noise_flags = classify_noise_flags(
                    page_text=full_page_text,
                    page_title=result.page_title,
                    http_status=status_code,
                )
                
                # 抽取候选（使用增强版提取方法）
                source_group = source.get('group_category', '')
                candidates = extract_candidates_from_html(
                    html=html,
                    base_url=final_url,
                    max_candidates=self.max_candidates,
                    source_group=source_group,
                    source_id=source.get('source_id', ''),
                )
                result.candidate_count = len(candidates)
                result.sample_candidates = candidates
                
                # 统计
                result.valid_candidate_count = len([c for c in candidates if c.relevance in ('high', 'medium')])
                result.relevant_candidate_count = len([c for c in candidates if c.relevance == 'high'])
                result.fresh_candidate_count = len([c for c in candidates if c.freshness == 'fresh'])
                
                # 重复候选检测（基于 URL 相似度）
                url_domains = set()
                duplicate_count = 0
                for c in candidates:
                    parsed = urlparse(c.url)
                    domain = parsed.netloc + parsed.path.split('/')[0] if parsed.path else parsed.netloc
                    if domain in url_domains:
                        duplicate_count += 1
                    else:
                        url_domains.add(domain)
                result.duplicate_candidate_count = duplicate_count
                
                # consolidated source: 记录 member_source_ids
                if result.is_consolidated and not result.member_source_ids:
                    # 尝试从 candidates 的 URL 反推 member 源
                    member_ids = list(set(
                        c.url.split('/')[-2] if '/' in c.url and c.url.split('/')[-2]
                        else c.source_id
                        for c in candidates[:3]
                    ))
                    result.member_source_ids = member_ids
                    
            except Exception as e:
                logger.error(f"Error parsing page for {url}: {e}")
                result.reason = f'Parse error: {e}'
        else:
            result.reason = 'No HTML parser available'
            
        # 评分和判定
        result.content_score = self._score_content(result)
        result.content_status, result.reason = self._determine_content_status(result)
        result.recommended_action = self._determine_recommended_action(
            result.content_status, 
            result.content_score
        )
        
        return result
    
    def audit_source_matrix(self, source: dict, audit_results: list[ContentAuditResult] = None) -> dict:
        """
        对单个源做矩阵评估（非 deep audit，只做分类）。
        
        这个方法不发送 HTTP 请求，仅根据源属性和已有审计结果做分类判定，
        适用于构建 92 源内容有效性总表。
        
        Args:
            source: 源配置字典（来自 source inventory）
            audit_results: 已有的 deep audit 结果列表（可选）
            
        Returns:
            包含分类信息的字典:
            {
                'source_id': ...,
                'content_validation_scope': 'matrix_only' | 'excluded' | 'on_demand_only' | 'deep_audit',
                'content_validation_status': 'content_ready' | ... | 'not_audited',
                'not_audited_reason': '...' | '',
                'recommended_next_action': '...',
            }
        """
        source_id = source.get('source_id', '')
        
        # 查找已有的 deep audit 结果
        existing_result = None
        if audit_results:
            for ar in audit_results:
                if isinstance(ar, ContentAuditResult) and ar.source_id == source_id:
                    existing_result = ar
                    break
                elif isinstance(ar, dict) and ar.get('source_id') == source_id:
                    existing_result = ar
                    break
        
        result = {
            'source_id': source_id,
            'content_validation_scope': 'matrix_only',
            'content_validation_status': 'not_audited',
            'not_audited_reason': '',
            'recommended_next_action': 'backlog',
        }
        
        # 如果已有 deep audit 结果，直接使用
        if existing_result:
            result['content_validation_scope'] = 'deep_audit'
            if isinstance(existing_result, ContentAuditResult):
                result['content_validation_status'] = existing_result.content_status
                result['recommended_next_action'] = existing_result.recommended_action
            elif isinstance(existing_result, dict):
                result['content_validation_status'] = existing_result.get('content_status', 'not_audited')
                result['recommended_next_action'] = existing_result.get('recommended_action', 'backlog')
            return result
        
        # 无 deep audit 结果，根据源属性分类
        source_group = source.get('group_category', '')
        automation_mode = source.get('automation_mode', '')
        tls_status = source.get('tls_status', '')
        risk_level = source.get('risk_level', '')
        status_flag = source.get('status', '')
        source_type = source.get('candidate_type', '')
        
        # 判断 scope
        scope = self._classify_matrix_scope(
            source_group=source_group,
            automation_mode=automation_mode,
            tls_status=tls_status,
            risk_level=risk_level,
            status_flag=status_flag,
            source_type=source_type,
        )
        result['content_validation_scope'] = scope
        
        # 判断状态和原因
        if scope == 'excluded':
            result['content_validation_status'] = 'not_audited'
            result['not_audited_reason'] = self._get_exclusion_reason(source_group, risk_level, status_flag)
            result['recommended_next_action'] = 'keep_excluded'
        elif scope == 'on_demand_only':
            result['content_validation_status'] = 'not_audited'
            result['not_audited_reason'] = self._get_on_demand_reason(source_group, automation_mode)
            result['recommended_next_action'] = 'keep_on_demand'
        elif scope == 'matrix_only':
            result['content_validation_status'] = 'not_audited'
            result['not_audited_reason'] = self._get_matrix_only_reason(
                source_group, tls_status, automation_mode
            )
            result['recommended_next_action'] = 'watch'
        else:
            result['content_validation_status'] = 'not_audited'
            result['not_audited_reason'] = 'Pending deep audit'
            result['recommended_next_action'] = 'backlog'
        
        return result
    
    def _classify_matrix_scope(
        self,
        source_group: str,
        automation_mode: str,
        tls_status: str,
        risk_level: str,
        status_flag: str,
        source_type: str,
    ) -> str:
        """
        分类矩阵验证范围（用于 audit_source_matrix）。
        
        Args:
            source_group: 源分组
            automation_mode: 自动化模式
            tls_status: TLS 状态
            risk_level: 风险等级
            status_flag: 状态标志
            source_type: 源类型
            
        Returns:
            验证范围: excluded / on_demand_only / matrix_only
        """
        sg = source_group.lower()
        am = automation_mode.lower()
        rl = risk_level.lower()
        sf = status_flag.lower()
        ts = tls_status.lower()
        
        # blocked_high_risk -> excluded
        if rl in ('high', 'blocked', 'blocked_high_risk') or sf in ('blocked', 'excluded'):
            return 'excluded'
        
        # search_providers -> on_demand_only
        if 'search' in sg:
            return 'on_demand_only'
        
        # community_dev_signals -> on_demand_only (dormant)
        if 'community' in sg and am in ('dormant', 'disabled', 'manual'):
            return 'on_demand_only'
        
        # TLS failed -> matrix_only
        if ts in ('failed', 'invalid', 'expired'):
            return 'matrix_only'
        
        # wechat -> matrix_only (wechat_archive_mapping_needed)
        if 'wechat' in sf or 'wechat' in sg or 'weixin' in sg:
            return 'matrix_only'
        
        # 其他非 operational -> matrix_only
        return 'matrix_only'
    
    def _get_exclusion_reason(self, source_group: str, risk_level: str, status_flag: str) -> str:
        """
        获取排除原因。
        
        Args:
            source_group: 源分组
            risk_level: 风险等级
            status_flag: 状态标志
            
        Returns:
            排除原因字符串
        """
        if risk_level.lower() in ('high', 'blocked', 'blocked_high_risk'):
            return f"blocked_high_risk (risk={risk_level})"
        if status_flag.lower() in ('blocked', 'excluded'):
            return f"status={status_flag}"
        return f"excluded: group={source_group}, risk={risk_level}"
    
    def _get_on_demand_reason(self, source_group: str, automation_mode: str) -> str:
        """
        获取 on_demand_only 原因。
        
        Args:
            source_group: 源分组
            automation_mode: 自动化模式
            
        Returns:
            原因字符串
        """
        if 'search' in source_group.lower():
            return "search_provider: 按需查询，非定期抓取"
        if 'community' in source_group.lower():
            return f"community_dev_signals: dormant ({automation_mode})"
        return f"on_demand_only: group={source_group}"
    
    def _get_matrix_only_reason(
        self,
        source_group: str,
        tls_status: str,
        automation_mode: str,
    ) -> str:
        """
        获取 matrix_only 原因。
        
        Args:
            source_group: 源分组
            tls_status: TLS 状态
            automation_mode: 自动化模式
            
        Returns:
            原因字符串
        """
        if tls_status.lower() in ('failed', 'invalid', 'expired'):
            return f"TLS {tls_status}: 需要修复连接后才能 deep audit"
        if 'wechat' in source_group.lower() or 'weixin' in source_group.lower():
            return "wechat_archive_mapping_needed: 需要微信归档映射"
        return f"matrix_only: 尚未分配 deep audit 资源"
    
    def audit_all_sources(self) -> list:
        """
        审计所有源。
        
        Returns:
            审计结果列表
        """
        self._init_http_client()
        
        results = []
        
        # 获取所有源
        trial_v1_sources = self.allowlist.get('trial_v1_base_sources', [])
        trial_v2_additions = self.allowlist.get('trial_v2_additions', [])
        
        all_sources = trial_v1_sources + trial_v2_additions
        
        logger.info(f"Auditing {len(all_sources)} sources")
        
        for source in all_sources:
            try:
                result = self.audit_source(source)
                results.append(result.to_dict())
                logger.info(f"Audited {source.get('source_id')}: {result.content_status}")
            except Exception as e:
                logger.error(f"Error auditing {source.get('source_id')}: {e}")
                results.append({
                    'source_id': source.get('source_id'),
                    'source_name': source.get('source_name'),
                    'content_status': 'technical_only',
                    'reason': f'Audit error: {e}',
                    'recommended_action': 'backlog'
                })
                
        return results

    def audit_sample_sources(self, count: int = 3) -> list:
        """
        抽样审计指定数量的源（用于快速验证）。
        
        Args:
            count: 抽样数量
            
        Returns:
            审计结果列表
        """
        self._init_http_client()
        
        trial_v1_sources = self.allowlist.get('trial_v1_base_sources', [])
        trial_v2_additions = self.allowlist.get('trial_v2_additions', [])
        all_sources = trial_v1_sources + trial_v2_additions
        
        sample = all_sources[:count]
        logger.info(f"抽样审计 {len(sample)} 个源")
        
        results = []
        for source in sample:
            try:
                result = self.audit_source(source)
                results.append(result.to_dict())
                logger.info(f"Sample audited {source.get('source_id')}: {result.content_status}")
            except Exception as e:
                logger.error(f"Error auditing {source.get('source_id')}: {e}")
                results.append({
                    'source_id': source.get('source_id'),
                    'source_name': source.get('source_name'),
                    'content_status': 'technical_only',
                    'reason': f'Audit error: {e}',
                    'recommended_action': 'backlog'
                })
        
        return results


# =============================================================================
# Content Validity Matrix Builder
# =============================================================================

class ContentValidityMatrixBuilder:
    """
    92 源内容有效性矩阵构建器。
    
    功能：
    1. 加载 92 个 source inventory 和 21 个 allowlist
    2. 为每个 source 生成 SourceContentMatrixRow
    3. operational trial_v2 sources: 从 audit_results 获取 content_status
    4. 非 operational: 根据 source_group/automation_mode 等属性分类
    """
    
    def __init__(
        self,
        inventory_path: str,
        allowlist_path: str,
        audit_results: list[ContentAuditResult] = None,
    ):
        """
        初始化矩阵构建器。
        
        Args:
            inventory_path: 92 源 inventory 文件路径（JSONL 格式）
            allowlist_path: trial_v2 allowlist 路径（YAML 格式）
            audit_results: 已有的 deep audit 结果列表（可选）
        """
        self.inventory_path = Path(inventory_path)
        self.allowlist_path = Path(allowlist_path)
        self.audit_results = audit_results or []
        
        # 加载数据
        self.inventory_sources = self._load_inventory()
        self.allowlist_data = self._load_allowlist()
        
        # 构建 operational trial_v2 source_id 集合
        self.operational_trial_v2_ids = self._build_operational_set()
        
        # 构建 audit_results 索引（source_id -> ContentAuditResult）
        self.audit_result_map: dict[str, ContentAuditResult] = {}
        for ar in self.audit_results:
            if isinstance(ar, ContentAuditResult):
                self.audit_result_map[ar.source_id] = ar
            elif isinstance(ar, dict):
                sid = ar.get('source_id', '')
                if sid:
                    self.audit_result_map[sid] = ar
    
    def _load_inventory(self) -> list[dict]:
        """
        加载 92 源 inventory 文件（YAML 或 JSONL 格式）。
        
        Returns:
            源配置字典列表
        """
        if not self.inventory_path.exists():
            logger.warning(f"Inventory not found: {self.inventory_path}")
            return []
        
        sources = []
        suffix = self.inventory_path.suffix.lower()
        
        if suffix in ('.yaml', '.yml'):
            # YAML 格式
            with open(self.inventory_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            sources = data.get('sources', [])
        else:
            # JSONL 格式
            try:
                with open(self.inventory_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        try:
                            source = json.loads(line)
                            sources.append(source)
                        except json.JSONDecodeError as e:
                            logger.warning(f"跳过无效行 {line_num}: {e}")
                            continue
            except Exception as e:
                logger.error(f"加载 JSONL inventory 失败: {e}")
        
        logger.info(f"加载了 {len(sources)} 个 inventory sources")
        return sources
    
    def _load_allowlist(self) -> dict:
        """
        加载 trial_v2 allowlist。
        
        Returns:
            allowlist 字典
        """
        if not self.allowlist_path.exists():
            logger.warning(f"Allowlist not found: {self.allowlist_path}")
            return {}
        
        try:
            with open(self.allowlist_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return data
        except Exception as e:
            logger.error(f"加载 allowlist 失败: {e}")
            return {}
    
    def _build_operational_set(self) -> set[str]:
        """
        从 allowlist 中提取 operational trial_v2 source_id 集合。
        
        Returns:
            source_id 集合
        """
        ids = set()
        
        # trial_v1 基础源
        for s in self.allowlist_data.get('trial_v1_base_sources', []):
            sid = s.get('source_id', '')
            if sid:
                ids.add(sid)
        
        # trial_v2 新增源
        for s in self.allowlist_data.get('trial_v2_additions', []):
            sid = s.get('source_id', '')
            if sid:
                ids.add(sid)
        
        logger.info(f"Operational trial_v2 sources: {len(ids)}")
        return ids
    
    def build_matrix(self) -> list[SourceContentMatrixRow]:
        """
        为每个 source 生成矩阵行。
        
        operational trial_v2 sources: 从 audit_results 获取 content_status
        非 operational: 根据 source_group/automation_mode 等属性分类为 matrix_only/excluded/on_demand_only/not_audited
        
        Returns:
            SourceContentMatrixRow 列表
        """
        rows = []
        total = len(self.inventory_sources)
        
        for source in self.inventory_sources:
            try:
                row = self._build_row(source)
                rows.append(row)
            except Exception as e:
                logger.error(f"构建矩阵行失败 ({source.get('source_id', 'unknown')}): {e}")
                # fail-soft：生成一个默认行
                rows.append(SourceContentMatrixRow(
                    source_id=source.get('source_id', 'unknown'),
                    source_name=source.get('source_name', ''),
                    source_group=source.get('group_category', ''),
                    content_validation_status='not_audited',
                    not_audited_reason=f'矩阵构建错误: {e}',
                    recommended_next_action='backlog',
                ))
        
        logger.info(f"构建矩阵完成: {len(rows)}/{total} 行")
        return rows
    
    def _build_row(self, source: dict) -> SourceContentMatrixRow:
        """
        为单个源构建矩阵行。
        
        Args:
            source: 源配置字典
            
        Returns:
            SourceContentMatrixRow
        """
        source_id = source.get('source_id', '')
        is_operational = source_id in self.operational_trial_v2_ids
        
        row = SourceContentMatrixRow(
            source_id=source_id,
            source_name=source.get('source_name', ''),
            source_group=source.get('group_category', ''),
            source_inventory_count=92,  # 92 源 inventory
            is_operational_trial_v2=is_operational,
        )
        
        # 设置技术分桶
        row.current_technical_bucket = self._get_technical_bucket(source)
        
        # 设置期望内容目标
        row.expected_content_goal = self._set_expected_content_goal(source)
        
        if is_operational:
            # operational trial_v2: 从 audit_results 获取 content_status
            audit_result = self.audit_result_map.get(source_id)
            if audit_result:
                if isinstance(audit_result, ContentAuditResult):
                    row.content_validation_scope = 'deep_audit'
                    row.content_validation_status = audit_result.content_status
                    row.not_audited_reason = ''  # 已审计
                    row.recommended_next_action = self._map_action(audit_result.recommended_action)
                elif isinstance(audit_result, dict):
                    row.content_validation_scope = 'deep_audit'
                    row.content_validation_status = audit_result.get('content_status', 'not_audited')
                    row.not_audited_reason = ''
                    row.recommended_next_action = self._map_action(
                        audit_result.get('recommended_action', 'backlog')
                    )
            else:
                # operational 但无 audit 结果
                row.content_validation_scope = 'deep_audit'
                row.content_validation_status = 'not_audited'
                row.not_audited_reason = 'operational_trial_v2 但尚未完成 deep audit'
                row.recommended_next_action = 'backlog'
        else:
            # 非 operational: 根据属性分类
            row.content_validation_scope = self._classify_validation_scope(source)
            row.content_validation_status = 'not_audited'
            row.not_audited_reason = self._classify_not_audited_reason(source, row.content_validation_scope)
        
        # 根据状态推荐后续动作
        if not row.recommended_next_action or row.recommended_next_action == 'backlog':
            row.recommended_next_action = self._set_recommended_next_action(row)
        
        return row
    
    def _get_technical_bucket(self, source: dict) -> str:
        """
        获取源的技术分桶。
        
        Args:
            source: 源配置字典
            
        Returns:
            技术分桶字符串
        """
        # 优先从 inventory 中读取
        tech_status = source.get('technical_status', '')
        if tech_status:
            return tech_status
        
        # 根据其他属性推断
        tls = source.get('tls_status', '')
        automation = source.get('automation_mode', '')
        
        if tls.lower() in ('failed', 'invalid'):
            return 'tls_failed'
        if automation.lower() in ('active', 'automated'):
            return 'operational'
        return 'unknown'
    
    def _set_expected_content_goal(self, source: dict) -> str:
        """
        根据 source_group 设置目标内容描述。
        
        Args:
            source: 源配置字典
            
        Returns:
            期望内容目标描述
        """
        # 优先使用源配置中的 notes
        notes = source.get('notes', '')
        if notes:
            return notes
        
        source_group = source.get('group_category', '')
        
        goal_map = {
            'news_aggregators': '聚合金融新闻标题和摘要',
            'investment_banks_research': '研究报告和分析师洞察',
            'us_government_economic': '美国经济数据和政府报告',
            'sec_regulatory': 'SEC 监管文件和公开披露',
            'central_banks': '央行政策声明和利率决策',
            'think_tanks': '政策研究和经济分析',
            'industry_associations': '行业报告和市场数据',
            'stock_exchanges': '交易所公告和上市信息',
            'credit_rating_agencies': '信用评级调整和分析',
            'podcasts': '金融播客和访谈内容',
            'search_providers': '搜索查询结果',
            'community_dev_signals': '社区开发信号和讨论',
            'blockchain_explorers': '区块链交易和地址数据',
        }
        
        return goal_map.get(source_group, '待定')
    
    def _classify_validation_scope(self, source: dict) -> str:
        """
        分类非 operational 源的内容验证范围。
        
        Args:
            source: 源配置字典
            
        Returns:
            验证范围: excluded / on_demand_only / matrix_only
        """
        source_group = (source.get('group_category', '') or '').lower()
        automation_mode = (source.get('automation_mode', '') or '').lower()
        tls_status = (source.get('tls_status', '') or '').lower()
        risk_level = (source.get('risk_level', '') or '').lower()
        status_flag = (source.get('status', '') or '').lower()
        
        # blocked_high_risk -> excluded
        if risk_level in ('high', 'blocked', 'blocked_high_risk') or status_flag in ('blocked', 'excluded'):
            return 'excluded'
        
        # search_providers -> on_demand_only
        if 'search' in source_group:
            return 'on_demand_only'
        
        # community_dev_signals -> on_demand_only (dormant)
        if 'community' in source_group and automation_mode in ('dormant', 'disabled', 'manual'):
            return 'on_demand_only'
        
        # TLS failed -> matrix_only
        if tls_status in ('failed', 'invalid', 'expired'):
            return 'matrix_only'
        
        # wechat -> matrix_only (wechat_archive_mapping_needed)
        if 'wechat' in status_flag or 'wechat' in source_group or 'weixin' in source_group:
            return 'matrix_only'
        
        # 其他非 operational -> matrix_only
        return 'matrix_only'
    
    def _classify_not_audited_reason(self, source: dict, scope: str) -> str:
        """
        根据 scope 和源属性返回未审计原因。
        
        Args:
            source: 源配置字典
            scope: 验证范围
            
        Returns:
            未审计原因字符串
        """
        source_group = (source.get('group_category', '') or '').lower()
        automation_mode = (source.get('automation_mode', '') or '').lower()
        tls_status = (source.get('tls_status', '') or '').lower()
        risk_level = (source.get('risk_level', '') or '').lower()
        status_flag = (source.get('status', '') or '').lower()
        
        if scope == 'excluded':
            if risk_level in ('high', 'blocked', 'blocked_high_risk'):
                return f"blocked_high_risk (risk_level={risk_level})"
            if status_flag in ('blocked', 'excluded'):
                return f"status={status_flag}, 非内容审计范围"
            return f"excluded: group={source_group}, risk={risk_level}"
        
        if scope == 'on_demand_only':
            if 'search' in source_group:
                return "search_provider: 按需查询，非定期抓取"
            if 'community' in source_group:
                return f"community_dev_signals: dormant (automation_mode={automation_mode})"
            return f"on_demand_only: group={source_group}"
        
        if scope == 'matrix_only':
            if tls_status in ('failed', 'invalid', 'expired'):
                return f"TLS {tls_status}: 需要修复连接后才能 deep audit"
            if 'wechat' in status_flag or 'wechat' in source_group or 'weixin' in source_group:
                return "wechat_archive_mapping_needed: 需要微信归档映射"
            return f"matrix_only: 尚未分配 deep audit 资源"
        
        return ""
    
    def _set_recommended_next_action(self, row: SourceContentMatrixRow) -> str:
        """
        根据状态推荐后续动作。
        
        Args:
            row: 矩阵行
            
        Returns:
            推荐后续动作
        """
        status = row.content_validation_status
        scope = row.content_validation_scope
        
        # 已完成 deep audit 的
        if status == 'content_ready':
            return 'include_in_trial_v2'
        if status == 'content_watch':
            return 'watch'
        if status == 'content_reject':
            return 'reject'
        if status == 'technical_only':
            return 'needs_connector'
        
        # 未审计的
        if scope == 'excluded':
            return 'keep_excluded'
        if scope == 'on_demand_only':
            return 'keep_on_demand'
        
        # matrix_only 的默认动作
        return 'backlog'
    
    def _map_action(self, action: str) -> str:
        """
        映射 audit 推荐动作到矩阵标准动作。
        
        Args:
            action: 原始推荐动作
            
        Returns:
            标准化动作
        """
        action_map = {
            'include_in_trial_v2': 'include_in_trial_v2',
            'watch': 'watch',
            'backlog': 'backlog',
            'reject': 'reject',
            'keep_excluded': 'keep_excluded',
            'keep_on_demand': 'keep_on_demand',
            'needs_connector': 'needs_connector',
        }
        return action_map.get(action, 'backlog')


# =============================================================================
# 顶层函数
# =============================================================================

def build_content_validity_report(results: list) -> dict:
    """
    构建内容有效性报告摘要。
    
    Args:
        results: 审计结果列表
        
    Returns:
        报告摘要字典
    """
    status_counts = {
        'content_ready': 0,
        'content_watch': 0,
        'content_reject': 0,
        'technical_only': 0
    }
    
    action_counts = {
        'include_in_trial_v2': 0,
        'watch': 0,
        'backlog': 0
    }
    
    for result in results:
        status = result.get('content_status', 'technical_only')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        action = result.get('recommended_action', 'backlog')
        action_counts[action] = action_counts.get(action, 0) + 1
        
    return {
        'total_sources': len(results),
        'status_counts': status_counts,
        'action_counts': action_counts,
        'timestamp': datetime.now().isoformat()
    }


def build_source_content_validity_matrix(
    inventory_path: str,
    allowlist_path: str,
    audit_results: list[ContentAuditResult] = None,
) -> list[SourceContentMatrixRow]:
    """
    构建 92 源内容有效性总表。
    
    Args:
        inventory_path: 92 源 inventory 文件路径（JSONL 格式）
        allowlist_path: trial_v2 allowlist 路径（YAML 格式）
        audit_results: 已有的 deep audit 结果列表（可选）
            
    Returns:
        SourceContentMatrixRow 列表
    """
    builder = ContentValidityMatrixBuilder(inventory_path, allowlist_path, audit_results)
    return builder.build_matrix()


def build_matrix_summary(rows: list[SourceContentMatrixRow]) -> dict:
    """
    构建矩阵摘要统计。
    
    Args:
        rows: SourceContentMatrixRow 列表
        
    Returns:
        摘要统计字典
    """
    scope_counts = {}
    status_counts = {}
    action_counts = {}
    operational_count = 0
    non_operational_count = 0
    
    for row in rows:
        # scope 统计
        scope = row.content_validation_scope
        scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        # status 统计
        status = row.content_validation_status
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # action 统计
        action = row.recommended_next_action
        action_counts[action] = action_counts.get(action, 0) + 1
        
        # operational 统计
        if row.is_operational_trial_v2:
            operational_count += 1
        else:
            non_operational_count += 1
    
    return {
        'total_sources': len(rows),
        'operational_trial_v2': operational_count,
        'non_operational': non_operational_count,
        'scope_distribution': scope_counts,
        'status_distribution': status_counts,
        'action_distribution': action_counts,
        'timestamp': datetime.now().isoformat(),
    }


# =============================================================================
# CLI 入口
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    # 使用子命令解析器
    parser = argparse.ArgumentParser(
        description='Content Validity Audit & Matrix Builder (M3C-5A5)'
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # --- validate-config 子命令 ---
    vc_parser = subparsers.add_parser('validate-config', help='验证配置文件完整性')
    vc_parser.add_argument('--config', default='configs/foundation_content_validity_audit.example.yaml')
    vc_parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml')
    vc_parser.add_argument('--inventory', default='configs/foundation_source_inventory.example.yaml')

    # --- sample 子命令 ---
    sample_parser = subparsers.add_parser('sample', help='快速抽样 3 个源验证')
    sample_parser.add_argument('--config', default='configs/foundation_content_validity_audit.example.yaml')
    sample_parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml')
    sample_parser.add_argument('--inventory', default='configs/foundation_source_inventory.example.yaml')
    sample_parser.add_argument('--output', default='data/foundation_content_validity/index/sample_audit.jsonl')
    sample_parser.add_argument('--max-candidates', type=int, default=5)
    sample_parser.add_argument('--timeout', type=int, default=20)

    # --- audit 子命令（原有功能） ---
    audit_parser = subparsers.add_parser('audit', help='对 trial_v2 源进行内容有效性审计')
    audit_parser.add_argument('--config', default='configs/foundation_content_validity_audit.example.yaml')
    audit_parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml')
    audit_parser.add_argument('--inventory', default='configs/foundation_source_inventory.example.yaml')
    audit_parser.add_argument('--output', default='data/foundation_content_validity/index/source_content_audit.jsonl')
    audit_parser.add_argument('--max-candidates', type=int, default=5)
    audit_parser.add_argument('--timeout', type=int, default=20)
    
    # --- matrix 子命令 ---
    matrix_parser = subparsers.add_parser('matrix', help='构建 92 源内容有效性总表')
    matrix_parser.add_argument('--inventory', default='configs/foundation_source_inventory.example.yaml', help='92 源 inventory 文件路径 (YAML)')
    matrix_parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml', help='trial_v2 allowlist 文件路径 (YAML)')
    matrix_parser.add_argument('--audit-results', default=None, help='已有的 deep audit 结果文件 (JSONL)')
    matrix_parser.add_argument('--output', default='data/foundation_content_validity/index/source_content_validity_matrix.jsonl')
    matrix_parser.add_argument('--summary', action='store_true', help='同时输出摘要统计')
    
    # 保持向后兼容：无子命令时使用原有 audit 行为
    parser.add_argument('--config', default='configs/foundation_content_validity_audit.example.yaml')
    parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml')
    parser.add_argument('--output', default='data/foundation_content_validity/index/source_content_audit.jsonl')
    parser.add_argument('--max-candidates', type=int, default=5)
    parser.add_argument('--timeout', type=int, default=20)
    
    args = parser.parse_args()
    
    if args.command == 'validate-config':
        # === validate-config 子命令 ===
        config_path = Path(args.config)
        allowlist_path = Path(args.allowlist)
        inventory_path = Path(args.inventory)
        errors = []
        
        if not config_path.exists():
            errors.append(f"配置文件不存在: {config_path}")
        else:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            scope = cfg.get('scope', {})
            if scope.get('operational_source_count') != 21:
                errors.append(f"operational_source_count 应为 21，实际为 {scope.get('operational_source_count')}")
            if scope.get('source_inventory_count', scope.get('operational_source_count')) and scope.get('source_inventory_count') != 92:
                errors.append(f"source_inventory_count 应为 92，实际为 {scope.get('source_inventory_count')}")
        
        if not allowlist_path.exists():
            errors.append(f"Allowlist 文件不存在: {allowlist_path}")
        
        if not inventory_path.exists():
            errors.append(f"Inventory 文件不存在: {inventory_path}")
        else:
            import yaml
            with open(inventory_path, 'r', encoding='utf-8') as f:
                inv = yaml.safe_load(f)
            sources = inv.get('sources', [])
            if len(sources) != 92:
                errors.append(f"Source inventory 应有 92 个源，实际有 {len(sources)}")
        
        if errors:
            for e in errors:
                print(f"  FAIL: {e}")
            print(f"\nvalidate-config: {len(errors)} 个错误")
            sys.exit(1)
        else:
            print("validate-config: PASS — 配置文件完整，source count 正确")
    
    elif args.command == 'sample':
        # === sample 子命令 ===
        auditor = ContentValidityAuditor(
            config_path=args.config,
            allowlist_path=args.allowlist,
            inventory_path=args.inventory,
            max_candidates=args.max_candidates,
            timeout=args.timeout
        )
        results = auditor.audit_sample_sources(count=3)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        summary = build_content_validity_report(results)
        print(f"sample: 完成 {len(results)} 个源抽样审计")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    elif args.command == 'matrix':
        # === matrix 子命令 ===
        # 加载已有的 audit results（如果提供）
        audit_results = []
        if args.audit_results:
            audit_path = Path(args.audit_results)
            if audit_path.exists():
                with open(audit_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            audit_results.append(json.loads(line))
                logger.info(f"加载了 {len(audit_results)} 个已有 audit 结果")
            else:
                logger.warning(f"Audit results 文件不存在: {audit_path}")
        
        # 构建矩阵
        rows = build_source_content_validity_matrix(
            inventory_path=args.inventory,
            allowlist_path=args.allowlist,
            audit_results=audit_results,
        )
        
        # 输出 JSONL
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for row in rows:
                f.write(json.dumps(row.to_dict(), ensure_ascii=False) + '\n')
        
        logger.info(f"矩阵输出到: {output_path}")
        
        # 摘要
        summary = build_matrix_summary(rows)
        
        # 同时输出 scope/status/action 交叉统计
        print(f"=== 92 源内容有效性矩阵摘要 ===")
        print(f"总源数: {summary['total_sources']}")
        print(f"  operational trial_v2: {summary['operational_trial_v2']}")
        print(f"  non-operational: {summary['non_operational']}")
        print(f"\n验证范围分布:")
        for scope, count in sorted(summary['scope_distribution'].items()):
            print(f"  {scope}: {count}")
        print(f"\n验证状态分布:")
        for status, count in sorted(summary['status_distribution'].items()):
            print(f"  {status}: {count}")
        print(f"\n推荐动作分布:")
        for action, count in sorted(summary['action_distribution'].items()):
            print(f"  {action}: {count}")
        print(f"\n时间: {summary['timestamp']}")
        
        if args.summary:
            print(f"\n详细摘要 JSON:")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    else:
        # === audit 子命令 / 向后兼容 ===
        auditor = ContentValidityAuditor(
            config_path=args.config,
            allowlist_path=args.allowlist,
            inventory_path=getattr(args, 'inventory', 'configs/foundation_source_inventory.example.yaml'),
            max_candidates=args.max_candidates,
            timeout=args.timeout
        )
        
        results = auditor.audit_all_sources()
        
        # 输出 JSONL
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        # 输出摘要
        summary = build_content_validity_report(results)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
