r"""准备 UML 渲染环境：中文字体 + PlantUML jar + jdk4py。

只需在有网的环境跑一次：

    .\.venv\Scripts\python.exe scripts\setup_uml.py

脚本幂等：已存在的文件会跳过。
"""
from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = PROJECT_ROOT / ".tools" / "fonts"
FONT_NAME = "NotoSansSC-VariableFont_wght.ttf"
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"
)
JAR_DIR = PROJECT_ROOT / ".tools" / "plantuml"
JAR_PATH = JAR_DIR / "plantuml.jar"
JAR_URL = "https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar"
PIP_PACKAGES = ("jdk4py",)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def download(url: str, dest: Path, label: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        print(f"下载 {label} …")
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180
        ) as resp, open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                fh.write(chunk)
        tmp.replace(dest)
        print(f"  ✓ {dest.relative_to(PROJECT_ROOT)}  {dest.stat().st_size / 1e6:.1f} MB")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ 失败：{type(exc).__name__} {exc}")
        if tmp.exists():
            tmp.unlink()
        return False


def pip_install(packages) -> bool:
    print(f"安装依赖 {' '.join(packages)} …")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", *packages],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout[-1500:])
        print(proc.stderr[-1500:])
        return False
    print("  ✓ 依赖就绪")
    return True


def check_module(name: str) -> bool:
    proc = subprocess.run(
        [sys.executable, "-c", f"import {name}"], capture_output=True, text=True
    )
    return proc.returncode == 0


def main() -> int:
    ok = True

    print("== 1/3 Python 依赖（jdk4py：自带 JRE）==")
    missing = [p for p in PIP_PACKAGES if not check_module(p)]
    if missing:
        ok = pip_install(missing) and ok
    else:
        print("  ✓ 已安装")

    print("== 2/3 中文字体（Noto Sans SC, OFL）==")
    font = FONT_DIR / FONT_NAME
    if font.exists():
        print(f"  ✓ 已存在 {font.relative_to(PROJECT_ROOT)}")
    else:
        ok = download(FONT_URL, font, "Noto Sans SC 字体") and ok

    print("== 3/3 PlantUML jar ==")
    if JAR_PATH.exists():
        print(f"  ✓ 已存在 {JAR_PATH.relative_to(PROJECT_ROOT)}")
    else:
        ok = download(JAR_URL, JAR_PATH, "PlantUML") and ok

    print()
    if not ok:
        print("环境未完全就绪，请按上面提示手动处理后重试。")
        return 1

    print("环境就绪。渲染 UML：")
    print("  .\\.venv\\Scripts\\python.exe scripts\\render_uml.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
