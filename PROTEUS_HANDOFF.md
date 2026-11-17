# Handoff: proteus changes suggested while porting air-water-vv

This note is for a proteus development session. The `proteus-2.0.x-update`
branch of air-water-vv changes only the input decks, and only enough that each
case runs with current `parun`: `parun case.py --TwoPhaseFlow` for the
`TwoPhaseFlowProblem` decks, and `parun case_so.py` for the older split-file
decks. It does not check the results against the reference data. Anything
that looks like it belongs in proteus is listed here and has **not** been
changed in proteus. Cases that still do not run, or are too large to run here,
are listed in `BROKEN_CASES.md`.

Tested against proteus `main` at `b9d98f5`, built from source in
`environment-openmpi-dev.yml` (OpenMPI 5, Python 3.13, numpy 2). The smoke
runs were short: a fraction of a second to a few seconds of simulated time, on
1 and 2 MPI ranks, in a 4-core, 15 GB container.

To reproduce a run in a container that runs as root, OpenMPI needs:

```bash
export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
```

## Notes for the next session

### Building proteus

- **Conda:** Miniforge plus `mamba env create -f environment-openmpi-dev.yml`
  (env `proteus-dev-openmpi`). It includes PETSc, PUMI (scorec), Chrono
  (`pychrono`) and the `gmsh` Python module.
- **Compile in parallel, then install editable:**
  ```bash
  N=<cores> python setup.py build_ext -i
  pip install --no-deps --no-build-isolation -e .
  ```
  A plain `pip install -e .` builds the 68 extensions one at a time (over
  30 min on 4 cores; about 2 min with `N=4`).
- **Run the proteus tests** with `pytest -n <k>` (xdist), not `--forked`:
  OpenMPI is not fork-safe.

### Running a case

- **Two kinds of deck:**
  - `TwoPhaseFlowProblem` decks:
    `parun case.py --TwoPhaseFlow -l 3 -v -D <outdir> -C "<opts>"`
  - split-file decks: `parun case_so.py -l 3 -v -D <outdir> -C "<opts>"`
  - Pass the case as a positional argument, not with `-f` (suggestion 1).
- **Shortening a run:** the end time must be at least half of `dt_output`
  (or `T/Np` in the wave decks), or the run stops after its first step and
  still reports success (suggestion 5). The status table at the end gives
  the `-C` options used for each case.
- **Decks with no end-time or mesh option** (most split-file 3D decks): run
  under `timeout` and count the case as working if
  `Step Taken, System time step t=` advances.
- **Output files land in the case folder:** meshes (`mesh.*`,
  `<name>.poly/.node/.ele`), `proteus_default.log`, `__pycache__`, and some
  generated input such as `RandomSeries_*` and `*.res` (wave tanks).
  - Clean them with `git clean -fdX 2d 3d Tests` (ignored files only).
  - Check `git status` before committing: `RandomSeries_*` and `*.res` are not
    ignored, and slipped into a commit once.
- **Smoke-run helper used for this port** (`$1` case folder, `$2` deck, `$3`
  ranks, `$4` `-C` options, `$5` time limit in seconds):
  ```bash
  cd "$1"; name=${2%.py}; out=/tmp/awvv/${name}_np$3; mkdir -p $out
  tpf=--TwoPhaseFlow; [[ $2 == *_so.py ]] && tpf=
  ulimit -v 10000000   # 10 GB cap, so a runaway mesh fails instead of the OOM killer
  timeout ${5:-900} mpiexec -n $3 parun $2 $tpf -l 3 -v -D $out -C "$4" > $out.log 2>&1
  grep -a -E "Elements Owned|Completed .* run" $out.log
  grep -a -oE "Step Taken, System time step t= *[0-9.e+-]+" $out.log | tail -1
  ```
- **Logs are binary-safe only with `grep -a`.** Several proteus errors
  (WaveTools) call `sys.exit` with no traceback, so read the last lines of
  the log as well.

### Branch conventions (the owner's preference)

- The air-water-vv branch `proteus-2.0.x-update` is kept as **one commit**.
  Amend it and push with `--force-with-lease`, and update the commit message's
  case list.
- This note and `BROKEN_CASES.md` live in that commit. Keep their status
  tables current.

### Pitfalls found during the port that may recur

- **Python 2 `zip`:** a loop like `for a, b in zip(lst, ...)` that appends to
  `lst` never ends under Python 3 and eats all memory. All such loops in the
  split-file decks are now `list(zip(...))`; watch for the same with `map` and
  `filter`.
- **Integer division:** Python 2 `/` between integers floored, and no tool
  catches this statically. Look for float counts passed to `range` or
  `linspace`.
- **numpy 2:**
  - ragged arrays need `dtype=object`;
  - numpy integers are not `int` (suggestion 9);
  - their `repr` is `np.int32(…)` (suggestion 14);
  - `linspace` needs an integer `num`.
- **Compiled (Cython) proteus classes reject lists** where they want arrays:
  `WaveTools` coefficients and positions, boundary orientations, `g` in k-ε.
  Use `np.array`.
- **Gravity in 3D:** `setDefaults()` puts gravity along −z in 3D. Decks with y
  vertical must set it themselves (suggestion 6).
- **Positional calls into `WaveTools.TimeSeries`** were shifted by a new
  argument (suggestion 15). Check other long positional calls the same way.

### Tools that helped

- **Python 2 → 3:** `fissix`, a maintained fork of `2to3`, installed outside
  the env with `pip install --target <dir> fissix` and run as
  `PYTHONPATH=<dir> python -m fissix -w -n -f print -f except -f raise -f zip ...`.
  Include the `zip`, `map` and `filter` fixers. Expand leading tabs with
  `expand -i -t 8`, which keeps Python 2's indentation meaning.
- **Splitting a PUMI mesh:** SCOREC's `split` (in the env) splits a one-part
  `.smb` for an n-rank run of `3d/floating_bar_scorec`:
  `mpiexec -n N split model.dmg mesh.smb out/mesh.smb N`.
- **Reference copies inside proteus:**
  - `test/RANS3PSed/bed_sediment` is proteus's updated copy of the air-water-vv
    sediment deck.
  - `test/TwoPhaseFlow/damBreak*.py`, `test/FSI/*` (Chrono, `MoveMeshElastic`)
    and `test/MeshAdaptPUMI/gauge_compare/*` show the current APIs.

