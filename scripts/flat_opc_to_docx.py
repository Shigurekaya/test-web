"""Convert a Word Flat OPC XML package into a DOCX file.

Word's ``Document.WordOpenXML`` property exposes the current in-memory document
as a complete Flat OPC package.  This converter repackages that XML without
using Word's unreliable Save() path on large documents.
"""

from __future__ import annotations

import argparse
import base64
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

PKG_NS = "http://schemas.microsoft.com/office/2006/xmlPackage"


def flat_opc_to_docx(source: Path, output: Path) -> tuple[int, int]:
    root = ET.parse(source).getroot()
    if root.tag != f"{{{PKG_NS}}}package":
        raise ValueError("输入文件不是 Word Flat OPC package")

    parts: list[tuple[str, str, bytes]] = []
    for part in root.findall(f"{{{PKG_NS}}}part"):
        name = (part.get(f"{{{PKG_NS}}}name") or "").lstrip("/")
        if not name or name == "[Content_Types].xml":
            continue
        content_type = part.get(f"{{{PKG_NS}}}contentType") or "application/octet-stream"
        xml_data = part.find(f"{{{PKG_NS}}}xmlData")
        binary_data = part.find(f"{{{PKG_NS}}}binaryData")
        if xml_data is not None:
            children = list(xml_data)
            if not children:
                continue
            payload = ET.tostring(children[0], encoding="utf-8", xml_declaration=True)
        elif binary_data is not None:
            payload = base64.b64decode("".join((binary_data.text or "").split()))
        else:
            continue
        parts.append((name, content_type, payload))

    overrides = "".join(
        f'<Override PartName="/{escape(name)}" ContentType="{escape(content_type)}"/>'
        for name, content_type, _ in parts
        if not name.endswith(".rels")
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        f"{overrides}</Types>"
    ).encode()

    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=".docx", dir=output.parent
    )
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            for name, _, payload in parts:
                archive.writestr(name, payload)
        with zipfile.ZipFile(temp_path) as archive:
            broken = archive.testzip()
            if broken:
                raise ValueError(f"生成的 DOCX 包含损坏条目：{broken}")
            if "word/document.xml" not in archive.namelist():
                raise ValueError("生成的 DOCX 缺少 word/document.xml")
        temp_path.replace(output)
    finally:
        temp_path.unlink(missing_ok=True)
    return len(parts), output.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count, size = flat_opc_to_docx(args.source, args.output)
    print(f"converted {count} parts -> {args.output} ({size} bytes)")


if __name__ == "__main__":
    main()
