"""
================================================================================
Upstox Services API Integration Module
================================================================================

This module provides wrapper functions around the Upstox API (v2.0), enabling 
integration with market data, options chains, order management, and user profile 
features. These services are used to fetch live data, place orders, and support 
custom analytics in the trading dashboard.

--------------------------------------------------------------------------------
Function Summary:
--------------------------------------------------------------------------------

• symbol_pricedata(gtok, instrumentkey)
    - Fetch full market quote for any given instrument key (equities/futures/options)

• options_status(gtok, edate)
    - Retrieve Put/Call option chain for Nifty 50 based on expiry date

• order_details(gtok)
    - Fetch all orders from the user’s order book

• positions_status(gtok)
    - Retrieve current positions from the user's portfolio

• profile_user(gtok)
    - Fetch user profile including fund and margin details

• get_india_vix_spot_future(gtok)
    - Fetch live India VIX, Nifty Spot, and configured Nifty Future prices from data.json

• niftyohlcservice(gtok)
    - Get 1-minute interval OHLC data for Nifty 50

• getniftytop10(gtok)
    - Get LTPs for top 10 Nifty 50 companies (predefined)

• getbanktop5(gtok)
    - Get LTPs for top 5 Bank Nifty stocks (predefined)

• getmidcaptop5(gtok)
    - Get LTPs for selected midcap stocks (predefined)

• placeordersrv(inputitems)
    - Places an equity order using pre-configured values and session token

================================================================================
Dependencies:
- upstox_client
- flask (session management in placeordersrv)
- json, os (used in VIX service)

Note:
- Ensure valid `access_token` is passed or stored in session
- Some functions depend on data stored in 'data.json'
- This file is designed to support live financial analytics and trading workflows

================================================================================
"""

import upstox_client
from upstox_client.rest import ApiException

### Below func is get Futures monthly, not particularly given for futures
### Use the same function to capture any stock
def symbol_pricedata(gtok,instrumentkey):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_version = '2.0'
    #Feb nifty fut= NSE_FO|35013
    instrument_key=instrumentkey
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
      
    try:
        api_response = api_instance.get_full_market_quote(instrument_key, api_version)
        #print(api_response)
        return api_response
    except ApiException as e:
        print("Exception MarketQuoteApi->get_full_market_quote %s\n" % e.body)


### Below func is get options data, edate is expiry date of option chain
def options_status(gtok,edate):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_version = '2.0'
    api_instance = upstox_client.OptionsApi(upstox_client.ApiClient(configuration))

    try:
        api_response = api_instance.get_put_call_option_chain("NSE_INDEX|Nifty 50", edate)
        #print(f'type of {api_response}',type(api_response))
        return(api_response)
    except ApiException as e:
        print("Exception when calling OrderApi->options apis: %s\n" % e.body)


###Below Function is to get orders equity
def order_details(gtok):
    
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
    api_version = '2.0'
    try:
        # Get order book
        api_response = api_instance.get_order_book(api_version)
        return (api_response)
    except ApiException as e:
        print("Exception when calling OrderApi->get_order_book: %s\n" % e)


###Below Function is to get Positions       
def positions_status(gtok):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_version = '2.0'
    api_instance = upstox_client.PortfolioApi(upstox_client.ApiClient(configuration))

    try:
        api_response = api_instance.get_positions(api_version)
        return(api_response)
    except ApiException as e:
        print("Exception when calling ChargeApi->get_brokerage: %s\n" % e)


###Below Function is to get profile 
def profile_user(gtok):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_version = '2.0'

    api_instance = upstox_client.UserApi(upstox_client.ApiClient(configuration))
    print('Profile Upstox Service progresses')
    try:
        # Get User Fund And Margin
        profile_detail = api_instance.get_profile(api_version)
        #print(f'profile data',profile_detail)
        # Pass profile data to the mainboard.html template
        return(profile_detail)
    except ApiException as e:
        print("Exception when calling UserApi->get_user_fund_margin: %s\n" % e)
        return f"Failed to fetch profile data: {e}", 500  # Handle API errors
       
