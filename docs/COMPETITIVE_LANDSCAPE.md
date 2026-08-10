# Competitive Landscape — Architecture & Interior Design Software

**Status:** living strategy document  
**Reviewed:** 2026-08-10  
**Purpose:** map the architecture/interior-design software landscape and extract product/architecture lessons for `archi`.

## Executive summary

The market does not contain a single system that `archi` should clone wholesale. The strongest products specialize in different layers of the design workflow:

- professional BIM systems excel at semantic building models, dependency propagation, documentation, and multidisciplinary delivery;
- residential systems excel at turning high-level house intent into conventional construction consequences quickly;
- computational/generative systems excel at option generation, parameterization, and optimization;
- interior-design systems excel at low-friction furnishing, catalogs, materials, and 2D↔3D workflows;
- open-source systems provide strong geometry, BIM, scripting, and drafting substrates;
- visualization systems excel at physically grounded presentation but should remain downstream of architectural truth.

The strategic opportunity for `archi` is therefore **not** “open-source Revit.” It is an **AI-native architectural reasoning and generation engine whose source of truth is a structured building model rather than a GUI or drawing**.

The ideal system lets an AI operate a deterministic design loop:

```text
intent
  → typed architectural command
  → constraints / program / precedent
  → generative proposal
  → solver refinement
  → canonical topology
  → geometry
  → code / engineering / cost / environmental analysis
  → critique
  → revision
  → documentation / BIM / visualization
```

This review materially changes the roadmap in five areas:

1. investigate **IfcOpenShell** as the BIM compiler rather than expanding a large custom IFC implementation;
2. study **Chief Architect** deeply as the closest commercial reference for residential intent→construction automation;
3. add a **design-system / precedent package layer** inspired by Finch and Hypar;
4. add **existing-plan ingestion** (`PDF/image/DXF/IFC → BuildingGraph`), not just graph→export;
5. move the layout engine toward **multi-objective iterative optimization** in the TestFit/Forma sense.

---

## Market map

| Family | Representative systems | Core strength | Main lesson for `archi` |
|---|---|---|---|
| Full professional BIM | Revit, Archicad, Vectorworks | Semantic building objects, coordinated documentation, schedules, multidisciplinary delivery | Treat the building model as authoritative and compile all downstream artifacts from it |
| Residential building design | Chief Architect | Fast house generation, roofs, framing, foundations, cabinetry, materials | High-level intent should automatically produce conventional construction consequences |
| Computational / generative design | Rhino + Grasshopper, Autodesk Forma, TestFit, Finch, Hypar | Parameterization, option generation, optimization, program/site reasoning | Make option generation, measurement, critique, and iteration first-class |
| Interior / consumer spatial design | Sweet Home 3D, Planner 5D, Coohom, SketchUp | Furniture, materials, catalogs, fast 2D↔3D workflows, presentation | Interior design needs richer semantics and relationship constraints, not just furniture bounding boxes |
| Open technical substrate | IfcOpenShell/Bonsai, FreeCAD, Blender, QCAD/LibreCAD | Open BIM, geometry, scripting, IFC, rendering, drafting | Integrate proven infrastructure rather than rebuilding every low-level subsystem |
| Visualization | D5, Twinmotion, Enscape, Lumion, Blender | Materials, lighting, atmosphere, walkthroughs | Visualization is a downstream compiler; generated imagery is not design truth |

---

# 1. Professional BIM

## Autodesk Revit

**Role in market:** canonical enterprise BIM reference.

Revit's most important architectural property is not its UI. It is dependency propagation. Walls, doors, windows, schedules, sections, plans, quantities, and other representations derive from one coordinated model; changing the model propagates into dependent artifacts.

### What `archi` should emulate

- one authoritative building information model;
- object relationships rather than independent drawing entities;
- derived views and schedules;
- explicit levels, assemblies, types, instances, and system relationships;
- dependency propagation from semantic changes to geometry and documentation;
- deep programmatic access.

### What `archi` should avoid copying

- GUI-first interaction as the primary control surface;
- forcing an AI to simulate mouse/keyboard CAD interaction;
- treating graphical editing operations as the underlying design language.

### Strategic lesson

`archi` should make this invariant increasingly true:

> Change an architectural object or constraint once; every dependent topology, geometry, analysis result, drawing, schedule, and export recompiles from the same source of truth.

