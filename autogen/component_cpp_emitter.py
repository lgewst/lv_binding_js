# Generate widget .cpp and .hpp files using shared manifest rules.

from __future__ import annotations

import re
from pathlib import Path
from string import Template
from textwrap import dedent, indent

import component_cpp_rules as rules

from widget_cpp_emitter import (
    AUTOGEN_DIR, WidgetEmitterError, generated_source, identifier, normalize_widget, read_widget, require,
)


TEMPLATE_DIR = AUTOGEN_DIR / "templates"
PARAMETER_TYPES = {
    "bool": "bool", "int32": "int32_t", "string": "std::string",
    "stringRef": "std::string&", "component": "BasicComponent*", "uint32": "uint32_t",
    "lvDir": "lv_dir_t", "bytes": "uint8_t*", "size": "size_t",
    "pointsRef": "std::vector<lv_point_precise_t>&", "datesRef": "std::vector<lv_calendar_date_t>&",
    "stringsRef": "std::vector<std::string>&", "axisDataRef": "std::vector<axis_data>&",
}
MEMBER_TYPES = {"points": "std::vector<lv_point_precise_t>", "dates": "std::vector<lv_calendar_date_t>",
                "string": "std::string", "bytes": "uint8_t*", "imageDescriptor": "lv_img_dsc_t_1*",
                "bool": "bool", "int32": "int32_t", "lvObject": "lv_obj_t*"}
MARSHAL_PARAMETERS = {
    "boolean": [{"bool"}], "string": [{"string", "stringRef"}],
    "int32": [{"int32", "uint32", "lvDir"}], "int32ArrayPair": [{"int32"}, {"int32"}],
    "int32Args2": [{"int32", "uint32"}, {"int32", "uint32"}], "int32Boolean": [{"int32"}, {"bool"}],
    "componentReference": [{"component"}], "noArgs": [],
    "booleanToInt32": [{"int32"}], "arrayBuffer": [{"bytes"}, {"size"}],
    "pointArray": [{"pointsRef"}, {"int32"}], "dateArray": [{"datesRef"}, {"int32"}],
    "stringArray": [{"stringsRef"}], "stringArrayLength": [{"stringsRef"}],
    "stringArrayLengthBoolean": [{"stringsRef"}, {"uint32"}],
    "int32Args3": [{"uint32", "int32"}] * 3, "axisOption": [{"int32"}] * 5,
    "axisData": [{"axisDataRef"}], "stringComponentReference": [{"stringRef"}, {"component"}],
    "arcImage": [{"bytes"}, {"size"}, {"int32"}, {"stringRef"}],
}
ENUM_TYPES = {
    "lv_anim_enable_t": {"bool", "int32"},
    "lv_keyboard_mode_t": {"int32"}, "lv_dir_t": {"int32", "uint32"},
    "lv_arc_mode_t": {"int32"}, "lv_chart_type_t": {"int32"}, "lv_roller_mode_t": {"uint32"},
    "int32_t": {"uint32", "int32"}, "uint32_t": {"uint32", "int32"},
}
# 명세의 operation 값에 대응하는 LVGL 함수. 이름을 조립하면 어느 검사도 그 토큰을
# 볼 수 없으므로 통째로 적는다.
FLAG_OPS = {"add": "lv_obj_add_flag", "clear": "lv_obj_remove_flag"}


# Save generated files in one components directory without widget subdirectories.
def output_paths(component: dict) -> tuple[Path, Path]:
    name = identifier(component["nativeDir"], "C++ 파일 이름")
    folder = AUTOGEN_DIR / "generated/components"
    return folder / f"{name}.cpp", folder / f"{name}.hpp"


# Validate an LVGL identifier and return its original value.
def lvgl_name(value: object, pattern: str, label: str) -> str:
    require(isinstance(value, str) and re.fullmatch(pattern, value) is not None,
            f"{label}: 지원하지 않는 LVGL 이름입니다: {value!r}")
    return value


