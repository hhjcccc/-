# 游戏宝箱双界面自动点击（Python）

根据你的流程：
1. **界面一**点击红框“打开”按钮。  
2. 切到**界面二**后点击红框“收集”按钮。  
3. 然后又回到界面一，循环往复。

本脚本会同时识别两个按钮，且默认优先点“收集”（避免弹窗停住）。

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Windows 把 `source .venv/bin/activate` 换成 `.venv\\Scripts\\activate`。

## 2) 准备两张模板图

你需要准备两张小图：

- `assets/open_btn.png`：界面一里红框“打开”按钮（建议只裁按钮本体）
- `assets/collect_btn.png`：界面二里红框“收集”按钮

建议：
- 尽量只保留按钮，不要裁太多背景。
- 每张模板大小建议 80~400 像素宽。
- 模板来自你实际运行分辨率（2560x1600）时的截图，匹配更稳。

## 3) 运行

```bash
python auto_clicker.py \
  --open-template assets/open_btn.png \
  --collect-template assets/collect_btn.png \
  --open-threshold 0.84 \
  --collect-threshold 0.84 \
  --interval 0.20
```

## 4) 推荐参数（你的场景）

先用 dry-run 调试：

```bash
python auto_clicker.py \
  --open-template assets/open_btn.png \
  --collect-template assets/collect_btn.png \
  --dry-run \
  --region 1500 1150 950 500
```

说明：
- `--region` 可以把识图范围限制在按钮附近，速度更快、误点更少。
- 对 2560x1600，这个区域通常覆盖右下角按钮区域（可按你的窗口微调）。

常用参数：
- `--max-clicks 500`：跑到 500 次自动停止。
- `--gray`：灰度匹配，速度更快。
- `--scales 0.9,1.0,1.1`：模板多尺度匹配，适合窗口缩放时使用。
- `--debug-dir debug_hits`：每次命中保存截图，便于排查。

## 5) 安全与稳定性

- 鼠标快速移动到左上角可触发 `pyautogui` failsafe，立即中断。
- 游戏可能有反自动化策略，请先确认规则允许。
- 若独占全屏模式截屏不稳定，可改为无边框窗口。
