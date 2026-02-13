# 游戏宝箱双界面自动点击（Python）

根据你的流程：
1. **界面一**点击红框“打开”按钮。
2. 切到**界面二**后点击红框“收集”按钮。
3. 然后又回到界面一，循环往复。

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 模板图

准备两张模板：
- `assets/open_btn.png`（界面一红框按钮）
- `assets/collect_btn.png`（界面二红框按钮）

## 3) 启动

最简：

```bash
python auto_clicker.py
```

推荐（对游戏更稳）：

```bash
python auto_clicker.py --click-backend pydirectinput --click-count 2 --post-move-delay 0.03
```

## 4) 关键参数

- `--click-backend auto|pyautogui|pydirectinput`
  - `auto` 默认优先用 `pydirectinput`（很多游戏只认它）。
- `--click-count 2`：每次命中连点两下。
- `--x-offset` / `--y-offset`：如果识别对了但点击点偏了，可微调。
- `--region LEFT TOP WIDTH HEIGHT`：只在按钮区域识图（更快、误点更少）。
- `--dry-run`：只打印坐标，不点鼠标。

## 5) 你这个“识别到了但游戏没反应”怎么处理

按顺序试：

1. 用 `pydirectinput`：

```bash
python auto_clicker.py --click-backend pydirectinput
```

2. 增加连点和短暂停顿：

```bash
python auto_clicker.py --click-backend pydirectinput --click-count 2 --post-move-delay 0.03
```

3. 加坐标微调（例如向下偏 8 像素）：

```bash
python auto_clicker.py --click-backend pydirectinput --y-offset 8
```

4. 先 dry-run 看坐标是否落在按钮正中：

```bash
python auto_clicker.py --dry-run
```

## 6) 注意

- 先保证游戏窗口在前台并可接收鼠标输入。
- 鼠标移到左上角可触发 failsafe 停止。
- 某些游戏有反自动化策略，请自行确认规则。
