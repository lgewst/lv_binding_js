# Render comp.ts and config.ts from a loaded widget.

from __future__ import annotations

from pathlib import Path
from string import Template

import component_ts_rules as rules

from widget_ts_emitter import (
    CONFIG_IMPORTS, GENERATED_DIR, HEADER, TEMPLATE_DIR, TS_TYPE_REF, TS_TYPE_SOURCES,
    identifier, require,
)


def emit_imports(widget: dict) -> str:
    declarations = (widget["props"] + widget.get("manual", [])
                    + widget.get("passive", []))
    referenced = {ref for p in declarations for ref in TS_TYPE_REF.findall(p["tsType"])}
    extra: dict[str, set[str]] = {}
    for ref in referenced:
        extra.setdefault(TS_TYPE_SOURCES[ref], set()).add(ref)

    lines = []
    sources = {source for _, source, _ in map_tables(widget)}
    if "lv_conf" in sources:
        lines.append('import * as lv_conf from "../../core/lv_conf";')
    for source in sorted(sources - {"lv_conf"}):
        lines.append(f'import {{ {source} }} from "../../core/lv_types";')
    if "StyleProps" in referenced or any(
            p["behavior"]["kind"] == "styleState" for p in widget["props"]):
        lines.append('import { StyleProps } from "../../core/style";')
    common = ["CommonComponentApi", "CommonProps"]
    common += sorted(extra.get("../common/index", set()) - set(common))
    lines.append("import { " + ", ".join(common) + ' } from "../common/index";')
    lines.append("import {")
    lines.extend(f"  {symbol}," for symbol in
                 sorted(extra.get("../config", set())) + list(CONFIG_IMPORTS))
    lines.append('} from "../config";')
    lines.append("")
    lines.append('import { GetBridge } from "../../core/bridge";')
    for module in sorted(set(extra) - {"../common/index", "../config", "../../core/style"}):
        lines.append("import { " + ", ".join(sorted(extra[module])) + f' }} from "{module}";')
    return "\n".join(lines)


def map_tables(widget: dict) -> list[tuple[str, str, dict]]:
    """(조회표 이름, 값이 오는 심볼, 키→상수) 목록. 이름이 겹치면 거부한다."""
    tables: list[tuple[str, str, dict]] = []
    seen: dict[str, tuple[str, dict]] = {}

    def add(label: str, name: str, source: str, values: object) -> None:
        require(isinstance(values, dict) and bool(values),
                f"{label}: 조회표에 mapValues 가 필요합니다.")
        identifier(source, f"{label} mapSource")
        if name in seen:
            require(seen[name] == (source, values),
                    f"{label}: 조회표 이름 {name} 이 다른 내용으로 겹칩니다.")
            return
        seen[name] = (source, values)
        tables.append((name, source, values))

    for prop in widget["props"]:
        behavior = prop["behavior"]
        if behavior["kind"] != "enumMap":
            continue
        add(f"{widget['reactName']}.{prop['name']}", behavior["map"],
            behavior.get("mapSource", "lv_conf"), behavior.get("mapValues"))
    for entry in (widget.get("reactClass") or {}).get("constructorProps", []):
        if entry.get("map"):
            add(f"{widget['reactName']}.{entry['name']}", entry["map"],
                entry["mapSource"], entry["mapValues"])
    return tables


def emit_maps(widget: dict) -> str:
    blocks = []
    for table, source, values in map_tables(widget):
        identifier(table, "조회표 이름")
        rows = [f"  {identifier(key, '조회표 키')}: "
                f"{source}.{identifier(constant, '조회표 값')},"
                for key, constant in values.items()]
        blocks.append(f"\nconst {table} = {{\n" + "\n".join(rows) + "\n};\n")
    return "".join(blocks)


def emit_prop_types(widget: dict) -> str:
    lines = []
    react_class = widget.get("reactClass") or {}
    for prop in (widget["props"] + widget.get("manual", [])
                 + react_class.get("constructorProps", []) + widget.get("passive", [])):
        if prop.get("doc"):
            lines.append(f"  /** {prop['doc']} */")
        lines.append(f"  {prop['name']}{'' if prop.get('required') else '?'}: "
                     f"{prop['tsType']};")
    return "\n".join(lines)


def has_manual(widget: dict) -> bool:
    return bool(widget.get("manual"))


def emit_manual_import(widget: dict) -> str:
    names = ["manualSetters"] if has_manual(widget) else []
    if (widget.get("reactClass") or {}).get("children") == "manual":
        names.append("manualChildren")
    if not names:
        return ""
    return '\nimport { %s } from "./manual";' % ", ".join(names)


# 세터 표를 거치지 않고 인스턴스에 바로 얹는 prop. 자식 훅이 읽는 값이라
# prop 이 빠진 재렌더에서도 같이 비워져야 한다.
def emit_stash(widget: dict) -> str:
    names = (widget.get("reactClass") or {}).get("stashProps", [])
    return "".join(f"    this.{n} = newProps.{n};\n" for n in names)


