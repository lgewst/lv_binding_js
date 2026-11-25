#!/usr/bin/env python3
# Check one setter shape per behaviour kind, the way the hand-written code writes it.

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import widget_ts_emitter as ts


def write_manifest(folder: Path, widget: dict) -> Path:
    path = folder / "manifest.json"
    path.write_text(json.dumps({"version": 2, "widgets": [widget]}), encoding="utf-8")
    return path


def base_widget(**over) -> dict:
    widget = {
        "reactName": "Demo", "nativeClass": "Demo", "nativeDir": "demo",
        "lvglCreate": "lv_demo_create", "compType": "COMP_TYPE_DEMO",
        "status": "specified",
        "generate": {"cpp": False, "ts": True, "nativeClass": False},
        "props": [], "manual": [],
        "cppBinding": {"features": ["alignment", "movement"]},
    }
    widget.update(over)
    return widget


def prop(name, kind, ts_type="number", **behavior) -> dict:
    entry = {"name": name, "tsType": ts_type, "behavior": {"kind": kind, **behavior}}
    if kind not in ("styleState", "event"):
        entry["bridgeMethod"] = "set" + name[0].upper() + name[1:]
    return entry


def manual(name, ts_type="string", reason="규칙으로 쓸 수 없다", after=None) -> dict:
    entry = {"name": name, "tsType": ts_type, "reason": reason}
    if after is not None:
        entry["after"] = after
    return entry


def load(widget: dict) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        return ts.load_widget(write_manifest(Path(folder), widget), widget["reactName"])


def setters_of(widget: dict) -> str:
    return emitter.emit_setters(load(widget))


# 수작업 코드가 하는 모양대로, kind 마다 한 가지씩.
class SetterShapes(unittest.TestCase):

    def test_state_toggle_compares_against_old_props(self):
        source = setters_of(base_widget(props=[
            prop("checked", "stateToggle", "boolean", state="LV_STATE_CHECKED")]))
        self.assertIn("if (val !== oldProps.checked) {", source)
        self.assertIn("comp.setChecked(val);", source)

    def test_style_state_joins_combined_constants(self):
        source = setters_of(base_widget(props=[
            prop("knobPressedStyle", "styleState", "StyleProps",
                 styleType=["PART_KNOB", "STATE_PRESSED"])]))
        self.assertIn("styleType: STYLE_TYPE.PART_KNOB | STYLE_TYPE.STATE_PRESSED,", source)

    def test_style_state_can_compare_against_another_prop(self):
        widget = base_widget(props=[
            prop("indicatorStyle", "styleState", "StyleProps",
                 styleType="PART_INDICATOR", oldStyleSheetProp="pointStyle"),
            prop("pointStyle", "styleState", "StyleProps", styleType="PART_ITEMS")])
        self.assertIn("oldStyleSheet: oldProps.pointStyle,", setters_of(widget))

    def test_event_registers_the_named_event(self):
        source = setters_of(base_widget(props=[
            prop("onChange", "event", "(e: OnChangeEvent) => void",
                 event="EVENT_VALUE_CHANGED")]))
        self.assertIn("handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_VALUE_CHANGED);", source)

    # guard 가 모양을, compare 가 연산자를 정한다.
    def test_guarded_value_rejects_before_comparing(self):
        source = setters_of(base_widget(props=[
            prop("value", "value", guard="number", compare="loose")]))
        self.assertIn("if (isNaN(val)) return;", source)
        self.assertIn("if (val == oldProps.value) return;", source)

    def test_unguarded_value_uses_a_block(self):
        source = setters_of(base_widget(props=[prop("text", "value", "string")]))
        self.assertIn("if (val !== oldProps.text) {", source)
        self.assertNotIn("isNaN", source)

    def test_loose_compare_uses_loose_operator(self):
        source = setters_of(base_widget(props=[
            prop("title", "value", "string", compare="loose")]))
        self.assertIn("if (val != oldProps.title) {", source)

    def test_extra_args_read_the_other_prop(self):
        widget = base_widget(
            props=[prop("value", "value", compare="strict",
                        extraArgs=[{"fromProp": "useAnimation", "coerce": "boolean"}])],
            passive=[{"name": "useAnimation", "tsType": "boolean", "note": "value 가 읽는다"}])
        self.assertIn("comp.setValue(val, !!newProps.useAnimation);", setters_of(widget))

    def test_array_tuple_destructures_and_guards(self):
        source = setters_of(base_widget(props=[
            prop("range", "tuple", "[number, number]", elements=2, callStyle="array")]))
        self.assertIn("if (!Array.isArray(arr)) return;", source)
        self.assertIn("const [min, max] = arr;", source)
        self.assertIn("if (isNaN(min) || isNaN(max)) return;", source)
        self.assertIn("comp.setRange([min, max]);", source)

    def test_spread_tuple_passes_elements_separately(self):
        source = setters_of(base_widget(props=[
            prop("range", "tuple", "number[]", elements=2, callStyle="spread")]))
        self.assertIn("comp.setRange(arr[0], arr[1]);", source)

    def test_more_than_two_elements_is_refused(self):
        with self.assertRaises(ts.TsEmitterError):
            setters_of(base_widget(props=[
                prop("size", "tuple", "number[]", elements=3, callStyle="array",
                     elementNames=["w", "h"])]))

    def test_options_checks_the_array_before_reading_length(self):
        source = setters_of(base_widget(props=[
            prop("items", "options", "string[]", lengthArg=True)]))
        self.assertIn("if (arr !== oldProps.items && Array.isArray(arr)) {", source)
        self.assertIn("comp.setItems(arr, arr.length);", source)
        # The guard has to come first, or an explicit undefined throws.
        self.assertLess(source.index("Array.isArray(arr)"), source.index("arr.length"))

    def test_options_without_length_argument(self):
        source = setters_of(base_widget(props=[
            prop("items", "options", "string[]", lengthArg=False)]))
        self.assertIn("comp.setItems(arr);", source)

    def test_enum_map_looks_the_value_up(self):
        source = setters_of(base_widget(props=[
            prop("mode", "enumMap", "string", map="modes",
                 mapValues={"normal": "LV_ARC_MODE_NORMAL"})]))
        self.assertIn('typeof modes[val] !== "undefined"', source)
        self.assertIn("comp.setMode(modes[val]);", source)

    def test_enum_map_table_is_generated(self):
        widget = load(base_widget(props=[
            prop("mode", "enumMap", "string", map="modes",
                 mapValues={"normal": "LV_ARC_MODE_NORMAL",
                            "reverse": "LV_ARC_MODE_REVERSE"})]))
        maps = emitter.emit_maps(widget)
        self.assertIn("const modes = {", maps)
        self.assertIn("  normal: lv_conf.LV_ARC_MODE_NORMAL,", maps)
        self.assertIn('import * as lv_conf from "../../core/lv_conf";', emitter.emit_imports(widget))

    def test_enum_map_without_values_is_refused(self):
        widget = load(base_widget(props=[prop("mode", "enumMap", "string", map="modes")]))
        with self.assertRaises(ts.TsEmitterError) as ctx:
            emitter.emit_maps(widget)
        self.assertIn("mapValues", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
