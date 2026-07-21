"""Project constants used across ShortTermDatabase modules.

Contains the MINIMUM_TECHNICAL_DISPATCH mapping extracted from
`db_dispatch_integrating.py` to keep large static data separate and
maintainable.
"""

MINIMUM_TECHNICAL_DISPATCH = {
    "HE PEHUENCHE U2": 126,
    "TER NEHUENCO CC1-TG": 145,
    "TER SAN ISIDRO II CC1-TG": 105,
    "TER SAN ISIDRO II CC1-TV": 64,
    "TER NEHUENCO CC1-TV": 80,
    "HE ANTUCO U1": 80,
    "HE ANTUCO U2": 80,
    "HE RALCO U2": 90,
    "TER CAMPICHE U1": 84,
    "TER NUEVA VENTANAS U1": 82,
    "TER TALTAL U1": 63,
    "TER TALTAL U2": 54,
    "TER KELAR CC1-TV": 53,
    "TER TOCOPILLA U16-TG-TV": 50,
    "TER CANDELARIA U1": 40,
    "TER CANDELARIA U2": 40,
    "TER MEJILLONES CTM3-TG": 40,
    "TER GUACOLDA U4": 38,
    "TER ATACAMA CC1-TG1": 31,
    "TER ATACAMA CC2-TG2": 31,
    "HP LA CONFLUENCIA U1": 28,
    "HE ANGOSTURA U1": 74,
    "HE ANGOSTURA U2": 74,
    "HE ANGOSTURA U3": 38.5,
    "HE MACHICURA U1": 18.6,
    "TER ARAUCO U1": 5,
    "HP SAN ANDRES U1": 5,
    "HP SAUZALITO U1": 5,
    "HP COYA U5": 4.8,
    "TER TOCOPILLA TG3": 4,
    "HP ITATA U1": 3.7,
    "HP PMG RENAICO U1": 3.2,
    "HP LAJA I U1": 6.1,
    "HP PMG SAN CLEMENTE U1": 1.4,
    "TER SANTA MARTA (U1-U10)": 0.2,
    "TER TENO GAS (U1-U26)": 0,
}

REFERENCE_MACHINES = [
    "HE RALCO U1",
    "HE RALCO U2",
    "HE PANGUE U1",
    "HE PANGUE U2",
    "HE ANTUCO U1",
    "HE ANTUCO U2",
    "TER SANTA MARIA U1",
]
