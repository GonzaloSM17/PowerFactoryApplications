# %%

# // 
import my_libs.user_tools as user_tools
import my_libs.data_science as ds

import pandas as pd
import numpy as np
from difflib import get_close_matches

# Merging by tolerance
import pandas as pd
import numpy as np
from fuzzywuzzy import process

# %%

# //
# user = user_tools.User('Gonzalo')
scripting_path = user_tools.scripting_path()

file_name = 'Proyectos-en-Gestion-de-Conexiones-Declarados-en-Construccion-ene-25.xlsx'
file_path = f'{scripting_path}//src//data//2025_S1//{file_name}'
projects = ds.File(file_path)

file_name = 'Tablas-Declaracion-Construccion-Diciembre-2024_v0-scc.xlsx'
file_path = f'{scripting_path}//src//data//2025_S1//{file_name}'
under_build = ds.File(file_path)

file_name = 'DCSO_Todas las Obras_2025_S1.xlsx'
file_path = f'{scripting_path}//src//data//2025_S1//{file_name}'
dcso_all = ds.File(file_path)

# %%

# // Projects
projects_gx = ds.Dataframe(projects).load_dataframe(sheet_name='Gx_En Gestión', header=8)
projects_tx = ds.Dataframe(projects).load_dataframe(sheet_name='Tx_En Gestión', header=8)

projects_gx = ds.format_columns(projects_gx, transform_method='title').loc[:, ['Nup', 'Nombrlle_Proyecto', "Fechas_Estimada_De_Eo"]]
projects_tx = ds.format_columns(projects_tx, transform_method='title').loc[:, ['Nup', 'Nombre_Proyecto', "Fechas_Estimada_De_Eo"]]

# //
replacing_dicc = {
    'Nup': 'NUP',
    "Fechas_Estimada_De_Eo": "Fecha_EO"
}

projects_gx.columns = ds.replace_customized(projects_gx.columns, replacements=replacing_dicc)
projects_tx.columns = ds.replace_customized(projects_tx.columns, replacements=replacing_dicc)

projects_gx.columns = [col + '_PGP' for col in projects_gx.columns]
projects_tx.columns = [col + '_PGP' for col in projects_tx.columns]

replacing_tx = {
    'SE ': 'S/E '
}
projects_tx['Nombre_Proyecto_PGP'] = projects_tx['Nombre_Proyecto_PGP'].replace(replacing_tx)

# //
replacing_dicc_1 = {
    'Decreto Adjudicación': 'Decreto de Adjudicación',
    'Decreto Plan de Expansión': 'Decreto Plan de Expansión o Resolución Exenta CNE',
    'Fecha de entrada en operación según Decreto de Adjudicación': 'Fecha de entrada en operación según Decreto o Resolución Exenta',
    'Fecha estimada de Entrada en Operación según Decreto': 'Fecha de entrada en operación según Decreto o Resolución Exenta',
    'Fecha de Entrada en Operación según Decreto de Adjudicación': 'Fecha de entrada en operación según Decreto o Resolución Exenta',
    'Fecha estimada de Interconexión': 'Fecha de entrada en operación según Decreto o Resolución Exenta',
    'Propietario': 'Responsable' 
    }

replacing_dicc_2 = {
    'Decreto Adjudicación': 'Decreto de Adjudicación',
    'Resolución Exenta CNE': 'Decreto Plan de Expansión o Resolución Exenta CNE',
    'Fecha de entrada en operación según Resoluciones Exentas CNE':'Fecha de entrada en operación según Decreto o Resolución Exenta',
    'Propietario': 'Responsable' 
    }

# // Under Build
ub_gx = ds.Dataframe(under_build).load_dataframe(sheet_name='P.Generación', header=2, usecols='B:L')
ub_bess = ds.Dataframe(under_build).load_dataframe(sheet_name='BESS', header=2, usecols='B:P')
ub_pmgd = ds.Dataframe(under_build).load_dataframe(sheet_name='PMGD', header=2, usecols='B:L')

