"""macOS 窗口定位与截图 — 基于 Quartz (CoreGraphics) / AppKit + mss。

================================================================================
技术栈

Quartz  (pyobjc-framework-Quartz) — macOS CoreGraphics 窗口管理
AppKit  (pyobjc-framework-AppKit) — macOS 原生窗口信息（Retina 缩放）

mss — 高性能截图（macOS 底层走 CoreGraphics，GPU 加速）

================================================================================
坐标系

macOS CoreGraphics 原点在屏幕左下角，mss 原点在左上角。
需要翻转 Y 轴：mss_top = screen_height - mac_y - height

================================================================================
Retina 屏

CGWindowBounds 返回的是逻辑像素（points），在 Retina 屏上需要乘以
backingScaleFactor（2x 或 3x）才能得到物理像素给 mss。

================================================================================
全屏游戏

macOS 全屏游戏会进入独立 Space。CGWindowListCopyWindowInfo 可能找不到。
建议使用无边框窗口模式而非全屏模式。如果必须全屏，可尝试 CGDisplayStream API。

================================================================================
权限要求

需要用户在「系统设置 → 隐私与安全性 → 屏幕录制」中授权。
"""

import numpy as np
import mss
import Quartz
from AppKit import NSScreen


# =============================================================================
# 内部：窗口查找
# =============================================================================

def _find_window_info(title_substring: str) -> dict | None:
    """遍历所有可见窗口，按标题关键词模糊匹配，返回首个命中窗口信息字典。

    CGWindowListCopyWindowInfo 返回的每个窗口字典包含：
        kCGWindowName        — 窗口标题
        kCGWindowOwnerName   — 所属程序名（如 "Yu-Gi-Oh! Master Duel"）
        kCGWindowBounds      — 窗口在屏幕上的位置和尺寸（CGRect -> dict）
        kCGWindowLayer       — 窗口层级（0=普通窗口）
        kCGWindowAlpha       — 窗口不透明度

    注意：macOS 没有 Windows 的"最小化窗口"概念。窗口被隐藏到 Dock
    时不再出现在 CGWindowListCopyWindowInfo 的普通窗口列表中。
    """
    # kCGWindowListOptionOnScreenOnly = 只列出当前屏幕上的窗口
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )

    for window in window_list:
        # 跳过系统窗口（Dock、菜单栏等）
        layer = window.get(Quartz.kCGWindowLayer, 0)
        if layer != 0:
            continue

        # 窗口标题匹配（大小写不敏感）
        name = window.get(Quartz.kCGWindowName, "") or ""
        if title_substring.lower() in name.lower():
            return window

    # 如果标题匹配失败，尝试按程序名匹配
    for window in window_list:
        layer = window.get(Quartz.kCGWindowLayer, 0)
        if layer != 0:
            continue
        owner = window.get(Quartz.kCGWindowOwnerName, "") or ""
        if title_substring.lower() in owner.lower():
            return window

    return None


def _get_screen_region(window_info: dict) -> list[int]:
    """把 CGWindowBounds 转成 mss 兼容的 [left, top, width, height] 区域。

    处理三个关键问题：
        1. Y 轴翻转：macOS 原点在左下，mss 原点在左上
        2. 多显示器：找到窗口所在显示器，用该显示器的高度翻转
        3. Retina：CGWindowBounds 是逻辑像素 (points)，mss 需要物理像素

    返回:
        [left, top, width, height] — mss 兼容的截图区域（物理像素）
    """
    bounds = window_info.get(Quartz.kCGWindowBounds, {})
    x = bounds.get("X", 0)
    y = bounds.get("Y", 0)           # macOS 坐标：左下角到屏幕底部
    w = bounds.get("Width", 0)
    h = bounds.get("Height", 0)

    # ---- 找到窗口所在的 NSScreen（处理多显示器） ----
    # 用窗口中心点匹配屏幕
    window_cx = x + w / 2
    window_cy = y + h / 2
    target_screen = None
    for screen in NSScreen.screens():
        frame = screen.frame()       # CGRect 在下角原点
        visible = screen.visibleFrame()
        sx, sy = frame.origin.x, frame.origin.y
        sw, sh = frame.size.width, frame.size.height
        if sx <= window_cx <= sx + sw and sy <= window_cy <= sy + sh:
            target_screen = screen
            break
    if target_screen is None:
        target_screen = NSScreen.mainScreen()  # 兜底：主屏

    screen_h = target_screen.frame().size.height
    scale = target_screen.backingScaleFactor()  # Retina 缩放：1x/2x/3x

    # ---- Y 轴翻转 ----
    # mac_y 是窗口左下角到屏幕底边距离
    # mss_top = 屏幕顶部到窗口顶部的距离
    mss_top = screen_h - y - h

    # ---- points → 物理像素 ----
    return [int(x * scale), int(mss_top * scale),
            int(w * scale), int(h * scale)]


# =============================================================================
# 公开 API
# =============================================================================

def get_window_status(title_substring: str = "masterduel"):
    """一次查询窗口是否存在、客户区尺寸、是否最小化。

    macOS 没有"最小化"概念（最小化 = 隐藏到 Dock，不在窗口列表中）。
    所以 is_minimized 始终返回 False（找不到窗口时也可能被视为隐藏）。

    返回:
        (None, None, False) — 未找到窗口
        (window_info, (width, height), False) — 找到窗口
    """
    info = _find_window_info(title_substring)
    if info is None:
        return None, None, False
    bounds = info.get(Quartz.kCGWindowBounds, {})
    w = int(bounds.get("Width", 0))
    h = int(bounds.get("Height", 0))
    return info, (w, h), False


def is_window_open(title_substring: str = "masterduel") -> bool:
    """检测指定标题的窗口是否当前可见。"""

    return _find_window_info(title_substring) is not None


def get_client_size(title_substring: str = "masterduel"):
    """获取窗口渲染区域尺寸。macOS 上窗口边界即渲染区域。"""

    info = _find_window_info(title_substring)
    if info is None:
        return None
    bounds = info.get(Quartz.kCGWindowBounds, {})
    return int(bounds.get("Width", 0)), int(bounds.get("Height", 0))


def is_window_minimized(title_substring: str = "masterduel") -> bool:
    """判断窗口是否被最小化。

    macOS 上最小化窗口不在窗口列表中，所以这儿返回 not is_window_open。
    如果需要更精确的判断（窗口存在但隐藏 vs 完全没开），
    需要用 NSWorkspace.runningApplications 检查进程状态。
    """
    # 简化处理：找不到窗口就当"最小化或不存在"
    return not is_window_open(title_substring)


def capture_window(title_substring: str = "masterduel") -> np.ndarray:
    """截取指定窗口。

    抛出 RuntimeError 如果窗口未找到。
    """
    info = _find_window_info(title_substring)
    if info is None:
        raise RuntimeError(f"未找到标题包含 '{title_substring}' 的窗口")
    region = _get_screen_region(info)
    return capture_screen(region=region)


def capture_screen(monitor_index: int = 0,
                   region: list[int] | None = None) -> np.ndarray:
    """截取指定显示器或区域的屏幕画面。mss 跨平台，代码同 Windows。"""
    with mss.MSS() as sct:
        monitors: list[dict] = sct.monitors
        if monitor_index >= len(monitors):
            monitor_index = 0

        if region and len(region) == 4:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = monitors[monitor_index]

        img = sct.grab(monitor)
        arr: np.ndarray = np.array(img)[:, :, :3]
        return arr
