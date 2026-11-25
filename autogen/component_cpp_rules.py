# Generate C++ bodies for compound rules such as arrays, images, and axes.

from string import Template

from widget_cpp_emitter import AUTOGEN_DIR, identifier, require, WidgetEmitterError


FEATURES = {"chartLayout", "focusKeyboard", "overlayStyle"}
AXES = {
    "left": ("LV_SCALE_MODE_VERTICAL_LEFT", "LV_CHART_AXIS_PRIMARY_Y"),
    "right": ("LV_SCALE_MODE_VERTICAL_RIGHT", "LV_CHART_AXIS_SECONDARY_Y"),
    "top": ("LV_SCALE_MODE_HORIZONTAL_TOP", "LV_CHART_AXIS_SECONDARY_X"),
    "bottom": ("LV_SCALE_MODE_HORIZONTAL_BOTTOM", "LV_CHART_AXIS_PRIMARY_X"),
}
RULE_FIELDS = {
    "retainedArray": {"member", "mode", "function"},
    "joinedOptions": {"function", "trailingSeparator", "emptyFunction"},
    "symbolMap": {"function", "mapping"}, "tabChild": {"function"},
    "imageBuffer": {"function", "bufferMember", "descriptorMember"},
    "styleImage": {"function"}, "memberAssign": {"member"},
    "axisRange": {"axis"}, "axisLabels": {"axis"}, "axisOptions": {"axis"},
    "axisData": {"axis"}, "scatterData": set(), "zoom": {"axis"},
}
FEATURE_FILES = {
    "chartLayout": "chart_layout", "focusKeyboard": "focus_keyboard", "overlayStyle": "overlay_style",
}
FEATURE_PARTS = {
    "chartLayout": {"cpp", "public.hpp", "private.hpp", "types.hpp", "ctor.cpp", "dtor.cpp"},
    "focusKeyboard": {"cpp", "public.hpp", "private.hpp", "ctor.cpp", "dtor.cpp"},
    "overlayStyle": {"cpp"},
}


# Load only the required feature templates and substitute the class name.
def feature_part(features: list[str], part: str, native_class: str) -> str:
    chunks = []
    for feature in features:
        prefix = FEATURE_FILES[feature]
        path = AUTOGEN_DIR / "templates/features" / f"{prefix}.{part}.in"
        if part in FEATURE_PARTS[feature]:
            try:
                chunks.append(Template(path.read_text(encoding="utf-8")).substitute(native_class=native_class))
            except (OSError, KeyError, ValueError) as exc:
                raise WidgetEmitterError(f"기능 양식을 읽을 수 없습니다: {path.name}: {exc}") from exc
    return "\n".join(chunks)