# // Following transmision projects
following_tx = ds.Dataframe(dcso_all).load_dataframe(sheet_name='Todas las obras', header=2, usecols='A:CL')

# %%

# // Transmission projects compile
ub_tx = pd.DataFrame()

for ub in under_build.sheets:
    condition1 = 'ON_STx' in ub or 'OA_STx' in ub
    condition2 = 'OPyM_ST' in ub
    condition3 = 'D418' in ub
    condition4 = 'Art.102' in ub

    if condition1:
        dataframe = ds.Dataframe(under_build).load_dataframe(sheet_name=ub, header=2, usecols='B:G')
        dataframe['Tipo'] = ub
        dataframe.columns = ds.replace_customized(dataframe.columns, replacements=replacing_dicc_1)
        ub_tx = pd.concat([ub_tx, dataframe], axis=0, ignore_index=False)
        
    elif condition2:
        dataframe = ds.Dataframe(under_build).load_dataframe(sheet_name=ub, header=2, usecols='B:H')
        dataframe['Tipo'] = ub
        dataframe.columns = ds.replace_customized(dataframe.columns, replacements=replacing_dicc_1)
        ub_tx = pd.concat([ub_tx, dataframe], axis=0, ignore_index=False)

    elif condition3:
        dataframe = ds.Dataframe(under_build).load_dataframe(sheet_name=ub, header=3, usecols='B:F')
        dataframe['Tipo'] = ub
        dataframe.columns = ds.replace_customized(dataframe.columns, replacements=replacing_dicc_1)
        ub_tx = pd.concat([ub_tx, dataframe], axis=0, ignore_index=False)

    elif condition4:
        dataframe = ds.Dataframe(under_build).load_dataframe(sheet_name=ub, header=2, usecols='B:F')
        dataframe['Tipo'] = ub
        dataframe.columns = ds.replace_customized(dataframe.columns, replacements=replacing_dicc_2)
        ub_tx = pd.concat([ub_tx, dataframe], axis=0, ignore_index=False)

ub_tx = ub_tx.dropna(subset=['Proyecto']).reset_index(drop=True)

# %%
        
# // Format
replacing_columns = {
    '_Dec_-': '_DeC_-',
    'Inteconexion': 'Interconexion' 
}        

ub_gx = ds.format_columns(ub_gx, transform_method='title')
ub_gx.columns = ds.replace_customized(ub_gx.columns, replacements=replacing_columns, standards_replacing=True)
ub_gx.columns = [col + '_DC' for col in ub_gx.columns]

ub_bess = ds.format_columns(ub_bess, transform_method='title')
ub_bess.columns = ds.replace_customized(ub_bess.columns, replacements=replacing_columns, standards_replacing=True)
ub_bess.columns = [col + '_DC' for col in ub_bess.columns]

ub_pmgd = ds.format_columns(ub_pmgd, transform_method='title')
ub_pmgd.columns = ds.replace_customized(ub_pmgd.columns, replacements=replacing_columns, standards_replacing=True)
ub_pmgd.columns = [col + '_DC' for col in ub_pmgd.columns]

ub_tx = ds.format_columns(ub_tx, transform_method='title')
ub_tx.columns = ds.replace_customized(ub_tx.columns, standards_replacing=True)
ub_tx.columns = [col + '_DC' for col in ub_tx.columns]

replacing_tx = {
    'SE ': 'S/E '
}
ub_tx['Proyecto_DC'] = ub_tx['Proyecto_DC'].replace(replacing_tx)


# // Following transmision projects
following_tx = following_tx.loc[:, ['NUP', 'Nombre de Obra', 'Decreto', 'Alcance del Proyecto', 'Estado de obra', 'Subestado de obra', 'Fecha término de obra', "Color (Desviación)"]]
following_tx = ds.format_columns(following_tx, transform_method='title')

