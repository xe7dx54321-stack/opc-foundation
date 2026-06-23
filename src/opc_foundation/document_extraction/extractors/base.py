"""Document Extractor 协议定义。

功能说明（小白解读）：
    本文件定义了 DocumentExtractor 协议，
    所有具体的提取器（如 PDF、HTML、TXT、Markdown）都必须实现这个协议。

    协议要求实现两个方法：
    - can_extract: 判断这个提取器是否能处理这个文档候选
    - extract:     对文档进行抽取，返回抽取结果

    提取器必须设计为 fail-soft：单个文档失败不能影响全局运行。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import DocumentCandidate, ExtractedDocument


@runtime_checkable
class DocumentExtractor(Protocol):
    """文档提取器协议。

    所有提取器必须实现 can_extract 和 extract 方法。

    设计原则（小白解读）：
        1. fail-soft：extract 方法内部出错应该捕获并返回 failed 状态，
           而不是让异常向上传播。
        2. 单文档失败不拖垮全局 run。
        3. 不做投资判断。
        4. 不调用真实网络（除了 document_url，fixture 测试用）。
        5. 支持 fixture 测试。
    """

    def can_extract(self, candidate: DocumentCandidate) -> bool:
        """判断这个提取器是否能处理这个文档候选。

        参数：
            candidate: 文档候选对象

        返回：
            True 如果这个提取器能处理，否则 False
        """
        ...

    def extract(self, candidate: DocumentCandidate) -> ExtractedDocument:
        """抽取文档内容。

        参数：
            candidate: 文档候选对象

        返回：
            ExtractedDocument 抽取结果

        注意：
            此方法应该 fail-soft，内部捕获所有异常并返回 failed 状态。
        """
        ...
