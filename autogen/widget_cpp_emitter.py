# Generate C++ wrappers from manifest conversion rules.
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from string import Template


REPO_DIR = Path(__file__).resolve().parent.parent
AUTOGEN_DIR = REPO_DIR / "autogen"
TEMPLATE = AUTOGEN_DIR / "templates/widget_wrap.cpp.in"
DEFAULT_MANIFEST = REPO_DIR / "scripts/data/widgets_manifest.json"
MARSHAL_KINDS = {
    "boolean", "string", "arrayBuffer", "noArgs", "pointArray", "int32",
    "int32ArrayPair", "int32Args2", "int32Boolean", "arcImage",
    "stringArrayLength", "stringArrayLengthBoolean", "booleanToInt32",
    "int32Args3", "dateArray", "stringArray", "axisOption", "axisData",
    "componentReference", "stringComponentReference",
}
FEATURES = {"children", "backgroundImage", "alignment", "movement", "refresh"}
COMMON_METHODS = {
    "nativeSetStyle", "addEventListener", "removeEventListener", "appendChild",
    "insertChildBefore", "align", "alignTo", "style", "getBoundingClientRect",
    "setBackgroundImage", "moveToFront", "moveToBackground", "scrollIntoView", "close", "refresh",
}


# Define errors for unreadable manifests and unsupported generation rules.
class WidgetEmitterError(ValueError):
    pass


# Stop generation with an explanatory message when a required condition fails.
def require(condition: bool, message: str) -> None:
    if not condition:
        raise WidgetEmitterError(message)


# Remove template comments and add only the generated file banner.
def generated_source(source: str) -> str:
    lines = [line for line in source.splitlines() if not line.lstrip().startswith("//")]
    return "// Generated file. Do not edit.\n" + "\n".join(lines).lstrip("\n") + "\n"


# Validate names used in C++ and JS code and return valid identifiers.
def identifier(value: object, label: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value)
            is not None, f"{label}: 유효한 C++/JS 이름이 아닙니다: {value!r}")
    return value


# Build the output path from the widget name.
def output_path(widget_name: str) -> Path:
    return AUTOGEN_DIR / "generated" / f"{identifier(widget_name, '위젯 이름').lower()}_wrap.cpp"


# Find the requested widget and return its shared owner's manifest data.
def read_widget(manifest_path: Path, widget_name: str) -> tuple[dict, dict]:
    identifier(widget_name, "위젯 이름")
    try:
        root = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WidgetEmitterError(f"manifest를 읽을 수 없습니다: {exc}") from exc
    require(isinstance(root, dict) and isinstance(root.get("widgets"), list),
            "manifest.widgets 배열이 필요합니다.")

    # Use the shared owner for widgets such as Input that share a C++ class.
    visited = set()
    while True:
        require(widget_name not in visited, "cppBinding.sharedWith가 순환합니다.")
        visited.add(widget_name)
        matches = [w for w in root["widgets"]
                   if isinstance(w, dict) and w.get("reactName") == widget_name]
        require(len(matches) == 1, f"{widget_name} 항목은 정확히 하나 있어야 합니다.")
        widget = matches[0]
        binding = widget.get("cppBinding")
        require(isinstance(binding, dict), "cppBinding 정보가 필요합니다.")
        target = binding.get("sharedWith")
        if target is None:
            break
        identifier(target, "공유 위젯 이름")
        require(set(binding) == {"sharedWith"},
                "공유 위젯은 자체 cppBinding을 중복 선언할 수 없습니다.")
        widget_name = target
    return root, widget


# Normalize wrapper metadata and check methods against original or generated headers.
def load_widget(manifest_path: Path, widget_name: str, header_source: str | None = None) -> dict:
    root, widget = read_widget(manifest_path, widget_name)
    normalized = normalize_widget(widget)
    if header_source is not None:
        normalized["generatedHeader"] = header_source
    # Reject unrelated JS objects before interpreting their data as COMP_REF.
    # Accept reference arguments only for native classes registered in the manifest.
    normalized["referenceClasses"] = sorted({
        identifier(w.get("cppBinding", {}).get("nativeClass", w.get("nativeClass")), "참조 클래스")
        for w in root["widgets"] if isinstance(w, dict)
        and isinstance(w.get("cppBinding"), dict) and w.get("nativeDir")
        and not w["cppBinding"].get("unavailableReason")
        and not w["cppBinding"].get("sharedWith")
    })
    validate_widget(normalized, widget["reactName"])
    return normalized


