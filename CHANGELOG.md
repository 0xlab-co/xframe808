# Changelog

本檔記錄 xFRAME808 的版本改動。格式參照 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [3.3.0] - 2026-04-23

本版改動微調模型：原本側邊欄單一全域「位置微調」被拆成**前景 / 後景 / 商品**三組獨立微調，商品微調並以每張檔案各自保存位置。右側預覽新增商品縮圖列，可直接點選要獨立調整的商品。

### Added

#### 每層 / 每商品獨立微調
- 新增 `LayerTransform` dataclass（`offset_x`、`offset_y`、`scale`）與 `IDENTITY_TRANSFORM`，取代舊版全域 `offset_x / offset_y / scale` scalar。
- 前景套框、後景底圖各自擁有一組 `LayerTransform`，整批商品共用；以畫布中心為錨點縮放，位移上限 ±300 px、縮放 50%~150%。
- 商品微調以 `dict[Path, LayerTransform]` 依檔案路徑保存；切換縮圖時自動帶出該張商品上次的位移 / 縮放。
- `core/compositor.py` 的 `build_composite_frame` / `build_composite` / `build_layer_preview` / `batch_composite` / `_process_video_product` 全部改吃 `background_transform` / `foreground_transform` / `product_transform(s)` kwargs；`CompositeWorker` 同步換簽章。
- 切換 preset 或輸入資料夾時會自動清除全部微調（位移單位是畫布像素，跨 preset 無意義）。

#### 商品縮圖列
- 右側預覽下方新增 `ThumbnailStrip`：橫向顯示商品資料夾內所有檔案，影片以首幀作縮圖並加上小 badge。
- 點縮圖切換目前預覽的商品、同時展開商品微調面板。
- 水平捲動採 bar 式 scrollbar，滑鼠滾輪會優先轉成水平捲動，避免在縮圖列上滾到頁面。

#### 套用全部
- 商品微調面板新增「套用全部」按鈕：把目前商品的 X / Y 位移與縮放一次複製到整個商品資料夾；之後仍可回到單張商品個別覆寫。

#### 可收合面板
- 新增 `CollapsibleSection` + 統一的 `TransformPanel`（前景 / 後景 / 商品皆使用）：預設收攏，header 使用箭頭 toggle，`重置` 置於面板底部 footer，避免收攏狀態誤觸。
- 前景 / 後景微調掛在 sidebar 對應 `PathRow` 下方，並以卡片視覺分群；商品微調掛在右側預覽縮圖列下方。

#### 測試
- 新增 6 項 `LayerTransform` 相關測試：identity 與 legacy 輸出逐像素一致、背景 offset 像素驗證、前景 scale 半縮、per-path 商品字典、空字典 fallback 至 identity、`build_layer_preview` 支援 layer transforms。

### Changed

- 側邊欄移除原本單一「位置微調」區塊，滑桿控制元件改為各自緊貼其影響的圖層 / 商品，並預設收攏以減少視覺噪音。
- 批次執行中所有微調面板與滑桿會一起 disabled，取消按鈕行為不變。

### Docs

- README 補上前景 / 後景 / 商品微調的使用方式、商品縮圖列、套用全部商品的流程說明，並註明切 preset 會清除微調。
- `scripts/build_mac.sh`、`scripts/build_win.bat`、`.github/workflows/build.yml` 同步補上 `--collect-all imageio_ffmpeg`，配合 v3.2 的影片打包需求；README 影片章節同步改為「已預先帶上此參數」。

## [3.2.0] - 2026-04-22

本版加入**影片商品套框 MVP**：商品資料夾可混放靜圖與短影片，影片會逐幀套框後以原容器輸出並保留音軌。前景 / 後景維持靜圖，UI 流程無大改動。

### Added

#### 影片商品套框
- 商品資料夾支援 `.mp4`、`.mov`、`.m4v`、`.webm`；依副檔名自動走影片路徑。
- 輸出容器與輸入一致（`_套框.mp4` / `.mov` / …），codec 走容器預設：mp4/mov/m4v → H.264、webm → VP9，皆走 `yuv420p`。
- 音軌以 ffmpeg `-map 0:v:0 -map 1:a:0?` 直接 mux 原音；原 codec 與目標容器不相容時降回 AAC / libopus 重新編碼。
- 新增 `core/video.py`：`probe_video` / `iter_frames` / `read_first_frame` / `open_writer` / `mux_audio`。
- 新增 `build_composite_frame(preset_id, product_image, ...)` 作為逐幀合成的核心；`build_composite(preset_id, product_path, ...)` 改為薄 wrapper，同時自動處理影片（取首幀供預覽用）。
- `batch_composite` 新增 `frame_progress` / `cancel_check` 關鍵字參數，worker 可觀察逐幀進度並在影片處理中途取消。
- `CompositeWorker` 新增 `frame_progress` Signal；主視窗進度區塊新增「{檔名} · x/N 幀」副標籤，檔案完成時自動清除。

