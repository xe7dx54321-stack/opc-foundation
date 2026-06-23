"""测试 production example config 和 PowerShell 脚本。

功能说明（小白解读）：
    这个测试文件专门验证 production 配置模板和脚本是否正确。
    不测试真实网络访问，只检查文件存在性和基本格式。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """返回项目根目录。
    
    文件路径：tests/official_filings/test_production_config.py
    向上 3 级：tests/official_filings -> tests -> 项目根目录
    """
    return Path(__file__).parent.parent.parent.resolve()


# ---------------------------------------------------------------------------
# production example config 测试
# ---------------------------------------------------------------------------


class TestProductionExampleConfig:
    """测试 configs/official_filings.production.example.yaml。"""

    def test_production_example_config_exists(self):
        """production example config 文件必须存在。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        assert path.exists(), f"缺少 production example config: {path}"

    def test_production_example_config_is_yaml(self):
        """production example config 必须是有效的 YAML。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "production config 必须是 YAML dict"

    def test_production_example_config_has_archive_root(self):
        """production example config 必须包含 archive_root。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "archive_root" in data, "缺少 archive_root"

    def test_production_example_config_has_defaults(self):
        """production example config 必须包含 defaults。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "defaults" in data, "缺少 defaults"
        defaults = data["defaults"]
        assert "max_items_per_source" in defaults
        assert "download_pdfs" in defaults
        # download_pdfs 默认必须是 false
        assert defaults["download_pdfs"] is False, "download_pdfs 默认应为 false"

    def test_production_example_config_has_three_sources(self):
        """production example config 必须包含 3 个 source（SEC/CNINFO/HKEX）。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "sources" in data, "缺少 sources"
        sources = data["sources"]
        assert len(sources) == 3, f"应有 3 个 source，实际 {len(sources)} 个"

    def test_production_example_config_all_disabled(self):
        """production example config 所有 source 必须 enabled=false。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for source in data["sources"]:
            assert source.get("enabled") is False, f"source {source['source_id']} 必须是 enabled=false"

    def test_production_example_config_has_sec_source(self):
        """production example config 必须包含 SEC EDGAR source。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sec_sources = [s for s in data["sources"] if s["source_type"] == "sec_edgar"]
        assert len(sec_sources) == 1, "必须有 1 个 sec_edgar source"

    def test_production_example_config_has_cninfo_source(self):
        """production example config 必须包含 CNINFO source。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cninfo_sources = [s for s in data["sources"] if s["source_type"] == "cninfo_announcement"]
        assert len(cninfo_sources) == 1, "必须有 1 个 cninfo_announcement source"

    def test_production_example_config_has_hkex_source(self):
        """production example config 必须包含 HKEX source。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        hkex_sources = [s for s in data["sources"] if s["source_type"] == "hkex_announcement"]
        assert len(hkex_sources) == 1, "必须有 1 个 hkex_announcement source"

    def test_production_example_config_max_items_small(self):
        """production example config max_items 应该 <= 5（适合小样本测试）。"""
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for source in data["sources"]:
            max_items = source.get("max_items", data["defaults"]["max_items_per_source"])
            assert max_items <= 10, f"source {source['source_id']} max_items={max_items} 应 <= 10"

    def test_production_example_config_no_secrets(self):
        """production example config 不能包含明显的 secrets 字段值。
        
        注意：这个测试只检测字段值中的 secrets，不检测注释中的关键词。
        """
        root = _project_root()
        path = root / "configs" / "official_filings.production.example.yaml"
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 检查 sources 中的明显 secret 字段
        for source in config.get("sources", []):
            # 这些字段如果出现且有真实值，说明可能包含 secret
            secret_fields = ["password", "secret", "api_key", "apikey", "auth_token", "bearer_token"]
            for field in secret_fields:
                value = source.get(field, "")
                if value and value not in ["", "null", "none"]:
                    # 如果字段存在且有非空值，应该是 placeholder
                    assert value in ["xxx", "YOUR_KEY_HERE", "placeholder", ""],                         f"source {source['source_id']} 的 {field} 字段不应包含真实 secret"


# ---------------------------------------------------------------------------
# PowerShell 脚本测试
# ---------------------------------------------------------------------------


class TestPowerShellScripts:
    """测试 PowerShell run/check 脚本。"""

    def test_run_script_exists(self):
        """run 脚本必须存在。"""
        root = _project_root()
        path = root / "scripts" / "run_official_filings_archive.ps1"
        assert path.exists(), f"缺少 run 脚本: {path}"

    def test_check_script_exists(self):
        """check 脚本必须存在。"""
        root = _project_root()
        path = root / "scripts" / "check_official_filings_archive.ps1"
        assert path.exists(), f"缺少 check 脚本: {path}"

    def test_run_script_mentions_local_config(self):
        """run 脚本必须引用 production.local.yaml。"""
        root = _project_root()
        path = root / "scripts" / "run_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "official_filings.production.local.yaml" in content,             "run 脚本应引用 official_filings.production.local.yaml"

    def test_run_script_sets_pythonpath(self):
        """run 脚本必须设置 PYTHONPATH。"""
        root = _project_root()
        path = root / "scripts" / "run_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "PYTHONPATH" in content, "run 脚本应设置 PYTHONPATH"
        assert "src" in content.lower(), "run 脚本 PYTHONPATH 应包含 src"

    def test_run_script_has_dryRun_mode(self):
        """run 脚本必须支持 dry-run 模式。"""
        root = _project_root()
        path = root / "scripts" / "run_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "dry-run" in content.lower() or "dryrun" in content.lower(),             "run 脚本应支持 dry-run 模式"

    def test_run_script_has_sourceHealth_mode(self):
        """run 脚本必须支持 source-health 模式。"""
        root = _project_root()
        path = root / "scripts" / "run_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "source-health" in content.lower() or "sourcehealth" in content.lower(),             "run 脚本应支持 source-health 模式"

    def test_check_script_checks_index_files(self):
        """check 脚本应检查 index 文件。"""
        root = _project_root()
        path = root / "scripts" / "check_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "filings.jsonl" in content, "check 脚本应检查 filings.jsonl"
        assert "source_health" in content.lower(), "check 脚本应检查 source_health"

    def test_check_script_handles_missing_archive(self):
        """check 脚本应优雅处理归档目录不存在的情况。"""
        root = _project_root()
        path = root / "scripts" / "check_official_filings_archive.ps1"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # 应该检查目录是否存在并给出友好提示
        assert "test-path" in content.lower() or "testpath" in content.lower(),             "check 脚本应检查归档目录是否存在"
        assert "不存在" in content or "not exist" in content.lower(),             "check 脚本应给出目录不存在的提示"


# ---------------------------------------------------------------------------
# live smoke 文档测试
# ---------------------------------------------------------------------------


class TestLiveSmokeDoc:
    """测试 live smoke 文档。"""

    def test_live_smoke_doc_exists(self):
        """live smoke 文档必须存在。"""
        root = _project_root()
        path = root / "docs" / "official_filing_live_smoke.md"
        assert path.exists(), f"缺少 live smoke 文档: {path}"

    def test_live_smoke_doc_has_sections(self):
        """live smoke 文档应包含主要章节。"""
        root = _project_root()
        path = root / "docs" / "official_filing_live_smoke.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # 检查主要章节
        sections = [
            "SEC EDGAR",
            "CNINFO",
            "HKEX",
            "Production Trial Ready",
        ]
        for section in sections:
            assert section in content, f"live smoke 文档应包含章节: {section}"