# Combine shared props and C++ extensions into the generated method list.
def normalize_widget(widget: dict) -> dict:
    binding = widget.get("cppBinding")
    require(isinstance(binding, dict), "cppBinding 정보가 필요합니다.")
    require(not binding.get("unavailableReason"),
            f"{widget.get('reactName')}: {binding.get('unavailableReason')}")
    require("sharedWith" not in binding, "공유 위젯은 load_widget으로 읽어야 합니다.")
    props = widget.get("props", [])
    extra = binding.get("methods", [])
    require(isinstance(props, list) and all(isinstance(p, dict) for p in props),
            "props는 객체 배열이어야 합니다.")
    require(isinstance(extra, list), "cppBinding.methods는 배열이어야 합니다.")
    prop_names = [p.get("name") for p in props]
    require(all(isinstance(n, str) for n in prop_names)
            and len(set(prop_names)) == len(prop_names), "props 이름이 없거나 중복됩니다.")
    overrides = {}
    additions = []
    for entry in extra:
        require(isinstance(entry, dict), "각 메서드는 객체여야 합니다.")
        require(set(entry) <= {"prop", "name", "cppMethod", "marshal", "returns",
                               "cast", "unavailableReason", "referenceClass"},
                "cppBinding.methods에 알 수 없는 필드가 있습니다.")
        require(("prop" in entry) != ("name" in entry),
                "메서드는 prop 참조 또는 name 중 하나만 지정해야 합니다.")
        if "prop" in entry:
            prop_name = identifier(entry["prop"], "참조 prop")
            require(prop_name in prop_names and prop_name not in overrides,
                    f"없거나 중복된 prop 참조: {prop_name}")
            overrides[prop_name] = entry
        else:
            additions.append(entry)

    methods = []
    for prop in props:
        behavior = prop.get("behavior", {})
        require(isinstance(behavior, dict), "prop.behavior는 객체여야 합니다.")
        kind = behavior.get("kind")
        # Handle styles and events through shared macros, and constructor props in the constructor.
        # Include extra calls for TS manual props through the additions below.
        direct = (prop.get("bridgeMethod") is not None
                  and prop.get("lifecycle", "update") == "update"
                  and kind not in {"styleState", "event"})
        override = overrides.get(prop["name"], {})
        require(direct or not override, f"직접 호출이 아닌 prop을 보완했습니다: {prop['name']}")
        if not direct:
            continue
        require(not override.get("unavailableReason"),
                f"{widget.get('reactName')}.{prop['name']}: {override.get('unavailableReason')}")
        marshal = override.get("marshal")
        if marshal is None:
            if kind == "stateToggle" or prop.get("tsType") == "boolean":
                marshal = "boolean"
            elif kind == "enumMap":
                marshal = "int32"
            elif kind == "value" and prop.get("tsType") == "string":
                marshal = "string"
        # Require explicit conversion rules for numbers and arrays with different native representations.
        # Require a manifest rule when the conversion cannot be determined.
        require(marshal is not None, f"{prop['name']}: marshal을 명시해야 합니다.")
        method = {"name": prop["bridgeMethod"],
                  "cppMethod": override.get("cppMethod", prop.get("cppMethod", prop["bridgeMethod"])),
                  "marshal": marshal}
        for key in ("returns", "cast", "referenceClass"):
            if key in override:
                method[key] = override[key]
        methods.append(method)
    methods.extend(deepcopy(additions))
    native_class = identifier(binding.get("nativeClass", widget.get("nativeClass")), "C++ 클래스")
    result = {"reactName": widget.get("reactName"),
            "nativeClass": native_class,
            "nativeDir": widget.get("nativeDir", native_class.lower()),
            "cppBinding": {"features": deepcopy(binding.get("features")), "methods": methods}}
    if "constructor" in binding:
        result["cppBinding"]["constructor"] = deepcopy(binding["constructor"])
    if "component" in binding:
        result["componentHeader"] = True
    return result