# Validate compound rule settings and stored members.
def validate_rule(rule: dict, members: dict, features: list[str], lvgl_name) -> None:
    kind = rule.get("kind")
    require(isinstance(kind, str) and kind in RULE_FIELDS, f"지원하지 않는 복합 처리법입니다: {kind}")
    required = {"method", "kind", "parameters"} | (RULE_FIELDS[kind] - {"emptyFunction"})
    require(required <= set(rule) <= required | {"emptyFunction"}, f"{kind}: 설정 항목이 맞지 않습니다.")
    params = rule["parameters"]
    for field in ("member", "bufferMember", "descriptorMember"):
        if field in rule:
            identifier(rule[field], "보관 멤버")
    if "function" in rule:
        lvgl_name(rule["function"], r"lv_[a-z0-9_]+", "LVGL 함수")
    if kind == "retainedArray":
        require(len(params) == 2 and params[0]["type"] in {"pointsRef", "datesRef"}, "배열과 길이가 필요합니다.")
        require(rule["mode"] in ("copy", "swap"), "배열 보관법은 copy 또는 swap입니다.")
        expected = {"pointsRef": "points", "datesRef": "dates"}[params[0]["type"]]
        require(members.get(rule["member"]) == expected, "보관할 배열 멤버의 타입이 맞지 않습니다.")
    elif kind == "joinedOptions":
        require(params and params[0]["type"] == "stringsRef" and len(params) in (1, 2), "선택지 목록이 필요합니다.")
        require(type(rule["trailingSeparator"]) is bool, "trailingSeparator는 bool이어야 합니다.")
        if rule.get("emptyFunction"):
            lvgl_name(rule["emptyFunction"], r"lv_[a-z0-9_]+", "빈 목록 함수")
    elif kind == "symbolMap":
        require(len(params) == 1 and params[0]["type"] == "int32", "심볼 변환에는 정수 하나가 필요합니다.")
        require(isinstance(rule["mapping"], list) and rule["mapping"], "심볼 대응표가 필요합니다.")
        seen = set()
        for entry in rule["mapping"]:
            require(isinstance(entry, dict) and set(entry) == {"value", "symbol"}
                    and type(entry["value"]) is int and entry["value"] not in seen, "심볼 값이 없거나 중복됩니다.")
            seen.add(entry["value"])
            lvgl_name(entry["symbol"], r"LV_SYMBOL_[A-Z0-9_]+", "심볼")
    elif kind == "tabChild":
        require([p["type"] for p in params] == ["stringRef", "component"], "탭 이름과 자식이 필요합니다.")
    elif kind == "imageBuffer":
        require([p["type"] for p in params] == ["bytes", "size"], "이미지 바이트와 길이가 필요합니다.")
        require(members.get(rule["bufferMember"]) == "bytes"
                and members.get(rule["descriptorMember"]) == "imageDescriptor", "이미지 보관 멤버의 타입이 맞지 않습니다.")
    elif kind == "styleImage":
        require([p["type"] for p in params] == ["bytes", "size", "int32", "stringRef"], "스타일 이미지 인자가 맞지 않습니다.")
    elif kind == "memberAssign":
        require(len(params) == 1 and params[0]["type"] in {"bool", "int32"}
                and members.get(rule["member"]) in {"bool", "int32"}, "대입할 멤버와 인자가 맞지 않습니다.")
    else:
        require("chartLayout" in features, f"{kind}: chartLayout 기능이 필요합니다.")
        expected = {"axisRange": ["int32"] * 2, "axisLabels": ["stringsRef"],
                    "axisOptions": ["int32"] * 5, "axisData": ["axisDataRef"],
                    "scatterData": ["axisDataRef"], "zoom": ["int32"]}[kind]
        require([p["type"] for p in params] == expected, "축 처리법의 인자 타입이 맞지 않습니다.")
        if kind == "zoom":
            require(rule["axis"] in ("x", "y"), "확대 방향은 x 또는 y입니다.")
        elif kind != "scatterData":
            require(isinstance(rule["axis"], str) and rule["axis"] in AXES, "축 방향이 맞지 않습니다.")


# Generate shared bodies that retain arrays or join string options.
def collection_body(method: dict) -> str:
    params = [p["name"] for p in method["parameters"]]
    if method["kind"] == "retainedArray":
        member = method["member"]
        store = f"this->{member}.swap({params[0]});" if method["mode"] == "swap" else f"this->{member} = {params[0]};"
        return f"{store}\n{method['function']}(this->instance, this->{member}.data(), {params[1]});"
    source = params[0]
    extra = f", static_cast<lv_roller_mode_t>({params[1]})" if len(params) == 2 else ""
    separator = 'joined.append("\\n");' if method["trailingSeparator"] else f'if (i + 1 < {source}.size()) joined.append("\\n");'
    body = f'''std::string joined;
for (size_t i = 0; i < {source}.size(); ++i) {{
    joined.append({source}[i].c_str());
    {separator}
}}
{method["function"]}(this->instance, joined.c_str(){extra});'''
    if method.get("emptyFunction"):
        body = f'''if ({source}.empty()) {{
    {method["emptyFunction"]}(this->instance);
    return;
}}
''' + body
    return body


# Release the previous image data and descriptor only after replacement succeeds.
def image_body(method: dict) -> str:
    buf, length = [p["name"] for p in method["parameters"][:2]]
    if method["kind"] == "imageBuffer":
        data, desc = method["bufferMember"], method["descriptorMember"]
        return f'''if ({buf} == nullptr || {length} < 13) return;
auto* next_desc = static_cast<lv_img_dsc_t_1*>(calloc(1, sizeof(lv_img_dsc_t_1)));
if (next_desc == nullptr) return;
uint8_t* next_data = GetImgDesc({buf}, {length}, next_desc);
if (next_data == nullptr) {{ free(next_desc); return; }}
auto* previous_data = this->{data};
auto* previous_desc = this->{desc};
this->{data} = next_data;
this->{desc} = next_desc;
{method["function"]}(this->instance, this->{desc});
free(previous_data);
free(previous_desc);'''
    selector, symbol = [p["name"] for p in method["parameters"][2:]]
    return f'''this->ensureStyle({selector});
lv_style_t* style = this->style_map.at({selector});
if ({buf} != nullptr) {{
    if ({length} < 13) return;
    auto* next = static_cast<lv_img_dsc_t_1*>(calloc(1, sizeof(lv_img_dsc_t_1)));
    if (next == nullptr) return;
    if (GetImgDesc({buf}, {length}, next) == nullptr) {{ free(next); return; }}
    auto found = this->image_desc_map.find({selector});
    auto* previous = found == this->image_desc_map.end() ? nullptr : found->second;
    this->image_desc_map[{selector}] = next;
    {method["function"]}(style, next);
    if (previous != nullptr) {{ free(const_cast<uint8_t*>(previous->dsc.data)); free(previous); }}
}} else {{
    this->symbol_map[{selector}] = {symbol};
    {method["function"]}(style, this->symbol_map[{selector}].c_str());
}}
lv_obj_invalidate(this->instance);'''


