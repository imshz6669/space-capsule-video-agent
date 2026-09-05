"""
编排层 —— 单条视频的线性 pipeline。

流程（wan3.0-video 参考图生视频）：
    run_one_video(task)
        ├─ 参考图：直接用 task 里的 reference_images（用户预先放置在
        │   assets/references/；缺失时只告警并按纯提示词生成，不生成参考图）
        ├─ video_gen.generate_video(reference_images, prompt)  → 宣传视频
        └─ state_manager.save_record()                         → 归档
"""

from .video_gen import generate_video
from .state_manager import save_record
from utils.logger import get_logger

logger = get_logger(__name__)


def run_one_video(task: dict) -> dict:
    """
    执行单条视频生成。

    参数：
        task : compose_task() 返回的任务 dict

    返回：
        更新后的 task，含 reference_images / video_path / status / error。
    """
    result = dict(task)

    # 1. 参考图（已就位则直接垫图；缺失时不生成参考图，走纯提示词生成）
    refs = list(task.get("reference_images", []))
    if not refs:
        logger.warning("未找到参考图，按纯提示词生成视频（不生成参考图）")

    # 2. 视频生成
    ok, video_path, msg = generate_video(refs, task["video_prompt"])
    if not ok:
        result["status"] = "failed"
        result["error"] = msg
        logger.error(f"视频生成失败: {msg}")
        return result
    result["video_path"] = video_path

    # 3. 归档
    save_record({
        "scene": task["scene"],
        "view": task["view"],
        "view_label": task["view_label"],
        "camera": task["camera"],
        "video_prompt": task["video_prompt"],
        "reference_images": refs,
        "video_path": video_path,
    })

    result["status"] = "done"
    logger.info(f"单条视频完成: {task['scene']}/{task['view_label']}/{task['camera']}")
    return result
