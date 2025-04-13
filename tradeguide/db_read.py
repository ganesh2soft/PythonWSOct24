from datetime import datetime
from sqlalchemy import func
def get_ledgers():
    # Querying the Ledger table for all entries
    from models import Options
    ledgers = Options.query.all()  # Fetch all ledger entries
    return ledgers

def getfut():
    # Get today's date
    today = datetime.today().date()
    from models import Futures
    # Query to get the two most recent distinct dates from the `ts` column
    last_two_dates_result = Futures.query.with_entities(func.date(Futures.ts)).distinct().order_by(func.date(Futures.ts).desc()).limit(1).all()
    
    if last_two_dates_result:
        # Extract the last two dates from the result (if available)
        last_dates = [date[0] for date in last_two_dates_result]
    else:
        last_dates = []  # If no data exists
    
    if not last_dates:
        return []

    # Check if the last available date is not today
    if last_dates[0] != today:
        print(f"Alert: The most recent available data is from {last_dates[0]}, not today!")

    # Query to get records for the last two distinct dates
    syms = Futures.query.filter(
        func.date(Futures.ts).in_(last_dates)
    ).all()

    return syms



def getopt(expirydate):
    print(f"Fetching data for expiry date: {expirydate}")
    today = datetime.today().date()
    from models import Options

    # Query to get the two most recent distinct dates from the `date_entry` column
    last_two_dates_result = Options.query.with_entities(func.date(Options.date_entry)).distinct().order_by(func.date(Options.date_entry).desc()).limit(2).all()

    if last_two_dates_result:
        # Extract the last two dates from the result (if available)
        last_dates = [date[0] for date in last_two_dates_result]
    else:
        last_dates = []  # If no data exists
    
    if not last_dates:
        return []

    # Check if the last available date is not today
    if last_dates[0] != today:
        print(f"Alert: The most recent available data is from {last_dates[0]}, not today!")

    # Query to get records for the last two distinct dates AND the given expiry date
    syms = Options.query.filter(
        func.date(Options.date_entry).in_(last_dates),
        Options.expiry_date == expirydate  # AND condition for expiry_date
    ).all()

    # Create a list of dictionaries with the required fields
    syms_list = []
    for option in syms:
        
        syms_list.append({
            'ledger_id': option.ledger_id,
            'date_entry': option.date_entry,
            'call_writer_oi': option.call_writer_oi,
            'call_wri_oi_prev': option.call_wri_oi_prev,
            'call_volume': option.call_volume,
            'call_ltp': option.call_ltp,
            'call_iv': option.call_iv,
            'expiry_date': option.expiry_date,
            'strike_price': option.strike_price,
            'put_writer_oi': option.put_writer_oi,
            'put_wri_oi_prev': option.put_wri_oi_prev,
            'put_volume': option.put_volume,
            'put_ltp': option.put_ltp,
            'put_iv': option.put_iv,
            'nifty_spot_price': option.nifty_spot_price,
            'pcr': option.pcr
            
        })

    return syms_list
