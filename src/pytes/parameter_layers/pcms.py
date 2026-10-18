#
# Phase-change material layers
#
"""
Phase-change material layers, as read by :class:`pytes.materials.PureMaterial`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`. Values and
citations are to be added, from cited sources. "PCM smoothing width [K]" is numerical, not a
property of the material, but stays in this layer for now (issue #3).
"""


def finned_tube_pcm():
    """
    The PCM of the default finned-tube battery, melting at 58 °C. Stands in for the PCM part
    of the finned-tube default set, which has no named material or source yet.

    Source: to be added.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": None,
        "PCM liquid phase conductivity [W.m-1.K-1]": None,
        "PCM solid phase density [kg.m-3]": None,
        "PCM liquid phase density [kg.m-3]": None,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM latent heat [J.kg-1]": None,
        "PCM melting temperature [K]": None,
        "PCM melting range [K]": None,
        "PCM smoothing width [K]": None,
    }


def nallusamy2007_paraffin():
    """
    The paraffin of Nallusamy, Sampath and Velraj (2007). Stands in for the PCM part of the
    packed-bed "Nallusamy2007" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": None,
        "PCM liquid phase conductivity [W.m-1.K-1]": None,
        "PCM solid phase density [kg.m-3]": None,
        "PCM liquid phase density [kg.m-3]": None,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM latent heat [J.kg-1]": None,
        "PCM melting temperature [K]": None,
        "PCM melting range [K]": None,
        "PCM smoothing width [K]": None,
    }


def raul2018_pcm():
    """
    The PCM of the "Raul2018" bed, melting at 168.7 °C. Stands in for the PCM part of the
    packed-bed "Raul2018" set.

    Source: to be added.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": None,
        "PCM liquid phase conductivity [W.m-1.K-1]": None,
        "PCM solid phase density [kg.m-3]": None,
        "PCM liquid phase density [kg.m-3]": None,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": None,
        "PCM latent heat [J.kg-1]": None,
        "PCM melting temperature [K]": None,
        "PCM melting range [K]": None,
        "PCM smoothing width [K]": None,
    }


#: The PCM layers, by name
LAYERS = {
    "Finned tube PCM": finned_tube_pcm,
    "Nallusamy2007 paraffin": nallusamy2007_paraffin,
    "Raul2018 PCM": raul2018_pcm,
}
