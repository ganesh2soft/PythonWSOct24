"""
================================================================================
Flask App — Market Data & Analytics Platform
================================================================================

This Flask application powers a financial analytics dashboard integrated with 
an Angular frontend. It handles data capture, live feeds, options analysis, 
trend calculations, and provides multiple API endpoints for frontend consumption.

--------------------------------------------------------------------------------
Route Summary:
--------------------------------------------------------------------------------

• /                      — Home route
• /mainboard            — Main dashboard
• /authorize            — User authentication
• /orders               — Orders display
• /input_options        — Input nearest expiry for live data
• /feedindicators       — Input for Pivots and Dollar Index
• /options_analysis     — Starts schedulers for background jobs
• /capturedata          — Inputs expiry dates, stores in data.json
• /optionchainlive      — Live data for single expiry day
• /serve_json           — Serves static JSON file
• /login_user           — (Can be ignored)
• /logout_user          — Logout user

--------------------------------------------------------------------------------
API Endpoints (Used by Angular):
--------------------------------------------------------------------------------

• /api/trend            — VIX, PCR display
• /api/options          — Options data
• /api/futures          — Futures data
• /api/gettopbank5      — Top 5 Bank Nifty stocks
• /api/getpremium       — Premium values
• /api/gettopmidcap5    — Top 5 Midcap stocks
• /api/gettopnifty10    — Top 10 Nifty stocks
• /api/getniftyhl       — Nifty 5-minute OHLC
• /api/get-expiry-dates — Available expiry dates
• /api/postorder/orderitems — Order display (incomplete)

--------------------------------------------------------------------------------
Core Business Logic Methods:
--------------------------------------------------------------------------------

• indiavixcalc()        — VIX calculator
• niftyohlc5min()       — Capture 5-min OHLC for Nifty 50
• findpremium()         — Premium calculation
• samplespremium()      — Premium sample calculation
• findtrend()           — Analyze nearest strike price (3 expiries)
• findbanktop()         — Calculate top 5 Bank Nifty
• findmidcaptop()       — Calculate top 5 Midcap
• findniftytop()        — Calculate top 10 Nifty
• processpcr()          — PCR calculator
• startrecord()         — Starts recording & triggers logic
• processoption()       — (Deprecated)
• testme()              — (Ignore)

================================================================================
"""

from flask import Flask ,render_template,redirect,session,url_for,request,send_from_directory,jsonify
from flask_bootstrap import Bootstrap5
import tokengen
import logoutuser
import upstoxapiservices
import db_read
from db_config import Config
import pandas as pd
import json
from flask_sqlalchemy import SQLAlchemy
import traceback
from datetime import datetime
import os
from flask import current_app
from datetime import timedelta
from flask_cors import CORS
import pytz
import logging
data_file = "data.json"

db = SQLAlchemy() 

# Create Flask application instance
app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=7)
app.secret_key = 'funit' 
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cookies across sites
app.config['SESSION_COOKIE_SECURE'] = True  # Set to True in production (HTTPS)

#CORS(app,origins='*', allow_headers='*')
#CORS(app, origins=["http://localhost:4200"], allow_headers='*')
#CORS(app, origins=["http://localhost:4200"])
CORS(app, supports_credentials=True, origins="http://localhost:4200")

# Initialize SQLAlchemy with the app
db.init_app(app)  # Ensure that db is initialized with the app

