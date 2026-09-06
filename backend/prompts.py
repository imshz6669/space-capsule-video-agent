"""
提示词模板库 —— 太空舱电商宣传视频 · 一镜到底看房 walkthrough (v3)

2026-09-05 按用户重写的四段式结构整体替换（v3）：
    ① 开场定位 + 参考图锚定（相机人设：1.6m 视高 / 云台 / 自然头部微动 / 24-28mm）
    ② 动线时间轴（节拍随时长等比缩放，10s 档）
    ③ 陈列规则（showroom 级）
    ④ 连续性 + 相机 + 光线 + 负面词簇

面向电商详情页的 10 秒短视频：第一人称连贯走完
外饰 → 客厅 → 主卧 → 卫生间 → 回主卧 → 落地窗看景，全片一条动线，
不回头不跳切。节拍按 VIDEO_DURATION 等比缩放（默认 10s）：

    0-1.5s   外景定帧（全片唯一一次外饰）
    1.5-2.5s 穿过敞开的舱门
    2.5-4s   客厅
    4-5.5s   主卧
    5.5-7s   卫生间
    7-8.5s   回主卧（全片最后一个动作）
    8.5-10s  落地窗推镜定帧收尾

核心经验（实测得出，v3 已全部内嵌到文本中）：
    1. r2v 模型对参考图传入顺序的服从度高于提示词文字 —— 参考图顺序必须
       与参观顺序一致，且末尾重复主卧参考图以锚定「回主卧落地窗收尾」
       （见 agent.collect_references）。
    2. 场景约束需在各段反复出现（{scene_en} 在 v3 中出现 5 次），否则结尾
       窗外会被模型"换季"。
    3. 房间切换必须点名禁止叠化/瞬移，并要求从真实门洞穿过。
    4. 外饰参考图舱门是关闭的，必须写明「门已打开、暖光外溢」。
    5. 「动线无杂物」必须显式写，否则路径中央会被摆装饰物。
    6. 外景只允许在开头出现一次。
    7. 转场写成空间特征（「客厅尽头的拱门」）+「边走边转场」最出连续转场
       （对照 230654 实测：过渡最顺）。
    8. 外景写「主舱主体、其余舱体散布背景」（对照 232049 实测：布局最合适）。
    9. 结尾必须显式锚定「回到主卧落地窗——never in the bathroom, never
       back outside」（对照 wan3.0 首批实测反馈）。
"""

# ==================== 场景库 ====================
SCENES = {
    "雪地": "白雪覆盖的旷野，地面铺满厚厚积雪，远处是连绵雪山，清冷通透的冬季氛围",
    "深林": "茂密幽深的原始森林，高大松树环绕，清晨薄雾缭绕，神秘静谧的氛围",
    "草地": "开阔青翠的草地，蓝天白云，远处起伏的绿色山丘，阳光明媚的氛围",
}

# 场景 → 英文（walkthrough 提示词用；以 {scene_en} 注入下列四段）
SCENE_EN = {
    "雪地": "snowy forest",
    "深林": "deep dark forest",
    "草地": "sunny grassland",
}

# ==================== 一镜到底动线 ====================
# 动线节拍（占全片时长的比例）。10s 档实测编排：外景定帧 1.5s 是电商开头
# 立住产品的最短呼吸感，进门 1s 是纯过场不占戏，其余每站 1.5s 够"看一眼"。
_ROUTE_BEATS = (0.15, 0.25, 0.40, 0.55, 0.70, 0.85)

_INTRO = (
    "A {duration}-second photorealistic e-commerce product commercial, {ratio}. "
    "One continuous first-person POV walkthrough of a futuristic space capsule "
    "house in a {scene_en} landscape, filmed as a single uninterrupted take with "
    "no cuts. The camera simulates a real person touring the home: eye height "
    "about 1.6 m, smooth gimbal movement, subtle natural head-bob, brisk but "
    "steady walking pace. No hands, no body, no camera rig visible. Reference "
    "images: [Image 1] is the capsule's real exterior photo — the exterior shell "
    "shape, roof line, window positions, door design, materials and ground "
    "context must match exactly. The remaining reference images show the real "
    "interior rooms in the exact order the camera visits them: living room, "
    "master bedroom, bathroom, then back to master bedroom. Match their layout, "
    "furniture, wall panels, lighting temperature and decor exactly."
)