# Validate widget settings, supported conversions, and C++ method names.
# Check argument counts and types in the final C++ build.
def validate_widget(widget: dict, widget_name: str) -> None:
    require(isinstance(widget, dict), "위젯 정보는 객체여야 합니다.")
    identifier(widget_name, "위젯 이름")
    require(widget.get("reactName") == widget_name, "React 이름이 요청한 위젯과 다릅니다.")
    native_class = identifier(widget.get("nativeClass"), "C++ 클래스")
    binding = widget.get("cppBinding")
    require(isinstance(binding, dict), "cppBinding 정보가 필요합니다.")
    features = binding.get("features")
    methods = binding.get("methods")
    require(isinstance(features, list)
            and all(isinstance(f, str) and f in FEATURES for f in features)
            and len(features) == len(set(features)),
            "알 수 없거나 중복된 cppBinding.features가 있습니다.")
    require(isinstance(methods, list), "cppBinding.methods 배열이 필요합니다.")
    constructor_parts(binding.get("constructor"))

    # Check that method names exist in the actual C++ header.
    # Leave parameter type checking to the final C++ build; this check inspects names only.
    source_name = identifier(widget.get("nativeDir", native_class.lower()), "C++ 디렉터리")
    header_path = REPO_DIR / f"src/render/native/components/{source_name}/{source_name}.hpp"
    header = widget.get("generatedHeader")
    if header is None:
        try:
            header = header_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise WidgetEmitterError(f"C++ 클래스 헤더를 읽을 수 없습니다: {exc}") from exc

    seen = set()
    handler_names = set()
    for method in methods:
        require(isinstance(method, dict), "각 메서드는 객체여야 합니다.")
        require(set(method) <= {"name", "cppMethod", "marshal", "returns", "cast", "referenceClass"},
                "현재 출력기가 지원하지 않는 메서드 세부 설정이 있습니다.")
        js_name = identifier(method.get("name"), "JS 메서드")
        cpp_name = identifier(method.get("cppMethod"), "C++ 메서드")
        handler_name = "NativeComp" + js_name[0].upper() + js_name[1:]
        kind = method.get("marshal")
        returns = method.get("returns", "undefined")
        # Validate manifest type names before inserting them into C++ code.
        require("cast" not in method or (kind == "int32" and method["cast"] == "lv_dir_t"),
                "지원하지 않는 C++ 인자 캐스트입니다.")
        if "referenceClass" in method:
            identifier(method["referenceClass"], "참조 대상 클래스")
            require(kind in {"componentReference", "stringComponentReference"},
                    "referenceClass는 컴포넌트 참조에만 지정할 수 있습니다.")
        require(js_name not in seen | COMMON_METHODS, f"중복된 JS 메서드: {js_name}")
        seen.add(js_name)
        require(handler_name not in handler_names, f"중복된 C++ wrapper 함수: {handler_name}")
        handler_names.add(handler_name)
        require(isinstance(kind, str) and kind in MARSHAL_KINDS,
                f"{widget_name}.{js_name}: 아직 지원하지 않는 값 변환: {kind}")
        require(isinstance(returns, str) and returns in {"undefined", "boolean"},
                f"지원하지 않는 반환값: {returns}")
        require(re.search(r"\b" + re.escape(cpp_name) + r"\s*\(", header) is not None,
                f"{header_path.name}에 없는 C++ 메서드: {cpp_name}")


# Build constructor declarations, option readers, and call arguments as separate fragments.
def constructor_parts(constructor: dict | None) -> tuple[str, str, str]:
    if constructor is None:
        return "", "", "uid, nullptr"
    require(isinstance(constructor, dict) and set(constructor) == {"arguments"},
            "constructor.arguments가 필요합니다.")
    args = constructor["arguments"]
    require(isinstance(args, list) and len(args) >= 2
            and args[0] == {"from": "uid", "marshal": "string"}
            and args[-1] == {"literal": None, "cppType": "lv_obj_t*"},
            "생성자는 uid와 parent=nullptr 사이에 숫자 옵션을 지정해야 합니다.")
    declarations, parsing, values, seen = [], [], ["uid"], set()
    for arg in args[1:-1]:
        require(isinstance(arg, dict) and set(arg) <= {"from", "marshal", "default"}
                and arg.get("marshal") == "int32", "생성자 옵션은 int32만 지원합니다.")
        key = identifier(arg.get("from"), "생성자 옵션")
        require(key not in seen and key != "uid", "중복된 생성자 옵션입니다.")
        seen.add(key)
        default = arg.get("default", 0)
        require((type(default) is int and -(2**31) <= default < 2**31)
                or default == "LV_DIR_TOP", "지원하지 않는 생성자 기본값입니다.")
        variable = f"option_{key}"
        declarations.append(f"    int32_t {variable} = {default};")
        parsing.append(f'''    {{
        GeneratedJSValue option(ctx, JS_GetPropertyStr(ctx, argv[0], "{key}"));
        if (JS_IsException(option.value)) goto fail;
        if (!JS_IsUndefined(option.value)) {{
            if (!JS_IsNumber(option.value)) {{
                JS_ThrowTypeError(ctx, "{key} must be a number");
                goto fail;
            }}
            if (JS_ToInt32(ctx, &{variable}, option.value) < 0) goto fail;
        }}
    }}''')
        values.append(variable)
    values.append("nullptr")
    return "\n".join(declarations), "\n".join(parsing), ", ".join(values)


