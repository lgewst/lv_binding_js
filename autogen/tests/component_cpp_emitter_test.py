#!/usr/bin/env python3
# Check manifest handling, unsupported inputs, and CLI options for component generation.

import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_cpp_emitter as emitter
import cpp_emitter as cli
import widget_cpp_emitter as wrapper


class ComponentEmitterTest(unittest.TestCase):
    # Prepare the shared Switch specification and a temporary output directory.
    def setUp(self):
        self.root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        self.raw = next(w for w in self.root["widgets"] if w["reactName"] == "Switch")
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.manifest = self.path / "widgets.json"

    # Save the modified manifest and return its component generation data.
    def load(self):
        self.manifest.write_text(json.dumps(self.root), encoding="utf-8")
        return emitter.load_component(self.manifest, self.raw["reactName"])

    # Check constructor initialization of the LVGL object, group, flags, and user data.
    def test_constructor_preserves_initialization(self):
        source, header = emitter.render_component(self.load())
        for fragment in ("lv_switch_create(parent != nullptr ? parent : GetWindowInstance())",
                         "this->type = COMP_TYPE_SWITCH", "this->uid = uid",
                         "lv_group_add_obj(lv_group_get_default(), this->instance)",
                         "lv_obj_remove_flag(this->instance, LV_OBJ_FLAG_SCROLL_ON_FOCUS)",
                         "lv_obj_add_flag(this->instance, LV_OBJ_FLAG_EVENT_BUBBLE)",
                         "lv_obj_add_flag(this->instance, LV_OBJ_FLAG_CLICK_FOCUSABLE)",
                         "lv_obj_set_user_data(this->instance, this)"):
            self.assertIn(fragment, source)
        self.assertIn("parent = nullptr", header)
        self.assertIn("initCompStyle(int32_t type) override", header)

    # Check that changed state constants and C++ names update declarations and definitions.
    def test_state_and_method_names_come_from_manifest(self):
        checked = next(p for p in self.raw["props"] if p["name"] == "checked")
        checked["cppMethod"] = "setPressed"
        checked["behavior"]["state"] = "LV_STATE_PRESSED"
        source, header = emitter.render_component(self.load())
        self.assertIn("void Switch::setPressed(bool value)", source)
        self.assertIn("void setPressed(bool value);", header)
        self.assertIn("lv_obj_add_state(this->instance, LV_STATE_PRESSED)", source)
        self.assertIn("lv_obj_remove_state(this->instance, LV_STATE_PRESSED)", source)
        self.assertNotIn("LV_STATE_CHECKED", source)

    # Reuse existing rules under another class name and generate all three files without an original header.
    def test_new_name_reuses_rules_without_handwritten_header(self):
        self.raw.update(reactName="Gauge", nativeClass="Gauge", nativeDir="gauge",
                        lvglCreate="lv_gauge_create", compType="COMP_TYPE_GAUGE")
        component = self.load()
        with patch.object(emitter, "AUTOGEN_DIR", self.path), \
                patch.object(cli, "output_path", return_value=self.path / "gauge_wrap.cpp"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--manifest", str(self.manifest), "--widget", "Gauge",
                                       "--target", "all"]), 0)
            for path in emitter.output_paths(component):
                path.unlink()
            self.assertEqual(cli.main(["--manifest", str(self.manifest), "--widget", "Gauge",
                                       "--component-header"]), 0)
            self.assertFalse(emitter.output_paths(component)[0].exists())
            self.assertEqual(cli.main(["--manifest", str(self.manifest), "--widget", "Gauge",
                                       "--target", "component"]), 0)
        self.assertIn("class Gauge", (self.path / "generated/components/gauge.hpp").read_text())
        self.assertIn("->setValue(value)", (self.path / "gauge_wrap.cpp").read_text())
        self.assertEqual(component["nativeClass"], "Gauge")

    # Check that disabling initial settings removes only the corresponding code.
    def test_constructor_options_are_not_fixed_to_switch(self):
        config = self.raw["cppBinding"]["component"]
        config.update(constructor={"group": False, "flags": [], "userData": False},
                      emptyStyleHook=False)
        source, header = emitter.render_component(self.load())
        self.assertNotIn("lv_group_add_obj", source)
        self.assertNotIn("lv_obj_add_flag", source)
        self.assertNotIn("lv_obj_set_user_data", source)
        self.assertNotIn("initCompStyle", header + source)

    # Check that unsupported widgets fail clearly without creating files.
    def test_other_widgets_are_explicitly_unsupported(self):
        for name in ("Window", "Canvas"):
            with self.subTest(widget=name), self.assertRaises(wrapper.WidgetEmitterError):
                emitter.load_component(cli.DEFAULT_MANIFEST, name)

    # Check that props unsupported by existing rules are rejected instead of omitted.
    def test_unknown_behavior_and_non_boolean_types_fail(self):
        checked = next(p for p in self.raw["props"] if p["name"] == "checked")
        for field, value in (("kind", "value"), ("kind", "manual"), ("type", "number")):
            with self.subTest(value=value):
                original = copy.deepcopy(checked)
                if field == "kind":
                    checked["behavior"]["kind"] = value
                else:
                    checked["tsType"] = value
                with self.assertRaises(wrapper.WidgetEmitterError):
                    self.load()
                checked.clear()
                checked.update(original)

    # Check rejection of missing settings, typos, invalid bool values, and duplicate flags.
    def test_invalid_component_settings_fail(self):
        config = self.raw["cppBinding"]["component"]
        variants = [dict(config, unknown=True), dict(config, emptyStyleHook=1),
                    dict(config, constructor={}),
                    dict(config, constructor={"group": True, "userData": True,
                                               "flags": [{"operation": "delete", "flag": "LV_OBJ_FLAG_CLICKABLE"}]}),
                    dict(config, constructor={"group": True, "userData": True,
                                               "flags": [config["constructor"]["flags"][0]] * 2})]
        for variant in variants:
            with self.subTest(config=variant):
                self.raw["cppBinding"]["component"] = variant
                with self.assertRaises(wrapper.WidgetEmitterError):
                    self.load()

    # Check rejection of invalid LVGL function and constant names before generation.
    def test_invalid_lvgl_names_fail(self):
        for field, value in (("lvglCreate", "lv_switch_create();"), ("compType", "other")):
            with self.subTest(field=field):
                old = self.raw[field]
                self.raw[field] = value
                with self.assertRaises(wrapper.WidgetEmitterError):
                    self.load()
                self.raw[field] = old
        self.raw["props"][-1]["behavior"]["state"] = "LV_STATE_DISABLED | 1"
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load()

    # Check rejection of duplicate C++ method names and extra methods without rules.
    def test_duplicate_methods_and_missing_call_rules_fail(self):
        self.raw["props"][-1]["cppMethod"] = "setValue"
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load()
        self.raw["props"][-1]["cppMethod"] = "setDisabled"
        self.raw["cppBinding"]["methods"] = [{"name": "customMethod", "marshal": "noArgs",
                                               "cppMethod": "customMethod"}]
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load()

    # Check that generating all three files leaves handwritten files unchanged.
    def test_cli_all_writes_flat_files_and_preserves_originals(self):
        component = self.load()
        manual = wrapper.REPO_DIR / "src/render/native/components/switch"
        before = {f: f.read_bytes() for f in manual.glob("*") if f.is_file()}
        with patch.object(emitter, "AUTOGEN_DIR", self.path), \
                patch.object(cli, "output_path", return_value=self.path / "switch_wrap.cpp"), \
                redirect_stdout(io.StringIO()):
            args = ["--manifest", str(self.manifest), "--target", "all"]
            self.assertEqual(cli.main(args), 0)
            self.assertEqual(cli.main(args + ["--check"]), 0)
            paths = emitter.output_paths(component)
            self.assertEqual([p.name for p in paths], ["switch.cpp", "switch.hpp"])
            self.assertEqual(paths[0].parent, self.path / "generated/components")
            timestamps = [p.stat().st_mtime_ns for p in paths]
            self.assertEqual(cli.main(args), 0)
            self.assertEqual(timestamps, [p.stat().st_mtime_ns for p in paths])
        self.assertEqual(before, {f: f.read_bytes() for f in before})

    # Check that stale headers do not cause check mode to modify any files.
    def test_check_and_describe_do_not_write(self):
        component = self.load()
        with patch.object(emitter, "AUTOGEN_DIR", self.path), \
                redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
            args = ["--manifest", str(self.manifest), "--target", "component"]
            self.assertEqual(cli.main(args + ["--describe"]), 0)
            description = json.loads(stdout.getvalue())
            self.assertTrue(description["componentHeader"].endswith("components/switch.hpp"))
            self.assertFalse(emitter.output_paths(component)[0].exists())
            self.assertEqual(cli.main(args + ["--check"]), 1)
            self.assertEqual(cli.main(args), 0)
            cpp, header = emitter.output_paths(component)
            original = cpp.read_bytes()
            header.write_text("stale")
            self.assertEqual(cli.main(args + ["--check"]), 1)
            self.assertEqual(header.read_text(), "stale")
            self.assertEqual(cpp.read_bytes(), original)

    # Check error reporting for missing or invalid templates.
    def test_bad_template_reports_error(self):
        component = self.load()
        with self.assertRaises(wrapper.WidgetEmitterError):
            emitter.render_component(component, self.path)
        for name in ("component.cpp.in", "component.hpp.in"):
            (self.path / name).write_text("${missing}")
        with self.assertRaises(wrapper.WidgetEmitterError):
            emitter.render_component(component, self.path)

    # Check that wrappers cannot add methods absent from generated headers.
    def test_wrapper_is_validated_against_generated_header(self):
        component = self.load()
        _, header = emitter.render_component(component)
        widget = wrapper.load_widget(self.manifest, "Switch", header_source=header)
        widget["cppBinding"]["methods"][0]["cppMethod"] = "missingMethod"
        with self.assertRaises(wrapper.WidgetEmitterError):
            wrapper.render_widget(widget)


