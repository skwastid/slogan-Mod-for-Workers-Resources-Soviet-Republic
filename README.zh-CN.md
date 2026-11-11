# Slogan Mod for Workers & Resources: Soviet Republic

[English](README.md)

把电脑里的字体变成《工人与资源：苏维埃共和国》可放置的立体标语建筑。

## 玩家下载

从 [Releases](https://github.com/skwastid/slogan-Mod-for-Workers-Resources-Soviet-Republic/releases) 下载 Windows 64 位便携版 ZIP，完整解压后双击 `SloganGenerator.exe`。不需要安装 Python；请保留旁边的 `_internal` 文件夹。

启动后先选择界面语言，再进入生成界面。默认读取本机已安装字体，也可以选择 TTF / OTF / TTC 文件。输入文字、调整字高、厚度、颜色和额外加粗，实时预览字形后生成建筑。

把生成的数字文件夹复制到游戏 `media_soviet/workshop_wip`，重启游戏，在 MOD 建筑中查找 `Custom Slogan`。生成结果是固定立体模型，不能用游戏内的 T_ 按钮修改。

## v0.3 功能

- 18 种界面语言，启动时选择，可返回切换。
- 读取电脑已安装字体，无需导入字体包。
- 1–40 字符单行文字，支持空格和常见重音字符。
- 字高 1–30 米、厚度 0.1–5 米、颜色和额外加粗可调。
- 字形、颜色及加粗的实时平面预览；预览不是游戏内三维渲染。
- 缺字检查、模型顶点数量限制检查，不覆盖既有生成项目。

语言：简体中文、繁体中文、英语、法语、德语、波兰语、俄语、西班牙语、意大利语、日语、巴西葡萄牙语、匈牙利语、韩语、乌克兰语、保加利亚语、土耳其语、斯洛伐克语、捷克语。

## 源码运行（开发者）

需要 Windows 64 位、Python 3.11+（含 tkinter）及已安装的游戏。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tools/import_game_assets.py "D:\SteamLibrary\steamapps\common\SovietRepublic"
python app.py
```

请把示例游戏路径改成自己的路径。游戏材质从本地安装目录导入，不存入 Git；工具不需要管理员权限。

## 构建便携版

在以上环境中运行：

```powershell
python -m pip install -r requirements-build.txt
.\build.ps1
```

产物：`dist/SloganGenerator-v0.3-windows-x64.zip`。规范构建应使用干净的虚拟环境。现有 Release 是此前验证过的便携构建；源码整理版调整了路径、材质导入和构建入口，功能相同。

可用的冒烟检查：

```powershell
python app.py --self-test test-output
python app.py --ui-test test-output-ui.json
```

## 使用限制

TTC 只使用第一个字体；没有复杂文字塑形、任意组合附加符号或彩色 Emoji 支持。语言支持依赖所选字体的字形覆盖。过长或复杂文字可能超过模型顶点上限。

每次生成独立的本地占位编号。发布到 Steam Workshop 时必须通过游戏创建真实项目，并保留真实 ITEM_ID / OWNER_ID；不能直接上传占位编号。生成器不会自动上传 Steam。

## 素材与许可

不打包玩家字体文件。公开分发字形模型时，请核对字体许可。游戏素材与 Python 依赖的说明见 [第三方材料说明](THIRD_PARTY_NOTICES.md)。本项目暂未指定开源许可证。

## 制作说明

由 GPT-6 Astra 协助制作。
