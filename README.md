# 游戏宝箱双界面自动点击（Python）

你现在这个日志特征是：
- `open` 会命中多个位置（例如 `1048` 和 `1746`）。
- 有时点完后并没有稳定进入下一界面。  
这通常是**误识别命中**导致（不是单纯点击失败）。

这版新增两类稳态控制：
1. `--open-region` / `--collect-region`：给两个按钮单独限定识图区域。
2. `--confirm-hit-frames`：要求连续命中 N 帧后再点击，过滤抖动误命中。

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

> 以下区域是按你 2560x1600 场景的示例，可按实际微调。

```bash
python auto_clicker.py \
  --use-native-win32-input \
  --auto-fallback-window-message \
  --window-point-priority \
  --window-title "Pixel Gun 3D" \
  --open-region 1500 1100 900 500 \
  --collect-region 900 1050 900 500 \
  --confirm-hit-frames 2 \
  --message-repeat 3 \
  --message-delay 0.01
```

## 新参数说明

- `--open-region LEFT TOP WIDTH HEIGHT`：只在该区域匹配 open。
- `--collect-region LEFT TOP WIDTH HEIGHT`：只在该区域匹配 collect。
- `--confirm-hit-frames 2`：同一位置连续命中 2 帧才点击。

## 备注

- 如果游戏管理员运行，脚本也请管理员运行。
