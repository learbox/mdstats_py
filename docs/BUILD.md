# EXE 打包说明

## 前置条件

- Python ≥ 3.11
- PyInstaller（项目 venv 中已安装）
- uv（可选，用于同步依赖）

## 打包步骤

### 1. 同步依赖

```bash
uv sync
```

### 2. 执行打包

```bash
.venv/Scripts/pyinstaller.exe MDStats.spec --noconfirm
```

打包产物在 `dist/MDStats/` 目录。

### 3. 组装发布目录

themes、csv、resource、config 等需要放在 exe 同级目录（不打包进 exe），以便用户自行修改。

```bash
mkdir -p dist/release
cp dist/MDStats/MDStats.exe dist/release/
cp -r dist/MDStats/.runtime dist/release/
cp -r themes dist/release/
cp -r csv dist/release/
cp -r resource dist/release/
cp config.toml dist/release/
cp .app_state.json dist/release/
cp docs/README_release.md dist/release/README.md
```

### 4. 打包为 ZIP

```bash
cd dist/release
python -c "
import zipfile, os
with zipfile.ZipFile('../MDStats-vX.Y.Z.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        for f in files:
            fp = os.path.join(root, f)
            if f.endswith('.pyc') or '__pycache__' in fp:
                continue
            arcname = os.path.relpath(fp, '.')
            zf.write(fp, arcname)
"
```

将 `vX.Y.Z` 替换为实际版本号。

## 发布包结构

```
MDStats/
├── MDStats.exe              # 主程序
├── .runtime/                # 运行时依赖（PyInstaller 生成）
├── config.toml              # 配置文件
├── .app_state.json          # 窗口状态持久化
├── csv/                     # 对战数据
├── resource/templates/      # 模板图片
├── themes/                  # 主题目录（用户可自定义）
└── README.md                # 用户说明（来自 docs/README_release.md）
```

## 注意事项

- `themes/` 不打包进 exe，用户可以自行添加/修改主题
- `csv/` 和 `resource/` 同样放在外部，用户可自行管理数据
- `MDStats.spec` 中 `datas` 只包含 `ui/main_window.ui`，不要加入 themes 等目录
- 打包前确认 `ui/meta.py` 中的版本号已更新
