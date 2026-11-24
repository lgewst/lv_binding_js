#!/usr/bin/env python3
# 지원 위젯의 생성 결과와 기존 공개 JS 메서드의 일치 여부를 검사.

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
    # 빈 임시 폴더에 wrapper를 생성한 뒤 기존 공개 메서드와 최신 여부를 검사.
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
                    # JS에 공개하는 메서드 이름 목록을 기준으로 비교.
                    self.assertEqual({m[0] for m in METHOD_RE.findall(manual)},
                                     {m[0] for m in METHOD_RE.findall(generated)})
                    self.assertIn(f"void NativeComponent{native_class}Init", generated)
                    self.assertIn(f"COMP_FINALIZER({native_class}Finalizer", generated)
            self.assertEqual(len(list(Path(folder).glob("*_wrap.cpp"))), 19)

    # Text의 문자열 변환과 C++ 메서드 호출 코드가 생성되는지 검사.
    def test_text_string_conversion(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "Text"))
        self.assertIn("JS_ToCStringLen(ctx, &length, argv[0])", source)
        self.assertIn("->setText(value)", source)

    # View의 자식 연결과 배경 이미지 기능이 생성되는지 검사.
    def test_view_children_and_background_image(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "View"))
        self.assertIn("WRAPPED_APPEND_CHILD(View", source)
        self.assertIn("WRAPPED_INSERT_CHILD(View", source)
        self.assertIn('TJS_CFUNC_DEF("setBackgroundImage"', source)

    # Button과 Mask의 자식 연결은 생성되고 나머지 공통 기능은 각 설정을 따르는지 검사.
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

    # Image와 GIF가 같은 바이트 배열 변환 규칙을 재사용하는지 검사.
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

    # Line의 좌표 배열 변환과 C++ 메서드 호출 코드가 생성되는지 검사.
    def test_line_point_array_conversion(self):
        source = emitter.render_widget(emitter.load_widget(MANIFEST, "Line"))
        self.assertIn("std::vector<lv_point_precise_t> points", source)
        self.assertIn("lv_point_precise_set(&point, x, y)", source)
        self.assertIn("->setPoints(\n        points", source)
        # 수작업 Line의 배경 이미지 기능은 매크로만 정의. 공개 메서드 등록 없음.
        self.assertNotIn('TJS_CFUNC_DEF("setBackgroundImage"', source)

    # 미지원 위젯이 불완전한 결과를 생성하지 않고 오류로 처리되는지 검사.
    def test_remaining_widgets_fail_with_reasons_instead_of_partial_output(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for widget in manifest["widgets"]:
            if widget["reactName"] in SUPPORTED:
                continue
            with self.subTest(widget=widget["reactName"]):
                with self.assertRaises(emitter.WidgetEmitterError):
                    emitter.load_widget(MANIFEST, widget["reactName"])

    # 알 수 없는 변환 규칙과 잘못된 메서드 설정이 거부되는지 검사.
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

    # Input이 Textarea의 생성 파일과 메서드를 그대로 공유하는지 검사.
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

    # 허용하지 않은 타입 변환이 C++ 코드 생성 전에 거부되는지 검사.
    def test_invalid_cast_is_rejected_before_cpp_output(self):
        widget = emitter.load_widget(MANIFEST, "Dropdownlist")
        direction = next(m for m in widget["cppBinding"]["methods"] if m["name"] == "setDir")
        direction["cast"] = "int); malicious("
        with self.assertRaisesRegex(emitter.WidgetEmitterError, "캐스트"):
            emitter.render_widget(widget)

    # Tabs 생성자의 기본값이 적용되고 잘못된 기본값은 거부되는지 검사.
    def test_tabs_constructor_defaults_and_unsafe_fields(self):
        widget = emitter.load_widget(MANIFEST, "Tabs")
        source = emitter.render_widget(widget)
        self.assertIn("int32_t option_tabSize = 0", source)
        self.assertIn("TabView(uid, option_tabPosition, option_tabSize, nullptr)", source)
        widget["cppBinding"]["constructor"]["arguments"][1]["default"] = "bad();"
        with self.assertRaisesRegex(emitter.WidgetEmitterError, "기본값"):
            emitter.render_widget(widget)

    # CMake용 정보에 실제 C++ 폴더와 공유 위젯의 소유자가 표시되는지 검사.
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
