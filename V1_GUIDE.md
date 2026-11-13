# v1.0 — image selection, 3D, materials and installation

Use **3D / appearance / install** from either the font screen or the image editor. The window captures the current text or repaired mask. Change letter height, depth, colour, weathering and base style there; these settings are used by its export buttons. Quick export reuses the latest appearance settings.

- **Colour extraction:** click Eyedropper, then a solid pixel inside a letter in the left image. Set Color tolerance and click Extract. Higher tolerance includes more RGB shades. This also works with Crop then extract. It is colour segmentation, not OCR: matching background colours can remain. Save projects to preserve selected colour and tolerance.
- **Brush cursor:** the repair canvas displays a ring at the brush's actual image-space size. Blue fills; red erases. The ring follows zoom and does not alter the image or export.
- **3D preview:** drag to orbit; wheel to zoom. Geometry, UV coordinates and aging textures come from the export pipeline. The simplified renderer has no game shadows or specular lighting. While dragging it uses flat materials; releasing restores full textures. Very complex silhouettes take longer to rebuild.
- **Weathering:** 0–100 controls fading, rust, paint chips and base dirt. It changes texture and material reflectivity, not mesh topology. The seed is fixed, so preview and export are reproducible.
- **Bases:** long plinth, no base, or a wall behind the text. Disconnected strokes and letters above the lowest baseline can remain unsupported; choose a wall when appropriate.
- **Install:** detect or browse to the SovietRepublic game root, then Generate & install. Alternatively export first and Install last export. The destination is `media_soviet/workshop_wip/<local ID>`. Generated project files are hash-verified; existing folders are never overwritten. No Steam login or upload is performed. Restart the game to load the new building. If copying fails, the exported building remains available to retry installation.

All generator windows support the same 18 interface languages, selected on the opening screen. Operating-system dialogs follow Windows language settings; raw technical diagnostics may retain library wording. Full projects preserve repaired pixels, extraction settings, movable character layers, appearance and camera settings. Only the current 1.0 project format is supported. Exported `generation.json` records appearance values.

Build in a clean virtual environment using pip wheels instead of the Conda/MKL stack. The build script enforces an extracted portable folder below 400,000,000 bytes. Generated buildings and images are separate user output and are not included in that budget.

## 中文使用说明

字体界面和图片编辑器均有“3D / 外观 / 导入”入口。它读取当前文字或修补结果；进入后调整字高、厚度、颜色、底座和做旧，窗口中的生成按钮会使用这些参数。主界面“快速生成”沿用最近调整的外观参数。

1. **吸管选色**：点吸管，再点击左侧文字内部颜色；调整容差后点自动提取。也可先取色再“裁剪后提取”。背景中同色物体仍可能被选中，需要修补。
2. **笔刷轮廓**：右侧蓝圈为填补、红圈为擦除，显示实际笔刷范围，跟随缩放，不会写进图片。
3. **3D 预览**：拖动旋转、滚轮缩放。拖动时显示简化材质，松开后恢复完整贴图。模型和贴图使用导出数据；预览没有游戏引擎的阴影与高光，不能保证与游戏截图完全相同。
4. **做旧**：0–100 调节褪色、锈蚀、脱漆和底座污渍；不改变文字轮廓，固定随机种子让结果可复现。
5. **底座**：长条底座、无底座、标语墙。分离笔画和字母基线差异可能造成悬空，可选择标语墙。
6. **一键导入**：自动检测游戏目录，也可浏览选择；点击“生成并导入游戏”。生成与安装分开使用也可以。仅写入本地 workshop_wip，逐文件校验，不覆盖已有建筑，不上传 Steam。完成后重启游戏。安装失败时已生成文件会保留，可修正目录后重试。

文字、图片修补、字块重排和3D窗口均支持首页选择的18种界面语言。系统对话框语言由Windows控制，底层技术错误详情可能保留库的原始文字。完整工程保存修补像素、选色参数、独立字块及3D外观和视角；只支持当前1.0工程格式；建筑目录的 generation.json 会记录生成参数。


## Projects and layout (included in 1.0)

- Save/Open `.sloganproj` from the font screen, image editor, or the Save button inside 3D/layout windows. Projects include original/working images, repaired pixels, individual letter blocks (including unapplied arrangements), typography, building name, output folder, appearance and camera. Fonts are referenced by local path and are not embedded. Select an installed font if reopening on another PC. Undo history is session-local.
- Changes are autosaved after approximately one second of inactivity to `%LOCALAPPDATA%/YourOwnBigSlogan/Recovery`. Font and image projects have separate checkpoints and a previous valid checkpoint. Use Recover to restore; the font screen also offers recovery on entry. Files use atomic replacement. Explicit saves remain independent of recovery files.
- In the lower layout view, Ctrl-click to toggle selection, drag empty space for a selection rectangle, or use the multi-select list. Drag a selected letter to move the group. Align left/right/top/bottom/centers or distribute equal horizontal/vertical edge-to-edge gaps. Scale and angle controls adjust the primary selected letter. Applied layouts retain editable blocks; later pixel painting merges them, with Undo available.
- Enter separates centered horizontal lines, or right-to-left columns in upright vertical mode. Letter height is per line; line/column spacing is adjustable from 0.5 to 4. Up to 120 characters and 12 lines, subject to the model vertex limit. Vertical characters remain upright; this is not language-specific vertical punctuation shaping.
- Building names accept up to 80 characters; quotes, backslashes and control characters are not allowed. An empty name uses an automatic name.
- Export thumbnails render the actual mesh, base, colour and weathering at a fixed camera angle, rather than drawing flat text. The 3D viewer camera is saved in the project but does not change the standard export-thumbnail angle.

## 工程与排版（均属于1.0）

- 字体页、图片页可以保存/打开完整工程，3D和重排窗口也有保存入口。保存原图、工作图、修补结果、独立字块（含未应用的排列）、排版参数、建筑名称、输出目录、外观和视角。字体只记录本地路径，不打包字体；换电脑后可重新选择。撤销历史仅限当前编辑会话。
- 停止修改约1秒后自动保存，字体和图片工程分别记录，并保留上一份有效记录；点“恢复上次”即可恢复。字体页进入时也会提示恢复。自动记录不覆盖手动保存的工程。
- 下方排列区支持Ctrl连续点选、空白处拖框、多选列表和整组拖动；可对齐边缘、居中和横向/纵向等间距。缩放、旋转调整主选中字块。应用后仍保留字块；之后使用像素笔刷会合并字块，可撤销恢复。
- Enter换行；竖排时换行创建新列，列从右到左。字高按单行计算，行/列距0.5–4；最多120字符、12行，仍受模型顶点数量限制。
- 建筑名称可自定义，最多80字符。缩略图渲染实际模型、底座、颜色和做旧，采用固定展示视角。
