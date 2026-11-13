# Image mode (v0.4 preview)

Select your language, then click **Image mode (experimental)** on the font screen.
The experimental image editor currently uses Chinese or English; the existing font screen retains its 18 languages.

1. Import a picture. Transparent pixels are composited over white; working images are limited to 1600 × 1000 pixels.
2. Select Crop and drag a rectangle on the left image. For perspective correction, select 4-point rectify and click top-left, top-right, bottom-right, bottom-left around the sign. Rectification clears the mask and can be undone.
3. Select dark or light lettering, threshold, minimum component area and optional local contrast, then Extract. Local contrast interprets threshold as contrast strength rather than an absolute brightness cutoff.
4. Edit on the right. Paint fills missing strokes, Erase removes unwanted pixels, Fill region fills a connected background region, and Erase region removes a connected foreground region. Zoom in before repairing small holes. Paint strokes interpolate between mouse positions. Undo/redo retain up to 15 edit states.
5. Use the mouse wheel or +/− to zoom, right-drag to pan, and Overlay to compare against the source image.
6. Save a `.sloganproj` file to resume editing later. Re-extracting prompts before replacing edited masks. The input file is never overwritten.
7. Check complexity. Adjust outline smoothing if needed. The exact export mesh must contain fewer than 65,536 vertices. If too complex, remove noise or split the image into separate lines.
8. Select height, depth, colour and output directory, then Generate building. Copy the numeric folder to `media_soviet/workshop_wip` and restart the game.

This is silhouette tracing, not OCR or historical reconstruction. Damaged strokes require manual repair. Disconnected marks may float above the base. The preview displays the editable pixel mask; outline smoothing is applied on export. Weathering textures are not included in this editor preview. Generated IDs are local placeholders, not Workshop upload IDs.

## 图片模式使用说明

选择语言后，在字体生成界面点击“图片生成（实验）”。新图片编辑窗口目前为中文或英文。

先导入图片，在左侧裁剪；有倾斜时用“四点校正”，依次点击标语区域左上、右上、右下、左下四角。选择黑字或白字，调整阈值与去杂点面积，再自动提取。复杂光照可尝试“局部对比”。

右侧用填补笔刷补齐断笔，用擦除笔刷清理背景；区域填充可填掉碎孔，删除区域可去掉一块孤立噪点。滚轮缩放、右键拖动平移，勾选“叠加原图”辅助描修。支持撤销/重做，以及保存工程后继续修改。重新提取会先提醒，并可撤销。

生成前检查复杂度；过于复杂时增加平滑、清理噪点或拆行。预览是编辑蒙版，平滑在导出时应用。字高、厚度与颜色可调。输出的数字文件夹放到游戏 `media_soviet/workshop_wip`，重启后加载。此版本未整合旧化贴图，分离的笔画和标点可能悬空。

## Select letters and arrange live

The upper canvas is the selection source; the lower canvas shows the actual layout. Drag a rectangle or click successive polygon vertices, then double-click or use Close polygon. Blue pixels show exactly which remaining strokes are selected. Click Add to layout to extract them as one piece. Already extracted source pixels are grey; the currently selected piece is teal.

Click a red piece in the lower preview to select it, then drag to move it. Drag its bottom-right square to scale or its upper circle to rotate. Scale and rotation sliders/entries update live around the piece centre. Undo/redo cover extraction, movement and transforms. Return to source restores the original pixels so a piece can be selected again. Wheel zooms around the cursor; right drag pans each view independently. Fit views recentres them.

One row / align bottoms orders pieces by extraction order, with 12 pixels of spacing. Keep uncut pixels includes remaining source strokes in the result; disable it to export only extracted pieces. Apply merges the layout into a tightly cropped mask, maximum 1600 × 1000 pixels. The main editor can undo the application. Save the original project separately to retain the photo. Projects retain merged pixels, not individual layers.

### 选字与实时排列

上方选字、下方实时预览。拖动矩形框选，或沿轮廓连续点击、双击完成多边形。蓝色笔画就是选区，点击“加入排列”后成为独立字块。已拆出的原图笔画变灰，当前选中字块在上方显示为青色。

下方点击红字即可选中，直接拖动位置；拖右下角方块缩放，拖上方圆点旋转。比例、旋转滑块和输入框实时生效，变换以字块中心为基准。支持撤销、重做，“放回上方原图”可恢复原笔画并重新选字。滚轮围绕鼠标缩放，右键平移，上下视图独立。

“排成一行”按拆字顺序排列、底部对齐，间隔 12 像素。“保留未拆部分”控制是否输出剩余原图笔画。应用后合并为像素图并收紧边界，可返回主窗口继续修补、保存或生成建筑。完整工程保留原照片和独立字块，再次进入重排可继续编辑；后续像素修补会合并字块，可撤销恢复。

## Crop then extract

Import or open the full image, click **Crop then extract**, and drag a rectangle on the left around the slogan. Releasing runs extraction on the crop using the current threshold, polarity and noise settings. One undo restores the full image and previous mask. For small poster lettering, try Noise area 2 to avoid discarding punctuation and thin strokes. Cropping isolates the region but cannot restore lost image detail.

“裁剪后提取”：导入整张图片，点击按钮，在左侧拖框圈住标语，松开后自动提取。使用当前黑/白字、阈值及去杂点设置；一次撤销即可恢复完整图片与原修补结果。低分辨率海报建议先将去杂点面积设为 2，避免删除小笔画。裁剪不会恢复原图中缺失的细节。
