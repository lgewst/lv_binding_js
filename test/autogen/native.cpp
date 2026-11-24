// 실제 위젯의 값, 객체 연결, 입력 경계와 자원 정리를 검사.
#include "engine.hpp"
#ifdef LV_BINDING_GENERATED_COMPONENT_Switch
#include "components/switch.hpp"
#else
#include "native/components/switch/switch.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_View
#include "components/view.hpp"
#else
#include "native/components/view/view.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Button
#include "components/button.hpp"
#else
#include "native/components/button/button.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Text
#include "components/text.hpp"
#else
#include "native/components/text/text.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Checkbox
#include "components/checkbox.hpp"
#else
#include "native/components/checkbox/checkbox.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Slider
#include "components/slider.hpp"
#else
#include "native/components/slider/slider.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_ProgressBar
#include "components/progressbar.hpp"
#else
#include "native/components/progressbar/progressbar.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Keyboard
#include "components/keyboard.hpp"
#else
#include "native/components/keyboard/keyboard.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Textarea
#include "components/textarea.hpp"
#else
#include "native/components/textarea/textarea.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Roller
#include "components/roller.hpp"
#else
#include "native/components/roller/roller.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Dropdownlist
#include "components/dropdownlist.hpp"
#else
#include "native/components/dropdownlist/dropdownlist.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Line
#include "components/line.hpp"
#else
#include "native/components/line/line.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Calendar
#include "components/calendar.hpp"
#else
#include "native/components/calendar/calendar.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_TabView
#include "components/tabview.hpp"
#else
#include "native/components/tabview/tabview.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Mask
#include "components/mask.hpp"
#else
#include "native/components/mask/mask.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Arc
#include "components/arc.hpp"
#else
#include "native/components/arc/arc.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Chart
#include "components/chart.hpp"
#else
#include "native/components/chart/chart.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_Image
#include "components/image.hpp"
#else
#include "native/components/image/image.hpp"
#endif
#ifdef LV_BINDING_GENERATED_COMPONENT_GIF
#include "components/gif.hpp"
#else
#include "native/components/gif/gif.hpp"
#endif
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <type_traits>


static_assert(std::is_same<decltype(&Text::setText), void (Text::*)(std::string&)>::value, "Text signature");
static_assert(std::is_same<decltype(&Checkbox::setText), void (Checkbox::*)(std::string)>::value, "Checkbox signature");
static_assert(std::is_same<decltype(&Slider::setRange), void (Slider::*)(int32_t, int32_t)>::value, "Slider signature");
static_assert(std::is_same<decltype(&ProgressBar::setValue), void (ProgressBar::*)(int32_t, bool)>::value, "ProgressBar signature");
static_assert(std::is_same<decltype(&Keyboard::setTextarea), void (Keyboard::*)(BasicComponent*)>::value, "Keyboard signature");

static_assert(std::has_virtual_destructor<BasicComponent>::value, "virtual destructor");

static const void* watched[2] = {};
static unsigned freed[2] = {};

#if defined(__has_feature)
#if __has_feature(address_sanitizer)
#define LIFETIME_ASAN 1
// ASan이 실제 free 호출을 관찰해 지정한 이미지 버퍼의 해제 횟수를 기록.
extern "C" void __sanitizer_free_hook(const volatile void* pointer) {
    for (unsigned i = 0; i < 2; ++i) {
        if (watched[i] != nullptr && pointer == watched[i]) ++freed[i];
    }
}
#endif
#endif



// JS 이벤트를 등록하지 않는 검사이므로 런타임 접근 불필요.
TJSRuntime* GetRuntime() { return nullptr; }

// 부모 아래의 LVGL 객체 수를 계산.
static size_t objectCount(lv_obj_t* parent) {
    size_t count = 1;
    for (uint32_t i = 0; i < lv_obj_get_child_count(parent); ++i) count += objectCount(lv_obj_get_child(parent, i));
    return count;
}

// 실제 렌더 타이머의 화면 전송 완료를 알림.
static void flush(lv_display_t* display, const lv_area_t*, uint8_t*) {
    lv_display_flush_ready(display);
}


