import pandas as pd
import numpy as np
import altair as alt
from pandas._config.config import reset_option

import requests
from bs4 import BeautifulSoup as bs

import streamlit as st

from IPython.core.display import HTML

### Read Dataframe and sperate Lat/Lon
df_PLZ_Stadt = pd.read_excel('PLZ-Stadt.xlsx', dtype={'Stadt': 'category', 'Postleitzahl': 'category'})
df_PLZ_Stadt[['Lat', 'Lon']] = df_PLZ_Stadt['LAT/LON'].str.split(';', expand=True)

df_PLZ_Stadt[['Lat', 'Lon']] = df_PLZ_Stadt[['Lat', 'Lon']].astype(float)


### Create LAT/LON by City
lat_lon_max = df_PLZ_Stadt.groupby(['Stadt']).max().reset_index()
lat_lon_max[['Lat_max', 'Lon_max']] = lat_lon_max[['Lat', 'Lon']]
lat_lon_min = df_PLZ_Stadt.groupby(['Stadt']).min().reset_index()
lat_lon_min[['Lat_min', 'Lon_min']] = lat_lon_min[['Lat', 'Lon']]
lat_lon_df = pd.merge(lat_lon_max, lat_lon_min, left_on=['Stadt'], right_on='Stadt').drop(columns=['Lat_x', 'Lat_y', 'Lon_x', 'Lon_y', 'LAT/LON_x', 'LAT/LON_y']).drop_duplicates()

### Merge Dataframe with info of LAT/LON per city
PLZ_Stadt = pd.merge(df_PLZ_Stadt, lat_lon_df, left_on=['Stadt'], right_on=['Stadt']).drop(columns=['LAT/LON']).drop_duplicates()

### Load second Dataframe with values
df_value = pd.read_excel('Immobilienmarktanalyse.xlsx', dtype={'Stadt': 'category', 'Postleitzahl': 'category', 'QM-Klasse': 'category', 'Zimmer': 'category'}, index_col='Unnamed: 0')

### Merge City Info and Value Info
df_value_coord = pd.merge(df_value, PLZ_Stadt, left_on=['Stadt', 'Postleitzahl'], right_on=['Stadt', 'Postleitzahl'])
df_value_coord['QM-Klasse'] = df_value_coord['QM-Klasse'].astype(str)
df_value_coord['Zimmer'] = df_value_coord['Zimmer'].astype(str)

### Add center point off each city Lon/Lat
df_value_coord['Lon_City'] = (df_value_coord['Lon_max'] + df_value_coord['Lon_min']) / 2
df_value_coord['Lat_City'] = (df_value_coord['Lat_max'] + df_value_coord['Lat_min']) / 2

df_clt = pd.DataFrame(df_value_coord[['Stadt', 'Lon_City', 'Lat_City']])

df = df_value_coord[['Stadt', 'Postleitzahl', 'QM-Klasse', 'Zimmer', 'Miete/QM - QMK', 'Preis/QM - QMK', 'Rendite (%) - QMK', 'Miete/QM - QMK - R', 'Preis/QM - QMK - R', 'Rendite (%) - QMK - R']]
select_list = df['Stadt'].drop_duplicates().to_list()
select_list.sort()

