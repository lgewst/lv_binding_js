#!/usr/bin/env python3
# Check the CLI contract: generate, then --check on what was generated.

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import ts_emitter as cli
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


class Cli(unittest.TestCase):
    def test_generate_then_check_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = write_manifest(root, base_widget(props=[prop("v", "value")]))
            with patch.object(cli, "GENERATED_DIR", root / "out"), redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--widget", "Demo", "--manifest", str(manifest)]), 0)
                self.assertEqual(
                    cli.main(["--widget", "Demo", "--manifest", str(manifest), "--check"]), 0)
            self.assertTrue((root / "out/Demo/comp.ts").is_file())
            self.assertTrue((root / "out/Demo/config.ts").is_file())

    def test_check_fails_when_the_output_is_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            widget = base_widget(props=[prop("v", "value")])
            manifest = write_manifest(root, widget)
            with patch.object(cli, "GENERATED_DIR", root / "out"), redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--widget", "Demo", "--manifest", str(manifest)]), 0)
            widget["props"].append(prop("w", "value"))
            write_manifest(root, widget)
            with patch.object(cli, "GENERATED_DIR", root / "out"), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(
                    cli.main(["--widget", "Demo", "--manifest", str(manifest), "--check"]), 1)

    def test_failure_is_reported_on_stderr(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = write_manifest(Path(folder), base_widget(
                props=[prop("v", "value", compare="stirct")]))
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli.main(["--widget", "Demo", "--manifest", str(manifest)]), 1)
            self.assertIn("생성 실패", err.getvalue())


if __name__ == "__main__":
    unittest.main()