### Function to get India VIX live data
def get_india_vix_spot_future(gtok):
    data_file = "data.json"
    import os,json
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Return expiry1, expiry2, expiry3, and instrumentkey from the file
            future_inst=data.get('instrumentkey', '')
    #print (f"Future Instrument Key: {future_inst}")
    

    india_vix_symbol = 'NSE_INDEX|India VIX'
    nifty_spot='NSE_INDEX|Nifty 50'
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_version = '2.0'
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
    try:
        api_response1 = api_instance.ltp(india_vix_symbol,api_version)
        api_response2 = api_instance.ltp(nifty_spot,api_version)
        api_response3 = api_instance.ltp(future_inst,api_version)

       # print("India VIX Data and Spot price:", api_response1,api_response2)
       # print("Account ",api_response3)
        # Check if data exists for the future instrument
        # Check if data exists for the future instrument
        if api_response3.data and 'NSE_FO:NIFTY25APRFUT' in api_response3.data:
            future_inst_price = api_response3.data['NSE_FO:NIFTY25APRFUT'].last_price
            
            # Check if future_inst_price is None or if the data is missing
            if future_inst_price is not None:
                print(f"Future Instrument Price: {future_inst_price}")
            else:
                print(f"Error: 'last_price' not found for {future_inst}")
        else:
            print(f"Error: No data available for {future_inst}")
        # Extract the India VIX value
        if api_response1.data and 'NSE_INDEX:India VIX' in api_response1.data:
            india_vix = api_response1.data['NSE_INDEX:India VIX'].last_price
            print(f"Current India VIX: {india_vix}")
        else:
            print("India VIX data not available in the response.")
            india_vix = None
        if api_response2.data and 'NSE_INDEX:Nifty 50' in api_response2.data:
            nifty_spot = api_response2.data['NSE_INDEX:Nifty 50'].last_price
            #print(f"Nifty spot data: {nifty_spot}")
        else:
            print("Nifty data not available in the response.")
              # Return None if the data is not available
            nifty_spot= None
        return india_vix ,nifty_spot,future_inst_price # Return the extracted value
                      
    except Exception as e:
        print("Error fetching data:", e)
    print('India VIX Upstox Service Completed')
###################################################################################################
### Function to get Nifty OHLC
def niftyohlcservice(gtok):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    niftyohlc50='NSE_INDEX|Nifty 50'
    api_version = '2.0'
    interval='I1'
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
    try:
        api_response1 = api_instance.get_market_quote_ohlc(niftyohlc50,interval,api_version)
        #print("Nifty OHLC Data:", api_response1)
        return api_response1
    except Exception as e:
        print("Error fetching data:", e)
    print('Nifty 5 min OHLC Upstox Service Completed')

#######################################################################################################
def getniftytop10(gtok):  
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok

    # Top 10 Nifty 50 symbols
    niftysymbols = [
        'NSE_EQ|INE040A01034',  # HDFC Bank Ltd.
        'NSE_EQ|INE002A01018',  # Reliance Industries Ltd.
        'NSE_EQ|INE090A01021',  # ICICI Bank Ltd.
        'NSE_EQ|INE009A01021',  # Infosys Ltd.
        'NSE_EQ|INE154A01025',  # ITC Ltd.
        'NSE_EQ|INE467B01029',  # Tata Consultancy Services Ltd.
        'NSE_EQ|INE018A01030',  # Larsen and Toubro Ltd.
        'NSE_EQ|INE238A01034',  # Axis Bank Ltd.
        'NSE_EQ|INE062A01020',  # Kotak Mahindra Bank Ltd.
        'NSE_EQ|INE397D01024'   # Bharti Airtel Ltd.
    ]
    
    api_version = '2.0'
    
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
    nifty_data = []  # Create an empty list to store results
    
    for symbol in niftysymbols:
        try:
            # Fetch the last traded price (LTP)
            api_response = api_instance.ltp(symbol, api_version)
            
            # Debugging: Print the entire API response
            #print(f"Raw response for {symbol}: {api_response}")
            
            # Check if the response is an instance of GetMarketQuoteLastTradedPriceResponse
            if isinstance(api_response, upstox_client.models.get_market_quote_last_traded_price_response.GetMarketQuoteLastTradedPriceResponse):
                # Access the 'data' field of the response
                if api_response.data:
                    # Iterate over the data
                    for key, value in api_response.data.items():
                        # If the instrument_token matches the symbol, extract the last price
                        if value.instrument_token == symbol:
                            last_price = round(value.last_price)  # Direct access to last_price property
                            if last_price is not None:
                                #print(f"LTP for {symbol}: {last_price}")
                                nifty_data.append({"symbol": symbol, "ltp": last_price})
                            else:
                                print(f"No LTP data for {symbol}")
                else:
                    print(f"No 'data' field in the response for {symbol}")
            else:
                print(f"Unexpected response format for {symbol}: {type(api_response)}")

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    if not nifty_data:
        print("No data available for the specified symbols.")
        return None
    print('Nifty 50 top 10 Upstox Service Completed')
    return nifty_data       
