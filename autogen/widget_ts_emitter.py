# Read one widget from the shared manifest and refuse what the emitter cannot write.

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
AUTOGEN_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = AUTOGEN_DIR / "templates"
GENERATED_DIR = AUTOGEN_DIR / "generated" / "react"
DEFAULT_MANIFEST = REPO_DIR / "scripts/data/widgets_manifest.json"

HEADER = "// 자동 생성 파일. 직접 수정하지 말 것. autogen/ts_emitter.py 로 다시 생성."

# The hand-written sources import the whole config block whether or not every
# symbol is used; the generated ones match so the diff stays small.
CONFIG_IMPORTS = ("EVENTTYPE_MAP", "STYLE_TYPE", "handleEvent", "setStyle",
                  "styleGetterProp", "applyDataPropsToDataset")

# Where each type a tsType may name comes from. A type that is not here would
# be written into the declaration with no import to resolve it.
TS_TYPE_SOURCES = {
    "CommonProps": "../common/index",
    "OnChangeEvent": "../common/index",
    "OnClickEvent": "../common/index",
    "StyleProps": "../../core/style",
    "EDropdownListArrowDirection": "../config",
    "EDropdownlistDirection": "../config",
    "InputComp": "../Input/comp",
}
TS_TYPE_REF = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")
# A tsType and a doc line go inside a declaration, so neither may end it early.
TS_FORBIDDEN = re.compile(r"[;{}/\n\r]")
DOC_FORBIDDEN = re.compile(r"\*/|[\n\r]")

KINDS = ("stateToggle", "styleState", "event", "value", "tuple", "options", "enumMap")
CHILDREN_MODES = ("full", "append", "none", "manual")
MOVEMENT_MODES = ("delegate", "block")
CLOSE_MODES = ("delegate", "block")
OLD_SHEET_VALUES = ("null", "{}")
# 생성자 호출 인자는 코드에 그대로 박히므로 리터럴만 허용한다.
CONSTRUCTOR_ARGS = frozenset(['0', '1', 'false', 'null', 'true'])
COMPARE_OPS = {"strict": ("===", "!=="), "loose": ("==", "!=")}
# 수작업 코드가 이전 값을 아예 보지 않는 자리도 있다 (Chart.type).
NO_COMPARE = "none"
# compare 와 guard 를 실제로 읽는 kind.
COMPARES = ("value", "stateToggle", "enumMap")
GUARDED = ("value", "stateToggle")
GUARDS = (None, "number")
CALL_STYLES = ("array", "spread")
COERCIONS = (None, "boolean")
TUPLE_ELEMENTS = 2
TUPLE_ELEMENT_NAMES = ("min", "max")


class TsEmitterError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TsEmitterError(message)


def identifier(value: object, label: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)
            is not None, f"{label}: 유효한 JS 이름이 아닙니다: {value!r}")
    return value


def ts_type(value: object, label: str) -> str:
    require(isinstance(value, str) and value, f"{label}: tsType이 필요합니다.")
    require(TS_FORBIDDEN.search(value) is None,
            f"{label}: tsType에 쓸 수 없는 문자가 있습니다: {value!r}")
    for ref in TS_TYPE_REF.findall(value):
        require(ref in TS_TYPE_SOURCES,
                f"{label}: 생성기가 import하지 못하는 타입입니다: {ref} "
                f"(가능: {', '.join(sorted(TS_TYPE_SOURCES))})")
    return value


def validate_declaration(prop: object, label: str) -> str:
    require(isinstance(prop, dict), f"{label}: 객체가 필요합니다.")
    name = identifier(prop.get("name"), label)
    ts_type(prop.get("tsType"), f"{label}.{name}")
    doc = prop.get("doc")
    require(doc is None or (isinstance(doc, str) and DOC_FORBIDDEN.search(doc) is None),
            f"{label}.{name}: doc에 쓸 수 없는 문자가 있습니다.")
    return name