# Collect only the C++ helpers required by the selected conversion rules.
def complex_helpers(kinds: set[str], reference_classes: list[str] | None = None,
                    constructor: bool = False) -> str:
    result = ""
    if constructor or kinds & {"stringArray", "dateArray", "axisOption", "axisData", "stringComponentReference", "componentReference"}:
        result += (AUTOGEN_DIR / "templates/value_helpers.cpp.in").read_text() + "\n"
    if "axisData" in kinds:
        result += (AUTOGEN_DIR / "templates/axis_helpers.cpp.in").read_text() + "\n"
    if kinds & {"componentReference", "stringComponentReference"}:
        require(bool(reference_classes), "참조할 C++ 컴포넌트 클래스 목록이 필요합니다.")
        names = ", ".join('"' + identifier(n, "참조 클래스") + '"' for n in reference_classes)
        result += '''static COMP_REF* GeneratedComponentRef(JSContext* ctx, JSValueConst value, const char* expected = nullptr) {
    if (!JS_IsObject(value)) return nullptr;
    JSClassID class_id = JS_GetClassID(value);
    GeneratedJSValue prototype(ctx, JS_GetClassProto(ctx, class_id));
    if (!JS_IsObject(prototype.value)) return nullptr;
    GeneratedJSValue global(ctx, JS_GetGlobalObject(ctx));
    GeneratedJSValue symbol(ctx, JS_GetPropertyStr(ctx, global.value, "Symbol"));
    if (JS_IsException(symbol.value)) return nullptr;
    GeneratedJSValue symbol_for(ctx, JS_GetPropertyStr(ctx, symbol.value, "for"));
    if (JS_IsException(symbol_for.value)) return nullptr;
    GeneratedJSValue key_name(ctx, JS_NewString(ctx, "lvgljs"));
    GeneratedJSValue key(ctx, JS_Call(ctx, symbol_for.value, symbol.value, 1, &key_name.value));
    if (JS_IsException(key.value)) return nullptr;
    JSAtom atom = JS_ValueToAtom(ctx, key.value);
    GeneratedJSValue bridge(ctx, JS_GetProperty(ctx, global.value, atom));
    JS_FreeAtom(ctx, atom);
    if (!JS_IsObject(bridge.value)) return nullptr;
    GeneratedJSValue render(ctx, JS_GetPropertyStr(ctx, bridge.value, "NativeRender"));
    if (!JS_IsObject(render.value)) return nullptr;
    GeneratedJSValue components(ctx, JS_GetPropertyStr(ctx, render.value, "NativeComponents"));
    if (!JS_IsObject(components.value)) return nullptr;
    const char* allowed[] = {''' + names + '''};
    bool found = false;
    for (const char* candidate : allowed) {
        if (expected != nullptr && std::string(candidate) != expected) continue;
        GeneratedJSValue constructor(ctx, JS_GetPropertyStr(ctx, components.value, candidate));
        if (JS_IsException(constructor.value)) return nullptr;
        if (!JS_IsObject(constructor.value)) continue;
        GeneratedJSValue candidate_proto(ctx, JS_GetPropertyStr(ctx, constructor.value, "prototype"));
        if (JS_IsException(candidate_proto.value)) return nullptr;
        if (JS_IsStrictEqual(ctx, prototype.value, candidate_proto.value)) { found = true; break; }
    }
    if (!found) return nullptr;
    auto* ref = static_cast<COMP_REF*>(JS_GetAnyOpaque(value, &class_id));
    return ref != nullptr && ref->comp != nullptr ? ref : nullptr;
}
'''
    return result


