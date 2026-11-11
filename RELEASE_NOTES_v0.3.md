# v0.3 — 实时预览 / Live font preview

## Windows 64-bit portable download

下载下方 SloganGenerator-v0.3-windows-x64.zip，完整解压，双击 SloganGenerator.exe。无需 Python，请保留 _internal 文件夹。

Download the ZIP below, extract it completely, and run SloganGenerator.exe. No Python installation is required. Keep the _internal folder.

- 启动语言选择页，支持 18 种界面语言 / 18 interface languages.
- 自动读取已安装字体 / Automatically discovers installed fonts.
- 自定义文字、颜色、字高、厚度和加粗 / Custom text, color, height, depth and weight.
- 实时平面字形预览 / Live flat font preview.
- 生成固定立体建筑，复制到游戏 workshop_wip 后重启 / Generates fixed 3D buildings for the game's workshop_wip folder.

## Validation

Portable executable generation and interface checks passed with Python paths removed. Eighteen language sample models passed structural validation. Preview tests covered Chinese, accented Latin text, spaces, weight changes, colors and missing glyphs. Selected generated buildings were also shown successfully in user-provided in-game screenshots; this is not a claim that every font or output has been tested in game.

SHA256SUMS.txt provides the download checksum. This release does not include the 18 prebuilt slogan pack or the hello showcase models.

## Limitations

1–40 characters, one line. TTC uses the first font; complex shaping and color emoji are unsupported. T_ cannot edit generated text. Workshop IDs are local placeholders. Public sharing of models remains subject to the selected font's license. See the repository README for details.
