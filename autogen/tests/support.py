# 네 테스트 모듈이 함께 쓰는 명세 조각과 생성 호출.

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import widget_ts_emitter as ts


def write_manifest(folder: Path, widget: dict) -> Path:
    path = folder / "manifest.json"
    path.write_text(json.dumps({"version": 2, "widgets": [widget]}), encoding="utf-8")
    return path


def base_widget(**over) -> dict:
    widget = {
        "reactName": "Demo", "nativeClass": "Demo", "nativeDir": "demo",
        "lvglCreate": "lv_demo_create", "compType": "COMP_TYPE_DEMO",
        "status": "specified",
        "generate": {"cpp": False, "ts": True, "nativeClass": False},
        "props": [], "manual": [],
        "cppBinding": {"features": ["alignment", "movement"]},
    }
    widget.update(over)
    return widget


def prop(name, kind, ts_type="number", **behavior) -> dict:
    entry = {"name": name, "tsType": ts_type, "behavior": {"kind": kind, **behavior}}
    if kind not in ("styleState", "event"):
        entry["bridgeMethod"] = "set" + name[0].upper() + name[1:]
    return entry


def manual(name, ts_type="string", reason="규칙으로 쓸 수 없다", after=None) -> dict:
    entry = {"name": name, "tsType": ts_type, "reason": reason}
    if after is not None:
        entry["after"] = after
    return entry


def load(widget: dict) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        return ts.load_widget(write_manifest(Path(folder), widget), widget["reactName"])


def setters_of(widget: dict) -> str:
    return emitter.emit_setters(load(widget))


# 명세에 구멍이 있으면 생성을 멈춰야지, 출력이 줄어들면 안 된다.
