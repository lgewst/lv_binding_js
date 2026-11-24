#!/usr/bin/env python3
# 실제 빌드의 JS 호출, LVGL 값과 gallery 화면 비교를 실행.

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
WIDGETS = ("Switch", "Text", "View", "Image", "GIF", "Line", "Button", "Mask", "Checkbox",
           "Slider", "ProgressBar", "Arc", "Roller", "Dropdownlist", "Textarea", "Input",
           "Calendar", "Keyboard", "Tabs", "Chart")
UPDATES = ("Roller", "Dropdownlist", "Textarea", "Input", "Calendar", "Keyboard", "Tabs", "Chart")
GUARD_CLASSES = ("Image", "GIF", "Arc", "Chart", "Textarea")


# 실행 결과를 로그에 저장하고 기대한 종료 코드인지 검사.
def execute(command, label, args, env=None, expected=0, timeout=90):
    result = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True, timeout=timeout)
    log = args.output_dir / f"{label}.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != expected:
        raise RuntimeError(f"{label}: exit {result.returncode}\n{log}\n" + result.stderr[-1500:])
    print(f"PASS {label}", flush=True)
    return result


# 실제 앱의 컴파일 옵션과 생성 클래스 선택 정보를 읽음.
def build_settings(build):
    commands = json.loads((build / "compile_commands.json").read_text(encoding="utf-8"))
    engine = next(item for item in commands if item["file"].endswith("/src/engine/engine.cpp"))
    tokens = shlex.split(engine["command"])
    generated = {word.split("=", 1)[0].removeprefix("-DLV_BINDING_GENERATED_COMPONENT_")
                 for word in tokens if word.startswith("-DLV_BINDING_GENERATED_COMPONENT_")}
    wrappers = {Path(item["file"]).stem.removesuffix("_wrap") for item in commands
                if "/autogen/generated/" in item["file"] and item["file"].endswith("_wrap.cpp")}
    return engine, generated, wrappers


# C++ 검사 프로그램은 한 번 컴파일하고 사례마다 독립 프로세스에서 실행.
def native_tests(args):
    engine, generated, _ = build_settings(args.build_dir)
    with tempfile.TemporaryDirectory(prefix="autogen-native-") as folder:
        temporary = Path(folder)
        binary, object_file = temporary / "native-test", temporary / "native.o"
        command = shlex.split(engine["command"])
        command[command.index("-o") + 1] = str(object_file)
        command[command.index("-c") + 1] = str(FOLDER / "native.cpp")
        execute(command + ["-UNDEBUG"], "native-compile", args)
        command = shlex.split((args.build_dir / "CMakeFiles/lvgljs.dir/link.txt").read_text())
        main_object = next(word for word in command if word.endswith("/src/engine/engine.cpp.o"))
        command[command.index(main_object)] = str(object_file)
        command[command.index("-o") + 1] = str(binary)
        command = [str(args.build_dir / word) if word.endswith((".o", ".a")) and not Path(word).is_absolute()
                   else word for word in command]
        execute(command, "native-link", args)
        suites = ["switch", "simple", "complex", "lifetime"]
        if set(GUARD_CLASSES) <= generated:
            suites.append("guards")
        else:
            print("SKIP native-guards: generated classes required", flush=True)
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1")
        for suite in suites:
            result = execute([str(binary), str(REPO), str(args.iterations), suite], f"native-{suite}", args, env)
            if f"NATIVE_PASS {suite} {args.iterations}" not in result.stdout:
                raise RuntimeError(f"Native test did not finish: {suite}")


# 생성 전용 입력 검사는 생성 wrapper 빌드에서만 실행.
def api_tests(args):
    _, _, wrappers = build_settings(args.build_dir)
    contracts = {"tabs", "keyboard", "chart"} <= wrappers
    env = dict(os.environ, AUTOGEN_ITERATIONS=str(args.iterations), AUTOGEN_CONTRACTS="1" if contracts else "0",
               ASAN_OPTIONS=os.environ.get("ASAN_OPTIONS", "detect_leaks=0:halt_on_error=1"))
    if not contracts:
        print("SKIP generated-only contracts: Tabs, Keyboard and Chart wrappers required", flush=True)
    result = execute([str(args.build_dir / "lvgljs"), "run", str(FOLDER / "api.js")], "api", args, env)
    if "API_PASS all" not in result.stdout:
        raise RuntimeError("API tests did not finish")


