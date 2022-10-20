import streamlit as st
import pandas as pd
import folium
from folium import FeatureGroup
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from geopy.distance import distance
import openrouteservice
from openrouteservice import convert
import datetime
from folium.plugins import BeautifyIcon
import io

from folium.plugins import BeautifyIcon
st.set_page_config(layout="wide", page_title="Route Optimizer", page_icon="📫")
st.markdown("# Point-to-point Route Optimizer")
st.markdown(f"Outlet data updated manually at __{datetime.datetime(2022,10,17).strftime('%Y-%m-%d')}__")

local_files = "data/Data_Outlet.xlsx"

@st.cache(allow_output_mutation=True)
def get_outlet_data(path):
    # read the file
    df =  pd.read_excel(path)
    # filter non-null values
    df =  df.loc[df["Last Transaction Date"].notnull()].copy()
    # slicing dataframe
    df =  df.loc[df["Google Maps"].notnull(), ["ID Merchant", "Nama Outlet", "Kota Outlet", "Provinsi Outlet","Google Maps"]].copy()
    # extracting longitude from Google Maps URL
    df["longitude"] = df['Google Maps'].str.split(",", expand=True)[1]
    # extracting longitude from Google Maps URL
    df["latitude"] = df['Google Maps'].str.split(",", expand=True)[0].str.split("=", expand=True)[1]
    # convert latitude and longitude into integer values
    df["latitude"] = pd.to_numeric(df["latitude"], errors='coerce')
    df["longitude"] = pd.to_numeric(df["longitude"], errors='coerce')
    # lowering columns' name
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    # final slicing, get rid of null values of longitude and latitude
    df = df.loc[(df["longitude"].notnull()) & (df["latitude"].notnull())].copy()

    # adding new columns (for openrouteservice api compatibility)
    df["needed_amount"] = 1
    df["open"] = datetime.datetime.today().replace(hour=8, minute=0, second=0)
    df["close"] = datetime.datetime.today().replace(hour=20, minute=0, second=0)

    return df

# run get_outlet_data
dataframe = get_outlet_data(local_files)


######################### FIRST select on sidebar
with st.sidebar:
    # city (multiple)
    select_city = st.multiselect(label="Select city", options=dataframe["kota_outlet"].unique().tolist(), default="Kota Jakarta Selatan", help="You can select multiple, but please select as minimum as possible to optimize the results")

############ SESSION STATE ############
# initiate session_state for select_city
if "city" not in st.session_state:
    st.session_state["city"] = select_city

# submit button to submit the changes in sidebar
with st.sidebar:
    submit_city = st.button("Change city")

    
# when submit button is clicked
if submit_city:
    st.session_state["city"] = select_city

############## TITLE #################
st.subheader("Data Outlet based on City You Selected")
st.markdown("You can scroll, view, or search the outlets' name here and paste it into ___Select Outlet___ filter on the sidebar")
st.dataframe(dataframe.loc[dataframe["kota_outlet"].isin(st.session_state["city"])])    
    

######################### SECOND select on sidebar
with st.sidebar:
    # outlet (multiple)
    select_outlet = st.multiselect(
        label="Select outlet",
        options=dataframe.loc[dataframe["kota_outlet"].isin(st.session_state["city"]), "nama_outlet"].unique().tolist(),
        help="Please select multiple outlets to run your trip, we suggest up to 20 outlets only per search"
    )

############ SESSION STATE ############
# initiate session_state for select_outlet
if "outlet" not in st.session_state:
    st.session_state["outlet"] = select_outlet

# submit button to submit the changes in sidebar
with st.sidebar:
    submit_outlet = st.button("Change outlet")

# when submit button is clicked
if submit_outlet:
    st.session_state["outlet"] = select_outlet


############## TITLE #################
if len(st.session_state["outlet"]) > 0:

    st.subheader("You've Selected Outlets Below")
    st.markdown("Make sure you select corectly number of outlets on the sidebar")
    st.dataframe(dataframe.loc[(dataframe["kota_outlet"].isin(st.session_state["city"])) &
        (dataframe["nama_outlet"].isin(st.session_state["outlet"]))]
    )    
else:
    st.warning("You have no outlets selected, please select first.")



######################### THIRD select on sidebar
with st.sidebar:
    # tutorial on how to find out longitude and latitude
    url = "https://tekno.kompas.com/read/2022/06/05/17150037/cara-cari-longitude-dan-latitude-di-google-maps-buat-isi-data-alamat"
    # center point
    input_latitude = st.number_input(label="Input latitude of start point", help="Example format: -6.xxxxxxx")
    input_longitude = st.number_input(label="Input longitude of start point", help="Example format: 10x.xxxxxxx")
    # clickable link
    st.markdown("_How to find out longitude and latitude [here](%s)_" % url)


