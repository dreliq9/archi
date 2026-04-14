import pytest
import tempfile
import os

def test_gltf_export_single_shape():
    from archi.export.gltf import export_shapes_to_gltf
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    box = backend.make_slab([Vector(0, 0, 0), Vector(120, 0, 0), Vector(120, 120, 0), Vector(0, 120, 0)], 96.0)
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        path = f.name
    try:
        export_shapes_to_gltf([box], output_path=path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)

def test_gltf_export_multiple_shapes():
    from archi.export.gltf import export_shapes_to_gltf
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    box1 = backend.make_slab([Vector(0, 0, 0), Vector(60, 0, 0), Vector(60, 60, 0), Vector(0, 60, 0)], 96.0)
    box2 = backend.make_slab([Vector(100, 0, 0), Vector(160, 0, 0), Vector(160, 60, 0), Vector(100, 60, 0)], 96.0)
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        path = f.name
    try:
        export_shapes_to_gltf([box1, box2], output_path=path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100
    finally:
        os.unlink(path)

def test_gltf_empty_shapes():
    from archi.export.gltf import export_shapes_to_gltf
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        path = f.name
    try:
        export_shapes_to_gltf([], output_path=path)
        assert os.path.exists(path)
    finally:
        os.unlink(path)
