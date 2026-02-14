#!/usr/bin/env python3
"""双界面循环的游戏宝箱自动识图点击脚本。"""

from __future__ import annotations

import argparse
import ctypes
import importlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np
import pyautogui


@dataclass
class MonitorRegion:
    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}


def enable_windows_dpi_awareness() -> None:
    if not sys.platform.startswith("win"):
        return

    user32 = ctypes.windll.user32
    try:
        # Windows 10+
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return
    except Exception:
        pass

    try:
        # Windows 8.1+
        shcore = ctypes.windll.shcore
        PROCESS_PER_MONITOR_DPI_AWARE = 2
        shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        return
    except Exception:
        pass

    try:
        # Windows Vista+
        user32.SetProcessDPIAware()
    except Exception:
        pass


def parse_scales(raw: str) -> list[float]:
    scales = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not scales:
        raise ValueError("--scales 不能为空")
    if any(scale <= 0 for scale in scales):
        raise ValueError("--scales 必须是正数")
    return scales


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="双界面循环自动识图点击（打开/收集）")
    parser.add_argument("--open-template", type=Path, default=Path("assets/open_btn.png"))
    parser.add_argument("--collect-template", type=Path, default=Path("assets/collect_btn.png"))
    parser.add_argument("--open-threshold", type=float, default=0.84)
    parser.add_argument("--collect-threshold", type=float, default=0.84)
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--cooldown", type=float, default=0.12)
    parser.add_argument("--max-clicks", type=int, default=0)
    parser.add_argument("--region", type=int, nargs=4, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"))
    parser.add_argument("--gray", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scales", default="1.0")
    parser.add_argument("--debug-dir", type=Path)

    parser.add_argument("--click-backend", choices=["auto", "pyautogui", "pydirectinput"], default="auto")
    parser.add_argument("--click-method", choices=["click", "downup"], default="downup")
    parser.add_argument("--click-count", type=int, default=1)
    parser.add_argument("--click-interval", type=float, default=0.03)
    parser.add_argument("--move-duration", type=float, default=0.0)
    parser.add_argument("--post-move-delay", type=float, default=0.03)
    parser.add_argument("--x-offset", type=int, default=0)
    parser.add_argument("--y-offset", type=int, default=0)
    parser.add_argument("--dpi-scale", type=float, default=1.0)
    parser.add_argument("--window-title", type=str, help="窗口标题关键字")
    parser.add_argument("--force-setcursor", action="store_true")
    parser.add_argument("--force-sendinput-move", action="store_true")
    parser.add_argument("--use-window-message-click", action="store_true", help="Windows: 用 PostMessage 直接向窗口发送点击，不依赖鼠标移动")
    parser.add_argument("--use-native-win32-input", action="store_true", help="Windows: 使用 SendInput 原生注入移动+点击（最底层）")
    parser.add_argument("--print-win-metrics", action="store_true", help="打印 Windows 屏幕指标，便于排查坐标缩放")
    parser.add_argument("--auto-fallback-window-message", action="store_true", help="原生移动偏差大时自动回退窗口消息点击")
    parser.add_argument("--window-point-priority", action="store_true", help="窗口消息点击时优先向目标坐标下的窗口句柄发送")
    parser.add_argument("--message-repeat", type=int, default=3, help="窗口消息点击重复次数")
    parser.add_argument("--message-delay", type=float, default=0.01, help="窗口消息点击每次间隔秒数")
    parser.add_argument("--open-region", type=int, nargs=4, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"), help="仅用于 open 模板的绝对屏幕区域")
    parser.add_argument("--collect-region", type=int, nargs=4, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"), help="仅用于 collect 模板的绝对屏幕区域")
    parser.add_argument("--confirm-hit-frames", type=int, default=1, help="连续命中多少帧后才点击（减少误识别）")
    return parser.parse_args()


def load_template(path: Path, gray: bool) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(
            f"模板图不存在: {path}\n"
            "请确认路径正确，或把模板放到默认位置：\n"
            "- assets/open_btn.png\n"
            "- assets/collect_btn.png"
        )
    flag = cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR
    template = cv2.imread(str(path), flag)
    if template is None:
        raise RuntimeError(f"模板图读取失败: {path}")
    return template


def capture_screen(sct: mss.mss, region: MonitorRegion | None, gray: bool) -> np.ndarray:
    monitor = region.to_dict() if region else sct.monitors[1]
    raw = np.array(sct.grab(monitor))
    frame_bgr = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if gray else frame_bgr


def match_with_scales(frame: np.ndarray, template: np.ndarray, scales: list[float]) -> tuple[float, tuple[int, int], tuple[int, int]]:
    best_score = -1.0
    best_loc = (0, 0)
    best_size = (template.shape[1], template.shape[0])
    for scale in scales:
        scaled = template if abs(scale - 1.0) < 1e-6 else cv2.resize(template, dsize=None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        th, tw = scaled.shape[:2]
        fh, fw = frame.shape[:2]
        if th > fh or tw > fw:
            continue
        result = cv2.matchTemplate(frame, scaled, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        if score > best_score:
            best_score, best_loc, best_size = score, loc, (tw, th)
    return best_score, best_loc, best_size




def to_region(region_values: list[int] | tuple[int, int, int, int] | None) -> MonitorRegion | None:
    if not region_values:
        return None
    left, top, width, height = region_values
    return MonitorRegion(left=left, top=top, width=width, height=height)


def crop_by_abs_region(
    frame: np.ndarray,
    capture_offset: tuple[int, int],
    abs_region: MonitorRegion | None,
) -> tuple[np.ndarray, tuple[int, int]]:
    if abs_region is None:
        return frame, capture_offset

    cap_left, cap_top = capture_offset
    rel_left = abs_region.left - cap_left
    rel_top = abs_region.top - cap_top
    rel_right = rel_left + abs_region.width
    rel_bottom = rel_top + abs_region.height

    h, w = frame.shape[:2]
    x1 = max(0, rel_left)
    y1 = max(0, rel_top)
    x2 = min(w, rel_right)
    y2 = min(h, rel_bottom)

    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0], capture_offset

    sub = frame[y1:y2, x1:x2]
    sub_offset = (cap_left + x1, cap_top + y1)
    return sub, sub_offset


def stable_hit(last_loc: tuple[int, int] | None, now_loc: tuple[int, int], tolerance: int = 10) -> bool:
    if last_loc is None:
        return False
    return abs(last_loc[0] - now_loc[0]) <= tolerance and abs(last_loc[1] - now_loc[1]) <= tolerance

def resolve_click_backend(name: str):
    if name == "pyautogui":
        return "pyautogui", pyautogui
    if name == "pydirectinput":
        module = importlib.import_module("pydirectinput")
        module.FAILSAFE = True
        module.PAUSE = 0
        return "pydirectinput", module
    try:
        module = importlib.import_module("pydirectinput")
        module.FAILSAFE = True
        module.PAUSE = 0
        return "pydirectinput", module
    except Exception:
        return "pyautogui", pyautogui


def find_window_by_title(fragment: str):
    if not fragment:
        return None
    try:
        gw = importlib.import_module("pygetwindow")
    except Exception:
        return None
    try:
        for w in gw.getAllWindows():
            title = getattr(w, "title", "") or ""
            if fragment.lower() in title.lower():
                return w
    except Exception:
        return None
    return None


def get_target_hwnd(window_title: str | None):
    if not sys.platform.startswith("win"):
        return None

    if window_title:
        w = find_window_by_title(window_title)
        hwnd = getattr(w, "_hWnd", None) if w else None
        if hwnd:
            return hwnd

    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        return hwnd if hwnd else None
    except Exception:
        return None


def focus_window_by_title(fragment: str) -> bool:
    target = find_window_by_title(fragment)
    if not target:
        return False
    try:
        target.activate()
        time.sleep(0.05)
        return True
    except Exception:
        return False


def _win_build_input_structs():
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_ulonglong),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]

    return MOUSEINPUT, INPUT


def _win_abs_xy(x: int, y: int) -> tuple[int, int]:
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    if screen_w <= 1 or screen_h <= 1:
        return x, y

    abs_x = int(round(x * 65535 / (screen_w - 1)))
    abs_y = int(round(y * 65535 / (screen_h - 1)))

    # SendInput 绝对坐标要求 0~65535
    abs_x = max(0, min(65535, abs_x))
    abs_y = max(0, min(65535, abs_y))
    return abs_x, abs_y


def win_native_move_and_click(x: int, y: int, click_count: int, click_interval: float) -> tuple[bool, bool]:
    if not sys.platform.startswith("win"):
        return False, False

    user32 = ctypes.windll.user32
    MOUSEINPUT, INPUT = _win_build_input_structs()

    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004

    abs_x, abs_y = _win_abs_xy(int(x), int(y))

    move_event = INPUT(
        type=INPUT_MOUSE,
        mi=MOUSEINPUT(dx=abs_x, dy=abs_y, mouseData=0, dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, time=0, dwExtraInfo=0),
    )

    user32.SendInput(1, ctypes.byref(move_event), ctypes.sizeof(move_event))

    down_event = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=0))
    up_event = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTUP, time=0, dwExtraInfo=0))

    for _ in range(max(1, click_count)):
        user32.SendInput(1, ctypes.byref(down_event), ctypes.sizeof(down_event))
        user32.SendInput(1, ctypes.byref(up_event), ctypes.sizeof(up_event))
        if click_interval > 0:
            time.sleep(click_interval)

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    moved_ok = True
    if user32.GetCursorPos(ctypes.byref(pt)):
        dx = abs(pt.x - int(x))
        dy = abs(pt.y - int(y))
        if dx > 4 or dy > 4:
            moved_ok = False
            print(f"[WARN] 原生注入后光标偏差较大: now=({pt.x},{pt.y}) target=({x},{y})")
    return True, moved_ok