// 이미지 파일을 읽어 갱신 검사에 사용.
static std::vector<uint8_t> readBytes(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    assert(input.good());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

// 관찰할 이미지 자원의 주소와 해제 횟수를 초기화.
static void watch(const void* first, const void* second) {
    watched[0] = first;
    watched[1] = second;
    freed[0] = freed[1] = 0;
}

// ASan에서 두 자원이 각각 한 번 해제됐는지 검사.
static void checkFreed() {
#if LIFETIME_ASAN
    assert(freed[0] == 1 && freed[1] == 1);
#endif
    watched[0] = watched[1] = nullptr;
}

// 기반 포인터 삭제 시 파생 소멸자 실행을 검사.
static void checkVirtualDestructor() {
    struct Probe : BasicComponent {
        bool& destroyed;
        Probe(std::string uid, bool& flag) : BasicComponent(uid), destroyed(flag) {
            instance = lv_obj_create(GetWindowInstance());
        }
        ~Probe() override { destroyed = true; }
    };
    bool destroyed = false;
    BasicComponent* probe = new Probe("lifetime-probe", destroyed);
    delete probe;
    assert(destroyed);
}

// 네 방향 축을 가진 차트를 생성.
static Chart* makeChart(const std::string& uid, lv_obj_t* parent, bool zoom) {
    auto* chart = new Chart(uid, parent);
    lv_obj_set_size(chart->instance, 300, 200);
    chart->setPointNum(3);
    std::vector<std::string> labels = {"A", "B", "C"};
    chart->setLeftAxisLabels(labels);
    chart->setRightAxisLabels(labels);
    chart->setTopAxisLabels(labels);
    chart->setBottomAxisLabels(labels);
    chart->setLeftAxisOption(6, 3, 3, 1, 30);
    chart->setRightAxisOption(6, 3, 3, 1, 30);
    chart->setTopAxisOption(6, 3, 3, 1, 30);
    chart->setBottomAxisOption(6, 3, 3, 1, 30);
    std::vector<axis_data> data = {{255, {10, 30, 20}}};
    chart->setLeftAxisData(data);
    if (zoom) {
        chart->setZoomX(512);
        chart->setZoomY(512);
        assert(chart->alignInstance() != chart->instance);
    }
    return chart;
}

// Switch의 초기 설정과 독립적인 상태 전환을 검사.
static void checkSwitch(Switch* component, lv_obj_t* parent) {
    lv_obj_t* object = component->instance;
    assert(component->type == COMP_TYPE_SWITCH);
    assert(lv_obj_check_type(object, &lv_switch_class));
    assert(lv_obj_get_parent(object) == parent);
    assert(lv_obj_get_group(object) == lv_group_get_default());
    assert(lv_obj_get_user_data(object) == component);
    assert(!lv_obj_has_flag(object, LV_OBJ_FLAG_SCROLL_ON_FOCUS));
    assert(lv_obj_has_flag(object, LV_OBJ_FLAG_EVENT_BUBBLE));
    assert(lv_obj_has_flag(object, LV_OBJ_FLAG_CLICK_FOCUSABLE));
    assert(!lv_obj_has_state(object, LV_STATE_CHECKED));
    assert(!lv_obj_has_state(object, LV_STATE_DISABLED));
    for (int step : {0, 1, 3, 2, 0, 3, 1, 0}) {
        bool checked = (step & 1) != 0;
        bool disabled = (step & 2) != 0;
        component->setValue(checked);
        component->setDisabled(disabled);
        assert(lv_obj_has_state(object, LV_STATE_CHECKED) == checked);
        assert(lv_obj_has_state(object, LV_STATE_DISABLED) == disabled);
    }
    component->initCompStyle(LV_PART_MAIN);
}

// 위젯의 공통 초기 설정과 스타일을 검사.
static void checkInitial(BasicComponent* component, lv_obj_t* parent,
                         ECOMP_TYPE type, const lv_obj_class_t* lv_class, bool style) {
    lv_obj_t* object = component->instance;
    assert(lv_obj_get_parent(object) == parent);
    assert(component->type == type && lv_obj_check_type(object, lv_class));
    assert(lv_obj_get_user_data(object) == component);
    assert(lv_obj_get_group(object) == lv_group_get_default());
    assert(lv_obj_has_flag(object, LV_OBJ_FLAG_EVENT_BUBBLE));
    assert(lv_obj_has_flag(object, LV_OBJ_FLAG_CLICK_FOCUSABLE));
    assert(!lv_obj_has_flag(object, LV_OBJ_FLAG_SCROLL_ON_FOCUS));
    assert((component->style_map.count(LV_PART_MAIN) != 0) == style);
}

// Switch의 기본 부모, 상태와 부모 우선 삭제 검사.
static void testSwitch(int iterations, const std::string& root) {
    (void)root;
    unsigned baseline = objectCount(lv_screen_active());
    for (int i = 0; i < iterations; ++i) {
        auto* component = new Switch("switch-default");
        assert(component->uid == "switch-default");
        checkSwitch(component, GetWindowInstance());
        delete static_cast<BasicComponent*>(component);
        assert(objectCount(lv_screen_active()) == baseline);

        lv_obj_t* parent = lv_obj_create(GetWindowInstance());
        component = new Switch("switch-child", parent);
        checkSwitch(component, parent);
        lv_obj_delete(parent);
        delete static_cast<BasicComponent*>(component);
        assert(objectCount(lv_screen_active()) == baseline);
    }
}

// 단순 위젯의 값, 애니메이션과 객체 연결 검사.
static void testSimple(int iterations, const std::string& root) {
    (void)root;
    unsigned baseline = objectCount(lv_screen_active());
    for (int i = 0; i < iterations; ++i) {
        lv_obj_t* parent = i % 2 ? lv_obj_create(GetWindowInstance()) : nullptr;
        lv_obj_t* expected_parent = parent ? parent : GetWindowInstance();
        auto* view = new View("simple-view", parent);
        auto* button = new Button("simple-button", parent);
        auto* text = new Text("simple-text", parent);
        auto* checkbox = new Checkbox("simple-checkbox", parent);
        auto* slider = new Slider("simple-slider", parent);
        auto* bar = new ProgressBar("simple-bar", parent);
        auto* keyboard = new Keyboard("simple-keyboard", parent);
        checkInitial(view, expected_parent, COMP_TYPE_VIEW, &lv_obj_class, false);
        checkInitial(button, expected_parent, COMP_TYPE_BUTTON, &lv_button_class, true);
        checkInitial(text, expected_parent, COMP_TYPE_TEXT, &lv_label_class, true);
        checkInitial(checkbox, expected_parent, COMP_TYPE_CHECKBOX, &lv_checkbox_class, true);
        checkInitial(slider, expected_parent, COMP_TYPE_SLIDER, &lv_slider_class, true);
        checkInitial(bar, expected_parent, COMP_TYPE_PROGRESSBAR, &lv_bar_class, false);
        checkInitial(keyboard, expected_parent, COMP_TYPE_TEXTAREA, &lv_keyboard_class, false);

        // 문자열을 교체하거나 원본을 바꿔도 LVGL에 저장된 값이 유지되는지 검사.
        for (std::string value : {std::string(""), std::string(u8"한글 Text"), std::string(1024, 'x')}) {
            std::string original = value;
            text->setText(value);
            checkbox->setText(value);
            value.assign("changed after call");
            assert(std::strcmp(lv_label_get_text(text->instance), original.c_str()) == 0);
            assert(std::strcmp(lv_checkbox_get_text(checkbox->instance), original.c_str()) == 0);
        }
        for (int state : {0, 1, 3, 2, 0}) {
            checkbox->setChecked((state & 1) != 0);
            checkbox->setDisabled((state & 2) != 0);
            assert(lv_obj_has_state(checkbox->instance, LV_STATE_CHECKED) == ((state & 1) != 0));
            assert(lv_obj_has_state(checkbox->instance, LV_STATE_DISABLED) == ((state & 2) != 0));
        }

        // 값의 상하한 처리와 Slider의 애니메이션 비활성 호출을 검사.
        slider->setRange(-50, 100);
        bar->setRange(-50, 100);
        assert(lv_slider_get_min_value(slider->instance) == -50);
        assert(lv_slider_get_max_value(slider->instance) == 100);
        assert(lv_bar_get_min_value(bar->instance) == -50);
        assert(lv_bar_get_max_value(bar->instance) == 100);
        for (int32_t value : {-100, -50, -7, 0, 77, 100, 140}) {
            int32_t expected = value < -50 ? -50 : value > 100 ? 100 : value;
            auto animations = lv_anim_count_running();
            slider->setValue(value);
            assert(lv_slider_get_value(slider->instance) == expected);
            assert(lv_anim_count_running() == animations);
            bar->setValue(value, false);
            assert(lv_bar_get_value(bar->instance) == expected);
        }
        bar->setValue(0, false);
        lv_obj_set_style_anim_duration(bar->instance, 100, LV_PART_MAIN);
        auto animations = lv_anim_count_running();
        bar->setValue(80, true);
        assert(lv_bar_get_value(bar->instance) == 80);
        assert(lv_anim_count_running() > animations);
        bar->setValue(20, false);
        assert(lv_bar_get_value(bar->instance) == 20);
        assert(lv_anim_count_running() == animations);

        // Keyboard의 모드와 Textarea 연결, 부모와 자식 연결을 검사.
        auto* textarea = new Textarea("simple-target", parent);
        textarea->setAutoRaiseKeyboard(false);
        keyboard->setTextarea(textarea);
        assert(lv_keyboard_get_textarea(keyboard->instance) == textarea->instance);
        for (int32_t mode : {0, 1, 2, 3, 0}) {
            keyboard->setMode(mode);
            assert(lv_keyboard_get_mode(keyboard->instance) == mode);
        }
        auto* child = new View("simple-child", parent);
        button->appendChild(child);
        assert(lv_obj_get_parent(child->instance) == button->instance);
        view->appendChild(child);
        assert(lv_obj_get_parent(child->instance) == view->instance);

        // 부모가 먼저 삭제된 경우에도 C++ 객체 정리가 안전한지 검사.
        if (parent) lv_obj_delete(parent);
        delete static_cast<BasicComponent*>(keyboard);
        delete static_cast<BasicComponent*>(textarea);
        delete static_cast<BasicComponent*>(child);
        BasicComponent* others[] = {view, button, text, checkbox, slider, bar};
        for (BasicComponent* component : others) {
            delete component;
        }
        assert(objectCount(lv_screen_active()) == baseline);
    }
}

// 배열, 날짜, 탭, 축과 키보드 검사.
static void testComplex(int iterations, const std::string& root) {
    (void)root;
    unsigned baseline = objectCount(lv_screen_active());
    unsigned top_baseline = objectCount(lv_layer_top());
    for (int i = 0; i < iterations; ++i) {
        lv_obj_t* parent = lv_obj_create(GetWindowInstance());
        auto* roller = new Roller("complex-roller", parent);
        std::vector<std::string> options = {"Apple", "Banana", "Cherry"};
        roller->setOptions(options, LV_ROLLER_MODE_NORMAL);
        assert(std::strcmp(lv_roller_get_options(roller->instance), "Apple\nBanana\nCherry") == 0);
        roller->setSelectIndex(2);
        assert(lv_roller_get_selected(roller->instance) == 2);
        roller->setVisibleRowCount(5);
        options.clear(); roller->setOptions(options, LV_ROLLER_MODE_NORMAL);
        assert(std::strcmp(lv_roller_get_options(roller->instance), "") == 0);
        options = {"A", "B"}; roller->setOptions(options, LV_ROLLER_MODE_INFINITE);
        roller->setSelectIndex(1); assert(lv_roller_get_selected(roller->instance) == 1);

        auto* dropdown = new Dropdownlist("complex-dropdown", parent);
        dropdown->setItems(options);
        assert(std::strcmp(lv_dropdown_get_options(dropdown->instance), "A\nB\n") == 0);
        dropdown->setSelectIndex(1); assert(lv_dropdown_get_selected(dropdown->instance) == 1);
        dropdown->setText("Retained label"); assert(std::strcmp(lv_dropdown_get_text(dropdown->instance), "Retained label") == 0);
        dropdown->setDir(LV_DIR_TOP); assert(lv_dropdown_get_dir(dropdown->instance) == LV_DIR_TOP);
        for (int direction : {0, 1, 2, 3}) dropdown->setArrowDir(direction);
        assert(std::strcmp(lv_dropdown_get_symbol(dropdown->instance), LV_SYMBOL_LEFT) == 0);
        dropdown->setHighLightSelect(false); assert(!lv_dropdown_get_selected_highlight(dropdown->instance));
        options.clear(); dropdown->setItems(options); assert(std::strcmp(lv_dropdown_get_options(dropdown->instance), "") == 0);
#ifdef LV_BINDING_GENERATED_COMPONENT_Dropdownlist
        dropdown->setArrowDir(9999);
#endif

        auto* line = new Line("complex-line", parent);
        std::vector<lv_point_precise_t> points = {{0, 0}, {20, 30}};
        line->setPoints(points, 2);
        assert(points.empty() && line->points.size() == 2);
        assert(lv_line_get_points(line->instance) == line->points.data());
        assert(lv_line_get_point_count(line->instance) == 2);
        assert(lv_line_get_points(line->instance)[1].y == 30);

        auto* calendar = new Calendar("complex-calendar", parent);
        calendar->setToday(2026, 11, 22); calendar->setShownMonth(2027, 2);
        assert(lv_calendar_get_today_date(calendar->instance)->day == 22);
        assert(lv_calendar_get_showed_date(calendar->instance)->month == 2);
        std::vector<lv_calendar_date_t> dates = {{2027, 2, 3}, {2027, 2, 5}};
        calendar->setHighlightDates(dates, 2); dates[0].day = 1;
        assert(lv_calendar_get_highlighted_dates_num(calendar->instance) == 2);
        assert(lv_calendar_get_highlighted_dates(calendar->instance) == calendar->highlighted_days.data());
        assert(lv_calendar_get_highlighted_dates(calendar->instance)[0].day == 3);

        auto* tabs = new TabView("complex-tabs", LV_DIR_BOTTOM, 48, parent);
        assert(lv_tabview_get_tab_bar_position(tabs->instance) == LV_DIR_BOTTOM);
        auto* content = new View("complex-content");
        std::string title = "Details"; tabs->setTab(title, content);
        assert(lv_tabview_get_tab_count(tabs->instance) == 1);
        assert(lv_obj_get_parent(content->instance) == lv_obj_get_child(lv_tabview_get_content(tabs->instance), 0));

        auto* mask = new Mask("complex-mask", parent);
        assert(lv_obj_get_parent(mask->instance) == lv_layer_top());
        assert(lv_obj_get_style_width(mask->instance, LV_PART_MAIN) == 1024);
        assert(lv_obj_get_style_height(mask->instance, LV_PART_MAIN) == 600);
        assert(lv_obj_get_style_bg_opa(mask->instance, LV_PART_MAIN) == LV_OPA_70);

        auto* arc = new Arc("complex-arc", parent);
        arc->setRange(-20, 80); arc->setValue(35); arc->setMode(0);
        arc->setStartAngle(20); arc->setEndAngle(270);
        assert(lv_arc_get_min_value(arc->instance) == -20 && lv_arc_get_max_value(arc->instance) == 80);
        assert(lv_arc_get_value(arc->instance) == 35);
        std::string symbol = LV_SYMBOL_OK; arc->setArcImage(nullptr, 0, LV_PART_MAIN, symbol);
        assert(arc->symbol_map.at(LV_PART_MAIN) == symbol);

        auto* text = new Textarea("complex-textarea", parent);
        text->setAutoRaiseKeyboard(false); text->setText("secret"); text->setPlaceHolder("placeholder");
        text->setOneLine(true); text->setPasswordMode(true); text->setMaxLength(20);
        assert(std::strcmp(lv_textarea_get_text(text->instance), "secret") == 0);
        assert(lv_textarea_get_one_line(text->instance) && lv_textarea_get_password_mode(text->instance));
        assert(lv_textarea_get_max_length(text->instance) == 20);
        text->setAutoRaiseKeyboard(true);
        lv_obj_send_event(text->instance, LV_EVENT_FOCUSED, nullptr);
        assert(text->keyboard != nullptr && lv_obj_is_valid(text->keyboard));
        assert(lv_keyboard_get_textarea(text->keyboard) == text->instance);
        lv_obj_send_event(text->instance, LV_EVENT_DEFOCUSED, nullptr);
        assert(text->keyboard == nullptr);
        lv_timer_handler();

        auto* chart = new Chart("complex-chart", parent);
        chart->setPointNum(3); chart->setType(LV_CHART_TYPE_LINE); chart->setDivLineCount(4, 5);
        std::vector<std::string> labels = {"A", "B", "C"};
        chart->setLeftAxisLabels(labels); chart->setRightAxisLabels(labels);
        chart->setTopAxisLabels(labels); chart->setBottomAxisLabels(labels);
        chart->setLeftAxisRange(0, 100); chart->setRightAxisRange(0, 100);
        chart->setTopAxisRange(0, 100); chart->setBottomAxisRange(0, 100);
        chart->setLeftAxisOption(6, 3, 3, 1, 30); chart->setRightAxisOption(6, 3, 3, 1, 30);
        chart->setTopAxisOption(6, 3, 3, 1, 30); chart->setBottomAxisOption(6, 3, 3, 1, 30);
        std::vector<axis_data> data = {{255, {10, 40, 80}}};
        chart->setLeftAxisData(data); chart->setRightAxisData(data);
        chart->setTopAxisData(data); chart->setBottomAxisData(data);
        assert(chart->left_axis.size() == 1 && chart->right_axis.size() == 1);
        assert(chart->top_axis.size() == 1 && chart->bottom_axis.size() == 1);
        for (auto* series : {chart->left_axis[0], chart->right_axis[0], chart->top_axis[0], chart->bottom_axis[0]}) {
            assert(lv_chart_get_series_y_array(chart->instance, series)[1] == 40);
        }
        chart->setType(LV_CHART_TYPE_SCATTER); data[0].data = {10, 20, 30, 40, 50, 60};
        chart->setScatterData(data);
        assert(lv_chart_get_series_x_array(chart->instance, chart->left_axis[0])[2] == 50);
        assert(lv_chart_get_series_y_array(chart->instance, chart->left_axis[0])[2] == 60);
        chart->setZoomX(512); chart->setZoomY(512);
        assert(chart->alignInstance() != chart->instance);

        if (i % 2) lv_obj_delete(parent);
        BasicComponent* widgets[] = {chart, text, arc, mask, content, tabs, calendar, line, dropdown, roller};
        for (auto* component : widgets) delete component;
        if (!(i % 2)) lv_obj_delete(parent);
        lv_timer_handler();
        assert(objectCount(lv_screen_active()) == baseline);
        assert(objectCount(lv_layer_top()) == top_baseline);
    }
}

// 이미지 자원과 Chart의 반복 정리 검사.
static void testLifetime(int iterations, const std::string& root) {
    (void)root;
    auto png = readBytes(root + "/test/assets/icons/01n.png");
    auto gif = readBytes(root + "/test/gif/1/sample.gif");
    const size_t baseline = objectCount(lv_screen_active());
    checkVirtualDestructor();
    for (int i = 0; i < iterations; ++i) {
        auto* image = new Image("native-lifetime-image");
        image->setImageBinary(png.data(), png.size());
        assert(image->image_buf && image->image_desc);
        watch(image->image_buf, image->image_desc);
        delete static_cast<BasicComponent*>(image);
        checkFreed();

        auto* animation = new GIF("native-lifetime-gif");
        animation->setGIFBinary(gif.data(), gif.size());
        animation->pause();
        assert(animation->gif_buf && animation->gif_desc);
        watch(animation->gif_buf, animation->gif_desc);
        delete static_cast<BasicComponent*>(animation);
        checkFreed();

        for (bool zoom : {false, true}) {
            auto* chart = makeChart("native-lifetime-chart", nullptr, zoom);
            delete static_cast<BasicComponent*>(chart);
            assert(objectCount(lv_screen_active()) == baseline);

            lv_obj_t* parent = lv_obj_create(GetWindowInstance());
            chart = makeChart("native-lifetime-orphan", parent, zoom);
            lv_obj_delete(parent);
            delete static_cast<BasicComponent*>(chart);
            assert(objectCount(lv_screen_active()) == baseline);
        }
        assert(comp_map.empty());
        assert(objectCount(lv_screen_active()) == baseline);
    }
}

#if defined(LV_BINDING_GENERATED_COMPONENT_Image) && defined(LV_BINDING_GENERATED_COMPONENT_GIF) && defined(LV_BINDING_GENERATED_COMPONENT_Arc) && defined(LV_BINDING_GENERATED_COMPONENT_Chart) && defined(LV_BINDING_GENERATED_COMPONENT_Textarea)

// 이미지 실패, 빈 축 레이블과 키보드 삭제 검사.
static void testGuards(int iterations, const std::string& root) {
    (void)root;
    auto png = readBytes(root + "/test/assets/icons/01n.png");
    auto gif = readBytes(root + "/test/gif/1/sample.gif");
    unsigned baseline = objectCount(lv_screen_active());
    unsigned top_baseline = objectCount(lv_layer_top());
    for (int i = 0; i < iterations; ++i) {
        auto* image = new Image("guard-image");
        auto* animation = new GIF("guard-gif");
        auto* arc = new Arc("guard-arc");
        uint8_t invalid[32] = {};
        std::string empty;
        for (int update = 0; update < 3; ++update) {
            image->setImageBinary(png.data(), png.size());
            auto* data = image->image_buf;
            auto* description = image->image_desc;
            image->setImageBinary(invalid, 1);
            image->setImageBinary(invalid, sizeof(invalid));
            assert(image->image_buf == data && image->image_desc == description);
            animation->setGIFBinary(gif.data(), gif.size());
            auto* gif_data = animation->gif_buf;
            animation->setGIFBinary(invalid, 2);
            animation->setGIFBinary(invalid, sizeof(invalid));
            assert(animation->gif_buf == gif_data);
            animation->pause(); animation->resume(); animation->pause();
            arc->setArcImage(png.data(), png.size(), LV_PART_MAIN, empty);
            auto* arc_description = arc->image_desc_map.at(LV_PART_MAIN);
            arc->setArcImage(invalid, 1, LV_PART_MAIN, empty);
            arc->setArcImage(invalid, sizeof(invalid), LV_PART_MAIN, empty);
            assert(arc->image_desc_map.at(LV_PART_MAIN) == arc_description);
            lv_timer_handler();
        }
        delete static_cast<BasicComponent*>(animation);
        delete static_cast<BasicComponent*>(image);
        delete static_cast<BasicComponent*>(arc);

        auto* chart = new Chart("guard-chart");
        std::vector<std::string> labels = {std::string(300, 'A'), std::string(300, 'B')};
        chart->setLeftAxisLabels(labels);
        chart->setLeftAxisOption(6, 3, 2, 1, 30);
        labels.clear(); chart->setLeftAxisLabels(labels);
        lv_timer_handler();
        delete static_cast<BasicComponent*>(chart);

        auto* parent = i % 2 ? lv_obj_create(GetWindowInstance()) : nullptr;
        auto* text = new Textarea("guard-textarea", parent);
        text->setMode(LV_KEYBOARD_MODE_NUMBER);
        lv_obj_send_event(text->instance, LV_EVENT_FOCUSED, nullptr);
        assert(text->keyboard != nullptr && lv_obj_is_valid(text->keyboard));
        auto* keyboard = text->keyboard;
        text->setMode(LV_KEYBOARD_MODE_NUMBER);
        assert(lv_keyboard_get_mode(keyboard) == LV_KEYBOARD_MODE_NUMBER);
        lv_obj_send_event(text->instance, LV_EVENT_FOCUSED, nullptr);
        assert(text->keyboard == keyboard);
        text->setAutoRaiseKeyboard(false);
        if (parent) lv_obj_delete(parent);
        delete static_cast<BasicComponent*>(text);
        assert(!lv_obj_is_valid(keyboard));
        assert(lv_obj_get_style_height(GetWindowInstance(), LV_PART_MAIN) == 600);
        lv_timer_handler();
        assert(objectCount(lv_screen_active()) == baseline);
        assert(objectCount(lv_layer_top()) == top_baseline);
    }
}

#endif

// 선택한 검사마다 독립 프로세스에서 같은 LVGL 초기화 사용.
int main(int argc, char** argv) {
    assert(argc == 4);
    const std::string root = argv[1], suite = argv[3];
    const int iterations = std::stoi(argv[2]);
    assert(iterations > 0);
    lv_init();
    auto* display = lv_display_create(1024, 600);
    static uint8_t buffer[1024 * 32 * 4];
    if (suite == "complex" || suite == "guards") {
        lv_display_set_buffers(display, buffer, nullptr, sizeof(buffer), LV_DISPLAY_RENDER_MODE_PARTIAL);
        lv_display_set_flush_cb(display, flush);
    }
    lv_group_set_default(lv_group_create());
    WindowInit();
    if (suite == "switch") testSwitch(iterations, root);
    else if (suite == "simple") testSimple(iterations, root);
    else if (suite == "complex") testComplex(iterations, root);
    else if (suite == "lifetime") testLifetime(iterations, root);
#if defined(LV_BINDING_GENERATED_COMPONENT_Image) && defined(LV_BINDING_GENERATED_COMPONENT_GIF) && defined(LV_BINDING_GENERATED_COMPONENT_Arc) && defined(LV_BINDING_GENERATED_COMPONENT_Chart) && defined(LV_BINDING_GENERATED_COMPONENT_Textarea)
    else if (suite == "guards") testGuards(iterations, root);
#endif
    else { std::fprintf(stderr, "Unsupported native suite: %s\n", suite.c_str()); return 2; }
    std::printf("NATIVE_PASS %s %d\n", suite.c_str(), iterations);
    lv_deinit();
}
