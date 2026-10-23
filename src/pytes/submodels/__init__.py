"""Submodels: the fluid, storage and coupling slots, the device-level energy, and the
surface flux laws of the couplings."""

from .. import deprecation
from .base_submodel import BaseSubModel
from .coupling import FinRootCoupling, FinStorageCoupling, WallCoupling
from .energy import DeviceEnergy, PerAreaTotals
from .fluid import AdvectedFluid, FlowPath
from .flux_laws import (
    CORRELATIONS,
    FluidState,
    Gnielinski,
    HeatTransferCoefficientOptions,
    Jeffreson,
    NewtonCooling,
    NusseltCorrelation,
    PackedBedCorrelation,
    SurfaceFluxLaw,
    TubeCorrelation,
    WakaoKaguei,
    register_correlation,
)
from .storage import EnthalpyStorage, LumpedGeometry, LumpedStorage, StorageGeometry

__all__ = [
    "AdvectedFluid",
    "BaseSubModel",
    "CORRELATIONS",
    "DeviceEnergy",
    "EnthalpyStorage",
    "FinRootCoupling",
    "FinStorageCoupling",
    "FlowPath",
    "FluidState",
    "Gnielinski",
    "HeatTransferCoefficientOptions",
    "Jeffreson",
    "LumpedGeometry",
    "LumpedStorage",
    "NewtonCooling",
    "NusseltCorrelation",
    "PackedBedCorrelation",
    "PerAreaTotals",
    "StorageGeometry",
    "SurfaceFluxLaw",
    "TubeCorrelation",
    "WakaoKaguei",
    "WallCoupling",
    "register_correlation",
]

# The old names of the couplings (LedgerWallCoupling, FinPCMCoupling) warn and give the
# new ones
__getattr__ = deprecation.module_getattr(__name__)