############ SESSION STATE ############
# initiate session_state for input_longitude and input_latitude
if "longitude" not in st.session_state:
    st.session_state["longitude"] = input_longitude

if "latitude" not in st.session_state:
    st.session_state["latitude"] = input_latitude

# submit button to submit the changes in sidebar
with st.sidebar:
    submit_start = st.button("Change start point")

# when submit button is clicked
if submit_start:
    st.session_state["longitude"] = input_longitude
    st.session_state["latitude"] = input_latitude

################# POST BUTTON TO CALL OPENROUTESERVICE API ##############
if len(st.session_state["outlet"]) > 0 and  st.session_state["longitude"] != 0 and st.session_state["latitude"] != 0:
    post_ors_api = st.sidebar.button("Run route optimizer")
else:
    st.sidebar.markdown("Please select outlet and start point to run route optimizer")



################# FUNNCTION TO CALL OPENROUTESERVICE API ##############

def get_vehicle():
    # Define the vehicles (how many canvassers are)
    # https://openrouteservice-py.readthedocs.io/en/latest/openrouteservice.html#openrouteservice.optimization.Vehicle
    vehicles = list()
    for idx in range(1):
        vehicles.append(
            openrouteservice.optimization.Vehicle(
                id=idx,
                # start point
                start=[st.session_state["longitude"], st.session_state["latitude"]],
                # len of outlets
                capacity=[len(st.session_state["outlet"])+2],
                time_window=[int(datetime.datetime.today().replace(hour=8, minute=0, second=0).timestamp()),
                            int(datetime.datetime.today().replace(hour=20, minute=0, second=0).timestamp())]
            )
        )
    return vehicles


def get_delivery():   
    # Next define the delivery stations
    # https://openrouteservice-py.readthedocs.io/en/latest/openrouteservice.html#openrouteservice.optimization.Job
    deliveries = list()
    for delivery in dataframe.loc[(dataframe["kota_outlet"].isin(st.session_state["city"])) & (dataframe["nama_outlet"].isin(st.session_state["outlet"]))].itertuples():
        deliveries.append(
            openrouteservice.optimization.Job(
                id=delivery.Index,
                location=[delivery.longitude, delivery.latitude],
                service=1200,
                amount=[delivery.needed_amount],
                time_windows=[[int(delivery.open.timestamp()), int(delivery.close.timestamp())]]
            )
        )

    return deliveries
    

def get_optimizer():
    # Initialize a client and make the request
    ors_client = openrouteservice.Client(key='5b3ce3597851110001cf6248f903a2eb28b04234bcb4b7ada2ccf7c3')  # Get an API key from https://openrouteservice.org/dev/#/signup
    result = ors_client.optimization(
        jobs=get_delivery(),
        vehicles=get_vehicle(),
        geometry=True
    )

    return result


