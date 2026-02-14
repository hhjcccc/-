# 游戏宝箱双界面自动点击（Python）

你现在的日志显示：
- 目标：`(1981,1267)`
- 实际光标：`(1279,799)`（屏幕中间附近）

这通常是**游戏锁鼠标到中心**，不是识图错了。为此我加了“自动回退窗口消息点击”。

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
python auto_clicker.py --use-native-win32-input --auto-fallback-window-message --window-title Pixel
```

说明：
- 先尝试原生 `SendInput` 移动+点击。
- 如果检测到光标仍被锁在中心（偏差大），会自动改用窗口消息点击，不再依赖光标移动。

## 调试命令（看坐标体系）

```bash
python auto_clicker.py --use-native-win32-input --print-win-metrics
```

## 关键参数

- `--use-native-win32-input`：最底层 Win32 移动+点击。
- `--auto-fallback-window-message`：原生移动失败时自动回退窗口消息点击（建议开启）。
- `--window-title`：窗口标题关键字（回退窗口消息时建议填写）。
- `--use-window-message-click`：只使用窗口消息点击。
- `--dpi-scale`：坐标倍率修正。

## 注意

- 若游戏管理员启动，脚本也需管理员启动。
- 某些反作弊会屏蔽窗口消息，此时只能依赖可用的输入注入路径。