Reference: <https://www.autodesk.com/products/revit/features>

---

## Graphisoft Archicad

**Role in market:** architect-oriented semantic BIM with strong OpenBIM positioning.

Archicad is philosophically important because it treats walls, slabs, roofs, doors, windows, stairs, curtain walls, spaces, and architectural documentation as native building concepts rather than generic geometry with metadata attached.

### What `archi` should emulate

- architectural objects as the native language of the model;
- strong IFC/BCF/IDS interoperability;
- automatic coordinated documentation;
- architect-centric workflows rather than generic solid-modeling workflows;
- embedded analysis and issue workflows.

### Strategic lesson

The OCCT kernel must remain an implementation layer beneath the architectural IR. `archi` should not become “an OCCT modeler with room labels.”

Reference: <https://www.graphisoft.com/en-us/plans-and-products/archicad/>

---

## Vectorworks Architect

**Role in market:** flexible BIM + permissive geometric design.

Vectorworks is a useful counterexample to overly rigid BIM. It combines building intelligence with relatively free modeling, algorithmic design, strong documentation, interiors, manufacturer content, interoperability, and analysis.

### What `archi` should emulate

- allow architectural semantics and unconstrained geometry to coexist;
- preserve an escape hatch for forms not anticipated by a fixed schema;
- support algorithmic and parametric design without requiring every form to map cleanly to a predeclared object class.

### Strategic lesson

Maintain two connected layers:

```text
architectural semantics ↔ arbitrary geometric representation
```

The semantic layer should remain authoritative wherever possible, but the geometry layer must be able to represent exceptions.

Reference: <https://www.vectorworks.net/en-US/architect>

---

# 2. Residential design

## Chief Architect

**Role in market:** probably the most important immediate commercial reference for `archi`'s residential vertical.

Chief Architect is purpose-built around residential and light-commercial workflows. Its core value is aggressive propagation of architectural intent into conventional house construction: walls become a building; openings cut walls; floors and ceilings form; roofs and foundations can be generated; framing can be generated; cabinetry and kitchen/bath workflows are unusually deep; material information follows the model.

### Why it matters more than Revit for the near-term roadmap

The relevant behavioral model is:

```text
3-bedroom ranch
  → room program
  → spatial layout
  → shared walls
  → doors/windows
  → floor/ceiling system
  → roof system
  → foundation
  → framing
  → cabinets/fixtures
  → quantities
  → drawings
```

That is much closer to how an AI-native architectural control plane should work than manually constructing each member.

### Capabilities worth tearing down in detail

- automatic roof generation and roof rebuilding;
- roof-type inference and editing;
- wall/floor/ceiling assemblies;
- automatic foundations;
- wall/floor/roof framing;
- doors/windows and framing consequences;
- kitchen and bath cabinetry;
- material takeoffs;
- residential drawing/document generation;
- room-type defaults and construction conventions.

### Strategic lesson

A future `archi` should increasingly operate on **design intent and building systems**, not primitive geometry.

Reference: <https://www.chiefarchitect.com/products/features/>

---

# 3. Computational and generative design

## Rhino + Grasshopper

**Role in market:** foundational computational-design environment.

Grasshopper established that architectural geometry can be generated from a computational graph rather than only manipulated as finished geometry.

### What `archi` should emulate

- explicit parametric relationships;
- reusable computational components;
- design variation from parameter changes;
- integration with analysis engines;
- optimization loops;
- provenance of generated geometry.

### Where `archi` can differ

Grasshopper exposes the computational graph directly to the human designer. `archi` can let the AI operate that graph on the user's behalf while retaining the graph internally for determinism and explainability.

### Strategic lesson

The computational graph should exist even when the user never sees or manually wires it.

Reference: <https://www.rhino3d.com/en/for/architecture/>

---

## Autodesk Forma

**Role in market:** early-stage site/design optioning and environmental analysis.

Forma's product direction is important because Autodesk is explicitly separating early generative reasoning from detailed BIM authoring. The workflow increasingly resembles:

```text
site/context
  → generated design options
  → environmental analysis
  → option comparison
  → refinement
  → detailed BIM
```

### What `archi` should emulate

- option sets as first-class artifacts;
- rapid site/program alternatives;
- environmental metrics integrated into design iteration;
- design comparison rather than one-shot generation;
- downstream handoff into detailed building models.