_ROUTE = (
    " 0–{t1}s EXTERIOR ONLY: The video opens on a fleet of identical white "
    "capsules naturally distributed across the {scene_en} — one capsule front "
    "and center in the foreground as the main subject, the others standing "
    "behind and beside it as a subtle background, never approached by the "
    "camera. The main capsule's front door is already open with warm 3500K "
    "light spilling out. Slow push-in or slight lateral dolly toward that "
    "door; do not enter yet. "
    "{t1}–{t2}s ENTRY: Walk straight through the open front door of the main "
    "capsule without stopping — physically cross the real threshold in one "
    "continuous move, the doorframe sliding past the edges of the lens into "
    "the interior; no cut, no dissolve, no morphing. "
    "{t2}–{t3}s LIVING ROOM: Inside, glance from the seating area on one side "
    "toward the arched opening at the far end that leads to the master bedroom. "
    "Show clean built-in furniture along walls, clear floor path, warm ambient "
    "lighting mixed with cold daylight. "
    "{t3}–{t4}s MASTER BEDROOM: Walk through the arch into the master bedroom. "
    "Pan slightly toward the floor-to-ceiling window, revealing the bed and the "
    "{scene_en} view outside. "
    "{t4}–{t5}s BATHROOM: Turn into the bathroom. Quick pan across vanity, "
    "mirror and shower area; keep moving, do not dwell. "
    "{t5}–{t6}s RETURN TO MASTER BEDROOM: Exit the bathroom and walk back into "
    "the master bedroom. Turn toward the floor-to-ceiling window; this return "
    "is the final move of the video. "
    "{t6}–{duration}s FINAL PUSH & FREEZE: Push toward the floor-to-ceiling "
    "window and freeze on a clean wide composition of the master bedroom with "
    "the {scene_en} exterior visible. Always end inside the master bedroom — "
    "never in the bathroom, never back outside."
)

_STAGING = (
    " Showroom-level cleanliness. All furniture placed against walls; all "
    "walking paths completely clear. No personal items, no clutter, no cables, "
    "no towels on racks, no toiletries on countertops, no wrinkles on bedding. "
    "Surfaces clean and dust-free; mirrors and glass streak-free. Use minimal, "
    "modern decor that makes the space feel larger and highlights the capsule's "
    "product features."
)

_RULES = (
    " Continuity: strict single continuous shot, no hidden cuts. Doorway and "
    "archway crossings must be physically continuous; no teleporting, no "
    "dissolve, no speed ramp, no morphing. Exterior appears only once at the "
    "beginning; all scenes share the same interior environment and consistent "
    "spatial layout. "
    "Camera: gimbal-stabilized first-person walk, natural walking momentum, no "
    "sudden acceleration or rotation blur. Equivalent focal length around "
    "24–28mm, low distortion, no fisheye, no visible camera shadow. "
    "Lighting: cold {scene_en} daylight from outside, around 6000K, mixing "
    "with warm 3500K interior LED strips/lamps. Balanced window exposure so the "
    "bright exterior view is not blown out and interior details stay visible; "
    "soft shadows, clean highlights. "
    "Negative prompt / avoid: no people, no hands, no body parts, no text, no "
    "subtitles, no watermark, no logo, no cuts, no transitions, no dissolve, "
    "no zoom cuts, no morphing, no warping, no speed ramps, no camera shake, "
    "no motion blur, no lens flare, no fisheye, no CGI uncanny look. Every "
    "second must show product features; output photorealistic e-commerce "
    "footage."
)


def _video_duration() -> int:
    """读取 VIDEO_DURATION 配置，失败时回退 10。"""
    try:
        from utils.config import get_video_cfg

        return int(get_video_cfg()["duration"] or 10)
    except Exception:
        return 10


def _video_ratio() -> str:
    """读取 VIDEO_RATIO 配置，失败时回退 16:9。"""
    try:
        from utils.config import get_video_cfg

        return get_video_cfg()["ratio"] or "16:9"
    except Exception:
        return "16:9"


def _fmt(t: float) -> str:
    """1.0 → '1'，1.5 → '1.5'：节拍时间戳显示更干净。"""
    return f"{t:g}"


def build_video_prompt(scene: str) -> str:
    """构建视频提示词：动线固定为 客厅→主卧→卫生间→回主卧→落地窗，节拍随时长等比缩放。"""
    scene_en = SCENE_EN.get(scene, "snowy forest")
    duration = _video_duration()
    ratio = _video_ratio()
    t1, t2, t3, t4, t5, t6 = (round(duration * b, 1) for b in _ROUTE_BEATS)
    return (
        _INTRO.format(duration=duration, ratio=ratio, scene_en=scene_en)
        + _ROUTE.format(
            scene_en=scene_en, duration=duration,
            t1=_fmt(t1), t2=_fmt(t2), t3=_fmt(t3),
            t4=_fmt(t4), t5=_fmt(t5), t6=_fmt(t6),
        )
        + _STAGING
        + _RULES.format(scene_en=scene_en)
    )
