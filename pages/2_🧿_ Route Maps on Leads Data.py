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
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

st.set_page_config(layout="wide", page_title="Route Optimizer", page_icon="🎭")
st.markdown("# Route Optimizer on CRM's Leads Data")
st.markdown(f"Outlet data updated manually at __{datetime.datetime(2022,10,21).strftime('%Y-%m-%d')}__")

local_files = "data/Data_Canvassing.csv"
visited_csv_file = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4FF4XSyOvwczZv-sSWnCv4jLBy7X8WXC275TslSnagbUCJCQ6i0PnlvlP5kC0E6q0FnXiPh0HK_ED/pub?output=csv"

@st.cache(allow_output_mutation=True)
def get_outlet_data(path):
    df =  pd.read_csv(path)
    # adding new columns (for openrouteservice api compatibility)
    df["needed_amount"] = 1
    
    # adding new column of google maps url
    df["google_maps"] = df.apply(lambda row: "https://www.google.com/maps/?q=" + str(row["outlet_langitude"]) + "," + str(row["outlet_longitude"]), axis=1)

    # phone number formatting
    df["pic_phone"] = df["pic_phone"].astype("category")

    return df

# run get_outlet_data
dataframe = get_outlet_data(local_files)

# auto filter function
def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

####################### EXPLORE THE DATAFRAME #################
st.subheader("Explore Data Here")
st.markdown("##### Before inputting into sidebar, please explore data below by filtering out")
st.dataframe(filter_dataframe(dataframe))


######################## SIDEBAR PART 1 ###############################
st.sidebar.markdown("#### Outlet Selection Section")
############ SELECT PROVINCE ############
select_province = st.sidebar.multiselect(label="Select province", options=dataframe["m_province_name"].unique().tolist(), default="DKI JAKARTA", help="You can select multiple, but please select as minimum as possible to optimize the results")
# initiate session_state for select_province
if "province" not in st.session_state:
    st.session_state["province"] = select_province

# button
submit_province = st.sidebar.button("Change province")
# button is clicked
if submit_province:
    st.session_state["province"] = select_province



############ SELECT CITY ############
select_city = st.sidebar.multiselect(label="Select city", options=dataframe.loc[dataframe["m_province_name"].isin(st.session_state["province"]), "m_regency_name"].unique().tolist(), default="KOTA JAKARTA SELATAN", help="You can select multiple, but please select as minimum as possible to optimize the results")
# initiate session_state for select_city
if "city" not in st.session_state:
    st.session_state["city"] = select_city

# button
submit_city = st.sidebar.button("Change city")
# button is clicked
if submit_city:
    st.session_state["city"] = select_city



############ SELECT DISTRICT ############
select_district = st.sidebar.multiselect(label="Select district", options=dataframe.loc[(dataframe["m_province_name"].isin(st.session_state["province"])) & (dataframe["m_regency_name"].isin(st.session_state["city"])), "m_district_name"].unique().tolist(), 
    default="KEBAYORAN BARU", 
    help="You can select multiple, but please select as minimum as possible to optimize the results"
)

# initiate session_state for select_district
if "district" not in st.session_state:
    st.session_state["district"] = select_district

# button
submit_district = st.sidebar.button("Change district")
# button is clicked
if submit_district:
    st.session_state["district"] = select_district



############ SELECT OUTLET ############
select_outlet = st.sidebar.multiselect(label="Select outlet", options=dataframe.loc[(dataframe["m_province_name"].isin(st.session_state["province"])) & (dataframe["m_regency_name"].isin(st.session_state["city"])) & (dataframe["m_district_name"].isin(st.session_state["district"])), "outlet_name"].unique().tolist(), 
    help="You can select multiple, but please select as minimum as possible to optimize the results"
)

# initiate session_state for select_district
if "outlet" not in st.session_state:
    st.session_state["outlet"] = select_outlet

# button
submit_outlet = st.sidebar.button("Change outlet")
# button is clicked
if submit_outlet:
    st.session_state["outlet"] = select_outlet



#################### Filtered DataFrame from sidebar #################################
if len(st.session_state["outlet"]) > 0:
    # title
    st.subheader("You've Selected Outlets Below")
    st.markdown("Make sure you select corectly number of outlets on the sidebar")
    # dataframe
    filtered_dataframe = dataframe.loc[
        (dataframe["m_province_name"].isin(st.session_state["province"])) &
        (dataframe["m_regency_name"].isin(st.session_state["city"])) &
        (dataframe["m_district_name"].isin(st.session_state["district"])) &
        (dataframe["outlet_name"].isin(st.session_state["outlet"]))].copy()
    st.dataframe(filtered_dataframe)
