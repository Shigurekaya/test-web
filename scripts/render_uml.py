r"""把 docs/uml/*.puml 渲染成可嵌入文档的图片（本地离线渲染，中文正常）。

用法：
    .\.venv\Scripts\python.exe scripts\render_uml.py              # 渲染 svg + png
    .\.venv\Scripts\python.exe scripts\render_uml.py --check      # 只校验语法
    .\.venv\Scripts\python.exe scripts\render_uml.py --only 用例图  # 名称子串过滤

产物：docs/uml/rendered/<名称>.svg 与 .png，并生成 index.md 供文档引用。

渲染依赖见 scripts/plantuml_local.py；首次使用先跑 scripts/setup_uml.py 准备环境。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from plantuml_local import RenderError, render  # noqa: E402

UML_DIR = PROJECT_ROOT / "docs" / "uml"
OUT_DIR = UML_DIR / "rendered"


def png_dimensions(data: bytes) -> tuple[int, int]:
    """读取 PNG 头部宽高，用于粗校验渲染结果非空。"""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染 PlantUML 源文件（本地，含中文）")
    parser.add_argument("--uml-dir", default=str(UML_DIR))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--only", default="", help="仅渲染文件名包含该子串的图")
    parser.add_argument("--check", action="store_true", help="仅校验语法，不写文件")
    args = parser.parse_args()

    uml_dir = Path(args.uml_dir)
    out_dir = Path(args.out_dir)
    sources = sorted(uml_dir.glob("*.puml"))
    if args.only:
        sources = [s for s in sources if args.only in s.stem]
    if not sources:
        print(f"未找到 .puml 文件：{uml_dir}（过滤：{args.only or '无'}）")
        return 1

    if not args.check:
        out_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[str, str]] = []
    rows: list[tuple[str, str, float, str]] = []

    for src in sources:
        text = src.read_text(encoding="utf-8")
        started = time.time()
        try:
            svg = render(text, fmt="svg")
            if b"<svg" not in svg[:1000]:
                raise RenderError("SVG 输出异常")
            size_note = f"{len(svg) / 1024:.1f} KB"
            if not args.check:
                (out_dir / f"{src.stem}.svg").write_bytes(svg)
                png = render(text, fmt="png")
                w, h = png_dimensions(png)
                if w < 50 or h < 50:
                    raise RenderError(f"PNG 尺寸异常 {w}x{h}")
                (out_dir / f"{src.stem}.png").write_bytes(png)
                size_note = f"{w}x{h}"
            rows.append((src.stem, size_note, time.time() - started, "ok"))
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
            failures.append((src.name, detail))
            rows.append((src.stem, "-", time.time() - started, "FAILED"))

    width = max(len(r[0]) for r in rows)
    for stem, size, secs, status in rows:
        print(f"{stem:<{width}}  {size:>12}  {secs:6.2f}s  {status}")

    if failures:
        print("\n以下文件渲染失败：")
        for name, detail in failures:
            print(f"  - {name}\n    {detail[:800]}")
        return 1

    if not args.check:
        lines = [
            "# UML 渲染产物",
            "",
            f"共 {len(rows)} 张图，由 `scripts/render_uml.py` 从同目录 `*.puml` 生成"
            "（本地 PlantUML + Noto Sans SC，中文正常）。",
            "",
            "| 图 | PNG | SVG |",
            "|----|-----|-----|",
        ]
        for stem, _size, _secs, _status in rows:
            lines.append(f"| {stem} | ![{stem}](./{stem}.png) | [{stem}.svg](./{stem}.svg) |")
        (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n已写入 {out_dir}")

    print(f"\n{len(rows) - len(failures)}/{len(rows)} 渲染成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
