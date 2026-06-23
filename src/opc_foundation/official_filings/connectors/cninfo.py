"""CNINFO 巨潮资讯连接器 —— 采集中国 A 股上市公司公告。

功能说明（小白解读）：
    巨潮资讯（cninfo.com.cn）是中国证监会指定的上市公司信息披露平台。
    本 connector 支持解析巨潮公告列表的 JSON fixture 结构。

    从公告列表中提取：
        - 证券代码
        - 证券简称/公司名
        - 公告标题
        - 公告类型
        - 公告日期
        - 公告 ID
        - PDF URL / announcement URL

MVP 范围：
    - 解析巨潮公告列表 JSON 结构的 fixture
    - 生成 FilingCandidate 列表
    - 支持 max_items 限制
    - 支持 filing_types 过滤

不做：
    - 验证码绕过
    - 反爬绕过
    - 浏览器自动化
    - PDF OCR
    - 公告利好/利空判断
    - 投资建议
"""
from __future__ import annotations

from datetime import datetime

from ..models import FilingArchiveConfig, FilingCandidate, FilingSourceConfig
from .base import OfficialFilingConnector


class CNINFOFilingConnector(OfficialFilingConnector):
    """CNINFO 巨潮资讯公告连接器。

    处理 source_type = cninfo_announcement 的信息源。

    使用方式：
        1. 在 source 配置里指定 endpoint_url（公告查询 API 地址）
        2. connector 读取公告列表 JSON，解析出候选披露
        3. 候选披露交给 archiver 做后续归档

    测试注入：
        构造时传 json_by_url（按 URL 返回 JSON 响应），跳过真实 HTTP。
    """

    connector_id = "cninfo_announcement"

    def discover(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
    ) -> list[FilingCandidate]:
        """从 CNINFO 公告列表 JSON 发现候选披露。

        参数：
            source: 信息源配置
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
                f"CNINFO source [{source.source_id}] 缺少 endpoint_url 或 base_url"
            )

        # 获取 JSON 数据（优先用注入的 fixture）
        raw_data = None
        if self._json_by_url is not None:
            raw_data = self._json_by_url(endpoint)

        if raw_data is None:
            raise ValueError(
                f"CNINFO connector MVP 仅支持 fixture 注入模式，"
                f"请传入 json_by_url 或配置 endpoint_url"
            )

        return self._parse_announcements(source, config, raw_data, endpoint)

    def _parse_announcements(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
        data: dict,
        source_url: str,
    ) -> list[FilingCandidate]:
        """解析 CNINFO 公告列表 JSON 结构。

        CNINFO 公告查询 API 典型返回结构：
            {
              "announcements": [
                {
                  "announcementId": "12345678",
                  "secCode": "000001",
                  "secName": "平安银行",
                  "announcementTitle": "平安银行：2023年年度报告",
                  "announcementType": "年度报告",
                  "announcementTime": 1703721600000,
                  "adjunctUrl": "finalpage/2023-12-28/12345678.PDF"
                }
              ],
              "totalAnnouncement": 100
            }

        参数：
            source:     source 配置
            config:     整体配置
            data:       公告列表 JSON 数据
            source_url: 来源 URL

        返回：
            FilingCandidate 列表
        """
        from datetime import datetime

        from ...run.time_utils import utcnow_iso

        candidates: list[FilingCandidate] = []

        # 公告列表可能在 announcements 字段里，也可能是其他字段名
        announcements = (
            data.get("announcements")
            or data.get("data")
            or data.get("list")
            or []
        )

        if not isinstance(announcements, list):
            return []

        max_items = source.max_items or config.defaults.max_items_per_source
        allowed_types = set(source.filing_types or [])
        now_str = utcnow_iso()

        base_cninfo = source.base_url or "https://www.cninfo.com.cn"

        for item in announcements:
            if len(candidates) >= max_items:
                break

            if not isinstance(item, dict):
                continue

            ann_id = str(item.get("announcementId") or item.get("id") or "")
            sec_code = str(item.get("secCode") or item.get("stockCode") or item.get("code") or "")
            sec_name = str(item.get("secName") or item.get("stockName") or item.get("name") or "")
            title = str(item.get("announcementTitle") or item.get("title") or "")
            ann_type = str(item.get("announcementType") or item.get("type") or "")

            # 公告时间：可能是毫秒时间戳或日期字符串
            ann_time = item.get("announcementTime") or item.get("time") or item.get("date")
            filing_date = self._parse_date(ann_time)

            # PDF URL
            adjunct_url = item.get("adjunctUrl") or item.get("pdfUrl") or item.get("fileUrl") or ""
            pdf_url = None
            if adjunct_url:
                if adjunct_url.startswith("http"):
                    pdf_url = adjunct_url
                else:
                    pdf_url = f"{base_cninfo}/{adjunct_url.lstrip('/')}"

            # 详情页 URL
            detail_url = None
            if ann_id:
                detail_url = f"{base_cninfo}/new/disclosure/detail?plate=&orgId=&stockCode={sec_code}&announcementId={ann_id}"

            # filing_types 过滤
            if allowed_types and ann_type and ann_type not in allowed_types:
                continue

            candidate = FilingCandidate(
                source_id=source.source_id,
                source_type="cninfo_announcement",
                market=source.market or "CN",
                jurisdiction=source.jurisdiction or "CN",
                issuer_name=sec_name,
                issuer_code=sec_code,
                filing_type=ann_type,
                filing_title=title,
                filing_date=filing_date,
                announcement_id=ann_id,
                source_url=source_url,
                document_url=detail_url,
                pdf_url=pdf_url,
                raw_entry=item,
                discovered_at=now_str,
            )
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _parse_date(time_val) -> str | None:
        """解析公告日期。

        支持：
            - 毫秒时间戳（int/float）
            - 日期字符串（YYYY-MM-DD / YYYY/MM/DD 等）
        """
        if not time_val:
            return None

        try:
            # 毫秒时间戳
            ts = float(time_val)
            if ts > 1e12:  # 毫秒级
                ts = ts / 1000
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass

        # 字符串日期
        if isinstance(time_val, str):
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(time_val[:19], fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None
