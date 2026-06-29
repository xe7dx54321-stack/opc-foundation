"""M3C-5A URL 恢复验证脚本。

功能说明（小白解读）：
    批量验证 URL/DNS/404/HTTP 4xx 类失败源的当前状态，
    并为每个失败源尝试候选替代入口。
    结果会保存到 data/foundation_trial/url_recovery/ 目录下。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 把 src 目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from opc_foundation.source_inventory.url_verify import verify_url


# ============================================
# 候选源清单（来自 triage 报告）
# ============================================

# DNS 解析失败的源
DNS_FAILED_SOURCES = [
    {
        "source_id": "bofa_global_research",
        "source_name": "BofA Global Research",
        "source_group": "official_public_research",
        "original_url": "https://research.bofa.com",
        "original_error": "dns_resolution_failed",
        "candidate_urls": [
            "https://www.bankofamerica.com/research",
            "https://www.bofaml.com",
            "https://www.bankofamerica.com/market-insights",
        ],
    },
    {
        "source_id": "bofa_must_read_research",
        "source_name": "BofA Must Read Research",
        "source_group": "official_public_research",
        "original_url": "https://research.bofa.com/must-read",
        "original_error": "dns_resolution_failed + 404",
        "candidate_urls": [
            "https://www.bankofamerica.com/research/must-read",
            "https://www.bankofamerica.com/market-insights",
        ],
    },
    {
        "source_id": "citi_institute",
        "source_name": "Citi Institute",
        "source_group": "official_public_research",
        "original_url": "https://www.citiinstitute.com",
        "original_error": "dns_resolution_failed",
        "candidate_urls": [
            "https://www.citivelocity.com",
            "https://www.citi.com/insights",
            "https://www.citi.com/citi-gps",
        ],
    },
    {
        "source_id": "china_fund_news",
        "source_name": "中国基金报",
        "source_group": "chinese_rebroadcast",
        "original_url": "https://www.chinafundnews.com",
        "original_error": "dns_resolution_failed",
        "candidate_urls": [
            "https://www.chnfund.com",
            "https://www.chinafund.com.cn",
        ],
    },
    {
        "source_id": "hk_stock_research",
        "source_name": "港股研究社",
        "source_group": "chinese_rebroadcast",
        "original_url": "https://www.hkstockresearch.com",
        "original_error": "dns_resolution_failed",
        "candidate_urls": [
            "https://www.hkstockre.com",
            "https://www.gelonghui.com",
        ],
    },
]

# HTTP 404 的源
HTTP_404_SOURCES = [
    {
        "source_id": "goldman_sachs_greater_china",
        "source_name": "Goldman Sachs Greater China 我们的观点",
        "source_group": "official_public_research",
        "original_url": "https://www.goldmansachs.com/greater-china/our-views",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.goldmansachs.com/insights/china",
            "https://www.goldmansachs.com/insights",
            "https://www.goldmansachs.com/greater-china",
        ],
    },
    {
        "source_id": "barclays_research",
        "source_name": "Barclays Research",
        "source_group": "official_public_research",
        "original_url": "https://www.barclays.com/research",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.barclays.com/insights",
            "https://home.barclays/insights",
            "https://www.barclays.com/investment-bank/insights",
        ],
    },
    {
        "source_id": "barclays_ib_research",
        "source_name": "Barclays Investment Bank Research",
        "source_group": "official_public_research",
        "original_url": "https://www.barclays.com/investment-bank-research",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.barclays.com/investment-bank/insights",
            "https://www.barclays.com/insights",
            "https://home.barclays/insights",
        ],
    },
    {
        "source_id": "goldman_sachs_exchanges",
        "source_name": "Goldman Sachs Exchanges",
        "source_group": "official_podcast_transcript",
        "original_url": "https://www.goldmansachs.com/podcasts/exchanges",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.goldmansachs.com/insights/podcasts/exchanges",
            "https://www.goldmansachs.com/podcasts",
            "https://www.goldmansachs.com/insights/podcasts",
        ],
    },
    {
        "source_id": "goldman_sachs_the_markets",
        "source_name": "Goldman Sachs The Markets",
        "source_group": "official_podcast_transcript",
        "original_url": "https://www.goldmansachs.com/podcasts/the-markets",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.goldmansachs.com/insights/podcasts/the-markets",
            "https://www.goldmansachs.com/insights/podcasts",
            "https://www.goldmansachs.com/podcasts",
        ],
    },
    {
        "source_id": "goldman_sachs_top_of_mind_podcast",
        "source_name": "Goldman Sachs Top of Mind (Podcast)",
        "source_group": "official_podcast_transcript",
        "original_url": "https://www.goldmansachs.com/podcasts/top-of-mind",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.goldmansachs.com/insights/podcasts/top-of-mind",
            "https://www.goldmansachs.com/insights/top-of-mind",
            "https://www.goldmansachs.com/insights/podcasts",
        ],
    },
    {
        "source_id": "goldman_sachs_communacopia",
        "source_name": "Goldman Sachs Communacopia + Technology Conference",
        "source_group": "bank_conference_transcripts",
        "original_url": "https://www.goldmansachs.com/conferences/communacopia",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.goldmansachs.com/events/communacopia",
            "https://www.goldmansachs.com/conferences",
            "https://www.goldmansachs.com/events",
        ],
    },
    {
        "source_id": "barclays_global_tech_conference",
        "source_name": "Barclays Global Technology Conference",
        "source_group": "bank_conference_transcripts",
        "original_url": "https://www.barclays.com/conferences/global-tech",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.barclays.com/investment-bank/conferences",
            "https://www.barclays.com/events",
            "https://www.barclays.com/insights",
        ],
    },
    {
        "source_id": "bernstein_strategic_decisions",
        "source_name": "Bernstein Strategic Decisions Conference",
        "source_group": "bank_conference_transcripts",
        "original_url": "https://www.bernstein.com/conferences/strategic-decisions",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.bernstein.com/conferences",
            "https://www.bernstein.com/insights",
            "https://www.alliancebernstein.com",
        ],
    },
    {
        "source_id": "texas_instruments_ir",
        "source_name": "Texas Instruments Investor Relations",
        "source_group": "bank_conference_transcripts",
        "original_url": "https://www.ti.com/investor",
        "original_error": "http_404",
        "candidate_urls": [
            "https://investor.ti.com",
            "https://www.ti.com/investor-relations",
            "https://ir.ti.com",
        ],
    },
    {
        "source_id": "merck_ir",
        "source_name": "Merck Investor Relations",
        "source_group": "bank_conference_transcripts",
        "original_url": "https://www.merck.com/investor",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.merck.com/investors",
            "https://investors.merck.com",
            "https://ir.merck.com",
        ],
    },
    {
        "source_id": "benzinga_analyst_ratings",
        "source_name": "Benzinga Analyst Ratings",
        "source_group": "analyst_actions",
        "original_url": "https://www.benzinga.com/analytics/ratings",
        "original_error": "http_404",
        "candidate_urls": [
            "https://www.benzinga.com/analyst-ratings",
            "https://www.benzinga.com/news/analyst-ratings",
            "https://www.benzinga.com",
        ],
    },
    {
        "source_id": "jiwen_vip_public",
        "source_name": "见闻VIP公开文章",
        "source_group": "chinese_rebroadcast",
        "original_url": "https://wallstreetcn.com/vip",
        "original_error": "http_404",
        "candidate_urls": [
            "https://wallstreetcn.com/news",
            "https://wallstreetcn.com/articles",
            "https://wallstreetcn.com",
        ],
    },
]

# HTTP 403 的源（排除 browser_like_needed 的 streetinsider 和 tipranks）
HTTP_403_SOURCES = [
    {
        "source_id": "investing_com_analyst_ratings",
        "source_name": "Investing.com Analyst Ratings",
        "source_group": "analyst_actions",
        "original_url": "https://www.investing.com/equities/ratings",
        "original_error": "http_403",
        "candidate_urls": [
            "https://www.investing.com/analysts/ratings",
            "https://www.investing.com/stock-screener",
            "https://www.investing.com/news",
        ],
    },
]

# HTTP 401 / 需要登录的源
HTTP_401_SOURCES = [
    {
        "source_id": "reuters",
        "source_name": "Reuters",
        "source_group": "media_research_mentions",
        "original_url": "https://www.reuters.com",
        "original_error": "http_401_需要登录",
        "candidate_urls": [
            "https://www.reuters.com/news",
            "https://www.reuters.com/business",
            "https://www.reuters.com/markets",
        ],
    },
    {
        "source_id": "marketwatch",
        "source_name": "MarketWatch",
        "source_group": "media_research_mentions",
        "original_url": "https://www.marketwatch.com",
        "original_error": "http_401_需要登录",
        "candidate_urls": [
            "https://www.marketwatch.com/investing",
            "https://www.marketwatch.com/news",
            "https://www.marketwatch.com/story",
        ],
    },
    {
        "source_id": "marketwatch_upgrades_downgrades",
        "source_name": "MarketWatch Upgrades/Downgrades",
        "source_group": "analyst_actions",
        "original_url": "https://www.marketwatch.com/tools/upgrades-downgrades",
        "original_error": "http_401_需要登录",
        "candidate_urls": [
            "https://www.marketwatch.com/investing/stock-analyst-ratings",
            "https://www.marketwatch.com/news",
        ],
    },
    {
        "source_id": "wsj_upgrades_downgrades",
        "source_name": "WSJ Market Data Upgrades/Downgrades",
        "source_group": "analyst_actions",
        "original_url": "https://www.wsj.com/market-data/quotes/upgrades-downgrades",
        "original_error": "http_401_需要订阅",
        "candidate_urls": [
            "https://www.wsj.com/market-data",
            "https://www.wsj.com/news",
        ],
    },
]

# URL verification needed（超时）
URL_VERIFICATION_NEEDED = [
    {
        "source_id": "quanshang_china",
        "source_name": "券商中国",
        "source_group": "chinese_rebroadcast",
        "original_url": "https://www.quanshang.cn",
        "original_error": "timed_out",
        "candidate_urls": [
            "https://www.quanshang.cn/news",
            "http://www.quanshang.cn",
        ],
    },
]


def verify_source(source: dict, timeout: int = 20) -> dict:
    """验证单个源及其候选 URL。

    功能说明（小白解读）：
        对一个源的原始 URL 和所有候选 URL 都做验证，
        然后找出最好的那个替代入口。

    Args:
        source: 源信息字典，包含 source_id, original_url, candidate_urls 等
        timeout: 每个 URL 验证的超时秒数

    Returns:
        dict: 包含完整验证结果的字典
    """
    result = {
        "source_id": source["source_id"],
        "source_name": source["source_name"],
        "source_group": source["source_group"],
        "original_url": source["original_url"],
        "original_error": source["original_error"],
        "original_url_verify": None,
        "candidate_results": [],
        "selected_url": "",
        "selected_url_status": "",
        "fix_result": "unchanged_not_recoverable",
        "trial_v2_eligible": False,
        "reason": "",
        "recommended_action": "",
    }

    # 1. 验证原始 URL
    print(f"  验证原始 URL: {source['original_url']}")
    orig_result = verify_url(source["original_url"], timeout=timeout)
    result["original_url_verify"] = orig_result.to_dict()
    print(f"    结果: {orig_result.final_verdict} - {orig_result.notes}")

    # 如果原始 URL 现在是好的，直接返回
    if orig_result.final_verdict in ("reachable", "python_client_limited"):
        result["selected_url"] = source["original_url"]
        result["selected_url_status"] = orig_result.final_verdict
        result["fix_result"] = "url_fixed_trial_v2_candidate"
        result["trial_v2_eligible"] = True
        result["reason"] = "原始 URL 现在可访问"
        result["recommended_action"] = "直接纳入 trial_v2"
        return result

    # 2. 验证候选 URL
    best_result = None
    best_url = ""
    best_score = -1

    # 评分标准：reachable=3, browser_like_needed=2, http_4xx=1, 其他=0
    score_map = {
        "reachable": 3,
        "python_client_limited": 3,
        "browser_like_needed": 2,
        "http_4xx": 1,
        "http_5xx": 0,
        "dns_failed": 0,
        "tls_handshake_failed": 0,
        "unreachable": 0,
    }

    for cand_url in source.get("candidate_urls", []):
        print(f"  验证候选 URL: {cand_url}")
        cand_result = verify_url(cand_url, timeout=timeout)
        cand_info = {
            "url": cand_url,
            "verdict": cand_result.final_verdict,
            "status_code": cand_result.curl_status,
            "notes": cand_result.notes,
            "dns_resolvable": cand_result.dns_resolvable,
        }
        result["candidate_results"].append(cand_info)
        print(f"    结果: {cand_result.final_verdict} - {cand_result.notes}")

        score = score_map.get(cand_result.final_verdict, 0)
        if score > best_score:
            best_score = score
            best_result = cand_result
            best_url = cand_url

    # 3. 判断修复结果
    if best_score >= 3:
        # 找到了可直接访问的替代入口
        result["selected_url"] = best_url
        result["selected_url_status"] = best_result.final_verdict
        # 判断相关性：URL 路径是否还在原机构域名下
        if best_result.final_verdict in ("reachable", "python_client_limited"):
            result["fix_result"] = "url_fixed_trial_v2_candidate"
            result["trial_v2_eligible"] = True
            result["reason"] = f"找到可访问的官方替代入口: {best_url}"
            result["recommended_action"] = "更新 source inventory，纳入 trial_v2 候选"
        else:
            result["fix_result"] = "official_alternative_found"
            result["trial_v2_eligible"] = False
            result["reason"] = f"找到替代入口但需进一步评估: {best_url}"
            result["recommended_action"] = "评估相关性后决定是否纳入"
    elif best_score == 2:
        # 需要浏览器 UA
        result["selected_url"] = best_url
        result["selected_url_status"] = best_result.final_verdict
        result["fix_result"] = "browser_like_candidate"
        result["trial_v2_eligible"] = False
        result["reason"] = f"找到替代入口但需浏览器式 UA: {best_url}"
        result["recommended_action"] = "后续 browser-like connector 支持后再纳入"
    elif best_score == 1:
        # 还是 4xx
        if not orig_result.dns_resolvable:
            result["fix_result"] = "dns_backlog"
            result["reason"] = "DNS 解析失败，候选入口也不可用"
            result["recommended_action"] = "继续寻找替代入口"
        else:
            result["fix_result"] = "url_backlog"
            result["reason"] = "候选入口也返回 4xx，需进一步寻找"
            result["recommended_action"] = "继续寻找替代入口或移除该源"
    else:
        # 都不行
        if not orig_result.dns_resolvable:
            result["fix_result"] = "dns_backlog"
            result["reason"] = "DNS 解析失败，未找到有效替代入口"
            result["recommended_action"] = "继续寻找替代入口或标记为 replace_or_remove"
        else:
            result["fix_result"] = "url_backlog"
            result["reason"] = "所有候选入口均不可用"
            result["recommended_action"] = "继续寻找替代入口或标记为 replace_or_remove"

    return result


def main():
    """主函数：批量验证所有候选源。"""
    all_sources = (
        DNS_FAILED_SOURCES
        + HTTP_404_SOURCES
        + HTTP_403_SOURCES
        + HTTP_401_SOURCES
        + URL_VERIFICATION_NEEDED
    )

    print(f"=" * 60)
    print(f"M3C-5A URL 恢复验证")
    print(f"处理源数: {len(all_sources)}")
    print(f"=" * 60)

    results = []
    stats = {
        "total": len(all_sources),
        "url_fixed_trial_v2_candidate": 0,
        "official_alternative_found": 0,
        "media_alternative_found": 0,
        "browser_like_candidate": 0,
        "dns_backlog": 0,
        "url_backlog": 0,
        "source_url_invalid": 0,
        "replace_or_remove_candidate": 0,
        "unchanged_not_recoverable": 0,
    }

    for i, source in enumerate(all_sources, 1):
        print(f"\n[{i}/{len(all_sources)}] {source['source_id']} - {source['source_name']}")
        try:
            result = verify_source(source, timeout=20)
            results.append(result)
            stats[result["fix_result"]] = stats.get(result["fix_result"], 0) + 1
        except Exception as e:
            print(f"  验证出错: {e}")
            result = {
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "source_group": source["source_group"],
                "original_url": source["original_url"],
                "original_error": source["original_error"],
                "fix_result": "unchanged_not_recoverable",
                "trial_v2_eligible": False,
                "reason": f"验证异常: {e}",
                "recommended_action": "手动验证",
            }
            results.append(result)
            stats["unchanged_not_recoverable"] += 1

    # 保存结果
    output_dir = Path(__file__).parent.parent / "data" / "foundation_trial" / "url_recovery"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"url_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_time": datetime.now().isoformat(),
                "stats": stats,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n{'=' * 60}")
    print("验证完成！统计结果：")
    print(f"{'=' * 60}")
    print(f"总源数: {stats['total']}")
    print(f"  成功修复 (trial_v2 候选): {stats['url_fixed_trial_v2_candidate']}")
    print(f"  找到官方替代入口: {stats['official_alternative_found']}")
    print(f"  找到媒体替代入口: {stats['media_alternative_found']}")
    print(f"  需浏览器 UA: {stats['browser_like_candidate']}")
    print(f"  DNS backlog: {stats['dns_backlog']}")
    print(f"  URL backlog: {stats['url_backlog']}")
    print(f"  未恢复: {stats['unchanged_not_recoverable']}")
    print(f"\n结果已保存到: {output_file}")

    return results, stats


if __name__ == "__main__":
    main()