### Suggested order for the next session

1. **Fix the proteus items that block cases or silently give wrong results:**
   - 12 (the `HsuSedStress` deep copy blocks `sediment_erosion` with k-ε);
   - 17 (`BodyDynamics`: default scheme and springs, 3D `coords_system`,
     Runge-Kutta rotating about z only);
   - 20 (PUMI `faceList`);
   - 5 and 4 (runs that stop early or drop gauges without a warning);
   - 14 (`writePoly`);
   - 21 (the `epsFact_solid` keyword silently changed meaning; check any other
     old decks for it).
   Then remove the matching deck workarounds:
   - the `RigidBody3D` subclass and forced `Forward_Euler` in
     `3d/floating_caisson`;
   - `reconstructedFlag = 0` in `3d/floating_bar_scorec`;
   - the `int()` flag wrappers;
   - the integer facets in `3d/bathyduck`.
2. **Run the six HPC-sized 3D cases** listed in `BROKEN_CASES.md`.
3. **Replace the `py2gmsh` refinement** in `Submerged_breakwater`,
   `Dingemans_wave_shoaling` and `floating_caisson_chrono` with the `gmsh`
   Python API, or update it to py2gmsh 4.2.3.1.
4. **Validation runs**, e.g. `2d/caissonBreakwater/sliding` against Cozzuto et
   al. (2019), Figs. 9–10 (cited in its README). The paper's mesh is λ/200
   (≈1 cm) and the run is about 20 s.
5. **Strengthen `Tests/`:** each test runs about 0.01 s and only checks for
   `Step Failed`. Most would also pass a run that stops at `dt_init`.

## Fixed in proteus (cekees/proteus#321, draft)

Suggestions 1, 2, 3, 4 (now a warning), 5, 9, 12, 15, 17 (default scheme/springs/constraints, 3D `coords_system`,
Runge_Kutta refusal for a free roll/pitch) and 21 (now a warning) were reproduced on `b9d98f5` and fixed or warned in
that PR; 14 and 20 are written up for their owners (writePoly patch; PUMI `faceList`), not applied. The decks no longer
need the `RigidBody3D` subclass or the forced scheme/springs in `3d/floating_caisson`, nor the `int()` flag wrapper in
`Submerged_breakwater`, once that PR is in a proteus you use; the integer facets in `3d/bathyduck` (14) and
`reconstructedFlag = 0` in `3d/floating_bar_scorec` (20) stay until their fixes. `sediment_erosion` at `useRANS=1` gets past
the deep copy (12) and then stops in `WallFunctions` (separate defect).

## Suggested proteus changes

### 1. `parun -f <case>.py --TwoPhaseFlow` crashes with `IndexError`

- **Where:** `scripts/parun` (installed as `bin/parun`), in the `elif opts.TwoPhaseFlow:` branch.
- **What happens:** the branch always reads the case from `args[0]`. When the
  case is given only with `-f`, `args` is empty and the run dies at
  `case_name=args[0]` with `IndexError: list index out of range`. Under
  `mpiexec` every rank aborts. The air-water-vv READMEs (and older docs) use the
  `-f` form for parallel runs.
- **Reproduce:**
  ```bash
  mpiexec -n 2 parun -f dambreak.py --TwoPhaseFlow -C "duration=0.05"
  ```
- **Suggested fix:** when `args` is empty, use `opts.fileName`, so both
  `parun case.py --TwoPhaseFlow` and `parun -f case.py --TwoPhaseFlow` work.
  Alternatively, fail with a clear message.
- **Workaround in the decks:** the READMEs now pass the case as a positional
  argument.

### 2. `OutputStepping.setOutputStepping` refers to an undefined name

- **Where:** `proteus/TwoPhaseFlow/TwoPhaseFlowProblem.py`, `OutputStepping.setOutputStepping`.
- **The line:**
  ```python
  assert not (self.dt_output is None and nDTout is None), "Provide dt_output or nDTout"
  ```
  `nDTout` should be `self.nDTout`.
- **Effect:** if `dt_output` is `None`, Python evaluates the undefined name and
  raises `NameError` instead of the intended assertion. That is exactly the case
  that later code (the `dt_output is None` / `dt_fixed` branch of
  `tnList` construction) is written to support, so a case that sets only
  `nDTout` cannot run.
- **Not reached by the ported decks**, which all set `dt_output`.

### 3. The old `TwoPhaseFlowProblem(...)` constructor fails with a bare `TypeError`

- **What happens:** decks written for proteus 1.7/1.8 call
  `TwoPhaseFlowProblem(ns_model=..., ls_model=..., nd=..., cfl=..., outputStepping=...)`
  and `TpFlow.OutputStepping(final_time=..., ...)`, and use
  `myTpFlowProblem.Parameters.Models` / `params.physical.densityA`. Today these
  fail with `TypeError: ... unexpected keyword argument` (or `AttributeError`),
  with no hint of the replacement.
- **Suggestion:** either a short migration section in the docs, or an error that
  names the new API (`SystemPhysics.useDefaultModels`, `outputStepping.*`,
  `SystemPhysics.rho_0/nu_0/...`). The mapping used for the air-water-vv port is
  below, in case it is useful for the docs.

### 4. Gauges attached through SpatialTools are silently ignored

- **Where:** `proteus/TwoPhaseFlow/TwoPhaseFlowProblem.py` and `mprans/SpatialTools.py`.
- **What happens:** `shape.attachPointGauges('twp', ...)` / `('ls', ...)` only
  collects the gauges in `domain.auxiliaryVariables[...]`. Nothing passes them to
  a model unless the deck appends them to `modelDict[...].auxiliaryVariables`
  itself. If it does not, the run succeeds and simply writes no gauge file.
- **Example:** `2d/benchmarks/wavesloshing` defined pressure and level-set gauges
  but never attached them.
- **Suggestion:** when `SystemPhysics.useBoundaryConditionsModule` is on, attach
  `domain.auxiliaryVariables` by key (`'twp'` → flow, `'vof'`, `'ls'` → ncls, ...).
  At minimum, warn when `domain.auxiliaryVariables` holds gauges that no model
  received.

