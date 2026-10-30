r"""PlantUML 本地渲染器（含中文字体）。

为什么不是在线服务：kroki.io / plantuml.com 的 PlantUML 服务器不带中文字体，
中文会全部渲染成豆腐块（□）。这里用 jdk4py（Python 包内自带 JRE）+ 本机 PlantUML
jar + 项目内置 Noto Sans SC 字体离线渲染，中文可正确显示。

首次使用需要准备两样东西（脚本会自动检测并给出下载命令）：

    # 1) 中文字体（Open Font License，可自由分发）
    .\.venv\Scripts\python.exe scripts\setup_uml.py

    # 2) 渲染
    .\.venv\Scripts\python.exe scripts\render_uml.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = PROJECT_ROOT / ".tools" / "fonts"
FONT_NAME = "NotoSansSC-VariableFont_wght.ttf"
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"
)
JAR_CANDIDATES = (
    PROJECT_ROOT / ".tools" / "plantuml" / "plantuml.jar",
    PROJECT_ROOT / ".tools" / "plantuml" / "plantuml-asl.jar",
)
CJK_FONT_FAMILY = "Noto Sans SC"

# 所有图统一套用的皮肤参数：中文字体 + 略大的字号，便于投影/截图阅读
SKIN_PARAMS = f"""
skinparam defaultFontName "{CJK_FONT_FAMILY}"
skinparam monospacedFontName "{CJK_FONT_FAMILY}"
skinparam dpi 120
skinparam shadowing false
skinparam wrapWidth 260
skinparam maxMessageSize 220
skinparam titleFontSize 18
skinparam LegendFontSize 13
skinparam ClassFontSize 13
skinparam ClassAttributeFontSize 12
skinparam NoteFontSize 13
"""


class RenderError(RuntimeError):
    pass


def find_jar() -> Path:
    for jar in JAR_CANDIDATES:
        if jar.exists():
            return jar
    raise RenderError(
        "未找到 PlantUML jar。请下载后放到 .tools/plantuml/plantuml.jar ：\n"
        "  https://github.com/plantuml/plantuml/releases/latest"
    )


def find_font() -> Path:
    font = FONT_DIR / FONT_NAME
    if not font.exists():
        raise RenderError(
            f"未找到中文字体 {font}。\n"
            f"请下载（Open Font License）：\n  {FONT_URL}\n"
            "或直接运行：python scripts/setup_uml.py"
        )
    return font


def ensure_java_font(font: Path) -> Path:
    """把中文字体装进 jdk4py 的 JRE，PlantUML 才能取到字形。"""
    try:
        import jdk4py
    except ImportError as exc:  # pragma: no cover
        raise RenderError(
            "缺少 jdk4py（自带 JRE 的 Python 包）。请安装：\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install jdk4py"
        ) from exc

    target_dir = Path(jdk4py.JAVA_HOME) / "lib" / "fonts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "NotoSansSC.ttf"
    if not target.exists():
        shutil.copyfile(font, target)
    return target


def java_bin() -> str:
    import jdk4py

    java = Path(jdk4py.JAVA)
    if os.name == "nt" and java.suffix != ".exe":
        java = java.with_suffix(".exe")
    if not java.exists():
        raise RenderError(f"jdk4py 内的 Java 不存在：{java}")
    return str(java)


def apply_skin(source: str) -> str:
    """在 @startuml 之后插入皮肤参数，且幂等。"""
    if "skinparam defaultFontName" in source:
        return source
    marker = "@startuml"
    idx = source.find(marker)
    if idx < 0:
        return source
    end = source.find("\n", idx)
    if end < 0:
        return source
    head, rest = source[: end + 1], source[end + 1 :]
    return head + SKIN_PARAMS.lstrip("\n") + rest


def render(source: str, fmt: str = "png", timeout: int = 300) -> bytes:
    """渲染单张图，返回文件字节。"""
    jar = find_jar()
    font = find_font()
    ensure_java_font(font)

    import tempfile

    with tempfile.TemporaryDirectory(prefix="puml_") as tmp:
        src_path = Path(tmp) / "diagram.puml"
        src_path.write_text(apply_skin(source), encoding="utf-8")
        suffix = "png" if fmt == "png" else "svg"
        cmd = [
            java_bin(),
            "-Djava.awt.headless=true",
            "-DPLANTUML_LIMIT_SIZE=8192",
            "-jar",
            str(jar),
            "-t" + suffix,
            "-pipe",
        ]
        proc = subprocess.run(
            cmd,
            input=apply_skin(source).encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
        out = proc.stdout
        if proc.returncode != 0 or not out:
            err = proc.stderr.decode("utf-8", "replace")[-1500:]
            raise RenderError(f"PlantUML 渲染失败（rc={proc.returncode}）：{err}")
        return out
