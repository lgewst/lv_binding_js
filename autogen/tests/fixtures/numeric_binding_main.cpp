// 실제 QuickJS로 JS 값을 만들고 생성 함수가 C++에 전달한 값을 검사.
// Gauge는 전달된 인자를 기록하는 객체이며 LVGL 화면은 별도 실행 파일로 비교.

#include "quickjs.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

enum lv_dir_t { TEST_DIR = 8 };
struct lv_calendar_date_t { uint16_t year; uint8_t month, day; };
struct axis_data { int32_t color; std::vector<int32_t> data; };
struct BasicComponent {};

static JSClassID GaugeClassID;
struct Gauge : BasicComponent {
    int calls = 0;
    int32_t first = 0, second = 0;
    bool flag = false;
    std::string symbol, bytes;
    std::vector<std::string> items;
    std::vector<lv_calendar_date_t> dates;
    std::vector<axis_data> axes;
    std::vector<int32_t> numbers;
    BasicComponent* child = nullptr;
    void setScalar(int32_t v) { ++calls; first = v; }
    void setPair(int32_t a, int32_t b) { ++calls; first = a; second = b; }
    void setMixed(int32_t a, bool b) { ++calls; first = a; flag = b; }
    void setItems(std::vector<std::string>& values) { ++calls; items = values; }
    void setOptions(std::vector<std::string>& values, bool mode) {
        ++calls; items = values; flag = mode;
    }
    void setDirection(lv_dir_t direction) { ++calls; first = direction; }
    void setDateArgs(int32_t y, int32_t m, int32_t d) { ++calls; numbers = {y, m, d}; }
    void setDates(std::vector<lv_calendar_date_t>& values, int32_t count) {
        ++calls; dates = values; first = count;
    }
    void setAxisOptions(int32_t a, int32_t b, int32_t c, int32_t d, int32_t e) {
        ++calls; numbers = {a, b, c, d, e};
    }
    void setAxes(std::vector<axis_data>& values) { ++calls; axes = values; }
    void setChild(BasicComponent* value) { ++calls; child = value; }
    void setNamedChild(std::string& title, BasicComponent* value) { ++calls; symbol = title; child = value; }
    void setImage(uint8_t* data, size_t length, int32_t type, std::string& text) {
        ++calls; first = type; symbol = text;
        bytes = data ? std::string(reinterpret_cast<char*>(data), length) : "";
    }
};
struct COMP_REF { void* comp; };

// Python 공통 생성기로 만든 함수 본문을 이 위치에 포함.
#include "handlers.inc"

static JSValue evaluate(JSContext* ctx, const char* expression) {
    JSValue value = JS_Eval(ctx, expression, strlen(expression), "case.js", JS_EVAL_TYPE_GLOBAL);
    assert(!JS_IsException(value));
    return value;
}

