"""
状态管理模块 —— 视频归档索引。

提供：
    - save_record()  : 保存一条视频记录到 index.json
    - load_records() : 加载历史记录（按时间倒序）
"""

import json
import os
from datetime import datetime

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


def _index_path() -> str:
    return os.path.join(get_config()["output_dir"], "index.json")


def save_record(record: dict) -> bool:
    """保存一条视频归档记录。"""
    try:
        os.makedirs(get_config()["output_dir"], exist_ok=True)

        records = []
        if os.path.exists(_index_path()):
            try:
                with open(_index_path(), "r", encoding="utf-8") as f:
                    records = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                records = []

        record.setdefault("created_at", datetime.now().isoformat())
        records.append(record)

        with open(_index_path(), "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info("归档记录已保存")
        return True

    except Exception as e:
        logger.error(f"归档保存失败: {e}")
        return False


def load_records(limit: int = 100) -> list:
    """加载历史记录（按时间倒序）。"""
    if not os.path.exists(_index_path()):
        return []

    try:
        with open(_index_path(), "r", encoding="utf-8") as f:
            records = json.load(f)
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return records[:limit]

    except (json.JSONDecodeError, FileNotFoundError):
        return []
