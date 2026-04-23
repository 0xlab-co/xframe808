# xFRAME808

**套框工具 / Frame Compositor** — 批次將商品圖片或短影片合成到促銷活動框架中的桌面工具。適用於客服與電商後台快速量產活動素材。

![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## 功能

- 支援四種固定輸出比例：`1:1`、`9:16`、`16:9`、`3:4`
- 商品可為靜圖或**短影片**（`.mp4` / `.mov` / `.m4v` / `.webm`）；影片逐幀套框後以原容器輸出、保留音軌
- 可分別選擇**後景底圖**與**前景套框**，也可只使用其中一層
- 前景 / 後景圖片可直接匯入任意像素尺寸；若比例不符合目前 preset，可立即裁切到指定比例後再使用
- 前景 / 後景各自支援**裁切**與**移除**，可在同一個工作階段快速切換活動素材
- 前景套框可直接使用白底或透明素材，程式會自動移除外圍近白背景
- 最終預覽與輸出會自動補成白底實圖，不保留透明區
- 選擇商品資料夾，一次批次處理所有商品（圖片或影片）
- 選擇輸出資料夾，結果自動加 `_套框` 後綴
- **即時預覽**：只選前景 / 後景時可先預覽圖層結果；選好商品資料夾後會自動顯示第一筆商品的合成結果（影片取首幀）
- **位置微調**：前景、後景、商品各自支援 X / Y 位移 ±300 px、縮放 50%~150%
- **商品縮圖列**：可快速切換單一商品預覽，商品微調會記住每張商品各自的位置設定
- **套用全部商品**：可把目前商品的微調結果一次套用到整個商品資料夾，之後仍可再對單張商品個別覆寫
- 批次執行時不凍結 UI，可隨時取消（影片亦可在處理中途取消）
- 介面採 warm cream light 風格，預覽區使用淺米格紋顯示畫布範圍

## 已知限制

- 商品安全區目前為內建 preset，尚未提供自訂商品區編輯
- 目前僅支援固定比例 preset，不支援自由輸出比例或自訂畫布尺寸
- 圖層裁切目前以「目前輸出比例」為基準，切換到其他 preset 時需依需要重新裁切
- 前景白底處理僅針對外圍連通的近白背景，不是完整智慧去背
- 影片僅支援不透明來源；前景 / 後景仍為靜圖，尚未支援動態框或 GIF
- 影片音軌目前只能保留原音，替換 / 靜音 UI 與 bitrate / codec 微調列入 roadmap
- 影片旋轉（rotation metadata）不會自動校正，直式影片請於來源端事先轉正
- 文字建議 / 系統字型功能尚未實作，先列入 roadmap
- macOS .app 使用 ad-hoc 簽名，首次開啟需解除 Gatekeeper 隔離
- Windows installer / .exe 未經過 Microsoft 簽名，首次執行仍會觸發 SmartScreen（需按「仍要執行」）
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
- **Windows（推薦）**：`xFRAME808-Windows-Setup.exe` — 安裝檔，自動建立捷徑、可從「新增移除程式」乾淨解除
- **Windows（免安裝版）**：`xFRAME808-Windows.zip` — 進階使用者用的綠色版，整個資料夾不能拆

### macOS 首次開啟

app 未經 Apple 簽章，macOS Gatekeeper 會阻擋。任選一種方式解除：

**方法 A — 終端機解除隔離（推薦，最快）**

下載並解壓縮後，在終端機執行：

```bash
xattr -cr ~/Downloads/xFRAME808.app
```

之後就能正常雙擊開啟。（若 .app 不在 Downloads，把路徑改成實際位置）

**方法 B — 系統設定手動允許**

1. 雙擊 `xFRAME808.app`，出現 *"Apple could not verify..."* 警告時按 **Done**
2. 開啟「系統設定」→「隱私權與安全性」
3. 捲到底部「安全性」區塊，點 **仍要打開 (Open Anyway)**
4. 輸入密碼確認

> macOS 13 及更早版本也可用「右鍵 → 開啟」繞過，但 macOS 15 Sequoia 起此方式失效。

### Windows 首次開啟

**方法 A — 使用安裝檔（推薦）**

1. 下載 `xFRAME808-Windows-Setup.exe`
2. 雙擊，若 SmartScreen 攔截 → 點「其他資訊」→「仍要執行」
3. 依精靈步驟完成安裝（可選擇是否建立桌面捷徑）
4. 從開始選單 / 桌面啟動；日後要移除從「新增移除程式」即可乾淨解除

**方法 B — 綠色版 zip**

下載 `xFRAME808-Windows.zip`，解壓縮後**整個 `xFRAME808\` 資料夾**要保留，雙擊裡面的 `xFRAME808.exe`。若 SmartScreen 攔截 → 點「其他資訊」→「仍要執行」。

> ⚠️ 綠色版不能把 `xFRAME808.exe` 搬出資料夾單獨使用，因為它需要同層 `_internal\` 裡的 Python / Qt DLL。想在桌面有圖示，對 .exe 右鍵 → 建立捷徑。

## 使用方式

1. 啟動 app
2. 選擇輸出比例：`1:1`、`9:16`、`16:9` 或 `3:4`
3. 點「選擇...」選擇後景底圖、前景套框，或兩者都選
4. 若圖片比例不符合目前 preset，會自動跳出裁切視窗；之後也可隨時點「裁切」重新調整
5. 若暫時不需要某一層，點「移除」即可清掉目前選取的前景或後景
6. 只要選到前景 / 後景，右側就會先顯示目前圖層預覽
7. 點「選擇...」選擇放商品（圖片或影片）的資料夾
8. 點「選擇...」選擇輸出資料夾
9. 預覽區會自動顯示第一筆商品的合成結果（影片取首幀）
10. 需要時可分別展開前景 / 後景微調，調整各自的 X/Y 位移與縮放
11. 商品資料夾選好後，可在右側縮圖列切換單張商品，再用「商品微調」調整該商品的位置
12. 若目前商品的位置想同步到整批商品，可在「商品微調」按「套用全部」；之後仍可回到單張商品再個別調整
13. 點「開始套框」開始批次處理；影片處理時會額外顯示「{檔名} · x/N 幀」進度

> 前景 / 後景圖片不需要剛好符合 preset 像素尺寸，只要寬高比相符即可；比例不符時會跳出裁切視窗先調整。
>
> 前景可以直接使用白底素材，程式會自動去除外圍近白背景；後景若帶透明，最後輸出也會自動補成白底實圖。
>
> 商品影片會逐幀套框並以原容器輸出（`.mp4` → `.mp4`…），音軌直接 mux 原始音訊；若原 codec 與容器不相容，程式會降回容器預設（mp4/mov/m4v → AAC、webm → Opus）重新編碼。

## 圖層裁切與移除

- 裁切視窗會先顯示原始圖片，並以目前輸出比例鎖定裁切框比例
- 可拖曳裁切框移動，也可拖曳四角調整範圍
- 點「套用裁切」後，該圖層會以裁切結果參與預覽與批次輸出
- 點「移除」會清掉目前圖層與該圖層的裁切設定，不影響另一層
- 若尚未選商品資料夾，右側預覽會先顯示純圖層合成結果，方便確認前 / 後景是否正確

## 微調流程

- 前景微調、後景微調為整批共用設定；調整後會套用到所有商品
- 商品微調為單張商品設定；切換縮圖時會保留各商品自己的位置
- 「套用全部」會把目前這張商品的微調值複製到整個商品資料夾
- 套用全部後，仍可回到個別商品再做不同的微調覆寫
- 每個微調面板都可收合，`重置` 按鈕位於面板底部

## 比例 Preset

內建四組固定輸出畫布與商品安全區：

- `1:1` → `1080 × 1080`
- `9:16` → `1080 × 1920`
- `16:9` → `1920 × 1080`
- `3:4` → `1080 × 1440`

商品安全區目前固定寫在 [core/compositor.py](core/compositor.py) 中，`1:1` 沿用舊版版位，其餘比例採置中預設框。

## 透明處理規則

- **前景套框**：自動移除從圖片邊界連通的近白背景，保留中間白色文字或裝飾
- **後景底圖**：不自動去背，透明區可保留參與合成
- **最終輸出**：不論素材是否含透明，預覽與匯出都會自動補成白底實圖

## Roadmap

- 文字建議輸入
- 使用系統已安裝字型
- 文字大小 / 位置 / 樣式控制
- 影片音軌替換 / 靜音選項
- 影片 bitrate / codec / 解析度微調
- 動態前景框（MP4 / GIF）支援

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

> 影片功能需要把 `imageio-ffmpeg` 內附的 ffmpeg binary 一起打包進 app。手動執行 `pyinstaller` 時請記得加上 `--collect-all imageio_ffmpeg`；沒加會跑起來但一碰到影片就炸。`scripts/build_mac.sh`、`scripts/build_win.bat` 與 `.github/workflows/build.yml` 已預先帶上此參數。

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed \
  --name "xFRAME808" \
  --osx-bundle-identifier "com.0xlab.xframe808" \
  --collect-all imageio_ffmpeg \
  main.py
# 產出 dist/xFRAME808.app
```

### Windows

```cmd
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "xFRAME808" --collect-all imageio_ffmpeg main.py
REM 產出 dist\xFRAME808\xFRAME808.exe
```

或使用內建的 [scripts/build_win.bat](scripts/build_win.bat)。

要額外產出 `Setup.exe` 安裝檔，請先安裝 [Inno Setup 6](https://jrsoftware.org/isinfo.php)（免費），再執行：

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=3.2.0 scripts\installer.iss
REM 產出 dist\installer\xFRAME808-Windows-Setup.exe
```

## 專案結構

```
├── main.py                 # 進入點
├── core/
│   ├── compositor.py       # 比例 preset、圖層裁切、圖片正規化與合成邏輯
│   └── video.py            # 影片解碼 / 編碼 / 音軌 mux
├── tests/
│   └── test_compositor.py  # 核心合成 / 裁切測試
├── ui/
│   ├── main_window.py      # 主視窗、圖層選擇、裁切整合與預覽流程
│   ├── crop_dialog.py      # 圖層裁切對話框
│   ├── preview.py          # 預覽畫布、商品縮圖列、商品微調區
│   ├── thumbnail_strip.py  # 商品縮圖列與水平捲動行為
│   ├── widgets.py          # 共用 UI 元件
│   ├── theme.py            # warm cream light 主題 token
│   ├── icons.py            # inline SVG icon renderer
│   └── worker.py           # 背景批次執行緒
├── scripts/
│   ├── build_mac.sh        # macOS 打包腳本
│   ├── build_win.bat       # Windows 打包腳本
│   └── installer.iss       # Inno Setup installer 腳本
├── .github/workflows/
│   └── build.yml           # GitHub Actions 自動打包
└── requirements.txt
```

## 技術棧

- [PySide6](https://pypi.org/project/PySide6/) — Qt 6 GUI
- [Pillow](https://pypi.org/project/Pillow/) — 圖片處理
- [imageio-ffmpeg](https://pypi.org/project/imageio-ffmpeg/) — 內建 ffmpeg binary，負責影片解碼 / 編碼 / 音軌 mux
- [PyInstaller](https://pyinstaller.org/) — 打包

## 版本紀錄

詳見 [CHANGELOG.md](CHANGELOG.md)。

## License

[MIT](LICENSE)
