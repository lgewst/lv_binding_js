# Generate the setter body for each behaviour kind.

from widget_ts_emitter import (
    COMPARE_OPS, TUPLE_ELEMENTS, TUPLE_ELEMENT_NAMES, identifier, require,
)


def extra_args(behavior: dict) -> str:
    parts = [f"!!newProps.{a['fromProp']}" if a.get("coerce") == "boolean"
             else f"newProps.{a['fromProp']}" for a in behavior.get("extraArgs") or []]
    return "".join(f", {part}" for part in parts)


def emit_style_state(prop: dict, react_name: str) -> list[str]:
    name, behavior = prop["name"], prop["behavior"]
    style_type = behavior["styleType"]
    types = style_type if isinstance(style_type, list) else [style_type]
    joined = " | ".join(f"STYLE_TYPE.{identifier(t, 'styleType')}" for t in types)
    return [f"    {name}(styleSheet) {{",
            "      setStyle({",
            "        comp,",
            "        styleSheet,",
            f'        compName: "{react_name}",',
            f"        styleType: {joined},",
            f"        oldStyleSheet: oldProps.{behavior.get('oldStyleSheetProp', name)},",
            "      });",
            "    },"]


def emit_event(prop: dict, react_name: str) -> list[str]:
    name = prop["name"]
    event = identifier(prop["behavior"].get("event"), "behavior.event")
    return [f"    {name}(fn) {{",
            f"      handleEvent(comp, fn, EVENTTYPE_MAP.{event});",
            "    },"]


def emit_value(prop: dict, react_name: str) -> list[str]:
    name, call, behavior = prop["name"], prop["bridgeMethod"], prop["behavior"]
    equal, differs = COMPARE_OPS[behavior.get("compare", "strict")]
    tail = extra_args(behavior)
    if behavior.get("guard") == "number":
        return [f"    {name}(val) {{",
                "      if (isNaN(val)) return;",
                f"      if (val {equal} oldProps.{name}) return;",
                f"      comp.{call}(val{tail});",
                "    },"]
    return [f"    {name}(val) {{",
            f"      if (val {differs} oldProps.{name}) {{",
            f"        comp.{call}(val{tail});",
            "      }",
            "    },"]


def emit_tuple(prop: dict, react_name: str) -> list[str]:
    name, call, behavior = prop["name"], prop["bridgeMethod"], prop["behavior"]
    count = behavior.get("elements", TUPLE_ELEMENTS)
    require(count == TUPLE_ELEMENTS,
            f"{react_name}.{name}: tuple 은 원소 2개만 지원합니다: {count}")
    names = TUPLE_ELEMENT_NAMES
    head = [f"    {name}(arr) {{", "      if (!Array.isArray(arr)) return;"]
    if behavior.get("callStyle") == "spread":
        unchanged = " && ".join(f"arr[{i}] === oldProps.{name}?.[{i}]" for i in range(count))
        return head + [f"      if ({unchanged}) return;",
                       f"      comp.{call}({', '.join(f'arr[{i}]' for i in range(count))});",
                       "    },"]
    unchanged = " && ".join(f"{e} === oldProps.{name}?.[{i}]" for i, e in enumerate(names))
    return head + [f"      const [{', '.join(names)}] = arr;",
                   f"      if ({unchanged}) return;",
                   f"      if ({' || '.join(f'isNaN({e})' for e in names)}) return;",
                   f"      comp.{call}([{', '.join(names)}]);",
                   "    },"]


def emit_options(prop: dict, react_name: str) -> list[str]:
    name, call, behavior = prop["name"], prop["bridgeMethod"], prop["behavior"]
    args = "arr, arr.length" if behavior["lengthArg"] else "arr"
    return [f"    {name}(arr) {{",
            f"      if (arr !== oldProps.{name} && Array.isArray(arr)) {{",
            f"        comp.{call}({args}{extra_args(behavior)});",
            "      }",
            "    },"]


def emit_enum_map(prop: dict, react_name: str) -> list[str]:
    name, call = prop["name"], prop["bridgeMethod"]
    behavior = prop["behavior"]
    table = identifier(behavior.get("map"), "behavior.map")
    known = f'typeof {table}[val] !== "undefined"'
    if behavior.get("compare") == "none":
        condition = known
    else:
        equal, differs = COMPARE_OPS[behavior.get("compare", "strict")]
        condition = f"val {differs} oldProps.{name} && {known}"
    return [f"    {name}(val) {{",
            f"      if ({condition}) {{",
            f"        comp.{call}({table}[val]);",
            "      }",
            "    },"]


EMITTERS = {
    # stateToggle 은 C++ 쪽이 behavior.state 를 읽어 구분하는 kind 다.
    # React 쪽에서 나오는 코드는 value 와 같다.
    "stateToggle": lambda prop, react_name: emit_value(prop, react_name),
    "styleState": emit_style_state,
    "event": emit_event,
    "value": emit_value,
    "tuple": emit_tuple,
    "options": emit_options,
    "enumMap": emit_enum_map,
}


