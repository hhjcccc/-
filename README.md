# 游戏宝箱双界面自动点击（Python）

你日志里出现了：目标是 `(1279, 1283)`，但系统光标实际在 `(1280, 799)`。这通常是 **Windows DPI 缩放导致坐标系不一致**（脚本进程没拿到真实分辨率坐标）。

这版已加入：
- 启动时自动设置进程 DPI Awareness（尽量拿到真实坐标）。
- `--print-win-metrics` 打印系统分辨率指标，快速确认是否仍存在缩放错位。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 模板

- `assets/open_btn.png`
- `assets/collect_btn.png`

## 先执行这个（排查 + 最底层点击）

```bash
python auto_clicker.py --use-native-win32-input --print-win-metrics
```

如果输出类似：
- `GetSystemMetrics=2560x1600`：坐标系正常。
- `GetSystemMetrics=1280x800`：说明仍被缩放影响，继续加 `--dpi-scale 2.0` 试。

示例：

```bash
python auto_clicker.py --use-native-win32-input --print-win-metrics --dpi-scale 2.0
```

## 备选模式

1) 窗口消息点击（不依赖光标移动）

```bash
python auto_clicker.py --window-title Pixel --use-window-message-click
```

2) 鼠标注入模式（旧链路）

```bash
python auto_clicker.py --click-backend pydirectinput --click-method downup --force-sendinput-move
```

## 关键参数

- `--use-native-win32-input`：Windows 最底层 SendInput 移动+点击（优先）
- `--print-win-metrics`：打印系统坐标指标，定位 DPI 缩放问题
- `--dpi-scale`：坐标倍率修正
- `--use-window-message-click`：窗口消息点击
- `--window-title`：窗口标题关键字

## 注意

- 如果游戏是“管理员权限”运行，脚本也要“管理员权限”运行，否则输入注入可能被拦截。
