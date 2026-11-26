#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from component_ts_emitter import render_comp, render_config
from widget_ts_emitter import (
    DEFAULT_MANIFEST, GENERATED_DIR, TsEmitterError, load_widget, require,
)


def output_paths(react_name: str) -> dict[Path, str]:
    directory = GENERATED_DIR / react_name
    return {directory / "comp.ts": "comp", directory / "config.ts": "config"}


# Generate the React files or check saved outputs according to the options.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="명세로 React 컴포넌트와 설정 생성")
    parser.add_argument("--widget", required=True, help="manifest의 reactName")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true", help="저장된 결과가 최신인지 검사")
    args = parser.parse_args(argv)

    try:
        widget = load_widget(args.manifest, args.widget)
        renderers = {"comp": render_comp, "config": render_config}
        outputs = {path: renderers[kind](widget)
                   for path, kind in output_paths(widget["reactName"]).items()}
        if args.check:
            for path, source in outputs.items():
                require(path.is_file() and path.read_text(encoding="utf-8") == source,
                        f"생성 결과가 없음 / 오래됨: {path}")
                print(f"PASS: {path}")
            return 0
        for path, source in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_text(encoding="utf-8") != source:
                path.write_text(source, encoding="utf-8")
            print(f"생성 완료: {path}")
        return 0
    except (TsEmitterError, KeyError, OSError) as exc:
        print(f"생성 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
