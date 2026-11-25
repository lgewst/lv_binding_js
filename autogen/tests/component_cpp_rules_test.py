#!/usr/bin/env python3
# Check shared compound widget rules, feature combinations, and invalid inputs.

import contextlib
import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_cpp_emitter as core
import component_cpp_rules as rules
import cpp_emitter as cli
import widget_cpp_emitter as wrapper


class ComplexComponentRulesTest(unittest.TestCase):
    # Prepare the shared manifest and a temporary input file.
    def setUp(self):
        self.root = json.loads(cli.DEFAULT_MANIFEST.read_text())
        self.widgets = {w['reactName']: w for w in self.root['widgets']}
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.manifest = self.path / 'widgets.json'

    # Save the modified manifest and return its component generation data.
    def load(self, name):
        self.manifest.write_text(json.dumps(self.root))
        return core.load_component(self.manifest, name)

    # Check generation into an empty directory, output banners, and shared class deduplication.
    def test_all_nineteen_owners_and_input_alias(self):
        owners = [w for w in self.root['widgets'] if w.get('cppBinding', {}).get('component')]
        self.assertEqual(len(owners), 19)
        outputs = set()
        with patch.object(core, 'AUTOGEN_DIR', self.path), \
                patch.object(cli, 'output_path', side_effect=lambda name: self.path / 'generated' / f'{name.lower()}_wrap.cpp'), \
                contextlib.redirect_stdout(io.StringIO()):
            for raw in owners:
                with self.subTest(widget=raw['reactName']):
                    component = self.load(raw['reactName'])
                    source, header = core.render_component(component)
                    widget = wrapper.load_widget(self.manifest, raw['reactName'], header_source=header)
                    paths = [*core.output_paths(component), cli.output_path(raw['reactName'])]
                    self.assertTrue(all(not path.exists() for path in paths))
                    args = ['--manifest', str(self.manifest), '--widget', raw['reactName'], '--target', 'all']
                    self.assertEqual(cli.main(args), 0)
                    self.assertEqual(cli.main(args + ['--check']), 0)
                    for path, text in zip(paths, (source, header, wrapper.render_widget(widget))):
                        saved = path.read_text(encoding='utf-8')
                        self.assertEqual(saved, text)
                        self.assertEqual(saved.splitlines()[0], '// Generated file. Do not edit.')
                        self.assertEqual(re.findall(r'//[^\n]*|/\*[\s\S]*?\*/', saved),
                                         ['// Generated file. Do not edit.'])
                        outputs.add(path)
            self.assertEqual(len(outputs), 57)
            before = {path: path.read_bytes() for path in outputs}
            self.assertEqual(cli.main(['--manifest', str(self.manifest), '--widget', 'Input', '--target', 'all']), 0)
            self.assertEqual(core.output_paths(self.load('Input')), core.output_paths(self.load('Textarea')))
            self.assertEqual(set((self.path / 'generated').rglob('*.*')), outputs)
            self.assertEqual(before, {path: path.read_bytes() for path in outputs})

    # Check that different widgets reuse the same array copy and swap rules.
    def test_retained_arrays_preserve_storage_strategy(self):
        line, header = core.render_component(self.load('Line'))
        calendar, _ = core.render_component(self.load('Calendar'))
        self.assertIn('std::vector<lv_point_precise_t> points;', header)
        self.assertIn('this->points.swap(points);', line)
        self.assertIn('lv_line_set_points(this->instance, this->points.data(), nums)', line)
        self.assertIn('this->highlighted_days = dates;', calendar)
        self.assertIn('this->highlighted_days.data(), num', calendar)

    # Check that the specification controls trailing separators and empty options.
    def test_joined_options_preserve_roller_and_dropdown_conventions(self):
        roller, _ = core.render_component(self.load('Roller'))
        dropdown, _ = core.render_component(self.load('Dropdownlist'))
        self.assertIn('if (i + 1 < options.size())', roller)
        self.assertIn('static_cast<lv_roller_mode_t>(mode)', roller)
        self.assertIn('lv_dropdown_clear_options(this->instance)', dropdown)
        self.assertIn('this->text = text;', dropdown)
        self.assertIn('this->text.c_str()', dropdown)
        self.assertIn('default: return;', dropdown)

    # Check manifest handling of extra constructor arguments and special parents.
    def test_constructor_arguments_and_parent_selection(self):
        tabs, header = core.render_component(self.load('Tabs'))
        mask, _ = core.render_component(self.load('Mask'))
        self.assertIn('uint32_t pos, uint32_t size', header)
        self.assertIn('lv_tabview_set_tab_bar_position(this->instance, static_cast<lv_dir_t>(pos))', tabs)
        self.assertIn('lv_tabview_add_tab(this->instance, tab.c_str())', tabs)
        self.assertIn('lv_obj_set_parent(content->instance, page)', tabs)
        self.assertIn('lv_obj_create(lv_layer_top())', mask)
        self.assertIn('lv_display_get_vertical_resolution', mask)

    # Check that Image and GIF share image replacement and cleanup rules.
    def test_image_buffer_rule_is_shared_and_releases_both_members(self):
        image = self.load('Image')
        gif = self.load('GIF')
        first = next(m for m in image['methods'] if m['kind'] == 'imageBuffer')
        second = next(m for m in gif['methods'] if m['kind'] == 'imageBuffer')
        a = rules.image_body(first).replace('image_buf', 'media_buf').replace('image_desc', 'media_desc').replace('lv_img_set_src', 'lv_media_set_src')
        b = rules.image_body(second).replace('gif_buf', 'media_buf').replace('gif_desc', 'media_desc').replace('lv_gif_set_src', 'lv_media_set_src')
        self.assertEqual(a, b)
        source, header = core.render_component(image)
        self.assertIn('if (buf == nullptr || len < 13) return;', source)
        self.assertIn('if (next_data == nullptr) { free(next_desc); return; }', source)
        self.assertIn('free(this->image_buf)', source)
        self.assertIn('free(this->image_desc)', source)
        self.assertIn('~Image() override;', header)

    # Check reuse of axis rules under another class name without original C++ files.
    def test_chart_feature_reuses_layout_for_a_new_class(self):
        raw = self.widgets['Chart']
        raw.update(reactName='Plot', nativeClass='Plot', nativeDir='plot')
        self.manifest.write_text(json.dumps(self.root))
        with patch.object(core, 'AUTOGEN_DIR', self.path), \
                patch.object(cli, 'output_path', return_value=self.path / 'plot_wrap.cpp'), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--widget', 'Plot', '--manifest', str(self.manifest), '--target', 'all']), 0)
        source = (self.path / 'generated/components/plot.cpp').read_text()
        self.assertIn('Plot::layoutScales', source)
        self.assertIn('Plot::~Plot', source)
        self.assertNotIn('Chart::', source)
        self.assertIn('Plot::setZoomX', source)

    # Check that shared axis rules select direction-specific constants and stored members.
    def test_four_axes_use_the_same_rules(self):
        component = self.load('Chart')
        for direction in ('left', 'right', 'top', 'bottom'):
            found = next(m for m in component['methods'] if m['kind'] == 'axisRange' and m['axis'] == direction)
            self.assertIn('this->scale_' + direction, rules.rule_body(found))
            found = next(m for m in component['methods'] if m['kind'] == 'axisData' and m['axis'] == direction)
            self.assertIn('this->' + direction + '_axis', rules.rule_body(found))

    # Check that generated keyboard callbacks and destructors detach references.
    def test_focus_keyboard_cleanup_is_generated(self):
        source, header = core.render_component(self.load('Textarea'))
        self.assertIn('~Textarea() override;', header)
        self.assertIn('lv_obj_remove_event_cb_with_user_data', source)
        self.assertIn('lv_obj_delete(this->keyboard)', source)
        self.assertIn('Textarea::raiseKeyboard', source)
        self.assertIn('Textarea::setMode', source)
        self.assertIn('this->auto_raise_keyboard = payload;', source)

    # Check calls on the retained keyboard and guards for a missing keyboard.
    def test_owned_object_call_uses_member_and_guard(self):
        source, _ = core.render_component(self.load('Textarea'))
        self.assertIn('lv_keyboard_set_mode(this->keyboard,', source)
        self.assertIn('this->keyboard == nullptr || !lv_obj_is_valid(this->keyboard)', source)
        call = next(c for c in self.widgets['Textarea']['cppBinding']['component']['calls'] if c['method'] == 'setMode')
        call['targetMember'] = 'auto_raise_keyboard'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Textarea')

    # Check rejection of calls on owned objects without lifetime guards.
    def test_owned_object_call_requires_lifetime_guard(self):
        call = next(c for c in self.widgets['Textarea']['cppBinding']['component']['calls'] if c['method'] == 'setMode')
        del call['guard']
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Textarea')

    # Check rejection of missing image cleanup rules and invalid member types.
    def test_missing_cleanup_or_wrong_member_type_fails(self):
        config = self.widgets['Image']['cppBinding']['component']
        original = copy.deepcopy(config)
        config['freeMembers'] = []
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Image')
        config.update(original)
        config['members'][0]['type'] = 'bytes'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Image')

    # Check rejection of missing axis features and incompatible directions or argument types.
    def test_invalid_axis_configuration_fails(self):
        config = self.widgets['Chart']['cppBinding']['component']
        config['features'] = []
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Chart')
        config['features'] = ['chartLayout']
        axis = next(c for c in config['calls'] if c.get('kind') == 'axisRange')
        axis['axis'] = 'diagonal'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Chart')
        axis['axis'] = 'left'
        axis['kind'] = 'axisData'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Chart')

    # Check rejection of unknown rules, duplicate members, and base class member collisions.
    def test_unknown_rules_and_duplicate_or_inherited_members_fail(self):
        config = self.widgets['Line']['cppBinding']['component']
        original = copy.deepcopy(config)
        config['calls'][0]['kind'] = 'unknown'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Line')
        config.update(copy.deepcopy(original))
        config['members'].append(copy.deepcopy(config['members'][0]))
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Line')
        config.update(original)
        config['members'][0]['name'] = 'instance'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Line')

    # Check that missing required feature templates fail instead of producing partial code.
    def test_missing_feature_template_fails(self):
        component = self.load('Chart')
        with patch.object(rules, 'AUTOGEN_DIR', self.path), self.assertRaises(wrapper.WidgetEmitterError):
            core.render_component(component)


if __name__ == '__main__':
    unittest.main(verbosity=2)
