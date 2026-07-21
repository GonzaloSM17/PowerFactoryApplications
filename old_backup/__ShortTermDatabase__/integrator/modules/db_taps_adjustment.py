"""
Tap Adjustment Module
Adjusts transformer tap positions iteratively to improve voltage profiles.
"""

from integrator.managers.taps_manager import TapGroupManager


class TapGroup:
    """Business logic for a transformer tap group adjustment"""

    def __init__(self, set_group):
        self.set = set_group
        self.set_group_content()

        self.adjust = True
        self.last_voltage = None
        self.threshold = 1.0

    def set_group_content(self):
        """Extract terminal and transformer from set"""
        self.terminal = self.set.GetAll("ElmTerm")[-1]
        self.transformer = self.set.GetAll("ElmTr2")[-1]

    def is_terminal_in_service(self):
        """Check if terminal is in service"""
        return self.terminal.GetAttribute("outserv") == 0

    def save_measurement(self):
        """Save current tap position and voltage"""
        if self.is_terminal_in_service():
            self.tap_step = self.transformer.GetAttribute("nntap")
            self.current_voltage = self.terminal.GetAttribute("m:u1")
        else:
            self.adjust = False

    def adjustment(self):
        """Adjust tap position based on voltage deviation"""
        threshold = self.threshold

        if self.current_voltage > threshold:
            # Voltage too high - increase tap
            max_tap = self.transformer.typ_id.ntpmx
            delta_step = self.transformer.GetAttribute("t:dutap") / 100
            delta = int(abs(self.current_voltage - 1) / delta_step)

            tap = min(self.tap_step + delta, max_tap)
            self.transformer.SetAttribute("nntap", tap)

        elif self.current_voltage <= threshold:
            # Voltage too low - decrease tap
            min_tap = self.transformer.typ_id.ntpmn
            delta_step = self.transformer.GetAttribute("t:dutap") / 100
            delta = int(abs(self.current_voltage - 1) / delta_step + 0.99)

            tap = max(self.tap_step - delta, min_tap)
            self.transformer.SetAttribute("nntap", tap)

        self.last_voltage = self.current_voltage


class TapAdjustmentStep:
    """
    Adjusts transformer tap positions to improve voltage profiles.
    Uses composition with TapGroupManager to access tap groups.
    """

    def __init__(self, app):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.project = app.GetActiveProject()
        self.ldf = app.GetFromStudyCase("ComLdf")
        self.tap_manager = TapGroupManager(app)

    def apply(self, context=None):
        """
        Apply tap adjustments.

        Args:
            context: ScenarioContext (optional)
        """
        # Get tap groups from manager
        tap_group_sets = self.tap_manager.tap_group_folder.GetContents("*.SetSelect")

        # Filter valid groups
        tap_groups = {
            set_obj.loc_name: TapGroup(set_obj)
            for set_obj in tap_group_sets
            if self._references_exist(set_obj)
        }

        if not tap_groups:
            return

        # Run load flow
        self.ldf.Execute()

        # Measure current state
        for tap_group in tap_groups.values():
            tap_group.save_measurement()

        # Apply adjustments
        for tap_group in tap_groups.values():
            if tap_group.adjust:
                tap_group.adjustment()

    def _references_exist(self, set_obj):
        """Check if set contains valid terminal and transformer references"""
        return bool(set_obj.GetAll("ElmTerm")) and bool(set_obj.GetAll("ElmTr2"))


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app

    step = TapAdjustmentStep(app)
    step.apply()

    print("✅ Tap adjustment completed")
