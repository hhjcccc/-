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


def parse_scales(raw: str) -> list[float]:
    scales = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not scales:
        raise ValueError("--scales 不能为空")
    if any(scale <= 0 for scale in scales):
        raise ValueError("--scales 必须是正数")
    return scales


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="双界面循环自动识图点击（打开/收集）")
    parser.add_argument("--open-template", type=Path, default=Path("assets/open_btn.png"), help="界面一模板图")
    parser.add_argument("--collect-template", type=Path, default=Path("assets/collect_btn.png"), help="界面二模板图")
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
    parser.add_argument("--click-method", choices=["click", "downup"], default="downup", help="click=普通点击；downup=按下抬起，部分游戏更兼容")
    parser.add_argument("--click-count", type=int, default=1)
    parser.add_argument("--click-interval", type=float, default=0.03)
    parser.add_argument("--move-duration", type=float, default=0.0)
    parser.add_argument("--post-move-delay", type=float, default=0.03)
    parser.add_argument("--x-offset", type=int, default=0)
    parser.add_argument("--y-offset", type=int, default=0)
    parser.add_argument("--dpi-scale", type=float, default=1.0, help="坐标缩放倍率，如系统缩放 125% 可尝试 1.25")
    parser.add_argument("--window-title", type=str, help="点击前激活窗口（标题包含匹配）")
    parser.add_argument("--force-setcursor", action="store_true", help="Windows 下额外调用 SetCursorPos 强制移动光标")
    parser.add_argument("--force-sendinput-move", action="store_true", help="Windows 下使用 SendInput 绝对坐标强制移动光标")
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
    if gray:
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return frame_bgr


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


def focus_window_by_title(fragment: str) -> bool:
    if not fragment:
        return False
    try:
        gw = importlib.import_module("pygetwindow")
    except Exception:
        print("[提示] 未安装 pygetwindow，跳过窗口激活。")
        return False

    try:
        wins = gw.getAllWindows()
        target = None
        for w in wins:
            title = getattr(w, "title", "") or ""
            if fragment.lower() in title.lower():
                target = w
                break
        if target is None:
            print(f"[提示] 未找到窗口标题包含: {fragment}")
            return False
        target.activate()
        time.sleep(0.05)
        return True
    except Exception as exc:
        print(f"[提示] 激活窗口失败: {exc}")
        return False


def win_sendinput_move(x: int, y: int) -> None:
    if not sys.platform.startswith("win"):
        return

    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    if screen_w <= 1 or screen_h <= 1:
        return

    # 坐标映射到 0~65535
    abs_x = int(x * 65535 / (screen_w - 1))
    abs_y = int(y * 65535 / (screen_h - 1))

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_ulonglong)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]

    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_ABSOLUTE = 0x8000

    inp = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=abs_x, dy=abs_y, mouseData=0, dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, time=0, dwExtraInfo=0))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def move_cursor(click_api, x: int, y: int, move_duration: float, force_setcursor: bool, force_sendinput_move: bool) -> None:
    # 先用自动化库移动
    click_api.moveTo(x, y, duration=move_duration)

    # 某些 Windows 游戏对移动事件不敏感，额外使用系统 API 强制设置光标位置
    if force_setcursor and sys.platform.startswith("win"):
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

    # 更强硬的系统输入注入移动（某些游戏只认这个）
    if force_sendinput_move and sys.platform.startswith("win"):
        win_sendinput_move(int(x), int(y))


def do_click(click_api, x: int, y: int, click_method: str) -> None:
    if click_method == "click":
        click_api.click(x, y)
        return

    # downup: 对部分游戏兼容性更高
    click_api.mouseDown(x=x, y=y)
    time.sleep(0.01)
    click_api.mouseUp(x=x, y=y)


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
) -> None:
    tw, th = template_size
    base_x = offset[0] + location[0] + tw // 2 + x_offset
    base_y = offset[1] + location[1] + th // 2 + y_offset
    click_x = int(round(base_x * dpi_scale))
    click_y = int(round(base_y * dpi_scale))

    if dry_run:
        print(f"[DRY] {label} -> ({click_x}, {click_y}) raw=({base_x}, {base_y}) scale={dpi_scale}")
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

    if sys.platform.startswith("win") and args.dpi_scale == 1.0:
        print("[提示] 若识别命中但游戏无反应，可尝试 --dpi-scale 1.25 或 1.5")
        print("[提示] 若光标不自动移动，可加 --force-sendinput-move")

    try:
        open_template = load_template(args.open_template, args.gray)
        collect_template = load_template(args.collect_template, args.gray)
    except FileNotFoundError as exc:
        print("[错误] 模板加载失败：")
        print(exc)
        print("示例运行：python auto_clicker.py --dry-run")
        return

    try:
        backend_name, click_api = resolve_click_backend(args.click_backend)
    except ModuleNotFoundError:
        print("[错误] 你指定了 pydirectinput，但本机未安装。请执行: pip install pydirectinput")
        return

    region = None
    offset = (0, 0)
    if args.region:
        left, top, width, height = args.region
        region = MonitorRegion(left=left, top=top, width=width, height=height)
        offset = (left, top)

    click_count = 0
    print(f"脚本启动，Ctrl+C 退出。点击后端: {backend_name}，点击方式: {args.click_method}。")

    with mss.mss() as sct:
        while True:
            frame = capture_screen(sct, region, args.gray)
            collect_score, collect_loc, collect_size = match_with_scales(frame, collect_template, scales)
            open_score, open_loc, open_size = match_with_scales(frame, open_template, scales)

            clicked = False
            if collect_score >= args.collect_threshold:
                print(f"[HIT] collect score={collect_score:.4f}, loc={collect_loc}")
                if args.window_title:
                    focus_window_by_title(args.window_title)
                if args.debug_dir:
                    save_debug(args.debug_dir, frame, "collect", collect_score)
                click_center(
                    collect_loc,
                    collect_size,
                    offset,
                    args.x_offset,
                    args.y_offset,
                    args.dpi_scale,
                    args.dry_run,
                    "collect",
                    click_api,
                    args.click_count,
                    args.click_interval,
                    args.move_duration,
                    args.post_move_delay,
                    args.click_method,
                    args.force_setcursor,
                    args.force_sendinput_move,
                )
                clicked = True
            elif open_score >= args.open_threshold:
                print(f"[HIT] open score={open_score:.4f}, loc={open_loc}")
                if args.window_title:
                    focus_window_by_title(args.window_title)
                if args.debug_dir:
                    save_debug(args.debug_dir, frame, "open", open_score)
                click_center(
                    open_loc,
                    open_size,
                    offset,
                    args.x_offset,
                    args.y_offset,
                    args.dpi_scale,
                    args.dry_run,
                    "open",
                    click_api,
                    args.click_count,
                    args.click_interval,
                    args.move_duration,
                    args.post_move_delay,
                    args.click_method,
                    args.force_setcursor,
                    args.force_sendinput_move,
                )
                clicked = True
            else:
                print(f"[MISS] collect={collect_score:.4f}, open={open_score:.4f}")

            if clicked:
                click_count += 1
                if args.max_clicks > 0 and click_count >= args.max_clicks:
                    print(f"达到最大点击次数 {args.max_clicks}，退出。")
                    return
                time.sleep(args.cooldown)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