def win_sendinput_move(x: int, y: int) -> None:
    if not sys.platform.startswith("win"):
        return
    user32 = ctypes.windll.user32
    MOUSEINPUT, INPUT = _win_build_input_structs()
    abs_x, abs_y = _win_abs_xy(int(x), int(y))
    inp = INPUT(type=0, mi=MOUSEINPUT(dx=abs_x, dy=abs_y, mouseData=0, dwFlags=0x0001 | 0x8000, time=0, dwExtraInfo=0))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def move_cursor(click_api, x: int, y: int, move_duration: float, force_setcursor: bool, force_sendinput_move: bool) -> None:
    click_api.moveTo(x, y, duration=move_duration)
    if force_setcursor and sys.platform.startswith("win"):
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
    if force_sendinput_move and sys.platform.startswith("win"):
        win_sendinput_move(int(x), int(y))


def do_click(click_api, x: int, y: int, click_method: str) -> None:
    if click_method == "click":
        click_api.click(x, y)
        return
    click_api.mouseDown(x=x, y=y)
    time.sleep(0.01)
    click_api.mouseUp(x=x, y=y)


def get_hwnd_from_screen_point(x: int, y: int):
    if not sys.platform.startswith("win"):
        return None

    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT(x, y)
    try:
        hwnd = user32.WindowFromPoint(pt)
        return hwnd if hwnd else None
    except Exception:
        return None


