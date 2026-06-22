"""图片下载。

功能说明（小白解读）：
    下载文章中的图片到本地 images/ 目录，生成 URL -> 本地相对路径的映射表，
    供 Markdown / HTML 改写使用。

    下载失败不会导致整个文章处理失败，只是记录一个 warning。
    同时：
    - 文件名使用 url 的 hash + 扩展名，避免非法字符和重复下载
    - 不会重复下载同一 URL（内存缓存）
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from pathlib import Path
from typing import Iterable

import httpx

from ..storage.path_utils import ensure_parent


def _guess_extension(url: str, content_type: str | None = None) -> str:
    """根据 URL 或 Content-Type 猜测文件扩展名（包括 .）。"""

    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
        if ext:
            # mimetypes 可能返回 .jpe / .htm 之类的，这里标准化几个常见的
            if ext in (".jpe", ".jpeg"):
                return ".jpg"
            if ext == ".htm":
                return ".html"
            return ext

    # 根据 URL 里的文件名后缀
    m = re.search(r"\.([a-zA-Z0-9]{2,5})(?:\?|$)", url)
    if m:
        return "." + m.group(1).lower()

    return ""


def _safe_filename_for(url: str) -> str:
    """根据 URL 生成一个稳定、安全、无路径分隔符的文件名前缀。"""

    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def download_article_images(
    image_urls: Iterable[str],
    archive_dir: str | Path,
    *,
    timeout: int = 15,
    user_agent: str = "Mozilla/5.0",
) -> tuple[dict[str, str], list[str]]:
    """下载一组图片到 archive_dir/images/。

    参数：
        image_urls: 要下载的图片 URL 列表
        archive_dir: 文章归档目录（图片放在它的 images/ 子目录下）
        timeout:    单张图片下载的超时秒数
        user_agent: HTTP User-Agent

    返回：
        (url_to_local, warnings)
        - url_to_local: {原始 URL: 相对路径（images/xxx.jpg）}
        - warnings: 下载失败时的警告信息列表
    """

    root = Path(archive_dir)
    images_dir = root / "images"
    if image_urls:
        images_dir.mkdir(parents=True, exist_ok=True)

    url_map: dict[str, str] = {}
    warnings: list[str] = []
    downloaded_names: set[str] = set()

    for url in image_urls:
        if not url or not isinstance(url, str):
            continue

        base_name = _safe_filename_for(url)
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": user_agent})
                resp.raise_for_status()

                ext = _guess_extension(url, resp.headers.get("Content-Type")) or ""
                filename = base_name + (ext or ".img")
                # 防重复：同 hash 同 ext 就不再下
                if filename in downloaded_names:
                    rel = f"images/{filename}"
                    url_map[url] = rel
                    continue
                target = images_dir / filename
                with open(target, "wb") as fh:
                    fh.write(resp.content)
                downloaded_names.add(filename)
                url_map[url] = f"images/{filename}"
        except Exception as exc:
            warnings.append(f"图片下载失败（{url}）: {exc}")

    return url_map, warnings


def download_cover_image(
    cover_url: str | None,
    archive_dir: str | Path,
    *,
    timeout: int = 15,
    user_agent: str = "Mozilla/5.0",
) -> tuple[str | None, str | None]:
    """下载封面图片到 archive_dir/cover.<ext>。

    返回：
        (本地相对路径, 错误信息)。失败或未提供 URL 时都返回 (None, err)。
    """

    if not cover_url:
        return None, None

    root = Path(archive_dir)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(cover_url, headers={"User-Agent": user_agent})
            resp.raise_for_status()

            ext = _guess_extension(cover_url, resp.headers.get("Content-Type")) or ".jpg"
            filename = "cover" + ext
            target = root / filename
            with open(target, "wb") as fh:
                fh.write(resp.content)
            return filename, None
    except Exception as exc:
        return None, f"封面图下载失败（{cover_url}）: {exc}"