#### 測試
- 新增 `test_build_composite_frame_matches_build_composite`，鎖定「path → image」重構前後像素一致。
- 新增 `test_list_products_includes_video_extensions`，確認影片副檔名會被 `list_products` 收錄。

### Changed

- `SUPPORTED_EXTENSIONS` 擴張為圖片 + 影片副檔名；新增 `SUPPORTED_IMAGE_EXTENSIONS` 作為純圖片集合。
- 批次輸出：影片沿用原容器副檔名，圖片仍輸出為 `.png`。
- `_fit_product_to_preset` 內部重構為 `_place_product`（吃 PIL Image 而非 path），支援路徑 / 記憶體幀兩條輸入。
- 主視窗空資料夾提示改為「圖片或影片」。
- `requirements.txt` 新增 `imageio-ffmpeg`。

### Not in Scope

刻意延後到後續版本：
- 替換 / 靜音音軌的 UI 欄位（`mux_audio` 介面已可用，只差 UI）。
- 解析度 / bitrate / CRF / 強制轉碼到指定容器等輸出微調。
- 動態前景 / 後景框（MP4 / GIF）。
- `.avi` / `.mkv` 等較冷門容器。
- 影片旋轉 metadata 自動校正（直式影片請於來源端事先轉正）。

### Packaging Notes

- `imageio-ffmpeg` 內建 ffmpeg binary（約 70 MB），PyInstaller 打包需補上 `--collect-all imageio_ffmpeg`；`scripts/build_mac.sh`、`scripts/build_win.bat` 與 `.github/workflows/build.yml` 已同步此參數。
- Installer / 綠色版體積會因此變大，首次開啟仍受 macOS Gatekeeper / Windows SmartScreen 限制（與既有版本相同）。

## [3.1.0] - 2026-04-22

### Added

