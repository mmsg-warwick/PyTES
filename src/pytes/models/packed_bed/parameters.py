#
# Parameters of the packed-bed family
#
"""
Parameters of the packed-bed family: a bed of spherical capsules of phase-change material
(PCM), with the heat transfer fluid (HTF) flowing through the voids between them.

Geometry. The bed has length ``Z`` along the flow, with ``z`` the distance from the inlet,
cross-sectional area ``A`` and porosity ``eps`` (the volume fraction of the voids, filled
with fluid). The capsules are spheres of radius ``R`` (the outer radius), with ``r`` the
distance from a capsule's centre; there are ``n = (1 - eps) / (4 pi R**3 / 3)`` of them per
unit bed volume, with ``3 (1 - eps) / R`` of capsule surface per unit bed volume.

The models neglect the capsule shell (its thermal mass and resistance), conduction between
capsules and along the bed in the PCM, axial dispersion in the fluid, heat losses to the
surroundings, convection in the liquid PCM and the volume change on melting (the latent heat
per unit volume uses the solid density).
"""

import numpy as np
import pybamm

from ...fluids import ConstantPropertyLiquid
from ...materials import PureMaterial
from ...parameters import DeviceParameters


class PackedBedParameters(DeviceParameters):
    """
    Parameters of the packed-bed family, as PyBaMM symbols. See
    :mod:`pytes.models.packed_bed.parameters` for the geometry and the assumptions.

    Attributes
    ----------
    Z : pybamm.Parameter
        "Bed length [m]".
    A : pybamm.Parameter
        "Bed cross-sectional area [m2]".
    eps : pybamm.Parameter
        "Bed porosity": the volume fraction of the bed taken by the fluid.
    R : pybamm.Parameter
        "Capsule radius [m]": the outer radius of a capsule.
    flow_area : pybamm.Symbol
        Area of the bed cross-section open to the flow, ``eps A`` [m2].
    capsule_density : pybamm.Symbol
        Number of capsules per unit bed volume [m-3].
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object, with zero enthalpy at the reference temperature.
    pcm : :class:`pytes.materials.PureMaterial`
        The PCM (parameters "PCM ...").
    T_m : pybamm.Parameter
        The PCM melting temperature [K].
    temperature_reference : pybamm.Symbol
        Reference of the temperature variables: the melting temperature.
    """

    def __init__(self):
        super().__init__()
        self.Z = pybamm.Parameter("Bed length [m]")
        self.A = pybamm.Parameter("Bed cross-sectional area [m2]")
        self.eps = pybamm.Parameter("Bed porosity")
        self.R = pybamm.Parameter("Capsule radius [m]")
        self.flow_area = self.eps * self.A
        self.capsule_density = (1 - self.eps) / (4 / 3 * np.pi * self.R**3)

        self.fluid = ConstantPropertyLiquid(T_ref=self.T_ref)
        self.pcm = PureMaterial("PCM")
        self.T_m = self.pcm.T_m
        self.temperature_reference = self.T_m
