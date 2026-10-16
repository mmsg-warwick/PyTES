#
# Parameters of the finned-tube family
#
"""
Parameters of the finned-tube family: a block of phase-change material (PCM) with metal fins,
crossed by parallel tubes carrying the heat transfer fluid (HTF).

Geometry. The device has ``N`` identical tubes, and the models describe one of them (device
totals are multiplied by ``N``):

- the HTF flows along a tube of radius ``R_f`` and length ``Z``, with ``z`` the distance from
  the inlet;
- the PCM fills the storage around the tube, from the tube wall (``y = R_f``) to an outer
  radius ``H = R_f + D``, with ``y`` the distance from the tube axis and ``D`` the
  "Storage depth" (its extent from the wall). ``H`` is about half the distance between
  neighbouring tubes, where the heat flux vanishes by symmetry;
- metal fins are annular discs around the tube, perpendicular to it, spanning the whole
  annulus. ``d_c`` is the fin thickness and ``d_m`` the fin pitch (the centre-to-centre
  distance between consecutive fins), so the fins take up a volume fraction
  ``delta = d_c / d_m``.

The models neglect conduction along the tube (in ``z``) in the PCM and the fins, heat losses
to the surroundings, the thermal mass and resistance of the tube wall (other than the heat
transfer coefficient ``h``), convection in the liquid PCM, and the volume change on melting
(the latent heat per unit volume uses the solid density).
"""

import numpy as np
import pybamm

from ...fluids import ConstantPropertyLiquid
from ...materials import CompositeMaterial, PureMaterial, SensibleMaterial
from ...parameters import DeviceParameters


class FinnedTubeParameters(DeviceParameters):
    """
    Parameters of the finned-tube family, as PyBaMM symbols. See
    :class:`pytes.parameters.DeviceParameters` for the device-level ones.

    Attributes
    ----------
    R_f : pybamm.Parameter
        "Tube radius [m]".
    Z : pybamm.Parameter
        "Tube length [m]".
    H : pybamm.Symbol
        The outer radius of the storage around a tube [m], ``R_f + D``.
    D : pybamm.Parameter
        "Storage depth [m]": the extent of the storage from the tube wall (the length of the
        "storage depth" domain), so that the storage outer radius is about half the
        distance between neighbouring tubes.
    d_c : pybamm.Parameter
        "Fin thickness [m]".
    d_m : pybamm.Parameter
        "Fin pitch [m]": the centre-to-centre distance between consecutive fins.
    delta : pybamm.Symbol
        Volume fraction of the fins, ``d_c / d_m``.
    N_tubes : pybamm.Parameter
        "Number of tubes".
    area, perimeter : pybamm.Symbol
        Flow area ``pi R_f**2`` [m2] and wall perimeter ``2 pi R_f`` [m] of one tube.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object, with zero enthalpy at the reference temperature.
    pcm : :class:`pytes.materials.PureMaterial`
        The PCM on its own (parameters "PCM ...").
    metal : :class:`pytes.materials.SensibleMaterial`
        The fin metal (parameters "Metal ...").
    composite : :class:`pytes.materials.CompositeMaterial`
        The PCM and the fins homogenised into one material.
    T_m : pybamm.Parameter
        The PCM melting temperature [K].
    temperature_reference : pybamm.Symbol
        Reference of the temperature variables: the melting temperature.
    """

    def __init__(self):
        super().__init__()
        self.R_f = pybamm.Parameter("Tube radius [m]")
        self.Z = pybamm.Parameter("Tube length [m]")
        self.D = pybamm.Parameter("Storage depth [m]")
        self.H = self.R_f + self.D
        self.d_c = pybamm.Parameter("Fin thickness [m]")
        self.d_m = pybamm.Parameter("Fin pitch [m]")
        self.delta = self.d_c / self.d_m
        self.N_tubes = pybamm.Parameter("Number of tubes")
        self.area = np.pi * self.R_f**2
        self.perimeter = 2 * np.pi * self.R_f

        self.fluid = ConstantPropertyLiquid(T_ref=self.T_ref)
        self.pcm = PureMaterial("PCM")
        self.metal = SensibleMaterial("Metal")
        self.composite = CompositeMaterial(self.pcm, self.metal, self.delta)
        self.T_m = self.pcm.T_m
        self.temperature_reference = self.T_m