# Generate argument checks, value conversion, and a C++ call for one method.
def method_handler(native_class: str, method: dict) -> str:
    js_name = method["name"]
    cpp_name = method["cppMethod"]
    kind = method["marshal"]
    returns = method.get("returns", "undefined")
    function_name = "NativeComp" + js_name[0].upper() + js_name[1:]
    if kind == "boolean":
        guard = "if (argc < 1 || !JS_IsBool(argv[0])) return JS_UNDEFINED;"
        body = f"""bool value = JS_ToBool(ctx, argv[0]);
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(value);"""
    elif kind == "string":
        guard = "if (argc < 1 || !JS_IsString(argv[0])) return JS_UNDEFINED;"
        body = f"""size_t length = 0;
    const char* chars = JS_ToCStringLen(ctx, &length, argv[0]);
    if (chars == nullptr) return JS_EXCEPTION;
    std::string value(chars, length);
    JS_FreeCString(ctx, chars);
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(value);"""
    elif kind == "arrayBuffer":
        guard = "if (argc < 1) return JS_UNDEFINED;"
        body = f"""size_t length = 0;
    uint8_t* data = JS_GetArrayBuffer(ctx, &length, argv[0]);
    if (data == nullptr) return JS_UNDEFINED;
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(data, length);"""
    elif kind == "noArgs":
        guard = "(void)ctx; (void)argc; (void)argv;"
        body = f"static_cast<{native_class}*>(ref->comp)->{cpp_name}();"
    elif kind in {"int32", "booleanToInt32"}:
        # Convert TS numbers and enums using JS_ToInt32, matching handwritten wrappers.
        check = "JS_IsBool" if kind == "booleanToInt32" else "JS_IsNumber"
        guard = f"if (argc < 1 || !{check}(argv[0])) return JS_UNDEFINED;"
        argument = f"static_cast<{method['cast']}>(value)" if "cast" in method else "value"
        body = f"""int32_t value = 0;
    if (JS_ToInt32(ctx, &value, argv[0]) < 0) return JS_EXCEPTION;
    static_cast<{native_class}*>(ref->comp)->{cpp_name}({argument});"""
    elif kind in {"stringArrayLength", "stringArrayLengthBoolean"}:
        # Accept a JS array and length but pass only the string vector to C++.
        # Skip non-string elements, matching the handwritten wrapper.
        with_boolean = kind == "stringArrayLengthBoolean"
        guard = ("if (argc < 3 || !JS_IsArray(argv[0]) || !JS_IsNumber(argv[1]) || !JS_IsBool(argv[2])) return JS_UNDEFINED;"
                 if with_boolean else
                 "if (argc < 2 || !JS_IsArray(argv[0]) || !JS_IsNumber(argv[1])) return JS_UNDEFINED;")
        boolean_argument = ", JS_ToBool(ctx, argv[2])" if with_boolean else ""
        body = f"""int32_t length = 0;
    if (JS_ToInt32(ctx, &length, argv[1]) < 0) return JS_EXCEPTION;
    if (length < 0) return JS_UNDEFINED;
    JSValue length_value = JS_GetPropertyStr(ctx, argv[0], "length");
    if (JS_IsException(length_value)) return JS_EXCEPTION;
    uint32_t actual_length = 0;
    int status = JS_ToUint32(ctx, &actual_length, length_value);
    JS_FreeValue(ctx, length_value);
    if (status < 0) return JS_EXCEPTION;
    // Clamp the requested length to the array size to avoid repeated out-of-range reads.
    uint32_t count = static_cast<uint32_t>(length);
    if (count > actual_length) count = actual_length;
    std::vector<std::string> items;
    for (uint32_t i = 0; i < count; ++i) {{
        JSValue item = JS_GetPropertyUint32(ctx, argv[0], i);
        if (JS_IsException(item)) return JS_EXCEPTION;
        if (JS_IsString(item)) {{
            size_t size = 0;
            const char* chars = JS_ToCStringLen(ctx, &size, item);
            if (chars == nullptr) {{
                JS_FreeValue(ctx, item);
                return JS_EXCEPTION;
            }}
            items.emplace_back(chars, size);
            JS_FreeCString(ctx, chars);
        }}
        JS_FreeValue(ctx, item);
    }}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(items{boolean_argument});"""
    elif kind == "int32ArrayPair":
        # Split one JS array into two numeric arguments for the C++ call.
        # Read both values before releasing them so exceptions leave no retained references.
        guard = "if (argc < 1 || !JS_IsArray(argv[0])) return JS_UNDEFINED;"
        body = f"""JSValue first_value = JS_GetPropertyUint32(ctx, argv[0], 0);
    if (JS_IsException(first_value)) return JS_EXCEPTION;
    JSValue second_value = JS_GetPropertyUint32(ctx, argv[0], 1);
    if (JS_IsException(second_value)) {{
        JS_FreeValue(ctx, first_value);
        return JS_EXCEPTION;
    }}
    int32_t first = 0, second = 0;
    int status = JS_ToInt32(ctx, &first, first_value);
    if (status >= 0) status = JS_ToInt32(ctx, &second, second_value);
    JS_FreeValue(ctx, first_value);
    JS_FreeValue(ctx, second_value);
    if (status < 0) return JS_EXCEPTION;
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(first, second);"""
    elif kind in {"int32Args2", "int32Args3", "int32Boolean"}:
        # ProgressBar range takes two numbers; value takes a number and a bool.
        second_check = "JS_IsBool" if kind == "int32Boolean" else "JS_IsNumber"
        third_guard = " || !JS_IsNumber(argv[2])" if kind == "int32Args3" else ""
        count = 3 if kind == "int32Args3" else 2
        guard = f"if (argc < {count} || !JS_IsNumber(argv[0]) || !{second_check}(argv[1]){third_guard}) return JS_UNDEFINED;"
        second = ("bool second = JS_ToBool(ctx, argv[1]);" if kind == "int32Boolean"
                  else "int32_t second = 0;\n    if (JS_ToInt32(ctx, &second, argv[1]) < 0) return JS_EXCEPTION;")
        third = "int32_t third = 0;\n    if (JS_ToInt32(ctx, &third, argv[2]) < 0) return JS_EXCEPTION;" if kind == "int32Args3" else ""
        args = "first, second, third" if kind == "int32Args3" else "first, second"
        body = f"""int32_t first = 0;
    if (JS_ToInt32(ctx, &first, argv[0]) < 0) return JS_EXCEPTION;
    {second}
    {third}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}({args});"""
    elif kind in {"componentReference", "stringComponentReference"}:
        named = kind == "stringComponentReference"
        index = 1 if named else 0
        guard = ("if (argc < 2 || !JS_IsString(argv[0]) || !JS_IsObject(argv[1])) return JS_UNDEFINED;"
                 if named else "if (argc < 1 || !JS_IsObject(argv[0])) return JS_UNDEFINED;")
        expected = ', "' + method["referenceClass"] + '"' if "referenceClass" in method else ""
        prefix = """size_t length = 0;
    const char* chars = JS_ToCStringLen(ctx, &length, argv[0]);
    if (chars == nullptr) return JS_EXCEPTION;
    std::string title(chars, length);
    JS_FreeCString(ctx, chars);
    """ if named else ""
        args = ("title, " if named else "") + "static_cast<BasicComponent*>(child->comp)"
        body = f"""auto* child = GeneratedComponentRef(ctx, argv[{index}]{expected});
    if (child == nullptr) return JS_ThrowTypeError(ctx, "Expected a live native component");
    {prefix}static_cast<{native_class}*>(ref->comp)->{cpp_name}({args});"""
    elif kind == "stringArray":
        guard = "if (argc < 1 || !JS_IsArray(argv[0])) return JS_UNDEFINED;"
        body = f"""uint32_t count = 0;
    if (!GeneratedArrayLength(ctx, argv[0], &count)) return JS_EXCEPTION;
    std::vector<std::string> items;
    for (uint32_t i = 0; i < count; ++i) {{
        GeneratedJSValue item(ctx, JS_GetPropertyUint32(ctx, argv[0], i));
        if (JS_IsException(item.value)) return JS_EXCEPTION;
        size_t length = 0;
        const char* chars = JS_ToCStringLen(ctx, &length, item.value);
        if (chars == nullptr) return JS_EXCEPTION;
        items.emplace_back(chars, length);
        JS_FreeCString(ctx, chars);
    }}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(items);"""
    elif kind == "dateArray":
        guard = "if (argc < 2 || !JS_IsArray(argv[0]) || !JS_IsNumber(argv[1])) return JS_UNDEFINED;"
        body = f"""int32_t requested = 0;
    if (JS_ToInt32(ctx, &requested, argv[1]) < 0) return JS_EXCEPTION;
    if (requested < 0) return JS_UNDEFINED;
    uint32_t length = 0;
    if (!GeneratedArrayLength(ctx, argv[0], &length)) return JS_EXCEPTION;
    if (length > static_cast<uint32_t>(requested)) length = static_cast<uint32_t>(requested);
    std::vector<lv_calendar_date_t> dates;
    for (uint32_t i = 0; i < length; ++i) {{
        GeneratedJSValue item(ctx, JS_GetPropertyUint32(ctx, argv[0], i));
        if (JS_IsException(item.value)) return JS_EXCEPTION;
        if (!JS_IsArray(item.value)) continue;
        GeneratedJSValue y(ctx, JS_GetPropertyUint32(ctx, item.value, 0));
        if (JS_IsException(y.value)) return JS_EXCEPTION;
        GeneratedJSValue m(ctx, JS_GetPropertyUint32(ctx, item.value, 1));
        if (JS_IsException(m.value)) return JS_EXCEPTION;
        GeneratedJSValue d(ctx, JS_GetPropertyUint32(ctx, item.value, 2));
        if (JS_IsException(d.value)) return JS_EXCEPTION;
        if (!JS_IsNumber(y.value) || !JS_IsNumber(m.value) || !JS_IsNumber(d.value)) continue;
        int32_t year = 0, month = 0, day = 0;
        if (JS_ToInt32(ctx, &year, y.value) < 0 || JS_ToInt32(ctx, &month, m.value) < 0 ||
            JS_ToInt32(ctx, &day, d.value) < 0) return JS_EXCEPTION;
        lv_calendar_date_t date;
        date.year = static_cast<uint16_t>(year);
        date.month = static_cast<uint8_t>(month);
        date.day = static_cast<uint8_t>(day);
        dates.push_back(date);
    }}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(dates, static_cast<int32_t>(dates.size()));"""
    elif kind == "axisOption":
        guard = "if (argc < 1 || !JS_IsObject(argv[0])) return JS_UNDEFINED;"
        body = f"""int32_t major_len = 0, minor_len = 0, major_num = 0, minor_num = 0, draw_size = 0;
    if (!GeneratedIntProperty(ctx, argv[0], "majorLen", &major_len) ||
        !GeneratedIntProperty(ctx, argv[0], "minorLen", &minor_len) ||
        !GeneratedIntProperty(ctx, argv[0], "majorNum", &major_num) ||
        !GeneratedIntProperty(ctx, argv[0], "minorNum", &minor_num) ||
        !GeneratedIntProperty(ctx, argv[0], "drawSize", &draw_size)) return JS_EXCEPTION;
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(major_len, minor_len, major_num, minor_num, draw_size);"""
    elif kind == "axisData":
        guard = "if (argc < 1 || !JS_IsArray(argv[0])) return JS_UNDEFINED;"
        body = f"""std::vector<axis_data> data;
    if (!GeneratedAxisData(ctx, argv[0], data)) return JS_EXCEPTION;
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(data);"""
    elif kind == "arcImage":
        # Accept image bytes or symbols supplied by style handling.
        # A true return value means the call was handled, not that image decoding succeeded.
        guard = "if (argc < 3 || (!JS_IsObject(argv[0]) && !JS_IsNull(argv[0])) || !JS_IsNumber(argv[1])) return JS_NewBool(ctx, 0);"
        body = f"""int32_t style_type = 0;
    if (JS_ToInt32(ctx, &style_type, argv[1]) < 0) return JS_EXCEPTION;
    size_t length = 0;
    uint8_t* data = nullptr;
    if (!JS_IsNull(argv[0])) {{
        data = JS_GetArrayBuffer(ctx, &length, argv[0]);
        if (data == nullptr && JS_HasException(ctx)) return JS_EXCEPTION;
    }}
    std::string symbol;
    if (JS_IsString(argv[2])) {{
        size_t symbol_length = 0;
        const char* chars = JS_ToCStringLen(ctx, &symbol_length, argv[2]);
        if (chars == nullptr) return JS_EXCEPTION;
        symbol.assign(chars, symbol_length);
        JS_FreeCString(ctx, chars);
    }}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(data, length, style_type, symbol);"""
    elif kind == "pointArray":  # Convert an array of [[x, y], ...] points and its length to a C++ vector.
        guard = "if (argc < 2 || !JS_IsArray(argv[0]) || !JS_IsNumber(argv[1])) return JS_UNDEFINED;"
        body = f"""int32_t length = 0;
    if (JS_ToInt32(ctx, &length, argv[1]) < 0 || length < 0) return JS_UNDEFINED;
    std::vector<lv_point_precise_t> points;
    for (int32_t i = 0; i < length; ++i) {{
        JSValue item = JS_GetPropertyUint32(ctx, argv[0], i);
        if (JS_IsArray(item)) {{
            JSValue x_value = JS_GetPropertyUint32(ctx, item, 0);
            JSValue y_value = JS_GetPropertyUint32(ctx, item, 1);
            if (JS_IsNumber(x_value) && JS_IsNumber(y_value)) {{
                int32_t x = 0, y = 0;
                if (JS_ToInt32(ctx, &x, x_value) >= 0 &&
                    JS_ToInt32(ctx, &y, y_value) >= 0) {{
                    lv_point_precise_t point;
                    lv_point_precise_set(&point, x, y);
                    points.push_back(point);
                }}
            }}
            JS_FreeValue(ctx, x_value);
            JS_FreeValue(ctx, y_value);
        }}
        JS_FreeValue(ctx, item);
    }}
    static_cast<{native_class}*>(ref->comp)->{cpp_name}(
        points, static_cast<int32_t>(points.size()));"""
    else:
        raise WidgetEmitterError(f"지원하지 않는 값 변환: {kind}")
    result = "return JS_NewBool(ctx, 1);" if returns == "boolean" else "return JS_UNDEFINED;"
    return f"""static JSValue {function_name}(
    JSContext* ctx, JSValueConst this_val, int argc, JSValueConst* argv) {{
    {guard}
    auto* ref = static_cast<COMP_REF*>(JS_GetOpaque(this_val, {native_class}ClassID));
    if (ref == nullptr || ref->comp == nullptr) return JS_UNDEFINED;
    {body}
    {result}
}}"""


