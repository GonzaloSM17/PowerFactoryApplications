# %%

"""
Script generador de condesandores sincrónicos

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


class SCCreator:

    # Initial coordinates
    padx, pady = 5, 3

    def __init__(self, master):
        self.master = master
        self.initialize_variables()
        self.create_widgets()
        self.check_initial_selection()

    def initialize_variables(self):
        self.technology = {
            "Synchronous Condenser": [""],
        }

        self.suffix = {"Synchronous Condenser": "CS"}

        self.models = {
            "Synchronous Condenser": "SC_Model",
        }

        # Simulating the app object
        self.app = app  # Change this to actual app object if available
        # self.app = pf.GetApplication()
        self.selection = None
        self.flag_graphic = None

    def about(self):
        messagebox.showinfo("Synchronous Condenser Creator", "by DEE")

    def create_widgets(self, padx=padx, pady=pady):
        self.master.title("SC Creator")
        self.master.geometry("700x400")
        self.master.resizable(0, 0)
        self.master.attributes("-topmost", True)

        # General labels
        Label(self.master, text="Machine Configuration:", anchor="w").grid(
            row=0, column=0, padx=padx, pady=pady, sticky="w"
        )

        # About button
        self.btn_about = Button(self.master, text="About...", command=self.about)
        self.btn_about.grid(row=0, column=3, padx=padx, pady=pady, sticky="e")

        # Name
        Label(self.master, text="Name:", anchor="w").grid(
            row=1, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_name = StringVar(self.master, value="Name synchronous condenser")
        self.entry_name = Entry(self.master, textvariable=self.variable_name, width=30)
        self.entry_name.grid(row=1, column=1, padx=padx, pady=pady, sticky="w")

        # Technology
        Label(self.master, text="Technology:", anchor="w").grid(
            row=2, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.combo_technology = Combobox(
            self.master, state="readonly", values=list(self.technology.keys()), width=30
        )
        self.combo_technology.current(0)
        # self.combo_technology.bind("<<ComboboxSelected>>", self.update_subcategories)
        self.combo_technology.grid(row=2, column=1, padx=padx, pady=pady, sticky="w")

        # Capacity
        Label(self.master, text="Capacity:", anchor="w").grid(
            row=4, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_capacity = IntVar(self.master, value=100)
        Entry(self.master, textvariable=self.variable_capacity, justify=RIGHT).grid(
            row=4, column=1, padx=padx, pady=pady, sticky="w"
        )
        Label(self.master, text="MVA", anchor="w").grid(
            row=4, column=2, padx=padx, pady=pady, sticky="w"
        )

        # Caution
        Label(
            self.master,
            text="Caution: Do not exceed 135 MVA, as this corresponds to the capacity of the base machine.",
            anchor="w",
        ).grid(row=5, column=1, columnspan=5, padx=padx, pady=pady, sticky="w")
        # ...

        # Parallel machines
        Label(self.master, text="Parallel units:", anchor="w").grid(
            row=6, column=0, padx=padx, pady=pady, sticky="w"
        )
        self.variable_parallel = IntVar(self.master, value=1)
        Entry(self.master, textvariable=self.variable_parallel, justify=RIGHT).grid(
            row=6, column=1, padx=padx, pady=pady, sticky="w"
        )
        Label(self.master, text="-", anchor="w").grid(
            row=6, column=2, padx=padx, pady=pady, sticky="w"
        )

        # Busbar or tap off selection
        Label(self.master, text="Connection:", anchor="w").grid(
            row=7, column=0, padx=padx, pady=pady, sticky="w"
        )

        self.label_selection = Label(self.master, text="-", anchor="w")
        self.label_selection.grid(row=7, column=1, padx=padx, pady=pady, sticky="w")

        # Selecting button (Busbar or section of line)
        Button(self.master, text="Select...", command=self.busbar_select).grid(
            row=7, column=3, padx=padx, pady=pady, sticky="e"
        )

        # SCR
        self.label_scl = Label(self.master, text=f'(S"k = - MVA)', anchor="w")
        self.label_scl.grid(row=8, column=1, padx=padx, pady=pady, sticky="w")

        self.btn_scr = Button(
            self.master, text="Calculate", command=self.calculate_SCR, state=DISABLED
        )
        self.btn_scr.grid(row=9, column=3, padx=padx, pady=pady, sticky="e")

        # Create
        self.btn_create = Button(
            self.master, text="Create Park", command=self.create, state=DISABLED
        )
        self.btn_create.grid(
            row=10, column=1, columnspan=3, padx=padx, pady=pady, sticky="we"
        )

    def busbar_select(self):
        self.terminals = self.app.GetCalcRelevantObjects("*.ElmTerm")
        bus_selection = self.app.ShowModalSelectBrowser(self.terminals, "", "", "")

        self.selection = bus_selection[-1]

        self.flag_graphic = 2
        self.selection.MarkInGraphics(1)
        self.label_selection.configure(text=self.selection.loc_name)
        self.btn_scr.config(state=NORMAL)

    def calculate_SCR(self):
        capacity = self.variable_capacity.get()
        no_parallel = self.variable_parallel.get()

        xd = 0.0972
        x_transformer = 0.08
        x_subtransient = xd + (x_transformer / (1.1))

        self.scl_value = no_parallel * (capacity / x_subtransient)
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
        messagebox.showinfo("SynchronousCondenserCreator", "Park successfully created")
        self.master.destroy()

    def create_park(self):
        # Park Configuration
        technology = self.combo_technology.get()
        template_name = self.models[technology]
        suffix = self.suffix[technology]

        sc_name = self.variable_name.get()
        sc_name = f"{suffix}_{sc_name}"

        capacity = self.variable_capacity.get()
        no_parallel = self.variable_parallel.get()

        # Create Site
        self.new_site = self.grid.CreateObject("ElmSite", sc_name)

        # Importing template
        templates = self.app.GetProjectFolder("templ").GetContents(
            "SC_Model_T*.IntFolder"
        )[-1]
        template = templates.GetContents(f"{template_name}.IntTemplate")[-1]

        # Template components
        components = template.GetContents(
            "*.ElmTr2,*.ElmSym,*.ElmTerm,*.ElmLne,*.ElmStactrl,*.ElmNec,*.ElmComp"
        )
        graphic_template = template.GetContents("*.IntGrfnet")[-1]

        # Rename elements
        for element in self.new_site.GetContents():
            element.loc_name = f"{element.loc_name}_{sc_name}"

        # Copy template diagram (Graphical objects) in folder of the project
        diagram = self.graphic_folder.PasteCopy(graphic_template)[-1]
        self.new_site.pDiagram, diagram.loc_name = diagram, sc_name

        # Associate of the graphic object (diagram) to the elements in site
        site_elements = self.new_site.AddCopy(components).GetContents(
            "*.ElmTr2,*.ElmSym,*.ElmTerm,*.ElmLne,*.ElmStactrl,*.ElmNec,*.ElmComp"
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
            if element.GetClassName() in {"ElmSym", "ElmTr2", "ElmLne"}:
                for equipment in equipments:
                    if element.typ_id.loc_name == equipment.loc_name:
                        element.typ_id = equipment

        # Generator settings
        generator = self.new_site.GetContents("*.ElmSym")[-1]

        generator.av_mode = "constq"
        generator.typ_id.sgn = 1.0 * capacity
        generator.P_max = capacity
        generator.Pmax_uc = generator.Pmax_ucPU = 0
        generator.pmaxratf = 1
        generator.pgini = 0
        generator.qgini = 0
        generator.ngnum = no_parallel

        try:
            operational = self.new_site.GetContents("Library")[-1].GetContents(
                "Operational*.IntFolder"
            )[-1]
            curves = operational.GetContents("MVAr*.IntFolder")[-1]
            generator.pQlimType = curves.GetContents("*.IntQlim")[-1]

        except Exception as e:
            self.app.PrintPlain(f"Exception in curve setting: {e}. There is not curve")

        # Interconnection of the project and high voltage line settings
        self.cubicle_terminal = self.terminal.CreateObject("StaCubic", "Cub_SC")
        hv_line = self.new_site.GetContents("LAT*.ElmLne")[-1]

        hv_line.bus2 = self.cubicle_terminal
        nominal_voltage = self.selection.GetAttribute("e:uknom")
        hv_line.typ_id.uline = nominal_voltage
        hv_line.typ_id.InomAir = capacity * hv_line.typ_id.InomAir / 110.0
        hv_line.typ_id.sline = capacity * hv_line.typ_id.sline / 110.0
        hv_line.nlnum = no_parallel

        cubicle_pcc = hv_line.bus1
        busbar_pcc = cubicle_pcc.GetParent()
        busbar_pcc.uknom = nominal_voltage

        # Transformer HV/MV setting
        transformer_hvmv = self.new_site.GetContents("TR*.ElmTr2")[-1]
        transformer_hvmv.typ_id.utrn_h = nominal_voltage
        transformer_hvmv.typ_id.strn = capacity * 1.1
        transformer_hvmv.typ_id.uktr = 10
        transformer_hvmv.typ_id.xtor = 20
        transformer_hvmv.ntnum = no_parallel

        # Rename elements
        for element in self.new_site.GetContents():
            if element.GetClassName() in {"ElmSym"}:
                element.loc_name = sc_name
            else:
                element.loc_name = f"{element.loc_name}_{sc_name}"

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
    tool = SCCreator(root)
    root.mainloop()
