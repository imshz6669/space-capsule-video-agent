"""
参考图管理模块 —— 扫描 assets/references/，按文件名关键词区分外饰/内饰。

参考图由用户预先放置（外饰 + 内饰各房间），生成视频时由 agent.collect_references
按动线顺序直接垫图，不生成任何参考图/首帧图。
"""

import os

from utils.config import get_config

# 参考图文件名关键词 → 视角（用于区分外饰/内饰参考图）
_REFERENCE_KEYWORDS = {
    "exterior": ["exterior", "外饰", "外观", "外部", "outside", "outdoor", "ext"],
    "interior": ["interior", "内饰", "内景", "内部", "inside", "indoor", "inner"],
}

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def list_reference_images(kind: str = "all"):
    """列出参考图目录中的图片路径。kind: all / exterior / interior。"""
    refs_dir = get_config()["references_dir"]
    if not os.path.isdir(refs_dir):
        return []
    files = [f for f in os.listdir(refs_dir)
             if f.lower().endswith(_IMAGE_EXTS) and not f.startswith(".")]
    files = sorted(files)
    if kind == "all":
        return [os.path.join(refs_dir, f) for f in files]
    kws = _REFERENCE_KEYWORDS.get(kind, [])
    return [os.path.join(refs_dir, f) for f in files
            if any(k in f.lower() for k in kws)]