def post_message_click(window_title: str | None, x: int, y: int, window_point_priority: bool, message_repeat: int, message_delay: float) -> bool:
    if not sys.platform.startswith("win"):
        return False

    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    hwnd_candidates = []
    if window_point_priority:
        pt_hwnd = get_hwnd_from_screen_point(x, y)
        if pt_hwnd:
            hwnd_candidates.append(pt_hwnd)
            # 把根窗口也加入候选，避免只发给子窗口无效
            GA_PARENT = 1
            GA_ROOT = 2
            try:
                parent = user32.GetAncestor(pt_hwnd, GA_PARENT)
                root = user32.GetAncestor(pt_hwnd, GA_ROOT)
                if parent:
                    hwnd_candidates.append(parent)
                if root:
                    hwnd_candidates.append(root)
            except Exception:
                pass

    by_title = get_target_hwnd(window_title)
    if by_title:
        hwnd_candidates.append(by_title)

    try:
        fg = user32.GetForegroundWindow()
        if fg:
            hwnd_candidates.append(fg)
    except Exception:
        pass

    unique_hwnds = []
    seen = set()
    for h in hwnd_candidates:
        if h and h not in seen:
            seen.add(h)
            unique_hwnds.append(h)

    if not unique_hwnds:
        return False

    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    MK_LBUTTON = 0x0001

    dispatched = False
    repeats = max(1, int(message_repeat))
    for hwnd in unique_hwnds:
        pt = POINT(x, y)
        if user32.ScreenToClient(hwnd, ctypes.byref(pt)) == 0:
            continue

        lparam = (pt.y << 16) | (pt.x & 0xFFFF)

        for _ in range(repeats):
            user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
            user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

            user32.SendMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
            user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
            user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
            if message_delay > 0:
                time.sleep(message_delay)

        dispatched = True

    return dispatched