### Strategic lesson

`archi` should not merely produce a plan. It should be able to produce, score, explain, and revise **families of alternatives**.

Reference: <https://www.autodesk.com/products/forma>

---

## TestFit

**Role in market:** feasibility-driven generative site/building planning.

TestFit is especially valuable because it does not optimize geometry in isolation. It considers project feasibility dimensions such as zoning, unit mixes, parking, topography, infrastructure, takeoffs, and financial implications.

### What `archi` should emulate

Move from a layout objective such as:

```text
minimize room-area deviation
```

toward multi-objective project design:

```text
maximize usable area
+ improve circulation
+ improve daylight
+ satisfy code
+ maintain code margin
+ reduce construction cost
+ reduce embodied/operational carbon
+ respect owner priorities
+ improve view / orientation quality
```

### Strategic lesson

The real optimization target is **the project**, not the geometry.

Reference: <https://www.testfit.io/>

---

## Finch

**Role in market:** generative building design informed by firm-specific design knowledge.

Finch is particularly relevant because it treats institutional architectural knowledge, design systems, plan libraries, accessibility rules, local standards, and constraints as reusable computational inputs.

### What `archi` should emulate

Introduce an architectural **design-system / precedent package** layer.

Possible future packages:

```text
residential.ranch.us_mountain_west
residential.craftsman
residential.adu
healthcare.patient_room.standard
hospitality.double_loaded_corridor
industrial.small_warehouse
bathroom.ada
kitchen.work_triangle_standard
```

A package could supply:

- preferred topology;
- required spaces;
- adjacency priors;
- dimension ranges;
- circulation patterns;
- assemblies;
- default openings;
- material assumptions;
- rule sets;
- objective weights;
- construction conventions;
- known-good precedents.

### Strategic lesson

Architectural precedent can become **executable knowledge**.

Reference: <https://www.finch3d.com/product>

---

## Hypar

**Role in market:** reusable computational building logic and program-driven generation.

Hypar is relevant both for its design workflows and its developer model. It treats architectural design logic as something reusable and publishable rather than hard-coded into one monolithic application.

### What `archi` should emulate

A longer-term plugin architecture could look like:

```text
archi core
  ├── residential plugin
  ├── healthcare planning plugin
  ├── hospitality plugin
  ├── retail plugin
  └── industrial plugin
```

Each plugin could contribute:

- domain vocabulary;
- design kernels;
- precedent packages;
- constraints/rules;
- specialized solvers;
- catalogs;
- analysis functions;
- export/document conventions.

### Strategic lesson

Domain-specific architectural intelligence should eventually be modular rather than accumulated in one core package.

Reference: <https://docs.hypar.io/>

---

# 4. Open-source technical substrate

## IfcOpenShell + Bonsai

**Role in market:** the most important open-source BIM ecosystem for `archi`.

IfcOpenShell is far more than an IFC reader/writer. It provides high-level Python/C++ APIs for IFC authoring and geometry, plus tooling around drawings, schedules, costing, structural data, distribution systems, clash workflows, BCF, IDS, and model transformation. Bonsai builds a native IFC authoring workflow on top of Blender/IfcOpenShell.

### Immediate implication

The current custom IFC exporter should probably **not** grow into an independent large BIM stack.

Prefer:

```text
BuildingGraph
  → archi BIM semantic compiler
  → IfcOpenShell
  → IFC / IDS / BCF ecosystem
```

rather than:

```text
BuildingGraph
  → ever-growing custom IFC implementation
```

### Investigation priorities

- mapping `BuildingGraph` entities to IFC entities;
- placements and local coordinate systems;
- wall/slab/opening/door/window geometry;
- property sets;
- types vs occurrences;
- space boundaries;
- classifications;
- quantities;
- materials/layers;
- IDS validation;
- BCF issue exchange;
- round-trip preservation.

### Strategic lesson

**Integrate mature open BIM infrastructure instead of rebuilding IFC semantics.**

References:
- <https://docs.ifcopenshell.org/introduction.html>
- <https://bonsaibim.org/>

---

## FreeCAD

**Role in market:** open parametric CAD platform with Python APIs and BIM capabilities.

FreeCAD is useful as a technical reference because it combines OCCT geometry with parametric dependency/history, Python scripting, workbenches/plugins, and BIM-related workflows.

