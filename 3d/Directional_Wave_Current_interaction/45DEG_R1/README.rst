45DEG_R1: waves at 45 degrees to a current
==========================================

Status on proteus 2.0 (2026-11-27): shelved
-------------------------------------------

**This deck does not run to its end time at the resolution it is set up for (he = wavelength/100), and the
cause is not known.** Every run at that resolution lost its time step. The case is shelved: no further jobs
until someone decides how to proceed. The deck is kept as ported (``bacd9f5``, ``8bceb42``, ``305193d``); the
front-face flux fix below delays the collapse but does not remove it.

What was measured (proteus ``main``-line builds, he = wavelength/100 = 59 mm, 49 million tetrahedra, T = 19.4 s of 77.6 s):

* Carpenter D1 (3,072 ranks), deck as ported, no flux fix: 986 accepted and 512 rejected steps (34 % of the attempts);
  median dt 19.5, 14.7, 8.0, 4.6, 2.5 ms in t = 0-1, 1-2, 2-3, 3-3.88, 3.88-5 s; killed by its wall time at t = 6.08 s.
* Carpenter D1a (3,072 ranks), ``305193d``, T = 3.88 s: 0 of 152 attempts rejected; dt 30 ms for t < 2.4 s, falling to
  13.1 ms at 3.88 s; air max |u| 0.50 / 0.99 / 1.86 m/s at t = 0 / 1.94 / 3.88 s (D1: 0.5 / 1.96 / 3.79 m/s).
* Mike 955338 (1,008 ranks), ``305193d``, to T = 19.4 s: cancelled at t = 5.37 s, 552 of 1,106 attempts failed, the last
  20 dt 0.9-4.1 ms.
* Mike 956064 (1,008 ranks), ``305193d`` plus a cure patch (relaxation zones 1 and 5 off, no VOF Dirichlet condition on
  the front face; the patches are not committed): cancelled at t = 3.47 s, 38 of 187 attempts failed (20 %), 22 of the
  last 54 since t = 2.9 s; dt median 16 ms, the last steps 5-10 ms.

At coarser resolution (8 to 32 ranks on one node) the front-face flux fix removes the collapse at he = wavelength/25
(87 steps accepted, 0 rejected, dt 87-91 ms to t = 7.76 s; without the fix 96 / 7, dt 37 ms after t = 7.67 s) but not at
he = wavelength/40 (dt falls from 37 ms to 9 ms from t = 4.5 s, 94 of 323 attempts rejected, 93 of them in the
redistancing solve). The onset of the collapse comes earlier as the mesh is refined. Cure variants tested at
wavelength/40 (relaxation zones 1 and 5 off together with no front-face VOF Dirichlet: no collapse to t = 5.8 s,
dt 37 ms) did not hold at wavelength/100 (Mike 956064 above). Tested at wavelength/25 or /40 with no effect on the
collapse: a smaller ``runCFL`` (0.45: earlier collapse), no turbulence closure (worse), shock capturing off, the
current's v added to the left face (6-20 % lower corner maximum only), front wall free-slip above the interface with the
relaxation limited to the water (worse: spikes at the wall).

What the data show: an air-side velocity jet at the ``front`` (y = 0) wall just above the interface (1.0-1.9 m/s
against 0.5 m/s of current), growing with time, with the water below it at 1.1-1.2 m/s. ``305193d`` corrects one
cause: ``getAFBC_p`` on the front face returned ``-currentVelocity`` (-0.5 m/s) while the imposed velocity there is
``v_current`` (0.354 m/s in the water, 0 in the air); the continuity and momentum data disagreed.

What is not known:

* whether this case ever ran to its end time on any proteus version;
* the cause of the remaining jet: not shown to be deck data (boundary and relaxation-zone setup) or a proteus kernel;
* behaviour at wavelength/50 (does not fit in memory on the one node used for the coarser tests) and for a coarser
  production mesh beyond wavelength/25 (nothing longer than T = 7.76 s was run there);
* whether the top face (p = 0, natural velocity) next to the front-wall Dirichlet velocity contributes: the one test
  of a closed-velocity top lid failed at the impulsive start (step failure at t = 0.0148 s) and was not iterated.

Raw numbers and step traces: ``AWVV_CARPENTER_PRODUCTION_PLAN_2026-11-22.md`` section 7.8 and the C48 handoffs of
2026-11-24 in the proteus work directory (not in this repository).

Running it anyway (proteus 2.0)
-------------------------------

The mesh has 49 million tetrahedra and needs about 65-70 KB per tetrahedron over all ranks (3.3 TB): HPC only
(Mike: 24 nodes x 42 ranks). ``T`` and ``dt_fixed`` are constants in ``tank3D.py`` (``T = 40.0*period``,
``dt_fixed = T``: one output time; ``-C`` options are not defined by this deck), not context options.

1. Generate the mesh once, serially, and keep it: ``pro msh tank3D_so.py`` (or one ``parun`` run with ``genMesh=True`` in
   ``tank3D.py``). The deck then has to find the stored mesh: set ``genMesh=False`` (``triangleOptions`` is
   defined at module level, so ``-F`` works without extra patches).
2. Production run on the stored mesh, every rank reading its share::

      mpiexec -n <ranks> parun -F tank3D_so.py -l 3 -v -D out --archive-driver mpio --wall-limit scheduler

   ``--archive-driver mpio`` is required at this size (the serial driver gathers the state on rank 0 and failed
   above 2 GiB on Intel MPI before ``cekees/proteus#356``). ``--wall-limit scheduler`` stops at a step boundary with
   room for a checkpoint before the SLURM or PBS job ends and exits with status 75; continue with the same command
   plus ``-H``.
3. The same through the ``pro`` command (``pro`` runs this deck since ``cekees/proteus#344``: ``pnList`` assigned
   in an ``if``/``else`` is recognised, and rank 0's rewrite of ``mesh.poly`` is ordered by a barrier in the
   deck)::

      pro msh tank3D_so.py
      mpiexec -n <ranks> pro run -F --no-mesh tank3D_so.py -l 3 -D out --archive-driver mpio --wall-limit scheduler

   On Carpenter ``pro run -F --no-mesh`` after ``pro msh`` gave histories and an h5 file the same size and dataset
   count as ``parun -F`` at 3,072 ranks (before ``#344`` was merged); the merged commit was not re-run at that scale.
4. Output: ``tank3D_so.py`` sets ``archiveFlag = ArchiveFlags.EVERY_SEQUENCE_STEP``, a frame at every accepted step
   (80 frames, 326 GB in an earlier Mike run; on builds before the static-mesh change every frame also rewrote the
   mesh). ``ArchiveFlags.EVERY_USER_STEP`` (the proteus default) writes one frame per ``dt_fixed``; the committed
   ``dt_fixed = T`` gives a single output time, so set ``dt_fixed`` to the period (1.94 s) for field
   output once per period.
