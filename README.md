# xFRAME808

**套框工具 / Frame Compositor** — 批次將商品圖片合成到促銷活動框架中的桌面工具。適用於電商活動素材量產。

![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## 功能

- 選擇任意框架圖片（輸入支援 PNG / JPG / WEBP，輸出固定為 PNG）
- 選擇商品資料夾，一次批次處理所有圖片
- 選擇輸出資料夾，結果自動加 `_套框` 後綴
- **即時預覽**：選好框架和資料夾後自動顯示第一張合成結果
- **位置微調**：X / Y 位移 ±300 px、縮放 50%~150%
- 批次執行時不凍結 UI，可隨時取消

## 已知限制

- `SAFE_BOX` 安全區座標為 hardcoded，預設 `(38, 145, 638, 850)`，適用於 1084×1084 的框架。若框架尺寸不同需修改 [core/compositor.py](core/compositor.py)
- macOS .app 使用 ad-hoc 簽名，首次開啟需右鍵 → 開啟
- Windows .exe 未經過 Microsoft 簽名，首次執行可能觸發 SmartScreen 警告
- 目前僅提供 Apple Silicon Mac，未支援 Intel Mac

## 平台支援

| 平台 | 架構 | 備註 |
|---|---|---|
| macOS | Apple Silicon (arm64) | macOS 12+ 建議 |
| Windows | x86_64 | Windows 10 / 11 |

> ⚠️ **目前 macOS 版僅支援 Apple Silicon（M1/M2/M3/M4）**。Intel Mac 使用者請從原始碼執行，或等待後續 universal2 支援。

## 下載

前往 [Releases](../../releases/latest) 下載最新版：

- **macOS（Apple Silicon）**：`xFRAME808-macOS.zip`
- **Windows**：`xFRAME808-Windows.zip`

### macOS 首次開啟

下載後解壓縮，**右鍵點擊 `xFRAME808.app` → 開啟**（第一次），之後就能正常雙擊。
若出現「無法驗證開發者」警告，在終端機執行：

```bash
xattr -cr /path/to/xFRAME808.app
```

### Windows 首次開啟

下載後解壓縮，雙擊 `xFRAME808.exe`。若 Windows Defender SmartScreen 攔截，點選「其他資訊」→「仍要執行」。

## 使用方式

1. 啟動 app
2. 點「選擇檔案...」選擇框架圖片（例：活動框架 PNG）
3. 點「選擇資料夾...」選擇放商品圖的資料夾
4. 點「選擇資料夾...」選擇輸出資料夾
5. 預覽區會自動顯示第一張合成結果
6. 需要時調整 X/Y 位移或縮放
7. 點「開始套框」開始批次處理

## 安全區設定

目前 `SAFE_BOX` 預設為 `(38, 145, 638, 850)`（針對 1084×1084 的框架）。若使用其他尺寸的框架，可於 [core/compositor.py](core/compositor.py) 修改。

## 從原始碼執行

需要 Python 3.12+。

```bash
git clone https://github.com/0xlab-co/xframe808.git
cd xframe808
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 自行打包

### macOS

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed \
  --name "xFRAME808" \
  --osx-bundle-identifier "com.0xlab.xframe808" \
  main.py
# 產出 dist/xFRAME808.app
```

### Windows

```cmd
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "xFRAME808" main.py
REM 產出 dist\xFRAME808\xFRAME808.exe
```

或使用內建的 [scripts/build_win.bat](scripts/build_win.bat)。

## 專案結構

```
├── main.py                 # 進入點
├── core/
│   └── compositor.py       # 圖片合成邏輯（無 GUI 相依）
├── ui/
│   ├── main_window.py      # 主視窗
│   └── worker.py           # 背景執行緒
├── scripts/
│   └── build_win.bat       # Windows 打包腳本
├── .github/workflows/
│   └── build.yml           # GitHub Actions 自動打包
└── requirements.txt
```

## 技術棧

- [PySide6](https://pypi.org/project/PySide6/) — Qt 6 GUI
- [Pillow](https://pypi.org/project/Pillow/) — 圖片處理
- [PyInstaller](https://pyinstaller.org/) — 打包

## License

[MIT](LICENSE)
