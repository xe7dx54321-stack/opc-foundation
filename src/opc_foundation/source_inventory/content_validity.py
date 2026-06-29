"""
Content Validity Auditor Module (M3C-5A4)
==========================================

功能说明（小白解读）：
    这个模块用于审计 21 个 trial_v2 源的内容有效性。
    它会：
    1. 读取配置文件和 trial_v2 allowlist
    2. 对每个源发送 HTTP 请求
    3. 解析 HTML 页面
    4. 抽取候选内容（如文章链接、新闻标题等）
    5. 判断内容是否有效、相关、近期
    6. 识别噪音页面（登录页、Cookie页、空页面等）
    7. 输出结构化的审计结果

使用方法：
    from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
    
    auditor = ContentValidityAuditor(
        config_path='configs/foundation_content_validity_audit.example.yaml',
        allowlist_path='configs/foundation_trial_v2_allowlist.example.yaml'
    )
    results = auditor.audit_all_sources()

Author: OPC Foundation
Version: 1.0
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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


# =============================================================================
# Content Validity Auditor
# =============================================================================

class ContentValidityAuditor:
    """
    内容有效性审计器。
    
    功能：
    1. 加载配置文件和 trial_v2 allowlist
    2. 对每个源进行内容有效性审计
    3. 输出结构化审计结果
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
        max_candidates: int = 5,
        timeout: int = 20
    ):
        """
        初始化内容审计器。
        
        Args:
            config_path: 配置文件路径
            allowlist_path: trial_v2 allowlist 路径
            max_candidates: 每个源最多抽取的候选数量
            timeout: HTTP 请求超时时间（秒）
        """
        self.config_path = Path(config_path)
        self.allowlist_path = Path(allowlist_path)
        self.max_candidates = max_candidates
        self.timeout = timeout
        
        # 加载配置
        self.config = self._load_config()
        self.thresholds = self.config.get('thresholds', {})
        self.noise_keywords = self.config.get('noise_detection', {})
        
        # 加载 allowlist
        self.allowlist = self._load_allowlist()
        
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
        从 HTML 中抽取候选内容。
        
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
                            from urllib.parse import urljoin
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
        审计单个源。
        
        Args:
            source: 源配置字典
            
        Returns:
            审计结果
        """
        result = ContentAuditResult(
            source_id=source.get('source_id', ''),
            source_name=source.get('source_name', ''),
            source_group=source.get('group_category', ''),
            is_consolidated=source.get('candidate_type') == 'consolidated',
            member_source_ids=source.get('member_source_ids', []),
            expected_content_goal=source.get('notes', ''),
            input_url=source.get('url', '')
        )
        
        # 获取 URL
        url = source.get('url', '')
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
                    
                # 检测噪音
                result.noise_flags = self._detect_noise(result.page_title, final_url)
                
                # 抽取候选
                candidates = self._extract_candidates(html, final_url)
                result.candidate_count = len(candidates)
                result.sample_candidates = candidates
                
                # 统计
                result.valid_candidate_count = len([c for c in candidates if c.relevance in ('high', 'medium')])
                result.relevant_candidate_count = len([c for c in candidates if c.relevance == 'high'])
                
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


if __name__ == '__main__':
    # 测试用
    import argparse
    
    parser = argparse.ArgumentParser(description='Content Validity Audit')
    parser.add_argument('--config', default='configs/foundation_content_validity_audit.example.yaml')
    parser.add_argument('--allowlist', default='configs/foundation_trial_v2_allowlist.example.yaml')
    parser.add_argument('--output', default='data/foundation_content_validity/index/source_content_audit.jsonl')
    parser.add_argument('--max-candidates', type=int, default=5)
    parser.add_argument('--timeout', type=int, default=20)
    
    args = parser.parse_args()
    
    auditor = ContentValidityAuditor(
        config_path=args.config,
        allowlist_path=args.allowlist,
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
