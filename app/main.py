"""
Streamlit 前端 —— 太空舱宣传视频生成 Agent

核心流程：参考图管理 + 一键生成 N 条 → 队列逐条执行（首帧图 → 视频）→ 预览/下载
布局：左侧控制面板（生成设置 + 参考图）+ 右侧结果面板 + 底部历史归档
"""

import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

from backend.agent import compose_tasks
from backend.graph import run_one_video
from backend.image_gen import list_reference_images
from backend.prompts import SCENES
from backend.state_manager import load_records
from backend.video_gen import VIDEO_MODEL
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="太空舱宣传视频生成 Agent",
    page_icon=":material/rocket_launch:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================== CSS（太空舱科技风） ====================

st.markdown("""
<style>
    .stApp {
        background-color: #0A1020;
        background-image:
            linear-gradient(rgba(56,189,248,0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(56,189,248,0.035) 1px, transparent 1px),
            radial-gradient(1100px 560px at 82% -8%, rgba(56,189,248,0.13), transparent 60%),
            radial-gradient(900px 520px at -8% 108%, rgba(14,165,233,0.10), transparent 60%),
            linear-gradient(160deg, #0A1020 0%, #0D1730 45%, #0A1322 100%);
        background-size: 44px 44px, 44px 44px, auto, auto, auto;
        color: #E6EDF6;
    }
    p, span, label, .stMarkdown, .stCaption, div[data-testid="stText"] {
        color: #E2EBF6 !important;
    }
    .stCaption p { color: #AFC4DD !important; }
    #MainMenu, footer, header { visibility: hidden; }

    .navbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.75rem 1.4rem;
        background: linear-gradient(180deg, rgba(22,36,60,0.82), rgba(16,26,46,0.72));
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(56,189,248,0.18);
        border-radius: 14px; margin-bottom: 0.9rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.30), inset 0 1px 0 rgba(125,211,252,0.10);
        position: relative; overflow: hidden;
    }
    .navbar::after {
        content: ""; position: absolute; left: 14px; right: 14px; bottom: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(56,189,248,0.55), transparent);
    }
    .navbar-left { display: flex; flex-direction: column; }
    .navbar-brand {
        font-size: 1.15rem; font-weight: 700; color: #EAF4FF;
        letter-spacing: 0.5px;
    }
    .navbar-brand .accent { color: #38BDF8; }
    .navbar-sub {
        font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
        font-size: 0.66rem; letter-spacing: 0.16em; color: #8CA5C4; margin-top: 3px;
    }
    .navbar-status {
        font-size: 0.78rem; color: #B7D3EC; display: flex; align-items: center; gap: 7px;
        font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    }
    .navbar-status .dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #34D399; box-shadow: 0 0 10px #34D399;
        animation: breathe 2.2s ease-in-out infinite;
    }
    @keyframes breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

    .panel {
        background: linear-gradient(180deg, rgba(18,30,52,0.90), rgba(13,22,40,0.85));
        border-radius: 14px; padding: 1.35rem;
        border: 1px solid rgba(56,189,248,0.16);
        box-shadow: 0 8px 32px rgba(0,0,0,0.32), inset 0 1px 0 rgba(125,211,252,0.08);
        position: relative;
    }
    .panel::before {
        content: ""; position: absolute; top: 0; left: 12px; right: 12px; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(56,189,248,0.5), transparent);
    }
    .panel-title {
        font-size: 1rem; font-weight: 600; color: #EAF4FF;
        letter-spacing: 0.02em; margin-bottom: 0.8rem;
    }

    .empty-icon { font-size: 3rem; margin-bottom: 0.8rem; }
    .empty-title { font-size: 1rem; font-weight: 600; color: #EAF4FF; margin-bottom: 0.3rem; }
    .empty-desc { font-size: 0.82rem; color: #A3B8D1; }

    .loading-spinner {
        width: 48px; height: 48px; margin: 0 auto 1rem;
        border: 3px solid rgba(56,189,248,0.14);
        border-top-color: #38BDF8; border-radius: 50%;
        box-shadow: 0 0 24px rgba(56,189,248,0.35);
        animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-text { color: #B7D3EC; font-weight: 500; font-size: 0.92rem; }
    .loading-timer { color: #8FA8C6; font-size: 0.8rem; margin-top: 0.3rem; }

    .stButton > button {
        background: linear-gradient(135deg, #0EA5E9, #0284C7) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
        transition: all 0.2s !important;
        box-shadow: 0 0 0 1px rgba(125,211,252,0.20) inset, 0 4px 18px rgba(14,165,233,0.32) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 0 0 1px rgba(125,211,252,0.30) inset, 0 6px 26px rgba(14,165,233,0.55) !important;
    }
    .stButton > button:disabled {
        background: #1C2A42 !important; color: #8FA8C6 !important; box-shadow: none !important;
    }

    input[type="text"] {
        border-radius: 8px !important; border-color: rgba(56,189,248,0.22) !important;
    }

    .result-card {
        background: rgba(16,26,46,0.72); border-radius: 12px; padding: 1rem;
        border: 1px solid rgba(56,189,248,0.14); margin-bottom: 1rem;
        box-shadow: inset 0 1px 0 rgba(125,211,252,0.05);
    }
    .result-meta {
        color: #B7D3EC; font-size: 0.85rem; margin-bottom: 0.5rem;
        font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    }
    .result-meta b { color: #EAF4FF; }

    .ref-chip {
        display: inline-block; background: rgba(14,165,233,0.12);
        border: 1px solid rgba(56,189,248,0.24); border-radius: 7px;
        padding: 0.2rem 0.6rem; font-size: 0.78rem; color: #B7D3EC; margin: 0.15rem;
        font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: rgba(56,189,248,0.14) !important;
    }

    .site-footer {
        text-align: center; padding: 1.4rem 0 0.5rem;
        color: #8FA8C6; font-size: 0.78rem; opacity: 0.85;
        font-family: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    }

    @media (prefers-reduced-motion: reduce) {
        .navbar-status .dot, .loading-spinner { animation: none; }
    }
</style>
""", unsafe_allow_html=True)


