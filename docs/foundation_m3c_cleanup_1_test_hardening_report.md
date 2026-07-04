# OPC Foundation M3C-Cleanup.1 — URL Text Extractor 测试网络依赖消除报告

**执行时间**: 2026-07-04
**base commit**: `5b7cbe2`
**branch**: `fix/cleanup1-url-text-extractor-tests`
**merge commit**: `6dc5a1f`

---

## 1. 执行前状态

- **master path**: `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **base commit**: `5b7cbe2`
- **branch**: `fix/cleanup1-url-text-extractor-tests`
- **git status**: clean

---

## 2. 问题定位

- **失败测试文件**: 5 个文件，共 9 个测试
- **失败测试数量**: 9
- **失败原因**: `example.com` 和 `hn.algolia.com` 在当前 macOS 网络环境中解析到被阻止的私有 IP（`198.18.0.22` / `198.18.0.20`），导致 `url_validator` 的 SSRF 防护将其拒绝
- **是否依赖 example.com**: 是
- **是否依赖真实外部网络**: 是（DNS 解析层面）

**失败测试清单**:

| 测试文件 | 测试名 | 涉及域名 |
|---|---|---|
| tests/test_url_text_extractor.py | test_trafilatura_extractor_returns_text | example.com |
| tests/test_url_text_extractor.py | test_trafilatura_extractor_handles_exception | example.com |
| tests/test_connector_reliability.py | test_hn_empty_hits_is_not_failure | hn.algolia.com |
| tests/test_connector_reliability.py | test_hn_429_produces_warning | hn.algolia.com |
| tests/test_connector_reliability.py | test_manual_url_empty_url_row_skipped | example.com |
| tests/test_hacker_news_connector.py | test_fetch_returns_signals | hn.algolia.com |
| tests/test_manual_url_connector.py | test_fetch_from_csv | example.com |
| tests/test_manual_url_connector.py | test_no_extractor_uses_notes | example.com |
| tests/test_rss_connector.py | test_fetch_from_feed_string | example.com |
| tests/test_rss_connector.py | test_max_items_respected | example.com |

**根本原因**: `TrafilaturaExtractor.extract()` 和多个 connector 在调用 mock HTTP client 之前，先执行了 `validate_url()` 进行 SSRF 检查。`validate_url()` 内部调用 `socket.getaddrinfo()` 解析域名，而当前环境中 `example.com` 和 `hn.algolia.com` 解析到了 `198.18.0.x`（私有/保留地址），被 `_is_ip_private_or_blocked()` 判定为不安全，导致在 mock 层生效前就已经返回错误。

---

## 3. 修复方式

### 3.1 全局 DNS mock（主要修复）

- **使用 mock**: 是
- **使用 fixture**: 是
- **使用 local HTTP server**: 否
- **是否修改业务逻辑**: 否
- **是否新增依赖**: 否

**实现**: 新增 `tests/conftest.py`，创建 session-scoped autouse fixture `mock_blocked_test_dns`：

```python
@pytest.fixture(autouse=True, scope="session")
def mock_blocked_test_dns():
    # 临时替换 socket.getaddrinfo
    # 对 example.com / hn.algolia.com 返回安全公网 IP
    # 其他域名仍走原始 DNS 解析
```

**优势**:
- 零侵入现有测试代码（不改任何已有测试）
- 零侵入业务逻辑（不改任何生产代码）
- 只影响测试环境（session-scoped fixture）
- 对其他域名的 DNS 解析无影响

### 3.2 补充 validate_url mock（辅助修复）

对于 `tests/test_url_text_extractor.py` 中两个缺失 `validate_url` mock 层的测试：
- `test_trafilatura_extractor_returns_text`
- `test_trafilatura_extractor_handles_exception`

补充 `patch("opc_foundation.web.trafilatura_extractor.validate_url")`，确保即使不使用全局 DNS mock，这些测试也能独立通过。

---

## 4. 修改文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `tests/conftest.py` | 新增 | session-scoped autouse DNS mock fixture |
| `tests/test_url_text_extractor.py` | 修改 | 补充 validate_url patch 到 2 个测试 |

---

## 5. 测试结果

| 测试套件 | 结果 |
|---|---|
| tests/test_url_text_extractor.py | 5 passed |
| tests/test_connector_reliability.py | 全部通过 |
| tests/test_hacker_news_connector.py | 全部通过 |
| tests/test_manual_url_connector.py | 全部通过 |
| tests/test_rss_connector.py | 全部通过 |
| tests/source_inventory | 590 passed |
| tests/scripts | 113 passed |
| tests/dashboard | 270 passed |
| **full pytest** | **1946 passed, 0 failed** |

修复前：1937 passed, 9 failed
修复后：1946 passed, 0 failed

---

## 6. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 trial_v2 allowlist | 否 |
| 是否修改 trial_v1 | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |
| 是否修改业务逻辑 | 否 |
| 是否新增外部依赖 | 否 |

---

## 7. Commit / Push

- **branch commit**: `fe5284d`
- **merge commit**: `6dc5a1f`
- **origin/master**: `6dc5a1f`
- **git status**: clean

---

## 8. 下一步建议

- **是否进入 M3C-6B**: 是（测试已稳定，可继续推进 6B 批量修复）
- **M3C-6B 候选**: 36 个 short_term usable 源中筛选高价值候选
- **是否继续暂缓 merck_ir**: 是（allowlist 9 源稳定，merck_ir 保持 next_scheduling_candidate）
- **是否继续暂缓 production**: 是（production_enabled 仍为 false）
