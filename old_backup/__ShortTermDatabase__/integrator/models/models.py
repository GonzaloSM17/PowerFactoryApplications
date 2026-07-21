from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DynamicModel:
    pf_obj: Any
    pf_name: str


@dataclass
class ElectricalAsset:
    """
    Base class for all electrical assets (generators, BESS, DER, etc.).
    """

    pf_obj: Any
    pf_name: str
    asset_type: str
    model_name: Optional[str]
    n_unit: int
    p_min: float
    p_rated: float
    p_max: float
    s_nom: float
    h: Optional[float] = None

    # dyn_model: Optional[DynamicModel] = None

    # def set_dyn_model_agreement(self, agreement: DynamicModel):
    #     self.dyn_model = agreement


@dataclass
class SynchronousAsset(ElectricalAsset):
    """Synchronous generator / unit"""

    pass


@dataclass
class InverterBasedAsset(ElectricalAsset):
    """Inverter-based resource (IBR, BESS, PV, etc.)"""

    pass


@dataclass
class AsynchronousAsset(ElectricalAsset):
    """Asynchronous / a-sym unit"""

    pass


@dataclass
class ReactiveAsset:
    """Reactive compensator, STATCOM, SVC, etc."""

    pf_obj: Any
    pf_name: str


@dataclass
class LoadAsset:
    """Electrical load"""

    pf_obj: Any
    pf_name: str
