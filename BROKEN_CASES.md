# Cases that do not run yet with proteus 2.0

These are cases, or code paths within a case, that the
`proteus-2.0.x-update` port could not get running within a few minutes of
effort. Each entry says what fails and what it would take. Suggested proteus
changes are in `PROTEUS_HANDOFF.md`; this list is about the input decks.

Tested against proteus `main` at `b9d98f5`.

## Cases that do not run

None. `2d/caissonBreakwater/fixed`, `3d/floating_caisson`, `3d/floating_bar` and
`3d/floating_bar_scorec`, listed here in an earlier version of this note, now
run; see the status table in `PROTEUS_HANDOFF.md`.

## Code paths that do not run (the case runs with another option)

### gmsh-refined meshes via `py2gmsh`

Cases affected:

| Case | Option that fails (its default) | Runs with |
|---|---|---|
| `2d/rubbleMoundBreakWater/Submerged_breakwater` | `use_gmsh=True` | `-C "use_gmsh=False"` (Triangle, ≈21k triangles) |
| `2d/waveTransformation/Dingemans_wave_shoaling` | `use_gmsh=True` | `-C "use_gmsh=False he=0.2"`; at the default `he=0.04`, Triangle gives ≈384k triangles, too big for a quick run |
| `2d/floatingStructures/floating_caisson_chrono` | `refinement=True` | `-C "refinement=False use_gmsh=False"` (Triangle, ≈12k triangles) |

- **Why:**
  - `py2gmsh` is not part of the proteus environment.
  - Its current release (4.2.3.1) renamed what these decks use: `Line` →
    `Curve`, `LineLoop` → `CurveLoop`, `py2gmsh.Fields` → `py2gmsh.Field`,
    `Mesh.getLinesFromIndex` → `getCurvesFromIndex`.
  - The bundled `MeshRefinement.py` also used `from ... import *` inside a
    function, which Python 3 forbids.
- **What the port did:** in `Submerged_breakwater` and
  `Dingemans_wave_shoaling`, the refinement block now runs only when
  `use_gmsh` is true, so `use_gmsh=False` works.
- **To fix:**
  - update `MeshRefinement.py` and the inline refinement blocks to the
    current `py2gmsh` names (or to `py2gmsh.geometry2mesh`, which now ships
    with py2gmsh);
  - or move the refinement to the `gmsh` Python API, which is in the
    environment;
  - and add `py2gmsh` to the environment if it stays.

### `2d/sediment/sediment_erosion` with its default `useRANS=1`

- **What fails:** proteus could not deep-copy the `HsuSedStress` closure passed to
  the k-ε models (`PROTEUS_HANDOFF.md`, suggestion 12; fixed in cekees/proteus#321).
  With that fix the run gets past model allocation and then stops in `WallFunctions`
  (the wall-function boundary condition is evaluated by a model it was not attached
  to), a separate proteus defect written up in the C48 handoff.
- **Runs with:** `-C "useRANS=0"`.
- **To fix:** in proteus; there is no deck-side workaround short of dropping
  the closure from the turbulence models, which would change the model.

### `3d/floating_bar_scorec` on more than one rank

- **What happens:** the case reads a PUMI mesh with one `.smb` part per rank,
  and the repository has only the one-part mesh (`floating_bar_3d0.smb`), so
  `mpiexec -n 2` aborts with `PUMI error: Could not find or open file
  "floating_bar_3d1.smb"`.
- **Workaround:** split the mesh first with SCOREC's `split` tool (in the
  proteus environment), e.g. for 2 ranks:
  ```bash
  mpiexec -n 2 split floating_bar_3d.dmg floating_bar_3d.smb parts/floating_bar_3d.smb 2
  ```
  then use `parts/floating_bar_3d0.smb` and `parts/floating_bar_3d1.smb` in
  place of the one-part file. Run this way, 2 ranks reproduce the serial bar
  motion (z = 0.2699 at t = 0.1). The split files are not committed.

## Large 3D cases: smoke runs on ceds-model (192 cores, 502 GB)

Run with the decks as committed (no `-C` options), proteus `cekees/main` b9d98f5d plus the fixes of cekees/proteus#321.
Memory over all ranks is about 65-70 KB per tetrahedron with the default PETSc options (about 120 KB with
`petsc.options.superlu_dist`), independent of the rank count.

| Case | Result |
|---|---|
| `3d/Penny_Price_Diffraction/Penny_Price_Diffraction_01` | completes on 32 ranks (935k tets, 64 GB, 1.5 h) |
| `3d/marin` | 32 ranks, 136 GB, t=4.3 of 6.0 in 4 h, no failed step; about 5.3 h in all |
| `3d/dambreak_Ubbink/dambreak_Ubbink_medium` | runs, but unstable: dt collapses at t=0.326 and the run exits 1 (default PETSc options) |
| `3d/dambreak_Ubbink/dambreak_Ubbink_fine` | runs on 32 ranks (1.59M tets, 114 GB), t≈0.07 of 0.8 at ~35 s/step; 7-16 h to finish |
| `2d/hydraulicStructures/sharp_crested_weir/deprecated/sharp_crested_weir_VM_V1`, `_VM_V2` | Refinement 185: no step with the default PETSc options (MCorr KSP stagnates); runs with `-O inputTemplates/petsc.options.superlu_dist`, 15 s/step on 8 ranks, so about 40 h to T=10 |
| `3d/Directional_Wave_Current_interaction/45DEG_R1` | needs HPC: 49M tets, 8.2M nodes, TetGen 33 min, ~3.4 TB RAM. `he=wavelength/25` runs (772k tets) |
| `3d/bathyduck` | needs HPC: 6.9M tets, >342 GB at the first allocation on 48 ranks. At 32+ ranks the geometry block at import races on the Triangle output files (`no 1.ele`) |

None of them has a context option for the mesh size.
