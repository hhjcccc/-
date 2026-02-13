#!/usr/bin/env python3
"""双界面循环的游戏宝箱自动识图点击脚本。"""

from __future__ import annotations

import argparse
import importlib
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
    parser.add_argument("--open-template", type=Path, default=Path("assets/open_btn.png"), help="界面一模板图，默认 assets/open_btn.png")
    parser.add_argument("--collect-template", type=Path, default=Path("assets/collect_btn.png"), help="界面二模板图，默认 assets/collect_btn.png")
    parser.add_argument("--open-threshold", type=float, default=0.84, help="打开按钮匹配阈值")
    parser.add_argument("--collect-threshold", type=float, default=0.84, help="收集按钮匹配阈值")
    parser.add_argument("--interval", type=float, default=0.2, help="每轮识别间隔秒数")
    parser.add_argument("--cooldown", type=float, default=0.12, help="每次点击后的冷却秒数")
    parser.add_argument("--max-clicks", type=int, default=0, help="最大点击次数，0 表示无限")
    parser.add_argument("--region", type=int, nargs=4, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"), help="仅在指定区域识图")
    parser.add_argument("--gray", action="store_true", help="灰度匹配（更快）")
    parser.add_argument("--dry-run", action="store_true", help="只输出日志，不实际点击")
    parser.add_argument("--scales", default="1.0", help="模板缩放倍率，例如 0.9,1.0,1.1")
    parser.add_argument("--debug-dir", type=Path, help="命中时保存截图到目录")

    parser.add_argument("--click-backend", choices=["auto", "pyautogui", "pydirectinput"], default="auto", help="点击后端，默认 auto")
    parser.add_argument("--click-count", type=int, default=1, help="每次命中连点次数，默认 1")
    parser.add_argument("--click-interval", type=float, default=0.03, help="连点间隔秒数")
    parser.add_argument("--move-duration", type=float, default=0.0, help="移动到目标点耗时秒数")
    parser.add_argument("--post-move-delay", type=float, default=0.02, help="移动到点位后的等待秒数")
    parser.add_argument("--x-offset", type=int, default=0, help="点击坐标 X 偏移（像素）")
    parser.add_argument("--y-offset", type=int, default=0, help="点击坐标 Y 偏移（像素）")
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

    # auto: 优先用 pydirectinput（对部分游戏更有效）
    try:
        module = importlib.import_module("pydirectinput")
        module.FAILSAFE = True
        module.PAUSE = 0
        return "pydirectinput", module
    except Exception:
        return "pyautogui", pyautogui


def click_center(
    location: tuple[int, int],
    template_size: tuple[int, int],
    offset: tuple[int, int],
    x_offset: int,
    y_offset: int,
    dry_run: bool,
    label: str,
    click_api,
    click_count: int,
    click_interval: float,
    move_duration: float,
    post_move_delay: float,
) -> None:
    tw, th = template_size
    click_x = offset[0] + location[0] + tw // 2 + x_offset
    click_y = offset[1] + location[1] + th // 2 + y_offset

    if dry_run:
        print(f"[DRY] {label} -> ({click_x}, {click_y})")
        return

    click_api.moveTo(click_x, click_y, duration=move_duration)
    if post_move_delay > 0:
        time.sleep(post_move_delay)
    for _ in range(max(1, click_count)):
        click_api.click(click_x, click_y)
        if click_interval > 0:
            time.sleep(click_interval)
    print(f"[OK] {label} -> ({click_x}, {click_y})")


def save_debug(debug_dir: Path, frame: np.ndarray, label: str, score: float) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    cv2.imwrite(str(debug_dir / f"{ts}_{label}_{score:.3f}.png"), frame)


def main() -> None:
    args = parse_args()
    scales = parse_scales(args.scales)

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0

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
    print(f"脚本启动，Ctrl+C 退出。点击后端: {backend_name}。优先点击【收集】，其次【打开】。")

    with mss.mss() as sct:
        while True:
            frame = capture_screen(sct, region, args.gray)
            collect_score, collect_loc, collect_size = match_with_scales(frame, collect_template, scales)
            open_score, open_loc, open_size = match_with_scales(frame, open_template, scales)

            clicked = False
            if collect_score >= args.collect_threshold:
                print(f"[HIT] collect score={collect_score:.4f}, loc={collect_loc}")
                if args.debug_dir:
                    save_debug(args.debug_dir, frame, "collect", collect_score)
                click_center(
                    collect_loc,
                    collect_size,
                    offset,
                    args.x_offset,
                    args.y_offset,
                    args.dry_run,
                    "collect",
                    click_api,
                    args.click_count,
                    args.click_interval,
                    args.move_duration,
                    args.post_move_delay,
                )
                clicked = True
            elif open_score >= args.open_threshold:
                print(f"[HIT] open score={open_score:.4f}, loc={open_loc}")
                if args.debug_dir:
                    save_debug(args.debug_dir, frame, "open", open_score)
                click_center(
                    open_loc,
                    open_size,
                    offset,
                    args.x_offset,
                    args.y_offset,
                    args.dry_run,
                    "open",
                    click_api,
                    args.click_count,
                    args.click_interval,
                    args.move_duration,
                    args.post_move_delay,
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
