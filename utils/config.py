"""
配置管理 —— 太空舱宣传视频生成 Agent

本地开发：.env 文件
Streamlit Cloud：Dashboard → Settings → Secrets 中配置
"""

import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _get_secret(key: str, default: str = "") -> str:
    """运行时读取配置：st.secrets → 环境变量 → 默认值。"""
    # 1. Streamlit Cloud secrets
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass

    # 2. st.secrets 嵌套分组
    try:
        import streamlit as st
        for section in st.secrets:
            if isinstance(st.secrets[section], dict):
                val = st.secrets[section].get(key, "")
                if val:
                    return str(val)
    except Exception:
        pass

    # 3. 环境变量
    return os.getenv(key, default)


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_path(p: str) -> str:
    """把相对路径解析为基于项目根目录的绝对路径。"""
    if not p:
        return p
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(PROJECT_ROOT, p))


def get_config() -> dict:
    """读取所有配置（不做校验，非 API 功能也可安全调用）。"""
    output_dir = _resolve_path(
        _get_secret("OUTPUT_DIR", os.path.join(PROJECT_ROOT, "data", "output"))
    )
    references_dir = _resolve_path(
        _get_secret("REFERENCES_DIR", os.path.join(PROJECT_ROOT, "assets", "references"))
    )
    return {
        "api_key": _get_secret("DASHSCOPE_API_KEY", ""),
        "base_url": _get_secret("DASHSCOPE_BASE_URL",
                                "https://dashscope.aliyuncs.com/api/v1"),
        # 图像生成（无参考图时生成虚拟参考图）
        "image_model": _get_secret("IMAGE_MODEL", "wan2.7-image-pro"),
        "image_size": _get_secret("DEFAULT_IMAGE_SIZE", "2K"),
        # 视频生成
        "video_model": _get_secret("VIDEO_MODEL", "wan3.0-video"),
        "video_resolution": _get_secret("VIDEO_RESOLUTION", "720P"),
        "video_ratio": _get_secret("VIDEO_RATIO", "16:9"),
        "video_duration": _to_int(_get_secret("VIDEO_DURATION", "10"), 10),
        # 批量生成
        "daily_count": _to_int(_get_secret("DAILY_VIDEO_COUNT", "5"), 5),
        # 参考图：auto（有参考图则垫图）/ true（强制垫图）/ false（强制纯文生图）
        "use_reference_image": _get_secret("USE_REFERENCE_IMAGE", "auto").strip().lower(),
        # 目录
        "references_dir": references_dir,
        "output_dir": output_dir,
        "images_dir": os.path.join(output_dir, "images"),
        "videos_dir": os.path.join(output_dir, "videos"),
    }


def get_dashscope_cfg() -> dict:
    """返回 DashScope 基础配置（校验 API Key）。"""
    cfg = get_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "未检测到 DASHSCOPE_API_KEY！\n"
            "请将 .env.example 复制为 .env 并填入密钥。"
        )
    return {"api_key": cfg["api_key"], "base_url": cfg["base_url"]}


def get_image_cfg() -> dict:
    """图像生成（无参考图时生成虚拟参考图）配置。"""
    cfg = get_config()
    return {
        "model": cfg["image_model"],
        "size": cfg["image_size"],
        "api_key": cfg["api_key"],
        "base_url": cfg["base_url"],
    }


def get_video_cfg() -> dict:
    """视频生成配置。"""
    cfg = get_config()
    return {
        "model": cfg["video_model"],
        "resolution": cfg["video_resolution"],
        "ratio": cfg["video_ratio"],
        "duration": cfg["video_duration"],
        "api_key": cfg["api_key"],
        "base_url": cfg["base_url"],
    }