# Validate constructor groups, flags, and initial styles.
def validate_constructor(constructor: object) -> None:
    require(isinstance(constructor, dict)
            and {"group", "flags", "userData"} <= set(constructor)
            and set(constructor) <= {"group", "flags", "userData", "initStyles", "parent", "parameters", "afterCreate"},
            "component.constructor에는 group, flags, userData 설정이 필요합니다.")
    for label in ("group", "userData"):
        require(type(constructor[label]) is bool, f"{label}은 bool이어야 합니다.")
    require(isinstance(constructor["flags"], list), "flags는 배열이어야 합니다.")
    seen_flags = set()
    for flag in constructor["flags"]:
        require(isinstance(flag, dict) and set(flag) == {"operation", "flag"},
                "각 플래그에는 operation, flag가 필요합니다.")
        require(flag["operation"] in ("add", "clear"), "플래그 처리법은 add 또는 clear입니다.")
        name = lvgl_name(flag["flag"], r"LV_OBJ_FLAG_[A-Z0-9_]+", "객체 플래그")
        require(name not in seen_flags, f"플래그 설정이 중복됩니다: {name}")
        seen_flags.add(name)
    styles = constructor.get("initStyles", [])
    require(isinstance(styles, list), "initStyles는 배열이어야 합니다.")
    seen_styles = set()
    for style in styles:
        lvgl_name(style, r"LV_(?:PART|STATE)_[A-Z0-9_]+", "기본 스타일")
        require(style not in seen_styles, f"기본 스타일이 중복됩니다: {style}")
        seen_styles.add(style)
    require(constructor.get("parent", "parentOrWindow") in ("parentOrWindow", "topLayer"), "생성 부모 규칙이 맞지 않습니다.")
    parameters = constructor.get("parameters", [])
    require(isinstance(parameters, list), "생성자 parameters는 배열이어야 합니다.")
    seen = {"uid", "parent"}
    for parameter in parameters:
        require(isinstance(parameter, dict) and set(parameter) == {"name", "type"}
                and parameter["type"] in ("int32", "uint32"), "생성자 매개변수는 정수만 지원합니다.")
        name = identifier(parameter["name"], "생성자 매개변수")
        require(name not in seen, "생성자 매개변수가 중복됩니다.")
        seen.add(name)
    require(isinstance(constructor.get("afterCreate", []), list), "afterCreate는 배열이어야 합니다.")
    for call in constructor.get("afterCreate", []):
        require(isinstance(call, dict) and set(call) == {"function", "arguments"}, "생성자 호출 설정이 맞지 않습니다.")
        lvgl_name(call["function"], r"lv_[a-z0-9_]+", "생성자 호출")
        require(isinstance(call["arguments"], list), "생성자 호출 arguments는 배열이어야 합니다.")
        for argument in call["arguments"]:
            argument_expression(argument, {p["name"]: p["type"] for p in parameters})


# Validate argument mappings and convert them to C++ expressions.
def argument_expression(argument: object, parameters: dict[str, str], members: dict | None = None) -> str:
    require(isinstance(argument, dict), "각 호출 인자는 객체여야 합니다.")
    if set(argument) == {"constant"}:
        return lvgl_name(argument["constant"], r"LV_[A-Z0-9_]+", "고정 인자")
    if "member" in argument:
        require(set(argument) <= {"member", "as"}, "멤버 인자 설정이 맞지 않습니다.")
        name = identifier(argument["member"], "보관 멤버")
        require(members is not None and name in members, f"없는 멤버입니다: {name}")
        require(argument.get("as") == "cString" and members[name] == "string", "문자열 멤버만 지원합니다.")
        return f"this->{name}.c_str()"
    require({"from"} <= set(argument) <= {"from", "as"}, "호출 인자는 from, as 또는 constant를 사용합니다.")
    name = identifier(argument["from"], "호출 인자")
    require(name in parameters, f"선언하지 않은 호출 인자입니다: {name}")
    conversion = argument.get("as")
    if conversion is None:
        require(parameters[name] in {"bool", "int32", "uint32", "lvDir"}, "문자열과 객체의 전달법을 명시해야 합니다.")
        return name
    require(isinstance(conversion, str), "인자 변환법은 문자열이어야 합니다.")
    if conversion == "cString":
        require(parameters[name] in {"string", "stringRef"}, "cString에는 문자열 인자가 필요합니다.")
        return f"{name}.c_str()"
    if conversion == "instance":
        require(parameters[name] == "component", "instance에는 컴포넌트 인자가 필요합니다.")
        return f"{name}->instance"
    require(conversion in ENUM_TYPES and parameters[name] in ENUM_TYPES[conversion],
            f"지원하지 않는 enum 변환입니다: {conversion}")
    return f"static_cast<{conversion}>({name})"


