# 第三轮重构总结

## 概要

将 MainWindow 中的三阶段对局状态机提取为纯数据类 `MatchState`，
状态转换逻辑集中管理，MainWindow 只负责 UI 联动和 CSV 写入等副作用。
`main_window.py` 从 ~1873 行降至 **1772 行**，三轮累计从 2077 行降至 1772 行（-14.6%）。

## 变更统计

```
src/match_state.py   | 111 +++++++++++++ (新建)
ui/main_window.py    |  70 +-----       (精简)
```

## 新增文件：`src/match_state.py`

`MatchState` 封装了"硬币 → 先后攻 → 胜负"的三阶段状态机：

| 方法 | 职责 |
|------|------|
| `advance_coin(coin_win)` | 自动识别硬币 → 推进到阶段1，返回是否成功 |
| `advance_turn(turn)` | 自动识别先后攻 → 推进到阶段2，返回是否成功 |
| `set_rank(rank)` | 缓存段位升降（不推进阶段） |
| `manual_step(side)` | 手动按钮点击 → 根据阶段解释语义并推进 |
| `undo()` | 撤销上一阶段，返回回退后的阶段号 |
| `reset()` | 重置到初始状态 |
| `snapshot()` | 返回当前缓存快照（reset 前保存通知所需信息） |

设计要点：
- **纯数据，无 UI 依赖** — 不引用任何 Qt 控件或信号
- **返回值驱动** — `advance_coin`/`advance_turn` 返回 bool 表示是否推进成功，调用方据此决定 UI 更新
- `manual_step` 返回 `(new_stage, turn_value)` — 阶段2不自动写入 CSV，由 MainWindow 负责

## MainWindow 变更

**实例变量精简**（4个 → 1个）：
```python
# 旧
self._stage: int = 0
self._coin_cache: str = ""
self._turn_cache: str = ""
self._rank_cache: str = ""

# 新
self._match = MatchState()
```

**方法改写**：

| 方法 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| `_on_coin_win_detected` | 手动检查 stage + 赋值缓存 + 推进 | `self._match.advance_coin(coin_win)` |
| `_on_rank_detected` | 直接赋值 rank_cache | `self._match.set_rank(rank)` |
| `_on_turn_detected` | 手动检查 stage + 赋值缓存 + 推进 | `self._match.advance_turn(turn)` |
| `_on_result_detected` | reset 前逐个复制缓存 | `self._match.snapshot()` 一次性获取 |
| `_manual_step_clicked` | 阶段0/1手动赋值缓存+推进 | `self._match.manual_step(side)` |
| `_on_undo` | if-elif 手动清缓存+回退 | `self._match.undo()` |
| `_reset_stage` | 4行逐个清空 | `self._match.reset()` |

**属性引用替换**（37处）：
- `self._stage` → `self._match.stage`
- `self._coin_cache` → `self._match.coin_cache`
- `self._turn_cache` → `self._match.turn_cache`
- `self._rank_cache` → `self._match.rank_cache`

## 三轮重构总效果

| 指标 | 重构前 | 第一轮后 | 第二轮后 | 第三轮后 |
|------|--------|---------|---------|---------|
| main_window.py 行数 | 2077 | ~1978 | ~1873 | **1772** |
| 累计减少 | — | -99 | -204 | **-305** |
| src/ 新增模块 | — | 2 | 3 | **4** |

新增的 `src/` 模块：

| 文件 | 职责 | 行数 |
|------|------|------|
| `hotkey_listener.py` | 全局热键监听（独立线程） | ~135 |
| `app_state.py` | 应用状态持久化（JSON 读写） | ~65 |
| `snapshot_controller.py` | 截图控制器（热键+截图+周期） | ~145 |
| `match_state.py` | 对局状态机（纯数据） | ~111 |