### 5. `final_time < dt_output` silently ends the run at `dt_init`

- **Where:** `OutputStepping.setOutputStepping` and the `tnList` construction in
  `TwoPhaseFlowProblem.py`.
- **What happens:** `nDTout = int(round(final_time/dt_output))` is 0 when
  `final_time < dt_output/2`. `tnList` is then `[0, dt_init]`, and the run stops
  after the first step, at `t = dt_init`. It reports normal completion and gives
  no warning.
- **Example:** this happened with `wavesloshing -C "T=0.02"`, where
  `dt_output` defaults to 0.05.
- **Suggestion:** always end `tnList` at `final_time`, e.g. with
  `nDTout = max(1, ...)` or by appending `final_time`, or warn.

### 6. `SystemPhysics.setDefaults()` puts gravity along −z in 3D; the 1.x default was −y

- **Where:** `proteus/TwoPhaseFlow/TwoPhaseFlowProblem.py`, `SystemPhysics.setDefaults`.
- **What happens:** 3D decks written for 1.x with y vertical (e.g. `3d/STLShape`,
  `3d/STLShape_Zones`, `opts.g = [0, -9.81, 0]`) never set gravity, because the
  old default matched. Ported literally, they run with gravity sideways and no
  error.
- **In the decks:** they now set `physics.gravity = opts.g` explicitly.
- **Suggestion:** a release note for the 2.0 change. Possibly also a warning when
  a SpatialTools BC set-up (e.g. `setAtmosphere(orientation=...)`,
  `vert_axis=1`) disagrees with the gravity direction.

### 7. `WaveTools.MonochromaticWaves`: explicit Fenton coefficients are ignored by default, and the error exits the process

- **Where:** `proteus/WaveTools.py`, `MonochromaticWaves.__init__`.
- **What happens:**
  - `autoFenton=True` is the default, so a deck that passes `Ycoeff`/`Bcoeff`
    has them recomputed. If it does not also pass `Nf`, the run stops with
    `ERROR!!: Number of Fourier modes is not set`, which does not mention
    `autoFenton`.
  - That check calls `sys.exit(1)` rather than raising, so under `mpiexec`
    there is no traceback.
  - The Cython signature now requires numpy arrays for `Ycoeff`/`Bcoeff`;
    lists fail with `TypeError: Cannot convert list to numpy.ndarray`.
- **In the decks:** they now pass `autoFenton=False`, `Nf=len(Bcoeff)` and
  `np.array(...)`.
- **Suggestions:**
  - treat explicit `Ycoeff`/`Bcoeff` as `autoFenton=False`, or say so in the
    error;
  - raise `ValueError` instead of calling `sys.exit`;
  - accept array-likes (`np.asarray`).

### 8. Shapes with list-valued `boundaryOrientations` fail inside `BC_Base`

- **Where:** `proteus/SpatialTools.py` (`CustomShape.__init__`) passing
  `b_or` to `proteus/BoundaryConditions.pyx` (`BC_Base.__init__`).
- **What happens:** `BC_Base` now takes `b_or` as a typed memoryview, so
  `boundaryOrientations={'bottom': [0., -1., 0.], ...}` fails with
  `TypeError: a bytes-like object is required, not 'list'`.
- **Suggestion:** `np.asarray(..., dtype=float)` in `CustomShape` (or in
  `BC_Base`).

### 9. `setPorousZones` / `setGenerationZones` / `setAbsorptionZones` reject a numpy integer flag

- **Where:** `proteus/mprans/SpatialTools.py`.
- **What happens:** they test `isinstance(flags, int)`. A flag taken from
  `shape.regionFlags[...]` is `numpy.int64`, so the code then tries to iterate
  it: `TypeError: 'numpy.int64' object is not iterable`.
- **Suggestion:** test `isinstance(flags, numbers.Integral)` (or
  `np.isscalar`).
- **In the decks:** they wrap the flag in `int()`.

### 10. `py2gmsh` refinement used by several decks is outside the environment and has drifted

- **What happens:** several decks generate graded meshes through `py2gmsh`,
  which is not in the proteus environment files, and whose current API no
  longer matches them (see `BROKEN_CASES.md`).
- **Suggestion:** either add `py2gmsh` to the dev environments and document
  it, or point users at a supported way to build a refined gmsh `.geo` from a
  SpatialTools domain (the `gmsh` Python module is already in the
  environment).

### 11. `VOS3P.Coefficients` defaults are inconsistent: `STABILIZATION_TYPE=0` with `FCT=True`

- **Where:** `proteus/mprans/VOS3P.py`.
- **What happens:** the defaults trip the model's own assertion
  `Use FCT just with STABILIZATION_TYPE>0`. Any deck that leaves both at their
  defaults fails at start-up.
- **Example:** three of the air-water-vv sediment decks.
- **Suggestion:** make the defaults consistent (`FCT=False` when
  `STABILIZATION_TYPE=0`), or default `FCT` from `STABILIZATION_TYPE`.
- **In the decks:** they pass `FCT=False`.

### 12. k-ε models with a sediment closure fail: `HsuSedStress` cannot be deep-copied

- **Where:** `proteus/Transport.py` (`MultilevelTransport.initialize` calls
  `copy.deepcopy(coefficients)`) and `proteus/mprans/SedClosure` (the Cython
  class `HsuSedStress`).
- **What happens:** `Kappa`/`Dissipation` coefficients built with
  `closure=HsuSedStress(...)` fail at model allocation with
  `TypeError: cannot pickle 'proteus.mprans.SedClosure.HsuSedStress' object`.
- **Example:** `2d/sediment/sediment_erosion` at its default `useRANS=1`; it
  runs with `useRANS=0`.
- **Suggestion:** give `HsuSedStress` `__reduce__`/`__deepcopy__` (it is a
  parameter holder), or avoid deep-copying coefficients that hold extension
  objects.

### 13. Wall-function classes dropped `b_or` without a deprecation path

- **Where:** `proteus/mprans/BoundaryConditions.py`, `kWall` and
  `WallFunctions`.
- **What happens:** the constructors no longer accept `b_or=`, so old decks
  fail with `TypeError ... unexpected keyword argument 'b_or'`.