def load_widget(manifest: Path, react_name: str) -> dict:
    identifier(react_name, "위젯 이름")
    try:
        root = json.loads(Path(manifest).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TsEmitterError(f"manifest를 읽을 수 없습니다: {exc}") from exc
    require(isinstance(root, dict) and isinstance(root.get("widgets"), list),
            "manifest.widgets 배열이 필요합니다.")

    widgets = root["widgets"]
    widget = next((w for w in widgets if w.get("reactName") == react_name), None)
    require(widget is not None, f"manifest에 없는 위젯입니다: {react_name} "
            f"(가능: {', '.join(w.get('reactName', '?') for w in widgets)})")
    require((widget.get("generate") or {}).get("ts"),
            f"{react_name}: generate.ts 가 켜져 있지 않습니다.")

    # manual prop 은 생성하지 않고 옆 파일의 수작업 세터를 끼워 쓴다. 세터 표의
    # 순서가 네이티브 호출 순서라, 어느 세터 뒤에 오는지를 after 로 적게 한다.
    manual = widget.get("manual") or []
    for entry in manual:
        name = validate_declaration(entry, react_name)
        require(bool(entry.get("reason")),
                f"{react_name}.{name}: manual 항목에는 reason 이 필요합니다.")
        require(entry.get("lifecycle", "update") == "update",
                f"{react_name}.{name}: 생성자에서 소비되는 prop 은 세터로 끼울 수 없습니다.")

    react_class = widget.get("reactClass") or {}
    require(react_class.get("children", "none") in CHILDREN_MODES,
            f"{react_name}: reactClass.children 이 올바르지 않습니다.")
    require(react_class.get("movement", "delegate") in MOVEMENT_MODES,
            f"{react_name}: reactClass.movement 가 올바르지 않습니다.")
    require(react_class.get("styleResetOldSheet", "null") in OLD_SHEET_VALUES,
            f"{react_name}: reactClass.styleResetOldSheet 가 올바르지 않습니다.")
    for field in ("nativeKey", "propsType"):
        if react_class.get(field) is not None:
            identifier(react_class[field], f"{react_name} reactClass.{field}")
    require(react_class.get("close", "delegate") in CLOSE_MODES,
            f"{react_name}: reactClass.close 가 올바르지 않습니다.")
    for name in react_class.get("stashProps", []):
        identifier(name, f"{react_name} reactClass.stashProps")
    for name, value in (react_class.get("instanceFields") or {}).items():
        identifier(name, f"{react_name} reactClass.instanceFields")
        require(value in CONSTRUCTOR_ARGS,
                f"{react_name}: 인스턴스 필드 초기값으로 쓸 수 없습니다: {value!r}")
    for entry in react_class.get("constructorProps", []):
        validate_declaration(entry, react_name)
        if entry.get("map") is not None:
            identifier(entry["map"], f"{react_name} constructorProps.map")
            if entry.get("fallback") is not None:
                require(entry["fallback"] in (entry.get("mapValues") or {}),
                        f"{react_name}.{entry['name']}: fallback 이 mapValues 의 키가 "
                        f"아닙니다: {entry['fallback']!r}")
            identifier(entry.get("mapSource"), f"{react_name} constructorProps.mapSource")
            require(isinstance(entry.get("mapValues"), dict) and entry["mapValues"],
                    f"{react_name}.{entry['name']}: map 에는 mapValues 가 필요합니다.")
            identifier(entry.get("fallback"), f"{react_name} constructorProps.fallback")
        if entry.get("default") is not None:
            require(entry["default"] in CONSTRUCTOR_ARGS,
                    f"{react_name}: 생성자 기본값으로 쓸 수 없습니다: {entry['default']!r}")
    for call in react_class.get("constructorCalls", []):
        identifier(call.get("method"), f"{react_name} constructorCalls.method")
        for arg in call.get("args", []):
            require(arg in CONSTRUCTOR_ARGS,
                    f"{react_name}: 생성자 인자로 쓸 수 없는 값입니다: {arg!r} "
                    f"(가능: {', '.join(sorted(CONSTRUCTOR_ARGS))})")

    props = widget.get("props", [])
    require(isinstance(props, list), f"{react_name}: props 는 배열이어야 합니다.")

    declared = {validate_declaration(p, react_name) for p in props}
    for entry in widget.get("passive", []):
        declared.add(validate_declaration(entry, react_name))
    declared |= {entry["name"] for entry in manual}

    # after 는 생성 세터 또는 앞에 적힌 manual 만 가리킬 수 있다. 그래야 자리가
    # 하나로 정해지고, 끼울 곳이 없는 항목이 조용히 빠지지 않는다.
    placed = {prop["name"] for prop in props}
    anchors: set = set()
    for entry in manual:
        anchor = entry.get("after")
        if anchor is not None:
            identifier(anchor, f"{react_name}.{entry['name']} after")
            require(anchor in placed,
                    f"{react_name}.{entry['name']}: after 가 가리키는 세터가 없습니다: {anchor}")
        require(anchor not in anchors,
                f"{react_name}.{entry['name']}: after 가 {anchor} 로 겹칩니다. "
                f"앞의 manual 항목을 가리키게 적을 것")
        anchors.add(anchor)
        placed.add(entry["name"])

    seen: set[str] = set()
    for prop in props:
        name = prop["name"]
        require(name not in seen, f"{react_name}.{name}: prop이 중복됩니다.")
        seen.add(name)
        require(prop.get("lifecycle", "update") == "update",
                f"{react_name}.{name}: lifecycle이 update가 아니면 세터로 만들 수 없습니다.")

        behavior = prop.get("behavior") or {}
        kind = behavior.get("kind")
        require(kind in KINDS, f"{react_name}.{name}: 지원하지 않는 kind입니다: {kind!r} "
                f"(가능: {', '.join(sorted(KINDS))})")
        if kind not in ("styleState", "event"):
            identifier(prop.get("bridgeMethod"), f"{react_name}.{name} bridgeMethod")
        # kind 마다 반드시 있어야 하는 필드. 없으면 생성 중에 KeyError 로 터진다.
        if kind == "styleState":
            # 하나이거나, 합쳐 쓰는 여러 개일 수 있다.
            style_type = behavior.get("styleType")
            for part in (style_type if isinstance(style_type, list) else [style_type]):
                identifier(part, f"{react_name}.{name} styleType")
        if kind == "enumMap":
            identifier(behavior.get("map"), f"{react_name}.{name} behavior.map")
            require(isinstance(behavior.get("mapValues"), dict) and behavior["mapValues"],
                    f"{react_name}.{name}: enumMap 에는 mapValues 가 필요합니다.")
        if kind == "event":
            identifier(behavior.get("event"), f"{react_name}.{name} behavior.event")

        compare = behavior.get("compare", "strict")
        require(compare in COMPARE_OPS or compare == NO_COMPARE,
                f"{react_name}.{name}: compare가 올바르지 않습니다: {compare!r}")
        require(behavior.get("guard") in GUARDS,
                f"{react_name}.{name}: guard가 올바르지 않습니다: {behavior.get('guard')!r}")
        # compare 와 guard 를 읽는 kind 는 정해져 있다. 다른 kind 에 적어 두면
        # 조용히 무시되므로, 무시될 자리에 적는 것을 거부한다.
        require("compare" not in behavior or kind in COMPARES,
                f"{react_name}.{name}: {kind} 는 compare 를 보지 않습니다.")
        require(compare != NO_COMPARE or kind == "enumMap",
                f"{react_name}.{name}: compare=none 은 enumMap 에서만 쓸 수 있습니다.")
        require("guard" not in behavior or kind in GUARDED,
                f"{react_name}.{name}: {kind} 는 guard 를 보지 않습니다.")
        if kind == "tuple":
            require(behavior.get("callStyle") in CALL_STYLES,
                    f"{react_name}.{name}: callStyle이 올바르지 않습니다: "
                    f"{behavior.get('callStyle')!r}")
        if kind == "options":
            require(isinstance(behavior.get("lengthArg"), bool),
                    f"{react_name}.{name}: lengthArg는 true/false여야 합니다.")
        if behavior.get("oldStyleSheetProp") is not None:
            source = identifier(behavior["oldStyleSheetProp"],
                                f"{react_name}.{name} oldStyleSheetProp")
            require(source in declared,
                    f"{react_name}.{name}: oldStyleSheetProp 가 선언되지 않은 prop 입니다: {source}")
        for arg in behavior.get("extraArgs") or []:
            source = identifier((arg or {}).get("fromProp"),
                                f"{react_name}.{name} extraArgs.fromProp")
            require(source in declared,
                    f"{react_name}.{name}: extraArgs가 선언되지 않은 prop을 읽습니다: {source}")
            require(arg.get("coerce") in COERCIONS,
                    f"{react_name}.{name}: coerce가 올바르지 않습니다: {arg.get('coerce')!r}")

    return widget


