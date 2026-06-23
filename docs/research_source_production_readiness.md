# Research Source Foundation Production Readiness Summary

> 更新时间：2026-06-23
> 状态：Production Trial Ready for Non-WeChat Research Sources

---

## 1. Executive Summary

Research Source Foundation 已完成非微信自动源主线真实公开源验证。

已验证 source_type：
- official_public_research
- podcast_transcript
- conference_transcript
- analyst_action
- media_mention
- rss_feed

可跳过：
- manual_url，人工兜底入口，不属于自动主线

待单独处理：
- wechat_archive

---

## 2. What Is Ready

### 2.1 Source Types Ready for Production Trial

| Source Type | Status | Production Use |
|---|---|---|
| official_public_research | ready with caveats | 官方公开研究页 |
| podcast_transcript | ready with caveats | 官方 podcast/transcript 页面 |
| conference_transcript | ready with caveats | IR/events/webcast/presentation metadata |
| analyst_action | ready with caveats | 公开 rating/target/coverage metadata |
| media_mention | ready with caveats | 公开媒体报道中的机构/分析师/研究提及 |
| rss_feed | ready | 公开 RSS/Atom feed |

### 2.2 Production Capabilities

- validate-config
- dry-run
- run
- check script
- source-health text/json
- daily report
- failed_queue
- duplicate detection
- retry-failed
- documents.jsonl
- documents.latest.jsonl

---

## 3. What Is Not Ready / Out of Scope

- JS rendering
- browser automation
- anti-bot bypass
- paywall bypass
- login/cookie/token
- PDF download/OCR
- audio download/transcription
- investment judgment
- th_capital_stock integration

---

## 4. Recommended Production Source Selection

### Prefer

- official static HTML pages
- valid RSS/Atom feed
- institution-owned public pages
- pages with direct article/event/episode links
- pages with text body in HTML

### Avoid

- JS-only pages
- anti-bot pages
- social platform redirects
- PDF-only repositories
- audio-only pages
- paywalled pages
- noisy official accounts with low signal-to-noise

---

## 5. Suggested Production Local Config Strategy

Start with:

```text
official_public_research: 2-3 sources
rss_feed: 2-3 sources
podcast_transcript: 1-2 sources
conference_transcript: 1-2 sources
analyst_action: 1-2 sources
media_mention: 1-2 sources
```

Keep:

```text
max_items_per_source <= 5 for pilot
download_assets=false
save_markdown=true
save_html=true
save_raw=true
```

Do not commit:

```text
configs/research_sources.production.local.yaml
data/research_archive/
```

---

## 6. Source Health Operating Rules

### Healthy

Source discovers candidates and saves documents or valid duplicates.

### Degraded

Source partially works:
- partial documents
- empty source
- some failed items
- duplicate-only source can still be healthy if expected

### Failed

Source cannot discover candidates or fetch content:
- connector_error
- fetch_error
- parse_error
- anti-bot/JS empty page
- rate limiting

---

## 7. Daily Operating Checklist

1. Run archive
2. Run check script
3. Review source-health
4. Review daily report
5. Inspect failed_queue
6. Verify duplicate behavior
7. Confirm no local config/data committed

---

## 8. Downstream Contract

Downstream systems should consume:

```text
data/research_archive/index/documents.jsonl
data/research_archive/index/documents.latest.jsonl
```

Downstream must not rely on raw local folder scanning.

Foundation does not decide:
- importance
- stock impact
- investment rating
- trade signal
- watchlist mapping

---

## 9. WeChat Status

wechat_archive remains separate.

Important principle:
Do not bulk-follow low signal-to-noise official broker accounts.
WeChat source selection should prioritize high-signal, first-hand research interpretation / meeting notes / industry intelligence sources.

---

## 10. Final Readiness Decision

Decision:
Non-WeChat Research Source Foundation is ready for production trial.

Conditions:
- start with small source set
- monitor source_health
- accept fail-soft behavior
- avoid JS/anti-bot/paywall sources
- keep all investment judgment downstream

---

## Cross-Repo Migration Outlook

Non-WeChat Research Source Foundation is production-trial ready.

The next foundation expansion should not immediately add more noisy research/news sources.  
The recommended next track is official filings:

- SEC EDGAR
- CNINFO
- HKEXnews

Reason:
official filings are public, official, reusable across projects, and separable from investment judgment.

See:
- docs/source_migration_from_th_capital_stock.md
