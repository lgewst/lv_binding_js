#!/usr/bin/env python3
# 공통 생성기의 Switch 회귀, 새 위젯 확장, 실행 옵션을 검사.

from __future__ import annotations

import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cpp_emitter as cli
import widget_cpp_emitter as core


class CommonEmitterTest(unittest.TestCase):
    # 각 테스트에서 사용할 Switch 정보를 manifest에서 새로 읽어 준비.
    def setUp(self):
        self.switch = core.load_widget(cli.DEFAULT_MANIFEST, "Switch")

    # Switch의 bool 메서드와 공통 기능이 같은 템플릿으로 생성되는지 검사.
    def test_switch_boolean_methods_use_the_common_template(self):
        source = core.render_widget(self.switch)
        self.assertIn("JS_IsBool(argv[0])", source)
        self.assertIn("->setValue(value)", source)
        self.assertIn("->setDisabled(value)", source)
        self.assertIn('#include "native/components/switch/switch.hpp"', source)
        self.assertNotIn("lv_obj_add_state(", source)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "switch_wrap.cpp"
            with patch.object(cli, "output_path", return_value=output), redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--widget", "Switch"]), 0)
                self.assertEqual(cli.main(["--widget", "Switch", "--check"]), 0)
            self.assertEqual(source, output.read_text(encoding="utf-8"))

    # 새 위젯 이름도 생성기 수정 없이 기존 bool 변환 규칙을 재사용하는지 검사.
    def test_new_widget_name_reuses_boolean_without_a_code_change(self):
        # 생성기에 없는 위젯 이름으로 헤더와 manifest만 준비해 기존 규칙을 재사용.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            header = root / "src/render/native/components/gauge/gauge.hpp"
            header.parent.mkdir(parents=True)
            header.write_text("class Gauge { void setEnabled(bool); };", encoding="utf-8")
            widget = {
                "reactName": "Gauge", "nativeClass": "Gauge",
                "nativeDir": "gauge",
                "props": [{"name": "enabled", "tsType": "boolean",
                           "bridgeMethod": "setEnabled", "cppMethod": "setEnabled",
                           "behavior": {"kind": "value"}}],
                "cppBinding": {
                    "features": ["alignment"],
                },
            }
            manifest = root / "widgets.json"
            manifest.write_text(json.dumps({"widgets": [widget]}), encoding="utf-8")
            with patch.object(core, "REPO_DIR", root):
                loaded = core.load_widget(manifest, "Gauge")
                source = core.render_widget(loaded)
            self.assertIn("static_cast<Gauge*>(ref->comp)->setEnabled(value)", source)
            self.assertIn("JS_ToBool(ctx, argv[0])", source)
            self.assertIn('TJS_CFUNC_DEF("setEnabled"', source)

    # 잘못된 JSON, 누락된 위젯, 중복된 위젯이 오류로 처리되는지 검사.
    def test_bad_manifest_and_missing_or_duplicate_widget_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "widgets.json"
            for content in ("not JSON", "{}", '{"widgets": []}',
                            json.dumps({"widgets": [self.switch, self.switch]})):
                with self.subTest(content=content[:30]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(core.WidgetEmitterError):
                        core.load_widget(path, "Switch")

    # 지원하지 않는 위젯을 생성하려 할 때 오류가 발생하는지 검사.
    def test_unsupported_widget_is_not_silently_generated(self):
        with self.assertRaises(core.WidgetEmitterError):
            core.load_widget(cli.DEFAULT_MANIFEST, "Window")

    # 모르는 변환 규칙과 실제로 없는 C++ 메서드가 거부되는지 검사.
    def test_unknown_marshal_and_missing_cpp_method_fail(self):
        for key, value in (("marshal", "unknown"), ("cppMethod", "missingMethod")):
            with self.subTest(key=key):
                widget = copy.deepcopy(self.switch)
                widget["cppBinding"]["methods"][0][key] = value
                with self.assertRaises(core.WidgetEmitterError):
                    core.render_widget(widget)

    # 코드에 넣을 수 없는 이름과 중복되는 메서드 이름이 거부되는지 검사.
    def test_unsafe_and_colliding_names_fail(self):
        for names in (("bad-name", "setDisabled"),
                      ("close", "setDisabled"),
                      ("setChecked", "SetChecked")):
            with self.subTest(names=names):
                widget = copy.deepcopy(self.switch)
                for method, name in zip(widget["cppBinding"]["methods"], names):
                    method["name"] = name
                with self.assertRaises(core.WidgetEmitterError):
                    core.render_widget(widget)

    # 지원하지 않는 공통 기능과 메서드 설정 항목이 거부되는지 검사.
    def test_unknown_feature_and_method_field_fail(self):
        widget = copy.deepcopy(self.switch)
        widget["cppBinding"]["features"].append("unknown")
        with self.assertRaises(core.WidgetEmitterError):
            core.render_widget(widget)
        widget = copy.deepcopy(self.switch)
        widget["cppBinding"]["methods"][0]["marhsal"] = "boolean"
        with self.assertRaises(core.WidgetEmitterError):
            core.render_widget(widget)

    # 반복 생성 결과가 같고 입력 manifest가 바뀌지 않는지 검사.
    def test_render_is_repeatable_and_does_not_change_manifest(self):
        original = copy.deepcopy(self.switch)
        self.assertEqual(core.render_widget(self.switch), core.render_widget(self.switch))
        self.assertEqual(self.switch, original)

    # Switch의 공개 메서드 이름이 공유 manifest의 속성 정보에서 결정되는지 검사.
    def test_shared_manifest_props_are_the_only_source_of_switch_method_names(self):
        root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        raw = next(w for w in root["widgets"] if w["reactName"] == "Switch")
        before = copy.deepcopy(raw)
        self.assertNotIn("methods", raw["cppBinding"])
        raw["props"][2]["bridgeMethod"] = "setToggled"
        normalized = core.normalize_widget(raw)
        source = core.render_widget(normalized)
        self.assertIn('TJS_CFUNC_DEF("setToggled"', source)
        self.assertNotIn('TJS_CFUNC_DEF("setChecked"', source)
        self.assertIn("->setValue(value)", source)
        # styleState와 event는 공통 코드에서 처리. 개별 설정 함수 추가 생략.
        self.assertEqual(len(normalized["cppBinding"]["methods"]), 2)
        before["props"][2]["bridgeMethod"] = "setToggled"
        self.assertEqual(raw, before)

    # 속성 참조로 지정한 좌표 배열 변환 정보가 생성기에 전달되는지 검사.
    def test_prop_reference_supplies_point_array_conversion(self):
        root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        raw = next(w for w in root["widgets"] if w["reactName"] == "Line")
        method = core.normalize_widget(raw)["cppBinding"]["methods"][0]
        self.assertEqual(method, {"name": "setPoints", "cppMethod": "setPoints",
                                  "marshal": "pointArray"})
        raw["cppBinding"]["methods"][0]["prop"] = "missing"
        with self.assertRaisesRegex(core.WidgetEmitterError, "prop 참조"):
            core.normalize_widget(raw)

    # 실제 C++ 클래스 이름과 TS 생성 여부가 각각 적용되는지 검사.
    def test_actual_cpp_class_name_and_ts_generation_flags_are_independent(self):
        # C++ 클래스 이름은 TS 원본의 Gif 대신 cppBinding.nativeClass의 GIF를 사용.
        widget = core.load_widget(cli.DEFAULT_MANIFEST, "GIF")
        self.assertEqual(widget["nativeClass"], "GIF")
        self.assertIn("new (std::nothrow) GIF(uid, nullptr)", core.render_widget(widget))
        # Text의 TS 생성 설정이 false인 경우에도 C++ wrapper 생성이 가능한지 확인.
        self.assertIn("->setText(value)", core.render_widget(core.load_widget(cli.DEFAULT_MANIFEST, "Text")))

    # 공유 위젯이 하나의 소유 위젯으로 해석되고 순환 참조는 거부되는지 검사.
    def test_shared_widget_resolves_to_one_owner_and_cycles_fail(self):
        root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        raw = next(w for w in root["widgets"] if w["reactName"] == "Switch")
        alias = {"reactName": "Alias", "cppBinding": {"sharedWith": "Switch"}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "widgets.json"
            path.write_text(json.dumps({"widgets": [raw, alias]}), encoding="utf-8")
            self.assertEqual(core.load_widget(path, "Alias")["reactName"], "Switch")
            alias["cppBinding"]["sharedWith"] = "Alias"
            path.write_text(json.dumps({"widgets": [alias]}), encoding="utf-8")
            with self.assertRaisesRegex(core.WidgetEmitterError, "순환"):
                core.load_widget(path, "Alias")

    # 미지원 위젯의 원래 사유가 오류 메시지에 포함되는지 검사.
    def test_unavailable_widget_reports_source_reason(self):
        for name, reason in (("Canvas", "완성된 Canvas 바인딩"), ("Window", "빌드 대상")):
            with self.subTest(widget=name):
                with self.assertRaisesRegex(core.WidgetEmitterError, reason):
                    core.load_widget(cli.DEFAULT_MANIFEST, name)

    # 숫자 변환법 누락과 생성 시점 속성에 대한 잘못된 보완 설정이 거부되는지 검사.
    def test_missing_numeric_marshalling_and_create_overrides_are_rejected(self):
        raw = {"reactName": "Gauge", "nativeClass": "Gauge", "cppBinding": {"features": []},
               "props": [{"name": "value", "tsType": "number", "bridgeMethod": "setValue",
                          "behavior": {"kind": "value"}}]}
        with self.assertRaisesRegex(core.WidgetEmitterError, "marshal"):
            core.normalize_widget(raw)
        raw["props"][0]["lifecycle"] = "create"
        self.assertEqual(core.normalize_widget(raw)["cppBinding"]["methods"], [])
        raw["cppBinding"]["methods"] = [{"prop": "value", "marshal": "int32"}]
        with self.assertRaisesRegex(core.WidgetEmitterError, "직접 호출"):
            core.normalize_widget(raw)

    # 없거나 잘못된 템플릿이 오류로 보고되는지 검사.
    def test_bad_template_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            template = Path(folder) / "bad.in"
            template.write_text("${missing}", encoding="utf-8")
            with self.assertRaises(core.WidgetEmitterError):
                core.render_widget(self.switch, template)

    # 실행 명령이 수작업 wrapper를 건드리지 않고 생성 파일을 저장하고 검사하는지 확인.
    def test_cli_writes_and_checks_without_touching_handwritten_wrapper(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "switch_wrap.cpp"
            original = (core.REPO_DIR / "src/render/native/components/switch/switch_wrap.cpp")
            original_bytes = original.read_bytes()
            with patch.object(cli, "output_path", return_value=output), redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--widget", "Switch"]), 0)
                self.assertEqual(cli.main(["--widget", "Switch", "--check"]), 0)
            self.assertEqual(output.read_text(encoding="utf-8"), core.render_widget(self.switch))
            self.assertEqual(original.read_bytes(), original_bytes)

    # 저장된 결과가 오래되어도 검사 모드가 파일을 수정하지 않는지 확인.
    def test_check_is_read_only_even_when_output_is_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "switch_wrap.cpp"
            with patch.object(cli, "output_path", return_value=output), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["--check"]), 1)
                self.assertFalse(output.exists())
                output.write_text("stale", encoding="utf-8")
                self.assertEqual(cli.main(["--check"]), 1)
                self.assertEqual(output.read_text(encoding="utf-8"), "stale")

    # 생성된 Switch bool 함수가 정상 입력과 잘못된 입력을 처리하는지 실행해 검사.
    @unittest.skipUnless(shutil.which("c++"), "C++ 컴파일러가 없음")
    def test_shared_boolean_handler_executes_for_switch(self):
        # 생성 함수에 모형 QuickJS 값과 C++ 객체를 넣어 bool과 오류 입력을 검사.
        handler = core.method_handler("Switch", self.switch["cppBinding"]["methods"][0])
        source = r'''
#include <cassert>
struct JSContext {};
struct JSValue { int tag; bool value; void* opaque; };
using JSValueConst = JSValue;
const JSValue JS_UNDEFINED = {0, false, nullptr};
const int SwitchClassID = 1;
bool JS_IsBool(JSValue v) { return v.tag == 1; }
bool JS_ToBool(JSContext*, JSValue v) { return v.value; }
void* JS_GetOpaque(JSValue v, int) { return v.opaque; }
struct Switch { bool checked = false; int calls = 0;
    void setValue(bool v) { checked = v; ++calls; } };
struct COMP_REF { void* comp; };
''' + handler + r'''
int main() {
    JSContext ctx; Switch comp; COMP_REF ref = {&comp};
    JSValue receiver = {2, false, &ref};
    JSValue yes = {1, true, nullptr}, no = {1, false, nullptr};
    JSValue number = {3, true, nullptr};
    NativeCompSetChecked(&ctx, receiver, 1, &yes);
    assert(comp.checked && comp.calls == 1);
    NativeCompSetChecked(&ctx, receiver, 1, &no);
    assert(!comp.checked && comp.calls == 2);
    NativeCompSetChecked(&ctx, receiver, 0, nullptr);
    NativeCompSetChecked(&ctx, receiver, 1, &number);
    assert(comp.calls == 2);
    ref.comp = nullptr;
    NativeCompSetChecked(&ctx, receiver, 1, &yes);
    assert(comp.calls == 2);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp, binary = Path(folder) / "test.cpp", Path(folder) / "test"
            cpp.write_text(source, encoding="utf-8")
            compiled = subprocess.run([shutil.which("c++"), "-std=c++14", str(cpp),
                                       "-o", str(binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(ran.returncode, 0, ran.stderr)


@unittest.skipUnless(shutil.which("c++"), "C++ 컴파일러가 없음")
class NumericMarshallingTest(unittest.TestCase):
    # 실제 QuickJS 라이브러리에 생성 함수를 연결해 테스트용 실행 파일을 한 번 빌드.
    @classmethod
    def setUpClass(cls):
        # 정수 변환, 배열 속성 접근 예외, ArrayBuffer 처리를 실제 QuickJS로 검사.
        # 프로젝트에서 빌드한 QuickJS 라이브러리에 생성 함수를 연결.
        quickjs = core.REPO_DIR / "deps/txiki/deps/quickjs"
        library = core.REPO_DIR / "build-generated-switch/deps/txiki/deps/quickjs/libqjs.a"
        if not library.is_file():
            raise unittest.SkipTest("먼저 build-generated-switch의 QuickJS를 빌드해야 합니다.")
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        root = Path(folder.name)
        methods = [
            ("scalar", "setScalar", "int32"),
            ("arrayPair", "setPair", "int32ArrayPair"),
            ("argsPair", "setPair", "int32Args2"),
            ("mixed", "setMixed", "int32Boolean"),
            ("image", "setImage", "arcImage"),
            ("stringList", "setItems", "stringArrayLength"),
            ("stringOptions", "setOptions", "stringArrayLengthBoolean"),
            ("booleanInt", "setScalar", "booleanToInt32"),
            ("direction", "setDirection", "int32"),
            ("dateArgs", "setDateArgs", "int32Args3"),
            ("dates", "setDates", "dateArray"),
            ("labels", "setItems", "stringArray"),
            ("axisOptions", "setAxisOptions", "axisOption"),
            ("axes", "setAxes", "axisData"),
            ("child", "setChild", "componentReference"),
            ("namedChild", "setNamedChild", "stringComponentReference"),
        ]
        handlers = []
        for name, cpp, kind in methods:
            method = {"name": name, "cppMethod": cpp, "marshal": kind}
            if kind == "arcImage":
                method["returns"] = "boolean"
            if name == "direction":
                method["cast"] = "lv_dir_t"
            handlers.append(core.method_handler("Gauge", method))
        helpers = core.complex_helpers({kind for _, _, kind in methods}, ["Gauge"])
        (root / "handlers.inc").write_text(helpers + "\n".join(handlers), encoding="utf-8")
        cls.binary = root / "marshalling-test"
        fixture = Path(__file__).parent / "fixtures/numeric_binding_main.cpp"
        built = subprocess.run([shutil.which("c++"), "-std=c++17", "-I", str(root),
                                "-I", str(quickjs), str(fixture), str(library),
                                "-pthread", "-lm", "-o", str(cls.binary)],
                               capture_output=True, text=True, timeout=60)
        if built.returncode != 0:
            raise AssertionError(built.stderr)

    # 준비한 실행 파일에서 지정한 사례를 실행하고 정상 종료 여부를 검사.
    def run_case(self, name):
        result = subprocess.run([str(self.binary), name], capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    # 실제 QuickJS에서 정수 변환과 인자 검사가 동작하는지 확인.
    def test_real_quickjs_int32_conversion_and_argument_guard(self):
        self.run_case("int32")

    # 배열 하나를 정수 두 개로 바꾸는 처리를 실제 QuickJS에서 검사.
    def test_real_quickjs_array_pair_conversion(self):
        self.run_case("arrayPair")

    # 분리된 정수 인자 두 개를 전달하는 처리를 실제 QuickJS에서 검사.
    def test_real_quickjs_separate_integer_arguments(self):
        self.run_case("args2")

    # 숫자와 bool 인자를 함께 전달하는 처리를 실제 QuickJS에서 검사.
    def test_real_quickjs_number_and_boolean_arguments(self):
        self.run_case("mixed")

    # 이미지 바이트, 심볼, 잘못된 이미지 인자를 실제 QuickJS에서 검사.
    def test_real_quickjs_image_buffer_symbol_and_invalid_input(self):
        self.run_case("image")

    # 배열 원소를 읽거나 값을 변환할 때 발생한 예외가 처리되는지 검사.
    def test_real_quickjs_array_getter_and_conversion_exceptions(self):
        self.run_case("exceptions")

    # 이미 닫힌 위젯에 대한 호출이 차단되는지 실제 QuickJS에서 검사.
    def test_real_quickjs_closed_component_guard(self):
        self.run_case("closed")

    # 문자열 배열과 요청 길이를 처리하는 규칙을 실제 QuickJS에서 검사.
    def test_real_quickjs_string_array_and_length(self):
        self.run_case("stringArray")

    # 문자열 배열, 길이, bool을 함께 전달하는 규칙을 실제 QuickJS에서 검사.
    def test_real_quickjs_string_array_length_and_boolean(self):
        self.run_case("stringArrayBoolean")

    # 문자열 배열의 원소를 읽다가 발생한 예외가 처리되는지 검사.
    def test_real_quickjs_string_array_getter_exception(self):
        self.run_case("stringArrayException")

    # bool을 C++ 정수로 바꾸는 규칙을 실제 QuickJS에서 검사.
    def test_real_quickjs_boolean_to_int32(self):
        self.run_case("booleanInt")

    # 정수 값을 지정한 C++ enum 타입으로 바꾸는 처리를 실제 QuickJS에서 검사.
    def test_real_quickjs_enum_cast(self):
        self.run_case("enumCast")

    # 날짜를 구성하는 정수 인자와 날짜 배열을 실제 QuickJS에서 검사.
    def test_real_quickjs_date_arguments_and_arrays(self):
        self.run_case("dates")

    # Chart 문자열 목록과 축 옵션 객체의 속성을 읽는 처리를 검사.
    def test_real_quickjs_chart_labels_and_object_fields(self):
        self.run_case("axisOptions")

    # 중첩된 축 데이터 변환과 예외 발생 시 임시 값 해제를 검사.
    def test_real_quickjs_nested_axis_data_and_exception_cleanup(self):
        self.run_case("axes")

    # 유효한 위젯 참조, 닫힌 위젯, 다른 종류의 객체 참조를 구분하는지 검사.
    def test_real_quickjs_live_closed_and_foreign_component_references(self):
        self.run_case("references")


if __name__ == "__main__":
    unittest.main(verbosity=2)
