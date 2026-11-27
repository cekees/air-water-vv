bathyduck: waves over the Duck (FRF) bathymetry
===============================================

Status on proteus 2.0 (2026-11-27): runs to T = 70 s on HPC
-----------------------------------------------------------

* Carpenter B1 (576 ranks, 3 nodes, ``parun -F`` on a stored mesh): completed T = 70 s, 9,340 steps, 72 frames, about
  45 GB (before the static-mesh change, which writes the mesh once), about 0.74 core-hours per step.
* Mike 954679 (144 ranks, 4 nodes x 36, ``--archive-driver mpio``, ``--wall-limit scheduler``, 5b671b38 build):
  running when this was written, 0 failed steps; t = 48.5 s of 70 s after 29 h at dt 7.8 ms (about 1.7 simulated
  seconds per wall hour). The comparison of the Mike and Carpenter results is not done yet.

The mesh has 6.9 million tetrahedra and needs about 65-70 KB per tetrahedron over all ranks (about 0.45 TB): a
multi-node job (a 48-rank probe, 7.8 GB per rank, ran four steps).

Running (proteus 2.0)
---------------------

``T`` and ``dt_fixed`` are constants in ``tank3D.py`` (``T = 70.``, ``dt_fixed = 1.``), not context options; edit them
for a shorter test (the ``-C`` options of this deck are the wave parameters only).

1. Generate the mesh once, serially, and keep it (``genMesh = True`` in ``tank3D.py``): ``pro msh tank3D_so.py``, or one
   ``parun tank3D_so.py`` run. Then set ``genMesh = False``: ``triangleOptions`` is a module-level line and ``zTop``
   is read from the stored ``frfDomain3D.poly``, so ``-F`` needs no other patch.
2. Production run on the stored mesh, every rank reading its share (as on Mike)::

      mpiexec -n <ranks> parun -F tank3D_so.py -l 3 -v -D out --archive-driver mpio --wall-limit scheduler

   ``--archive-driver mpio`` is the driver for long runs (the serial driver gathers the 19.5 GB solver state on
   rank 0 and failed above 2 GiB on Intel MPI before ``cekees/proteus#356``). ``--wall-limit scheduler`` stops at a
   step boundary with room for a checkpoint before the SLURM or PBS job ends and exits with status 75; continue with
   the same command plus ``-H``.
3. The same through ``pro`` (``pro`` runs this deck since ``cekees/proteus#344``)::

      pro msh tank3D_so.py
      mpiexec -n <ranks> pro run -F --no-mesh tank3D_so.py -l 3 -D out --archive-driver mpio --wall-limit scheduler

   On Carpenter ``pro run -F --no-mesh`` after ``pro msh`` matched ``parun -F`` (histories and h5 size and dataset
   count) at 576 ranks, before ``#344`` was merged; the merged commit was not re-run at that scale.
4. Output: ``tank3D_so.py`` sets ``archiveFlag = ArchiveFlags.EVERY_SEQUENCE_STEP``, a frame at every accepted step
   (858 frames, 305 GB in an earlier Mike run). ``ArchiveFlags.EVERY_USER_STEP`` (the proteus default) writes one
   frame per ``dt_fixed``: 71 frames of 0.126 GB plus the mesh once (0.207 GB) plus the 19.5 GB solver state, about
   29 GB in all.
