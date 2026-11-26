#!/usr/bin/env python3
# Check that the manifest reader refuses a spec this emitter cannot write.

from __future__ import annotations

import json
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import widget_ts_emitter as ts
from support import base_widget, load, manual, prop, setters_of, write_manifest


class Refusals(unittest.TestCase):

    def test_manual_without_reason_is_refused(self):
        entry = manual("src")
        del entry["reason"]
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[prop("v", "value")], manual=[entry]))
        self.assertIn("reason", str(ctx.exception))

    def test_manual_after_must_name_an_earlier_setter(self):
        """표의 순서가 네이티브 호출 순서다. 끼울 자리가 없으면 거부한다."""
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[prop("v", "value")],
                             manual=[manual("src", after="nothing")]))
        self.assertIn("after", str(ctx.exception))

    def test_compare_on_a_kind_that_ignores_it_is_refused(self):
        """읽지 않는 자리에 적어 두면 조용히 무시된다. 그래서 거부한다."""
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[prop("size", "tuple", "[number, number]",
                                         callStyle="array", compare="loose")]))
        self.assertIn("compare", str(ctx.exception))

    def test_guard_on_a_kind_that_ignores_it_is_refused(self):
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[prop("items", "options", "string[]",
                                         lengthArg=False, guard="number")]))
        self.assertIn("guard", str(ctx.exception))

    def test_old_style_sheet_prop_must_be_declared(self):
        """setStyle 인자 안에 그대로 들어가므로 선언된 prop 이어야 한다."""
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[prop("itemStyle", "styleState", "StyleProps",
                                         styleType="PART_ITEMS",
                                         oldStyleSheetProp="x, isInit: true")]))
        self.assertIn("oldStyleSheetProp", str(ctx.exception))

    def test_unmarked_widget_is_refused(self):
        widget = base_widget(generate={"cpp": False, "ts": False, "nativeClass": False})
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(widget)
        self.assertIn("generate.ts", str(ctx.exception))

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ts.TsEmitterError):
            load(base_widget(props=[prop("x", "telepathy")]))

    def test_create_lifecycle_is_refused(self):
        entry = prop("tabSize", "value")
        entry["lifecycle"] = "create"
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(base_widget(props=[entry]))
        self.assertIn("lifecycle", str(ctx.exception))

    def test_extra_args_to_undeclared_prop_is_refused(self):
        widget = base_widget(props=[
            prop("value", "value", extraArgs=[{"fromProp": "useAnimation"}])])
        with self.assertRaises(ts.TsEmitterError) as ctx:
            load(widget)
        self.assertIn("useAnimation", str(ctx.exception))

    def test_duplicate_prop_is_refused(self):
        widget = base_widget(props=[prop("v", "value"), prop("v", "value")])
        with self.assertRaises(ts.TsEmitterError):
            load(widget)

    def test_ts_type_cannot_close_the_declaration(self):
        widget = base_widget(props=[prop("v", "value", "number; evil: string")])
        with self.assertRaises(ts.TsEmitterError):
            load(widget)

    def test_unknown_widget_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_manifest(Path(folder), base_widget())
            with self.assertRaises(ts.TsEmitterError) as ctx:
                ts.load_widget(path, "Nope")
            self.assertIn("Nope", str(ctx.exception))


# 공개 타입은 이미 쓰이는 모양 그대로 유지되어야 한다.
class PropsType(unittest.TestCase):

    def test_required_prop_has_no_question_mark(self):
        entry = prop("points", "options", "[number, number][]", lengthArg=True)
        entry["required"] = True
        widget = load(base_widget(props=[entry]))
        self.assertIn("  points: [number, number][];", emitter.emit_prop_types(widget))

    def test_optional_is_the_default(self):
        widget = load(base_widget(props=[prop("v", "value")]))
        self.assertIn("  v?: number;", emitter.emit_prop_types(widget))

    def test_doc_comment_is_kept(self):
        entry = prop("v", "value")
        entry["doc"] = "Must be within the defined range"
        widget = load(base_widget(props=[entry]))
        self.assertIn("  /** Must be within the defined range */",
                      emitter.emit_prop_types(widget))

    def test_passive_prop_stays_in_the_type(self):
        widget = load(base_widget(
            props=[prop("options", "options", "string[]", lengthArg=True,
                        extraArgs=[{"fromProp": "infinity", "coerce": "boolean"}])],
            passive=[{"name": "infinity", "tsType": "boolean",
                      "note": "options 가 읽는다"}]))
        types = emitter.emit_prop_types(widget)
        self.assertIn("  infinity?: boolean;", types)
        self.assertNotIn("infinity(", emitter.emit_setters(widget))


# 명세가 ts 로 표시한 위젯은 실제로 생성되어야 한다.
class ShippedManifest(unittest.TestCase):

    def setUp(self):
        self.data = json.loads(ts.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def test_marked_widgets_generate(self):
        marked = [w["reactName"] for w in self.data["widgets"]
                  if (w.get("generate") or {}).get("ts")]
        self.assertTrue(marked, "no widget is marked for TS generation")
        for name in marked:
            with self.subTest(widget=name):
                widget = ts.load_widget(ts.DEFAULT_MANIFEST, name)
                self.assertIn(f"export class {name}Comp", emitter.render_comp(widget))
                self.assertIn(f"tagName = \"{name}\"", emitter.render_config(widget))

    def test_widget_with_manual_props_ships_a_manual_module(self):
        """생성 파일이 ./manual 을 import 하므로 그 파일이 실제로 있어야 한다."""
        root = ts.REPO_DIR / "src/render/react/components"
        for widget in self.data["widgets"]:
            if not (widget.get("generate") or {}).get("ts"):
                continue
            if not widget.get("manual"):
                continue
            with self.subTest(widget=widget["reactName"]):
                self.assertTrue((root / widget["reactName"] / "manual.ts").is_file())


if __name__ == "__main__":
    unittest.main()