- **Suggestion:** accept and ignore it with a warning for one release, or
  note it in the release notes.

### 14. `PiecewiseLinearComplexDomain.writePoly` writes numpy integers as `np.int32(95)`

- **Where:** `proteus/Domain.py`, `PiecewiseLinearComplexDomain.writePoly`.
- **What happens:** it writes facet vertex indices (and facet-hole numbers)
  with `repr(...)`. Under numpy 2 the repr of a numpy integer is
  `np.int32(95)`, so a `.poly` built from numpy-integer facets (e.g. taken from
  a mesh's arrays) is unreadable. TetGen then writes no `.ele` and proteus fails
  with `could not read a tetgen mesh from X.node and X.ele`.
- **Example:** `3d/bathyduck`.
- **Suggestion:** format with `'%d'`, like the vertex lines already are.
- **In the deck:** the facets are converted to `int` first.

### 15. `WaveTools.TimeSeries` gained `cutoffTotal` before `rec_direct`, shifting positional calls

- **Where:** `proteus/WaveTools.py`, `TimeSeries.__init__`.
- **What happens:** a 1.x call passing `rec_direct, window_params`
  positionally now passes them as `cutoffTotal, rec_direct`. The only symptom
  is `ERROR! ... window_params must be a dictionary` followed by `sys.exit`
  (see suggestion 7).
- **Example:** `3d/bathyduck`.
- **Suggestion:** make the arguments after `g` keyword-only, or move
  `cutoffTotal` to the end.

### 16. `MeshAdaptPUMI.MeshAdaptPUMI` was renamed without an alias

- **Where:** `proteus/MeshAdaptPUMI`.
- **What happens:** `from proteus.MeshAdaptPUMI import MeshAdaptPUMI` (used
  by `3d/floating_bar_scorec`) fails; the module is now
  `proteus.MeshAdaptPUMI.MeshAdapt`.
- **Suggestion:** a compatibility alias or a release note.

### 17. `BodyDynamics.RigidBody` / `CaissonBody`: required set-up without defaults, and 3D rotation bugs

- **Where:** `proteus/mprans/BodyDynamics.py`.
- **No defaults for the scheme or the springs.** A body that never calls
  `setNumericalScheme(...)` and `setSprings(...)` fails at its first step with
  `AttributeError: ... no attribute 'scheme'` (then `'Kx'`), even when springs
  are not wanted. Suggestion: default to `Forward_Euler` and springs off.
- **`getInertia`'s 3D branch reads `self.coords_system`.** `RigidBody` never
  sets that attribute (the shape has it), so any 3D rotation fails with
  `AttributeError`. It looks like the method moved from the shape to the body
  without being updated. Suggestion: use `self.Shape.coords_system`. The
  `3d/floating_caisson` deck works around it with a two-line subclass.
- **`Runge_Kutta` integrates rotation about z only.** That suits 2D, but a 3D
  roll or pitch does not move at all, silently. Suggestion: integrate the full
  vector, or refuse `Runge_Kutta` for 3D rotations. The deck uses
  `Forward_Euler`.
- **`setInertiaTensor`'s docstring is contradictory.** It says the tensor should
  "not be already scaled with the mass", but the body computes the moment as
  `It * mass`, i.e. it expects `It` per unit mass, as in 1.x.
- **A fully constrained body records zero loads.** Forces are recorded as
  `getTotalForces() * free_x`, so a fixed structure's wave loads are not
  recorded. `2d/caissonBreakwater/fixed` keeps the 1.x trick: free DOFs, very
  large density, and a mesh that does not move. A "record unconstrained loads"
  option would be cleaner.

### 18. `Kappa` (k-ε) requires gravity as a numpy array

- **Where:** `proteus/mprans/Kappa.py`, `getResidual`.
- **What happens:** with `g` given as a list, it fails with
  `argsDict["g"] = self.coefficients.g  TypeError: must be real number, not list`.
  The flow models accept the list, so a deck works until `useRANS` is switched
  on.
- **Suggestion:** `np.asarray(g, dtype=float)` in the coefficients.

### 19. `MeshOptions.elementSize` was renamed `setElementSize` without an alias

- **Where:** `proteus/Domain.py`, `MeshOptions`.
- **What happens:** old decks call `domain.MeshOptions.elementSize(he)` and get
  an `AttributeError`.
- **Suggestion:** an alias.

### 20. PUMI: a deck's `faceList` is silently ignored by default

- **Where:** `proteus/MeshAdaptPUMI` (`AdaptManager.reconstructedFlag`) and
  `MeshTools.convertFromPUMI`.
- **What happens:**
  - `AdaptManager.reconstructedFlag` defaults to 2 (a "reconstructed model").
    In that mode `convertFromPUMI` never applies `domain.faceList`, so the
    boundary flags are raw model-face IDs.
  - The `faceList` path also needs `domain.boundaryLabels`, which nothing
    documents for split-file decks.
  - Old decks therefore fail far from the cause, in `3d/floating_bar_scorec`
    with flags above 7 in the bar's force bookkeeping.
- **Suggestion:** use `faceList` when it is given (or warn), and default
  `boundaryLabels` to `1..len(faceList)`.
- **In the deck:** `reconstructedFlag = 0` and `boundaryLabels` are set.

### 21. `RANS2P.Coefficients(epsFact_solid=...)` silently changed meaning

- **Where:** `proteus/mprans/RANS2P.py`, `Coefficients`.
- **What happens:**
  - In 1.x, `epsFact_solid` was the smoothing width of the porous/relaxation
    zones. In 2.0 that is `epsFact_porous`, and `epsFact_solid` is the
    immersed-solid smoothing.
  - An old `_p` file that passes `epsFact_solid=epsFact_solidTypes` still
    runs, but its relaxation zones get the default smoothing (ones). The
    smoothing it asked for goes to an unused immersed-solid parameter, with no
    warning.
- **Found in:** `3d/linear_waves_flat_3D`, `3d/Penny_Price_Diffraction`,
  `3d/Directional_Wave_Current_interaction` and
  `2d/hydraulicStructures/sharp_crested_weir/deprecated/sharp_crested_weir_AV_V1`.
  `linear_waves_flat_3D` "ran" in the earlier smoke test with its wave
  generation zone mis-smoothed. All four now pass `epsFact_porous=`.
- **Suggestion:** warn when `epsFact_solid` is given and no immersed-solid
  model is active, or give the immersed-solid parameter a name that cannot
  collide with 1.x decks.

### 22. VOF with `shockCapturingFactor=0.5` stalls where 1.x ran (behaviour difference, not necessarily a bug)

- **Where:** `deprecated/sharp_crested_weir_VM_V1`, which used 0.5 for the
  level set, VOF and redistancing models.
- **What happens:** the VOF Newton solve stalls (residual about 5e-4, 50
  iterations) at the first step. Every retry fails, and the run ends with exit
  status 1 without taking a step. 0.25, as in the otherwise identical
  `VM_V2`, `V1` and the maintained deck, runs normally.
- **Status:** seen only on a coarsened copy (Refinement 60 instead of 185), so
  it may depend on resolution. The deck now uses 0.25.
- **For proteus:** possibly worth a look as a change in VOF shock-capturing
  or its default solver settings since 1.x. **Update:** at Refinement 185 the failing model is MCorr, not VOF, and it fails the same way
  for `VM_V2` (0.25 already); the decks need the PETSc options file (`-O`), see the status table.

## Migration recipe used for the decks (old API → proteus 2.0)

| Old (1.x `TwoPhaseFlowProblem`) | New |
|---|---|
| `TpFlow.OutputStepping(final_time=T, dt_init=..., dt_output=...)` passed to the constructor | `myTpFlowProblem.outputStepping.final_time = T` (and likewise `dt_init`, `dt_output`) |
| `TwoPhaseFlowProblem(ns_model=None, ls_model=None, ...)` (defaults: RANS2P + VOF/NCLS/RDLS/MCorr) | `TwoPhaseFlowProblem()`; `.domain = domain`; `SystemPhysics.setDefaults()`; `SystemPhysics.useDefaultModels(flowModel=0, interfaceModel=0)` |
| `ns_model=1` (RANS3PF), `ls_model=1` (CLSVOF) | `useDefaultModels(flowModel=1, interfaceModel=1)` |
| `cfl=` | `SystemNumerics.cfl` |
| single-phase RANS with `m.rans2p`, `m.kappa`, `m.dissipation` indexed and `params.physical.useRANS = n` | `physics.useRANS = n`; `addModel(ParametersModelRANS2P, 'flow')`, `addModel(ParametersModelKappa, 'kappa')`, `addModel(ParametersModelDissipation, 'dissipation')`; ICs `kappa`, `epsilon` |
| no gravity set (1.x default −y) | 3D: set `physics.gravity` explicitly (see suggestion 6) |
| `myTpFlowProblem.useSuperLu` | `SystemNumerics.useSuperlu` |
| `params.physical.densityA/B`, `kinematicViscosityA/B`, `surf_tension_coeff`, `gravity` | `SystemPhysics.rho_0/rho_1`, `nu_0/nu_1`, `surf_tension_coeff`, `gravity` |
| `params.Models.rans2p` / `.vof` / `.ncls` / `.rdls` / `.mcorr` | `SystemPhysics.modelDict['flow' / 'vof' / 'ncls' / 'rdls' / 'mcorr']`; the order and indices come from `useDefaultModels`, so the explicit `.index = n` lines are dropped |
| `initialConditions={'pressure', 'vel_u', 'vel_v', 'vel_w', 'vof', 'ncls', 'rdls'}` | `m['flow'].p.initialConditions['p' / 'u' / 'v' / 'w']`, `m['vof']...['vof']`, `m['ncls']...['phi']`, `m['rdls']...['phid']`, `m['mcorr']...['phiCorr']` (new; set to zero) |
| `boundaryConditions=None` with SpatialTools | unchanged: BCs come from `domain.bc` (`SystemPhysics.useBoundaryConditionsModule`, default `True`) |
| `params.Models.rans2p.auxiliaryVariables += ...` | `m['flow'].auxiliaryVariables += ...` |
| `m.rdls.p.coefficients.epsFact = ...` | `m['rdls'].p.coefficients.epsFact = ...` |
| `m.moveMeshElastic.index = 0` (moving mesh) | `SystemPhysics.movingDomain = True`; `addModel(Parameters.ParametersModelMoveMeshElastic, 'moveMeshElastic')` **before** `useDefaultModels`, so it is model 0; initial conditions `hx`, `hy` (and `hz`) set to zero |
| `params.mesh.genMesh`, `params.mesh.he` | `domain.MeshOptions.genMesh`, `domain.MeshOptions.he` |
| `setGenerationZones(flags, epsFact_solid=..., ...)` / `setAbsorptionZones(...)` on a shape | `epsFact_porous=...` (renamed keyword) |
| gauges from `attachPointGauges('twp' / 'ls', ...)` | append `domain.auxiliaryVariables['twp']` to `m['flow'].auxiliaryVariables` and `['ls']` to `m['ncls'].auxiliaryVariables` (see suggestion 4) |

### Older split-file cases (`*_so.py` with `_p`/`_n` modules)

| Old | New |
|---|---|
| Python 2 syntax (`print x`, `raise E, msg`, `except E, e`, `` `x` ``, `xrange`, `dict.has_key`, mixed tabs and spaces) | converted with the standard 2to3 fixers (via `fissix`); leading tabs expanded at 8 columns, which keeps Python 2's indentation meaning |
| `domain.epsFact_solid` (porous/relaxation-zone smoothing), and `RANS2P.Coefficients(epsFact_solid=...)` | `domain.epsFact_porous` and `RANS2P.Coefficients(epsFact_porous=...)`. `RANS2P`'s `epsFact_solid` is now a different, immersed-solid parameter, and passing the old keyword is silently accepted (suggestion 21) |
| `MonochromaticWaves(..., waveType='Fenton', Ycoeff=..., Bcoeff=...)` | add `autoFenton=False, Nf=len(Bcoeff)`, with `np.array(...)` for the coefficients |
| `from proteus.mbd import ChRigidBody as crb`; `crb.ProtChSystem(g)`; `pyChronoCore.ChVector` / `ChQuaternion` | `from proteus.mbd import CouplingFSI as crb`; `import pychrono`; `crb.ProtChSystem()` then `system.ChSystem.SetGravitationalAcceleration(pychrono.ChVector3d(...))`; `pychrono.ChVector3d` / `ChQuaterniond` |
| ragged `tank.facets = np.array([...])` | `np.array([...], dtype=object)` (numpy 2 no longer builds ragged arrays implicitly) |
| `setPorousZones(flags=shape.regionFlags[i], ...)` | `flags=int(shape.regionFlags[i])` (see suggestion 9) |
| `from proteus.mprans import RDLS3P` (removed) | `RDLS` (same names: `Coefficients`, `LevelModel`, `SubgridError`, `ShockCapturing`, `PsiTC`, `setZeroLSweakDirichletBCsSimple`), as in proteus's own copy, `test/RANS3PSed/bed_sediment` |
| `VOS3P.Coefficients(...)` with default stabilization | add `FCT=False` (see suggestion 11) |
| `bc.kWall(..., b_or=...)`, `bc.WallFunctions(..., b_or=...)` | drop `b_or` |
| `for a, b in zip(lst, ...): lst.append(...)` (Python 2 `zip` returned a list) | `list(zip(...))`. Python 3's lazy `zip` sees the appended items and loops until memory runs out, as in `3d/dambreak_Ubbink/*`; every `for ... in zip(...)` in the split-file decks is wrapped |
| hand-written relaxation zones writing `coefficients.q_phi_solid` / `q_velocity_solid` and `q['phi_solid']` | `q_phi_porous` / `q_velocity_porous` and `q['phi_porous']` / `q['velocity_porous']`. In 2.0 the `*_solid` fields are for immersed solids |
| `np.genfromtxt(..., skiprows=n)` | `skip_header=n` |
| `TimeSeries(file, skiprows, pos, depth, N, mwl, waveDir, g, rec_direct, window_params)` | pass `rec_direct=` and `window_params=` by keyword (see suggestion 15); `timeSeriesPosition` as `np.array` |
| `shape.setRigidBody()`, `setMass`, `setConstraints`, `setRecordValues`, `setFriction` on a SpatialTools shape | `body = bd.RigidBody(shape=...)` (or `bd.CaissonBody`) and the same methods on the body, plus `setNumericalScheme` and `setSprings` (see suggestion 17). In 3D, use `Forward_Euler` for rotations; moving-mesh BCs are `setFixedNodes()` on the tank and `setRigidBodyMoveMesh(body)` on the shape (`3d/floating_caisson`) |
| old `Tank3D`: `setSponge(front=, back=, left=, right=)`, `BC.front`/`.back`/`.left`/`.right`/`.bottom`/`.top` | `setSponge(x_n=, x_p=, y_n=, y_p=)`; `BC['x-']`/`['x+']`/`['y-']`/`['y+']`/`['z-']`/`['z+']` (front = x−, back = x+, left = y−, right = y+) |
| `BC.<name>.setOpenAir()` | `BC['<name>'].setAtmosphere()` |
| `setUnsteadyTwoPhaseVelocityInlet(..., windSpeed=...)`, `setGenerationZones(..., windSpeed=...)` | drop `windSpeed`; pass `smoothing=` (and `dragAlpha=` for zones) |
| PyODE rigid body (`import ode`; `ode.World`, `ode.Body`, `ode.Mass.setBox`, `body.setForce`/`setTorque`, `world.step`, `body.getRelPointPos`) | `pychrono`: `ChSystemNSC` with gravity, `ChBodyEasyBox(lx, ly, lz, density, False, False, ChContactMaterialNSC())`, `AddAccumulator` / `EmptyAccumulator` / `AccumulateForce(i, F, body.GetPos(), False)` / `AccumulateTorque(i, M, False)`, `DoStepDynamics(dt)`, `TransformPointLocalToParent` (`3d/floating_bar`) |
| `from proteus.MeshAdaptPUMI import MeshAdaptPUMI`; `domain.PUMIMesh = MeshAdaptPUMI.MeshAdaptPUMI(hmax=, hmin=, numIter=, sfConfig=)`; `loadModelAndMesh("x.dmg", "x.smb")` | `Domain.PUMIDomain(dim=3, manager=MeshAdapt.AdaptManager())`; `domain.AdaptManager.PUMIAdapter.loadModelAndMesh(b"x.dmg", b"x.smb")`; `modelDict`, `sizeInputs`, `adapt`, `hmax`, `hmin`, `hphi`, `numIterations` on `AdaptManager`, then `setAdaptProperties`; `reconstructedFlag = 0` and `boundaryLabels` to keep `faceList` (suggestion 20); `conservativeFlux = None` and matching `domain.MeshOptions` partitioning (element) |
| `domain.MeshOptions.elementSize(he)` | `setElementSize(he)` |
| old-style `_p` files: `lambda x, flag: domain.bc[flag].u_dirichlet` | `domain.bc[flag].u_dirichlet.init_cython()` (likewise `_advective`, `_diffusive`, `_stress`) |
| `useSuperlu = True` (LU) in a deck run on several ranks | proteus now refuses LU in parallel: `useSuperlu = Comm.get().size() == 1` |

## Deck issues noticed but left unchanged

These are about the physics or set-up of a case, not about running it, so they
are left for whoever validates the results:

- `2d/benchmarks/dambreak_with_obstacle`: the default pressure gauge
  `gauge_location_p = (3.219999, 0.12, 0)` was copied from `dambreak`. It lies
  outside this 0.584 m tank. Proteus now warns
  (`gauge location ... is not on any local element; using the value at its nearest node`)
  and records the nearest node, so the gauge output is not a meaningful
  measurement.
- `2d/benchmarks/dambreak` and `dambreak_with_obstacle`: `P_IC` sets a constant
  pressure everywhere in the air, rather than a hydrostatic one. This is harmless
  for running, since the first solve corrects it.
- `2d/benchmarks/wavesloshing`: the `structured=True` / `useHex=True` options
  already failed before the port (they use an undefined `refinement`), and the
  old `params.mesh.nnx/nny` settings for them have no direct counterpart. They are
  left unsupported; the default unstructured mesh is used.
- `2d/hydraulicStructures/broad_crested_weir`: the original was not valid Python
  (an unclosed `setHydrostaticPressureOutletWithDepth(` call), and it assembled
  the domain twice. Both are fixed. The old deck also put `moveMeshElastic` in the
  model list, although nothing in the case moves, so it was a no-op; it is left
  out. Its gauges sit inside a string literal, so they are disabled, as before.
- `2d/waveOvertopping/Overtopping`: the vertical probe loop used
  `np.linspace(crest, height, num=opts.dx)` with `dx=0.01`. Old numpy truncated
  `num` to 0, so no probe was ever added; numpy 2 raises `TypeError`. The loop
  would also append single points to a list of line-gauge end points. It is
  commented out, keeping the old behaviour; whoever validates the case should
  decide which probes were intended.
- `3d/STLShape_Zones`: the original was not valid Python (an unclosed
  `np.array(` in `SG.regions`); fixed.

## Regression scripts in `Tests/`

All 13 files in `Tests/1st_set` and `Tests/2nd_set` pass with proteus `b9d98f5`
(serial, each in its own `pytest` process). The only change needed was dropping
an unused `import tables` (PyTables is not in the proteus environment).

These tests are weak: each runs about 0.01 s of simulated time and checks only
that the log contains no `Step Failed`. Several of them would also pass for a
run that stops at `dt_init`, which happens when `final_time` is less than half
of `dt_output` (suggestion 5). `test_standingWaves` passes `refinement=2`, an
option `standing_waves.py` does not define (it has `refinement_level`), and the
run does not complain.

## Status of the cases

| Case | Status | Smoke runs (proteus `b9d98f5`) |
|---|---|---|
| `2d/benchmarks/dambreak` | ported | serial to t=0.1 at `he=0.05`; `-n 2` to t=0.05 at the default `he=0.02` (≈46k triangles) |
| `2d/benchmarks/dambreak_with_obstacle` | ported | serial and `-n 2` to t=0.05 at the default `he=0.015` (≈4.7k triangles) |
| `2d/benchmarks/wavesloshing` | ported; gauges now attached | serial to t=0.1 at `he=0.004` (also with `movingDomain=True`); `-n 2` to t=0.1 at the default `he=0.001` (≈32k triangles) |
| `2d/numericalTanks/regularWaves` | ported | serial to t=0.2 with `refinement_level=25`; `-n 2` to t=0.2 at the default (≈18k triangles) |
| `2d/numericalTanks/standingWaves` | ported | serial to t=0.2 with `refinement_level=25`; `-n 2` to t=0.2 at the default (≈75k triangles, ~70 s for 0.2 s) |
| `2d/numericalTanks/randomWaves` | ported | serial to t=0.2 with `fract=1764 refinement_level=25`; `-n 2` at the default (≈14k triangles) |
| `2d/hydraulicStructures/broad_crested_weir` | ported; syntax error fixed | serial to t=0.2 with `refinement=50`; `-n 2` to t=0.2 at the default (≈14k triangles) |
| `2d/waveOvertopping/Overtopping` | ported | serial to t≈0.4 with `refinement_level=40`; `-n 2` with `refinement_level=100` (≈19k triangles; the default 200 gives ≈80k) |
| `2d/waveOvertopping/new_wave_overtopping` | ported; README `-f` usage fixed | serial to t=0.2 with `refinement_level=40`; `-n 2` with `refinement_level=100` (≈32k triangles; the default 200 gives ≈125k) |
| `2d/benchmarks/flatPlate_wallFunctions` | ported (single-phase RANS2P + k-ε) | serial and `-n 2` to t=0.1 at the default (≈5.7k triangles; slow, ~45 s per 0.1 s) |
| `2d/floatingStructures/floating_caisson_BodyDynamics` | ported (MoveMeshElastic + CaissonBody) | serial and `-n 2` to t=0.1 at the default (≈9.7k triangles); the body rotates and the mesh moves |
| `2d/oscillating_cylinder` | ported (MoveMeshElastic) | serial and `-n 2` to t=0.1 at the default (≈21k triangles) |
| `3d/STLShape` | ported; gravity set explicitly | serial and `-n 2` to the default `T=0.1` (≈24k tetrahedra) |
| `3d/STLShape_Zones` | ported; syntax error fixed; `epsFact_porous`; gravity set explicitly | serial (~2.5 min) and `-n 2` to the default `T=0.1` (≈57k tetrahedra) |
| `2d/caissonBreakwater/sliding` | ported | serial to t≈1.95 and `-n 2` to t≈1.87 of `duration=2` within the time limit (≈12.5k triangles) |
| `2d/caissonBreakwater/fixed` | rewritten on `proteus.mprans.SpatialTools` + `BodyDynamics.CaissonBody` (the bundled `SpatialTools.py` fork is removed); model files from `../sliding`; fixed caisson whose loads are recorded in `caisson2D.csv` | serial to t≈0.57 and `-n 2` to t≈0.61 within the time limit, with `refinement_level=25` (≈45k triangles; the default 200 gives ≈1.5M) |
| `2d/floatingStructures/floating_caisson_chrono` | ported (CouplingFSI + pychrono); gmsh refinement path broken | serial and `-n 2` complete the default `T=1` with `refinement=False use_gmsh=False` (≈12k triangles) |
| `2d/hydraulicStructures/crump_weir` | runs after the Python 3 conversion | serial to t≈23 and `-n 2` to t≈17 within the time limit (≈2.2k triangles) |
| `2d/hydraulicStructures/sharp_crested_weir` | runs after the Python 3 conversion and an unterminated-string fix | serial at the default `refinement=40` (≈64k triangles; reached only t=0.003 in 2 min); `-n 2` with `refinement=15` to t=0.5 |
| `2d/hydraulicStructures/sluice_gate` | runs after the Python 3 conversion | serial and `-n 2` complete (≈630 triangles) |
| `2d/rubbleMoundBreakWater/Submerged_breakwater` | ported; gmsh path broken | serial to t≈1.65 and `-n 2` to t≈1.47 with `use_gmsh=False` (≈21k triangles) |
| `2d/waveTransformation/Dingemans_wave_shoaling` | ported; gmsh path broken | serial to t≈4.8 and `-n 2` to t≈4.0 with `use_gmsh=False he=0.2` (≈15k triangles; the default `he` with Triangle gives ≈384k) |
| `2d/sediment/bed_sediment` | runs after `RDLS3P` → `RDLS` | serial and `-n 2` complete `refinement=10 duration=0.02` (≈640 triangles; the default refinement 25 gives ≈4k) |
| `2d/sediment/strip_sediment` | as `bed_sediment` | same |
| `2d/sediment/friction_angle_dambrek_sediment` | `RDLS`; `FCT=False`; LU only in serial | serial and `-n 2` complete `refinement=10 duration=0.02` |
| `2d/sediment/group_sediment` | `RDLS`; `FCT=False` | serial and `-n 2` complete `refinement=10 duration=0.02` (77 triangles) |
| `2d/sediment/pipe_scour` | `RDLS`; `FCT=False` | serial and `-n 2` complete `refinement=10 duration=0.02` (≈2.2k triangles; this deck's default refinement is 4) |
| `2d/sediment/sediment_erosion` | `RDLS`; wall functions without `b_or`; **default `useRANS=1` blocked by proteus** (suggestion 12) | serial and `-n 2` complete `refinement=10 duration=0.02 useRANS=0` (≈3k triangles) |
| `3d/dambreak` | runs after the Python 3 conversion | serial to t≈0.07 and `-n 2` to t≈0.095 within the time limit (≈23k tetrahedra) |
| `3d/dambreak_Gomez` | runs after the Python 3 conversion | serial to t≈0.085 and `-n 2` to t≈0.14 (≈57k tetrahedra) |
| `3d/dambreak_Ubbink/dambreak_Ubbink_coarse` | `list(zip(...))`; added the missing `vof_p.py`/`vof_n.py` (copied from `medium`) | serial to t≈0.06 and `-n 2` to t≈0.086 (≈24k tetrahedra) |
| `3d/dambreak_Ubbink/dambreak_Ubbink_medium`, `_fine` | same deck at higher resolution; set-up runs | ceds-model, 16 and 32 ranks: medium (98k tets) reaches t=0.326 of 0.8 in 2,385 s, then dt collapses (RANS2P Newton diverges) and the run exits 1 with the default PETSc options; fine (1.59M tets) steps to t≈0.07 (114 GB, ~35 s/step; with `petsc.options.superlu_dist` 189 GB, ~75 s/step), an estimated 7-16 h to finish |
| `3d/linear_waves_flat_3D/linear_waves_flat_3D_01_GAZ` | relaxation-zone fields renamed to `*_porous`; `epsFact_porous=` keyword (suggestion 21) | serial to t≈1.9 and `-n 2` to t≈2.7 (≈62k tetrahedra) |
| `3d/Penny_Price_Diffraction/Penny_Price_Diffraction_01` | same relaxation-zone rename; set-up and meshing run | ceds-model, 32 ranks: **completes** to t=38.8 (935k tets, 417 steps, none failed, 5,237 s, 64 GB) |
| `3d/Directional_Wave_Current_interaction/45DEG_R1` | same relaxation-zone rename; set-up runs | HPC-sized: 49.1M tets / 8.2M nodes, TetGen 33 min, ~3.4 TB of RAM at the measured memory per tet. A scratch copy at `he=wavelength/25` (772k tets, 32 ranks, 53 GB) runs to t=8.4 of 77.6 with step retries |
| `3d/bathyduck` | `skip_header`; `TimeSeries` keywords; integer facets | HPC-sized: 6.9M tets (TetGen 4 min), >342 GB at the first model allocation on 48 ranks; at 32+ ranks the geometry block at import races on the Triangle files (`no 1.ele`): ranks > 0 need a private directory |
| `3d/marin` | runs after the Python 3 conversion | ceds-model, 32 ranks: 2.17M tets, 136 GB, t=4.30 of 6.0 in 4 h (1,501 steps, none failed); ~5.3 h in all |
| `3d/floating_caisson` | body on `BodyDynamics.RigidBody` (`Forward_Euler`; `coords_system` shim, suggestion 17); `Tank3D` and BC names updated; `.init_cython()` in the `_p` files | serial completes `T=0.3` (≈53k tetrahedra); the 15° roll decays (0.262 → 0.183 rad by t≈0.29); `-n 2` completes `T=0.1` |
| `3d/floating_bar` | PyODE replaced by `pychrono` in the deck's `RigidBar` | serial completes `T=0.2` (≈10.5k tetrahedra); the half-density bar rises (z 0.400 → 0.421); `-n 2` completes `T=0.1` |
| `3d/floating_bar_scorec` | as `floating_bar`, plus the PUMI `AdaptManager` interface | serial completes `T=0.1` with mesh adaptation (4.7k → 12.5k tetrahedra); `-n 2` completes with a split mesh made outside the repository (see `BROKEN_CASES.md`) and matches serial |
| `2d/hydraulicStructures/sharp_crested_weir/deprecated/sharp_crested_weir_V1` | Python 3 conversion only | serial to t=0.005 within 2 min at its hard-coded Refinement 75 (≈68k triangles); `-n 2` to t≈0.07 |
| `.../deprecated/sharp_crested_weir_VM_V1` | Python 3 conversion; level-set, VOF and redistancing shock capturing 0.5 → 0.25 (suggestion 22) | Refinement 185 (≈208k triangles) on ceds-model: with the default PETSc options **no step** at 1 and 8 ranks (the MCorr solve, `ls_consrv`, stagnates at 1000 KSP iterations against atol 1e-10); with the PETSc options file the decks' PBS scripts use (`-O inputTemplates/petsc.options.superlu_dist`) it runs, 8 ranks, 15 s/step, t=0.28 of 10 in 40 min (a copy at Refinement 60 runs to t≈0.32 without it) |
| `.../deprecated/sharp_crested_weir_VM_V2` | Python 3 conversion only | as `VM_V1` (t=0.26 with the options file in 40 min) |
| `.../deprecated/sharp_crested_weir_AV_V1` | Python 3 conversion; relaxation-zone fields and keyword renamed to `*_porous` (suggestion 21) | serial to t≈0.06 and `-n 2` to t≈0.12 within the time limit (≈56k triangles) |