replacing_tx = {
    'Nup'   : 'NUP',
    "_De_"  : "_de_",
    "_Del_" : "_del_",
    "Fecha_Termino_de_Obra" : "Fecha_TO",
    "Color_(Desviacion)": "Desviacion",
    
}

following_tx.columns = ds.replace_customized(following_tx.columns, replacements=replacing_tx, standards_replacing=True)
following_tx.columns = [col + '_SO' for col in following_tx.columns]

# %%

# // Some modificación to found more coincidences

# Transformaciones adicionales
tx_merge = ds.fuzzy_merge(ub_tx, projects_tx, left_on='Proyecto_DC', right_on='Nombre_Proyecto_PGP', threshold=90)
gx_merge = ds.fuzzy_merge(ub_gx, projects_gx, left_on='Proyecto_DC', right_on='Nombre_Proyecto_PGP', threshold=95)
bess_merge = ds.fuzzy_merge(ub_bess, projects_gx, left_on='Proyecto_DC', right_on='Nombre_Proyecto_PGP', threshold=95)

tx_merge = ds.fuzzy_merge(tx_merge, following_tx, left_on='Proyecto_DC', right_on='Nombre_de_Obra_SO', threshold=90)

# %%

# # // Date format fixing
# import locale
# locale.setlocale(locale.LC_TIME, 'es_ES.utf8')

# def date_format(in_dataframe, column):

#     condition = in_dataframe[column].isna() | (in_dataframe[column] == 'S/I')

#     to_formatted = in_dataframe[~condition].copy()
#     to_save = in_dataframe[condition].copy()

#     to_formatted[column] = pd.to_datetime(to_formatted[column], errors='coerce')
#     to_formatted[column] = to_formatted[column].dt.strftime('%B-%Y')

#     out_dataframe = pd.concat([to_formatted, to_save]).sort_index()

#     return out_dataframe

# tx_merge = date_format(tx_merge, 'Fecha_de_Entrada_En_Operacion_Segun_Decreto_o_Resolucion_Exenta')
# tx_merge = tx_merge.drop('Fecha_Estimada_de_Entrada_En_Operacion_Segun_CEN', axis='columns')

# gx_merge = date_format(gx_merge, 'Fecha_Original_de_Interconexion')
# gx_merge = date_format(gx_merge, 'Fecha_Estimada_de_Interconexion')

# bess_merge = date_format(bess_merge, 'Fecha_Original_de_Interconexion')
# bess_merge = date_format(bess_merge, 'Fecha_Estimada_de_Interconexion')

# # // Adding and deleting columns to fill in the process to check date or state
# tx_merge['Fecha_PGP'], tx_merge['Estado_Seguimiento'] = np.nan, np.nan
# gx_merge['Fecha_PGP'] = np.nan
# bess_merge['Fecha_PGP'] = np.nan

# tx_merge = tx_merge.drop('Nombre_Proyecto', axis='columns')
# gx_merge = gx_merge.drop('Nombre_Proyecto', axis='columns')
# bess_merge = bess_merge.drop('Nombre_Proyecto', axis='columns')

# %%

# // Create Excel Writer
out_file_name = "Proyectos_Compilados_2025S1.xlsx"
out_file_path = f'{scripting_path}//src//data//output//{out_file_name}'
xlwriter = pd.ExcelWriter(out_file_path, engine='xlsxwriter')

gx_merge.to_excel(excel_writer=xlwriter, sheet_name="Generación", index=False)
bess_merge.to_excel(excel_writer=xlwriter, sheet_name="Almacenamiento", index=False)
tx_merge.to_excel(excel_writer=xlwriter, sheet_name="Transmisión", index=False)
ub_pmgd.to_excel(excel_writer=xlwriter, sheet_name="PMGD", index=False)

projects_tx.to_excel(excel_writer=xlwriter, sheet_name="NUP Generación", index=False)
projects_gx.to_excel(excel_writer=xlwriter, sheet_name="NUP Transmisión", index=False)

# Save and close the Excel Writer
xlwriter.close()

# %%