### What `archi` should learn

- parametric dependency/history concepts;
- plugin/workbench architecture;
- OCCT interoperability patterns;
- robust document serialization/migration;
- editable procedural geometry.

### What not to copy

`archi` should not turn into a general-purpose desktop CAD application.

Reference: <https://www.freecad.org/>

---

## Blender

**Role in market:** procedural geometry + visualization + animation.

Geometry Nodes provides a mature procedural graph over meshes, curves, instances, volumes, fields, and attributes. Blender is also an exceptional downstream visualization environment.

### `archi` positioning

Do **not** make Blender the building source of truth.

Do support Blender as:

- high-fidelity visualization target;
- procedural detailing surface;
- animation/walkthrough target;
- geometry-processing adapter where useful.

Reference: <https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/introduction.html>

---

## Sweet Home 3D

**Role in market:** unusually effective open-source interior/furnishing workflow.

Sweet Home 3D demonstrates how little friction there can be between drawing a plan, placing doors/windows/furniture, and immediately seeing a usable 3D representation.

### What `archi` should learn

- synchronized plan + 3D interaction concepts;
- automatic openings in walls;
- furniture catalogs;
- material application;
- interior-focused affordances;
- extensible catalogs/plugins.

### Licensing caution

Sweet Home 3D is GPL. It is useful for architectural/product reference, but direct code reuse requires license-aware analysis.

Reference: <https://www.sweethome3d.com/features/>

---

## QCAD / LibreCAD

**Role in market:** mature 2D drafting references.

These systems are less useful for architectural intelligence, but valuable references for:

- dimensions;
- snapping;
- layers;
- blocks;
- hatches;
- line types;
- symbols;
- annotations;
- sheet-style drafting;
- command-line conversion and scripting.

### Strategic lesson

When `archi` reaches serious documentation generation, drafting quality becomes its own compiler problem and should be treated separately from building topology.

References:
- <https://librecad.org/>
- <https://www.qcad.org/>

---

# 5. Interior-design platforms

## Planner 5D

**Role in market:** accessible AI-assisted interior planning with strong ingestion and visualization workflows.

Planner 5D's important architectural capability is not just image generation. It can recognize floor plans and convert them into editable spatial models, then layer furnishing/rendering workflows on top.

### What `archi` should emulate

Add bidirectional workflow:

```text
BuildingGraph → plans / BIM / geometry
```

and:

```text
PDF / raster floor plan / DXF / IFC
  → recognition / parsing
  → topology reconstruction
  → BuildingGraph
```

### Strategic lesson

Existing-building ingestion is likely as important commercially as greenfield generation.

Reference: <https://support.planner5d.com/>

---

## Coohom

**Role in market:** high-speed floor-plan ingestion, furnishing, catalog workflows, and rendering.

Coohom demonstrates how powerful a large product/material/furniture knowledge layer becomes when tied to an editable spatial model.

### What `archi` should learn

The interior model needs semantic relationships beyond `{x, y, width, depth}`.

Future interior object classes should include at least:

```text
furniture
fixture
appliance
cabinetry
finish
surface
lighting
textile
decor
```

Useful relationships/constraints include:

```text
against_wall
centered_on
faces
aligned_with
adjacent_to
work_triangle
clearance_zone
visual_axis
task_light_for
served_by
opens_into
```

### Strategic lesson

Interior design should become its own semantic constraint domain rather than a generic geometry-placement feature.

Reference: <https://www.coohom.com/>

---

## SketchUp

**Role in market:** extremely approachable direct 3D modeling with a large extension/content ecosystem.

SketchUp's main lesson is usability and ecosystem reach. It is not the strongest semantic BIM system, but it made spatial modeling approachable and built enormous value around extensions and reusable components.

### What `archi` should learn

- keep rapid conceptual edits cheap;
- allow imperfect/incomplete models during early design;
- make reusable content and extensions easy to create;
- avoid requiring fully specified BIM semantics before a concept can exist.

Reference: <https://www.sketchup.com/>

---

# 6. Visualization platforms

## D5 Render, Twinmotion, Enscape, Lumion

These platforms show how specialized architectural visualization has become: real-time ray/path tracing, material systems, asset libraries, vegetation, lighting, environments, animation, VR, live synchronization, and presentation workflows.

### Strategic conclusion

`archi` should **not** attempt to make diffusion output the renderer of record.

