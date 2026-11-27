Sharp crested weir
==================

Description
----------

A rectangular sharp-crested weir is a hydraulic structure mainly used
as a flow control and measurement device in open-channels. It is a
channel obstruction made from a thin plate with a sharp edge at the
top (crest), spanned across the width of the channel. This artificial
barrier obstructs the natural flow of the water, leading to an
increase in the water level upstream, before spilling over the
structure.  The computational domain is a 2D rectangular box with
height equal to 1.8m and the length might vary from case to case. The
weir has a height of P=1.0m and a small width of
b=0.01 m.  A uniform velocity distribution from bottom
to the free water level is imposed in the left wall boundary
condition. The top of the domain is left open and the right wall
allows the flow to leave the domain. A ventilation patch is also introduced at the downstream face of the weir
In the following figure, a simple sketch of the structure is presented showing the main
parameters.

.. figure:: ./SharpWeir.bmp
   :width: 100%
   :align: center

where, u_0 is the approach velocity, H is the upstream
potential head, hv is the upstream velocity head, Ht = H + hv is the upstream total head, h is the thickness of the
nappe, d1 is the backwater depth beneath the nappe, d2 is the backwater depth downstream of the nappe.

This case tests the ability of PROTEUS to simulate the free-surface
evolution and the flow separation. The results of the simulations can
be compared with the data in the following references.  For more
details, see runfiles or references.

Running
-------

Run it from this directory with the deck's own direct-solver/ASM option file (``inputTemplates/petsc.options.asm``
at the root of this repository, the file ``garnet.pbs`` uses), with ``parun`` or with ``pro`` (``pro run`` takes the same
``-l``, ``-O``, ``-D`` and ``-C`` flags)::

   parun sharp_crested_weir_so.py -l 5 -O ../../../inputTemplates/petsc.options.asm -D result_folder
   pro run sharp_crested_weir_so.py -l 5 -O ../../../inputTemplates/petsc.options.asm -D result_folder

Under MPI put ``mpiexec -n <ranks>`` in front. With the default solver options the run stops at t=1.5614 (step
failure); with the option file it passes that point (8 ranks, to t=2.0 in 2,722 s; 32 ranks, past 3.46 s with no
failure). ``-O ../../../inputTemplates/petsc.options.superlu_dist`` (direct LU) is about 5.6 times slower on this deck;
it is what the two ``deprecated/sharp_crested_weir_VM_V1`` and ``_VM_V2`` decks need (no step with the defaults). Add ``-C "T=2.0"`` for a short check.

References
----------

- Montes, J.S. (1992). "Curvature Analysis of Spillway Profiles."
  Proc. 11th Australasian Fluid Mechanics Conference AFMC, Hobart,
  Australia, Paper 7E-7,2, 941-944.

- U. S. Army Engineer Waterways Experiment Station (WES, 1977) -
  HYDRAULIC DESIGN CRITERIA - SHEETS 111-11 to 111-14/1 - Overflow
  Spillway Crest – Upper Nappe Profile.
