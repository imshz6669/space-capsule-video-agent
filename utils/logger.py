"""
日志工具模块 —— 统一的日志输出。

提供：
    - get_logger(name) : 返回配置好的 logging.Logger 实例
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    获取一个配置好的 logger 实例。

    参数：
        name : logger 名称（通常传 __name__）

    返回：
        logging.Logger 实例。
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # 控制台输出
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)

        # 格式
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # 防止日志冒泡到 root logger
        logger.propagate = False

    return logger