- Windows 版新增 `xFRAME808-Windows-Setup.exe` 安裝檔（由 [Inno Setup 6](https://jrsoftware.org/isinfo.php) 打包）：雙擊安裝、自動建立開始選單 / 選擇性桌面捷徑、可從「新增移除程式」乾淨解除。
- 新增 `scripts/installer.iss` Inno Setup 腳本，版本號由 CI 從 git tag 自動注入（`/DAppVersion=x.y.z`）。

### Changed

- GitHub Actions `build.yml` Windows job 在既有 zip 之外，加一步 Inno Setup 編譯，Release 同時上架 `.exe` installer 與 `.zip` 綠色版。
- README 首次開啟 / 下載段落改為先推 installer，再說明綠色版注意事項（資料夾不可拆、需用捷徑）。
- `scripts/build_win.bat` 加上本機 Inno Setup 指令提示。

### Notes

- Installer 本身未簽章，首次執行仍會觸發 Windows SmartScreen 警告（同綠色版）；徹底解除需購買 Authenticode 憑證，屬於後續決策，不在本版範圍。

## [3.0.0] - 2026-04-22

本版為 UI 全面重構：從原本的單欄表單升級為 sidebar + 預覽雙欄佈局，並加入任意尺寸圖層裁切流程。同時切換至 warm cream light 主題。

### Added

#### 介面重構
- 新主視窗採「左側 sidebar（圖層 / 資料夾 / 位置微調）+ 右側即時預覽」雙欄佈局。
- sidebar 寬度固定 408 px，可捲動，底部固定 sticky action 區（狀態膠囊 + 進度條 + 主要動作按鈕）。
- 預覽區採淺米色底 + 格紋 matte，隨輸出比例自動鎖定 aspect ratio。
- 全新 warm cream light 主題：奶米底、暖棕字、赤褐 terracotta accent，取代原本深色主題。
- 導入 inline SVG icon 系統（feather-style），走 `QSvgRenderer.paintEvent` 直接繪製，DPR-safe 且依 widget 實際大小自適應。
- 新增 `ui/theme.py`、`ui/icons.py`、`ui/widgets.py`、`ui/preview.py` 四個模組。

#### 圖層裁切
- 新增 `CropDialog`：可視化裁切對話框，以目前輸出比例鎖定裁切框比例，支援拖曳移動與四角縮放。
- 匯入前景 / 後景時若比例不符目前 preset，自動跳出裁切視窗，不再直接拒絕。
- 每個圖層獨立保留裁切設定；`PathRow` 上新增「裁切」與「移除」按鈕，可隨時重新調整或清掉單一圖層。
- 切換 preset 時保留原始檔案選取，提示使用者重新裁切。
- 新增 core 層 `apply_crop_box()` 與 `CropBox` 型別，`load_layer` / `load_layers` / `batch_composite` / `CompositeWorker` 串接 crop box 參數。

#### 圖層預覽
- 新增 `build_layer_preview()`：未選商品資料夾時，可先預覽前 / 後景圖層合成結果，方便確認素材是否正確。
- `MainWindow` 在尚未選擇商品資料夾但已選到圖層時，改顯示圖層預覽而非錯誤訊息。

#### 測試
- 新增 `test_load_layer_accepts_crop_box_from_wrong_ratio_image`、`test_build_layer_preview_flattens_layers_without_product`、`test_batch_composite_accepts_crop_box_for_wrong_ratio_background` 三個案例，覆蓋裁切 + 圖層預覽路徑。

### Changed

- `load_layer` / `load_layers` 新增 `crop_box` / `background_crop_box` / `foreground_crop_box` 參數。
- `batch_composite` 與 `CompositeWorker` 同步擴充 crop box 欄位。
- `MainWindow` 大幅改寫：狀態邏輯改以 `_layer_crops` dict 管理每層各 preset 的裁切框；預覽 pipeline 拆出 `_update_preview` 與 `build_layer_preview` 兩路。
- 行為按鈕文案與 icon 改為雙語（中文 + 英文小字），sticky action 以 terracotta 實色強調。
- README 更新：新增「圖層裁切與移除」段、調整「使用方式」步驟與已知限制。

### Not in Scope

- 商品安全區編輯器（持續延後）
- 自由輸出比例 / 自訂畫布尺寸
- 跨 preset 自動重映射裁切框（目前切 preset 需使用者重新裁切）
- 文字建議 / 字型 / 樣式控制（Roadmap 項目）

## [2.0.0] - 2026-04-22

本版整併了 v2.0「多景套框與比例 Preset」與 v2.1「自動去白底與白底輸出」兩階段升級。

### Added

#### 比例 Preset 系統
- 新增 `LAYOUT_PRESETS` 固定四組輸出比例，以按鈕列切換：
  - `1:1` → `1080 × 1080`
  - `9:16` → `1080 × 1920`
  - `16:9` → `1920 × 1080`
  - `3:4` → `1080 × 1440`
- 每個 preset 內建商品安全區（`safe_box`）：
  - `1:1`：沿用舊版 `1084` 座標，按比例 scale 到 `1080` 畫布。
  - `9:16`：左右 10%、上下 14% 邊距置中。
  - `16:9`：左右 11%、上下 12% 邊距置中。
  - `3:4`：左右 10%、上下 13% 邊距置中。

#### 多景合成模型
- 合成順序固定為「後景 → 商品 → 前景」。
- UI 新增獨立的 `後景底圖` 與 `前景套框` 欄位，兩者可任選其一或同時使用（至少一個）。
- 前景/後景可為任意像素尺寸，只要寬高比符合所選 preset（容許 ±0.5% 誤差），程式會自動正規化到固定輸出畫布。
- 比例不符合時，預覽直接提示錯誤、批次不執行。

#### 自動去白底（前景）
- 新增 `remove_edge_connected_near_white`：以 BFS 從圖片四邊往內掃描，只清除與邊界連通的近白區域，保留中間的白色文字或裝飾。
- 近白判定固定為每通道 `>= 245`（`NEAR_WHITE_THRESHOLD`），不開放使用者調整。
- 去白底僅作用於前景層，商品圖與後景層維持原狀。
- 去白底在正規化到 preset 畫布之前完成，避免放大後白邊更明顯。

#### 白底 Flatten 輸出
- 新增 `flatten_on_white`：將合成結果疊在純白 `#FFFFFF` 底上，抹除任何殘餘透明。
- `build_composite` 回傳值一律為已補白的最終圖像。
- 預覽與匯出 PNG 內容皆為完全不透明的白底實圖。

#### 測試
- 新增 `tests/test_compositor.py`，覆蓋 11 個核心案例：多 preset 合成、單前景/單後景/雙層、比例驗證、透明邊界裁切、去白底保留內部白色、透明背景補白、同比例不同像素正規化等。

### Changed

- `build_composite(...)` 介面調整為接收 `preset_id`、`background`、`foreground`、`offset_x/y`、`scale`。
- `batch_composite(...)` / `CompositeWorker` 同步改為傳遞 `preset_id` 與前/後景路徑；取消模型不變。
- UI 主視窗加入比例按鈕列、兩個圖層檔案選擇器，並加入 layer cache 避免重複執行去白底運算。
- 預覽採 40ms debounce timer，合併連續滑桿事件。
- README 更新：說明比例 preset、透明處理規則、macOS Gatekeeper（Sequoia+）解除方式。

### Not in Scope

刻意不做的項目（延後或永不）：
- 商品安全區編輯器（v2.x 再評估）
- 自訂輸出比例 / 自由畫布尺寸
- 設定檔存取、preset 命名管理
- 文字建議輸入、系統字型、文字樣式（列為 Roadmap）
- 智慧去背、陰影分離、白邊進階消除
- 非純白的補底色選項

## [1.0.0] - 2026-04-16

- 初版：單一 1:1 正方形框、批次套框、macOS/Windows 打包。
