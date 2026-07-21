"""
Governors Activation Module
Activates/deactivates governor controls based on unit bias configuration.
"""

from integrator.managers.assest_manager import UnitAssetManager


class GovernorsActivationStep:
    """
    Activates governors for synchronous units based on bias (Kpf) value.
    Units with bias > 0 have governors active, otherwise inactive.
    """

    def __init__(self, app=None):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.asset_manager = UnitAssetManager(app)

    def apply(self, context=None):
        """
        Apply governor activation/deactivation.

        Args:
            context: ScenarioContext (optional)
        """
        # Process only synchronous units (ElmSym)
        for asset in self.asset_manager.sym_assets:
            unit = asset.pf_obj
            self._align_governors(unit)

    def _align_governors(self, unit):
        """Align governor status with unit bias"""
        bias = unit.GetAttribute("e:Kpf")

        if unit.c_pmod:
            for element in unit.c_pmod.GetContents():
                if element:
                    try:
                        # Check if element is governor-related
                        if any(
                            gov_type in element.typ_id.loc_name
                            for gov_type in ["pcu", "gov", "pmu", "pco"]
                        ):
                            # Active if bias > 0, inactive otherwise
                            element.outserv = 0 if bias > 0 else 1
                    except AttributeError:
                        pass


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app

    step = GovernorsActivationStep(app)
    step.apply()

    print("✅ Governors activation completed")
