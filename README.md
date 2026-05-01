# archi — AI-Native Architectural Design MCP Server

<!-- mcp-name: io.github.dreliq9/archi -->

**Design buildings that pass code.** archi is an MCP server for AI-native
architectural and interior design — automatic room layout, real-time
IRC-2021 code compliance, photorealistic interior renders, and
contractor-ready export. One server, design through delivery.

```
You: "Design a 3-bedroom ranch on an 80×120 lot, check it against IRC-2021,
      render the kitchen in farmhouse style, and export DXF for the contractor."
Claude → arch_create_building → arch_add_floor → arch_add_room (×N)
       → query_check_code → render_room → export_to_dxf
Result: Validated floor plan + farmhouse kitchen render + contractor DXF
```

Where generic AI image tools stop at a render and CAD packages stop at
geometry, archi covers the full design loop:

- **Layout engine** — TreemapSolver auto-fits rooms to lot dimensions and setbacks — 5 tools
- **Live code compliance** — IRC-2021 egress, ventilation, dimensions, structural spans — every tool call returns current violations
- **Interior design** — Parametric furniture with clearance and interference detection — 2 tools
- **AI rendering** — Pollinations (free, no key) + fal.ai Flux (paid) — 5 tools
- **Multi-format export** — SVG plans, DXF for contractors, glTF for browsers, IFC for BIM — 3 tools (+ optional IFC)

## Available Tools (21 across 5 categories)

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

---

## Setup

### Prerequisites

