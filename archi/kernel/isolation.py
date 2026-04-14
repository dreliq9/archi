"""Subprocess isolation for heavy geometry operations.

OCCT segfaults are process-fatal. This module runs heavy booleans in a
subprocess so the main server survives crashes. Same pattern as CAiD.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape

from archi.kernel.backend import shape_volume
from archi.kernel.result import BuildResult

_SEGFAULT_CODES = {139, 134, -11, -6}

_WORKER_SCRIPT = '''
import sys
import json
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


def load_brep(path: str) -> TopoDS_Shape:
    shape = TopoDS_Shape()
    builder = BRep_Builder()
    BRepTools.Read_s(shape, path, builder)
    return shape


def save_brep(shape: TopoDS_Shape, path: str) -> None:
    BRepTools.Write_s(shape, path)


def volume(shape: TopoDS_Shape) -> float:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def main():
    args = json.loads(sys.argv[1])
    base = load_brep(args["base_path"])
    tool = load_brep(args["tool_path"])
    op = args["operation"]

    if op == "cut":
        algo = BRepAlgoAPI_Cut(base, tool)
    elif op == "union":
        algo = BRepAlgoAPI_Fuse(base, tool)
    else:
        print(json.dumps({"ok": False, "reason": f"Unknown operation: {op}"}))
        sys.exit(1)

    if not algo.IsDone():
        print(json.dumps({"ok": False, "reason": f"Boolean {op} failed"}))
        sys.exit(1)

    result = algo.Shape()
    save_brep(result, args["result_path"])
    vol = volume(result)
    print(json.dumps({"ok": True, "volume": vol}))


if __name__ == "__main__":
    main()
'''


def _save_brep(shape: TopoDS_Shape, path: str) -> None:
    BRepTools.Write_s(shape, str(path))


def _load_brep(path: str) -> TopoDS_Shape:
    shape = TopoDS_Shape()
    builder = BRep_Builder()
    BRepTools.Read_s(shape, str(path), builder)
    return shape


def _run_isolated(base_shape: TopoDS_Shape, tool_shape: TopoDS_Shape, operation: str) -> BuildResult:
    if base_shape is None or tool_shape is None:
        return BuildResult.fail("Cannot run boolean on None shape")

    with tempfile.TemporaryDirectory(prefix="archi_iso_") as tmpdir:
        base_path = str(Path(tmpdir) / "base.brep")
        tool_path = str(Path(tmpdir) / "tool.brep")
        result_path = str(Path(tmpdir) / "result.brep")
        script_path = str(Path(tmpdir) / "worker.py")

        _save_brep(base_shape, base_path)
        _save_brep(tool_shape, tool_path)

        with open(script_path, "w") as f:
            f.write(_WORKER_SCRIPT)

        args = json.dumps({
            "base_path": base_path,
            "tool_path": tool_path,
            "result_path": result_path,
            "operation": operation,
        })

        try:
            proc = subprocess.run(
                [sys.executable, script_path, args],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return BuildResult.fail(
                f"Boolean {operation} timed out after 30s",
                hint="Geometry may be too complex — simplify before retrying",
            )

        if proc.returncode in _SEGFAULT_CODES or proc.returncode < 0:
            return BuildResult.fail(
                f"OCCT segfault during boolean {operation} (exit code {proc.returncode})",
                hint="Simplify geometry or try a different boolean approach",
            )

        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            return BuildResult.fail(f"Boolean {operation} subprocess failed: {stderr}")

        try:
            output = json.loads(proc.stdout.strip())
        except (json.JSONDecodeError, ValueError):
            return BuildResult.fail(f"Could not parse subprocess output: {proc.stdout[:200]}")

        if not output.get("ok"):
            return BuildResult.fail(output.get("reason", "Unknown subprocess error"))

        result_shape = _load_brep(result_path)
        vol = output.get("volume", shape_volume(result_shape))

        return BuildResult(shape=result_shape, valid=True, volume=vol)


def safe_boolean_cut(base: TopoDS_Shape | None, tool: TopoDS_Shape | None) -> BuildResult:
    if base is None or tool is None:
        return BuildResult.fail("Cannot run boolean on None shape")
    return _run_isolated(base, tool, "cut")


def safe_boolean_union(a: TopoDS_Shape | None, b: TopoDS_Shape | None) -> BuildResult:
    if a is None or b is None:
        return BuildResult.fail("Cannot run boolean on None shape")
    return _run_isolated(a, b, "union")