# Fill the template with constructor, shared feature, and method code to produce the wrapper.
def render_widget(widget: dict, template_path: Path = TEMPLATE) -> str:
    widget_name = widget.get("reactName")
    validate_widget(widget, widget_name)
    native_class = widget["nativeClass"]
    binding = widget["cppBinding"]
    features = binding["features"]
    methods = binding["methods"]
    declarations, constructor_parse, constructor_args = constructor_parts(binding.get("constructor"))
    macros = []
    child_entries = []
    if "backgroundImage" in features:
        macros.append(f'WRAPPED_JS_BACKGROUND_IMAGE({native_class}, "{native_class}")')
    if "children" in features:
        macros.extend([f'WRAPPED_APPEND_CHILD({native_class}, "{native_class}")',
                       f'WRAPPED_INSERT_CHILD({native_class}, "{native_class}")'])
        child_entries = [
            '    TJS_CFUNC_DEF("appendChild", 0, NativeCompAppendChild),',
            '    TJS_CFUNC_DEF("insertChildBefore", 0, NativeCompInsertChildBefore),',
        ]
    # Add alignment and stacking methods only for widgets selected in the manifest.
    alignment_macros = "\n".join((
        f'WRAPPED_JS_Align({native_class}, "{native_class}")',
        f'WRAPPED_JS_Align_To({native_class}, "{native_class}")',
    )) if "alignment" in features else ""
    alignment_entries = "\n".join((
        '    TJS_CFUNC_DEF("align", 0, NativeCompSetAlign),',
        '    TJS_CFUNC_DEF("alignTo", 0, NativeCompSetAlignTo),',
    )) if "alignment" in features else ""
    movement_macros = "\n".join((
        f'WRAPPED_MOVE_TO_FRONT({native_class}, "{native_class}")',
        f'WRAPPED_MOVE_TO_BACKGROUND({native_class}, "{native_class}")',
        f'WRAPPED_SCROLL_INTO_VIEW({native_class}, "{native_class}")',
    )) if "movement" in features else ""
    movement_entries = "\n".join((
        '    TJS_CFUNC_DEF("moveToFront", 0, NativeCompMoveToFront),',
        '    TJS_CFUNC_DEF("moveToBackground", 0, NativeCompMoveToBackground),',
        '    TJS_CFUNC_DEF("scrollIntoView", 0, NativeCompScrollIntoView),',
    )) if "movement" in features else ""
    entries = []
    if "refresh" in features:
        macros.append(f'''static JSValue NativeCompRefreshComponent(JSContext* ctx, JSValueConst this_val,
    int argc, JSValueConst* argv) {{
    (void)argc; (void)argv;
    auto* ref = static_cast<COMP_REF*>(JS_GetOpaque(this_val, {native_class}ClassID));
    if (ref == nullptr || ref->comp == nullptr) return JS_UNDEFINED;
    lv_obj_invalidate(static_cast<BasicComponent*>(ref->comp)->instance);
    return JS_UNDEFINED;
}}''')
        entries.append('    TJS_CFUNC_DEF("refresh", 0, NativeCompRefreshComponent),')
    for method in methods:
        name = method["name"]
        function = "NativeComp" + name[0].upper() + name[1:]
        entries.append(f'    TJS_CFUNC_DEF("{name}", 0, {function}),')
    source_name = widget.get("nativeDir", native_class.lower())
    component_include = f'#include "native/components/{source_name}/{source_name}.hpp"'
    if widget.get("componentHeader"):
        # Use headers from the flat generated directory only for selected widgets.
        component_include = (f"#ifdef LV_BINDING_GENERATED_COMPONENT_{native_class}\n"
                             f'#include "components/{source_name}.hpp"\n#else\n'
                             f"{component_include}\n#endif")
    try:
        template = Template(template_path.read_text(encoding="utf-8"))
        return generated_source(template.substitute(
            source_name=source_name, native_class=native_class, component_include=component_include,
            alignment_macros=alignment_macros,
            alignment_entries=alignment_entries + ("\n" if alignment_entries else ""),
            movement_macros=movement_macros,
            movement_entries=movement_entries + ("\n" if movement_entries else ""),
            feature_macros="\n".join(macros) + ("\n" if macros else ""),
            method_handlers=complex_helpers({m["marshal"] for m in methods}, widget.get("referenceClasses"),
                                           "constructor" in binding)
            + "\n\n".join(method_handler(native_class, m) for m in methods)
            + ("\n" if methods else ""),
            child_entries="\n".join(child_entries) + ("\n" if child_entries else ""),
            method_entries="\n".join(entries) + ("\n" if entries else ""),
            background_entry=(
                '    TJS_CFUNC_DEF("setBackgroundImage", 0, NativeCompSetBackgroundImage),\n'
                if "backgroundImage" in features else ""),
            constructor_declarations=declarations,
            constructor_parse=constructor_parse,
            constructor_arguments=constructor_args,
        ))
    except (OSError, KeyError, ValueError) as exc:
        raise WidgetEmitterError(f"공통 C++ 양식을 채울 수 없습니다: {exc}") from exc
