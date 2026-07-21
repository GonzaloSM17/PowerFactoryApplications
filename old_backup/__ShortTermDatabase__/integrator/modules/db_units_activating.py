import time
from abc import ABC, abstractmethod

# Import new managers and models
from integrator.managers.assest_manager import (
    UnitAssetManager,
    LoadManager,
)
from integrator.models.models import (
    SynchronousAsset,
    InverterBasedAsset,
    AsynchronousAsset,
    ReactiveAsset,
    LoadAsset,
)

# Define problematic units for reactive compensation
ISSUE_UNITS = {"ReactiveCompensation": {"ANDES SOLAR IIB", "QUILAPILUN"}}

REFERENCE_MACHINES = [
    "HE RALCO U1",
    "HE RALCO U2",
    "HE PANGUE U1",
    "HE PANGUE U2",
    "HE ANTUCO U1",
    "HE ANTUCO U2",
    "TER SANTA MARIA U1",
]


class UnitProcessorBase(ABC):
    def __init__(self, unit):
        self.unit = unit

    @abstractmethod
    def process(self):
        pass


class ReactiveCompensationProcessor(UnitProcessorBase):

    def process(self):

        self.unit.pgini = 0
        self.unit.qgini = 0

        problematic_units = ISSUE_UNITS["ReactiveCompensation"]

        if any(keyword in self.unit.loc_name.upper() for keyword in problematic_units):

            self.unit.outserv = 1

            if self.unit.c_pstac is not None:
                self.unit.c_pstac.outserv = 1
        else:

            self.unit.outserv = 0

            if self.unit.c_pstac is not None:
                self.unit.c_pstac.outserv = 0


class GeneralUnitProcessor(UnitProcessorBase):

    def process(self):

        _pgini_non_zero = self.unit.pgini != 0
        _in_service_status = bool(self.unit.outserv)

        if _pgini_non_zero == _in_service_status:
            self.unit.outserv = not _pgini_non_zero
        else:
            pass

        # Special treatment for Q of ElmGenstat
        if self.unit.GetClassName() == "ElmGenstat":

            if self.unit.qgini != 0:
                self.unit.qgini = 0

        # Arrange Q limits for ElmGenstat
        if self.unit.GetClassName() == "ElmGenstat" and self.unit.pQlimType is None:

            if (self.unit.q_min != -0.33) or (self.unit.q_max != 0.33):

                self.unit.q_min = -0.33
                self.unit.q_max = 0.33

        if self.unit.GetClassName() == "ElmSym":

            def _voltage_adjust(unit):
                _unit = unit

                if _unit.usetp < 0.95:
                    _unit.usetp = 0.95

                elif _unit.usetp > 1.05:
                    _unit.usetp = 1.05

                else:
                    _usetp = round(self.unit.usetp, 3)
                    _unit.usetp = _usetp

            # Adjust voltage target
            _voltage_adjust(self.unit)

            # Setting mode
            _capacity = self.unit.typ_id.sgn * self.unit.typ_id.cosn * self.unit.ngnum
            if _capacity < 20:
                self.unit.av_mode = "constq"
            else:
                self.unit.av_mode = "constv"

            # Setting Q target for "constv" (for clearence)
            if self.unit.av_mode == "constv":
                self.unit.qgini = 0

        # Ensure no reference machine
        self.unit.ip_ctrl = 0


class ReactiveCompensatorProcessor:

    def __init__(self, svs):
        self.svs = svs

    def process(self):
        self.svs.outserv = 0


class LoadProcessor:

    def __init__(self, load):
        self.load = load

    def process(self):
        if self.load.outserv == 0 and self.load.plini == 0:
            self.load.outserv = 1
        else:
            return


class UnitsActivationStep:
    """
    Step that activates/deactivates and configures PowerFactory units for simulation.
    Uses composition to access UnitAssetManager and LoadManager.

    Single responsibility: Configure units based on dispatch and system requirements.
    """

    def __init__(self, app):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        # Composition: use managers instead of inheritance
        self.asset_manager = UnitAssetManager(app)
        self.load_manager = LoadManager(app)

    def _process_units(self):
        """Process all generation assets (sync, ibr, async)"""

        # Process synchronous assets (ElmSym)
        for asset in self.asset_manager.sym_assets:
            unit = asset.pf_obj
            processor = GeneralUnitProcessor(unit)
            processor.process()

        # Process inverter-based assets (ElmGenstat)
        for asset in self.asset_manager.no_sym_assets:
            unit = asset.pf_obj
            processor = GeneralUnitProcessor(unit)
            processor.process()

        # Process asynchronous assets (ElmAsm)
        for asset in self.asset_manager.a_sym_assets:
            unit = asset.pf_obj
            processor = GeneralUnitProcessor(unit)
            processor.process()

    def _set_reference_machine(self):
        """Set one synchronous machine as reference (swing bus)"""

        for ref_machine_name in REFERENCE_MACHINES:
            # Search in synchronous assets only
            for asset in self.asset_manager.sym_assets:
                if asset.pf_name == ref_machine_name:
                    unit = asset.pf_obj

                    # Check if it's dispatched and in service
                    if hasattr(unit, "pgini") and hasattr(unit, "outserv"):
                        if unit.pgini > 0 and unit.outserv == 0:
                            unit.ip_ctrl = 1
                            print(
                                f"Reference machine chosen: {unit.loc_name} "
                                f"(dispatch={unit.pgini:.2f} MW, in-service)"
                            )
                            return  # Exit after finding first valid reference

    def _process_reactive_compensators(self):
        """Process reactive compensators (SVS, STATCOM, etc.)"""

        for asset in self.asset_manager.reactive_assets:
            reactive_compensator = asset.pf_obj
            ReactiveCompensatorProcessor(reactive_compensator).process()

    def _process_loads(self):
        """Process electrical loads"""

        for asset in self.load_manager.loads:
            load = asset.pf_obj
            LoadProcessor(load).process()

    def apply(self, context=None):
        """
        Apply unit activation/configuration to PowerFactory.

        Args:
            context: ScenarioContext (optional for now, for future compatibility)
        """

        self._process_units()
        self._set_reference_machine()
        self._process_reactive_compensators()
        self._process_loads()


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app
    app.Show()

    # Running time...
    start_time = time.time()

    step = UnitsActivationStep(app)
    step.apply()

    # End timing
    end_time = time.time()
    minutes, seconds = divmod(end_time - start_time, 60)
    print(
        f"Time taken to process units: {int(minutes)} minutes and {seconds:.2f} seconds"
    )