# ==================== Session ====================

def init_session():
    if "gen_queue" not in st.session_state:
        st.session_state.gen_queue = []          # 待执行任务队列
    if "gen_results" not in st.session_state:
        st.session_state.gen_results = []        # 已完成结果
    if "total_count" not in st.session_state:
        st.session_state.total_count = 0
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "current_task" not in st.session_state:
        st.session_state.current_task = None     # 正在生成的任务（进度显示）


# ==================== 导航栏 ====================

def render_navbar():
    st.markdown("""
    <div class="navbar">
        <div class="navbar-left">
            <div class="navbar-brand"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="vertical-align:-3px;margin-right:7px;"><rect x="2.5" y="8.5" width="19" height="7" rx="3.5" fill="#0EA5E9"/><circle cx="14.5" cy="12" r="2.4" fill="#0A1020" stroke="#7DD3FC" stroke-width="1.2"/><path d="M5.5 12h4" stroke="#7DD3FC" stroke-width="1.3" stroke-linecap="round" opacity="0.85"/></svg>太空舱<span class="accent">宣传视频</span>生成 Agent</div>
            <div class="navbar-sub">SPACE CAPSULE / VIDEO GENERATION SYSTEM</div>
        </div>
        <div class="navbar-status"><span class="dot"></span>系统在线</div>
    </div>
    """, unsafe_allow_html=True)


# ==================== 控制面板（左列） ====================