# Check call arguments against the C++ types passed by the wrapper.
def validate_call(call: object, method: dict, members: dict | None = None, features: list | None = None) -> dict:
    require(isinstance(call, dict) and {"method", "parameters"} <= set(call), "메서드와 매개변수가 필요합니다.")
    parameters = call["parameters"]
    require(isinstance(parameters, list), "parameters는 배열이어야 합니다.")
    require(isinstance(method.get("marshal"), str), "인자 변환법은 문자열이어야 합니다.")
    signature = MARSHAL_PARAMETERS.get(method["marshal"])
    require(signature is not None and len(signature) == len(parameters),
            f"{call['method']}: wrapper의 인자 개수 또는 변환법과 맞지 않습니다.")
    names = {}
    for parameter, allowed in zip(parameters, signature):
        require(isinstance(parameter, dict) and set(parameter) == {"name", "type"},
                "각 매개변수에는 name, type이 필요합니다.")
        name = identifier(parameter["name"], "매개변수")
        kind = parameter["type"]
        require(isinstance(kind, str) and kind in allowed,
                f"{call['method']}.{name}: wrapper의 인자 타입과 맞지 않습니다.")
        require(name not in names, f"매개변수가 중복됩니다: {name}")
        names[name] = kind
    if call.get("kind", "call") != "call":
        rules.validate_rule(call, members or {}, features or [], lvgl_name)
        return dict(call, name=call["method"])
    require({"method", "function", "parameters", "arguments"} <= set(call)
            <= {"method", "function", "parameters", "arguments", "store", "guard", "ifDefined", "kind", "targetMember"},
            "calls 항목의 설정이 맞지 않습니다.")
    lvgl_name(call["function"], r"lv_[a-z0-9_]+", "LVGL 호출 함수")
    arguments = call["arguments"]
    require(isinstance(arguments, list), "arguments는 배열이어야 합니다.")
    expressions = [argument_expression(argument, names, members) for argument in arguments]
    used = {argument["from"] for argument in arguments if "from" in argument}
    if "store" in call:
        store = call["store"]
        require(isinstance(store, dict) and set(store) == {"member", "from"}, "보관 규칙이 맞지 않습니다.")
        require(members is not None and members.get(store["member"]) == "string"
                and names.get(store["from"]) in ("string", "stringRef"), "문자열 보관 규칙이 맞지 않습니다.")
        used.add(store["from"])
    require(call.get("guard") in (None, "instance", "target"), "지원하지 않는 호출 가드입니다.")
    if "targetMember" in call:
        target = identifier(call["targetMember"], "호출 대상 멤버")
        require(members is not None and members.get(target) == "lvObject", "호출 대상은 LVGL 객체 멤버여야 합니다.")
        require(call.get("guard") == "target", "보관한 객체 호출에는 target 가드가 필요합니다.")
    require(call.get("guard") != "target" or "targetMember" in call, "target 가드에 대상 멤버가 필요합니다.")
    if "ifDefined" in call:
        lvgl_name(call["ifDefined"], r"LV_USE_[A-Z0-9_]+", "조건부 기능")
    require(used == set(names), f"{call['method']}: 전달하지 않은 매개변수가 있습니다.")
    return {"kind": "call", "name": call["method"], "function": call["function"],
            "parameters": parameters, "arguments": expressions,
            **{key: call[key] for key in ("store", "guard", "ifDefined", "targetMember") if key in call}}