###App
def main():
    """ Stock APP """
    ##General Settings
    st.beta_set_page_config(page_title='CLUE - Immobilienatlas', page_icon='logo.jpg')

    ## Hide Hamburger Menu
    hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
    st.markdown(hide_menu_style, unsafe_allow_html=True)

    ##Selectbox of city
    city = st.selectbox('Wähle deine Stadt aus', select_list, 0)
    df_select = df[(df['Stadt'] == city)]
    
    try:
        ### Get offers
        city_name = city
        city_Lon = format(df_clt['Lon_City'][(df_clt['Stadt'] == city_name)].drop_duplicates().values[0])
        city_Lat = format(df_clt['Lat_City'][(df_clt['Stadt'] == city_name)].drop_duplicates().values[0])

        offer = requests.get('https://www.realbest.de/immobiliensuche?realEstateType=CONDOMINIUM&scrollToResults=true&cityinput='+city_name+'%2C+Deutschland&longitude='+city_Lon+'&latitude='+city_Lat+'&searchRadius=FIFTEEN&searchParameters=true&cid=352040&afId=4mhZD105376')
        soup_offer = bs(offer.content, 'html.parser')
        content = soup_offer.body('td', {'class': 'details-with-more-columns'})

        ## Scraping PLZ und Stadt
        data_PLZ = soup_offer.body('span', {'class': 'address'})
        content_PLZ = pd.DataFrame(data_PLZ).astype(str)
        df_PLZ = pd.DataFrame(content_PLZ[0].str.split().to_list(), columns=[0,1,2,3]).drop(columns=[0, 1]).rename(columns={3: 'Stadt', 2: 'Postleitzahl'}).dropna().reset_index().drop(columns=['index'])

        ## Scraping Preis
        data_preis = soup_offer.body('strong')
        content_preis = pd.DataFrame(data_preis).astype(str)
        df_preis = pd.DataFrame(content_preis[0].str.split().to_list(), columns=[0,1,2,3]).drop(columns=[1,2,3]).rename(columns={0: 'Preis'})
        df_preis_1 = pd.DataFrame(df_preis['Preis'].str.replace('<strong>', '').apply(pd.to_numeric, errors='coerce').dropna()).reset_index().drop(columns=['index'])
        df_preis_final = df_preis_1[(df_preis_1['Preis'] > 100)].reset_index().drop(columns=['index']) * 1000

        ## Scraping QM
        data_qm = soup_offer.body('span', {'class': 'size'})
        content_qm = pd.DataFrame(data_qm).astype(str)
        df_qm = pd.DataFrame(content_qm[0].str.split().to_list(), columns=[0,1,]).rename(columns={0: 'QM'}).reset_index().drop(columns=[1, 'index']).dropna()

        ## Get Link
        data_link = soup_offer.body('a', {'type': 'submit'})
        content_link = pd.DataFrame(data_link).astype(str)
        df_link = pd.DataFrame(content_link[0].str.split('"').to_list())
        df_links = 'https://www.realbest.de' + df_link[[1,3]][(df_link[1] == 'hidden-print')].reset_index().drop(columns=['index', 1]).rename(columns={3: 'Link'}) + '&afId=4mhZD105376'

        ## Concat
        df_p_qm = pd.concat([df_PLZ, df_preis_final, df_qm, df_links], axis=1)
        df_p_qm['QM'] = df_p_qm['QM'].str.replace(',', '').astype(float) / 100
        df_p_qm['Preis/QM'] = round(df_p_qm['Preis'] / df_p_qm['QM'], 1)

        offer_1 = pd.merge(df_p_qm, df_value_coord[['Stadt', 'Postleitzahl', 'Miete/QM - PLZ']], left_on=['Stadt', 'Postleitzahl'], right_on=['Stadt', 'Postleitzahl']).drop_duplicates()
        offer_1['Erwartete Rendite (%)'] = round((offer_1['Miete/QM - PLZ'] * 12) / offer_1['Preis/QM'] * 100 , 2)
        offer_2 = offer_1.rename(columns={'Miete/QM - PLZ': 'Erwartete Miete/QM'}).drop(columns=['Stadt'])

        offer_3 = offer_2[['Postleitzahl', 'Preis', 'QM', 'Preis/QM', 'Erwartete Miete/QM', 'Erwartete Rendite (%)', 'Link']].reset_index().drop(columns=['index'])
        offer_3['Angebot'] = '<a href="' + offer_3['Link'] + '" target="_blank">Zum Angebot</a>'

        offer_4 = offer_3[['Postleitzahl', 'Preis', 'QM', 'Preis/QM', 'Erwartete Miete/QM', 'Erwartete Rendite (%)', 'Angebot']]
        html = offer_4.to_html(escape=False, index=False)
        tr = 1
    except:
        tr = 0

    ###Plotting
    #Scatter per City and zipcode
    st.success(city + ' - Preis und Miete je Qudratmeterklasse (QM-Klasse) und je Postleitzahl')

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
    df_scatter = pd.DataFrame(df_select[['Postleitzahl', 'QM-Klasse', 'Miete/QM - QMK', 'Preis/QM - QMK', 'Rendite (%) - QMK']]).drop_duplicates()
    df_scatter.sort_values(by=['Rendite (%) - QMK'], inplace=True, ascending=False)
    df_scatter.reset_index(inplace=True)
    df_scatter.drop(columns=['index'], inplace=True)
    
    st.altair_chart(scat_city)


    ## Angebote Tabelle
    if tr == 1:
        st.success('Aktuelle Angebote in - ' + city)
        st.markdown(html, unsafe_allow_html=True)
        st.text('')
    else:
        pass

    ##Table
    st.success('Details zur gewählten Stadt - ' + city)
    
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