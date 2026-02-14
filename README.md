# 游戏宝箱双界面自动点击（Python）

你当前日志说明：原生移动经常被锁到中心，但偶发能成功。这类情况一般是游戏窗口输入层不稳定或消息发给了“错误句柄”（父窗口/子窗口不一致）。

这版新增：
- `--window-point-priority`：窗口消息点击时，优先给“目标坐标下的真实窗口句柄”发消息。
- 同时发送 `PostMessage` + `SendMessage`，提升窗口消息路径命中率。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 模板

- `assets/open_btn.png`
- `assets/collect_btn.png`

## 推荐命令（针对你当前日志）

```bash
python auto_clicker.py \
  --use-native-win32-input \
  --auto-fallback-window-message \
  --window-point-priority \
  --window-title Pixel
```

说明：
1. 先走原生 SendInput。
2. 若检测到光标仍被锁中心，自动回退窗口消息点击。
3. 回退时优先把消息发给目标点下的窗口句柄，而不是只靠标题匹配。

## 可选排查

```bash
python auto_clicker.py --use-native-win32-input --print-win-metrics
```

## 关键参数

- `--use-native-win32-input`
- `--auto-fallback-window-message`
- `--window-point-priority`
- `--window-title`
- `--use-window-message-click`

## 注意

- 游戏若管理员启动，脚本也请管理员启动。