# 표의 순서가 네이티브 호출 순서다. manual 은 after 가 가리키는 세터 뒤에 온다.
def setter_order(widget: dict) -> list[dict]:
    followers: dict[object, list[dict]] = {}
    for entry in widget.get("manual") or []:
        followers.setdefault(entry.get("after"), []).append(entry)

    order: list[dict] = []

    def place(anchor) -> None:
        for entry in followers.get(anchor, []):
            order.append(entry)
            place(entry["name"])

    place(None)
    for prop in widget["props"]:
        order.append(prop)
        place(prop["name"])
    return order


def emit_setters(widget: dict) -> str:
    lines = []
    for entry in setter_order(widget):
        behavior = entry.get("behavior")
        if behavior is None:
            lines.append(f"    {entry['name']}: manual.{entry['name']},")
        else:
            lines.extend(rules.EMITTERS[behavior["kind"]](entry, widget["reactName"]))
    return "\n".join(lines)


def emit_manual_table(widget: dict) -> str:
    if not has_manual(widget):
        return ""
    return "  const manual = manualSetters({ comp, newProps, oldProps });\n"


def emit_children(widget: dict) -> str:
    mode = (widget.get("reactClass") or {}).get("children", "none")
    if mode == "manual":
        return "\n".join([
            "  insertBefore(child, beforeChild) {",
            "    manualChildren.insertBefore.call(this, child, beforeChild);",
            "  }",
            "  appendInitialChild(child) {",
            "    manualChildren.appendInitialChild.call(this, child);",
            "  }",
            "  appendChild(child) {",
            "    manualChildren.appendChild.call(this, child);",
            "  }",
        ])
    insert = ("    super.insertChildBefore(child, beforeChild);\n" if mode == "full" else "")
    initial = ("    this.appendChild(child);\n" if mode == "full" else "")
    append = ("    super.appendChild(child);\n" if mode in ("full", "append") else "")
    def method(signature: str, inner: str) -> str:
        return f"  {signature} {{}}" if not inner else f"  {signature} {{\n{inner}  }}"
    return "\n".join([
        method("insertBefore(child, beforeChild)", insert),
        method("appendInitialChild(child)", initial),
        method("appendChild(child)", append),
    ])


def emit_movement(widget: dict) -> str:
    mode = (widget.get("reactClass") or {}).get("movement", "delegate")
    names = ("moveToFront", "moveToBackground", "scrollIntoView")
    if mode == "block":
        return "".join(f"  {n}() {{}}\n" for n in names)
    return "".join(f"  {n}() {{\n    super.{n}();\n  }}\n" for n in names)


def emit_constructor(widget: dict) -> str:
    entries = (widget.get("reactClass") or {}).get("constructorProps", [])
    params = ["uid"] + [e["name"] + (f" = {e['default']}" if e.get("default") else "")
                        for e in entries]
    lines = [f"  constructor({{ {', '.join(params)} }}) {{"]
    for entry in entries:
        if entry.get("map"):
            table, name, fallback = entry["map"], entry["name"], entry["fallback"]
            lines.append(f"    {name} = {table}[{name}] || {table}.{fallback};")
    forwarded = ", ".join(["uid"] + [e["name"] for e in entries])
    lines.append(f"    super({{ {forwarded} }});")
    lines.append("    this.uid = uid;")
    for call in (widget.get("reactClass") or {}).get("constructorCalls", []):
        lines.append(f"    super.{call['method']}({', '.join(call.get('args', []))});")
    return "\n".join(lines)


def emit_instance_fields(widget: dict) -> str:
    fields = (widget.get("reactClass") or {}).get("instanceFields") or {}
    return "".join(f"    this.{n} = {v};\n" for n, v in fields.items())


def emit_close(widget: dict) -> str:
    if (widget.get("reactClass") or {}).get("close", "delegate") == "block":
        return "  close() {}"
    return "  close() {\n    super.close();\n  }"


def emit_old_sheet(widget: dict) -> str:
    return (widget.get("reactClass") or {}).get("styleResetOldSheet", "null")


def render(name: str, **fields) -> str:
    return Template((TEMPLATE_DIR / name).read_text(encoding="utf-8")).substitute(**fields)


def names(widget: dict) -> dict:
    react_class = widget.get("reactClass") or {}
    name = widget["reactName"]
    return {"reactName": name,
            "nativeKey": react_class.get("nativeKey", name),
            "propsType": react_class.get("propsType", f"{name}Props")}


def render_comp(widget: dict) -> str:
    return render("comp.ts.in", header=HEADER, **names(widget),
                  imports=emit_imports(widget), maps=emit_maps(widget),
                  propTypes=emit_prop_types(widget),
                  setterEntries=emit_setters(widget),
                  manualImport=emit_manual_import(widget),
                  manualTable=emit_manual_table(widget),
                  stash=emit_stash(widget),
                  instanceFields=emit_instance_fields(widget),
                  children=emit_children(widget), movement=emit_movement(widget),
                  oldSheet=emit_old_sheet(widget),
                  constructor=emit_constructor(widget),
                  close=emit_close(widget))


def render_config(widget: dict) -> str:
    # 생성자가 prop 을 받는 위젯은 config 가 그것까지 넘겨야 한다.
    uses_props = bool((widget.get("reactClass") or {}).get("constructorProps"))
    return render("config.ts.in", header=HEADER, **names(widget),
                  createArgs="{ uid, ...newProps }" if uses_props else "{ uid }")