##### CONDITIONS TO CALL FUNCTION#####
if len(st.session_state["outlet"]) > 0 and  st.session_state["longitude"] != 0 and st.session_state["latitude"] != 0:
    if post_ors_api:
        try:
            result = get_optimizer()
            if result:
                # create list of extracted result
                stations = list()
                for route in result['routes']:
                    vehicle = list()
                    for step in route["steps"]:
                        vehicle.append([
                                step.get("job", "Center/Start"),  # Station ID
                                step["arrival"],  # Arrival time
                                step["arrival"] + step.get("service", 0),  # Departure time
                                step["location"],
                                step["distance"],
                                step["duration"]
                            ])
                    stations.append(vehicle)
                
                # create dataframe
                df_stations = pd.DataFrame(stations[0], columns=["Station ID", "Arrival", "Departure", "Location", "Distance", "Duration"])
                df_stations['Arrival'] = pd.to_datetime(df_stations['Arrival'], unit='s')
                df_stations['Departure'] = pd.to_datetime(df_stations['Departure'], unit='s')
                df_stations["Distance to Previous"] = df_stations["Distance"] - df_stations["Distance"].shift(periods=1, fill_value=0)
                df_stations["Duration to Previous"] = df_stations["Duration"] - df_stations["Duration"].shift(periods=1, fill_value=0)
                
                # merge filtered dataframe and df_stations to get nama_outlet and google_maps link
                df_merged = pd.merge(
                    df_stations,
                    dataframe.loc[(dataframe["kota_outlet"].isin(st.session_state["city"])) & (dataframe["nama_outlet"].isin(st.session_state["outlet"])), ["nama_outlet", "google_maps"]],
                    how="outer", 
                    left_on="Station ID", 
                    right_index=True
                )
            
                # # rename columns' name
                df_merged.columns = df_merged.columns.str.lower().str.replace(" ", "_")
                df_merged_clean = df_merged.loc[df_merged["duration"].notnull()].copy()

                # # start to show the maps
                m = folium.Map(location=[st.session_state["latitude"], st.session_state["longitude"]], zoom_start=10, tiles='cartodbpositron')
                
                # # Plot the locations on the map with more info in the ToolTip
                for location in df_merged_clean.itertuples():
                    tooltip = folium.map.Tooltip("Merchant: {}".format(location.nama_outlet))
                    popup=folium.map.Popup(f"Distance to Previous: {location.distance_to_previous/1000:.2f} km <br> Duration to Previous: {location.duration_to_previous/60:.2f} minutes <br> Maps URL: <a href={location.google_maps}>{location.google_maps}</a>")
                    
                    folium.Marker(
                        location=list(reversed(location.location)),
                        tooltip=tooltip,
                        popup=popup,
                        icon=BeautifyIcon(
                            icon_shape='marker',
                            number=int(location.Index),
                            spin=True,
                            text_color='red',
                            background_color="#FFF",
                            inner_icon_style="font-size:12px;padding-top:-5px;"
                        )
                    ).add_to(m)

                

                # # plot start point
                folium.Marker(
                    location=[st.session_state["latitude"], st.session_state["longitude"]],
                    icon=folium.Icon(color="green", icon="bus", prefix='fa'),
                    setZIndexOffset=1000,tooltip="Start Point"
                ).add_to(m)

                

                # add geometry distance
                for color, route in zip(['green', 'red', 'blue'], result['routes']):
                    decoded = convert.decode_polyline(route['geometry'])  # Route geometry is encoded
                    gj = folium.GeoJson(
                        name='Vehicle {}'.format(route['vehicle']),
                        data={"type": "FeatureCollection", "features": [{"type": "Feature",
                                                                        "geometry": decoded,
                                                                        "properties": {"color": color}
                                                                        }]},
                        style_function=lambda x: {"color": x['properties']['color']}
                    )
                    gj.add_to(m)
                folium.LayerControl().add_to(m)

                # title
                st.subheader("The Generated Routes in Order")

                # showing the maps using streamlit_folium
                folium_static(m, width=900, height=600)

                # check the length of the dataframe to find out invalid longitude and latitude
                if len(st.session_state["outlet"])+1 != len(df_stations):
                    st.markdown("There are invalid data of selected outlet (longitude and latitude). The number of generated routes are decreased from its origin.")
                    st.markdown("__Invalid Data Shown Below__")
                    st.dataframe(df_merged.loc[df_merged["duration"].isnull()])
                else:
                    st.success("All generated data are valid")

                # showing the final dataframe
                st.subheader("Downloadable Data")
                st.markdown("Please download the data to save it offline")

                # add url link to columns
                df_merged_clean["google_maps_url"] = df_merged_clean["google_maps"].apply(lambda x: f'<a href={x}">{x}</a>')

                # slicing the important columns
                df_merged_clean_linked = df_merged_clean.loc[:, ["nama_outlet", "google_maps_url", "duration_to_previous", "distance_to_previous"]].copy()
                
                # change unit in duration
                df_merged_clean_linked['duration_to_previous'] = df_merged_clean_linked['duration_to_previous']/60
                df_merged_clean_linked['duration_to_previous'] = df_merged_clean_linked['duration_to_previous'].round(2)

                # change unit in distance
                df_merged_clean_linked['distance_to_previous'] = df_merged_clean_linked['distance_to_previous']/1000
                df_merged_clean_linked['distance_to_previous'] = df_merged_clean_linked['distance_to_previous'].round(2)

                # rename columns
                df_merged_clean_linked.columns = ["nama_outlet", "google_maps_url", "duration_to_previous_in_minutes", "distance_to_previous_in_km"]
                # convert to HTML
                df_link = df_merged_clean_linked.copy().to_html(escape=False)
                # show the HTML
                st.write(df_link, unsafe_allow_html=True)

                # download the dataframe
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    # Write excel with single worksheet
                    df_merged_clean_linked.to_excel(writer, index=False)
                    # Close the Pandas Excel writer and output the Excel file to the buffer
                    writer.save()

                    # assign file to download button
                    st.download_button(
                        label="Download Data in Excel",
                        data=buffer,
                        file_name=f"optimized_routes{datetime.datetime.now().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                )

        except:
            st.markdown("There was an error when trying to call openrouteservice API. Please try again and make sure press __Run Optimizer__ first.")
    else:
        st.markdown("There was an error when trying to call openrouteservice API. Please try again by inputting correctly.")
else:
    st.warning("You're not able to run until you have selected outlet and start point corectly")