# Collect generated methods from shared props and C++ call rules.
def component_methods(raw: dict, component: dict, native_class: str) -> list[dict]:
    props = raw.get("props")
    require(isinstance(props, list), "props 배열이 필요합니다.")
    binding_methods = normalize_widget(raw)["cppBinding"]["methods"]
    methods_by_js = {identifier(method["name"], "JS 메서드"): method for method in binding_methods}
    states = {}
    for prop in props:
        behavior = prop.get("behavior")
        require(isinstance(behavior, dict), f"{prop['name']}: behavior가 필요합니다.")
        kind = behavior.get("kind")
        if kind in ("styleState", "event"):
            require(not prop.get("bridgeMethod") and not prop.get("cppMethod"),
                    f"{prop['name']}: 공통 처리 속성에 직접 호출을 지정할 수 없습니다.")
            continue
        if prop.get("lifecycle") == "create":
            continue
        require(kind in ("stateToggle", "value", "tuple", "enumMap", "options")
                and prop.get("lifecycle", "update") == "update"
                and prop.get("bridgeMethod") in methods_by_js,
                f"{prop['name']}: 현재 .cpp/.hpp 생성기가 지원하지 않는 속성입니다.")
        if kind == "stateToggle":
            method = methods_by_js[prop["bridgeMethod"]]
            require(prop.get("tsType") == "boolean" and method["marshal"] == "boolean",
                    "상태 변경에는 boolean 인자가 필요합니다.")
            states[method["cppMethod"]] = lvgl_name(behavior.get("state"), r"LV_STATE_[A-Z0-9_]+", "상태 상수")
    calls = component.get("calls", [])
    require(isinstance(calls, list), "component.calls는 배열이어야 합니다.")
    calls_by_method = {}
    for call in calls:
        require(isinstance(call, dict), "calls의 각 항목은 객체여야 합니다.")
        name = identifier(call.get("method"), "C++ 메서드")
        require(name not in calls_by_method and name not in states, f"호출 규칙이 중복됩니다: {name}")
        calls_by_method[name] = call
    methods = []
    seen = set()
    additional = component.get("nativeMethods", [])
    require(isinstance(additional, list), "nativeMethods는 배열이어야 합니다.")
    for entry in additional:
        require(isinstance(entry, dict) and set(entry) == {"name", "marshal"}, "추가 C++ 메서드 설정이 맞지 않습니다.")
        binding_methods.append({"name": entry["name"], "cppMethod": entry["name"], "marshal": entry["marshal"]})
    members = {m["name"]: m["type"] for m in component.get("members", [])}
    for method in binding_methods:
        name = identifier(method["cppMethod"], "C++ 메서드")
        require(name not in seen | {native_class, "initCompStyle"}, f"C++ 메서드 이름이 충돌합니다: {name}")
        seen.add(name)
        if name in states:
            methods.append({"kind": "stateToggle", "name": name, "state": states[name],
                            "parameters": [{"name": "value", "type": "bool"}]})
        else:
            require(name in calls_by_method, f"{name}: component.calls의 호출 규칙이 필요합니다.")
            methods.append(validate_call(calls_by_method[name], method, members, component.get("features", [])))
    require(set(calls_by_method) <= seen, "선언에 없는 C++ 호출 규칙이 있습니다.")
    return methods


# Validate stored members, feature combinations, cleanup rules, and enums.
def validate_component(component: dict) -> None:
    require({"constructor", "emptyStyleHook"} <= set(component)
            and set(component) <= {"constructor", "emptyStyleHook", "calls", "members", "freeMembers",
                                    "features", "nativeMethods", "enums", "windowsAlias"},
            "component에 지원하지 않는 설정이 있습니다.")
    validate_constructor(component["constructor"])
    require(type(component["emptyStyleHook"]) is bool, "emptyStyleHook은 bool이어야 합니다.")
    features = component.get("features", [])
    require(isinstance(features, list) and all(isinstance(f, str) and f in rules.FEATURES for f in features)
            and len(set(features)) == len(features), "지원하지 않거나 중복된 C++ 기능입니다.")
    require(not (component["emptyStyleHook"] and set(features) & {"focusKeyboard", "overlayStyle"}),
            "스타일 함수를 중복 생성할 수 없습니다.")
    members = component.get("members", [])
    require(isinstance(members, list), "members는 배열이어야 합니다.")
    names = {}
    for member in members:
        require(isinstance(member, dict) and {"name", "type"} <= set(member) <= {"name", "type", "initial"},
                "멤버 설정이 맞지 않습니다.")
        name = identifier(member["name"], "멤버")
        kind = member["type"]
        require(isinstance(kind, str) and kind in MEMBER_TYPES and name not in names, "멤버 타입이 없거나 이름이 중복됩니다.")
        require(name not in {"instance", "uid", "type", "style_map", "image_desc_map", "symbol_map"}, "기반 클래스의 멤버와 충돌합니다.")
        if "initial" in member:
            value = member["initial"]
            require((kind in {"bytes", "imageDescriptor", "lvObject"} and value is None)
                    or (kind == "bool" and type(value) is bool)
                    or (kind == "int32" and type(value) is int and -(2**31) <= value < 2**31),
                    "멤버 초기값이 타입과 맞지 않습니다.")
        names[name] = kind
    free_members = component.get("freeMembers", [])
    require(isinstance(free_members, list) and all(isinstance(n, str) and names.get(n) in {"bytes", "imageDescriptor"} for n in free_members)
            and len(set(free_members)) == len(free_members), "해제할 멤버가 없거나 중복됩니다.")
    if "focusKeyboard" in features:
        require(names.get("keyboard") == "lvObject" and names.get("auto_raise_keyboard") == "bool", "키보드 기능의 멤버가 필요합니다.")
    enums = component.get("enums", [])
    require(isinstance(enums, list), "enums는 배열이어야 합니다.")
    for enum in enums:
        require(isinstance(enum, dict) and set(enum) == {"name", "values"}, "열거형 설정이 맞지 않습니다.")
        identifier(enum["name"], "열거형")
        require(isinstance(enum["values"], list) and enum["values"], "열거값 목록이 필요합니다.")
        for value in enum["values"]:
            identifier(value, "열거값")
        require(len(set(enum["values"])) == len(enum["values"]), "열거값이 중복됩니다.")
    if "windowsAlias" in component:
        identifier(component["windowsAlias"], "Windows 클래스 별칭")