The authoritative visualization pipeline should become:

```text
BuildingGraph
  → canonical topology
  → geometry/material/light scene
  → physically grounded renderer
  → optional generative enhancement
```

not:

```text
room description
  → diffusion image
  → assume image matches design
```

The current AI rendering layer remains useful for ideation and mood exploration, but it should be clearly distinguished from geometry-faithful visualization.

References:
- <https://www.d5render.com/solutions/architecture>
- <https://www.twinmotion.com/>
- <https://www.chaos.com/enscape>
- <https://lumion.com/>

---

# 7. Competitive whitespace

The market is crowded, but the strongest products remain organized around human-operated applications.

`archi`'s potential differentiation is the control plane itself:

> An AI can reason directly over structured design state, invoke deterministic solvers and geometry operations, inspect structured evidence, revise its own design, compare alternatives, and compile professional artifacts without operating a GUI as a human surrogate.

No single reviewed competitor combines all of the following as its primary architecture:

- LLM-native command surface;
- structured architectural graph as source of truth;
- deterministic constraint solving;
- canonical architectural topology;
- robust solid geometry;
- code/compliance evidence returned inside the design loop;
- generative option exploration;
- program/site/cost/environment objective optimization;
- interior semantic reasoning;
- professional BIM/documentation compilation;
- autonomous iterative critique/revision.

That is the whitespace `archi` should target.

---

# 8. Target architecture implied by the review

At the center should be a richer **architectural IR / BuildingGraph**:

```text
site
  → building
    → levels
      → spaces / zones
      → walls
      → openings
      → slabs
      → roofs
      → stairs
      → assemblies
      → fixtures / furniture
      → materials
      → building systems
```

Around it, distinct engines should remain separable:

## Constraint engine

Responsible for:

- building code;
- accessibility;
- zoning;
- dimensional constraints;
- adjacency;
- program requirements;
- owner requirements.

## Generative / optimization engine

Responsible for:

- treemap seeds;
- CP-SAT refinement;
- heuristics;
- design-space exploration;
- evolutionary/search methods where useful;
- learned proposal generation;
- Pareto-front / multi-objective comparison.

## Topology compiler

Responsible for converting semantic spatial intent into canonical architectural relationships:

- shared walls;
- exterior walls;
- wall junctions;
- openings;
- boundaries;
- floor/roof interfaces;
- circulation topology.

## Geometry kernel

OCCT-backed exact geometry:

- solids;
- booleans;
- interference;
- intersections;
- fabrication-grade geometry where necessary;
- subprocess isolation for crash-prone operations.

## Building-systems engine

Progressively add:

- roofing;
- floor systems;
- foundations;
- framing;
- cabinetry;
- eventually MEP and envelope assemblies.

## Analysis engine

Potential analyses:

- daylight;
- solar;
- energy;
- acoustics;
- circulation;
- view quality;
- embodied carbon;
- quantities/cost;
- structural screening / delegated engineering adapters;
- site/environment constraints.

## Interior engine

Responsible for:

- furniture;
- cabinetry;
- appliances;
- fixtures;
- finishes;
- lighting;
- ergonomic/clearance constraints;
- visual and functional relationships.

## Documentation compiler

Responsible for:

- plans;
- sections;
- elevations;
- dimensions;
- schedules;
- details;
- quantities;
- sheets / annotations.

## BIM compiler

Prefer an `IfcOpenShell`-backed path for:

- IFC;
- IDS;
- BCF;
- semantic BIM handoff;
- interoperability validation.

## Visualization compiler

Targets may include:

- glTF;
- Blender;
- Twinmotion / D5 / similar adapters;
- physically grounded internal rendering;
- optional generative enhancement.

## AI design orchestrator

The orchestration layer should be capable of:

```text
propose
→ solve
→ inspect
→ analyze
→ criticize
→ modify
→ compare
→ select
→ document
```

That iterative loop is the core product differentiation.

---

# 9. Roadmap implications

## P0 — immediate research / architecture decisions

### A. IfcOpenShell integration spike

Determine whether `archi.export.ifc` should become a thin compiler layer over IfcOpenShell.

Deliverables:

- BuildingGraph→IFC mapping experiment;
- walls/slabs/spaces/openings/doors/windows;
- property-set strategy;
- material/assembly mapping;
- round-trip test;
- IDS/BCF feasibility.

