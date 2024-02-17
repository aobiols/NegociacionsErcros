import pandas as pd
import streamlit as st
import numpy as np
import streamlit_highcharts as hg
import datetime
import glob
import os

import_minim = 1000
import_minim_parcial = 15000
import_maxim = 150000


@st.cache_data
def llegeix_i_filtra_dades(ticker):
    print("LLEGINT DADES ................")

    # LLegim les dades de tots els anys que tinguem ordenades
    all_files = glob.glob(os.path.join('.\\dades', "operacions_" + ticker + "*.csv"))
    df = pd.concat((pd.read_csv(f) for f in sorted(all_files)), ignore_index=True)

    # Afegim columna amb l'import de l'operacio
    df['Import'] = df['Volum'] * df['Preu']

    # Filtrem les dades
    #  Que la Venue sigui Null i que l'operació sigui C o V
    df = df[((df['Import'] >= import_minim) & ((df['Operacio'] == 'C') | (df['Operacio'] == 'V')))]

    # Afegim la columna de datetime
    df['dia_hora'] = df['Dia'] + ' ' + df['Hora']
    df['datetime'] = pd.to_datetime(df['dia_hora'], format="%d/%m/%y %H:%M:%S")

    # Resetegem l'index
    df.reset_index(inplace=True)
    # Afegim el volum d'accions amb signe per poder saber quantes se n'han comp
    df['Signe'] = np.where(df['Operacio'] == 'C', 1, -1)
    df['Volum_signe'] = df['Volum'] * df['Signe']

    import_maxim_slider = int(df['Import'].max())

    return df, import_maxim_slider


# --------------------------------------------------------------------------------------------
def main(df_principal, import_maxim_main):
    st.title('ERCROS')

    st.sidebar.title("Filtros")

    filtre_import = st.sidebar.slider('Importe', import_minim, import_maxim_main, (import_minim_parcial,
                                                                                   import_maxim_main), format='%d EUR')

    # FILTRE PER LES DATES
    format_data = 'DD/MM/YY'
    data_inicial_tot = datetime.date(2022, 1, 1)
    data_inicial_parcial = datetime.date(2023, 1, 1)
    # data_final = dt.datetime.now().date()
    data_final = df_principal['datetime'].max().date()
    filtre_dates = st.sidebar.slider('Rango de fechas', data_inicial_tot, data_final,
                                     (data_inicial_parcial, data_final), format=format_data)
    data_maxima = np.datetime64(filtre_dates[1]) + np.timedelta64(1, 'D')
    mask_dates = (df_principal['datetime'] >= np.datetime64(filtre_dates[0])) & (
                df_principal['datetime'] <= data_maxima)
    df_principal = df_principal.loc[mask_dates]

    # FILTRE PELA IMPORTS
    df_principal = df_principal[df_principal['Import'].between(filtre_import[0], filtre_import[1])]

    # Calculem la Suma acumulada segons els filtres
    df_principal['Cumsum_volum'] = df_principal['Volum_signe'].cumsum()

    # PREPAREM en un altre dataframe les dades que es pintaran a la gràfica
    df_a_pintar = df_principal[['datetime', 'Cumsum_volum', 'Preu']]
    df_a_pintar = df_a_pintar.set_index('datetime')

    # GRÀFICA AMB HIGHCHARTS
    columna_data_np = df_a_pintar.index.values.astype(np.int64) / 1000000
    columna_data = columna_data_np.tolist()
    columna_valor_cumsum = df_a_pintar["Cumsum_volum"].to_numpy().tolist()
    combined = np.vstack((columna_data, columna_valor_cumsum)).T.tolist()

    columna_preu = df_a_pintar["Preu"].to_numpy().tolist()
    combined2 = np.vstack((columna_data, columna_preu)).T.tolist()

    grafica = {
        'series': [{'data': combined, 'name': 'Acumulado'},
                   {'data': combined2, 'name': 'Precio',
                    'tooltip': {'valueSuffix': ' EUR'},
                    'yAxis': 1, }],
        'xAxis': {
            'type': 'datetime',
        },
        'title': {'text': 'Negociaciones por volumen vs Precio'},
        'yAxis': [{'title': {'text': 'Acumulado'}},
                  {'title': {'text': 'Precio'}, 'opposite': True}]
    }

    hg.streamlit_highcharts(grafica, 640)

    #################################################
    # La taula de baix

    df_principal = df_principal[['Dia', 'Hora', 'Preu', 'Volum', 'Import', 'Operacio', 'Cumsum_volum']]
    df_principal.columns = ['Dia', 'Hora', 'Precio', 'Volumen', 'Importe', 'Operación', 'Acumulado']

    df_principal['Hora'] = df_principal['Hora'].str[:8]

    # ATENCIO STYLE NOMES ES POT APLICAR UN SOL COP , O COLOR O FORMAT !!!

    df_principal = df_principal.style.format({'Precio': '{:.2f}', 'Importe': '{:,.0f} EUR'})
    st.dataframe(df_principal, hide_index=True, use_container_width=True)

    # def highlight_survived(s):
    #    return ['background-color: green'] * len(s) if s.Import>15000 else ['background-color: red'] * len(s)

    # st.dataframe(df_sencer.style.apply(highlight_survived, axis=1), hide_index=True, use_container_width=True)

    #################################################

    st.sidebar.title("\n")
    st.sidebar.info('\n\nEstudio de las negociaciones de Ercros para los compañeros de Nemer'
                    '\n\n Mètodo usado:'
                    '\n 1) Obtención de los cruces desde 1/1/2022 en la Bolsa de Madrid'
                    '\n 2) La primera i la última negociacion del dia se consideran Subasta Inicial i Final (No '
                    'cuentan)'
                    '\n 3) Si el precio de la acción sube, consideramos que ha entrado una operación de Compra'
                    '\n 4) Si el precio de la acción baja, consideramos que ha entrado una operación de Venta'
                    '\n 5) Si el precio de la acción se mantiene, consideramos que continua la operación Anterior'
                    '\n 6) Si es una compra sumamos el número de acciones al acumulado i si es una venta lo restamos'
                    '\n \n La idea es saber si hay una relacion entre las "grandes" compras/ventas y lo que sucederá '
                    'en un futuro')


if __name__ == '__main__':
    asset = 'ECRe'
    df_sencer, import_maxim = llegeix_i_filtra_dades(asset)

    main(df_sencer, import_maxim)
