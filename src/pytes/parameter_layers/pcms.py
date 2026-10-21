#
# Phase-change material layers
#
"""
Phase-change material layers, as read by :class:`pytes.materials.PureMaterial`.

Each layer is a function returning a fresh dict, registered in :data:`LAYERS`, with the
sources of its values in ``"citations"``. "PCM smoothing width [K]" is numerical, not a
property of the material, but stays in this layer for now (issue #3). Each docstring records
the temperature at which the constant values were taken, where the source gives one value
per phase over a range (DESIGN, deferred: temperature-dependent properties).
"""


def nallusamy2007_paraffin():
    """
    The paraffin of Nallusamy, Sampath and Velraj (2007).

    Source: `Nallusamy, Sampath and Velraj (2007)
    <https://doi.org/10.1016/j.renene.2006.04.015>`__.
    Taken at: not specified.
    """
    return {
        "citations": ["Nallusamy2007"],
        "PCM solid phase conductivity [W.m-1.K-1]": 0.4,
        "PCM liquid phase conductivity [W.m-1.K-1]": 0.15,
        "PCM solid phase density [kg.m-3]": 861,
        "PCM liquid phase density [kg.m-3]": 778,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": 1850,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 2384,
        "PCM latent heat [J.kg-1]": 213e3,
        "PCM melting temperature [K]": 60 + 273.15,
        "PCM melting range [K]": 0,
        "PCM smoothing width [K]": 0.01,
    }


def raul2018_pcm():
    """
    A164, the PCM of Raul et al. (2018).

    Source: `Raul et al. (2018)
    <https://doi.org/10.1016/j.applthermaleng.2018.07.123>`__.
    Taken at: not specified.
    """
    return {
        "citations": ["Raul2018"],
        "PCM solid phase conductivity [W.m-1.K-1]": 0.45,
        "PCM liquid phase conductivity [W.m-1.K-1]": 0.45,
        "PCM solid phase density [kg.m-3]": 1500,
        "PCM liquid phase density [kg.m-3]": 1500,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2013.3,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 2013.3,
        "PCM latent heat [J.kg-1]": 249700,
        "PCM melting temperature [K]": 168.7 + 273.15,
        "PCM melting range [K]": 0,
        "PCM smoothing width [K]": 0.01,
    }


def pcm_10n():
    """
    A representative PCM for cold storage applications. The values are representative of a
    commercial PCM, but not of any one product.

    Taken at: not specified.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": 0.6,
        "PCM liquid phase conductivity [W.m-1.K-1]": 0.4,
        "PCM solid phase density [kg.m-3]": 1000,
        "PCM liquid phase density [kg.m-3]": 1200,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2000,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 3500,
        "PCM latent heat [J.kg-1]": 330e3,
        "PCM melting temperature [K]": 263.15,
        "PCM melting range [K]": 1,
        "PCM smoothing width [K]": 0.01,
    }


def pcm_30():
    """
    A representative PCM for room temperature applications. The values are representative of
    a commercial PCM, but not of any one product.

    Taken at: not specified.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": 0.3,
        "PCM liquid phase conductivity [W.m-1.K-1]": 0.15,
        "PCM solid phase density [kg.m-3]": 1000,
        "PCM liquid phase density [kg.m-3]": 850,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2200,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 2800,
        "PCM latent heat [J.kg-1]": 180e3,
        "PCM melting temperature [K]": 303.15,
        "PCM melting range [K]": 3.0,
        "PCM smoothing width [K]": 0.01,
    }


def pcm_60():
    """
    A representative PCM for hot water applications. The values are representative of a
    commercial PCM, but not of any one product.

    Taken at: not specified.
    """
    return {
        "citations": [],
        "PCM solid phase conductivity [W.m-1.K-1]": 0.6,
        "PCM liquid phase conductivity [W.m-1.K-1]": 0.5,
        "PCM solid phase density [kg.m-3]": 1400,
        "PCM liquid phase density [kg.m-3]": 1300,
        "PCM solid phase specific heat capacity [J.kg-1.K-1]": 2500,
        "PCM liquid phase specific heat capacity [J.kg-1.K-1]": 3000,
        "PCM latent heat [J.kg-1]": 250e3,
        "PCM melting temperature [K]": 333.15,
        "PCM melting range [K]": 2.0,
        "PCM smoothing width [K]": 0.01,
    }


#: The PCM layers, by name
LAYERS = {
    "Paraffin (Nallusamy 2007)": nallusamy2007_paraffin,
    "A164 (Raul 2018)": raul2018_pcm,
    "PCM 10N": pcm_10n,
    "PCM 30": pcm_30,
    "PCM 60": pcm_60,
}