def click_center(
    location: tuple[int, int],
    template_size: tuple[int, int],
    offset: tuple[int, int],
    x_offset: int,
    y_offset: int,
    dpi_scale: float,
    dry_run: bool,
    label: str,
    click_api,
    click_count: int,
    click_interval: float,
    move_duration: float,
    post_move_delay: float,
    click_method: str,
    force_setcursor: bool,
    force_sendinput_move: bool,
    use_window_message_click: bool,
    use_native_win32_input: bool,
    auto_fallback_window_message: bool,
    window_point_priority: bool,
    message_repeat: int,
    message_delay: float,
    window_title: str | None,
) -> None:
    tw, th = template_size
    base_x = offset[0] + location[0] + tw // 2 + x_offset
    base_y = offset[1] + location[1] + th // 2 + y_offset
    click_x = int(round(base_x * dpi_scale))
    click_y = int(round(base_y * dpi_scale))

    if dry_run:
        print(f"[DRY] {label} -> ({click_x}, {click_y}) raw=({base_x}, {base_y})")
        return

    # 新增：直接发窗口消息点击（不依赖光标移动）
    if use_window_message_click and post_message_click(window_title, click_x, click_y, window_point_priority, message_repeat, message_delay):
        print(f"[OK] {label} -> ({click_x}, {click_y}) method=window_message")
        return

    # 更底层：Win32 SendInput 一步完成移动+点击
    if use_native_win32_input:
        native_ok, moved_ok = win_native_move_and_click(click_x, click_y, click_count, click_interval)
        if native_ok:
            if moved_ok:
                print(f"[OK] {label} -> ({click_x}, {click_y}) method=native_win32")
                return
            if auto_fallback_window_message and post_message_click(window_title, click_x, click_y, window_point_priority, message_repeat, message_delay):
                print(f"[OK] {label} -> ({click_x}, {click_y}) method=native_win32+window_message_fallback")
                return
            print(f"[OK] {label} -> ({click_x}, {click_y}) method=native_win32 (cursor_locked)")
            return

    move_cursor(click_api, click_x, click_y, move_duration, force_setcursor, force_sendinput_move)
    if post_move_delay > 0:
        time.sleep(post_move_delay)
    for _ in range(max(1, click_count)):
        do_click(click_api, click_x, click_y, click_method)
        if click_interval > 0:
            time.sleep(click_interval)
    print(f"[OK] {label} -> ({click_x}, {click_y}) method={click_method}")


def save_debug(debug_dir: Path, frame: np.ndarray, label: str, score: float) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    cv2.imwrite(str(debug_dir / f"{ts}_{label}_{score:.3f}.png"), frame)


