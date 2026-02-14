# 游戏宝箱双界面自动点击（Python）

你现在这个日志说明：
- 识图命中稳定。
- 原生移动经常被锁在中心。
- 已经走了 `window_message_fallback`，但窗口可能不是正确句柄（父/子窗口差异）。

这版加强了窗口消息点击：
1. 目标点句柄 + 父/根窗口一起尝试。
2. 同时发送 `PostMessage` 和 `SendMessage`。
3. 支持重复发送（默认 3 次）。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 模板

- `assets/open_btn.png`
- `assets/collect_btn.png`

## 推荐命令（先跑这个）

```bash
python auto_clicker.py \
  --use-native-win32-input \
  --auto-fallback-window-message \
  --window-point-priority \
  --message-repeat 3 \
  --message-delay 0.01 \
  --window-title "Pixel Gun 3D"
```

## 参数说明

- `--window-point-priority`：优先使用目标坐标下句柄，再尝试父/根窗口。
- `--message-repeat`：每个候选窗口重复发消息次数。
- `--message-delay`：每次消息发送间隔。
- `--auto-fallback-window-message`：原生移动偏差大时自动切到窗口消息点击。

## 备注

- 如果游戏管理员运行，脚本也请管理员运行。
