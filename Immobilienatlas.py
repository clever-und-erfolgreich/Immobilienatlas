import pandas as pd
import numpy as np
import altair as alt
from pandas._config.config import reset_option

import streamlit as st

### Read Dataframe and sperate Lat/Lon
df_PLZ_Stadt = pd.read_excel('PLZ-Stadt.xlsx', dtype={'Stadt': 'category', 'Postleitzahl': 'category'})
df_PLZ_Stadt[['Lat', 'Lon']] = df_PLZ_Stadt['LAT/LON'].str.split(';', expand=True)

df_PLZ_Stadt[['Lat', 'Lon']] = df_PLZ_Stadt[['Lat', 'Lon']].astype(float)

### Load second Dataframe with values
df_value = pd.read_excel('Immobilienmarktanalyse.xlsx', dtype={'Stadt': 'category', 'Postleitzahl': 'category', 'QM-Klasse': 'category', 'Zimmer': 'category'}, index_col='Unnamed: 0')

### Merge City Info and Value Info
df_value_coord = pd.merge(df_value, df_PLZ_Stadt, left_on=['Stadt', 'Postleitzahl'], right_on=['Stadt', 'Postleitzahl'])
df_value_coord['QM-Klasse'] = df_value_coord['QM-Klasse'].astype(str)
df_value_coord['Zimmer'] = df_value_coord['Zimmer'].astype(str)

df = df_value_coord[['Stadt', 'Postleitzahl', 'QM-Klasse', 'Zimmer', 'Miete/QM - QMK', 'Preis/QM - QMK', 'Rendite (%) - QMK', 'Miete/QM - QMK - R', 'Preis/QM - QMK - R', 'Rendite (%) - QMK - R']]
select_list = df['Stadt'].drop_duplicates().to_list()
select_list.sort()

###App
def main():
    """ Stock APP """
    ##General Settings
    st.beta_set_page_config(page_title='CLUE - Immobilienatlas', page_icon='logo.jpg')

    input = st.selectbox('Wähle deine Stadt aus', select_list)
    df_select = df[(df['Stadt'] == input)]

    ##Plotting
    #Scatter per City and zipcode
    scat_city = alt.Chart(df_select).mark_circle(size=60, clip=True, opacity=0.8).encode(
        alt.X('Preis/QM - QMK',
            scale=alt.Scale(domain=(df_select['Preis/QM - QMK'].min(), df_select['Preis/QM - QMK'].max())),
            title='Preis/QM'),
        alt.Y('Miete/QM - QMK',
            scale=alt.Scale(domain=(df_select['Miete/QM - QMK'].min(), df_select['Miete/QM - QMK'].max())),
            title='Miete/QM'),
            tooltip=['Postleitzahl', 'QM-Klasse', 'Miete/QM - QMK', 'Preis/QM - QMK', 'Rendite (%) - QMK'],
            size='Rendite (%) - QMK',
            color=alt.Color('Rendite (%) - QMK', scale=alt.Scale(scheme='redyellowgreen'), legend=alt.Legend(orient="top"))).interactive().properties(
                width=700, ##if HTML div has defined width: 100%, we can use container
                height=450
    )
    
    ##Table
    df_scatter = pd.DataFrame(df_select[['Postleitzahl', 'QM-Klasse', 'Miete/QM - QMK', 'Preis/QM - QMK', 'Rendite (%) - QMK']]).drop_duplicates()
    df_scatter.sort_values(by=['Rendite (%) - QMK'], inplace=True, ascending=False)
    df_scatter.reset_index(inplace=True)
    df_scatter.drop(columns=['index'], inplace=True)
    
    st.altair_chart(scat_city)
    
    left_col, right_col =st.beta_columns(2)
    with left_col:
        PLZ = st.text_input("Gib eine Postleitzahl ein, um danach zu filtern", "")
    
    if PLZ == '':
        plz_input = df_scatter
    else:
        plz_input = df_scatter[(df_scatter['Postleitzahl'] == PLZ)]

    with right_col:
        QMK = st.selectbox('Wähle eine QM-Klasse, um danach zu filtern', ['', 'bis 40 QM', '40 bis 60 QM', '60 bis 80 QM', '80 bis 100 QM', '100 bis 120 QM', 'ab 120 QM'])
    
    if QMK == '':
        qmk_input = plz_input
    else:
        qmk_input = plz_input[(plz_input['QM-Klasse'] == QMK)]

    st.table(qmk_input)

    
if __name__ == '__main__':
    main() 