class GenericCallEmitterTest(unittest.TestCase):
    # Prepare a fresh manifest and temporary files to isolate each test.
    def setUp(self):
        self.root = json.loads(cli.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        self.widgets = {w["reactName"]: w for w in self.root["widgets"]}
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.manifest = self.path / "widgets.json"

    # Save the current test manifest and return its component generation data.
    def load(self, name):
        self.manifest.write_text(json.dumps(self.root), encoding="utf-8")
        return emitter.load_component(self.manifest, name)

    # Check that all eight classes share one entry point and a flat output directory.
    def test_all_eight_classes_generate_before_checking_files(self):
        for name in ("Switch", "View", "Button", "Text", "Checkbox", "Slider", "ProgressBar", "Keyboard"):
            with self.subTest(widget=name):
                component = self.load(name)
                source, header = emitter.render_component(component)
                with patch.object(emitter, "AUTOGEN_DIR", self.path), redirect_stdout(io.StringIO()):
                    outputs = emitter.output_paths(component)
                    self.assertTrue(all(not output.exists() for output in outputs))
                    args = ["--manifest", str(self.manifest), "--widget", name, "--target", "component"]
                    self.assertEqual(cli.main(args), 0)
                    self.assertEqual(cli.main(args + ["--check"]), 0)
                    for output, content in zip(outputs, (source, header)):
                        self.assertEqual(output.read_text(encoding="utf-8"), content)
                        self.assertEqual(output.parent.name, "components")
                wrapper.load_widget(self.manifest, name, header_source=header)

    # Check that Text and Checkbox retain their distinct C++ string parameter types.
    def test_shared_string_rule_preserves_reference_and_value_signatures(self):
        text, text_header = emitter.render_component(self.load("Text"))
        checkbox, checkbox_header = emitter.render_component(self.load("Checkbox"))
        self.assertIn("void setText(std::string& str);", text_header)
        self.assertIn("lv_label_set_text(this->instance, str.c_str());", text)
        self.assertIn("void setText(std::string text);", checkbox_header)
        self.assertIn("lv_checkbox_set_text(this->instance, text.c_str());", checkbox)

    # Check that constructors initialize styles only when specified.
    def test_style_initialization_is_selected_by_manifest(self):
        for name in ("Button", "Text", "Checkbox", "Slider"):
            source, _ = emitter.render_component(self.load(name))
            self.assertIn("this->initStyle(LV_PART_MAIN);", source)
        for name in ("Switch", "View", "ProgressBar", "Keyboard"):
            source, _ = emitter.render_component(self.load(name))
            self.assertNotIn("this->initStyle(", source)
        self.widgets["Button"]["cppBinding"]["component"]["constructor"]["initStyles"] = ["LV_STATE_FOCUSED"]
        source, _ = emitter.render_component(self.load("Button"))
        self.assertIn("this->initStyle(LV_STATE_FOCUSED);", source)

    # Check Slider calls with two integer arguments and a fixed animation value.
    def test_integer_pair_and_fixed_argument_are_shared_rules(self):
        source, header = emitter.render_component(self.load("Slider"))
        self.assertIn("void setRange(int32_t min, int32_t max);", header)
        self.assertIn("lv_slider_set_range(this->instance, min, max);", source)
        self.assertIn("lv_slider_set_value(this->instance, value, LV_ANIM_OFF);", source)
        self.widgets["Slider"]["cppBinding"]["component"]["calls"][1]["arguments"][-1]["constant"] = "LV_ANIM_ON"
        source, _ = emitter.render_component(self.load("Slider"))
        self.assertIn("lv_slider_set_value(this->instance, value, LV_ANIM_ON);", source)

    # Check bool and integer enum casts and instance arguments from other widgets.
    def test_enum_and_component_instance_conversions(self):
        source, _ = emitter.render_component(self.load("ProgressBar"))
        self.assertIn("static_cast<lv_anim_enable_t>(use_animation)", source)
        source, header = emitter.render_component(self.load("Keyboard"))
        self.assertIn("void setTextarea(BasicComponent* child);", header)
        self.assertIn("lv_keyboard_set_textarea(this->instance, child->instance);", source)
        self.assertIn("static_cast<lv_keyboard_mode_t>(mode)", source)
        self.assertIn("this->type = COMP_TYPE_TEXTAREA;", source)

    # Check that all C++ methods are generated while preserving TS manual handling records.
    def test_ts_manual_records_do_not_disable_native_generation(self):
        for name, method in (("Text", "setText"), ("Keyboard", "setTextarea")):
            original = copy.deepcopy(self.widgets[name])
            self.assertTrue(original["manual"])
            source, _ = emitter.render_component(self.load(name))
            self.assertIn(f"::{method}(", source)
            self.assertEqual(self.widgets[name], original)

    # Check that renamed string methods and LVGL functions need no generator changes.
    def test_new_class_reuses_call_rule_without_original_header(self):
        raw = self.widgets["Text"]
        raw.update(reactName="Caption", nativeClass="Caption", nativeDir="caption")
        raw["cppBinding"]["methods"][0].update(name="setCaption", cppMethod="setCaption")
        raw["cppBinding"]["component"]["calls"][0]["method"] = "setCaption"
        self.manifest.write_text(json.dumps(self.root))
        with patch.object(emitter, "AUTOGEN_DIR", self.path), \
                patch.object(cli, "output_path", return_value=self.path / "caption_wrap.cpp"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--widget", "Caption", "--manifest", str(self.manifest),
                                       "--target", "all"]), 0)
        source = (self.path / "generated/components/caption.cpp").read_text()
        self.assertIn("void Caption::setCaption(std::string& str)", source)
        self.assertIn("lv_label_set_text(this->instance, str.c_str());", source)

    # Check rejection of missing call rules and rules without wrapper methods.
    def test_missing_and_extra_calls_fail(self):
        config = self.widgets["Text"]["cppBinding"]["component"]
        original = copy.deepcopy(config["calls"])
        config["calls"] = []
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load("Text")
        config["calls"] = original + [dict(original[0], method="missing")]
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load("Text")

    # Check rejection of argument counts or types that conflict with the wrapper.
    def test_parameter_count_and_type_must_match_wrapper(self):
        call = self.widgets["Slider"]["cppBinding"]["component"]["calls"][0]
        original = copy.deepcopy(call["parameters"])
        for value in ([], [{"name": "min", "type": "bool"}, original[1]]):
            call["parameters"] = value
            with self.assertRaises(wrapper.WidgetEmitterError):
                self.load("Slider")

    # Check rejection of missing argument references, invalid conversions, and invalid constants.
    def test_invalid_argument_expressions_fail(self):
        call = self.widgets["Slider"]["cppBinding"]["component"]["calls"][1]
        variants = [[{"from": "missing"}], [{"from": "value", "as": "cString"}],
                    [{"from": "value", "as": "instance"}], [{"constant": "LV_ANIM_OFF()"}],
                    [{"from": "value", "as": "unknown"}], [{"constant": "LV_ANIM_OFF"}]]
        for arguments in variants:
            with self.subTest(arguments=arguments):
                call["arguments"] = arguments
                with self.assertRaises(wrapper.WidgetEmitterError):
                    self.load("Slider")

    # Check rejection of duplicate call rules and overrides of state toggle rules.
    def test_duplicate_calls_and_state_override_fail(self):
        config = self.widgets["Checkbox"]["cppBinding"]["component"]
        config["calls"].append(copy.deepcopy(config["calls"][0]))
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load("Checkbox")
        config["calls"][-1]["method"] = "setChecked"
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load("Checkbox")


if __name__ == "__main__":
    unittest.main(verbosity=2)
