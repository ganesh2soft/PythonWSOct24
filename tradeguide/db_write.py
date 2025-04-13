from flask import  jsonify
from datetime import datetime
import pandas as pd
def add_ledger(optbook,db):
    #print(f'Structure of data: {type(optbook)}')
    
    if not isinstance(optbook, list):
        return jsonify({"error": "Invalid input, expected a list of option data"}), 400

    data = optbook
    
    # Print how many entries are being processed for debugging
    # print(f"Processing {len(data)} rows of data")


    from models import Options
    for rowl in data:
        #print(f'Entering For loop, processing row: {rowl}')

        # Check if rowl is an instance of OptionStrikeData and access attributes directly
        new_ledger = Options(
                date_entry=rowl.date_entry if hasattr(rowl, 'date_entry') else datetime.now(),
                expiry_date=rowl.expiry if hasattr(rowl, 'expiry') else None,
                call_writer_oi=rowl.call_options.market_data.oi if hasattr(rowl, 'call_options') else 0,
                call_wri_oi_prev=rowl.call_options.market_data.prev_oi if hasattr(rowl, 'call_options') else 0,
                call_volume=rowl.call_options.market_data.volume if hasattr(rowl, 'call_options') else 0,
                call_ltp=rowl.call_options.market_data.ltp if hasattr(rowl, 'call_options') else 0,
                call_iv=rowl.call_options.option_greeks.iv if hasattr(rowl, 'call_options') else 0,
                strike_price=rowl.strike_price if hasattr(rowl, 'strike_price') else 0,
                put_writer_oi=rowl.put_options.market_data.oi if hasattr(rowl, 'put_options') else 0,
                put_wri_oi_prev=rowl.put_options.market_data.prev_oi if hasattr(rowl, 'put_options') else 0,
                put_volume=rowl.put_options.market_data.volume if hasattr(rowl, 'put_options') else 0,
                put_ltp = rowl.put_options.market_data.ltp if hasattr(rowl, 'put_options') and hasattr(rowl.put_options, 'market_data') else 0,
                put_iv=rowl.put_options.option_greeks.iv if hasattr(rowl, 'put_options') else 0,
                nifty_spot_price=rowl.underlying_spot_price if hasattr(rowl, 'underlying_spot_price') else 0,
                pcr=rowl.pcr if hasattr(rowl, 'pcr') else 0
                
            )
        #df=pd.DataFrame(rowl)
        #print(df)
        # Add to database session
        db.session.add(new_ledger)
        
    # Commit all ledger entries to the database
    db.session.commit()

    # Return success response
    return jsonify({"message": "New ledger(s) added", "ledger_id": new_ledger.ledger_id}), 201

def fut_senti(longbuy,shortsell):
    # Calculate the ratio
    frefer = shortsell / longbuy
    
    # "Strong Bearish" if frefer is greater than 4.1
    if frefer > 4.1:
        return "Strong Bearish"
    
    # "Bear" if frefer is between 4 and 2
    elif frefer >= 2 and frefer <= 4:
        return "Bear"
    
    # "Bear-to-SW" if frefer is between 1.9 and 1.1
    elif frefer > 1 and frefer <= 1.9:
        return "Bear-to-SW"
    
     
    # "SW-to-Bull" if frefer is between 0.9 and 0.5
    elif frefer > 0.5 and frefer <= 1:
        return "SW-to-Bull"
    
    # "Bull" if frefer is between 0.49 and 0.26
    elif frefer > 0.26 and frefer <= 0.49:
        return "Bull"
    
    # "Strong Bullish" if frefer is greater than 0.25
    elif frefer <= 0.24:
        return "Strong Bullish"
    
    # If no conditions match, return "Unknown"
    else:
        return "Check manually"

def addfut(mktbook,db):
    
    data = mktbook
    #print(f'Structure of of of data: {type(data)}')
    if isinstance(data, dict):  # Ensure that we have a dictionary
        #print(f"Processing {len(data)} rows of data")
        
        from models import Futures
        
        # Iterate over each symbol and its corresponding data
        for symbol, symbol_data in data.items():
            #print(f'Entering For loop, processing symbol: {symbol}')
            #print(f'Data for symbol: {symbol_data}')

              # Extract the values from symbol_data dictionary
            total_buy_quantity = symbol_data.total_buy_quantity
            total_sell_quantity = symbol_data.total_sell_quantity
            result=fut_senti(total_buy_quantity,total_sell_quantity)
            # Calculate result (Bull if buy > sell, else Bear)
            # result = 'Bull Wins' if total_buy_quantity > (1.5* total_sell_quantity) else 'Bear Wins'
            # Now rowl is symbol_data (which is a dictionary)
            # Create a new Symtbl instance using the data for that symbol
            new_symtbl = Futures(
                ts=datetime.fromisoformat(symbol_data.timestamp) if hasattr(symbol_data, 'timestamp') else datetime.now(),  # Timestamp
                average_price=symbol_data.average_price if hasattr(symbol_data, 'average_price') else 0,  # Default to 0 if not available
                instrument_token=symbol_data.instrument_token if hasattr(symbol_data, 'instrument_token') else '',
                last_price=symbol_data.last_price if hasattr(symbol_data, 'last_price') else 0.00,  # Default to 0.00 for Decimal type
                oi=symbol_data.oi if hasattr(symbol_data, 'oi') else 0,
                symbol=symbol_data.symbol if hasattr(symbol_data, 'symbol') else '',
                total_buy_quantity=symbol_data.total_buy_quantity if hasattr(symbol_data, 'total_buy_quantity') else 0,
                total_sell_quantity=symbol_data.total_sell_quantity if hasattr(symbol_data, 'total_sell_quantity') else 0,
                volume=symbol_data.volume if hasattr(symbol_data, 'volume') else 0,
                result=result
                    
            )

            # Add the new entry to the database session
            db.session.add(new_symtbl)
            #print(f'Added symbol data for {symbol}')

        # Commit all symtbl entries to the database
        db.session.commit()
        print('All data committed successfully.')
    

        # Return success response
        return jsonify({"message": "New Instruments(s) added", "symid": new_symtbl.symid}), 201
    else:
        return jsonify({"error": "Invalid input format, expected a dictionary"}), 400