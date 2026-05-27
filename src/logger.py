"""日志模块 — 线程安全地将状态消息写入日志文件，支持按作用域过滤。

================================================================================
为什么需要独立的日志模块？
================================================================================

程序在运行时会输出大量状态信息（"已识别硬币"、"截图已保存"等），
这些信息原本只显示在左下角状态栏中，一旦关闭程序就丢失了。日志模块让
用户可以选择性地把这些信息持久化到文件中，方便事后排查问题。

================================================================================
线程安全
================================================================================

日志写入可能同时被多个线程调用：
    - 主线程：_on_status() → 记录状态栏消息
    - 工作线程：_save_detection_screenshot() → 记录截图事件
    - 异常钩子：sys.excepthook → 记录未捕获的异常

用 threading.Lock() 保证同一时刻只有一个线程在写文件，避免内容交错。

================================================================================
作用域过滤
================================================================================

日志内容分为三类（作用域），用户可在设置中勾选要记录哪些：
    - "status"      → 标签 [STATUS]，记录所有状态栏消息
    - "screenshots" → 标签 [SCRN]，记录截图的保存/清除操作
    - "errors"      → 标签 [ERROR]，记录未捕获的异常

通过 set_scopes() 控制，write() 内部检查标签对应的作用域是否启用。
如果未启用，静默跳过（不写文件）。

================================================================================
使用示例
================================================================================

    # 初始化（只需要调用一次，多次调用只生效第一次）
    _log.init_log(Path("logs"))
    _log.set_scopes({"status", "errors"})

    # 写入日志（线程安全，未初始化或不在作用域内时静默跳过）
    _log.write("STATUS", "正在运行 — 等待识别硬币…")
    _log.write("ERROR", "工作线程异常: ...")
    _log.write("SCRN", "已保存: coin_win_1920x1080.png")
"""

import threading
from datetime import datetime
from pathlib import Path

# 日志文件的路径（None = 未初始化，此时所有 write() 调用静默跳过）
_log_path: Path | None = None

# 线程锁 — 保证多线程同时写日志时内容不交错
_lock = threading.Lock()

# 日志标签 → 作用域的映射
# 例如 write("STATUS", ...) 会检查 "status" 是否在 _scopes 中
_TAG_SCOPE = {"STATUS": "status", "SCRN": "screenshots", "ERROR": "errors"}

# 当前启用的作用域集合（默认全开，后续由 set_scopes() 修改）
_scopes: set[str] = {"status", "screenshots", "errors"}


def init_log(directory: Path) -> None:
    """初始化日志文件。

    在指定的目录下创建 mdstats_YYYYMMDD.log 文件。
    多次调用只生效第一次 — 日志路径设置后就不会再变，保证一个
    会话的所有日志写入同一个文件。

    Args:
        directory: 日志文件所在的目录（通常是项目根下的 logs/）。
    """
    global _log_path
    if _log_path is not None:
        return  # 已初始化，不重复创建
    directory.mkdir(parents=True, exist_ok=True)
    _log_path = directory / f"mdstats_{datetime.now().strftime('%Y%m%d')}.log"


def set_scopes(scopes: set[str]) -> None:
    """设置日志记录范围。

    scopes 中的值必须来自 {"status", "screenshots", "errors"}。
    不在该集合中的作用域会被 write() 静默跳过。

    每次配置重载时可以调用这个函数来更新作用域，无需重新初始化日志文件。

    Args:
        scopes: 要启用的作用域集合。
    """
    global _scopes
    _scopes = scopes


def enabled() -> bool:
    """检查日志是否已初始化（即 init_log 是否被调用过）。

    Returns:
        True 表示日志可用，False 表示尚未初始化。
    """
    return _log_path is not None


def write(tag: str, msg: str) -> None:
    """线程安全地追加一行日志。

    日志格式: "2026-05-28 14:30:25 [STATUS] 消息内容"

    以下情况会静默跳过（不写文件，也不报错）：
        1. 日志尚未初始化（init_log 没被调用）
        2. 当前标签对应的作用域未被用户勾选

    Args:
        tag: 日志标签，必须是 "STATUS"、"SCRN"、"ERROR" 之一。
        msg: 日志消息内容。
    """
    # 未初始化 → 静默跳过
    if _log_path is None:
        return

    # 检查作用域：如果该标签对应的作用域未启用，不记录
    scope = _TAG_SCOPE.get(tag)
    if scope and scope not in _scopes:
        return

    # 构造日志行：时间戳 [标签] 消息
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{tag}] {msg}\n"

    # 加锁写文件 — 保证多线程并发写入时不会交错
    with _lock:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(line)