# Load a widget specification and check support for its selected rules.
def load_component(manifest: Path, widget_name: str) -> dict:
    _, raw = read_widget(manifest, widget_name)
    binding = raw.get("cppBinding")
    require(isinstance(binding, dict) and not binding.get("unavailableReason"),
            "사용 가능한 cppBinding 정보가 필요합니다.")
    generate = raw.get("generate")
    require(isinstance(generate, dict) and generate.get("nativeClass") is True,
            f"{raw.get('reactName')}: .cpp/.hpp 생성이 활성화되지 않았습니다.")
    component = binding.get("component")
    require(isinstance(component, dict), "cppBinding.component 설정이 필요합니다.")
    validate_component(component)
    extra = component["constructor"].get("parameters", [])
    wrapper_constructor = binding.get("constructor", {}).get("arguments", [])
    require(len(extra) == max(0, len(wrapper_constructor) - 2), "wrapper와 위젯 생성자의 인자 개수가 다릅니다.")
    native_class = identifier(binding.get("nativeClass", raw.get("nativeClass")), "C++ 클래스")
    source_name = identifier(raw.get("nativeDir", native_class.lower()), "C++ 파일 이름")
    create = lvgl_name(raw.get("lvglCreate"), r"lv_[a-z0-9_]+_create", "생성 함수")
    comp_type = lvgl_name(raw.get("compType"), r"COMP_TYPE_[A-Z0-9_]+", "위젯 타입")
    methods = component_methods(raw, component, native_class)
    for method in methods:
        if method["kind"] == "imageBuffer":
            require({method["bufferMember"], method["descriptorMember"]}
                    <= set(component.get("freeMembers", [])), "이미지 보관 멤버의 해제 규칙이 필요합니다.")
    return {"reactName": raw["reactName"], "nativeClass": native_class, "nativeDir": source_name,
            "lvglCreate": create, "compType": comp_type, "constructor": component["constructor"],
            "emptyStyleHook": component["emptyStyleHook"], "methods": methods, "component": component}


# Build a parameter list shared by declarations and definitions.
def parameter_list(method: dict) -> str:
    return ", ".join(f'{PARAMETER_TYPES[p["type"]]} {p["name"]}' for p in method["parameters"])


# Generate a bool method that adds or clears a state.
def state_method(native_class: str, method: dict) -> str:
    return f'''void {native_class}::{method["name"]}(bool value) {{
    if (value) {{
        lv_obj_add_state(this->instance, {method["state"]});
    }} else {{
        lv_obj_remove_state(this->instance, {method["state"]});
    }}
}}'''


# Generate an LVGL call using the configured argument mappings.
def call_method(native_class: str, method: dict) -> str:
    target = "this->" + method["targetMember"] if "targetMember" in method else "this->instance"
    arguments = ", ".join([target, *method["arguments"]])
    body = ""
    if method.get("guard"):
        guarded = target if method["guard"] == "target" else "this->instance"
        body += f"if ({guarded} == nullptr || !lv_obj_is_valid({guarded})) return;\n"
    if "store" in method:
        body += f'this->{method["store"]["member"]} = {method["store"]["from"]};\n'
    body += f'{method["function"]}({arguments});'
    if "ifDefined" in method:
        body = f'#if {method["ifDefined"]}\n{body}\n#endif'
    return (f'void {native_class}::{method["name"]}({parameter_list(method)}) {{\n'
            + indent(body, "    ") + '\n}')