### B. Chief Architect capability teardown

Document how Chief models and automatically derives:

- roofs;
- foundations;
- framing;
- floors/ceilings;
- cabinets;
- materials;
- openings;
- residential documentation.

For each capability classify:

```text
architectural rule
solver/generator
geometry compiler
catalog/default data
analysis
documentation behavior
```

The goal is conceptual reimplementation, not binary compatibility or UI cloning.

### C. Design-system / precedent package RFC

Define the package contract for domain knowledge such as:

```text
residential.ranch
residential.adu
bathroom.ada
hospitality.hotel_floor
industrial.warehouse
```

Packages should be able to contribute schemas, priors, rules, objective weights, and generators without modifying the core.

---

## P1 — model and workflow expansion

### D. Existing-plan ingestion

Add a pipeline for:

```text
IFC / DXF / SVG / PDF / raster plan
  → parsed primitives
  → topology inference
  → semantic classification
  → BuildingGraph
  → confidence / unresolved evidence
```

Do not silently guess ambiguous topology; expose uncertainty to the agent.

### E. Multi-objective design engine

Evolve CP-SAT and/or higher-level search into an option-generation system with explicit objectives and tradeoffs.

Return multiple alternatives with structured scoring rather than only one feasible plan.

### F. Richer interior IR

Move from generic furniture placement to semantic objects, relations, clearances, circulation zones, and functional patterns.

---

## P2 — downstream professional fidelity

### G. Documentation compiler

Upgrade plans/DXF into professional drawing semantics:

- dimensions;
- symbols;
- line weights;
- hatches;
- room tags;
- door/window tags;
- schedules;
- sections/elevations;
- sheets.

### H. Physically grounded visualization

Generate deterministic render geometry/material/light scenes first, then optionally use generative models for enhancement or style exploration.

### I. Building-system generators

Following the Chief Architect reference model, progressively implement intent→construction automation for:

- roof;
- foundation;
- floors/ceilings;
- framing;
- cabinets;
- envelope assemblies.

---

# 10. Product-positioning guardrails

The competitive review suggests several things `archi` should **not** become.

## Do not become a Revit clone

Professional BIM compatibility is important; duplicating decades of GUI/workflow surface is not.

## Do not become a generic CAD kernel

OCCT is infrastructure. Architectural intent and reasoning are the product.

## Do not make AI imagery architectural truth

Generated images are useful for ideation; geometry/BIM must remain authoritative.

## Do not hide uncertainty

Code checks, imported plans, inferred topology, structural assumptions, and generated alternatives should carry explicit evidence/coverage/confidence.

## Do not accumulate every vertical in core

Domain-specific architectural intelligence should become package/plugin-based once the shared substrate is stable.

## Do not optimize a floor plan in isolation

The long-term objective function is the whole project: spatial quality, code, cost, environment, constructability, owner preferences, and downstream delivery.

---

# 11. Current `archi` alignment

The topology-hardening work already moves the repository toward this competitive target:

- `BuildingGraph` provides semantic state;
- `TreemapSolver → CSPSolver` provides deterministic layout generation/refinement;
- canonical shared wall topology bridges spaces into architectural topology;
- wall-bound openings improve semantic/geometry coherence;
- OCCT provides a real geometry kernel;
- subprocess isolation protects the agent/server from OCCT boolean failures;
- SVG/DXF/glTF compile from design state;
- live validation places evidence inside the mutation loop;
- MCP exposes the model directly to an AI rather than requiring GUI automation.

The main remaining gaps are therefore increasingly clear:

1. richer architectural entities and building systems;
2. robust BIM compilation via IfcOpenShell;
3. precedent/design-system knowledge packages;
4. bidirectional model ingestion;
5. multi-option, multi-objective optimization;
6. deeper interior semantics;
7. professional documentation;
8. broader and more rigorous compliance evidence.

---

## Bottom line

The competitive landscape validates `archi`'s control-plane direction.

The strongest opportunity is not to beat every incumbent at its specialty. Instead, `archi` should compose proven specialty layers beneath an AI-native architectural IR and iteration engine.

The long-term product thesis is:

> **Architecture as a machine-operable reasoning system: structured intent, deterministic generation, explicit constraints and evidence, iterative optimization, and professional compilation to BIM, drawings, geometry, and visualization.**