# 위젯 20종과 변경 상태, 기존 조합 화면 5개를 한 gallery에서 캡처.
def capture_gallery(build, folder, args):
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.png"):
        path.unlink()
    cases = [(name, 0) for name in WIDGETS] + [(name, 1) for name in UPDATES]
    cases += [("Numeric", phase) for phase in (0, 1, 2)] + [("TextView", 0), ("ButtonMask", 0)]
    for name, phase in cases:
        output = folder / f"{name}-{phase}.png"
        env = dict(os.environ, AUTOGEN_WIDGET=name, AUTOGEN_PHASE=str(phase), TEST_CAPTURE="1",
                   TEST_RENDER_MS="3700", TEST_SCREENSHOT_PATH=str(output))
        env.pop("LVGLJS_CAPTURE_LAYER", None)
        if name in ("Mask", "ButtonMask"):
            env["LVGLJS_CAPTURE_LAYER"] = "top"
        execute([str(build / "lvgljs"), "run", "scripts/gui-test-runner.js",
                 "test/autogen/widget_gallery/index.js"], f"{folder.name}-{name}-{phase}",
                args, env, expected=95, timeout=20)
        if not output.is_file():
            raise RuntimeError(f"Screenshot missing: {output}")


# 기존 PNG 도구로 모든 RGBA 값을 직접 대조해 차이 픽셀 수를 저장.
def compare_gallery(before, after, args):
    program = """
const fs = require('fs'), path = require('path'), {PNG} = require('pngjs');
const [before, after] = process.argv.slice(1);
const names = fs.readdirSync(before).filter(n => n.endsWith('.png')).sort();
const actual = fs.readdirSync(after).filter(n => n.endsWith('.png')).sort();
if (!names.length || JSON.stringify(names) !== JSON.stringify(actual)) throw Error('Screenshot set differs');
const rows = names.map(name => {
  const a = PNG.sync.read(fs.readFileSync(path.join(before, name)));
  const b = PNG.sync.read(fs.readFileSync(path.join(after, name)));
  if (a.width !== b.width || a.height !== b.height) throw Error('Size differs: ' + name);
  let differentPixels = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    if ([0,1,2,3].some(c => a.data[i+c] !== b.data[i+c])) ++differentPixels;
  }
  return {name, differentPixels};
});
console.log(JSON.stringify(rows, null, 2));
process.exitCode = rows.some(row => row.differentPixels !== 0) ? 1 : 0;
"""
    result = execute(["node", "-e", program, str(before), str(after)], "pixel-diff", args)
    rows = json.loads(result.stdout)
    (args.output_dir / "pixel-diff.json").write_text(json.dumps(rows, indent=2))
    print(f"PASS gallery: {len(rows)} pairs, different pixels 0", flush=True)


# 빌드 경로와 검사 종류를 선택해 같은 진입점에서 실행.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, default=REPO / "build-generated-switch")
    parser.add_argument("--compare-build-dir", type=Path, default=REPO / "build")
    parser.add_argument("--suite", choices=("all", "api", "native", "screenshots"), default="all")
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--output-dir", type=Path, default=REPO / "_screenshots/autogen")
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("iterations must be positive")
    args.build_dir = args.build_dir.resolve()
    args.compare_build_dir = args.compare_build_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    if args.suite in ("all", "screenshots") and args.build_dir == args.compare_build_dir:
        parser.error("Screenshot comparison requires two different build directories")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.suite in ("all", "native"):
        native_tests(args)
    if args.suite in ("all", "api"):
        api_tests(args)
    if args.suite in ("all", "screenshots"):
        execute(["node", "build.js"], "bundle", args)
        before, after = args.output_dir / "before", args.output_dir / "after"
        capture_gallery(args.compare_build_dir, before, args)
        capture_gallery(args.build_dir, after, args)
        compare_gallery(before, after, args)


if __name__ == "__main__":
    main()
