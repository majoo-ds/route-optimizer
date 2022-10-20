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
        
        **👇 Here how it works**
       
        - __1. Choose the city to run the trip__
        At first we need to narrow down the locations we're going to visit
        - __2. Select maximum number of destination__
        By limiting the number of locations, the app will work faster to return the results
        - __3. App will suggest the order route__
        Once, both steps above have been implemented, app will generate an interactive map along with the trip order and selected locations
        - __4. Save to offline__
        We recommend that you save the result in provided excel format, so you do no need to return to this app and save your time. 
        
        __Note__: _We can run app and save the result multiple times_
    """
    )


if __name__ == "__main__":
    run()