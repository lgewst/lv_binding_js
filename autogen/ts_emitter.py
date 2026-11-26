#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from component_ts_emitter import render_comp, render_config
from widget_ts_emitter import (
    COMPONENTS_DIR, DEFAULT_MANIFEST, GENERATED_DIR, TsEmitterError, load_widget, require,
)

RENDERERS = {"comp": render_comp, "config": render_config}


# src 가 기본이다. 생성 결과가 컴포넌트 자리에 그대로 들어가고, gen:all:check 가
# 최신인지 지킨다. generated 는 수작업 코드와 대조할 때만 쓴다.
def output_paths(react_name: str, dest: str) -> dict[Path, str]:
    root = COMPONENTS_DIR if dest == "src" else GENERATED_DIR
    directory = root / react_name
    return {directory / "comp.ts": "comp", directory / "config.ts": "config"}


def widget_names(manifest: Path) -> list[str]:
    widgets = json.loads(manifest.read_text(encoding="utf-8"))["widgets"]
    return [w["reactName"] for w in widgets if (w.get("generate") or {}).get("ts")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="명세로 React 컴포넌트와 설정 생성")
    parser.add_argument("--widget", help="manifest의 reactName. 생략하면 대상 전부")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dest", choices=("src", "generated"), default="src")
    parser.add_argument("--check", action="store_true", help="저장된 결과가 최신인지 검사")
    args = parser.parse_args(argv)

    try:
        names = [args.widget] if args.widget else widget_names(args.manifest)
        require(bool(names), "생성 대상 위젯이 없습니다 (generate.ts).")
        for name in names:
            widget = load_widget(args.manifest, name)
            for path, kind in output_paths(widget["reactName"], args.dest).items():
                source = RENDERERS[kind](widget)
                if args.check:
                    require(path.is_file() and path.read_text(encoding="utf-8") == source,
                            f"생성 결과가 없음 / 오래됨: {path}")
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.is_file() or path.read_text(encoding="utf-8") != source:
                    path.write_text(source, encoding="utf-8")
        print(f"{'PASS' if args.check else '생성 완료'}: 위젯 {len(names)}개")
        return 0
    except (TsEmitterError, KeyError, OSError) as exc:
        print(f"생성 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
