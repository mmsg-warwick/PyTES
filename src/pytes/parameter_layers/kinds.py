#
# Kinds of parameter layer
#
"""
The kinds of parameter layer and the names each one holds (DESIGN D1).

A layer holds every name its kind requires, may hold the kind's optional names, and holds no
other names, so layers of different kinds never share a name and merge without clashes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerKind:
    """
    A kind of parameter layer.

    Attributes
    ----------
    key : str
        Identifier of the kind, e.g. "pcm", used as a keyword of
        :func:`pytes.parameter_layers.compose`.
    description : str
        What a layer of this kind describes.
    required : tuple of str
        Parameter names every layer of this kind holds.
    optional : tuple of str
        Parameter names a layer of this kind may hold, used by no model yet (hooks, e.g. the
        fluid viscosity for a flow-dependent heat transfer coefficient).
    """

    key: str
    description: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()

    @property
    def names(self):
        """Every parameter name a layer of this kind may hold"""
        return self.required + self.optional


OPERATION = LayerKind(
    "operation",
    "How the device is run: the energy reference, the initial state and the controls "
    "(DESIGN D14)",
    (
        "Reference temperature [K]",
        "Initial temperature [K]",
        "Inlet temperature [K]",
        "Mass flow rate [kg.s-1]",
    ),
)

COUPLING = LayerKind(
    "coupling",
    "Parameters of the surface flux law between the fluid and the storage (DESIGN D6, D8)",
    ("Heat transfer coefficient [W.m-2.K-1]",),
)

HEAT_TRANSFER_FLUID = LayerKind(
    "heat_transfer_fluid",
    "The heat transfer fluid, as read by :class:`pytes.fluids.ConstantPropertyLiquid`",
    (
        "Heat transfer fluid density [kg.m-3]",
        "Heat transfer fluid specific heat capacity [J.kg-1.K-1]",
        "Heat transfer fluid conductivity [W.m-1.K-1]",
    ),
    ("Heat transfer fluid viscosity [Pa.s]",),
)

PCM = LayerKind(
    "pcm",
    "The phase-change material, as read by :class:`pytes.materials.PureMaterial`. "
    '"PCM smoothing width [K]" is numerical, but stays in this layer for now (issue #3)',
    (
        "PCM solid phase conductivity [W.m-1.K-1]",
        "PCM liquid phase conductivity [W.m-1.K-1]",
        "PCM solid phase density [kg.m-3]",
        "PCM liquid phase density [kg.m-3]",
        "PCM solid phase specific heat capacity [J.kg-1.K-1]",
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]",
        "PCM latent heat [J.kg-1]",
        "PCM melting temperature [K]",
        "PCM melting range [K]",
        "PCM smoothing width [K]",
    ),
)

METAL = LayerKind(
    "metal",
    "The metal of the fins, as read by :class:`pytes.materials.SensibleMaterial`. One "
    "metal per device for now (issue #3)",
    (
        "Metal conductivity [W.m-1.K-1]",
        "Metal density [kg.m-3]",
        "Metal specific heat capacity [J.kg-1.K-1]",
    ),
)

FINNED_TUBE_FLOW_PATH = LayerKind(
    "finned_tube_flow_path",
    "The tubes of the finned-tube family, and so the size of the device (see "
    ":class:`pytes.models.finned_tube.FinnedTubeParameters`)",
    (
        "Number of tubes",
        "Tube radius [m]",
        "Tube length [m]",
    ),
)

FINNED_TUBE_STORAGE_ELEMENT = LayerKind(
    "finned_tube_storage_element",
    "The fins of the finned-tube family, per unit length of tube (see "
    ":class:`pytes.models.finned_tube.FinnedTubeParameters`)",
    (
        "Fin thickness [m]",
        "Fin pitch [m]",
        "Storage depth [m]",
    ),
)

PACKED_BED_FLOW_PATH = LayerKind(
    "packed_bed_flow_path",
    "The bed of the packed-bed family, and so the size of the device (see "
    ":class:`pytes.models.packed_bed.PackedBedParameters`)",
    (
        "Bed length [m]",
        "Bed cross-sectional area [m2]",
    ),
)

PACKED_BED_STORAGE_ELEMENT = LayerKind(
    "packed_bed_storage_element",
    "The capsules of the packed-bed family and how they pack (see "
    ":class:`pytes.models.packed_bed.PackedBedParameters`)",
    (
        "Capsule radius [m]",
        "Bed porosity",
    ),
)

#: Every kind of layer, by key
KINDS = {
    kind.key: kind
    for kind in (
        OPERATION,
        COUPLING,
        HEAT_TRANSFER_FLUID,
        PCM,
        METAL,
        FINNED_TUBE_FLOW_PATH,
        FINNED_TUBE_STORAGE_ELEMENT,
        PACKED_BED_FLOW_PATH,
        PACKED_BED_STORAGE_ELEMENT,
    )
}
