# Changelog

本檔記錄 xFRAME808 的版本改動。格式參照 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

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