# Fill the shared templates with initialization, methods, and features, then return both files.
def render_component(component: dict, template_dir: Path = TEMPLATE_DIR) -> tuple[str, str]:
    native_class = component["nativeClass"]
    constructor = component["constructor"]
    config = component["component"]
    features = config.get("features", [])
    setup = []
    if constructor["group"]:
        setup.append("    lv_group_add_obj(lv_group_get_default(), this->instance);")
    for flag in constructor["flags"]:
        setup.append(f'    {FLAG_OPS[flag["operation"]]}(this->instance, {flag["flag"]});')
    if constructor["userData"]:
        setup.append("    lv_obj_set_user_data(this->instance, this);")
    for style in constructor.get("initStyles", []):
        setup.append(f"    this->initStyle({style});")
    constructor_feature = rules.feature_part(features, "ctor.cpp", native_class)
    if constructor_feature:
        setup.append(constructor_feature.rstrip())
    after_create = []
    for call in constructor.get("afterCreate", []):
        arguments = ["this->instance"] + [argument_expression(a, {p["name"]: p["type"] for p in constructor.get("parameters", [])}) for a in call["arguments"]]
        after_create.append(f'    {call["function"]}({", ".join(arguments)});')
    declarations = [f'    void {method["name"]}({parameter_list(method)});' for method in component["methods"]]
    definitions = []
    for method in component["methods"]:
        if method["kind"] == "stateToggle":
            definitions.append(state_method(native_class, method))
        elif method["kind"] == "call":
            definitions.append(call_method(native_class, method))
        else:
            body = indent(rules.rule_body(method), "    ")
            definitions.append(f'void {native_class}::{method["name"]}({parameter_list(method)}) {{\n{body}\n}}')
    if component["emptyStyleHook"]:
        declarations.append("    void initCompStyle(int32_t type) override;")
        definitions.append(f"void {native_class}::initCompStyle(int32_t type) {{\n    (void)type;\n}}")
    if "overlayStyle" in features:
        declarations.append("    void initCompStyle(int32_t type) override;")
    public = indent(dedent(rules.feature_part(features, "public.hpp", native_class)), "    ")
    private = indent(dedent(rules.feature_part(features, "private.hpp", native_class)), "    ")
    feature_source = rules.feature_part(features, "cpp", native_class)
    if feature_source:
        definitions.append(feature_source.rstrip())
    cleanup = rules.feature_part(features, "dtor.cpp", native_class).strip("\n")
    for member in config.get("freeMembers", []):
        cleanup += f'\n    free(this->{member});\n    this->{member} = nullptr;'
    destructor_declaration = ""
    if cleanup.strip():
        destructor_declaration = f"    ~{native_class}() override;\n"
        definitions.append(f"{native_class}::~{native_class}() {{\n{cleanup}\n}}")
    members = []
    for member in config.get("members", []):
        declaration = f'    {MEMBER_TYPES[member["type"]]} {member["name"]}'
        if "initial" in member or member["type"] in {"bytes", "imageDescriptor", "lvObject"}:
            value = member.get("initial")
            declaration += " = " + ("nullptr" if value is None else str(value).lower())
        members.append(declaration + ";")
    types = rules.feature_part(features, "types.hpp", native_class)
    for enum in config.get("enums", []):
        types += f'enum {enum["name"]} {{ {", ".join(enum["values"])} }};\n'
    if "windowsAlias" in config:
        types += f'#ifdef _WIN32\n#define {native_class} {config["windowsAlias"]}\n#endif\n'
    extra_parameters = "".join(f', {PARAMETER_TYPES[p["type"]]} {p["name"]}' for p in constructor.get("parameters", []))
    parent = "lv_layer_top()" if constructor.get("parent") == "topLayer" else "parent != nullptr ? parent : GetWindowInstance()"
    values = dict(component, setup="\n".join(setup), declarations="\n".join(declarations),
                  definitions="\n\n".join(definitions), constructor_parameters=extra_parameters,
                  parent_expression=parent, after_create="\n".join(after_create) + ("\n" if after_create else ""),
                  type_declarations=types + ("\n" if types else ""),
                  members="\n".join(members) + ("\n" if members else ""),
                  destructor_declaration=destructor_declaration,
                  feature_public=public, feature_private=("\nprivate:\n" + private if private else ""))
    try:
        return tuple(generated_source(Template((template_dir / name).read_text(encoding="utf-8")).substitute(values))
                     for name in ("component.cpp.in", "component.hpp.in"))
    except (OSError, KeyError, ValueError) as exc:
        raise WidgetEmitterError(f"위젯 구현 양식을 채울 수 없습니다: {exc}") from exc