###########################################################################################
def getbanktop5(gtok):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    banksymbols=['NSE_EQ|INE040A01034','NSE_EQ|INE090A01021','NSE_EQ|INE238A01034','NSE_EQ|INE237A01028','NSE_EQ|INE062A01020']
    api_version = '2.0'
    # hdfc,icici,axis,kotak,sbi  
    
    
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
    bank_data = []  # Create an empty list to store results
    for symbol in banksymbols:
        try:
            # Fetch the last traded price (LTP)
            api_response = api_instance.ltp(symbol, api_version)
            
            # Debugging: Print the entire API response
            #print(f"Raw response for {symbol}: {api_response}")
            
            # Check if the response is an instance of GetMarketQuoteLastTradedPriceResponse
            if isinstance(api_response, upstox_client.models.get_market_quote_last_traded_price_response.GetMarketQuoteLastTradedPriceResponse):
                # Access the 'data' field of the response
                if api_response.data:
                    # Iterate over the data
                    for key, value in api_response.data.items():
                        # If the instrument_token matches the symbol, extract the last price
                        if value.instrument_token == symbol:
                            last_price = round(value.last_price)  # Direct access to last_price property
                            if last_price is not None:
                                #print(f"LTP for {symbol}: {last_price}")
                                bank_data.append({"symbol": symbol, "ltp": last_price})
                            else:
                                print(f"No LTP data for {symbol}")
                else:
                    print(f"No 'data' field in the response for {symbol}")
            else:
                print(f"Unexpected response format for {symbol}: {type(api_response)}")

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    if not bank_data:
        print("No data available for the specified symbols.")
        return None
    #print(f"Bank data: at Upstox Service level####################### {bank_data}")
    print('Bank Nifty top 5 Upstox Service Completed')
    return bank_data  # Return the list of responses for all symbols
############################################################################################
def getmidcaptop5(gtok):
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
  
    # Define your Midcap symbols here (you can update this list as required)
    midcapsymbols = ['NSE_EQ|INE027H01010', 'NSE_EQ|INE118H01025', 'NSE_EQ|INE262H01021', 'NSE_EQ|INE591G01017', 'NSE_EQ|INE417T01026','NSE_EQ|INE935N01020']
    
    api_version = '2.0'
    # Midcap symbols list for Midcap 5 (this is a placeholder, update accordingly)
    # midcap symbols: "Max Healthcare", "Persistent Systems", "Coforge", etc. (update your list here)
    
    api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
    midcap_data = []  # Create an empty list to store results
    
    for symbol in midcapsymbols:
        try:
            # Fetch the last traded price (LTP)
            api_response = api_instance.ltp(symbol, api_version)
            
            # Debugging: Print the entire API response
            #print(f"Raw response for {symbol}: {api_response}")
            
            # Check if the response is an instance of GetMarketQuoteLastTradedPriceResponse
            if isinstance(api_response, upstox_client.models.get_market_quote_last_traded_price_response.GetMarketQuoteLastTradedPriceResponse):
                # Access the 'data' field of the response
                if api_response.data:
                    # Iterate over the data
                    for key, value in api_response.data.items():
                        # If the instrument_token matches the symbol, extract the last price
                        if value.instrument_token == symbol:
                            last_price = round(value.last_price)  # Direct access to last_price property
                            if last_price is not None:
                                #print(f"LTP for {symbol}: {last_price}")
                                midcap_data.append({"symbol": symbol, "ltp": last_price})
                            else:
                                print(f"No LTP data for {symbol}")
                else:
                    print(f"No 'data' field in the response for {symbol}")
            else:
                print(f"Unexpected response format for {symbol}: {type(api_response)}")

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    if not midcap_data:
        print("No data available for the specified symbols.")
        return None
    
    #print(f"Midcap data: at Upstox Service level####################### {midcap_data}")
    print('Midcap Upstox Service Completed')
    return midcap_data  # Return the list of responses for all symbols
###########################################################################################
def placeordersrv(inputitems):
    #print('Alert_____________Control reached placeordersrv')
    #print('inputitems as of placecorder service:',inputitems)
    from flask import session
    gtok = session.get('access_token')

    
    if not gtok:
        print("Error: Access token is missing!")
        return {"error": "Access token is missing"}
    configuration = upstox_client.Configuration()
    configuration.access_token = gtok
    api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
    api_version = '2.0'
    inputitems = upstox_client.PlaceOrderRequest(1, "D", "DAY", 20.0, "string", "NSE_EQ|INE528G01035", "LIMIT", "BUY", 0, 20.1, False)

    try:
        api_response = api_instance.place_order(inputitems, api_version)
        #print(api_response)
        return api_response
    except ApiException as e:
        print("Exception when calling OrderApi->place_order: %s\n" % e)
        return None