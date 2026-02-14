# 游戏宝箱双界面自动点击（Python）

你反馈“还是不能自动移动”，我这版新增了更底层的 **Win32 原生输入注入**：`SendInput` 直接做“移动+点击”，不再依赖高层库的 moveTo 行为。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 模板

- `assets/open_btn.png`
- `assets/collect_btn.png`

## 优先推荐（针对你当前问题）

```bash
python auto_clicker.py --use-native-win32-input
```

如果窗口识别需要指定标题，再加：

```bash
python auto_clicker.py --window-title Pixel --use-native-win32-input
```

## 备选模式

1) 窗口消息点击（不依赖光标移动）：

```bash
python auto_clicker.py --window-title Pixel --use-window-message-click
```

2) 鼠标注入模式（旧方案）：

```bash
python auto_clicker.py --click-backend pydirectinput --click-method downup --force-sendinput-move
```

## 关键参数

- `--use-native-win32-input`：Windows 下最底层 SendInput 移动+点击（优先推荐）
- `--use-window-message-click`：发窗口消息点击
- `--window-title`：窗口标题关键字
- `--force-sendinput-move`：鼠标模式下强制 SendInput 移动

## 说明

- 如果游戏以管理员权限运行，脚本也建议用管理员权限运行（否则输入注入可能被系统拦截）。
