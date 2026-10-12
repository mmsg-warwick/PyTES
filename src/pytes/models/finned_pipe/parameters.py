#
# Parameters of the finned-pipe family
#
"""
Parameters of the finned-pipe family: a block of phase-change material (PCM) with metal fins,
crossed by parallel pipes carrying the heat transfer fluid (HTF).

Geometry. The device has ``N`` identical pipes, and the models describe one of them (device
totals are multiplied by ``N``):

- the HTF flows along a pipe of radius ``R_f`` and length ``Z``, with ``z`` the distance from
  the inlet;
- the PCM fills the annulus around the pipe, from the pipe wall (``y = R_f``) to an outer
  radius ``H`` ("PCM outer radius"), with ``y`` the distance from the pipe axis. ``H`` is
  about half the distance between neighbouring pipes, where the heat flux vanishes by
  symmetry;
- metal fins are annular discs around the pipe, perpendicular to it, spanning the whole
  annulus. ``d_c`` is the fin thickness and ``d_m`` the fin pitch (the centre-to-centre
  distance between consecutive fins), so the fins take up a volume fraction
  ``delta = d_c / d_m``.

The models neglect conduction along the pipe (in ``z``) in the PCM and the fins, heat losses
to the surroundings, the thermal mass and resistance of the pipe wall (other than the heat
transfer coefficient ``h``), convection in the liquid PCM, and the volume change on melting
(the latent heat per unit volume uses the solid density).
"""

import numpy as np
import pybamm

from ...fluids import ConstantPropertyLiquid
from ...materials import CompositeMaterial, PureMaterial, SensibleMaterial
from ...parameters import DeviceParameters


class FinnedPipeParameters(DeviceParameters):
    """
    Parameters of the finned-pipe family, as PyBaMM symbols. See
    :class:`pytes.parameters.DeviceParameters` for the device-level ones.

    Attributes
    ----------
    R_f : pybamm.Parameter
        "Pipe radius [m]".
    Z : pybamm.Parameter
        "Pipe length [m]".
    H : pybamm.Parameter
        "PCM outer radius [m]": the outer radius of the PCM annulus, measured from the pipe
        axis (not the thickness of the PCM layer, which is ``H - R_f``).
    d_c : pybamm.Parameter
        "Fin thickness [m]".
    d_m : pybamm.Parameter
        "Fin spacing [m]": the fin pitch, i.e. the centre-to-centre distance between
        consecutive fins.
    delta : pybamm.Symbol
        Volume fraction of the fins, ``d_c / d_m``.
    N_pipes : pybamm.Parameter
        "Number of pipes".
    area, perimeter : pybamm.Symbol
        Flow area ``pi R_f**2`` [m2] and wall perimeter ``2 pi R_f`` [m] of one pipe.
    fluid : :class:`pytes.fluids.ConstantPropertyLiquid`
        The fluid-property object, with zero enthalpy at the lower temperature limit.
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
        self.R_f = pybamm.Parameter("Pipe radius [m]")
        self.Z = pybamm.Parameter("Pipe length [m]")
        self.H = pybamm.Parameter("PCM outer radius [m]")
        self.d_c = pybamm.Parameter("Fin thickness [m]")
        self.d_m = pybamm.Parameter("Fin spacing [m]")
        self.delta = self.d_c / self.d_m
        self.N_pipes = pybamm.Parameter("Number of pipes")
        self.area = np.pi * self.R_f**2
        self.perimeter = 2 * np.pi * self.R_f

        self.fluid = ConstantPropertyLiquid(T_ref=self.T_low)
        self.pcm = PureMaterial("PCM")
        self.metal = SensibleMaterial("Metal")
        self.composite = CompositeMaterial(self.pcm, self.metal, self.delta)
        self.T_m = self.pcm.T_m
        self.temperature_reference = self.T_m
