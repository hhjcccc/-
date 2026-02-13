# 游戏宝箱双界面自动点击（Python）

你现在的问题是：**能识别（HIT），但游戏里没反应**。这通常不是识图问题，而是“点击注入方式”或“DPI坐标缩放”问题。

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 模板图

- `assets/open_btn.png`（界面一红框）
- `assets/collect_btn.png`（界面二红框）

## 3) 先用这条（推荐）

```bash
python auto_clicker.py --click-backend pydirectinput --click-method downup --click-count 2 --post-move-delay 0.03
```

## 4) 仍无反应时，按顺序调

### A. 处理 Windows 缩放导致“坐标不在真实按钮上”

```bash
python auto_clicker.py --click-backend pydirectinput --dpi-scale 1.25
```

如果你系统缩放是 150%，就试：

```bash
python auto_clicker.py --click-backend pydirectinput --dpi-scale 1.5
```

### B. 坐标微调

```bash
python auto_clicker.py --click-backend pydirectinput --y-offset 8
```

### C. 窗口激活（防止点到了后台）

```bash
python auto_clicker.py --window-title Pixel
```

> `--window-title` 传游戏窗口标题里的一部分关键词。

## 5) 常用参数

- `--click-backend auto|pyautogui|pydirectinput`
- `--click-method click|downup`
- `--click-count` / `--click-interval`
- `--dpi-scale`
- `--x-offset` / `--y-offset`
- `--region LEFT TOP WIDTH HEIGHT`
- `--dry-run`

## 6) 说明

- `downup` 在很多游戏里比 `click()` 更容易生效。
- `auto` 会优先用 `pydirectinput`。
- 鼠标移到左上角可触发 failsafe 停止。
