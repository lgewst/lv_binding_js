#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import component_cpp_emitter as component_core
from widget_cpp_emitter import DEFAULT_MANIFEST, WidgetEmitterError, load_widget, output_path, render_widget


REPO_DIR = Path(__file__).resolve().parent.parent


# 실행 옵션에 따라 위젯 코드를 생성하거나, 저장된 결과의 최신 여부를 검사.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="명세로 C++ wrapper와 위젯 구현 생성")
    parser.add_argument("--widget", default="Switch", help="manifest의 reactName")
    parser.add_argument("--target", choices=("wrapper", "component", "all"), default="wrapper",
                        help="wrapper: wrapper, component: .cpp/.hpp, all: 세 파일")
    parser.add_argument("--component-header", action="store_true",
                        help="wrapper 호출을 생성된 클래스 선언과 대조")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true", help="저장된 결과가 최신인지 검사")
    parser.add_argument("--describe", action="store_true", help="CMake용 소유 위젯, 경로 JSON 출력")
    args = parser.parse_args(argv)

    try:
        outputs = {}
        description = {}
        header_source = None
        if args.target in ("component", "all") or args.component_header:
            component = component_core.load_component(args.manifest, args.widget)
            source, header_source = component_core.render_component(component)
            cpp_path, hpp_path = component_core.output_paths(component)
            if args.target in ("component", "all"):
                outputs.update({cpp_path: source, hpp_path: header_source})
            description.update(owner=component["reactName"], nativeDir=component["nativeDir"],
                               componentSource=str(cpp_path), componentHeader=str(hpp_path),
                               headerDefine="LV_BINDING_GENERATED_COMPONENT_" + component["nativeClass"])
        if args.target in ("wrapper", "all"):
            widget = load_widget(args.manifest, args.widget, header_source=header_source)
            outputs[output_path(widget["reactName"])] = render_widget(widget)
            description.update(owner=widget["reactName"], nativeDir=widget["nativeDir"],
                               output=str(output_path(widget["reactName"])))
        if args.describe:
            print(json.dumps(description))
            return 0
        # 세 파일 모두 생성 가능한지 확인한 뒤 저장 또는 검사 시작.
        if args.check:
            for output, source in outputs.items():
                if not output.is_file() or output.read_text(encoding="utf-8") != source:
                    raise WidgetEmitterError(f"생성 결과가 없음 / 오래됨: {output}")
            for output in outputs:
                print(f"PASS: {output}")
        else:
            for output, source in outputs.items():
                output.parent.mkdir(parents=True, exist_ok=True)
                if not output.is_file() or output.read_text(encoding="utf-8") != source:
                    output.write_text(source, encoding="utf-8")
                print(f"생성 완료: {output}")
        return 0
    except (WidgetEmitterError, OSError) as exc:
        print(f"생성 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
