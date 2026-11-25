#!/usr/bin/env python3
# Check shared generator Switch regression, widget extension, and CLI options.

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
    # Load fresh Switch data from the manifest for each test.
    def setUp(self):
        self.switch = core.load_widget(cli.DEFAULT_MANIFEST, "Switch")

    # Check generation of Switch bool methods and shared features from one template.
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

    # Check that new widget names reuse bool conversion without generator changes.
    def test_new_widget_name_reuses_boolean_without_a_code_change(self):
        # Prepare only a header and manifest for a widget name unknown to the generator.
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

    # Check errors for invalid JSON, missing widgets, and duplicate widgets.
    def test_bad_manifest_and_missing_or_duplicate_widget_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "widgets.json"
            for content in ("not JSON", "{}", '{"widgets": []}',
                            json.dumps({"widgets": [self.switch, self.switch]})):
                with self.subTest(content=content[:30]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(core.WidgetEmitterError):
                        core.load_widget(path, "Switch")

    # Check that unsupported widgets cause generation errors.
    def test_unsupported_widget_is_not_silently_generated(self):
        with self.assertRaises(core.WidgetEmitterError):
            core.load_widget(cli.DEFAULT_MANIFEST, "Window")

    # Check rejection of unknown conversion rules and missing C++ methods.
    def test_unknown_marshal_and_missing_cpp_method_fail(self):
        for key, value in (("marshal", "unknown"), ("cppMethod", "missingMethod")):
            with self.subTest(key=key):
                widget = copy.deepcopy(self.switch)
                widget["cppBinding"]["methods"][0][key] = value
                with self.assertRaises(core.WidgetEmitterError):
                    core.render_widget(widget)

    # Check rejection of invalid identifiers and duplicate method names.
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

    # Check rejection of unsupported shared features and method settings.
    def test_unknown_feature_and_method_field_fail(self):
        widget = copy.deepcopy(self.switch)
        widget["cppBinding"]["features"].append("unknown")
        with self.assertRaises(core.WidgetEmitterError):
            core.render_widget(widget)
        widget = copy.deepcopy(self.switch)
        widget["cppBinding"]["methods"][0]["marhsal"] = "boolean"
        with self.assertRaises(core.WidgetEmitterError):
            core.render_widget(widget)

    # Check deterministic output and an unchanged input manifest.
    def test_render_is_repeatable_and_does_not_change_manifest(self):
        original = copy.deepcopy(self.switch)
        self.assertEqual(core.render_widget(self.switch), core.render_widget(self.switch))
        self.assertEqual(self.switch, original)

    # Check that shared manifest props determine public Switch method names.
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
        # Handle styleState and event through shared code without extra setters.
        self.assertEqual(len(normalized["cppBinding"]["methods"]), 2)
        before["props"][2]["bridgeMethod"] = "setToggled"
        self.assertEqual(raw, before)

    # Check that a prop reference passes its point array conversion to the generator.
    def test_prop_reference_supplies_point_array_conversion(self):
        root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        raw = next(w for w in root["widgets"] if w["reactName"] == "Line")
        method = core.normalize_widget(raw)["cppBinding"]["methods"][0]
        self.assertEqual(method, {"name": "setPoints", "cppMethod": "setPoints",
                                  "marshal": "pointArray"})
        raw["cppBinding"]["methods"][0]["prop"] = "missing"
        with self.assertRaisesRegex(core.WidgetEmitterError, "prop 참조"):
            core.normalize_widget(raw)

    # Check independent handling of native class names and TS generation settings.
    def test_actual_cpp_class_name_and_ts_generation_flags_are_independent(self):
        # Use GIF from cppBinding.nativeClass instead of Gif from the TS source.
        widget = core.load_widget(cli.DEFAULT_MANIFEST, "GIF")
        self.assertEqual(widget["nativeClass"], "GIF")
        self.assertIn("new (std::nothrow) GIF(uid, nullptr)", core.render_widget(widget))
        # Check C++ wrapper generation when TS generation is disabled for Text.
        self.assertIn("->setText(value)", core.render_widget(core.load_widget(cli.DEFAULT_MANIFEST, "Text")))

    # Check resolution to one shared owner and rejection of reference cycles.
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

    # Check that unsupported widget errors include the original reason.
    def test_unavailable_widget_reports_source_reason(self):
        for name, reason in (("Canvas", "완성된 Canvas 바인딩"), ("Window", "빌드 대상")):
            with self.subTest(widget=name):
                with self.assertRaisesRegex(core.WidgetEmitterError, reason):
                    core.load_widget(cli.DEFAULT_MANIFEST, name)

    # Check rejection of missing number conversions and invalid additions to constructor props.
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

    # Check errors for missing or invalid templates.
    def test_bad_template_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            template = Path(folder) / "bad.in"
            template.write_text("${missing}", encoding="utf-8")
            with self.assertRaises(core.WidgetEmitterError):
                core.render_widget(self.switch, template)

    # Check that the CLI writes and checks generated files without changing handwritten wrappers.
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

    # Check that check mode leaves stale saved outputs unchanged.
    def test_check_is_read_only_even_when_output_is_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "switch_wrap.cpp"
            with patch.object(cli, "output_path", return_value=output), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["--check"]), 1)
                self.assertFalse(output.exists())
                output.write_text("stale", encoding="utf-8")
                self.assertEqual(cli.main(["--check"]), 1)
                self.assertEqual(output.read_text(encoding="utf-8"), "stale")

    # Execute generated Switch bool methods with valid and invalid inputs.
    @unittest.skipUnless(shutil.which("c++"), "C++ 컴파일러가 없음")
    def test_shared_boolean_handler_executes_for_switch(self):
        # Use mock QuickJS values and C++ objects to check bool conversion and invalid inputs.
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
    # Build one test executable linking generated functions to the real QuickJS library.
    @classmethod
    def setUpClass(cls):
        # Check integer conversion, array access exceptions, and ArrayBuffer handling in real QuickJS.
        # Link generated functions to the QuickJS library built by the project.
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

    # Run a selected case in the prepared executable and check successful exit.
    def run_case(self, name):
        result = subprocess.run([str(self.binary), name], capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    # Check integer conversion and argument validation in real QuickJS.
    def test_real_quickjs_int32_conversion_and_argument_guard(self):
        self.run_case("int32")

    # Check conversion of one array into two integer arguments in real QuickJS.
    def test_real_quickjs_array_pair_conversion(self):
        self.run_case("arrayPair")

    # Check passing two separate integer arguments in real QuickJS.
    def test_real_quickjs_separate_integer_arguments(self):
        self.run_case("args2")

    # Check passing numeric and bool arguments together in real QuickJS.
    def test_real_quickjs_number_and_boolean_arguments(self):
        self.run_case("mixed")

    # Check image bytes, symbols, and invalid image inputs in real QuickJS.
    def test_real_quickjs_image_buffer_symbol_and_invalid_input(self):
        self.run_case("image")

    # Check exceptions from reading array elements and converting values.
    def test_real_quickjs_array_getter_and_conversion_exceptions(self):
        self.run_case("exceptions")

    # Check that real QuickJS rejects calls on closed widgets.
    def test_real_quickjs_closed_component_guard(self):
        self.run_case("closed")

    # Check string array and requested length handling in real QuickJS.
    def test_real_quickjs_string_array_and_length(self):
        self.run_case("stringArray")

    # Check string arrays with length and bool arguments in real QuickJS.
    def test_real_quickjs_string_array_length_and_boolean(self):
        self.run_case("stringArrayBoolean")

    # Check exceptions raised while reading string array elements.
    def test_real_quickjs_string_array_getter_exception(self):
        self.run_case("stringArrayException")

    # Check bool to C++ integer conversion in real QuickJS.
    def test_real_quickjs_boolean_to_int32(self):
        self.run_case("booleanInt")

    # Check integer to configured C++ enum conversion in real QuickJS.
    def test_real_quickjs_enum_cast(self):
        self.run_case("enumCast")

    # Check integer date arguments and date arrays in real QuickJS.
    def test_real_quickjs_date_arguments_and_arrays(self):
        self.run_case("dates")

    # Check Chart string lists and axis option property access.
    def test_real_quickjs_chart_labels_and_object_fields(self):
        self.run_case("axisOptions")

    # Check nested axis data conversion and temporary value cleanup on exceptions.
    def test_real_quickjs_nested_axis_data_and_exception_cleanup(self):
        self.run_case("axes")

    # Check valid widget references, closed widgets, and references to unrelated objects.
    def test_real_quickjs_live_closed_and_foreign_component_references(self):
        self.run_case("references")


if __name__ == "__main__":
    unittest.main(verbosity=2)
