#!/usr/bin/env python3
# 복합 위젯의 공통 규칙과 기능 조합, 입력 오류 처리를 검사.

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
    # 공용 명세와 임시 입력 파일을 준비.
    def setUp(self):
        self.root = json.loads(cli.DEFAULT_MANIFEST.read_text())
        self.widgets = {w['reactName']: w for w in self.root['widgets']}
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.manifest = self.path / 'widgets.json'

    # 수정한 명세를 저장하고 생성에 사용할 정보를 반환.
    def load(self, name):
        self.manifest.write_text(json.dumps(self.root))
        return core.load_component(self.manifest, name)

    # 빈 폴더에서 전체 파일 생성, 안내 주석과 공유 별칭의 중복 방지를 검사.
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
                        self.assertEqual(saved.splitlines()[0], '// 자동 생성 파일. 직접 수정 금지.')
                        self.assertEqual(re.findall(r'//[^\n]*|/\*[\s\S]*?\*/', saved),
                                         ['// 자동 생성 파일. 직접 수정 금지.'])
                        outputs.add(path)
            self.assertEqual(len(outputs), 57)
            before = {path: path.read_bytes() for path in outputs}
            self.assertEqual(cli.main(['--manifest', str(self.manifest), '--widget', 'Input', '--target', 'all']), 0)
            self.assertEqual(core.output_paths(self.load('Input')), core.output_paths(self.load('Textarea')))
            self.assertEqual(set((self.path / 'generated').rglob('*.*')), outputs)
            self.assertEqual(before, {path: path.read_bytes() for path in outputs})

    # 배열 보관의 swap과 copy를 서로 다른 위젯이 같은 처리법으로 사용하는지 검사.
    def test_retained_arrays_preserve_storage_strategy(self):
        line, header = core.render_component(self.load('Line'))
        calendar, _ = core.render_component(self.load('Calendar'))
        self.assertIn('std::vector<lv_point_precise_t> points;', header)
        self.assertIn('this->points.swap(points);', line)
        self.assertIn('lv_line_set_points(this->instance, this->points.data(), nums)', line)
        self.assertIn('this->highlighted_days = dates;', calendar)
        self.assertIn('this->highlighted_days.data(), num', calendar)

    # 목록의 마지막 줄바꿈과 빈 목록의 차이가 주문표에서 결정되는지 검사.
    def test_joined_options_preserve_roller_and_dropdown_conventions(self):
        roller, _ = core.render_component(self.load('Roller'))
        dropdown, _ = core.render_component(self.load('Dropdownlist'))
        self.assertIn('if (i + 1 < options.size())', roller)
        self.assertIn('static_cast<lv_roller_mode_t>(mode)', roller)
        self.assertIn('lv_dropdown_clear_options(this->instance)', dropdown)
        self.assertIn('this->text = text;', dropdown)
        self.assertIn('this->text.c_str()', dropdown)
        self.assertIn('default: return;', dropdown)

    # 추가 생성자 인자와 특수 부모 선택을 명세대로 생성하는지 검사.
    def test_constructor_arguments_and_parent_selection(self):
        tabs, header = core.render_component(self.load('Tabs'))
        mask, _ = core.render_component(self.load('Mask'))
        self.assertIn('uint32_t pos, uint32_t size', header)
        self.assertIn('lv_tabview_set_tab_bar_position(this->instance, static_cast<lv_dir_t>(pos))', tabs)
        self.assertIn('lv_tabview_add_tab(this->instance, tab.c_str())', tabs)
        self.assertIn('lv_obj_set_parent(content->instance, page)', tabs)
        self.assertIn('lv_obj_create(lv_layer_top())', mask)
        self.assertIn('lv_display_get_vertical_resolution', mask)

    # 이미지와 GIF가 같은 데이터 교체 처리법과 해제 규칙을 사용하는지 검사.
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

    # 축 처리법을 다른 클래스 이름에서도 원본 C++ 파일 없이 사용하는지 검사.
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

    # 같은 축 처리법이 네 방향의 상수와 보관 멤버를 선택하는지 검사.
    def test_four_axes_use_the_same_rules(self):
        component = self.load('Chart')
        for direction in ('left', 'right', 'top', 'bottom'):
            found = next(m for m in component['methods'] if m['kind'] == 'axisRange' and m['axis'] == direction)
            self.assertIn('this->scale_' + direction, rules.rule_body(found))
            found = next(m for m in component['methods'] if m['kind'] == 'axisData' and m['axis'] == direction)
            self.assertIn('this->' + direction + '_axis', rules.rule_body(found))

    # 생성된 키보드 콜백과 소멸자에 연결 해제 코드가 포함되는지 검사.
    def test_focus_keyboard_cleanup_is_generated(self):
        source, header = core.render_component(self.load('Textarea'))
        self.assertIn('~Textarea() override;', header)
        self.assertIn('lv_obj_remove_event_cb_with_user_data', source)
        self.assertIn('lv_obj_delete(this->keyboard)', source)
        self.assertIn('Textarea::raiseKeyboard', source)
        self.assertIn('Textarea::setMode', source)
        self.assertIn('this->auto_raise_keyboard = payload;', source)

    # 보관한 키보드를 대상으로 호출하고 비어 있는 경우를 검사하는지 확인.
    def test_owned_object_call_uses_member_and_guard(self):
        source, _ = core.render_component(self.load('Textarea'))
        self.assertIn('lv_keyboard_set_mode(this->keyboard,', source)
        self.assertIn('this->keyboard == nullptr || !lv_obj_is_valid(this->keyboard)', source)
        call = next(c for c in self.widgets['Textarea']['cppBinding']['component']['calls'] if c['method'] == 'setMode')
        call['targetMember'] = 'auto_raise_keyboard'
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Textarea')

    # 소유한 객체를 호출할 때 수명 검사를 생략하면 생성 전에 거부하는지 확인.
    def test_owned_object_call_requires_lifetime_guard(self):
        call = next(c for c in self.widgets['Textarea']['cppBinding']['component']['calls'] if c['method'] == 'setMode')
        del call['guard']
        with self.assertRaises(wrapper.WidgetEmitterError):
            self.load('Textarea')

    # 이미지 해제 규칙과 멤버 타입이 빠지면 생성 전에 거부하는지 검사.
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

    # 축 기능이 없거나 축 방향과 인자 종류가 다르면 거부하는지 검사.
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

    # 모르는 처리법, 중복 멤버, 기반 클래스 멤버 충돌을 거부하는지 검사.
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

    # 필수 기능 양식이 없을 때 부분 코드로 넘어가지 않는지 검사.
    def test_missing_feature_template_fails(self):
        component = self.load('Chart')
        with patch.object(rules, 'AUTOGEN_DIR', self.path), self.assertRaises(wrapper.WidgetEmitterError):
            core.render_component(component)


if __name__ == '__main__':
    unittest.main(verbosity=2)