- Python 3.11+
- [OCP](https://github.com/CadQuery/OCP) (the OpenCASCADE kernel) — pulled in as a dependency
- **Optional:** [fal.ai](https://fal.ai) account and `FAL_KEY` for paid render tiers
- **Optional:** `[ifc]` extra for IFC/BIM export

### Install

```bash
git clone https://github.com/dreliq9/archi.git
cd archi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Optional: paid render tiers (fal.ai Flux)
pip install -e ".[render]"

# Optional: IFC export
pip install -e ".[ifc]"
```

### Verify

```bash
source .venv/bin/activate
python -c "import archi; print(archi.__version__)"
pytest tests/ -v
```

### Connect to Claude Code

```bash
claude mcp add-json archi '{"type":"stdio","command":"python","args":["-m","archi"],"cwd":"/FULL/PATH/TO/archi","env":{"PYTHONPATH":"/FULL/PATH/TO/archi"}}' --scope user
```

Or edit `~/.claude.json` directly:

```json
{
  "mcpServers": {
    "archi": {
      "command": "python",
      "args": ["-m", "archi"],
      "cwd": "/FULL/PATH/TO/archi",
      "env": {
        "PYTHONPATH": "/FULL/PATH/TO/archi"
      }
    }
  }
}
```

### Claude Desktop

Add the same config to your Claude Desktop config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Verify connection

```bash
claude mcp list       # from terminal
/mcp                  # inside Claude Code
```

---

## Key Features

### Live IRC-2021 code compliance

Most CAD tools validate after the fact. archi's `LiveValidator` re-runs
on every room add, move, or modification — egress paths re-traced,
ventilation re-computed, span tables re-checked. Violations come back
with every tool response, so the agent course-corrects mid-design
instead of hitting a wall at QC.

Codes implemented:

- **Egress (R311)** — every habitable room must reach an exterior door through doorways
- **Minimum room dimensions (R304)** — 7ft habitable, 5ft non-habitable
- **Natural ventilation (R303.1)** — operable window area must be at least 4% of floor area
- **Mechanical ventilation (R303.4)** — kitchen and bath exhaust or operable windows
- **Structural spans** — floor joist spans checked against lumber grade tables

Each violation includes the IRC code reference for transparency.

### TreemapSolver auto-layout

Adding a room doesn't drop it on top of others. The `TreemapSolver`
re-fits the floor plan to the lot, respecting setbacks, adjacency
hints, and minimum dimensions. The agent says "add a kitchen and a
master bedroom"; the solver figures out where they go.

### Free AI rendering, no key required

The default render tier uses [Pollinations.ai](https://pollinations.ai)
— no signup, no API key, no payment. From `pip install` to first
photorealistic render is one tool call. Upgrade to fal.ai Flux
(~$0.01/image) or Flux Pro (~$0.05/image) when you need higher quality.

### Multi-format handoff to the full delivery chain

One design, every downstream surface:

- **SVG** — floor plans with violation overlays for review
- **DXF** — 2D CAD for contractor handoff (AutoCAD-compatible)
- **glTF** — 3D model for browser viewers (Three.js, model-viewer, Blender)
- **IFC** — BIM-grade industry standard for architects and engineers (via `[ifc]` extra)

### OCCT geometry kernel

archi runs on [OpenCASCADE](https://dev.opencascade.org/) via the
[OCP](https://github.com/CadQuery/OCP) Python bindings — the same
kernel that powers FreeCAD, KiCad's 3D viewer, and (under the hood)
every CadQuery script. Walls, slabs, and openings are real
`TopoDS_Solid` shapes, not bitmap approximations.

### Stateful design graph

The `BuildingGraph` (nodes for rooms / openings / levels, edges for
adjacency and connections) persists across tool calls. An agent can
incrementally add rooms, query the current state, run compliance, and
revise — without reloading or re-specifying the design.

### Structured tool outputs

`arch_*` tools return Pydantic-validated envelopes — both human-readable
text (via `__str__`) and typed JSON (`structuredContent`). Agents can
read fields like `result.building_id` or `result.violation_counts`
directly. Inputs are schema-validated: `room_type` and `opening_type`
are `Literal` enums (typos like `"kitcen"` rejected before the graph
touches the value), and numeric inputs are range-constrained
(lot dimensions `> 0`, stories `1..10`, etc.).

---

## Examples

Sample prompts to try:

- *"Design a 3-bedroom 2-bathroom ranch on an 80×120 lot, IRC compliant, then render every room."*
- *"Add a master suite to the existing first floor — auto-layout, then check the egress paths."*
- *"Show me three style options for the kitchen: modern, farmhouse, Mediterranean."*
- *"Walk through the house in adjacency order — entry, living room, kitchen, dining."*
- *"Export floor plans as SVG and the 3D model as glTF — I want to share it in a browser."*
- *"Run a full code check, then list any violations with IRC references."*
- *"Place a king bed, two nightstands, and a dresser in the master bedroom — flag any clearance issues."*
- *"Render the kitchen in five lighting conditions: morning, midday, golden hour, dusk, night."*

---

## AI Rendering

Three quality tiers for interior renders:

| Quality | Backend | API Key | Cost/image |
|---------|---------|---------|-----------|
| `free` (default) | Pollinations.ai | None | $0.00 |
| `fast` | fal.ai Flux | `FAL_KEY` | ~$0.01 |
| `high` | fal.ai Flux Pro | `FAL_KEY` | ~$0.05 |

The free tier works out of the box. For paid tiers, set `FAL_KEY` in
the MCP server config:

```json
"env": {
  "PYTHONPATH": "/FULL/PATH/TO/archi",
  "FAL_KEY": "your-key-here"
}
```

Get a key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys).

---

## Architecture

```
Claude Code / Claude Desktop / any MCP client
        │
        │  stdio (JSON-RPC)
        ▼
   archi server (archi/server.py)
        │
        ├── graph/model        ← BuildingGraph (rooms, openings, levels)
        ├── graph/solver       ← TreemapSolver (auto-layout)
        ├── graph/validator    ← LiveValidator (real-time code compliance)
        ├── kernel/primitives  ← OCP geometry (walls, slabs, openings)
        ├── kernel/furniture   ← Parametric furniture defaults
        ├── kernel/interference← Collision and clearance detection
        ├── rules/engine       ← Rule evaluation, IRC-2021 profile
        ├── render             ← Pollinations + fal.ai Flux
        └── export             ← SVG / DXF / glTF / IFC
              │
              ▼
        Renders + plans + 3D models + BIM exports
```

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

---

## Output Files

By default, renders and exports save into the current working
directory of the MCP server process. Override per call via the
`output_path` parameter on `render_*` and `export_*` tools.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'OCP'`** — OCP installation can fail
on macOS without proper wheels. Try `pip install cadquery-ocp` directly, or
use the [conda-forge package](https://anaconda.org/conda-forge/ocp) and
launch the server inside the conda env.

**`render_room` returns "Failed to fetch from Pollinations"** —
Pollinations.ai is a free, best-effort service. Retry, or upgrade to the
`fast`/`high` tier with a `FAL_KEY`.

**Tool calls return code violations even on simple designs** — Working as
intended. archi reports violations continuously so the agent can fix them
incrementally. Use `query_check_code` for a full report or
`query_get_violations` to see the current list.

**`fal.ai` returns 401** — `FAL_KEY` not set, or set in your shell but not
in the MCP config. MCP servers don't inherit shell env by default — add
`FAL_KEY` to the `env` block in your `~/.claude.json` config.

**Generated DXF won't open in newer AutoCAD versions** — archi exports a
broadly compatible DXF flavor. If a tool requires a newer version,
post-process with `qcad` or `oda-file-converter`.

**`pytest` fails on import** — activate the venv and reinstall:
`pip install -e ".[render,ifc]"`.

---

## Planned Work

- **More jurisdictions** — California Building Code (CBC), International Building Code (IBC) for commercial, IRC variants for additional states
- **Multi-floor egress** — staircase egress paths and discharge requirements (R311)
- **Energy codes** — IECC residential, Title 24 for California
- **Structural** — basic seismic and wind-load checks beyond span tables
- **Exterior parametrics** — siding, roofing, foundation
- **Live 3D viewer** — return interactive viewer URLs directly in MCP responses
- **Multi-building sites** — accessory dwelling units, garages, site planning

---

## Acknowledgments

archi was co-developed by Adam Steen and [Claude](https://claude.ai) (Anthropic).

## License

MIT — see [LICENSE](LICENSE).