int main(int argc, char** argv) {
    assert(argc == 2);
    JSRuntime* rt = JS_NewRuntime();
    JSContext* ctx = JS_NewContext(rt);
    JS_NewClassID(rt, &GaugeClassID);
    JSClassDef def = {};
    def.class_name = "Gauge";
    assert(JS_NewClass(rt, GaugeClassID, &def) == 0);
    JSValue constructor = evaluate(ctx, "globalThis[Symbol.for('lvgljs')] = {NativeRender:{NativeComponents:{Gauge:function Gauge(){}}}}; globalThis[Symbol.for('lvgljs')].NativeRender.NativeComponents.Gauge");
    JS_SetClassProto(ctx, GaugeClassID, JS_GetPropertyStr(ctx, constructor, "prototype"));
    JS_FreeValue(ctx, constructor);
    Gauge gauge;
    COMP_REF ref = {&gauge};
    JSValue receiver = JS_NewObjectClass(ctx, GaugeClassID);
    JS_SetOpaque(receiver, &ref);
    std::string test = argv[1];
    if (test == "int32") {
        JSValue v = JS_NewFloat64(ctx, 4294967299.9);
        NativeCompScalar(ctx, receiver, 1, &v);
        assert(gauge.first == 3 && gauge.calls == 1);
        JS_FreeValue(ctx, v);
        v = JS_NewString(ctx, "123");
        NativeCompScalar(ctx, receiver, 1, &v);
        NativeCompScalar(ctx, receiver, 0, nullptr);
        assert(gauge.calls == 1);
        JS_FreeValue(ctx, v);
    } else if (test == "arrayPair") {
        JSValue v = evaluate(ctx, "['-50', 99.9]");
        NativeCompArrayPair(ctx, receiver, 1, &v);
        assert(gauge.first == -50 && gauge.second == 99 && gauge.calls == 1);
        JS_FreeValue(ctx, v);
    } else if (test == "args2") {
        JSValue args[] = {JS_NewInt32(ctx, -100), JS_NewFloat64(ctx, 200.9)};
        NativeCompArgsPair(ctx, receiver, 2, args);
        assert(gauge.first == -100 && gauge.second == 200 && gauge.calls == 1);
        NativeCompArgsPair(ctx, receiver, 1, args);
        args[1] = JS_TRUE;
        NativeCompArgsPair(ctx, receiver, 2, args);
        assert(gauge.calls == 1);
    } else if (test == "mixed") {
        JSValue args[] = {JS_NewFloat64(ctx, 70.9), JS_TRUE};
        NativeCompMixed(ctx, receiver, 2, args);
        assert(gauge.first == 70 && gauge.flag && gauge.calls == 1);
        args[1] = JS_FALSE;
        NativeCompMixed(ctx, receiver, 2, args);
        assert(!gauge.flag && gauge.calls == 2);
        args[1] = JS_NewInt32(ctx, 1);
        NativeCompMixed(ctx, receiver, 2, args);
        assert(gauge.calls == 2);
    } else if (test == "image") {
        JSValue args[] = {JS_NULL, JS_NewInt32(ctx, 2), JS_NewStringLen(ctx, "a\0b", 3)};
        JSValue result = NativeCompImage(ctx, receiver, 3, args);
        assert(JS_ToBool(ctx, result) == 1 && gauge.symbol.size() == 3 && gauge.first == 2);
        assert(JS_ToBool(ctx, NativeCompImage(ctx, receiver, 2, args)) == 0);
        assert(gauge.calls == 1); // 기존 wrapper와 동일하게 인자가 두 개인 호출은 처리 생략.
        JS_FreeValue(ctx, args[2]);
        const uint8_t bytes[] = {1, 2, 3, 4};
        args[0] = JS_NewArrayBufferCopy(ctx, bytes, sizeof(bytes));
        args[2] = JS_UNDEFINED;
        result = NativeCompImage(ctx, receiver, 3, args);
        assert(JS_ToBool(ctx, result) == 1 && gauge.bytes.size() == 4 && gauge.symbol.empty());
        JS_FreeValue(ctx, args[0]);
        args[0] = JS_NewObject(ctx); // ArrayBuffer가 아닌 객체는 예외로 처리.
        result = NativeCompImage(ctx, receiver, 3, args);
        assert(JS_IsException(result) && gauge.calls == 2);
        JS_FreeValue(ctx, JS_GetException(ctx));
        JS_FreeValue(ctx, args[0]);
    } else if (test == "exceptions") {
        for (const char* expression : {
            "Object.defineProperty([], 0, {get() {throw Error('first')}})",
            "Object.defineProperty(['5'], 1, {get() {throw Error('second')}})",
            "[Symbol('cannot convert'), '7']"
        }) {
            JSValue v = evaluate(ctx, expression);
            JSValue result = NativeCompArrayPair(ctx, receiver, 1, &v);
            assert(JS_IsException(result) && gauge.calls == 0);
            JS_FreeValue(ctx, JS_GetException(ctx));
            JS_FreeValue(ctx, v);
        }
    } else if (test == "stringArray") {
        JSValue args[] = {evaluate(ctx, "['Apple', 9, '한글', null, 'Last']"), JS_NewInt32(ctx, 5)};
        NativeCompStringList(ctx, receiver, 2, args);
        assert(gauge.calls == 1 && gauge.items == std::vector<std::string>({"Apple", "한글", "Last"}));
        args[1] = JS_NewInt32(ctx, 2);
        NativeCompStringList(ctx, receiver, 2, args);
        assert(gauge.items == std::vector<std::string>({"Apple"}));
        args[1] = JS_NewInt32(ctx, 2147483647); // 실제 배열 길이까지만 순회.
        NativeCompStringList(ctx, receiver, 2, args);
        assert(gauge.calls == 3 && gauge.items.size() == 3);
        args[1] = JS_NewInt32(ctx, -1);
        NativeCompStringList(ctx, receiver, 2, args);
        assert(gauge.calls == 3);
        JS_FreeValue(ctx, args[0]);
    } else if (test == "stringArrayBoolean") {
        JSValue args[] = {evaluate(ctx, "['A','B','C']"), JS_NewInt32(ctx, 3), JS_TRUE};
        NativeCompStringOptions(ctx, receiver, 3, args);
        assert(gauge.calls == 1 && gauge.items.size() == 3 && gauge.flag);
        args[2] = JS_FALSE;
        NativeCompStringOptions(ctx, receiver, 3, args);
        assert(gauge.calls == 2 && !gauge.flag);
        args[2] = JS_NewInt32(ctx, 1);
        NativeCompStringOptions(ctx, receiver, 3, args);
        NativeCompStringOptions(ctx, receiver, 2, args);
        assert(gauge.calls == 2);
        JS_FreeValue(ctx, args[0]);
    } else if (test == "stringArrayException") {
        // 문자열 처리 후 다음 속성 읽기에 실패하면 예외 전달. C++ 호출 생략.
        for (int i = 0; i < 30; ++i) {
            JSValue args[] = {evaluate(ctx, "Object.defineProperty(['ok'],1,{get(){throw Error('item')}})"), JS_NewInt32(ctx, 2)};
            assert(JS_IsException(NativeCompStringList(ctx, receiver, 2, args)));
            JS_FreeValue(ctx, JS_GetException(ctx));
            JS_FreeValue(ctx, args[0]);
        }
        assert(gauge.calls == 0);
    } else if (test == "booleanInt") {
        JSValue v = JS_TRUE;
        NativeCompBooleanInt(ctx, receiver, 1, &v);
        assert(gauge.first == 1 && gauge.calls == 1);
        v = JS_FALSE;
        NativeCompBooleanInt(ctx, receiver, 1, &v);
        assert(gauge.first == 0 && gauge.calls == 2);
        v = JS_NewInt32(ctx, 1);
        NativeCompBooleanInt(ctx, receiver, 1, &v);
        assert(gauge.calls == 2);
    } else if (test == "enumCast") {
        JSValue v = JS_NewInt32(ctx, 8);
        NativeCompDirection(ctx, receiver, 1, &v);
        assert(gauge.calls == 1 && gauge.first == 8);
    } else if (test == "dates") {
        JSValue args[] = {JS_NewInt32(ctx, 2026), JS_NewInt32(ctx, 11), JS_NewInt32(ctx, 16)};
        NativeCompDateArgs(ctx, receiver, 3, args);
        assert(gauge.numbers == std::vector<int32_t>({2026, 11, 16}));
        JSValue input[] = {evaluate(ctx, "[[2026,11,16],['skip',1,1],[2026,12,25],null]"), JS_NewInt32(ctx, 4)};
        NativeCompDates(ctx, receiver, 2, input);
        assert(gauge.first == 2 && gauge.dates.size() == 2 && gauge.dates[1].day == 25);
        JS_FreeValue(ctx, input[0]);
    } else if (test == "axisOptions") {
        JSValue value = evaluate(ctx, "({majorLen:10,minorLen:5,majorNum:6,minorNum:2,drawSize:40})");
        NativeCompAxisOptions(ctx, receiver, 1, &value);
        assert(gauge.numbers == std::vector<int32_t>({10,5,6,2,40}));
        JS_FreeValue(ctx, value);
        value = evaluate(ctx, "['A', 123, true]");
        NativeCompLabels(ctx, receiver, 1, &value);
        assert(gauge.items == std::vector<std::string>({"A","123","true"}));
        JS_FreeValue(ctx, value);
        value = evaluate(ctx, "Object.defineProperty({},'majorLen',{get(){throw Error('field')}})");
        assert(JS_IsException(NativeCompAxisOptions(ctx, receiver, 1, &value)));
        JS_FreeValue(ctx, JS_GetException(ctx)); JS_FreeValue(ctx, value);
    } else if (test == "axes") {
        JSValue value = evaluate(ctx, "[{color:16711680,data:[1,2.9,-3]},{color:255,data:[4,5]}]");
        NativeCompAxes(ctx, receiver, 1, &value);
        assert(gauge.axes.size() == 2 && gauge.axes[0].data == std::vector<int32_t>({1,2,-3}));
        JS_FreeValue(ctx, value);
        for (int i = 0; i < 30; ++i) {
            value = evaluate(ctx, "[{color:1,data:[3]}, {get color(){throw Error('nested')},data:[4]}]");
            assert(JS_IsException(NativeCompAxes(ctx, receiver, 1, &value)));
            JS_FreeValue(ctx, JS_GetException(ctx)); JS_FreeValue(ctx, value);
        }
        assert(gauge.calls == 1);
    } else if (test == "references") {
        Gauge other; COMP_REF other_ref = {&other};
        JSValue child = JS_NewObjectClass(ctx, GaugeClassID);
        JS_SetOpaque(child, &other_ref);
        NativeCompChild(ctx, receiver, 1, &child);
        assert(gauge.child == &other && gauge.calls == 1);
        JSValue args[] = {JS_NewString(ctx, "Tab 1"), child};
        NativeCompNamedChild(ctx, receiver, 2, args);
        assert(gauge.symbol == "Tab 1" && gauge.calls == 2);
        JS_FreeValue(ctx, args[0]);
        other_ref.comp = nullptr;
        assert(JS_IsException(NativeCompChild(ctx, receiver, 1, &child)));
        JS_FreeValue(ctx, JS_GetException(ctx)); JS_FreeValue(ctx, child);
        JSClassID foreign_id = 0; JS_NewClassID(rt, &foreign_id);
        JSClassDef foreign_def = {}; foreign_def.class_name = "OtherNative";
        assert(JS_NewClass(rt, foreign_id, &foreign_def) == 0);
        child = JS_NewObjectClass(ctx, foreign_id);
        JS_SetOpaque(child, reinterpret_cast<void*>(1)); // 클래스 검사 없이 접근하면 충돌하는 포인터를 넣어 잘못된 참조의 차단 여부를 확인.
        assert(JS_IsException(NativeCompChild(ctx, receiver, 1, &child)));
        JS_FreeValue(ctx, JS_GetException(ctx)); JS_FreeValue(ctx, child);
        assert(gauge.calls == 2);
    } else if (test == "closed") {
        JSValue v = JS_NewInt32(ctx, 10);
        ref.comp = nullptr;
        assert(JS_IsUndefined(NativeCompScalar(ctx, receiver, 1, &v)));
        assert(gauge.calls == 0);
    } else {
        assert(false);
    }
    JS_SetOpaque(receiver, nullptr);
    JS_FreeValue(ctx, receiver);
    assert(!JS_HasException(ctx));
    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);
}
