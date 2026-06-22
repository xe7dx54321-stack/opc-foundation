"""本地文件写入与目录管理。

功能说明（小白解读）：
    - 为每篇文章生成一个稳定的目录名（日期_公众号名_标题slug）
    - 写 metadata.json / article.md / article.html / images/
    - 追加写 index/articles.jsonl
    - 写 state/run_log.jsonl 和 state/failed_queue.jsonl

    所有写入都尽量用 UTF-8，中文不转义。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ArchivedArticle, FailedArticle


# 非法文件名字符（Windows 下更严格，这里统一处理）
_INVALID_FS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_WS = re.compile(r"\s+")


def sanitize_filename(text: str, max_len: int = 40, default: str = "untitled") -> str:
    """把一段文本转成合法的文件名片段（保留中英文、数字、常见符号）。"""

    if not text:
        return default
    cleaned = _INVALID_FS.sub(" ", text).strip()
    cleaned = _WS.sub("-", cleaned)
    cleaned = cleaned.strip("-.")
    if not cleaned:
        return default
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip("-")
    return cleaned or default


def article_directory(
    archive_root: str | Path,
    published_at: str | None,
    account_name: str | None,
    title: str,
    fallback_datetime: datetime | None = None,
) -> Path:
    """为一篇文章生成一个稳定、可读、无非法字符的本地目录。

    目录结构：
        <archive_root>/articles/YYYY/MM/<YYYY-MM-DD>__<account>__<title-slug>/
    """

    root = Path(archive_root)
    # 解析或使用当前日期
    try:
        if published_at:
            # 宽松解析：支持 ISO、YYYY-MM-DD HH:MM 等
            date_part = re.split(r"[T ]", published_at.strip(), maxsplit=1)[0]
            y, m, d = date_part.split("-")
        else:
            raise ValueError("no date")
    except Exception:
        now = fallback_datetime or datetime.now()
        y, m, d = f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}"

    dir_name = f"{y}-{m}-{d}__{sanitize_filename(account_name or 'unknown', max_len=30)}__{sanitize_filename(title, max_len=40)}"
    return root / "articles" / y / m / dir_name


# ---------------------------------------------------------------------------
# 原子化文件写入
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写文件：先写到临时文件，再 rename 过去，避免写入过程中断造成半文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        # 失败时清理临时文件
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def write_markdown(path: str | Path, text: str) -> Path:
    p = Path(path)
    _atomic_write(p, text or "")
    return p


def write_html(path: str | Path, html: str) -> Path:
    p = Path(path)
    _atomic_write(p, html or "")
    return p


def write_metadata(path: str | Path, data: dict[str, Any]) -> Path:
    p = Path(path)
    _atomic_write(p, json.dumps(data, ensure_ascii=False, indent=2))
    return p


# ---------------------------------------------------------------------------
# JSONL 追加（非原子，但每一行都是完整 JSON）
# ---------------------------------------------------------------------------


def append_jsonl(path: str | Path, record: dict[str, Any] | ArchivedArticle) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(record, ArchivedArticle):
        line = record.model_dump_json(
            exclude_none=True,
        )
    elif isinstance(record, FailedArticle):
        line = record.model_dump_json(exclude_none=True)
    else:
        line = json.dumps(record, ensure_ascii=False)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_failed_queue(path: str | Path) -> list[FailedArticle]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[FailedArticle] = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                out.append(FailedArticle(**data))
            except Exception:
                continue
    return out
