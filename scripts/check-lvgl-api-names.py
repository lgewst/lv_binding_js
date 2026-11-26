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
# 생성기(.py)도 본다. C 코드를 문자열로 들고 있어 구 이름이 숨을 수 있다.
# .ts/.js 도 본다. 주석과 문서 문자열에 LVGL 이름이 들어 있다.
SCAN_ROOTS = ("src", "autogen", "scripts")
SCAN_SUFFIXES = {".c", ".cpp", ".h", ".hpp", ".in", ".json", ".py", ".ts", ".tsx", ".js"}
# 껍데기 헤더가 자기 인클루드 가드로 쓰는 이름. 구 API 가 아니다.
NOT_API = re.compile(r"^LV_API_MAP")
# 껍데기 안에 있지만 v9 의 현재 이름이거나 lv_conf 가 정의하는 옵션.
CURRENT = frozenset(("LV_FS_DEFAULT_DRIVER_LETTER", "LV_DRAW_LAYER_SIMPLE_BUF_SIZE"))

# 일부러 적어 둔 언급. 근거를 함께 남긴다.
ALLOWED = {
    ("scripts/data/lv_conf_manifest.json", "_LV_EVENT_LAST"):
        "renames 기능 설명의 예시로 구 이름을 쓴다",
}

DEFINE = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)(?:\s*\([^)]*\))?\s+\S", re.M)
TYPEDEF = re.compile(r"^\s*typedef\s+.+?\s+([A-Za-z_]\w*)\s*;", re.M)
INLINE = re.compile(r"^\s*static\s+inline\s+[^(]*?\b([a-z_]\w*)\s*\(", re.M)
WORD = re.compile(r"\b[A-Za-z_]\w*\b")


def deprecated_names() -> dict[str, str]:
    if not (ROOT / "deps/lvgl/src").is_dir():
        sys.exit("deps/lvgl 서브모듈이 없습니다. git submodule update --init 먼저 실행하세요.")
    if not MAP_HEADERS:
        # LVGL 이 호환 껍데기를 지운 버전이다. 검사할 것이 없으면 통과다.
        print("OK: LVGL 에 호환 껍데기 헤더가 없습니다. 검사할 구 이름이 없습니다.")
        raise SystemExit(0)
    names: dict[str, str] = {}
    for header in MAP_HEADERS:
        text = header.read_text(encoding="utf-8", errors="ignore")
        for pattern in (DEFINE, TYPEDEF, INLINE):
            for match in pattern.finditer(text):
                name = match.group(1)
                if NOT_API.match(name) or name in CURRENT:
                    continue
                names.setdefault(name, header.name)
    return names


def scan_files():
    # 이 파일 자신은 빼야 한다. 허용 목록이 구 이름을 들고 있다.
    me = Path(__file__).resolve()
    for entry in SCAN_ROOTS:
        path = ROOT / entry
        if path.is_file():
            yield path
        else:
            yield from (p for p in path.rglob("*")
                        if p.is_file() and p.suffix in SCAN_SUFFIXES
                        and "generated" not in p.parts
                        and p.resolve() != me)


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

    used = set()
    kept = []
    for file, number, token, header in hits:
        if (file, token) in ALLOWED:
            used.add((file, token))
            continue
        kept.append((file, number, token, header))
    stale = sorted(set(ALLOWED) - used)
    for file, token in stale:
        print(f"FAIL: ALLOWED 의 {file} {token} 은 더 이상 없습니다. 지울 것", file=sys.stderr)
    hits = kept

    if not hits and not stale:
        print(f"OK: 구 이름 사용 없음 "
              f"(검사 대상 {len(names)}개, {len(MAP_HEADERS)}개 헤더, 허용 {len(ALLOWED)}건)")
        return 0
    if not hits:
        return 1

    print(f"FAIL: 호환 껍데기로만 해결되는 이름 {len(hits)}곳", file=sys.stderr)
    for file, number, token, header in hits:
        print(f"  {file}:{number}  {token}  ({header})", file=sys.stderr)
    print("\n새 이름은 해당 헤더의 #define 오른쪽에 적혀 있습니다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
