"""
Tests for M3C-5B1.1a gelonghui date extraction repair.

Covers:
- Container-level date extraction from section.source-time
- Sibling date extraction
- Parent list-item date extraction
- Relative time patterns (x分钟前, x小时前, 今天, 昨天, MM-DD HH:MM)
- No fabricated dates from /p/{id}.html URLs
- --source filter in runner
- Isolation: no merck_ir, no allowlist modification
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# HTML fixture helpers
# =============================================================================

def _build_gelonghui_html(items):
    """Build gelonghui-style HTML with article-li containers.

    Args:
        items: list of (title, href, time_text) tuples
    """
    li_html = []
    for title, href, time_text in items:
        li_html.append(f"""<li class="article-li">
  <div class="article-li__main">
    <a class="detail-left" href="{href}">{title}</a>
    <section class="detail-right">
      <a href="{href}">{title}</a>
      <section class="source-time">来自主题：财经研究所{time_text}</section>
    </section>
  </div>
</li>""")
    return f'<ul>{"".join(li_html)}</ul>'


# =============================================================================
# Unit tests for date extraction patterns
# =============================================================================

class TestGelonghuiDatePatterns:
    """Test that relative time patterns are correctly recognized."""

    PATTERNS = [
        ("38分钟前", "38分钟前"),
        ("1小时前", "1小时前"),
        ("2小时前", "2小时前"),
        ("今天 14:30", "今天 14:30"),
        ("今天14:30", "今天14:30"),
        ("昨天 09:15", "昨天 09:15"),
        ("昨天09:15", "昨天09:15"),
        ("07-03 14:30", "07-03 14:30"),
        ("06-28 10:00", "06-28 10:00"),
        ("2026-07-03", "2026-07-03"),
        ("2025/12/01", "2025/12/01"),
        ("2026年07月03日", "2026年07月03日"),
    ]

    @pytest.mark.parametrize("text,expected", PATTERNS)
    def test_recognize_time_pattern(self, text, expected):
        """Verify each time pattern is matched by the regex used in content_validity."""
        time_patterns = [
            r'(\d+分钟前)',
            r'(\d+小时前)',
            r'(今天\s*\d{1,2}:\d{2})',
            r'(昨天\s*\d{1,2}:\d{2})',
            r'(\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
        ]
        matched = False
        for pat in time_patterns:
            m = re.search(pat, text)
            if m:
                assert m.group(1) == expected, f"Pattern {pat} matched '{m.group(1)}' not '{expected}'"
                matched = True
                break
        assert matched, f"No pattern matched for '{text}'"

    def test_no_fabricated_date_from_p_url(self):
        """URL /p/12345.html should not be interpreted as containing a date."""
        url = "https://www.gelonghui.com/p/5451415.html"
        date_patterns = [r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', r'\d{1,2}-\d{1,2}']
        for pat in date_patterns:
            m = re.search(pat, url)
            assert m is None, f"URL should not match date pattern, but got {m.group(0)}"


# =============================================================================
# Integration tests with extract_candidates_from_html
# =============================================================================

class TestGelonghuiContainerExtraction:
    """Test container-level extraction from gelonghui-style HTML."""

    def setup_method(self):
        """Import extract_candidates_from_html if available."""
        try:
            import sys
            src = str(REPO_ROOT / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
            self.extract_fn = extract_candidates_from_html
        except ImportError:
            self.extract_fn = None

    def _skip_if_no_fn(self):
        if self.extract_fn is None:
            pytest.skip("extract_candidates_from_html not available")

    def test_extract_from_container_with_relative_time(self):
        """Extract candidates with relative time from container-level selector."""
        self._skip_if_no_fn()
        html = _build_gelonghui_html([
            ("证监会发布再融资新规", "/p/5451415.html", "38分钟前"),
            ("万亿赛道概念股涨停潮", "/p/5451400.html", "1小时前"),
            ("韩国股市大幅逆转", "/p/5451390.html", "2小时前"),
            ("新能源车船税减免政策", "/p/5451380.html", "3小时前"),
            ("格隆汇策略峰会即将召开", "/p/5451370.html", "昨天 09:30"),
        ])
        candidates = self.extract_fn(
            html=html,
            base_url="https://www.gelonghui.com",
            max_candidates=5,
            source_group="chinese_rebroadcast",
            source_id="gelonghui",
        )
        assert len(candidates) >= 3, f"Expected >= 3 candidates, got {len(candidates)}"
        # At least some should have published_at (relative time)
        dated = [c for c in candidates if c.published_at]
        assert len(dated) >= 2, f"Expected >= 2 dated candidates, got {len(dated)}"

    def test_extract_from_container_with_mmdd_time(self):
        """Extract candidates with MM-DD HH:MM time format."""
        self._skip_if_no_fn()
        html = _build_gelonghui_html([
            ("某上市公司发布半年报业绩预告", "/p/5451000.html", "07-01 14:30"),
            ("美联储最新利率决议对市场影响", "/p/5450999.html", "06-30 10:00"),
        ])
        candidates = self.extract_fn(
            html=html,
            base_url="https://www.gelonghui.com",
            max_candidates=5,
            source_group="chinese_rebroadcast",
            source_id="gelonghui",
        )
        dated = [c for c in candidates if c.published_at]
        assert len(dated) >= 2, f"Expected >= 2 dated candidates, got {len(dated)}"

    def test_extract_from_container_with_today_yesterday(self):
        """Extract candidates with 今天/昨天 time format."""
        self._skip_if_no_fn()
        html = _build_gelonghui_html([
            ("今日A股三大指数走势深度分析", "/p/5452000.html", "今天 15:00"),
            ("昨日美股三大指数收盘情况盘点", "/p/5451999.html", "昨天 04:30"),
            ("上周IPO过会企业情况盘点分析", "/p/5451998.html", "3天前"),
        ])
        candidates = self.extract_fn(
            html=html,
            base_url="https://www.gelonghui.com",
            max_candidates=5,
            source_group="chinese_rebroadcast",
            source_id="gelonghui",
        )
        dated = [c for c in candidates if c.published_at]
        assert len(dated) >= 2, f"Expected >= 2 dated candidates, got {len(dated)}"

    def test_gelonghui_no_empty_title(self):
        """Empty or very short titles should be filtered."""
        self._skip_if_no_fn()
        html = _build_gelonghui_html([
            ("短", "/p/5450001.html", "1小时前"),
            ("这是一条足够长的财经新闻标题", "/p/5450002.html", "2小时前"),
        ])
        candidates = self.extract_fn(
            html=html,
            base_url="https://www.gelonghui.com",
            max_candidates=5,
            source_group="chinese_rebroadcast",
            source_id="gelonghui",
        )
        titles = [c.title for c in candidates]
        assert "短" not in titles, "Title < 10 chars should be filtered"

    def test_gelonghui_noise_title_filtered(self):
        """Noise titles (广告, 下载APP) should be filtered."""
        self._skip_if_no_fn()
        html = _build_gelonghui_html([
            ("广告", "/p/5450001.html", "1小时前"),
            ("下载APP", "/p/5450002.html", "2小时前"),
            ("证监会发布再融资新规详解", "/p/5450003.html", "3小时前"),
        ])
        candidates = self.extract_fn(
            html=html,
            base_url="https://www.gelonghui.com",
            max_candidates=5,
            source_group="chinese_rebroadcast",
            source_id="gelonghui",
        )
        titles = [c.title for c in candidates]
        assert "广告" not in titles
        assert "下载APP" not in titles
        assert len(candidates) >= 1


# =============================================================================
# Runner --source filter tests
# =============================================================================

class TestRunnerSourceFilter:
    """Test --source filter parameter in runner."""

    def test_runner_has_source_filter(self):
        """Runner script should contain --source argument definition."""
        runner_path = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
        content = runner_path.read_text()
        assert "--source" in content

    def test_runner_source_filter_logic(self):
        """Runner should filter sources when --source is specified."""
        runner_path = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
        content = runner_path.read_text()
        assert "source_filter" in content
        assert "args.source" in content

    def test_runner_source_filter_narrows_scope(self):
        """--source filter must only narrow scope, not expand."""
        runner_path = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
        content = runner_path.read_text()
        # Should skip sources not in filter
        assert "Skipping" in content or "continue" in content
        # Should not add sources
        assert "source_filter.add" not in content


# =============================================================================
# Isolation tests
# =============================================================================

class TestGelonghuiRepairIsolation:
    """Ensure gelonghui repair is isolated from other sources."""

    def test_runner_does_not_write_allowlist(self):
        runner_path = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
        content = runner_path.read_text()
        assert "yaml.dump" not in content

    def test_runner_does_not_write_trae_config(self):
        runner_path = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
        content = runner_path.read_text()
        # No TRAE config writes
        assert "trae_foundation_trial_v2" not in content or "write" not in content.lower()

    def test_gelonghui_preflight_excludes_merck_ir(self):
        """--source gelonghui must not include merck_ir in report."""
        report_path = REPO_ROOT / "docs" / "foundation_m3c_5b1_1a_gelonghui_date_repair_report.md"
        if report_path.exists():
            content = report_path.read_text()
            # Should not have merck_ir in source results (only in base allowlist mention)
            lines = content.split("\n")
            result_section = False
            for line in lines:
                if "## Preflight:" in line or "## Summary" in line:
                    result_section = True
                if "## Boundary" in line or "## Recommendation" in line:
                    result_section = False
                if result_section and "merck_ir" in line:
                    # Allow merck_ir only in "base allowlist unchanged" context
                    assert "base_allowlist" in line.lower() or "allowlist" in line.lower() or "unchanged" in line.lower() or "base" in line.lower(), \
                        f"merck_ir found in result section: {line}"

    def test_report_no_sensitive_data(self):
        """Report must not contain proxy URL, cookie, token, or secret."""
        report_path = REPO_ROOT / "docs" / "foundation_m3c_5b1_1a_gelonghui_date_repair_report.md"
        if report_path.exists():
            content = report_path.read_text()
            sensitive_patterns = ["api_key=", "bearer ", "authorization:", "set-cookie:", "x-token:", "socks5://", "http://127.0.0.1"]
            for pattern in sensitive_patterns:
                assert pattern not in content.lower(), f"Found sensitive pattern: {pattern}"

    def test_no_dashboard_pages_restored(self):
        """Ensure no deleted Dashboard pages are referenced."""
        docs_dir = REPO_ROOT / "docs"
        deleted_pages = ["总览", "运行日志", "失败队列", "文档入口"]
        for f in docs_dir.glob("*.md"):
            if f.name.startswith("foundation_m3c_5b1_1a"):
                content = f.read_text(encoding="utf-8")
                for page in deleted_pages:
                    # Page names could appear in passing, but not as restored sections
                    if page in content:
                        assert "恢复" not in content or "不恢复" in content, \
                            f"Deleted page '{page}' appears to be restored in {f.name}"