def render_controls():
    cfg = get_config()

    st.markdown('<div class="panel-title">生成设置</div>', unsafe_allow_html=True)

    scene = st.radio(
        "生成场景", list(SCENES.keys()), horizontal=True,
        disabled=st.session_state.processing,
    )

    count = st.number_input(
        "本次生成条数", min_value=1, max_value=5,
        value=min(int(cfg.get("daily_count", 5)), 5),
        step=1, disabled=st.session_state.processing,
        help="单条约需 5-10 分钟",
    )

    # 只读展示当前视频配置（模型写死在 backend/video_gen.py，其余改 .env）
    st.caption(f"模型：`{VIDEO_MODEL}`　·　分辨率：`{cfg['video_resolution']}`　·　比例：`{cfg['video_ratio']}`　·　时长：`{cfg['video_duration']}s`　·　参考图策略：`{cfg['use_reference_image']}`")

    st.write("")
    if st.button(
        ":material/rocket_launch: 一键生成", width="stretch", type="primary",
        disabled=st.session_state.processing,
    ):
        _trigger_generation(int(count), scene)

    st.divider()
    st.markdown('<div class="panel-title">参考图管理</div>', unsafe_allow_html=True)
    _render_reference_manager()


def _render_reference_manager():
    cfg = get_config()
    refs_dir = cfg["references_dir"]
    os.makedirs(refs_dir, exist_ok=True)

    images = list_reference_images("all")
    if images:
        st.caption(f"当前 {len(images)} 张参考图（放 `assets/references/`，文件名含 `exterior`/`interior` 自动区分内外饰）：")
        for i in range(0, len(images), 2):
            cols = st.columns(2, gap="small")
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(images):
                    continue
                p = images[idx]
                name = os.path.basename(p)
                with col:
                    with st.container(border=True):
                        st.image(p, width=200)
                        st.markdown(f'<span class="ref-chip">{name}</span>', unsafe_allow_html=True)
                        if st.button(":material/delete: 删除", key=f"del_{name}", width="stretch", help="删除此参考图"):
                            try:
                                os.remove(p)
                                st.rerun()
                            except OSError as e:
                                st.error(str(e))
    else:
        st.caption("尚无参考图，生成将走纯文生图。可在此上传，或直接放入 `assets/references/`。")

    tag = st.radio("参考图类型", ["外饰参考", "内饰参考"], horizontal=True, key="ref_tag",
                   disabled=st.session_state.processing)
    up = st.file_uploader(
        "上传参考图", type=["png", "jpg", "jpeg", "webp"],
        key="ref_uploader", disabled=st.session_state.processing,
        label_visibility="collapsed",
    )
    if up is not None:
        if st.button(":material/save: 保存参考图", disabled=st.session_state.processing):
            prefix = "exterior" if "外饰" in tag else "interior"
            safe = f"{prefix}_{up.name}"
            with open(os.path.join(refs_dir, safe), "wb") as f:
                f.write(up.getbuffer())
            st.success(f"已保存参考图：{safe}")
            st.rerun()


# ==================== 结果面板（右列） ====================

def render_results():
    if st.session_state.processing:
        _render_processing()
    elif st.session_state.gen_results:
        _render_success()
    else:
        _render_empty()


def _render_empty():
    st.markdown("""
    <div style="text-align:center;padding:3rem 0;min-height:420px;display:flex;flex-direction:column;justify-content:center;">
        <div class="empty-icon"><svg width="52" height="52" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="filter: drop-shadow(0 0 12px rgba(56,189,248,0.45));"><rect x="2.5" y="8.5" width="19" height="7" rx="3.5" fill="#0EA5E9"/><circle cx="14.5" cy="12" r="2.4" fill="#0A1020" stroke="#7DD3FC" stroke-width="1.2"/><path d="M5.5 12h4" stroke="#7DD3FC" stroke-width="1.3" stroke-linecap="round" opacity="0.85"/></svg></div>
        <div class="empty-title">生成的宣传视频将在这里呈现</div>
        <div class="empty-desc">在左侧选择场景与条数，点击「一键生成」<br>生成所选场景（雪地 / 深林 / 草地）的内外饰一镜到底视频</div>
    </div>
    """, unsafe_allow_html=True)


def _render_processing():
    st.markdown("""
    <div style="text-align:center;padding:2.5rem 0;min-height:420px;display:flex;flex-direction:column;justify-content:center;">
        <div class="loading-spinner"></div>
        <div class="loading-text">AI 正在生成宣传视频……</div>
        <div class="loading-timer">单条约需 5-10 分钟，请耐心等待</div>
    </div>
    """, unsafe_allow_html=True)


