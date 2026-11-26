#!/usr/bin/env python3
# Check the CLI contract: generate, then --check on what was generated.

from __future__ import annotations

import io
import tempfile
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import component_ts_emitter as emitter
import ts_emitter as cli
import widget_ts_emitter as ts
from support import base_widget, load, manual, prop, setters_of, write_manifest


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
