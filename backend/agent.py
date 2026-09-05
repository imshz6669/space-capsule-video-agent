"""
场景编排模块 —— 按指定场景收集参考图，构建单条视频任务。

视频为一镜到底 walkthrough（外饰 → 客厅 → 主卧 → 卫生间 → 回主卧 →
落地窗看景）；场景由用户在「生成设置」中指定（雪地/深林/草地），
不再随机抽取。
参考图按动线顺序传入 media（r2v 模型按 media 顺序参观房间，顺序即动线，
见 prompts.py 模块 docstring），末尾重复主卧参考图锚定「回主卧落地窗收尾」。
"""

import os

from .prompts import build_video_prompt
from .image_gen import list_reference_images
from utils.logger import get_logger

logger = get_logger(__name__)

# 动线房间（按参观顺序）→ 参考图文件名关键词；某房间缺文件时该拍无垫图，仅靠文字描述
_ROOM_ORDER = (
    ("客厅", ("living", "客厅")),
    ("主卧", ("bedroom", "主卧")),
    ("卫生间", ("bath", "toilet", "卫生间")),
)


def _pick_room(paths: list, keywords: tuple) -> str:
    """按文件名关键词找出房间参考图路径，找不到返回 None。"""
    for p in paths:
        name = os.path.basename(p).lower()
        if any(k.lower() in name for k in keywords):
            return p
    return None


def collect_references() -> list:
    """按 walkthrough 参观顺序收集参考图（顺序即动线，末尾重复主卧锚定收尾）。"""
    exterior = list_reference_images("exterior")
    interior = list_reference_images("interior")
    picked = {key: _pick_room(interior, kws) for key, kws in _ROOM_ORDER}

    refs = exterior[:1]
    refs += [picked[key] for key, _ in _ROOM_ORDER if picked.get(key)]
    if picked.get("主卧"):
        refs.append(picked["主卧"])

    logger.info(f"参考图按动线排序: {len(refs)}张, 动线=外饰→客厅→主卧→卫生间→回主卧")
    return refs


def compose_task(scene: str) -> dict:
    """编排一条指定场景的视频任务。"""
    refs = collect_references()

    task = {
        "scene": scene,
        "view": "walkthrough",
        "view_label": "内外饰一镜到底",
        "camera": "第一人称步行",
        "reference_images": refs,
        "video_prompt": build_video_prompt(scene),
    }
    logger.info(f"编排任务: 场景={scene}, 参考图={len(refs)}张")
    return task


def compose_tasks(n: int, scene: str) -> list:
    """编排 n 条指定场景的视频任务。"""
    return [compose_task(scene) for _ in range(max(0, n))]
