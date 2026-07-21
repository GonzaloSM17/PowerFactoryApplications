from typing import Any, List, Optional, Tuple
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from integrator.models.models import (
    SynchronousAsset,
    InverterBasedAsset,
    AsynchronousAsset,
    ReactiveAsset,
    LoadAsset,
)


class LoadManager:
    """
    Manages all loads, storing them as dataclasses for further integration.
    """

    def __init__(self, app: Any):
        if app is None:
            raise ValueError("A PowerFactory app instance is required.")
        self.app = app
        self.loads: List[LoadAsset] = []
        self.load_all()

    def load_all(self) -> None:
        raw_loads = self.app.GetCalcRelevantObjects("*.ElmLod") or []
        self.loads = [LoadAsset(pf_obj=ld, pf_name=ld.loc_name) for ld in raw_loads]


class UnitAssetManager:
    """
    Manages all generation assets (synchronous, inverter-based, asynchronous)
    and reactive compensators. Loads them from PowerFactory and classifies into dataclasses.
    """

    def __init__(self, app: Any):
        if app is None:
            raise ValueError("A PowerFactory app instance is required.")
        self.app = app

        self.sym_assets: List[SynchronousAsset] = []
        self.no_sym_assets: List[InverterBasedAsset] = []
        self.a_sym_assets: List[AsynchronousAsset] = []
        self.reactive_assets: List[ReactiveAsset] = []

        self.load_assets()

    @staticmethod
    def _extract_unit_ratings(unit) -> Tuple[float, float, float, float]:
        """Safely extracts p_min, p_rated, p_max, and s_nom."""
        try:
            p_min = round(unit.Pmin_uc, 2)
        except AttributeError:
            p_min = 0.0
        try:
            p_rated = round(unit.Pnom, 2)
        except AttributeError:
            try:
                p_rated = round(unit.typ_id.pgn, 1)
            except AttributeError:
                p_rated = 0.0
        try:
            p_max = round(unit.Pmax_uc, 2)
        except AttributeError:
            try:
                p_max = round(unit.typ_id.pgn, 1)
            except AttributeError:
                p_max = 0.0
        try:
            s_nom = round(unit.sgn, 2)
        except AttributeError:
            try:
                s_nom = round(unit.typ_id.sgn, 1)
            except AttributeError:
                s_nom = 0.0
        return p_min, p_rated, p_max, s_nom

    @staticmethod
    def _extract_model_name(unit) -> Optional[str]:
        try:
            return unit.c_pmod.loc_name
        except AttributeError:
            return None

    def _get_units(self):
        """Retrieve raw units from PowerFactory."""
        sym_units = self.app.GetCalcRelevantObjects("*.ElmSym") or []
        no_sym_units = self.app.GetCalcRelevantObjects("*.ElmGenstat") or []
        asym_units = self.app.GetCalcRelevantObjects("*.ElmAsm") or []
        reactive_units = self.app.GetCalcRelevantObjects("*.ElmSvs") or []
        return sym_units, no_sym_units, asym_units, reactive_units

    def load_assets(self) -> None:
        sync_units, ibr_units, async_units, reactive_units = self._get_units()

        # Synchronous units
        self.sym_assets = [
            SynchronousAsset(
                pf_obj=u,
                pf_name=u.loc_name,
                asset_type="sym_asset",
                model_name=self._extract_model_name(u),
                n_unit=u.ngnum,
                p_min=round(u.Pmin_uc, 2),
                p_rated=round(u.Pnom, 2),
                p_max=round(u.Pmax_uc, 2),
                s_nom=round(u.typ_id.sgn, 2),
                h=round(u.typ_id.h, 3),
            )
            for u in sync_units
        ]

        # Inverter-based units
        self.no_sym_assets = [
            InverterBasedAsset(
                pf_obj=u,
                pf_name=u.loc_name,
                asset_type="no_sym_asset",
                model_name=self._extract_model_name(u),
                n_unit=u.ngnum,
                p_min=self._extract_unit_ratings(u)[0],
                p_rated=self._extract_unit_ratings(u)[1],
                p_max=self._extract_unit_ratings(u)[2],
                s_nom=self._extract_unit_ratings(u)[3],
            )
            for u in ibr_units
        ]

        # Asynchronous units
        self.a_sym_assets = [
            AsynchronousAsset(
                pf_obj=u,
                pf_name=u.loc_name,
                asset_type="a_sym_asset",
                model_name=self._extract_model_name(u),
                n_unit=u.ngnum,
                p_min=self._extract_unit_ratings(u)[0],
                p_rated=self._extract_unit_ratings(u)[1],
                p_max=self._extract_unit_ratings(u)[2],
                s_nom=self._extract_unit_ratings(u)[3],
            )
            for u in async_units
        ]

        # Reactive assets
        self.reactive_assets = [
            ReactiveAsset(pf_obj=u, pf_name=u.loc_name) for u in reactive_units
        ]


if __name__ == "__main__":

    import _powerfactory_app_  # tu app PowerFactory
    import time
    import pandas as pd

    start_time = time.time()

    _powerfactory_app_.app.Show()

    gen_manager = UnitAssetManager(app=_powerfactory_app_.app)
    load_manager = LoadManager(app=_powerfactory_app_.app)

    end_time = time.time()
    logger.info(
        "Time taken to create managers: %.2f minutes",
        round((end_time - start_time) / 60, 2),
    )

    sheets = {
        "Synchronous_Assets": gen_manager.sym_assets,
        "InverterBased_Assets": gen_manager.no_sym_assets,
        "Asynchronous_Assets": gen_manager.a_sym_assets,
        "Reactive_Assets": gen_manager.reactive_assets,
        "Loads": load_manager.loads,
    }

    with pd.ExcelWriter("PowerfactoryAssets.xlsx") as writer:
        for sheet_name, assets_list in sheets.items():
            if not assets_list:
                continue

            df = pd.DataFrame(
                [
                    {k: v for k, v in u.__dict__.items() if k != "pf_obj"}
                    for u in assets_list
                ]
            )

            if "pf_name" in df.columns:
                df = df.sort_values("pf_name").reset_index(drop=True)

            df.to_excel(writer, sheet_name=sheet_name, index=False)
