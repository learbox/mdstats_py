# 第一轮重构总结

## 概要

将 `ui/` 中的业务逻辑拆分到 `src/`，消除 `MainWindow` 与 `ThemeManager` 之间的代码重复。
净减 **99 行**，`main_window.py` 从 ~2077 行降至 ~1978 行。

## 变更统计

```
src/app_state.py               |  57 +++++++++++ (新建)
{ui => src}/hotkey_listener.py |  29 +++++++ (移动 + 迁入 parse_hotkey)
ui/main_window.py              | 227 +++----- (大幅精简)
```

## 具体改动

### 1A. 移动 `hotkey_listener.py` + 迁入 `parse_hotkey`

- `ui/hotkey_listener.py` → `src/hotkey_listener.py`（纯移动，内容不变）
- 将 `MainWindow._parse_hotkey()` 移入 `src/hotkey_listener.py`，改为模块级函数 `parse_hotkey()`
- `main_window.py` 导入改为 `from src.hotkey_listener import HotkeyListener, parse_hotkey`

**理由**：`HotkeyListener` 是纯 Windows API + Qt 信号的封装，无任何 UI 控件，与 `src/stats_worker.py`（QThread 子类）性质一致。`parse_hotkey` 是纯字符串解析函数，与 `HotkeyListener` 天然同属热键领域。

### 1B. 删除 MainWindow 与 ThemeManager 重复的颜色工具方法

删除 `MainWindow` 中 5 个与 `ThemeManager` 完全重复的方法：

| 删除的方法 | ThemeManager 对应方法 |
|-----------|---------------------|
| `_parse_hex()` | `_parse_hex()` |
| `_lighter()` | `lighter_color()` |
| `_darker()` | `darker_color()` |
| `_readable_on()` | `readable_text_color()` |
| `_btn_style()` | `make_button_style()` |

5 处调用替换：`self._btn_style(bg, padding=...)` → `self._tm.make_button_style(bg, padding=...)`

**理由**：两套实现完全等价，参数签名一致，属于典型的复制粘贴重复。统一后颜色计算逻辑只存在于 `ThemeManager` 中。

### 1C. 提取 app_state 持久化到 `src/app_state.py`

从 `MainWindow` 移出以下代码到新文件 `src/app_state.py`：

- 常量 `APP_STATE_DEFAULTS`（列宽/分割条/窗口位置默认值）
- 函数 `read_app_state()` — 读取 `.app_state.json`，缺字段自动补齐
- 函数 `write_app_state(data)` — 写入 `.app_state.json`
- 函数 `parse_pos(raw, min_val)` — 验证坐标有效性

`main_window.py` 中约 12 处调用替换：`self._read_app_state()` → `read_app_state()` 等。

**理由**：这些是纯粹的 JSON 文件读写，不涉及任何 UI 控件。提取后其他模块（如悬浮窗）可以独立使用，不需要通过 MainWindow 实例。

## 未改动的文件

| 文件 | 结论 |
|------|------|
| `config_dialog.py` | 暂不拆分（_write_toml 与弹窗紧密绑定） |
| `about_dialog.py` | 暂不拆分（更新检查仅 40 行） |
| `floating_window.py` | 无需调整 |
| `theme_manager.py` | 无需调整 |
| `titlebar.py` | 无需调整 |

## 后续计划

| 轮次 | 内容 | 预计减行 |
|------|------|---------|
| 第二轮 | 提取热键/截图管理为 `src/snapshot_controller.py` | ~110 行 |
| 第三轮（可选） | 提取状态机到 `src/match_state.py` | ~50-60 行 |