def _render_success():
    results = st.session_state.gen_results
    st.markdown(
        f'<div class="panel-title">本次生成 · {len(results)} 条</div>',
        unsafe_allow_html=True,
    )

    for i in range(0, len(results), 2):
        cols = st.columns(2, gap="medium")
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(results):
                with col:
                    _render_result_card(idx, results[idx])


def _render_result_card(i: int, r: dict):
    with st.container(border=True):
        st.markdown(
            f'<div class="result-meta"><b>第 {i + 1} 条</b> · {r.get("scene", "-")} · {r.get("view_label", "-")}</div>',
            unsafe_allow_html=True,
        )

        if r.get("status") == "done":
            video_path = r.get("video_path", "")
            if video_path and os.path.exists(video_path):
                with open(video_path, "rb") as f:
                    video_bytes = f.read()
                st.video(video_bytes)
                st.download_button(
                    ":material/download: 下载视频", data=video_bytes,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4",
                    key=f"dl_{i}",
                    width="stretch",
                )
        else:
            st.error(r.get("error", "未知错误"))


# ==================== 历史归档 ====================

def render_history():
    records = load_records(limit=10)
    if not records:
        return

    video_paths = [
        rec["video_path"] for rec in records
        if rec.get("video_path") and os.path.exists(rec["video_path"])
    ]
    if not video_paths:
        return

    st.divider()
    st.markdown('<div class="panel-title">历史生成记录</div>', unsafe_allow_html=True)

    for i in range(0, len(video_paths), 2):
        cols = st.columns(2, gap="medium")
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(video_paths):
                continue
            with col:
                with st.container(border=True):
                    with open(video_paths[idx], "rb") as f:
                        video_bytes = f.read()
                    st.video(video_bytes)
                    st.download_button(
                        ":material/download: 下载", data=video_bytes,
                        file_name=os.path.basename(video_paths[idx]),
                        mime="video/mp4",
                        key=f"hist_dl_{idx}",
                        width="stretch",
                    )


# ==================== 核心逻辑 ====================

def _trigger_generation(count: int, scene: str):
    """构建任务队列 → rerun 显示加载界面 → 逐条执行。"""
    if st.session_state.processing:
        return

    tasks = compose_tasks(count, scene=scene)
    st.session_state.gen_queue = tasks
    st.session_state.gen_results = []
    st.session_state.total_count = count
    st.session_state.processing = True
    st.session_state.current_task = tasks[0] if tasks else None
    st.rerun()


def _execute_next():
    """执行队列中的下一条任务（阻塞），完成后 rerun。"""
    queue = st.session_state.gen_queue
    if not queue:
        st.session_state.processing = False
        st.session_state.current_task = None
        return

    task = queue[0]
    t0 = time.time()
    result = run_one_video(task)
    logger.info(f"单条耗时: {time.time() - t0:.1f}s")

    st.session_state.gen_results.append(result)
    remaining = queue[1:]
    st.session_state.gen_queue = remaining
    st.session_state.current_task = remaining[0] if remaining else None
    if not remaining:
        st.session_state.processing = False
    st.rerun()


# ==================== Footer ====================

def render_footer():
    st.divider()
    st.markdown("""
    <div class="site-footer">
        太空舱宣传视频生成 Agent —— 面向电商宣传的 AI 视频自动化工具
    </div>
    """, unsafe_allow_html=True)


# ==================== 主入口 ====================

def main():
    init_session()
    render_navbar()

    left, right = st.columns([5, 7], gap="medium")
    with left:
        with st.container(border=True):
            render_controls()
    with right:
        with st.container(border=True):
            render_results()

    render_history()
    render_footer()

    # 渲染完成后，执行待处理任务
    if st.session_state.processing and st.session_state.gen_queue:
        _execute_next()


if __name__ == "__main__":
    main()
