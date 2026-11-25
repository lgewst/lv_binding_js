#!/usr/bin/env python3
# Check generated widgets against the existing public JS method names.

from __future__ import annotations

import copy
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import widget_cpp_emitter as emitter
import cpp_emitter as cli


MANIFEST = emitter.DEFAULT_MANIFEST
SUPPORTED = ("Switch", "Text", "View", "Image", "GIF", "Line", "Button", "Mask", "Checkbox",
             "Slider", "ProgressBar", "Arc", "Roller", "Dropdownlist", "Textarea", "Input",
             "Calendar", "Keyboard", "Tabs", "Chart")
METHOD_RE = re.compile(r'TJS_CFUNC_DEF\("([^"\n]+)",\s*\d+,\s*(\w+)\)')


class WidgetCppEmitterTest(unittest.TestCase):
    # Generate wrappers in an empty temporary directory, then check public methods and freshness.
    def test_all_manifest_generated_wrappers_match_handwritten_public_methods(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["widgets"]), 22)
        with tempfile.TemporaryDirectory() as folder:
            for name in SUPPORTED:
                with self.subTest(widget=name):
                    widget = emitter.load_widget(MANIFEST, name)
                    output = Path(folder) / f"{widget['reactName'].lower()}_wrap.cpp"
                    with patch.object(cli, "output_path", return_value=output), redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main(["--widget", name]), 0)
                        self.assertEqual(cli.main(["--widget", name, "--check"]), 0)
                    generated = output.read_text(encoding="utf-8")
                    directory = widget["nativeDir"]
                    native_class = widget["nativeClass"]
                    manual = (emitter.REPO_DIR / "src/render/native/components" / directory
                              / f"{directory}_wrap.cpp").read_text(encoding="utf-8")
                    # Compare the public JS method name sets.
                    self.assertEqual({m[0] for m in METHOD_RE.findall(manual)},
                                     {m[0] for m in METHOD_RE.findall(generated)})
                    self.assertIn(f"void NativeComponent{native_class}Init", generated)
                    self.assertIn(f"COMP_FINALIZER({native_class}Finalizer", generated)
            self.assertEqual(len(list(Path(folder).glob("*_wrap.cpp"))), 19)

    # Check Text string conversion and C++ method calls.
    def test_text_string_conversion(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "Text"))
        self.assertIn("JS_ToCStringLen(ctx, &length, argv[0])", source)
        self.assertIn("->setText(value)", source)

    # Check View child handling and background image support.
    def test_view_children_and_background_image(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "View"))
        self.assertIn("WRAPPED_APPEND_CHILD(View", source)
        self.assertIn("WRAPPED_INSERT_CHILD(View", source)
        self.assertIn('TJS_CFUNC_DEF("setBackgroundImage"', source)

    # Check Button and Mask child handling and their configured shared features.
    def test_button_and_mask_share_children_but_not_all_common_methods(self):
        button = emitter.render_widget(emitter.load_widget(MANIFEST, "Button"))
        mask = emitter.render_widget(emitter.load_widget(MANIFEST, "Mask"))
        for source in (button, mask):
            self.assertIn('TJS_CFUNC_DEF("appendChild"', source)
            self.assertIn('TJS_CFUNC_DEF("insertChildBefore"', source)
        self.assertIn('TJS_CFUNC_DEF("align"', button)
        self.assertIn('TJS_CFUNC_DEF("moveToFront"', button)
        self.assertIn('TJS_CFUNC_DEF("setBackgroundImage"', button)
        self.assertNotIn('TJS_CFUNC_DEF("align"', mask)
        self.assertNotIn('TJS_CFUNC_DEF("moveToFront"', mask)
        self.assertNotIn('TJS_CFUNC_DEF("setBackgroundImage"', mask)

    # Check that Image and GIF reuse the same byte array conversion rule.
    def test_image_and_gif_share_array_buffer_conversion(self):
        for name, method in (("Image", "setImageBinary"), ("GIF", "setGIFBinary")):
            with self.subTest(widget=name):
                source = emitter.render_widget(emitter.load_widget(MANIFEST, name))
                self.assertIn("JS_GetArrayBuffer(ctx, &length, argv[0])", source)
                self.assertIn(f"->{method}(data, length)", source)
                self.assertIn("return JS_NewBool(ctx, 1)", source)
        image = emitter.render_widget(emitter.load_widget(MANIFEST, "Image"))
        self.assertIn("->setSymbol(value)", image)
        gif = emitter.render_widget(emitter.load_widget(MANIFEST, "GIF"))
        self.assertIn("->pause()", gif)
        self.assertIn("->resume()", gif)

    # Check Line point array conversion and C++ method calls.
    def test_line_point_array_conversion(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "Line"))
        self.assertIn("std::vector<lv_point_precise_t> points", source)
        self.assertIn("lv_point_precise_set(&point, x, y)", source)
        self.assertIn("->setPoints(\n        points", source)
        # The handwritten Line defines the background image macro but does not register its public method.
        self.assertNotIn('TJS_CFUNC_DEF("setBackgroundImage"', source)

    # Check that unsupported widgets fail instead of producing incomplete output.
    def test_remaining_widgets_fail_with_reasons_instead_of_partial_output(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for widget in manifest["widgets"]:
            if widget["reactName"] in SUPPORTED:
                continue
            with self.subTest(widget=widget["reactName"]):
                with self.assertRaises(emitter.WidgetEmitterError):
                    emitter.load_widget(MANIFEST, widget["reactName"])

    # Check rejection of unknown conversion rules and invalid method settings.
    def test_unknown_and_invalid_rules_are_rejected(self):
        widget = emitter.load_widget(MANIFEST, "Text")
        variants = []
        for field, value in (("marshal", "unrecognized"),
                             ("cppMethod", "doesNotExist"),
                             ("name", "bad-name")):
            changed = copy.deepcopy(widget)
            changed["cppBinding"]["methods"][0][field] = value
            variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed["cppBinding"]):
                with self.assertRaises(emitter.WidgetEmitterError):
                    emitter.render_widget(changed)
        with self.assertRaises(emitter.WidgetEmitterError):
            emitter.load_widget(MANIFEST, "Window")

    # Check that Input shares Textarea output files and methods.
    def test_input_reuses_textarea_file_and_all_methods(self):
        owner = emitter.load_widget(MANIFEST, "Textarea")
        alias = emitter.load_widget(MANIFEST, "Input")
        self.assertEqual(alias, owner)
        self.assertEqual(emitter.output_path(alias["reactName"]), emitter.output_path("Textarea"))
        self.assertFalse(emitter.output_path("Input").exists())
        methods = {m["name"]: m for m in owner["cppBinding"]["methods"]}
        self.assertEqual(methods["setAutoKeyboard"]["cppMethod"], "setAutoRaiseKeyboard")
        self.assertIn("setOneLine", methods)
        self.assertIn("setMaxLength", methods)

    # Check rejection of unsupported type conversions before C++ generation.
    def test_invalid_cast_is_rejected_before_cpp_output(self):
        widget = emitter.load_widget(MANIFEST, "Dropdownlist")
        direction = next(m for m in widget["cppBinding"]["methods"] if m["name"] == "setDir")
        direction["cast"] = "int); malicious("
        with self.assertRaisesRegex(emitter.WidgetEmitterError, "캐스트"):
            emitter.render_widget(widget)

    # Check Tabs constructor defaults and rejection of invalid defaults.
    def test_tabs_constructor_defaults_and_unsafe_fields(self):
        widget = emitter.load_widget(MANIFEST, "Tabs")
        source = emitter.render_widget(widget)
        self.assertIn("int32_t option_tabSize = 0", source)
        self.assertIn("TabView(uid, option_tabPosition, option_tabSize, nullptr)", source)
        widget["cppBinding"]["constructor"]["arguments"][1]["default"] = "bad();"
        with self.assertRaisesRegex(emitter.WidgetEmitterError, "기본값"):
            emitter.render_widget(widget)

    # Check that CMake metadata reports native directories and shared widget owners.
    def test_cmake_metadata_resolves_native_directory_and_shared_owner(self):
        import cpp_emitter as cli
        import io
        from contextlib import redirect_stdout
        for name, owner, directory in [("Tabs", "Tabs", "tabview"), ("Input", "Textarea", "textarea")]:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["--widget", name, "--describe"]), 0)
            metadata = json.loads(output.getvalue())
            self.assertEqual((metadata["owner"], metadata["nativeDir"]), (owner, directory))


if __name__ == "__main__":
    unittest.main()