def main() -> None:
    args = parse_args()
    scales = parse_scales(args.scales)

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0

    enable_windows_dpi_awareness()

    try:
        open_template = load_template(args.open_template, args.gray)
        collect_template = load_template(args.collect_template, args.gray)
    except FileNotFoundError as exc:
        print("[错误] 模板加载失败：")
        print(exc)
        return

    try:
        backend_name, click_api = resolve_click_backend(args.click_backend)
    except ModuleNotFoundError:
        print("[错误] 你指定了 pydirectinput，但本机未安装。请执行: pip install pydirectinput")
        return

    if args.print_win_metrics and sys.platform.startswith("win"):
        user32 = ctypes.windll.user32
        sm_w = user32.GetSystemMetrics(0)
        sm_h = user32.GetSystemMetrics(1)
        pg_w, pg_h = pyautogui.size()
        print(f"[WIN] GetSystemMetrics={sm_w}x{sm_h}, pyautogui={pg_w}x{pg_h}, dpi_scale={args.dpi_scale}")

    capture_region = to_region(args.region)
    capture_offset = (capture_region.left, capture_region.top) if capture_region else (0, 0)

    open_region = to_region(args.open_region)
    collect_region = to_region(args.collect_region)

    confirm_need = max(1, args.confirm_hit_frames)
    streaks = {"open": 0, "collect": 0}
    last_locs: dict[str, tuple[int, int] | None] = {"open": None, "collect": None}

    print(f"脚本启动，Ctrl+C 退出。后端: {backend_name}")
    click_total = 0

    with mss.mss() as sct:
        while True:
            frame = capture_screen(sct, capture_region, args.gray)

            collect_frame, collect_offset = crop_by_abs_region(frame, capture_offset, collect_region)
            open_frame, open_offset = crop_by_abs_region(frame, capture_offset, open_region)

            collect_score, collect_loc, collect_size = (-1.0, (0, 0), (0, 0))
            if collect_frame.size > 0:
                collect_score, collect_loc, collect_size = match_with_scales(collect_frame, collect_template, scales)

            open_score, open_loc, open_size = (-1.0, (0, 0), (0, 0))
            if open_frame.size > 0:
                open_score, open_loc, open_size = match_with_scales(open_frame, open_template, scales)

            target = None
            if collect_score >= args.collect_threshold:
                if stable_hit(last_locs["collect"], collect_loc):
                    streaks["collect"] += 1
                else:
                    streaks["collect"] = 1
                last_locs["collect"] = collect_loc

                if streaks["collect"] >= confirm_need:
                    target = ("collect", collect_loc, collect_size, collect_score, collect_offset)
            else:
                streaks["collect"] = 0
                last_locs["collect"] = None

            if target is None and open_score >= args.open_threshold:
                if stable_hit(last_locs["open"], open_loc):
                    streaks["open"] += 1
                else:
                    streaks["open"] = 1
                last_locs["open"] = open_loc

                if streaks["open"] >= confirm_need:
                    target = ("open", open_loc, open_size, open_score, open_offset)
            elif target is not None:
                # collect 命中时，open 的连击计数清零，避免跨界面误触
                streaks["open"] = 0
                last_locs["open"] = None
            else:
                streaks["open"] = 0
                last_locs["open"] = None

            if target is None:
                print(
                    f"[MISS] collect={collect_score:.4f}(streak={streaks['collect']}) "
                    f"open={open_score:.4f}(streak={streaks['open']})"
                )
            else:
                label, loc, size, score, target_offset = target
                print(f"[HIT] {label} score={score:.4f}, loc={loc}, streak={streaks[label]}")

                if args.window_title:
                    focus_window_by_title(args.window_title)

                if args.debug_dir:
                    save_debug(args.debug_dir, frame, label, score)

                click_center(
                    loc,
                    size,
                    target_offset,
                    args.x_offset,
                    args.y_offset,
                    args.dpi_scale,
                    args.dry_run,
                    label,
                    click_api,
                    args.click_count,
                    args.click_interval,
                    args.move_duration,
                    args.post_move_delay,
                    args.click_method,
                    args.force_setcursor,
                    args.force_sendinput_move,
                    args.use_window_message_click,
                    args.use_native_win32_input,
                    args.auto_fallback_window_message,
                    args.window_point_priority,
                    args.message_repeat,
                    args.message_delay,
                    args.window_title,
                )

                streaks[label] = 0
                last_locs[label] = None

                click_total += 1
                if args.max_clicks > 0 and click_total >= args.max_clicks:
                    print(f"达到最大点击次数 {args.max_clicks}，退出。")
                    return
                time.sleep(args.cooldown)

            time.sleep(args.interval)


if __name__ == "__main__":
    main()
