"""
视频生成模块 —— wan3.0-video 全能视频生成（模型已在代码中写死，
.env 的 VIDEO_MODEL 不再生效，如需换模型改本文件 VIDEO_MODEL 常量）。

协议（异步，官方文档《万相3.0视频生成API参考》）：
    POST {base}/services/aigc/video-generation/video-synthesis
    Header: X-DashScope-Async: enable
    Body:   {"model", "input":{"prompt","media":[{"type":"reference_image","url"}]},
             "parameters":{"resolution","ratio","duration"}}
    返回 task_id → 轮询 GET {base}/tasks/{task_id} → output.video_url

说明：
    - wan3.0-video 为文生/图生/参考生一体模型，参考图走 input.media 数组
      （type=reference_image，最多 10 张，顺序即提示词中 [Image N] 的顺序）。
    - media 的 url 支持公网 URL 或 data:image/...;base64 本地图。
    - parameters.audio 默认 true（wan3.0 自带音轨生成）；如需无声视频，
      在 payload 的 parameters 里显式加 "audio": False。
"""

import os
import time
import base64
import requests
from io import BytesIO
from datetime import datetime

from PIL import Image

from utils.config import get_video_cfg, get_config
from utils.logger import get_logger

logger = get_logger(__name__)

# 模型写死：wan3.0-video（文生/图生/参考生一体，分辨率 480P/720P/1080P，
# 时长 [2,30]s，参考图 ≤10 张）
VIDEO_MODEL = "wan3.0-video"


def _image_to_base64(path: str, max_side: int = 1536) -> str:
    """压缩图片并转 base64（控制体积）。"""
    img = Image.open(path)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _to_url_or_data_uri(path: str) -> str:
    """本地路径转 data URI，公网 URL 直接透传。"""
    if path.startswith(("http://", "https://")):
        return path
    return f"data:image/jpeg;base64,{_image_to_base64(path)}"


def generate_video(reference_images: list, video_prompt: str):
    """
    生成视频。

    参数：
        reference_images : 参考图路径或 URL 列表（顺序即 [Image N] 引用顺序）
        video_prompt     : 视频提示词（可用 [Image N] 引用参考图）

    返回：(success, video_path, message)
    """
    cfg = get_video_cfg()

    payload = {
        "model": VIDEO_MODEL,
        "input": {"prompt": video_prompt},
        "parameters": {
            "resolution": cfg["resolution"],
            "ratio": cfg["ratio"],
            "duration": cfg["duration"],
        },
    }
    if reference_images:
        payload["input"]["media"] = [
            {"type": "reference_image", "url": _to_url_or_data_uri(p)}
            for p in reference_images
        ]
    else:
        logger.warning("未找到参考图，按纯提示词文生视频")

    return _submit_and_poll(payload, cfg)


def _submit_and_poll(payload: dict, cfg: dict):
    """HTTP 异步提交 + 轮询 + 下载。"""
    base = cfg["base_url"].rstrip("/")
    submit_url = f"{base}/services/aigc/video-generation/video-synthesis"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    try:
        resp = requests.post(submit_url, json=payload, headers=headers, timeout=60)
        data = resp.json()
        task_id = ((data.get("output") or {}).get("task_id")) or data.get("task_id")
        if not task_id:
            err = data.get("message") or data.get("code") or resp.text[:200]
            logger.error(f"视频任务提交失败: {err}")
            return False, "", f"视频提交失败: {err}"
    except Exception as e:
        logger.error(f"视频任务提交异常: {e}")
        return False, "", f"视频提交异常: {str(e)[:120]}"

    logger.info(f"视频任务已提交: model={VIDEO_MODEL}, task_id={task_id}")
    video_url = _poll_task(task_id, cfg)
    if not video_url:
        return False, "", "视频生成失败或超时"

    video_path = _download_video(video_url)
    return True, video_path, "视频生成完成"


def _poll_task(task_id: str, cfg: dict, timeout: int = 600, interval: int = 6) -> str:
    """轮询任务直到完成，返回 video_url 或空串。"""
    base = cfg["base_url"].rstrip("/")
    url = f"{base}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()
            output = data.get("output") or {}
            status = output.get("task_status") or data.get("task_status")
            if status == "SUCCEEDED":
                return output.get("video_url", "")
            if status in ("FAILED", "CANCELED"):
                logger.error(f"视频任务{status}: {output.get('message', '')}")
                return ""
        except Exception as e:
            logger.warning(f"轮询异常: {e}")
        time.sleep(interval)

    logger.error("视频任务轮询超时")
    return ""


def _download_video(url: str) -> str:
    """下载视频到 videos_dir，返回本地路径。"""
    videos_dir = get_config()["videos_dir"]
    os.makedirs(videos_dir, exist_ok=True)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(videos_dir, f"video_{ts}.mp4")
    with open(path, "wb") as f:
        f.write(resp.content)
    logger.info(f"视频已保存: {path}")
    return path
