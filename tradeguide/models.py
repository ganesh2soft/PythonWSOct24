from app import db 

class Options(db.Model):
    __tablename__ = 'optionstbl'  # Name of the table in MySQL

    ledger_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Primary key with auto-increment
    date_entry=db.Column(db.TIMESTAMP)
    call_writer_oi = db.Column(db.Integer)  # Open Interest for Call Writer
    call_wri_oi_prev = db.Column(db.Integer)  # Open Interest for Call Writer
    call_volume = db.Column(db.Integer)  # Call Option Volume
    call_ltp = db.Column(db.Numeric(10, 2))  # Call Last Traded Price (decimal with 2 decimal places)
    call_iv = db.Column(db.Numeric(5, 2))  # Call Implied Volatility
    expiry_date = db.Column(db.Date)
    strike_price = db.Column(db.Integer)  # Strike Price
    put_writer_oi = db.Column(db.Integer)  # Open Interest for Put Writer
    put_wri_oi_prev = db.Column(db.Integer)  # Open Interest for Put Writer
    put_volume = db.Column(db.Integer)  # Put Option Volume
    put_ltp = db.Column(db.Numeric(10, 2))  # Put Last Traded Price (decimal with 2 decimal places)
    put_iv = db.Column(db.Numeric(5, 2))  # Put Implied Volatility
    nifty_spot_price = db.Column(db.Numeric(10, 2))  # Nifty Spot Price
    pcr = db.Column(db.Numeric(5, 4))  # Put-Call Ratio
    
    
    
    def __repr__(self):
        return f'<Options {self.ledger_id}>'

    def __init__(self, date_entry, call_writer_oi, call_wri_oi_prev, call_volume, call_ltp, call_iv, 
                 expiry_date,strike_price, put_writer_oi, put_wri_oi_prev, put_volume, put_ltp, put_iv, nifty_spot_price, pcr):
        self.date_entry=date_entry
        self.call_writer_oi = call_writer_oi
        self.call_wri_oi_prev = call_wri_oi_prev
        self.call_volume = call_volume
        self.call_ltp = call_ltp
        self.call_iv = call_iv
        self.expiry_date = expiry_date
        self.strike_price = strike_price
        self.put_writer_oi = put_writer_oi
        self.put_wri_oi_prev = put_wri_oi_prev
        self.put_volume = put_volume
        self.put_ltp = put_ltp
        self.put_iv = put_iv
        self.nifty_spot_price = nifty_spot_price
        self.pcr = pcr


class Trendone(db.Model):

    __tablename__ = 'trendonetbl'  # Name of the table in MySQL
    trendoneid= db.Column(db.Integer, primary_key=True, autoincrement=True)  # Primary key with auto-increment
    trendonets=db.Column(db.TIMESTAMP, default=db.func.current_timestamp()) 
    underlying_spot_price = db.Column(db.Integer)  # Open Interest for Call Writer
    calculatedpcr =  db.Column(db.Numeric(8, 3))  # Call Option Volume
    trendonenow = db.Column(db.String(255)) # Call Last Traded Price (decimal with 2 decimal places)
    trendonedir = db.Column(db.String(255))  # Call Implied Volatility

    def __repr__(self):
        return f'<Trendone {self.trendoneid}>'

    def __init__(self, trendonets, underlying_spot_price, calculatedpcr, trendonenow, trendonedir):
        self.trendonets=trendonets
        self.underlying_spot_price = underlying_spot_price
        self.calculatedpcr = calculatedpcr
        self.trendonenow = trendonenow
        self.trendonedir = trendonedir
   
class Futures(db.Model):
    __tablename__ = 'futurestbl'  # Table name in MySQL

    symid = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Primary key with auto-increment
    ts = db.Column(db.TIMESTAMP)  # Timestamp for when the record was created
    average_price = db.Column(db.Integer)  # Average price as integer
    instrument_token = db.Column(db.String(255))  # Instrument token as string
    last_price = db.Column(db.Numeric(10, 2))  # Last traded price with 2 decimal places
    oi = db.Column(db.Integer)  # Open Interest as integer
    symbol = db.Column(db.String(255))  # Symbol of the instrument
    total_buy_quantity = db.Column(db.Integer)  # Total buy quantity as integer
    total_sell_quantity = db.Column(db.Integer)  # Total sell quantity as integer
    volume = db.Column(db.Integer)  # Volume of the instrument
    result = db.Column(db.String(255), nullable=True) 
    def __repr__(self):
        return f'<Futures {self.symid}>'

    def __init__(self, ts, average_price, instrument_token, last_price, oi, symbol, total_buy_quantity, total_sell_quantity, volume,result):
        self.ts = ts
        self.average_price = average_price
        self.instrument_token = instrument_token
        self.last_price = last_price
        self.oi = oi
        self.symbol = symbol
        self.total_buy_quantity = total_buy_quantity
        self.total_sell_quantity = total_sell_quantity
        self.volume = volume
        self.result=result