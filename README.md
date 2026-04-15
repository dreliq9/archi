# archi

AI-native architectural and interior design server. Design buildings, validate against IRC building codes, and render photorealistic interiors — all through [Model Context Protocol](https://modelcontextprotocol.io) (MCP).

## What it does

- **Design buildings** with rooms, floors, doors, and windows on constrained lots
- **Auto-layout** rooms using a treemap solver that respects lot dimensions and setbacks
- **Live code compliance** against IRC-2021 residential building codes (egress, ventilation, room dimensions, structural spans)
- **Place furniture** with clearance checking and interference detection
- **Render interiors** with AI image generation — free tier included, no API key needed
- **Export** to SVG, DXF (contractor handoff), glTF (3D browser viewing), and IFC (BIM)

## Install

```bash
# Clone and install
git clone https://github.com/dreliq9/archi.git
cd archi
pip install -e .

# Optional: AI render paid tiers (fal.ai Flux)
pip install -e ".[render]"

# Optional: IFC export
pip install -e ".[ifc]"
```

Requires Python 3.11+ and [OCP](https://github.com/CadQuery/OCP) (the Open CASCADE kernel).

## Quick start

Add to your Claude Code MCP config (`~/.mcp.json`):

```json
{
  "mcpServers": {
    "archi": {
      "command": "python",
      "args": ["-m", "archi"],
      "cwd": "/path/to/archi",
      "env": {
        "PYTHONPATH": "/path/to/archi"
      }
    }
  }
}
```

Then in Claude Code:

```
Create a 3-bedroom ranch house on an 80x120 lot.
Add a kitchen, living room, and two bathrooms.
Render the kitchen in farmhouse style.
```

## Tools (21)

### Architecture
| Tool | Description |
|------|-------------|
| `arch_create_building` | Initialize a building on a lot with dimensions and setbacks |
| `arch_add_floor` | Add a floor/story |
| `arch_add_room` | Add a room by type — triggers automatic layout |
| `arch_remove_room` | Remove a room and its connections |
| `arch_add_opening` | Add a door, window, or archway |

### Interior
| Tool | Description |
|------|-------------|
| `interior_place_furniture` | Place parametric furniture in a room |
| `interior_remove_furniture` | Remove a furniture piece |

### Query
| Tool | Description |
|------|-------------|
| `query_get_plan` | Get floor plan as SVG with violation overlay |
| `query_get_room` | Get room details (dimensions, furniture, violations) |
| `query_get_building` | Get building summary |
| `query_check_code` | Run full code compliance check |
| `query_get_violations` | Get current violation list |
| `query_list_rooms` | List all rooms, optionally filtered by level |

### Render
| Tool | Description |
|------|-------------|
| `render_room` | Generate a photorealistic render of a room |
| `render_explore` | Render a room in multiple styles for comparison |
| `render_set_style` | Save a style preference on a room |
| `render_showcase` | Render every room on a floor in one call |
| `render_walkthrough` | Render rooms in adjacency order as a visual tour |

### Export
| Tool | Description |
|------|-------------|
| `export_to_svg` | Export 2D floor plan as SVG |
| `export_to_dxf` | Export 2D CAD for contractor handoff |
| `export_to_gltf` | Export 3D model as glTF binary (.glb) |

## AI Rendering

Three quality tiers for interior renders:

| Quality | Backend | API Key | Cost/image |
|---------|---------|---------|-----------|
| `free` (default) | Pollinations.ai | None | $0.00 |
| `fast` | fal.ai Flux | `FAL_KEY` | ~$0.01 |
| `high` | fal.ai Flux Pro | `FAL_KEY` | ~$0.05 |

The free tier works out of the box. For paid tiers, set `FAL_KEY` in your environment or in the MCP server config:

```json
"env": {
  "FAL_KEY": "your-key-here"
}
```

Get a key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys).

## Code compliance

Archi validates designs against IRC-2021 residential building codes in real time:

- **Egress** — every room must have a path through doorways to an exterior door
- **Room dimensions** — minimum width/depth per room type (7ft habitable, 5ft non-habitable)
- **Natural ventilation** — operable window area must be 4% of floor area
- **Mechanical ventilation** — kitchens and bathrooms require exhaust or operable windows
- **Structural spans** — floor joist spans checked against lumber grade tables

Violations are returned with every tool call and include IRC code references.

## Architecture

```
archi/
  server.py          # MCP server + BuildingState
  render.py          # AI image generation (Pollinations, fal.ai)
  graph/
    model.py         # BuildingGraph — nodes, edges, types
    solver.py        # TreemapSolver — automatic room layout
    validator.py     # LiveValidator — real-time code compliance
  kernel/
    primitives.py    # OCP geometry (walls, slabs, openings)
    furniture.py     # Parametric furniture defaults
    interference.py  # Collision detection
  rules/
    engine.py        # Rule evaluation engine
    profiles/        # Jurisdiction-specific rule sets (IRC-2021)
    computed/        # Computed rules (egress, ventilation, spans)
  export/
    svg.py           # Floor plan SVG renderer
    dxf.py           # DXF CAD export
    gltf.py          # glTF 3D export
    ifc.py           # IFC BIM export
  tools/
    arch.py          # Architecture MCP tools
    interior.py      # Interior design MCP tools
    query.py         # Query MCP tools
    render.py        # AI render MCP tools
    export.py        # Export MCP tools
```

## License

MIT
