# 游戏宝箱双界面自动点击（Python）

你反馈“还是不能自动移动”，说明游戏可能屏蔽了常规鼠标移动事件。这个版本新增了**窗口消息点击模式**，不依赖光标实际移动。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 模板

- `assets/open_btn.png`
- `assets/collect_btn.png`

## 优先推荐命令（针对你当前问题）

> 把 `Pixel` 换成你的游戏窗口标题关键字。

```bash
python auto_clicker.py --window-title Pixel --use-window-message-click
```

## 若仍需鼠标注入模式

```bash
python auto_clicker.py --click-backend pydirectinput --click-method downup --force-sendinput-move
```

## 参数补充

- `--use-window-message-click`：Windows 下直接 `PostMessage` 发送点击到游戏窗口（不依赖光标是否移动）。
- `--window-title`：用于定位目标窗口（窗口消息模式建议必须带上）。
- `--force-sendinput-move`：继续使用鼠标方式时，强制 `SendInput` 移动。

## 注意

- 有些游戏（尤其反作弊严格的）会屏蔽窗口消息点击；这时就只能继续用鼠标注入策略调参。
