# Canonical topology pipeline

Archi treats solved room rectangles as the spatial source of truth and compiles them into derived building topology after every layout solve.

## Design flow

1. Semantic room intent is stored in `BuildingGraph` (`target_area`, level, adjacency, preferred dimensions).
2. `TreemapSolver` produces a deterministic seed.
3. `CSPSolver` refines positions and dimensions against room-area and adjacency constraints.
4. `sync_wall_topology()` splits all collinear room boundaries at every endpoint and creates one canonical wall node for each unique segment.
5. Shared segments carry two room owners; exterior segments carry one.
6. Semantic openings remain connected to rooms and are rebound to a canonical wall after every topology refresh.
7. SVG, DXF, and glTF export consume the canonical walls rather than independently reconstructing four walls around every room.

## Wall invariants

Derived wall nodes have:

- `derived=true`
- `wall_key`: deterministic geometry key for the current solved layout
- `orientation`: `h` or `v`
- `start_x`, `start_y`, `end_x`, `end_y` in feet
- `length_ft`
- `room_ids`: one room for exterior walls, normally two for shared walls
- `exterior`
- `thickness_in`
- `structural`
- `material`

Wall geometry and ownership are always regenerated. User-adjustable attributes (`thickness_in`, `structural`, `material`) are retained when the same `wall_key` survives a relayout.

## Opening invariants

Opening dimensions are component-scale dimensions in inches. An opening stores semantic room connections plus its derived wall binding:

- `width`, `height`, `sill_height` in inches
- `exterior`
- `wall_id`, `wall_key`
- `wall_offset_ft`
- `topology_status=bound|unresolved`

Interior openings require two rooms on the same level and bind only to a canonical wall owned by those two rooms. Exterior openings require one room and bind only to an exterior wall owned by that room. An opening that cannot fit on a candidate wall is rejected transactionally.

## Geometry safety

3D export builds each canonical wall once. Door/window cutter solids are applied with subprocess-isolated OCCT booleans via `safe_boolean_cut()`. A failed or crashing boolean is returned as a geometry warning rather than taking down the MCP server.

Furniture interference uses the same isolation strategy through `safe_boolean_common()`. Placements outside the room or colliding with existing furniture are rejected before graph commit.

## Current limitations

- Exterior openings without a wall hint choose a deterministic best-fit exterior wall (longest candidate, then wall key). A future API should expose explicit wall/side preference and opening offset.
- Furniture front direction/orientation is not modeled yet, so clearance is conservative perimeter screening, not full ergonomic compliance.
- Wall type/assembly semantics remain minimal; structural/header checking is screening only.
- The canonical topology is rectangular/axis-aligned because the current room solver produces rectangular rooms.
