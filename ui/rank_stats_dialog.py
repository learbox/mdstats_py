"""详细统计信息弹窗 — 按卡组 + 对方段位筛选，展示 17 项统计指标。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from src.recorder import compute_filtered_stats, load_records, STATS_COLUMNS

# 段位大段列表（含"全部"）
RANK_TIERS = ["全部", "新手", "青铜", "白银", "黄金", "铂金", "钻石", "大师", "巅峰"]


class RankStatsDialog(QDialog):
    """详细统计信息弹窗。"""

    def __init__(self, parent, config: dict, theme_colors: dict,
                 bg_path: str = "", widget_bg: str = "#ffffff",
                 main_bg: str = "#f0f0f0"):
        super().__init__(parent)
        self._config = config
        self._colors = theme_colors
        self._bg_path = bg_path
        self._widget_bg = widget_bg
        self._main_bg = main_bg

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Dialog)
        self.setMinimumSize(460, 520)
        self.resize(500, 560)

        # ---- 背景 ----
        content = QWidget()
        content.setObjectName("contentWidget")
        self.setStyleSheet(f"#contentWidget {{ background-color: {main_bg}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ---- 标题栏 ----
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("详细统计信息"))
        title_row.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        title_row.addWidget(close_btn)
        layout.addLayout(title_row)

        # ---- 筛选栏 ----
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("卡组:"))
        self._deck_combo = QComboBox()
        self._deck_combo.setMinimumWidth(120)
        filter_row.addWidget(self._deck_combo)

        filter_row.addWidget(QLabel("对方段位:"))
        self._rank_combo = QComboBox()
        self._rank_combo.addItems(RANK_TIERS)
        self._rank_combo.setMinimumWidth(80)
        filter_row.addWidget(self._rank_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ---- 统计标签网格 (2 列) ----
        self._stat_labels: dict[str, QLabel] = {}
        grid = QGridLayout()
        grid.setSpacing(4)
        items = [
            ("对局数", "胜",),
            ("负", "胜率"),
            ("赢硬币次数", "输硬币次数"),
            ("赢硬币概率", "赢硬币胜率"),
            ("输硬币胜率", "先攻次数"),
            ("后攻次数", "先攻胜"),
            ("后攻胜", "先攻胜率"),
            ("后攻胜率", "升段次数"),
            ("降段次数", "升段胜率"),
            ("降段胜率", ""),
        ]
        for row, (k1, k2) in enumerate(items):
            for col, key in enumerate([k1, k2]):
                if not key:
                    continue
                lbl_key = QLabel(f"{key}:")
                lbl_key.setStyleSheet("color: #888; font-size: 12px;")
                lbl_val = QLabel("—")
                lbl_val.setStyleSheet("font-weight: bold; font-size: 14px;")
                self._stat_labels[key] = lbl_val
                pair = QHBoxLayout()
                pair.setSpacing(4)
                pair.addWidget(lbl_key)
                pair.addWidget(lbl_val)
                pair.addStretch()
                grid.addLayout(pair, row, col)
        layout.addLayout(grid)

        layout.addStretch()

        # ---- 联动刷新 ----
        self._deck_combo.currentTextChanged.connect(self._refresh)
        self._rank_combo.currentTextChanged.connect(self._refresh)

        # ---- 初始填充 ----
        self._populate_decks()
        self._refresh()

    def _populate_decks(self) -> None:
        """从 CSV 加载卡组列表到下拉框。"""
        records = load_records()
        decks = sorted({r.get("使用卡组", "(未指定)") or "(未指定)"
                        for r in records})
        self._deck_combo.addItem("全部")
        for d in decks:
            self._deck_combo.addItem(d)
        # 默认选最近对局的卡组
        if records:
            last_deck = records[-1].get("使用卡组", "") or "全部"
            idx = self._deck_combo.findText(last_deck)
            if idx >= 0:
                self._deck_combo.setCurrentIndex(idx)

    def _refresh(self) -> None:
        """根据筛选条件刷新统计显示。"""
        deck = self._deck_combo.currentText()
        if deck == "全部":
            deck = ""
        rank = self._rank_combo.currentText()
        if rank == "全部":
            rank = ""

        records = load_records()
        stats = compute_filtered_stats(records, deck, rank)

        for key in self._stat_labels:
            val = stats.get(key, "—")
            self._stat_labels[key].setText(str(val))
