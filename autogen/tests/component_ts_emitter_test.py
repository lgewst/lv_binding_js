#!/usr/bin/env python3
# Check the class body and how the hand-written setters are spliced in.

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import widget_ts_emitter as ts
from support import base_widget, load, manual, prop, setters_of, write_manifest


class ClassBody(unittest.TestCase):

    def body(self, **react_class) -> dict:
        return load(base_widget(props=[prop("v", "value")], reactClass=react_class))

    def test_full_container_delegates_every_hook(self):
        source = emitter.emit_children(self.body(children="full"))
        self.assertIn("super.insertChildBefore(child, beforeChild);", source)
        self.assertIn("this.appendChild(child);", source)
        self.assertIn("super.appendChild(child);", source)

    def test_append_container_only_delegates_append(self):
        source = emitter.emit_children(self.body(children="append"))
        self.assertIn("insertBefore(child, beforeChild) {}", source)
        self.assertIn("appendInitialChild(child) {}", source)
        self.assertIn("super.appendChild(child);", source)

    def test_leaf_keeps_every_hook_empty(self):
        source = emitter.emit_children(self.body(children="none"))
        self.assertIn("appendChild(child) {}", source)
        self.assertNotIn("super.", source)

    def test_unknown_children_mode_is_refused(self):
        with self.assertRaises(ts.TsEmitterError):
            self.body(children="partial")

    def test_movement_can_be_delegated_or_blocked(self):
        self.assertIn("super.moveToFront();", emitter.emit_movement(self.body(movement="delegate")))
        self.assertIn("moveToFront() {}", emitter.emit_movement(self.body(movement="block")))

    def test_close_can_be_blocked(self):
        self.assertIn("super.close();", emitter.emit_close(self.body(close="delegate")))
        self.assertEqual("  close() {}", emitter.emit_close(self.body(close="block")))

    def test_style_reset_sheet_follows_the_spec(self):
        self.assertEqual("{}", emitter.emit_old_sheet(self.body(styleResetOldSheet="{}")))
        self.assertEqual("null", emitter.emit_old_sheet(self.body()))

    def test_unknown_style_reset_sheet_is_refused(self):
        with self.assertRaises(ts.TsEmitterError):
            self.body(styleResetOldSheet="undefined")

    # 생성자에서 부르는 네이티브 메서드
    def test_constructor_calls_are_emitted(self):
        widget = self.body(constructorCalls=[{"method": "setOneLine", "args": ["false"]}])
        self.assertIn("    super.setOneLine(false);", emitter.emit_constructor(widget))

    def test_instance_fields_are_set_in_the_constructor(self):
        widget = self.body(instanceFields={"currentAppendIndex": "0"})
        self.assertEqual("    this.currentAppendIndex = 0;\n",
                         emitter.emit_instance_fields(widget))

    def test_instance_field_value_must_be_a_literal(self):
        with self.assertRaises(ts.TsEmitterError):
            self.body(instanceFields={"x": "evil()"})

    def test_stash_props_are_assigned_before_the_setter_table(self):
        """세터 표는 prop 이 있을 때만 돈다. 자식 훅이 읽는 값은 항상 덮여야 한다."""
        widget = self.body(stashProps=["tabs"])
        self.assertEqual("    this.tabs = newProps.tabs;\n", emitter.emit_stash(widget))

    def test_constructor_argument_must_be_a_literal(self):
        with self.assertRaises(ts.TsEmitterError) as ctx:
            self.body(constructorCalls=[{"method": "setOneLine",
                                         "args": ["evil(); drop()"]}])
        self.assertIn("생성자 인자", str(ctx.exception))


# manual prop 은 생성하지 않고 옆 파일의 수작업 세터를 끼워 쓴다.
class ManualEscapeHatch(unittest.TestCase):

    def widget(self) -> dict:
        return load(base_widget(
            props=[prop("v", "value")],
            manual=[manual("src", reason="3분기 로딩", after="v")]))

    def test_manual_module_is_imported(self):
        self.assertIn('import { manualSetters } from "./manual";',
                      emitter.emit_manual_import(self.widget()))

    def test_manual_setters_keep_their_place_in_the_table(self):
        """표의 순서가 네이티브 호출 순서다. manual 이 앞으로 끌려나오면 순서가 바뀐다."""
        source = emitter.emit_setters(self.widget())
        self.assertIn("    src: manual.src,", source)
        self.assertLess(source.index("v(val)"), source.index("src: manual.src"))

    def test_manual_table_is_built_once(self):
        self.assertEqual("  const manual = manualSetters({ comp, newProps, oldProps });\n",
                         emitter.emit_manual_table(self.widget()))

    def test_manual_prop_stays_in_the_props_type(self):
        self.assertIn("  src?: string;", emitter.emit_prop_types(self.widget()))

    def test_no_import_without_manual_props(self):
        widget = load(base_widget(props=[prop("v", "value")]))
        self.assertEqual("", emitter.emit_manual_import(widget))


if __name__ == "__main__":
    unittest.main()