else:
    st.warning("You have no outlets selected, please select first.")



######################## SIDEBAR PART 2 ###############################
st.sidebar.markdown("#### Openrouteservice API Section")

############ SELECT NUMBER PER VISIT IN MINUTES ############
with st.sidebar:
    # time per visit
    select_minutes = st.number_input("Input estimated duration per visit (minutes)", value=20, help="Insert how long a member should stay in an outlet in minutes, default is 20 minutes")
    # what time to start
    clock1, clock2 = st.columns(2)
    select_clock_hour = clock1.number_input("Starting time (hour)", value=8, help="Insert what time to start in hour, default is 8:00 o'clock")
    select_clock_minute = clock2.number_input("Starting time (minute)", value=0, help="Insert what time to start in minutes, default is 8:00 o'clock")

    # what time to finish
    select_clock_hour_finish = clock1.number_input("End time (hour)", value=20, help="Insert what time to end in hour, default is 20:00 o'clock")
    select_clock_minute_finish = clock2.number_input("End time (minute)", value=0, help="Insert what time to end in minutes, default is 20:00 o'clock")

# initiate session_state for select_district
if "minutes" not in st.session_state:
    st.session_state["minutes"] = select_minutes

# start
if "clock_hour" not in st.session_state:
    st.session_state["clock_hour"] = select_clock_hour

if "clock_minute" not in st.session_state:
    st.session_state["clock_minute"] = select_clock_minute

# end
if "clock_hour_finish" not in st.session_state:
    st.session_state["clock_hour_finish"] = select_clock_hour_finish

if "clock_minute_finish" not in st.session_state:
    st.session_state["clock_minute_finish"] = select_clock_minute_finish


# button
submit_minutes = st.sidebar.button("Change time")

# button is clicked
if submit_minutes:
    st.session_state["minutes"] = select_minutes
    st.session_state["clock_hour"] = select_clock_hour
    st.session_state["clock_minute"] = select_clock_minute
    st.session_state["clock_hour_finish"] = select_clock_hour_finish
    st.session_state["clock_minute_finish"] = select_clock_minute_finish

############ INSERT LONGITUDE LATITUDE ############
with st.sidebar:
    # tutorial on how to find out longitude and latitude
    url = "https://tekno.kompas.com/read/2022/06/05/17150037/cara-cari-longitude-dan-latitude-di-google-maps-buat-isi-data-alamat"
    # center point
    coor1, coor2 = st.columns(2)
    input_latitude = coor1.number_input(label="Input latitude of start point", help="Example format: -6.xxxxxxx")
    input_longitude = coor2.number_input(label="Input longitude of start point", help="Example format: 10x.xxxxxxx")
    # clickable link
    st.markdown("_How to find out longitude and latitude [click here](%s)_" % url)

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
    post_ors_api = st.sidebar.button("Run Optimizer")
else:
    st.sidebar.markdown("Please select outlet and start point to run route optimizer")


################### OPENROUTESERVICE API SECTION #################################

###### Add filtered_dataframe with open and close hours
if len(st.session_state["outlet"]) > 0 and  st.session_state["longitude"] != 0 and st.session_state["latitude"] != 0:
    filtered_dataframe["open"] = datetime.datetime.today().replace(hour=st.session_state["clock_hour"], minute=st.session_state["clock_minute"], second=0)
    filtered_dataframe["close"] = datetime.datetime.today().replace(hour=st.session_state["clock_hour_finish"], minute=st.session_state["clock_minute_finish"], second=0)


# Define the vehicles (how many canvassers are)
def get_vehicle():
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
                time_window=[int(datetime.datetime.today().replace(hour=st.session_state["clock_hour"], minute=st.session_state["clock_minute"], second=0).timestamp()),
                            int(datetime.datetime.today().replace(hour=st.session_state["clock_hour_finish"], minute=st.session_state["clock_minute_finish"], second=0).timestamp())]
            )
        )
    return vehicles

