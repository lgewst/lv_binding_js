#!/usr/bin/env python3
"""LVGL 의 구 이름 호환 껍데기에 기대고 있는 곳을 찾는다.

`lvgl.h` 는 LV_DISABLE_API_MAPPING 이 없을 때 lv_api_map_v*.h 를 끌어온다. 거기
정의된 이름은 지우려고 남겨 둔 것이라 다음 메이저 버전에서 사라진다. 우리 코드가
그 이름을 쓰면 빌드는 되지만 버전업에서 한 번에 깨지므로, 쓰는 곳이 생기면 막는다.

목록은 서브모듈에서 직접 읽으므로 LVGL 을 올리면 검사 대상도 함께 바뀐다.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_HEADERS = sorted((ROOT / "deps/lvgl/src").glob("lv_api_map_v*.h"))
SCAN_ROOTS = ("src", "autogen", "scripts/data/widgets_manifest.json")
# 생성기(.py)도 본다. C 코드를 문자열로 들고 있어 구 이름이 숨을 수 있다.
SCAN_SUFFIXES = {".c", ".cpp", ".h", ".hpp", ".in", ".json", ".py"}

DEFINE = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)(?:\s*\([^)]*\))?\s+\S", re.M)
TYPEDEF = re.compile(r"^\s*typedef\s+.+?\s+([A-Za-z_]\w*)\s*;", re.M)
INLINE = re.compile(r"^\s*static\s+inline\s+[^(]*?\b([a-z_]\w*)\s*\(", re.M)
WORD = re.compile(r"\b[A-Za-z_]\w*\b")


def deprecated_names() -> dict[str, str]:
    if not MAP_HEADERS:
        sys.exit("deps/lvgl 서브모듈이 없습니다. git submodule update --init 먼저 실행하세요.")
    names: dict[str, str] = {}
    for header in MAP_HEADERS:
        text = header.read_text(encoding="utf-8", errors="ignore")
        for pattern in (DEFINE, TYPEDEF, INLINE):
            for match in pattern.finditer(text):
                names.setdefault(match.group(1), header.name)
    return names


def scan_files():
    for entry in SCAN_ROOTS:
        path = ROOT / entry
        if path.is_file():
            yield path
        else:
            yield from (p for p in path.rglob("*")
                        if p.is_file() and p.suffix in SCAN_SUFFIXES
                        and "generated" not in p.parts)


def main() -> int:
    names = deprecated_names()
    hits: list[tuple[str, int, str, str]] = []
    for path in scan_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for token in WORD.findall(line):
                if token in names:
                    hits.append((str(path.relative_to(ROOT)), number, token, names[token]))

    if not hits:
        print(f"OK: 구 이름 사용 없음 (검사 대상 {len(names)}개, {len(MAP_HEADERS)}개 헤더)")
        return 0

    print(f"FAIL: 호환 껍데기로만 해결되는 이름 {len(hits)}곳", file=sys.stderr)
    for file, number, token, header in hits:
        print(f"  {file}:{number}  {token}  ({header})", file=sys.stderr)
    print("\n새 이름은 해당 헤더의 #define 오른쪽에 적혀 있습니다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