#'funit' is user-defined 
# Initialize Bootstrap-Flask extension
bootstrap=Bootstrap5(app)
# Define a route for the home page
logging.basicConfig(filename='tradelogger.log', level=logging.DEBUG,  # Set log level to DEBUG (you can change it)
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# You can also log to a file by adding a filename argument:
# logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Get logger
logger = logging.getLogger(__name__)



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/mainboard')
def mainboard():
    access_token = session.get('access_token', None)
    profile_user=upstoxapiservices.profile_user(access_token)
    return render_template('mainboard.html', profile=profile_user.data)

# Define the /authorize route to handle the authorization logic
@app.route('/authorize', methods=['POST'])
def authorize():
    
    print(f'Reached first authorize')
    # Call the authorize function from the loginapilogic.py module
    authcode=request.form['authcode']
    print(authcode)
    gtok=tokengen.token_generate(authcode)
    #print(f'Generated token is',gtok)
    app.logger.info(f"Generated token is {gtok}")
    profile_user=upstoxapiservices.profile_user(gtok)
        # Store the access token in the session
    session['access_token'] = gtok  # Store the token in session
    print(f"Access token: {session['access_token']}")
    # Debug print to check the structure of profile_user
    #print(f"Structure of profile_user: {type(profile_user)}, {profile_user}")
    app.logger.info(f"Profile User:  {profile_user}")
       # Start the scheduler once the user logs in
    # This will start the scheduler when the user logs in    
    return render_template('mainboard.html', profile=profile_user.data)
    
# Define a route for orders page
@app.route('/orders')
def orders():
    access_token = session.get('access_token', None)
    orderbook=upstoxapiservices.order_details(access_token)
    print(f"Structure of orderbook: {type(orderbook)}, {orderbook}")
    # Check if the 'orderbook' object has a 'data' attribute
    if hasattr(orderbook, 'data'):
        # Render the orders page with the data extracted from the object
        return render_template('orders.html', orderb=orderbook.data)
    else:
        # If the 'data' attribute is missing, show an error message
        return render_template('orders.html', orderb=None, error_message="No order data available.")
    

# Define a route for positions page
@app.route('/positions')
def positions():
    access_token = session.get('access_token', None)
    positionsbook=upstoxapiservices.positions_status(access_token)
    print(f"Structure of Positions: {type(positionsbook)}, {positionsbook}")
    if hasattr(positionsbook, 'data'):
        print(f'Found position book +++++++++++++++++++++++++++')
        return render_template('positions.html', positionb=positionsbook.data)
    else:
        print(f'Nothing found*************************************')
        return render_template('positions.html',positionb=None, error_message='No positions')

@app.route('/input_options.html', methods=['GET', 'POST'])
def input_opt():
    if request.method == 'POST':
        # Capture the selected date from the form
        selected_date = request.form['date_input']
        session['selected_date'] = selected_date  # Store the date in session
        
        # Redirect back to the options page after selecting the date
        return redirect(url_for('optionchainlive'))
    
    return render_template('input_options.html')


       
@app.route('/feedindicators', methods=['GET', 'POST'])
def feedindicators():
    if request.method == 'POST':
        # Get the form data and convert to float where necessary
        R1 = float(request.form['R1'])
        R2 = float(request.form['R2'])
        Pivot = float(request.form['Pivot'])
        S1 = float(request.form['S1'])
        S2 = float(request.form['S2'])
        Niftynow = float(request.form['Niftynow'])
        
        dxynow = float(request.form['dxynow'])
        previousdxy = float(request.form['previousdxy'])
        usbondyield = float(request.form['usbondyield'])
       
        # Market sentiment logic
        sentiment = ""
        if Niftynow < S2:
            sentiment = "Ultimate Bearish! Avoid buy both call and Buy Strictly"
        elif S1 <= Niftynow < Pivot:
            sentiment = f"Bearish! buy Put near to Pivot {Pivot} and Buy call at Support S1 {S1} "
        elif S2 <= Niftynow < S1:
            sentiment = f"Heavy Bearish! buy Put near to S1 {S1}, Avoid buy Call "
        elif R1 <= Niftynow < Pivot:
            sentiment = f"Bullish! buy Call near to Pivot {Pivot} and buy Put at Resistance R1 {R1} "
        elif R2 <= Niftynow < R1:
            sentiment = f"Heavy Bullish! Buy Call near to R1 {R1} , Avoid buy Put "
        elif Niftynow > R2:
            sentiment = "Ultimate Bullish! Buy call near to R2, Avoid buy Put"
        # Fallback check if no sentiment is set
        if not sentiment:
            sentiment = "Sentiment not determined"

        print(f"Market sentiment Under feed indicators {sentiment}")

        # Prepare the data to be appended
        trend = {
            'recdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stdpivot': sentiment
        }

        trendfile = 'trend.json'

        # Read the existing file, append the new data, and write it back
        try:
            with open(trendfile, 'r') as f:
                existing_data = json.load(f)  # Load existing data
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is empty, initialize an empty array
            existing_data = []

        # Append the new trend data to the existing data
        existing_data.append(trend)

        # Write the updated list back to the file
        with open(trendfile, 'w') as f:
            json.dump(existing_data, f, indent=4)

        # Dollar Index Trend
        if dxynow > previousdxy and (dxynow - previousdxy) > 1:
            dxytrend = "Dollar Apprecicated heavily, Bearish indian market"
        elif previousdxy - dxynow >= 1:
            dxytrend = "Rupee Appreciated heavily, Bullish indian market"
        else:
            dxytrend = "Neutral dollar"
        
        print(f"DXY Trend: {dxytrend}")
         
        
        trend = {
        'recdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dxytrend' :dxytrend,
        'usbondyield':usbondyield,
       
        }
        trendfile = 'trend.json'

        # Read the existing file, append the new data, and write it back
        try:
            with open(trendfile, 'r') as f:
                existing_data = json.load(f)  # Load existing data
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is empty, initialize an empty array
            existing_data = []

        # Append the new trend data to the existing data
        existing_data.append(trend)

        # Write the updated list back to the file
        with open(trendfile, 'w') as f:
            json.dump(existing_data, f, indent=4)
        return redirect('options_analysis.html')
    return render_template('feedindicators.html') 
########################################################################################################

@app.route('/api/trend', methods=['GET'])
def get_trend_data():
    trendfile = 'trend.json'
    if os.path.exists(trendfile):
        # Open the file and read the data
        with open(trendfile, 'r') as f:
            data = json.load(f)
    else:
        return jsonify({'error': 'File not found'}), 404
    return jsonify(data)
########################################################################################################

    
@app.route('/api/options', methods=['GET'])
def get_options_data():
    data_file = 'data.json'  # The file containing your expiry data
    
    if os.path.exists(data_file):
        # Open the file and read the data
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Retrieve expiry dates and instrument key from the file
            expiry1 = data.get('expiry1', '')
            expiry2 = data.get('expiry2', '')
            expiry3 = data.get('expiry3', '')
                       
    else:
        return jsonify({'error': 'File not found'}), 404
    expdatelist = [expiry1, expiry2, expiry3]
            
    calloption_data, putoption_data = findtrend()
    calloption_data.to_csv('calloption_data.csv', index=False)
    putoption_data.to_csv('putoption_data.csv', index=False)
    print('!!!!!!!!!! returned back from findtrend, Control flow in  /api/options at get_options_data')    
    print('Type of calloption_data and putoption_data inside get_options_data')
    print('Call options properties inside /api/options')
    print(calloption_data.columns)
    #print(calloption_data.info)
    #print(calloption_data.shape)
    #print('Put options properties')
    #print(putoption_data.info)
    #print(putoption_data.shape)
    ist = pytz.timezone('Asia/Kolkata')
    # Check if both calloption_data and putoption_data are empty
    if calloption_data.empty and putoption_data.empty:
        return jsonify({
            'call_options': [],
            'put_options': []
        })
    call_options_list = []

# Loop through each row in the DataFrame
    for _, call in calloption_data.iterrows():
        expiry_date = call['expiry_date'].strftime('%Y-%m-%d') 
        # Append the data to the list
        call_options_list.append({
            'date_entry': call['date_entry'],
            'strike_price': call['strike_price'],
            'call_writer_oi': call['call_writer_oi'],
            'call_wri_oi_prev': call['call_wri_oi_prev'],
            'call_volume': call['call_volume'],
            'call_ltp': call['call_ltp'],
            'nifty_spot_price': call['nifty_spot_price'],
            'expiry_date': expiry_date
        })

    # Now, `call_options_list` should have the properly processed data
    print("Conversion to list of dictionaries done")
    #print("Type of Call Options List after appending", type(call_options_list))


    # Convert put option data to list of dictionaries
    put_options_list = []
    for _, put in putoption_data.iterrows():
        expiry_date = put['expiry_date'].strftime('%Y-%m-%d') 
        put_options_list.append({
            'date_entry': put['date_entry'],
            'strike_price': put['strike_price'],
            'put_writer_oi': put['put_writer_oi'],
            'put_wri_oi_prev': put['put_wri_oi_prev'],
            'put_volume': put['put_volume'],
            'put_ltp': put['put_ltp'],
            'nifty_spot_price': put['nifty_spot_price'],
            'expiry_date': expiry_date
            
        })

    print('Conversion to list of dictionaries done')
    #print(f'Type of Call Options List after appending {type(call_options_list)}')
    #print(f'Type of Put Options List after appending {type(put_options_list)}') 
    print(len(call_options_list))
    print(len(put_options_list))
    
    
    # Return the data as a JSON response with separate fields for call and put options
    return jsonify({'expiry_dates': expdatelist,
                    'call_options': call_options_list,
                    'put_options': put_options_list
                    })
###########################################################################################################

# Angular side api get for futures data 
###########################################################################################################
@app.route('/api/futures', methods=['GET'])
def get_futures_data():
    # Convert the DataFrame to a dictionary

    futures_data=db_read.getfut()
    
     # Define the IST timezone
    ist = pytz.timezone('Asia/Kolkata')

    # If there's no data, return an empty array
    if not futures_data:
        return jsonify([])
    
    # Convert each Futures object into a dictionary
    futures_list = []
    for future in futures_data:
        if isinstance(future.ts, datetime):
            future_ts = future.ts.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')
        else:
            future_ts = future.ts  # Assuming 'ts' is already in an acceptable format
        futures_list.append({
            'ts': future_ts,
            'last_price': future.last_price,
            'symbol': future.symbol,
            'oi': future.oi,
            'total_buy_quantity': future.total_buy_quantity,
            'total_sell_quantity': future.total_sell_quantity,
            'volume': future.volume,
            'result': future.result
        })

    # Return the data as a JSON response
    return jsonify(futures_list)
######################################################################################################

@app.route('/options_analysis.html')
def optionsanalysis():
    app.logger.info("Options analysis visited")
    access_token = session.get('access_token', None)
    if access_token is None:
        print("Access token is missing!")
    print(f"Access token at options analysis: {access_token}")
    
    try:
        from scheduler import start_scheduler
        start_scheduler() 

    except Exception as e:
        print(f"Error fetching options data: {e}")
        traceback.print_exc()  # Print the full error trace
    call_df,put_df=findtrend()
    
    call_arr = call_df.to_dict(orient='records')
    put_arr = put_df.to_dict(orient='records')
        
    futurerows=db_read.getfut()
    return render_template('options_analysis.html',exp1_put_df=put_arr,exp1_call_df=call_arr,futurerows=futurerows)
########################################################################################################

@app.route('/capturedata.html',methods=['GET', 'POST'])
def capturedata():
    access_token = session.get('access_token', None)
    if request.method == 'POST':
        expiry1=request.form['expiry1']
        expiry2=request.form['expiry2']
        expiry3=request.form['expiry3']
        instrumentkey=request.form['instrumentkey']
        # Save data to the file
        data = {
        'expiry1': expiry1,
        'expiry2': expiry2,
        'expiry3': expiry3,
        'instrumentkey': instrumentkey
            }
        with open(data_file, 'w') as f:
            json.dump(data, f)          
        
        return redirect('options_analysis.html')
    return render_template('capturedata.html')  

###############################################################################################
def indiavixcalc(access_token):
    from upstoxapiservices import get_india_vix_spot_future
    # Assuming get_india_vix_spot_future returns (ivix, nifty50, nifty_futures) or None
    result = get_india_vix_spot_future(access_token)
    
    # Check if the result is None
    if result is None:
        print("Error: No data returned from get_india_vix_spot_future")
        return  # Optionally handle error or raise exception
    
    # Unpack the result if it's valid
    ivix, nifty50, nifty_futures = result
    app.logger.info(f"IVIX: {ivix}, Nifty50: {nifty50}, Nifty Futures: {nifty_futures}")
    #print(f"IVIX: {ivix}, Nifty50: {nifty50}, Nifty Futures: {nifty_futures}")

    # ivix,nifty50,nifty_futures=get_india_vix_spot_future(access_token)
    nifty50=round(nifty50)
    nifty_futures=round(nifty_futures)
    #print(f'India VIX : {ivix}')
    trend_vix = {
            'vixts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ivix': ivix,
            'nifty50': nifty50,
            'nifty_futures':nifty_futures
        }

    trendfile = 'trend.json'
    try:
        with open(trendfile, 'r') as f:
            existing_data = json.load(f)  # Load existing data
            # Ensure existing_data is a dictionary
            if not isinstance(existing_data, dict):
                existing_data = {"vix_set": [], "pcr_set": []}
            if "vix_set" not in existing_data:
                existing_data["vix_set"] = []
            if "pcr_set" not in existing_data:
                existing_data["pcr_set"] = []

    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, initialize an empty structure
        existing_data = {"vix_set": [],"pcr_set": []}

    # Append the new VIX data to vix_set
    existing_data['vix_set'].append(trend_vix)

    # Write the updated data back to the file
    with open(trendfile, 'w') as f:
        json.dump(existing_data, f, indent=4)
    print('India VIX completed')
################################################################################################       
def niftyohlc5min(access_token):
    from upstoxapiservices import niftyohlcservice
    ohlc_data=niftyohlcservice(access_token)
    
    if hasattr(ohlc_data, 'data') and 'NSE_INDEX:Nifty 50' in ohlc_data.data:
        nifty_data = ohlc_data.data['NSE_INDEX:Nifty 50']

        # Access OHLC data from the 'NSE_INDEX:Nifty 50'
        if hasattr(nifty_data, 'ohlc'):
            ohlc = nifty_data.ohlc  # Assuming 'ohlc' is an attribute of 'nifty_data'
            
            # Extract individual OHLC values
            open_price = ohlc.open if hasattr(ohlc, 'open') else None
            high_price = ohlc.high if hasattr(ohlc, 'high') else None
            low_price = ohlc.low if hasattr(ohlc, 'low') else None
            close_price = ohlc.close if hasattr(ohlc, 'close') else None

            # Extract last price
            last_price = nifty_data.last_price if hasattr(nifty_data, 'last_price') else None

            # Get current timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Create the data to write into the JSON file
            data_to_write = {
                "timestamp": timestamp,
                "last_price": last_price,
                "ohlc": {
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price
                }
            }

            # Write to JSON file
            file_name = 'nifty5min.json'

            # Check if the file exists and load the existing data
            try:
                with open(file_name, 'r') as file:
                    existing_data = json.load(file)
            except FileNotFoundError:
                existing_data = []

            # Append the new data to the existing data (or start fresh if no data exists)
            existing_data.append(data_to_write)

            # Write the updated data back to the file
            with open(file_name, 'w') as file:
                json.dump(existing_data, file, indent=4)

            #print(f"Data has been written to {file_name} successfully.")
        else:
            print("OHLC data not found in 'NSE_INDEX:Nifty 50'.")
    else:
        print("No data found or 'NSE_INDEX:Nifty 50' is missing in the response.")
    print('Nifty OHLC completed')
#######################################################################################################
@app.route('/api/gettopbank5', methods=['GET'])
def banktop5tofrontend():
    try:
        # Read the banktop5.json file
        with open('banktop5.json', 'r') as json_file:
            banktop_data = json.load(json_file)
        
        # Return the data as JSON response
        return jsonify(banktop_data)
    
    except Exception as e:
        # Log and return error if there's an issue reading the file
        app.logger.error(f"Error occurred while reading banktop5.json: {str(e)}")
        return jsonify({'error': 'Unable to fetch bank data'}), 500

############################################################################
@app.route('/api/getpremium', methods=['GET'])
def premium():
    datafile = 'premium.json'  # Update path if needed

    if not os.path.exists(datafile):
        return jsonify({'error': 'File not found'}), 404

    try:
        with open(datafile, 'r') as f:
            data = json.load(f)

        # Ensure 'premium_set' exists in the file
        if 'premium_set' not in data:
            return jsonify({'error': 'Invalid data format'}), 400

        return jsonify(data)  # returns: {"premium_set": [ ... ] }

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

############################################################################
def findpremium(access_token):
    if os.path.exists(data_file):
        # Open the file and read the data
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Return the values of expiry1, expiry2, expiry3, and instrumentkey
            expiry1 = data.get('expiry1', '')
    
    print('Inside premiumstudy with expiry date =',expiry1)
    
    try:
        with current_app.app_context():
                optbook = upstoxapiservices.options_status(access_token, expiry1)
    except Exception as e:
            print(f"Error fetching options data inside premium study process: {e}")
            traceback.print_exc()  # Print the full error trace
       
    if hasattr(optbook, 'data'):
        dataarray=[]      
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        totcallltp=0;
        totputltp=0;
        # Extract the relevant data from each row in caplist
        for row in optbook.data:
            call_ltp = row.call_options.market_data.ltp or 0
            put_ltp = row.put_options.market_data.ltp or 0

            dataarray.append({
                'date_entry': current_timestamp,
                'call_ltp': call_ltp,
                'strike_price': row.strike_price,
                'underlying_spot_price': row.underlying_spot_price,
                'put_ltp': put_ltp,
            })

            totcallltp = round(totcallltp + call_ltp)
            totputltp = round(totputltp + put_ltp)
        print(f'Total Call premium {totcallltp}')
        print(f'Total Put Premium {totputltp}')
    else:
        print("No data found in optbook")
    
        # Read the existing file, append the new data, and write it back
    #print(type(dataarray))
    #print('Testinng########################## ',dataarray)
    df=pd.DataFrame(dataarray)
    #print('Dataframe shape',df)
    sample_call_tot,sample_put_tot=samplespremium(df)
    #print('Control ends in premium study#################################################')
    premiumstudy={
        'recdate': current_timestamp,
        'totcallltp': totcallltp,
        'totputltp': totputltp,
        'sample_call_tot': sample_call_tot,
        'sample_put_tot': sample_put_tot,
    }     
    premiumfile = 'premium.json'
    try:
        with open(premiumfile, 'r') as f:
            existing_data = json.load(f)  # Load existing data
            # Ensure existing_data is a dictionary
            if not isinstance(existing_data, dict):
                existing_data = {"premium_set": []}
            
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, initialize an empty structure
        existing_data = {"premium_set": []}

    existing_data['premium_set'].append(premiumstudy)

    # Write the updated data back to the file
    with open(premiumfile, 'w') as f:
        json.dump(existing_data, f, indent=4)
    print('Premium study completed')
#################################################################################################################
def samplespremium(df):
       
    #df = pd.DataFrame(optbook)
    
    #print(df.shape)
    
    #print(df.columns)
    #print(df)
    # Check if the necessary columns are in the DataFrame
    if 'underlying_spot_price' not in df.columns or 'strike_price' not in df.columns:
        print("Required columns are missing!")
    else:
        # Round the underlying spot price to the nearest 100
        df['rounded_spot_price'] = df['underlying_spot_price'].apply(lambda x: round(x / 100) * 100)
        
        # Get the first value of rounded spot price (or use a more relevant value if needed)
        tempvar1 = df.iloc[0]['rounded_spot_price']
        sprice = tempvar1
        
        # Calculate the apex values
        apexs = sprice - 1000
        apexr = sprice + 1000
        print(f"Lower Apex: {apexs}")
        print(f"Upper Apex: {apexr}")
        
        # Filter the DataFrame based on strike price being a multiple of 100 and within the apex range
        filtered_df = df[(df['strike_price'] % 100 == 0) & (df['strike_price'] >= apexs) & (df['strike_price'] <= apexr)]
        
        # Check if there are any rows in the filtered DataFrame
        if filtered_df.empty:
            print("No data found within the specified apex range.")
        else:
            print('Stage1:Dataframe filtered for strike price multiples of 100 and within the apex range')
            #print('At end of Stage 1',filtered_df)
    samples_total_call_ltp = round(filtered_df['call_ltp'].sum())
    samples_total_put_ltp = round(filtered_df['put_ltp'].sum())
    print("Samples_Total Call LTP:", samples_total_call_ltp)
    print("Samples_Total Put LTP:", samples_total_put_ltp)
    return samples_total_call_ltp,samples_total_put_ltp
    
    
############################################################################

def mainindexfun(access_token):
    from upstoxapiservices import mainindex
    import json
    import os
    from datetime import datetime
    try:
        main_index=mainindex(access_token)
        mainindexfile = 'mainindex.json'
        # Load existing data or create new list
        if os.path.exists('mainindex.json'):
            with open('mainindex.json', 'r') as json_file:
                existing_data = json.load(json_file)
                if not isinstance(existing_data, list):
                    existing_data = []
        else:
                existing_data = []

            # Add timestamped result
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = {
                "timestamp": current_timestamp,
                "main_index": main_index
        }

            # Append and save the updated list
        existing_data.append(result)
            
        with open('mainindex.json', 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)

    except Exception as e:
        # Log or print the error
        app.logger.error(f"Error occurred in findMain Indextop function: {str(e)}")
        print(f"Error: {str(e)}")
        return None
    print('Main Index completed')
    
##################################################################################################
@app.route('/api/getmainindex', methods=['GET'])
def get_main_index_data():
    try:
        if not os.path.exists('mainindex.json'):
            return jsonify({'error': 'File not found'}), 404
            # If the file doesn't exist, create an empty list
           
        with open('mainindex.json', 'r') as json_file:
                main_index = json.load(json_file)

        return jsonify(main_index)

    except Exception as e:
        app.logger.error(f"Error occurred while reading midcaptop5.json: {str(e)}")
        return jsonify({'error': 'Unable to Main Indics data'}), 500

####################################################################################################
@app.route('/api/gettopmidcap5', methods=['GET'])
def midcaptop5tofrontend():
    try:
        

        if not os.path.exists('midcaptop5.json'):
            return jsonify({'error': 'Data file not found'}), 404

        with open('midcaptop5.json', 'r') as json_file:
            midcap_data = json.load(json_file)

        return jsonify(midcap_data)

    except Exception as e:
        app.logger.error(f"Error occurred while reading midcaptop5.json: {str(e)}")
        return jsonify({'error': 'Unable to fetch midcap data'}), 500
#################################################################################################
def findbanktop(access_token):
    from upstoxapiservices import getbanktop5  # Assuming this function exists in your API service
    
    try:
        # Fetch the top 5 bank stocks using the provided access token
        banktop_data = getbanktop5(access_token)
                        
        # Load symbolnamemapping.json to get the symbol-to-company mapping
        with open('symbolnamemapping.json', 'r') as symbol_file:
            symbolnamemapping = json.load(symbol_file)
        
        # Replace stock symbols in banktop_data with company names
        for stock in banktop_data:
            symbol = stock.get('symbol')
            if symbol in symbolnamemapping:
                stock['symbol'] = symbolnamemapping[symbol]
            else:
                stock['symbol'] = "Unknown Symbol"  # Fallback in case symbol is not found
                #stock['company_name'] = "Unknown Company"  # Fallback in case symbol is not found
        
             
        if os.path.exists('banktop5.json'):
            with open('banktop5.json', 'r') as json_file:
                existing_data = json.load(json_file)
                if not isinstance(existing_data, list):  # Ensure it's a list
                    existing_data = []
        else:
            existing_data = []
        # Create a dictionary with the timestamp and the fetched data
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = {
            "timestamp": current_timestamp,  # Include the timestamp for when the data was fetched
            "top_banks": banktop_data  # The actual data
        }   
                         
                 
        existing_data.append(result)
        with open('banktop5.json', 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)
        
        
    except Exception as e:
        # Log any errors that occur during the function execution
        app.logger.error(f"Error occurred in findbanktop function: {str(e)}")
        print(f"Error: {str(e)}")
        return None
    print('Bank Top 5 completed')
#############################################################################
def findmidcaptop(access_token):
    from upstoxapiservices import getmidcaptop5  # Assuming this function exists
    import json
    import os
    from datetime import datetime

    try:
        # Fetch the top 5 midcap stocks
        midcap_data = getmidcaptop5(access_token)

        # Load symbol-to-company mapping
        with open('symbolnamemapping.json', 'r') as symbol_file:
            symbolnamemapping = json.load(symbol_file)

        # Replace stock symbols with company names
        for stock in midcap_data:
            symbol = stock.get('symbol')
            stock['symbol'] = symbolnamemapping.get(symbol, "Unknown Symbol")
        
        # Load existing data or create new list
        if os.path.exists('midcaptop5.json'):
            with open('midcaptop5.json', 'r') as json_file:
                existing_data = json.load(json_file)
                if not isinstance(existing_data, list):
                    existing_data = []
        else:
            existing_data = []

        # Add timestamped result
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = {
            "timestamp": current_timestamp,
            "top_midcaps": midcap_data
        }

        # Append and save the updated list
        existing_data.append(result)
        
        with open('midcaptop5.json', 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)

    except Exception as e:
        # Log or print the error
        app.logger.error(f"Error occurred in findmidcaptop function: {str(e)}")
        print(f"Error: {str(e)}")
        return None
    print('Midcap Top 5 completed')
#############################################################################################

def findniftytop(access_token):
    from upstoxapiservices import getniftytop10  # Assuming this function exists in your API service

    try:
        # Fetch the top 10 Nifty stocks using the provided access token
        niftytop_data = getniftytop10(access_token)
        
        # Load symbolnamemapping.json to get the symbol-to-company mapping
        with open('symbolnamemapping.json', 'r') as symbol_file:
            symbolnamemapping = json.load(symbol_file)
        
        # Replace stock symbols in niftytop_data with company names
        for stock in niftytop_data:
            symbol = stock.get('symbol')
            if symbol in symbolnamemapping:
                stock['symbol'] = symbolnamemapping[symbol]
            else:
                stock['symbol'] = "Unknown Company"  # Fallback in case symbol is not found
        
        # Log the structure of the modified niftytop_data for debugging purposes
        app.logger.info(f"Structure of modified niftytop_data: {type(niftytop_data)}, {niftytop_data}")
        if os.path.exists('niftytop10.json'):
            with open('niftytop10.json', 'r') as json_file:
                existing_data = json.load(json_file)
                if not isinstance(existing_data, list):  # Ensure it's a list
                    existing_data = []
        else:
            existing_data = []
        # Get current timestamp
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Create the final structure with the timestamp and top 10 nifty data
        result = {
            "timestamp": current_timestamp,
            "top_nifty": niftytop_data
        }
        existing_data.append(result)
        # Write the modified niftytop_data to 'niftytop10.json' file
        with open('niftytop10.json', 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)
      
    except Exception as e:
        # Log any errors that occur during the function execution
        app.logger.error(f"Error occurred in findniftytop function: {str(e)}")
        print(f"Error: {str(e)}")
    print('Nifty Top 10 completed')
######################################################################################
@app.route('/api/gettopnifty10', methods=['GET'])
def niftytop10tofrontend():
    try:
        # Read the niftytop10.json file
        with open('niftytop10.json', 'r') as json_file:
            niftytop_data = json.load(json_file)
        
        # Return the data as JSON response
        return jsonify(niftytop_data)
    
    except Exception as e:
        # Log and return error if there's an issue reading the file
        app.logger.error(f"Error occurred while reading niftytop10.json: {str(e)}")
        return jsonify({'error': 'Unable to fetch Nifty data'}), 500
##############################################################################################
###########To analyze options strike with LTP and volume##########
def fewstrikes(access_token,expiry1):
    options_status = upstoxapiservices.options_status(access_token, expiry1)
    dataarr=[]
    opt_df=pd.DataFrame(options_status.data)  
    print('Inside Few Strikes Dataframe',opt_df)
    print('Type of opt_df',type(opt_df))
    print('Print columns of opt_df',opt_df.columns)
    #nf_spot=opt_df.nifty_spot_price.iloc[0] if not opt_df.empty else 0
    #print(f'Teseting before loop Underlying Spot Price for Nifty is {nf_spot}')  
    
    for row in options_status.data:
        call_ltp = row.call_options.market_data.ltp or 0
        put_ltp = row.put_options.market_data.ltp or 0
        dataarr.append({
            'expiry':row.expiry,            
            'call_volume':row.call_options.market_data.volume,
            'call_ltp': call_ltp,
            'strike_price':row.strike_price ,
            'underlying_spot_price': row.underlying_spot_price,            
            'put_volume':row.put_options.market_data.volume,
            'put_ltp': put_ltp          
        })  
    
    df2=pd.DataFrame(dataarr)
     # Example: Round the underlying spot price to the nearest 100
    df2['rounded_spot_price'] = df2['underlying_spot_price'].apply(lambda x: round(x / 100) * 100)
    roundsp= df2.iloc[0]['rounded_spot_price']
    
    sup01=roundsp - 100
    sup02=roundsp - 200
    sup03=roundsp - 300
    sup04=roundsp - 400
    res01=roundsp + 100
    res02=roundsp + 200
    res03=roundsp + 300
    res04=roundsp + 400
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print(sup04,sup03,sup02,sup01,roundsp,res01,res02,res03,res04)
    
   
    strike_levels = set()
    levels = {
        'sup04': sup04,
        'sup03': sup03,
        'sup02': sup02,
        'sup01': sup01,
        'round_spot': roundsp,
        'res01': res01,
        'res02': res02,
        'res03': res03,
        'res04': res04
    }
    strike_levels.update(levels)
    print('Strike Levels:', strike_levels)
    
    print('Dataframe columns',df2)
        ################################################################################################
def startrecord(expiry1,expiry2,expiry3,instrumentkey,access_token):
        
        ##### Call the below indiavixcalc  to record the vix
        indiavixcalc(access_token)
        niftyohlc5min(access_token)
        findbanktop(access_token)
        findniftytop(access_token)
        findmidcaptop(access_token)
        findpremium(access_token)
        mainindexfun(access_token)
        fewstrikes(access_token,expiry1)
        expiry1=expiry1
        expiry2=expiry2
        expiry3=expiry3
        instrumentkey=instrumentkey 
        exparray=[expiry1,expiry2,expiry3]     
        #access_token = session.get('access_token', None)
        # Call the options_status function with the selected date
        for exp in exparray:
            try:
                with current_app.app_context():
                    optbook = upstoxapiservices.options_status(access_token, exp)
            except Exception as e:
                print(f"Error fetching options data: {e}")
                traceback.print_exc()  # Print the full error trace
                

            if hasattr(optbook, 'data'):
              
                processpcr(optbook.data,exp)

                        
                
                try:
                    
                    # Add ledger data
                    from db_write import add_ledger
                    add_ledger(optbook.data, db)
                except Exception as e:
                    print(f"Error adding ledger: {e}")
                    traceback.print_exc()

        try:
            with current_app.app_context():
                # Print some details about the current app context
                #print(f"App Name: {current_app.name}")
                #print(f"App Config: {current_app.config}")
                
                future_response=upstoxapiservices.symbol_pricedata(access_token,instrumentkey)
        except Exception as e:
            print(f"Error fetching Nifty Futures/SYmbols data: {e}")
            traceback.print_exc()  # Print the full error trace
        if hasattr(future_response, 'data'):
            print(f'Found Nifty Futures/SYmbols details ')
            
            try:
                # Add Symbol data
                #with current_app.app_context():
                from db_write import addfut
                addfut(future_response.data, db)
            except Exception as e:
                print(f"Error adding Nifty Futures/SYmbols rows to DB: {e}")
                traceback.print_exc()
        else:
            print(f'Future data writing not done')
       
####################################################################################################
def processpcr(optdict,exp):
    tcall = 0
    tput = 0
    #print(f'Inside process pcr fun, {type(optdict)}')
    # Create a list of dictionaries to hold the data for the DataFrame
    data = []
    tpcr=0
    # Extract the relevant data from each row in caplist
    for row in optdict:
        calli=row.call_options.market_data.oi or 0
        puti=row.put_options.market_data.oi or 0
        data.append({
            'expiry':row.expiry,
            'call_oi':calli,
            'call_volume':row.call_options.market_data.volume,
            'strike_price':row.strike_price ,
            'underlying_spot_price': row.underlying_spot_price,
            'put_oi':puti ,
            'put_volume':row.put_options.market_data.volume,
            'nifty_spot_price':row.underlying_spot_price,
           
        })  
        tcall=calli+tcall
        tput=puti+tput
    #print(tcall,tput)
    tpcr = round(tput / tcall, 4)
    
    if 0.01 <= tpcr <= 0.849:
        pcrtrend="Bearish"
    elif 0.85 <= tpcr <= 0.999:
        pcrtrend= "Bear-to-SW"
    elif 1 <= tpcr <= 1.199:
        pcrtrend= "SW-to-Bull"
    elif tpcr >= 1.2:
        pcrtrend="Bullish"
    else:
        pcrtrend= "Check again"
    
    #print(tpcr)    
    # Prepare the data to be appended
    trend_pcr = {
            'expiry':exp,
            'recdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tpcr':tpcr,
            'pcrtrend':pcrtrend
    }
    
    trendfile = 'trend.json'
    try:
        with open(trendfile, 'r') as f:
            existing_data = json.load(f)  # Load existing data
            # Ensure existing_data is a dictionary
            if not isinstance(existing_data, dict):
                existing_data = {"vix_set": [], "pcr_set": []}
            if "vix_set" not in existing_data:
                existing_data["vix_set"] = []
            if "pcr_set" not in existing_data:
                existing_data["pcr_set"] = []

    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, initialize an empty structure
        existing_data = {"vix_set": [],"pcr_set": []}

    # Append the new VIX data to vix_set
    existing_data['pcr_set'].append(trend_pcr)

    # Write the updated data back to the file
    with open(trendfile, 'w') as f:
        json.dump(existing_data, f, indent=4)
        # Read the existing file, append the new data, and write it back
    
    # Convert the list of dictionaries into a pandas DataFrame
    df = pd.DataFrame(data)
    #print(df)
    app.logger.info('Processed PCR data and saved to JSON file')
    print('PCR calculation completed')
  

####################################################################################################
@app.route('/optionchainlive',methods=['GET', 'POST'])
def optionchainlive():
    try:
        access_token = session.get('access_token', None)

        selected_date = session.get('selected_date', None)

        # If there's no date in the session, redirect to input date page
        if not selected_date:
            return redirect(url_for('input_opt'))  # Redirect to input options if no date is selected
             
        # Call the options_status function with the selected date
        try:
            optbook = upstoxapiservices.options_status(access_token, selected_date)
        except Exception as e:
            print(f"Error fetching options data: {e}")
            traceback.print_exc()  # Print the full error trace
            return render_template('optionchainlive.html', optionb=None, error_message='Error fetching data.')

        if hasattr(optbook, 'data'):
            print(f'Found Options details +++++++++++++++++++++++++++')
            
            try:
                # Add ledger data
                from db_write import add_ledger
                add_ledger(optbook.data, db)
            except Exception as e:
                print(f"Error adding ledger: {e}")
                traceback.print_exc()
                return render_template('optionchainlive.html', optionb=None, error_message='Error adding ledger data.')
            
            caplist=optbook.data
            #print(f'type of caplist is {type(caplist)}')
            processoption(caplist)     
            findtrend(caplist) 

            return render_template('optionchainlive.html', optionb=optbook.data, selected_date=selected_date)
        else:
            print(f'Nothing found*************************************')
            return render_template('optionchainlive.html', optionb=None, error_message='No Data', selected_date=selected_date)

    except Exception as e:
        # Catch all other exceptions
        print(f"Unexpected error: {e}")
        traceback.print_exc()  # Print the full error trace
        return render_template('optionchainlive.html', optionb=None, error_message='Unexpected error occurred.')
    

#################################################################################################
def processoption(caplist):
    # Create a list of dictionaries to hold the data for the DataFrame
    data = []
    
    # Extract the relevant data from each row in caplist
    for row in caplist:
        data.append({
            'expiry':row.expiry,
            'call_oi':row.call_options.market_data.oi,
            'call_volume':row.call_options.market_data.volume,
            'strike_price':row.strike_price ,
            'underlying_spot_price': row.underlying_spot_price,
            'put_oi':row.put_options.market_data.oi ,
            'put_volume':row.put_options.market_data.volume,
            'nifty_spot_price':row.underlying_spot_price,
        })  
    # Convert the list of dictionaries into a pandas DataFrame
    df = pd.DataFrame(data)
            
    # You can now process the DataFrame as needed
    # Example: Calculate the maximum call open interest (oi)
    max_calloi = df['call_oi'].max()
    print(f"The maximum value of call open interest is: {max_calloi}")
    
    # Example: Round the underlying spot price to the nearest 100
    df['rounded_spot_price'] = df['underlying_spot_price'].apply(lambda x: round(x / 100) * 100)
    tempvar1= df.iloc[0]['rounded_spot_price']
    tempvar2=df.iloc[0]['underlying_spot_price']
    sprice=tempvar1
    print(df['underlying_spot_price'].dtype)
    # Ensure both s and r are assigned values
    s = tempvar1
    r = tempvar1
    # Determine support and resistance based on rounded spot price
    if tempvar1 > tempvar2:
        r = tempvar1
        s = tempvar1 - 100  # If rounded price is higher, set support below it
    else:
        s = tempvar1
        r = tempvar1 + 100  # If rounded price is lower, set resistance above it
    
    # Calculating support and resistance levels
    s1 = s - 100
    s2 = s - 200
    s3 = s - 300
   
    r1 = r + 100
    r2 = r + 200
    r3 = r + 300
    
    temp=round(sprice/500)*500
    s1_500=temp-500
    s2_500=temp-1000
    r1_500=temp+500
    r2_500=temp+1000
    apexs=sprice-1000
    apexr=sprice+1000
    print(apexs)
    print(apexr)
    # Ensure that 'underlying_spot_price' is numeric
    #df['strike_price'] = pd.to_numeric(df['strike_price'], errors='coerce')
    #filtered_df = df[(df['strike_price'] >= apexs) & (df['strike_price'] <= apexr)]

    filtered_df = df[(df['strike_price'] % 100 == 0) & (df['strike_price'] >= apexs) & (df['strike_price'] <= apexr)]


    print(f'Support levels: {s2_500}, {s1_500},  {s3}, {s2}, {s1}, {s}')
    print(f'Resistance levels: {r}, {r1}, {r2}, {r3},{r1_500},{r2_500} ')
    #print(filtered_df)
    # Convert the filtered DataFrame to HTML format
    html_output = filtered_df.to_html()

    # Optionally, save the HTML output to a file
    with open('filtered_data.html', 'w') as f:
        f.write(html_output)

      # Convert DataFrame to HTML table
    html_table = df.to_html(classes="table table-bordered")
    # Save the DataFrame to an Excel file
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f"filtered_data_{current_time}.xlsx"
###############################################################################################

def findtrend():
    if os.path.exists(data_file):
        # Open the file and read the data
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Return the values of expiry1, expiry2, expiry3, and instrumentkey
            expiry1 = data.get('expiry1', '')
            expiry2 = data.get('expiry2', '')
            expiry3 = data.get('expiry3', '')
            

    # Get options data for expiry1 (you can add other expiry dates similarly)
    opt1_arr = db_read.getopt(expiry1)
    opt2_arr = db_read.getopt(expiry2)
    opt3_arr = db_read.getopt(expiry3)
    #print('Tough place to tackle',opt1_arr)
    opt1_df = pd.DataFrame(opt1_arr)
    opt2_df = pd.DataFrame(opt2_arr)
    opt3_df = pd.DataFrame(opt3_arr)
    #print(opt1_df)
    #print(f'Second opt2{opt2_df.shape}')    
    #print(f'Third opt3{opt3_df.shape}')

    df = pd.concat([opt1_df, opt2_df, opt3_df], ignore_index=True)
    #print(df.shape)
    df.to_csv('df.csv', index=False)
   

    # Check if the necessary columns are in the DataFrame
    if 'nifty_spot_price' not in df.columns or 'strike_price' not in df.columns:
        print("#####################Control is now in findtrend######################")
        
    else:
        # Round the underlying spot price to the nearest 100
        df['rounded_spot_price'] = df['nifty_spot_price'].apply(lambda x: round(x / 100) * 100)
        
        # Get the first value of rounded spot price (or use a more relevant value if needed)
        tempvar1 = df.iloc[0]['rounded_spot_price']
        sprice = tempvar1
        
        # Calculate the apex values
        apexs = sprice - 1000
        apexr = sprice + 1000
        #print(f"Lower Apex: {apexs}")
        #print(f"Upper Apex: {apexr}")
        
        # Filter the DataFrame based on strike price being a multiple of 100 and within the apex range
        filtered_df = df[(df['strike_price'] % 100 == 0) & (df['strike_price'] >= apexs) & (df['strike_price'] <= apexr)]
        
        # Check if there are any rows in the filtered DataFrame
        if filtered_df.empty:
            #print("No data found within the specified apex range.")
            print('ignore this message')
        else:
            print('ignore this message')
            #print('Stage1:Dataframe filtered for strike price multiples of 100 and within the apex range')
            #print(filtered_df)
    
        # Ensure the 'date_entry' column is in datetime format
    filtered_df.to_csv('filtered_df.csv', index=False)
    #print(filtered_df.shape)
    #filtered_df['date_entry'] = pd.to_datetime(filtered_df['date_entry'])
    filtered_df.loc[:, 'date_entry'] = pd.to_datetime(filtered_df['date_entry'])

    #print(filtered_df.shape)

    # Get today's date (without normalizing, so it keeps the time info)
    today = pd.to_datetime('today')

    # Get the latest (most recent) date in the filtered DataFrame
    last_day = filtered_df['date_entry'].max()

    # Debugging prints to check today's date and the last date in the filtered DataFrame
    #print(f"Today's Date: {today}")
    #print(f"Last Date: {last_day}")

    # Filter the DataFrame for rows with today's date or the most recent date
    filtered_df2 = filtered_df[(filtered_df['date_entry'].dt.date == today.date()) | 
                            (filtered_df['date_entry'] == last_day)]
        # Filter the DataFrame for rows with today's date or the most recent date
    # filtered_df2 = filtered_df[(filtered_df['date_entry'] == today) | (filtered_df['date_entry'] == last_day)]

        # Show the filtered DataFrame

    if filtered_df2.empty:
        print('ignore this message')
        #print("No data found for today's date or the last date.")
    else:
        #print('Stage2:Filtered DataFrame for today or the last date')
        #print('Testing ')
        #print(filtered_df2.shape)
        filtered_df2.to_csv('filtered_df2.csv', index=False)
    
    call_df = filtered_df2[['date_entry', 'strike_price', 'call_writer_oi', 'call_wri_oi_prev','call_volume', 'call_ltp','expiry_date','nifty_spot_price']]
    
    # Create the DataFrame for Puts
    put_df = filtered_df2[['date_entry', 'strike_price', 'put_writer_oi','put_wri_oi_prev', 'put_volume', 'put_ltp','expiry_date','nifty_spot_price']]
    
    put_df.to_csv('put_df.csv', index=False)

    # Group by 'strike_price' and display all rows without aggregation
    call_group_df = call_df.groupby('strike_price', as_index=False).apply(lambda x: x)
    put_group_df = put_df.groupby('strike_price', as_index=False).apply(lambda x: x)
    #print('Stage3:Before leaving after applying group by strike price')
    #print(call_group_df.shape)
    #print(put_group_df.shape)
    #print('############################## Alert ##############################')
    #print(call_group_df.columns)
    #print(put_group_df.columns)
    put_group_df.to_csv('put_group_df.csv', index=False)
    #correct till now
    #print('Stage3:Group by strike price done')
    
    print('!!!!!!!!!!!!!!!!!!!!!!!!!! Exiting Findtrend')  
    return call_group_df, put_group_df   
    #return call_df, put_df


#####################################################################################
@app.route('/api/postorder/orderitems', methods=['POST'])
def postorder():
    access_token = session.get('access_token')
    print(f"Session contents: {session}")

    print('from postorder',access_token)
    if access_token is None:
        print("Access token is missing!")

    print('Inside postorder')
    # Check if the request contains JSON data       
    inputitems = request.json  # Extract JSON data from the request body 
    print('Request reached to postorder',inputitems)
    """
    from upstoxapiservices import placeordersrv
    msg=placeordersrv(inputitems)
    """
    session.clear()
    testme()
    #return "Hello from postorder", 200
  
    #return jsonify({'message': 'Order items received successfully'}), 200  
#####################################################################################
def testme():
    print('Test function called##################')
    gtok=session.get('access_token')
    print('Access token from testme',gtok)
     
@app.route('/api/getniftyhl', methods=['GET'])
def getniftyhl():
    # Read the data from the JSON file
    file_name = 'nifty5min.json'
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            data = json.load(file)
    else:
        return jsonify({'error': 'File not found'}), 404

    return jsonify(data)
#####################################################################################


@app.route('/api/get-expiry-dates', methods=['GET'])
def get_expiry_dates():
    data_file = 'data.json'  # The file containing your expiry data
    
    if os.path.exists(data_file):
        # Open the file and read the data
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Retrieve expiry dates and instrument key from the file
            expiry1 = data.get('expiry1', '')
            expiry2 = data.get('expiry2', '')
            expiry3 = data.get('expiry3', '')
            print(expiry1, expiry2, expiry3)
            # Return the values in JSON format
            return jsonify({
                'expiry1': expiry1,
                'expiry2': expiry2,
                'expiry3': expiry3
                
            })
    else:
        return jsonify({'error': 'File not found'}), 404        

# Serve the data.json file from the root directory
@app.route('/data.json')
def serve_json():
    # Get the absolute path to the root directory
    root_dir = os.getcwd()  # This will be 'D:\PythonWSOct24\tradeguide'
    # Serve the data.json file from this directory
    return send_from_directory(root_dir, 'data.json')
     
@app.route('/login')
def login_user():
    pass
#########################################################################################################
@app.route('/logout_user')
def logout_user():
    
    informmsg=logoutuser.logout_user()
    print(informmsg)
    # Optionally, you can redirect to the home page or login page
    return redirect(url_for('home'))
#########################################################################################################

# Run the app
if __name__ == '__main__':
    
    app.run(debug=True)