# Next, define the delivery stations
def get_delivery():   
    # https://openrouteservice-py.readthedocs.io/en/latest/openrouteservice.html#openrouteservice.optimization.Job
    deliveries = list()
    for delivery in filtered_dataframe.itertuples():
        deliveries.append(
            openrouteservice.optimization.Job(
                id=delivery.Index,
                location=[delivery.outlet_longitude, delivery.outlet_langitude],
                service=st.session_state["minutes"]*60,
                amount=[delivery.needed_amount],
                time_windows=[[int(delivery.open.timestamp()), int(delivery.close.timestamp())]]
            )
        )

    return deliveries


# this function is intended to call ors api
@st.cache(allow_output_mutation=True)
def get_optimizer():
    # Initialize a client and make the request
    ors_client = openrouteservice.Client(key='5b3ce3597851110001cf6248f903a2eb28b04234bcb4b7ada2ccf7c3')  # Get an API key from https://openrouteservice.org/dev/#/signup
    result = ors_client.optimization(
        jobs=get_delivery(),
        vehicles=get_vehicle(),
        geometry=True
    )

    return result


############################## CONDITIONS TO CALL FUNCTION #####################################

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

                ###### CARD #######
                st.subheader("Estimated Route in Total")
                st.markdown("Time in total is calculated by adding total visit time and total trip time.")
                st.markdown("__Disclaimer__: _Estimated time does not calculate the traffic jam._")
                col1, col2, col3 = st.columns(3)
                # total distance
                col1.metric(label="Total Estimated Distance", value=f"{df_stations.tail(1)['Distance'].values[0]/1000:.2f} km")
                # total duration in minutes
                col2.metric(label="Total Estimated Time", value=f"{(df_stations.tail(1)['Duration'].values[0]/60)+((len(df_stations)-1)*st.session_state['minutes']):.2f} in minute(s)")
                # total duration in minutes
                col3.metric(label="Total Estimated Time", value=f"{((df_stations.tail(1)['Duration'].values[0]/60)+((len(df_stations)-1)*st.session_state['minutes']))/60:.2f} in hour(s)")

                # merge filtered dataframe and df_stations to get nama_outlet and google_maps link
                df_merged = pd.merge(
                    df_stations,
                    filtered_dataframe.loc[:, ["mt_leads_code", "outlet_name", "google_maps"]],
                    how="outer", 
                    left_on="Station ID", 
                    right_index=True
                )

                # rename columns' name
                df_merged.columns = df_merged.columns.str.lower().str.replace(" ", "_")
                # copying df_merged
                df_merged_clean = df_merged.loc[df_merged["duration"].notnull()].copy()


                # create map by instantiating folium object
                m = folium.Map(location=[st.session_state["latitude"], st.session_state["longitude"]], zoom_start=10, tiles='cartodbpositron')

                

                # Plot the locations on the map with more info in the ToolTip (using for loop)
                for location in df_merged_clean.itertuples():
                    tooltip = folium.map.Tooltip("Merchant: {}".format(location.outlet_name))
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

                # plot starting point
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

                ######################## DOWNLOADABLE DATAFRAME #########################
                # add url link to columns
                df_merged_clean["google_maps_url"] = df_merged_clean["google_maps"].apply(lambda x: f'<a href="{x}">{x}</a>')

                ######################## SHOWING DATAFRAME (HTML) #########################
                # slicing the important columns
                df_merged_clean_linked = df_merged_clean.loc[:, ["mt_leads_code", "outlet_name", "arrival", "departure", "google_maps_url", "duration_to_previous", "distance_to_previous"]].copy()
                
                # change unit in duration
                df_merged_clean_linked['duration_to_previous'] = df_merged_clean_linked['duration_to_previous']/60
                df_merged_clean_linked['duration_to_previous'] = df_merged_clean_linked['duration_to_previous'].round(2)

                # change unit in distance
                df_merged_clean_linked['distance_to_previous'] = df_merged_clean_linked['distance_to_previous']/1000
                df_merged_clean_linked['distance_to_previous'] = df_merged_clean_linked['distance_to_previous'].round(2)

                # rename columns
                df_merged_clean_linked.columns = ["mt_leads_code", "outlet_name", "arrival", "departure", "google_maps_url", "duration_to_previous_in_minutes", "distance_to_previous_in_km"]
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


            else:
                st.markdown("There was an error in generating the result")
        except:
            st.markdown("Maker sure you have pressed __Run Optimizer__ button first on the sidebar.")
    else:
        st.markdown("There was an error when trying to call openrouteservice API. Please try again by checking all inputs correctly.")

else:
    st.warning("You're not able to run the app until you have selected outlet and input starting point (longitude and latitude) corectly")