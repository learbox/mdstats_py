"""无边框弹窗基类 — ConfigDialog 和 RankStatsDialog 的共享代码。

提取以下公共逻辑：
    - 背景图加载与 paintEvent
    - DWM 窗口圆角
    - 鼠标拖拽移动
"""

from __future__ import annotations

import ctypes

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QDialog


class _BaseFramelessDialog(QDialog):
    """无边框 + 可拖拽 + 背景图支持的弹窗基类。

    子类需在 __init__ 中：
        1. 调用 self._init_background(bg_path)  加载背景图
        2. 调用 self._init_drag()               初始化拖拽状态
        3. 设置 self.setWindowFlags(FramelessWindowHint | Window | Dialog)
        4. 设置 self.setAttribute(WA_StyledBackground, True)
        5. 调用 self._apply_dwm_round_corners() 启用 Win11 圆角
    """

    # 类型注解声明（实值在 _init_background / _init_drag 中赋值）
    _bg_pixmap: QPixmap | None
    _dragging: bool
    _drag_start: QPoint

    def _init_background(self, bg_path: str | None) -> None:
        """加载主题背景图，如果路径无效或文件不存在则 _bg_pixmap 为 None。"""
        self._bg_pixmap: QPixmap | None = None
        if bg_path:
            pm = QPixmap(bg_path)
            if not pm.isNull():
                self._bg_pixmap = pm

    def _init_drag(self) -> None:
        """初始化鼠标拖拽状态。"""
        self._dragging = False
        self._drag_start = QPoint()

    # =========================================================================
    # 背景绘制
    # =========================================================================

    def paintEvent(self, event) -> None:
        """有背景图则贴图填充，无图走 QSS 纯色背景。"""
        painter = QPainter(self)
        bg = self._bg_pixmap
        if bg is not None:
            scaled = bg.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        painter.end()
        super().paintEvent(event)

    # =========================================================================
    # DWM 圆角（Windows 11）
    # =========================================================================

    def _apply_dwm_round_corners(self) -> None:
        """给无边框窗口加上 Win11 原生圆角（DWM API）。"""
        try:
            hwnd = int(self.winId())
            dwmwa = 33                         # DWMWA_WINDOW_CORNER_PREFERENCE
            dwmwcp_round = 2                   # 圆角模式
            ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
                hwnd, dwmwa,
                ctypes.byref(ctypes.c_int(dwmwcp_round)),
                ctypes.sizeof(ctypes.c_int),
            )
        except (OSError, AttributeError):
            pass

    # =========================================================================
    # 拖拽
    # =========================================================================

    def mousePressEvent(self, event) -> None:
        """左键按下时记录窗口内相对位置，进入拖拽模式。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """拖拽时保持鼠标与窗口的相对位置不变。"""
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_start)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """释放鼠标退出拖拽模式。"""
        self._dragging = False
        super().mouseReleaseEvent(event)
