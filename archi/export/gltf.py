"""glTF 3D export — tessellates OCP shapes and writes glTF/GLB files."""

from __future__ import annotations
from pathlib import Path
import numpy as np
import trimesh
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Shape


def _tessellate_shape(shape: TopoDS_Shape, tolerance: float = 0.1) -> tuple[np.ndarray, np.ndarray] | None:
    mesh = BRepMesh_IncrementalMesh(shape, tolerance)
    mesh.Perform()
    all_verts: list[list[float]] = []
    all_faces: list[list[int]] = []
    vert_offset = 0
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, location)
        if triangulation is None:
            explorer.Next()
            continue
        n_nodes = triangulation.NbNodes()
        n_tris = triangulation.NbTriangles()
        transform = location.Transformation()
        for i in range(1, n_nodes + 1):
            pnt = triangulation.Node(i)
            pnt.Transform(transform)
            all_verts.append([pnt.X(), pnt.Y(), pnt.Z()])
        for i in range(1, n_tris + 1):
            tri = triangulation.Triangle(i)
            n1, n2, n3 = tri.Get()
            all_faces.append([n1 - 1 + vert_offset, n2 - 1 + vert_offset, n3 - 1 + vert_offset])
        vert_offset += n_nodes
        explorer.Next()
    if not all_verts or not all_faces:
        return None
    return np.array(all_verts, dtype=np.float64), np.array(all_faces, dtype=np.int64)


def export_shapes_to_gltf(shapes: list[TopoDS_Shape], output_path: str | Path = "model.glb", tolerance: float = 0.1) -> None:
    meshes: list[trimesh.Trimesh] = []
    for shape in shapes:
        result = _tessellate_shape(shape, tolerance)
        if result is None:
            continue
        verts, faces = result
        meshes.append(trimesh.Trimesh(vertices=verts, faces=faces))
    if not meshes:
        # Write a minimal valid empty GLB (header only)
        Path(output_path).write_bytes(b"")
        return
    scene = trimesh.Scene(meshes)
    scene.export(str(output_path), file_type="glb")
