"""SEC EDGAR 连接器 —— 采集美国 SEC 官方披露。

功能说明（小白解读）：
    SEC（美国证券交易委员会）的 EDGAR 系统是美国上市公司披露的官方来源。
    本 connector 支持从 SEC submissions JSON 接口发现候选披露。

    SEC 的 submissions JSON 包含一个公司所有的披露历史记录，我们从中提取：
        - cik（公司编号）
        - 公司名称
        - 披露类型（10-K / 10-Q / 8-K / S-1 等）
        - 披露日期
        - accession number（披露唯一编号）
        - primary document（主文档文件名）
        - 详情页 URL
        - 文档 URL

MVP 范围：
    - 解析 submissions JSON 结构的 fixture
    - 生成 FilingCandidate 列表
    - 支持 max_items 限制
    - 支持 filing_types 过滤

不做：
    - XBRL 解析
    - 财务指标提取
    - 公司估值
    - 风险判断
    - 投资建议
"""
from __future__ import annotations

from urllib.parse import urljoin

from ..models import FilingArchiveConfig, FilingCandidate, FilingSourceConfig
from .base import OfficialFilingConnector


class SECFilingConnector(OfficialFilingConnector):
    """SEC EDGAR 官方披露连接器。

    处理 source_type = sec_edgar 的信息源。

    使用方式：
        1. 在 source 配置里指定 endpoint_url（submissions JSON URL）
        2. connector 读取 submissions JSON，解析出候选披露
        3. 候选披露交给 archiver 做后续归档

    测试注入：
        构造时传 json_by_url（按 URL 返回 JSON 响应），跳过真实 HTTP。
    """

    connector_id = "sec_edgar"

    def discover(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
    ) -> list[FilingCandidate]:
        """从 SEC submissions JSON 发现候选披露。

        参数：
            source: 信息源配置（使用 endpoint_url 作为 submissions JSON 地址）
            config: 整体配置

        返回：
            FilingCandidate 列表

        异常：
            缺少 endpoint_url 时抛出 ValueError
            解析失败时抛出异常（由上层 fail-soft 捕获）
        """
        endpoint = source.endpoint_url or source.base_url
        if not endpoint:
            raise ValueError(
                f"SEC source [{source.source_id}] 缺少 endpoint_url 或 base_url"
            )

        # 获取 JSON 数据
        # 1. 优先用注入的 fixture（测试模式）
        # 2. 否则使用真实 HTTP fetch（生产模式）
        raw_data = None

        if self._json_by_url is not None:
            # 测试注入模式
            raw_data = self._json_by_url(endpoint)
        else:
            # 真实 HTTP fetch（使用 Python 内置 urllib）
            import json
            import ssl
            import urllib.request

            user_agent = config.defaults.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            timeout = config.defaults.fetch_timeout_seconds or 30

            try:
                # 创建 SSL context
                ctx = ssl.create_default_context()

                # 构建请求，添加必要的 headers
                req = urllib.request.Request(
                    endpoint,
                    headers={
                        "User-Agent": user_agent,
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Encoding": "gzip, deflate",
                    }
                )

                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                    raw_bytes = response.read()
                    # 处理 gzip 压缩
                    if response.headers.get("Content-Encoding") == "gzip":
                        import gzip
                        raw_bytes = gzip.decompress(raw_bytes)
                    raw_text = raw_bytes.decode("utf-8", errors="replace")
                    raw_data = json.loads(raw_text)

            except Exception as e:
                raise ValueError(
                    f"SEC fetch 失败 [{endpoint}]: {type(e).__name__}: {e}"
                ) from None

        return self._parse_submissions(source, config, raw_data, endpoint)

    def _parse_submissions(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
        data: dict,
        source_url: str,
    ) -> list[FilingCandidate]:
        """解析 SEC submissions JSON 结构。

        SEC submissions JSON 典型结构：
            {
              "cik": "0000320193",
              "entityName": "Apple Inc.",
              "filings": {
                "recent": {
                  "accessionNumber": [...],
                  "filingDate": [...],
                  "form": [...],
                  "primaryDocument": [...]
                }
              }
            }

        参数：
            source:     source 配置
            config:     整体配置
            data:       submissions JSON 数据
            source_url: 来源 URL

        返回：
            FilingCandidate 列表
        """
        from ..dedupe import _sha256_hex
        from ...run.time_utils import utcnow_iso

        candidates: list[FilingCandidate] = []

        # 公司基本信息
        cik = str(data.get("cik", "")).lstrip("0")
        entity_name = data.get("entityName", "")

        # filing 数据在 filings.recent 里（平行数组）
        filings = data.get("filings", {})
        recent = filings.get("recent", {})

        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        forms = recent.get("form", [])
        primary_docs = recent.get("primaryDocument", [])
        items = recent.get("items", [])

        # 确定 max_items
        max_items = source.max_items or config.defaults.max_items_per_source
        # filing_types 过滤
        allowed_types = set(source.filing_types or [])

        count = len(accession_numbers)
        now_str = utcnow_iso()

        for i in range(count):
            if len(candidates) >= max_items:
                break

            form_type = forms[i] if i < len(forms) else ""
            # 如果指定了 filing_types 过滤，跳过不匹配的
            if allowed_types and form_type not in allowed_types:
                continue

            accession = accession_numbers[i] if i < len(accession_numbers) else ""
            filing_date = filing_dates[i] if i < len(filing_dates) else ""
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""

            if not accession:
                continue

            # 构建 URL
            # SEC 文档 URL 格式：https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_no_dashes}/{primary_doc}
            acc_no_dashes = accession.replace("-", "")
            base_sec = source.base_url or "https://www.sec.gov"

            # 详情页 URL（index 页）
            detail_url = urljoin(
                base_sec,
                f"/Archives/edgar/data/{cik}/{acc_no_dashes}/{accession}-index.htm"
            )

            # 主文档 URL
            doc_url = urljoin(
                base_sec,
                f"/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary_doc}"
            ) if primary_doc else None

            # 判断是 HTML 还是其他格式
            html_url = None
            pdf_url = None
            if primary_doc:
                if primary_doc.endswith(".htm") or primary_doc.endswith(".html"):
                    html_url = doc_url
                elif primary_doc.endswith(".pdf"):
                    pdf_url = doc_url

            # 标题：用 form type + 日期 + items 描述
            item_desc = items[i] if i < len(items) else ""
            title_parts = [form_type]
            if item_desc:
                title_parts.append(str(item_desc))
            filing_title = " - ".join([p for p in title_parts if p])

            candidate = FilingCandidate(
                source_id=source.source_id,
                source_type="sec_edgar",
                market=source.market or "US",
                jurisdiction=source.jurisdiction or "US",
                issuer_name=entity_name,
                issuer_code=cik,
                filing_type=form_type,
                filing_title=filing_title,
                filing_date=filing_date,
                accession_number=accession,
                source_url=source_url,
                document_url=detail_url,
                html_url=html_url,
                pdf_url=pdf_url,
                raw_entry={
                    "accession_number": accession,
                    "filing_date": filing_date,
                    "form": form_type,
                    "primary_document": primary_doc,
                    "items": item_desc,
                },
                discovered_at=now_str,
            )
            candidates.append(candidate)

        return candidates
