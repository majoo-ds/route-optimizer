import streamlit as st
from PIL import Image

def run():
    # favicon image
    im = Image.open("favicon.ico")

    # set page
    st.set_page_config(
        page_title="Route Optimization",
        page_icon= im
    )

    st.write("# Welcome to Route Optimizer App! 🗺️")

    st.markdown(
        """
        ### Overview
        Route optimizer is intended to help the field team to choose the best route order on their daily basis.
        It suggests the route order of location inputs so the team can go to selected route until reach the final destination point in an efficient way.
        There are two available data sources, __Existing Merchants__ (subscribed to Majoo) and __Leads from CRM__ (not subscribed to Majoo yet).
        
        **👇 Here how it works**
       
        - __1. Explore the data__
        We recommend that you explore data at first to help you make a better choice in selecting outlets
        - __2. Insert parameters on `Outlet Selection Section` on the sidebar__
        We recommend that you explore data at first to help you make a better choice in selecting outlets
        - __3. Input `Openrouteservices API Section` on the sidebar__
        By limiting the number of locations, the app will work faster to return the results
        - __4. App will suggest the order route__
        Once, both steps above have been implemented, app will generate an interactive map along with the trip order and selected locations when we press `Run Optimizer` button
        - __5. Save to offline__
        We recommend that you save the result in provided excel format, so you do no need to return to this app and save your time. 
        
        __Note__: _We can run app and save the result multiple times_
    """
    )


if __name__ == "__main__":
    run()