# Reuse axis handling bodies with direction-specific ranges, labels, and series.
def axis_body(method: dict) -> str:
    params = [p["name"] for p in method["parameters"]]
    kind = method["kind"]
    if kind == "zoom":
        axis = method["axis"]
        return f'''this->ensureZoomWrapper();
this->zoom_{axis} = {params[0]} > 0 ? {params[0]} : LV_SCALE_NONE;
this->applyZoom();'''
    axis = method.get("axis", "left")
    mode, chart_axis = AXES[axis]
    if kind == "axisRange":
        lo, hi = params
        return f'''lv_chart_set_axis_range(this->instance, {chart_axis}, {lo}, {hi});
if (this->scale_{axis}) lv_scale_set_range(this->scale_{axis}, {lo}, {hi});'''
    if kind == "axisLabels":
        return f'''this->{axis}_axis_labels = {params[0]};
this->applyScaleLabels(this->scale_{axis}, this->{axis}_axis_labels, this->{axis}_label_ptrs);'''
    if kind == "axisOptions":
        return f'''lv_obj_t* scale = this->ensureScale(&this->scale_{axis}, {mode});
this->configureScale(scale, {mode}, {", ".join(params)});
this->applyScaleLabels(scale, this->{axis}_axis_labels, this->{axis}_label_ptrs);'''
    source = params[0]
    setup = f'''for (auto* series : this->{axis}_axis) lv_chart_remove_series(this->instance, series);
this->{axis}_axis.clear();
for (auto& entry : {source}) {{
    this->{axis}_axis.push_back(lv_chart_add_series(this->instance, this->seriesColor(entry.color), {chart_axis}));
}}
'''
    if kind == "axisData":
        return setup + f'''for (size_t i = 0; i < {source}.size(); ++i) this->fillSeriesY(this->{axis}_axis[i], {source}[i].data);
lv_chart_refresh(this->instance);'''
    return setup + f'''uint32_t count = lv_chart_get_point_count(this->instance);
for (size_t i = 0; i < {source}.size(); ++i) {{
    auto* x = lv_chart_get_series_x_array(this->instance, this->left_axis[i]);
    auto* y = lv_chart_get_series_y_array(this->instance, this->left_axis[i]);
    if (x == nullptr || y == nullptr) continue;
    for (size_t j = 0; j < {source}[i].data.size() && j / 2 < count; ++j) {{
        if (j % 2 == 0) x[j / 2] = {source}[i].data[j];
        else y[j / 2] = {source}[i].data[j];
    }}
}}
lv_chart_refresh(this->instance);'''


# Select a compound rule and return the code for its method body.
def rule_body(method: dict) -> str:
    kind = method["kind"]
    params = [p["name"] for p in method["parameters"]]
    if kind in ("retainedArray", "joinedOptions"):
        return collection_body(method)
    if kind in ("imageBuffer", "styleImage"):
        return image_body(method)
    if kind.startswith("axis") or kind in ("scatterData", "zoom"):
        return axis_body(method)
    if kind == "memberAssign":
        return f"this->{method['member']} = {params[0]};"
    if kind == "tabChild":
        return f'''lv_obj_t* page = {method["function"]}(this->instance, {params[0]}.c_str());
lv_obj_set_parent({params[1]}->instance, page);'''
    cases = "\n".join(f'    case {entry["value"]}: symbol = {entry["symbol"]}; break;' for entry in method["mapping"])
    return f'''const void* symbol = nullptr;
switch ({params[0]}) {{
{cases}
    default: return;
}}
{method["function"]}(this->instance, symbol);'''
