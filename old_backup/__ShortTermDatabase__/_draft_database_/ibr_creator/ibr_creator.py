# %%

"""
Script Generador de Parques IBR (PS, WT, BESS, DER)

"""

# Custom library imports
import common_libs.user_tools as user_tools

# Standard libraries
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Combobox

# import powerfactory as pf

import ctypes
import sys
import math


class IBRCreator:

    # Initial coordinates
    padx, pady = 5, 3

    def __init__(self, master):
        self.master = master

        self.initialize_variables()
        self.create_widgets()
        self.check_initial_selection()

    def initialize_variables(self):
        self.category = {
            "Photovoltaic": [""],
            "Wind": ["Type_4B", "Type_4A"],
            "BESS": ["Grid Following", "Grid Forming"],
            "DER": [""],
        }

        self.suffix = {
            "Photovoltaic": "PFV",
            "Wind": "PE",
            "BESS": "BESS",
            "DER": "PMGD",
        }

        self.control_mode = {"Q Control": 0, "V Control": 1}

        self.models = {
            "Photovoltaic": "WECC_PV",
            "Wind_Type_4A": "WECC_WT_Type4A",
            "Wind_Type_4B": "WECC_WT_Type4B",
            "BESS_Grid Following": "WECC_BESS_GridFollowing",
            "BESS_Grid Forming": "WECC_BESS_GridForming",
            "DER": "WECC_DER",
        }

        # Simulating the app object
        self.app = app  # Change this to actual app object if available
        # self.app = pf.GetApplication()
        self.selection = None
        self.flag_graphic = None

    def create_widgets(self, padx=padx, pady=pady):
        self.master.title("IBR Creator")
        self.master.geometry("700x350")
        self.master.resizable(0, 0)
        self.master.attributes("-topmost", True)

        # General labels
        Label(self.master, text="Park Configuration:", anchor="w").grid(
            row=0, column=0, padx=padx, pady=pady, sticky="w"
        )

        # About button
        self.btn_about = Button(self.master, text="About...", command=self.about)
        self.btn_about.grid(row=0, column=3, padx=padx, pady=pady, sticky="e")

        # Name
        Label(self.master, text="Name:", anchor="w").grid(
            row=1, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_name = StringVar(self.master, value="Name new park")
        self.entry_name = Entry(self.master, textvariable=self.variable_name)
        self.entry_name.grid(row=1, column=1, padx=padx, pady=pady, sticky="w")

        # Category
        Label(self.master, text="Category:", anchor="w").grid(
            row=2, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.combo_category = Combobox(
            self.master, state="readonly", values=list(self.category.keys())
        )
        self.combo_category.current(0)
        self.combo_category.bind("<<ComboboxSelected>>", self.update_subcategories)
        self.combo_category.grid(row=2, column=1, padx=padx, pady=pady, sticky="w")

        # Control Mode
        self.control_mode_label = Label(self.master, text="Control Mode:", anchor="w")
        self.combo_control_mode = Combobox(
            self.master,
            state="readonly",
            values=list(self.control_mode.keys()),
            width=10,
        )
        self.combo_control_mode.current(0)
        self.control_mode_label.grid(row=2, column=4, padx=padx, pady=pady, sticky="w")
        self.combo_control_mode.grid(row=2, column=5, padx=padx, pady=pady, sticky="w")

        # # Reactive Droop
        # self.variable_reactive_droop = IntVar(self.master, value=2)
        # self.entry_reactive_droop = Entry(self.master, textvariable=self.variable_reactive_droop, justify=RIGHT, width=5)
        # self.label_reactive_droop = Label(self.master, text="Kc:", anchor="w")
        # self.label_reactive_droop_unit = Label(self.master, text="%:", anchor="w")

        # Subcategory
        Label(self.master, text="Subcategory:", anchor="w").grid(
            row=3, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.combo_subcategory = Combobox(self.master, state="readonly")
        self.combo_subcategory.grid(row=3, column=1, padx=padx, pady=pady, sticky="w")

        # Inertia (H in seconds) of Wind Park type_4A (Maybe useful for Grid Forming too)
        self.variable_Ht = IntVar(self.master, value=5)  # Hidden
        self.variable_Hg = IntVar(self.master, value=1)  # Hidden

        self.entry_Ht = Entry(
            self.master, textvariable=self.variable_Ht, justify=RIGHT, width=3
        )  # Hidden
        self.label_Ht = Label(self.master, text="Ht:", anchor="w")  # Hidden
        self.label_Ht_unit = Label(self.master, text="s", anchor="w")  # Hidden
        self.entry_Hg = Entry(
            self.master, textvariable=self.variable_Hg, justify=RIGHT, width=3
        )  # Hidden
        self.label_Hg = Label(self.master, text="Hg:", anchor="w")  # Hidden
        self.label_Hg_unit = Label(self.master, text="s", anchor="w")  # Hidden

        # Capacity
        Label(self.master, text="Active Power:", anchor="w").grid(
            row=4, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_activePower = DoubleVar(self.master, value=100.0)
        Entry(self.master, textvariable=self.variable_activePower, justify=RIGHT).grid(
            row=4, column=1, padx=padx, pady=pady, sticky="w"
        )
        Label(self.master, text="MW", anchor="w").grid(
            row=4, column=2, padx=padx, pady=pady, sticky="w"
        )

        # Busbar or tap off selection
        Label(self.master, text="Connection:", anchor="w").grid(
            row=5, column=0, padx=padx, pady=pady, sticky="w"
        )

        self.label_selection = Label(self.master, text="-", anchor="w")
        self.label_selection.grid(row=5, column=1, padx=padx, pady=pady, sticky="w")

        # Selecting button (Busbar or section of line)
        Button(self.master, text="Select...", command=self.busbar_select).grid(
            row=5, column=3, padx=padx, pady=pady, sticky="e"
        )

        # SCR
        Label(self.master, text="SCR:", anchor="w").grid(
            row=6, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_scr = DoubleVar(self.master, value=3.3)
        Entry(self.master, textvariable=self.variable_scr, justify=RIGHT).grid(
            row=6, column=1, padx=padx, pady=pady, sticky="w"
        )

        self.label_scl = Label(self.master, text=f'(S"k = - )', anchor="w")
        self.label_scl.grid(row=7, column=1, padx=padx, pady=pady, sticky="w")

        self.btn_scr = Button(
            self.master, text="Calculate", command=self.calculate_SCR, state=DISABLED
        )
        self.btn_scr.grid(row=6, column=3, padx=padx, pady=pady, sticky="e")

        # Create
        self.btn_create = Button(
            self.master, text="Create Park", command=self.create, state=DISABLED
        )
        self.btn_create.grid(
            row=8, column=1, columnspan=3, padx=padx, pady=pady, sticky="we"
        )

        # Bind events
        self.combo_category.bind("<<ComboboxSelected>>", self.update_subcategories)
        self.combo_subcategory.bind("<<ComboboxSelected>>", self.update_H_entry)

    def about(self):
        messagebox.showinfo("IBR Creator", "by DEE")

    def update_subcategories(self, event=None):
        selected_category = self.combo_category.get()
        subcategories = self.category.get(selected_category, [])
        self.combo_subcategory["values"] = subcategories
        if subcategories:
            self.combo_subcategory.current(0)
            self.update_H_entry()
        self.update_control_mode()

    def update_H_entry(self, event=None):
        selected_subcategory = self.combo_subcategory.get()
        if selected_subcategory == "Type_4A":
            self.label_Ht.grid(
                row=3, column=4, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.entry_Ht.grid(
                row=3, column=5, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.label_Ht_unit.grid(
                row=3, column=6, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.label_Hg.grid(
                row=3, column=7, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.entry_Hg.grid(
                row=3, column=8, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.label_Hg_unit.grid(
                row=3, column=9, padx=self.padx, pady=self.pady, sticky="w"
            )
        else:
            self.label_Ht.grid_forget()
            self.entry_Ht.grid_forget()
            self.label_Ht_unit.grid_forget()
            self.label_Hg.grid_forget()
            self.entry_Hg.grid_forget()
            self.label_Hg_unit.grid_forget()

    def update_control_mode(self, event=None):
        selected_category = self.combo_category.get()
        selected_subcategory = self.combo_subcategory.get()
        if selected_category in ["Photovoltaic", "Wind"] or (
            selected_category == "BESS" and selected_subcategory == "Grid Following"
        ):
            self.control_mode_label.grid(
                row=2, column=4, padx=self.padx, pady=self.pady, sticky="w"
            )
            self.combo_control_mode.grid(
                row=2, column=5, padx=self.padx, pady=self.pady, sticky="w"
            )
        else:
            self.control_mode_label.grid_forget()
            self.combo_control_mode.grid_forget()

    def busbar_select(self):
        self.terminals = self.app.GetCalcRelevantObjects("*.ElmTerm")
        bus_selection = self.app.ShowModalSelectBrowser(self.terminals, "", "", "")

        self.selection = bus_selection[-1]

        self.flag_graphic = 2
        self.selection.MarkInGraphics(1)
        self.label_selection.configure(text=self.selection.loc_name)
        self.btn_scr.config(state=NORMAL)

    def calculate_SCR(self):
        shc = self.app.GetFromStudyCase("ComShc")
        shc.iopt_mde = 3
        shc.iopt_asc = 0
        shc.iopt_dfr = 0
        shc.ildfinit = 0
        shc.cfac_full = 1
        shc.shcobj = self.selection
        shc.Execute()

        self.scl_value = self.selection.GetAttribute("m:Skss")

        self.variable_scr.set(self.scl_value / self.variable_activePower.get())
        self.scl = str(int(self.scl_value))
        self.label_scl.configure(text=f'(S"k = {self.scl_value} MVA)')

        self.btn_create.config(state=NORMAL)

    def create(self):
        # Getting the grid
        self.grid = self.selection.GetParent()
        while self.grid.GetClassName() != "ElmNet":
            self.grid = self.grid.GetParent()
        self.grid_name = self.grid.loc_name

        # Graphic elements
        self.graphic_folder = self.app.GetProjectFolder("dia")
        self.graphic_list = self.graphic_folder.GetContents("*.IntGrf", 1)

        # Checking if the terminal is drawn, graphic elements and grid of the terminal
        self.terminal = self.selection
        self.terminal_graphic = None
        self.grid_graphic_terminal = None

        for graphic_object in self.graphic_list:
            terminal_associated = graphic_object.pDataObj
            if terminal_associated == self.selection:
                self.terminal_graphic = graphic_object
                if self.flag_graphic != 1:
                    self.terminal.MarkInGraphics(1)

                self.grid_graphic_terminal = self.app.GetCurrentDiagram()
                break

        # Activating the creation process
        self.create_park()

        # Finishing the creation process
        messagebox.showinfo("IBRCreator", "Park successfully created")
        self.master.destroy()

    def create_park(self):
        # Park Configuration
        category, subcategory = self.combo_category.get(), self.combo_subcategory.get()
        category_key = f"{category}_{subcategory}" if subcategory else category

        suffix = self.suffix[category]
        template_name = self.models[category_key]

        park_name = self.variable_name.get().upper()
        park_name = f"{suffix}_{park_name}"

        active_power = self.variable_activePower.get()
        scr = self.variable_scr.get()

        # Create Site
        self.new_site = self.grid.CreateObject("ElmSite", park_name)

        # Importing template
        templates = self.app.GetProjectFolder("templ").GetContents(
            "IBR_Model_Templates.IntFolder"
        )[-1]
        template = templates.GetContents(f"{template_name}.IntTemplate")[-1]

        # Template components
        components = template.GetContents(
            "*.ElmTr2,*.ElmGenstat,*.ElmTerm,*.ElmLne,*.ElmStactrl,*.ElmShnt,*.ElmNec,*.ElmComp"
        )
        graphic_template = template.GetContents("*.IntGrfnet")[-1]

        # Copy template diagram (Graphical objects) in folder of the project
        diagram = self.graphic_folder.PasteCopy(graphic_template)[-1]
        self.new_site.pDiagram, diagram.loc_name = diagram, park_name

        # Associate of the graphic object (diagram) to the elements in site
        site_elements = self.new_site.AddCopy(components).GetContents(
            "*.ElmTr2,*.ElmGenstat,*.ElmTerm,*.ElmLne,*.ElmStactrl,*.ElmShnt,*.ElmNec,*.ElmComp"
        )
        graphic_objects = diagram.GetContents("*.IntGrf")
        for graphic_object in graphic_objects:
            if graphic_object.pDataObj:
                for element in site_elements:
                    if element.loc_name == graphic_object.pDataObj.loc_name:
                        graphic_object.pDataObj = element

        # Copy library in site
        library = template.GetContents("Library")
        if library:
            self.new_site.AddCopy(library)
            self.new_site.GetContents("Library")[-1].GetContents("Dynamic*.IntFolder")[
                0
            ].Delete()

        # Type of the equipments in the libray in site
        equipments = (
            self.new_site.GetContents("Library")[-1]
            .GetContents("Equipment*.IntFolder")[-1]
            .GetContents()
        )
        for element in site_elements:
            if element.GetClassName() in {"ElmTr2", "ElmLne"}:
                for equipment in equipments:
                    if element.typ_id.loc_name == equipment.loc_name:
                        element.typ_id = equipment

        # Generator settings
        generator = self.new_site.GetContents("*.ElmGenstat")[-1]
        cosn = generator.cosn

        generator.sgn = active_power / cosn
        generator.P_max = generator.Pmax_uc = active_power
        generator.Pmax_ucPU = 1
        generator.pmaxratf = 1
        generator.pgini = 0 * active_power  # 50% Dispatch
        generator.qgini = 0

        if generator.cCategory == "Storage":
            generator.Pmin_uc = (-1) * generator.P_max
            generator.Pmin_ucPU = -1

        else:
            pass

        # Curves
        try:
            operational = self.new_site.GetContents("Library")[-1].GetContents(
                "Operational*.IntFolder"
            )[-1]
            curves = operational.GetContents("MVAr*.IntFolder")[-1]
            generator.pQlimType = curves.GetContents("*.IntQlim")[-1]

        except Exception as e:
            self.app.PrintPlain(f"Exception in curve setting: {e}. There is not curve")

        # Interconnection of the project and high voltage line settings
        self.cubicle_terminal = self.terminal.CreateObject("StaCubic", "Cub_IBR")
        hv_line = self.new_site.GetContents("LAT*.ElmLne")[-1]

        hv_line.bus2 = self.cubicle_terminal
        nominal_voltage = self.selection.GetAttribute("e:uknom")
        hv_line.typ_id.uline = nominal_voltage
        hv_line.typ_id.InomAir = active_power * hv_line.typ_id.InomAir / 100.0
        hv_line.typ_id.sline = active_power * hv_line.typ_id.sline / 100.0

        cubicle_pcc = hv_line.bus1
        busbar_pcc = cubicle_pcc.GetParent()
        busbar_pcc.uknom = nominal_voltage

        # Transformer HV/MV setting
        transformer_hvmv = self.new_site.GetContents("TR.ElmTr2")[-1]
        transformer_hvmv.typ_id.utrn_h = nominal_voltage
        transformer_hvmv.typ_id.strn = active_power * 1.1
        transformer_hvmv.typ_id.uktr = 10
        transformer_hvmv.typ_id.xtor = 20

        # # Capacitor setting (Check how it is calculate)
        try:
            capacitor = self.new_site.GetContents("*.ElmShnt")[-1]
            capacitor.ncapa = 0

            max_deltaV, max_stepQ = 1.5 / 100.0, 0.15
            Qmax_stepC = (
                max_stepQ * 0.33 * active_power if scr >= 3.3 else max_deltaV * scr
            )
            capacitor.qcapn = Qmax_stepC

            Q_max = 0.1 * active_power
            capacitor.ncapx = math.ceil(Q_max / Qmax_stepC)
            capacitor.ncapa = capacitor.ncapx

            if capacitor.ncapx * Qmax_stepC > Q_max:
                capacitor.qcapn = Q_max / capacitor.ncapx

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in capacitor configuration: {e}. There is not capacitor element"
            )

        # Collector Paremeter (If there is)
        try:
            collector = self.new_site.GetContents("CE.ElmLne")[-1]
            collector.typ_id.InomAir = active_power * collector.typ_id.InomAir / 100.0
            collector.typ_id.sline = active_power * collector.typ_id.sline / 100.0
            collector.typ_id.rline = 100.0 * collector.typ_id.rline / active_power
            collector.typ_id.xline = 100.0 * collector.typ_id.xline / active_power
            collector.typ_id.rline0 = 100.0 * collector.typ_id.rline0 / active_power
            collector.typ_id.xline0 = 100.0 * collector.typ_id.xline0 / active_power
            collector.typ_id.bline = active_power * collector.typ_id.bline / 100.0
            collector.typ_id.bline0 = active_power * collector.typ_id.bline0 / 100.0

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in collector configuration: {e}. There is not collector element"
            )

        # Transformer MV/LV
        try:
            transformer_mvlv = self.new_site.GetContents("TR_EQ.ElmTr2")
            transformer_mvlv[-1].typ_id.strn = (float(active_power)) * 1.1
            transformer_mvlv[-1].typ_id.uktr = 6
            transformer_mvlv[-1].typ_id.xtor = 15

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in transformer MV/LV configuration: {e}. There is not transformer MV/LV element"
            )

        # Inertia of the WT Type4A
        try:
            dsl_drivetrain = self.new_site.GetContents("*.ElmComp")[-1].GetContents(
                "WTGT*.ElmDsl"
            )[-1]
            parameters_drivetrain = dsl_drivetrain.params

            ht, hg = self.variable_Ht.get(), self.variable_Hg.get()
            parameters_drivetrain[0], parameters_drivetrain[3] = ht, hg

            dsl_drivetrain.params = parameters_drivetrain

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in DSL configuration: {e}. There is not inertia settings DSL"
            )

        # Paremeter of the control (PI of PPC) and Mesuarements devices set
        try:
            # Composite and DSL
            composite_pcc = self.new_site.GetContents("*.ElmComp")[-1].GetContents(
                "*.ElmComp"
            )[-1]
            composite_pcc.loc_name = f"{composite_pcc.loc_name}_{park_name}"

            dsl_ppc = composite_pcc.GetContents("*.ElmDsl")[-1]
            parameters_ppc = dsl_ppc.params

            # Get Control Mode Desired
            selected_control_mode = self.combo_control_mode.get()
            control_mode = self.control_mode.get(selected_control_mode, 0)

            # Droop and times ---
            kc = parameters_ppc[10]  # Could be an entry
            tu, te = parameters_ppc[2], 10

            if control_mode == 1:
                ki = (
                    (1 - (4 * tu / te))
                    * (4 * math.sqrt(scr**2 + 1))
                    / (te * (scr * kc + 1))
                )
                kp = ki / 100

            elif control_mode == 0:
                ki = (
                    (1 - (4 * tu / te))
                    * (4 * math.sqrt(scr**2 + 1))
                    / (te * scr * (scr * kc + 1))
                )
                kp = ki / 100

            # parameters_ppc[12] = control_mode
            ki_rounded, kp_rounded = round(ki, 5), round(kp, 5)
            parameters_ppc[5], parameters_ppc[6] = kp_rounded, ki_rounded

            # Setting the new parameters
            dsl_ppc.params = parameters_ppc

            # Power en current Mesuarements
            power_measuarements = composite_pcc.GetContents("*.StaPqmea")
            current_measuarement = composite_pcc.GetContents("*.StaImea")[-1]

            for power_measuarement in power_measuarements:
                power_measuarement.i_mode = 2
                power_measuarement.Snom = active_power / cosn

            current_measuarement.Inom = (active_power / cosn) / (
                math.sqrt(3) * self.selection.GetAttribute("e:uknom")
            )
            current_measuarement.i_mode = 2

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in DSL configuration: {e}. There is no Plant Controller"
            )

        # Rename elements
        for element in self.new_site.GetContents():
            if element.GetClassName() in {"ElmGenstat"}:
                element.loc_name = park_name
            else:
                element.loc_name = f"{element.loc_name}_{park_name}"

        # Activating the creation of the site inf the diagram of the grid
        self.create_graphic(interconnection_line=hv_line)

    def create_graphic(self, interconnection_line=None):

        # Find the generic line graphic object
        self.line_generic_graphic = next(
            (obj for obj in self.graphic_list if obj.sSymNam == "d_lin"), None
        )

        try:
            # Get graphical elements from the generic line graphic
            graphic_elements_generic_line = self.line_generic_graphic.GetContents(
                "*.IntGrfcon"
            )
            coordinates = [-1 for _ in graphic_elements_generic_line[0].rX]

            # Create and set up the line graphic for the site
            line_site_graphic = self.grid_graphic_terminal.AddCopy(
                self.line_generic_graphic
            )
            line_site_graphic.pDataObj = interconnection_line

            # Define coordinates based on terminal rotation
            rotation = self.terminal_graphic.iRot
            if rotation in {0, 180}:
                line_site_graphic.rCenterX = self.terminal_graphic.rCenterX + 10
                line_site_graphic.rCenterY = self.terminal_graphic.rCenterY - 14

                line_site_graphic_elements = line_site_graphic.GetContents(
                    "*.IntGrfcon"
                )
                if len(line_site_graphic_elements) < 2:
                    line_site_graphic_elements.append(
                        line_site_graphic.AddCopy(line_site_graphic_elements[0])
                    )

                # Update coordinates
                coordinates[0] = self.terminal_graphic.rCenterX + 10
                coordinates[1] = self.terminal_graphic.rCenterX + 10
                line_site_graphic_elements[0].rX = coordinates

                coordinates[0] = self.terminal_graphic.rCenterY - 14
                coordinates[1] = self.terminal_graphic.rCenterY - 28
                line_site_graphic_elements[0].rY = coordinates

                coordinates[0] = self.terminal_graphic.rCenterX + 10
                coordinates[1] = self.terminal_graphic.rCenterX + 10
                line_site_graphic_elements[1].rX = coordinates

                coordinates[0] = self.terminal_graphic.rCenterY - 14
                coordinates[1] = self.terminal_graphic.rCenterY
                line_site_graphic_elements[1].rY = coordinates

            elif rotation in {90, 270}:
                line_site_graphic.rCenterX = self.terminal_graphic.rCenterX + 14
                line_site_graphic.rCenterY = self.terminal_graphic.rCenterY + 10

                line_site_graphic_elements = line_site_graphic.GetContents(
                    "*.IntGrfcon"
                )
                if len(line_site_graphic_elements) < 2:
                    line_site_graphic_elements.append(
                        line_site_graphic.AddCopy(line_site_graphic_elements[0])
                    )

                # Update coordinates
                coordinates[0] = self.terminal_graphic.rCenterX + 14
                coordinates[1] = self.terminal_graphic.rCenterX + 28
                line_site_graphic_elements[0].rX = coordinates

                coordinates[0] = self.terminal_graphic.rCenterY + 10
                coordinates[1] = self.terminal_graphic.rCenterY + 10
                line_site_graphic_elements[0].rY = coordinates

                coordinates[0] = self.terminal_graphic.rCenterX + 14
                coordinates[1] = self.terminal_graphic.rCenterX
                line_site_graphic_elements[1].rX = coordinates

                coordinates[0] = self.terminal_graphic.rCenterY + 10
                coordinates[1] = self.terminal_graphic.rCenterY + 10
                line_site_graphic_elements[1].rY = coordinates

            # Create and set up the site graphic
            site_graphic = self.grid_graphic_terminal.AddCopy(self.terminal_graphic)
            site_graphic.sSymNam = "SiteCirc"
            site_graphic.pDataObj = self.new_site
            site_graphic.rSizeX = 1
            site_graphic.rSizeY = 1

            if rotation in {0, 180}:
                site_graphic.rCenterX = self.terminal_graphic.rCenterX + 10
                site_graphic.rCenterY = self.terminal_graphic.rCenterY - 24
            elif rotation in {90, 270}:
                site_graphic.rCenterX = self.terminal_graphic.rCenterX + 24
                site_graphic.rCenterY = self.terminal_graphic.rCenterY + 10

            self.app.Rebuild(2)
            self.app.PrintPlain(
                f"A park '{self.new_site}' has been created successfully on the busbar: '{self.selection}'"
            )

        except Exception as e:
            self.app.PrintPlain(
                f"Exception in drawn of the site process: {e}. A propoerly interconnection is requiere"
            )

    def check_initial_selection(self):
        list_selection = self.app.GetDiagramSelection()
        if list_selection:
            self.selection = list_selection[0]
            type_select = self.selection.GetClassName()
            self.flag_graphic = 1
            if type_select == "ElmTerm":
                self.label_selection.configure(text=self.selection.loc_name)
                self.btn_scr.config(state=NORMAL)

            else:
                messagebox.showinfo(
                    "IBR Creator",
                    "Select a terminal or busbar element to perform the script",
                )


if __name__ == "__main__":
    user = user_tools.User("DefaultUser")
    app = user.start_powerfactory()

    root = Tk()
    tool = IBRCreator(root)
    root.mainloop()
