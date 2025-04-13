CREATE TABLE optionstbl (
    ledger_id INT AUTO_INCREMENT PRIMARY KEY,
    date_entry TIMESTAMP,
    call_writer_oi INT,
    call_wri_oi_prev INT,
    call_volume INT,
    call_ltp DECIMAL(10, 2),
    call_iv DECIMAL(5, 2),
    expiry_date DATE,
    strike_price DECIMAL(10, 2),
    put_writer_oi INT,
    put_wri_oi_prev INT,
    put_volume INT,
    put_ltp DECIMAL(10, 2),
    put_iv DECIMAL(5, 2),
    nifty_spot_price DECIMAL(10, 2),
    pcr DECIMAL(5, 2),
    slabid VARCHAR(255) NOT NULL
);









SELECT * FROM traderdb.ledgertbl;
ALTER TABLE ledgertbl MODIFY COLUMN date_entry TIMESTAMP;
truncate  ledgertbl;
desc ledgertbl;
ALTER TABLE ledgertbl
MODIFY COLUMN pcr DECIMAL(12,2);
CREATE TABLE trendonetbl (
    trendoneid INT AUTO_INCREMENT PRIMARY KEY,
    trendonets TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Renamed to trendonets
    underlying_spot_price DECIMAL(10, 2),
    trendonenow VARCHAR(255),  -- Renamed to trendonenow
    trendonedir VARCHAR(255),  -- Renamed to trendonedir
    calculatedpcr DECIMAL(8, 3)
);
desc trendonetbl;
ALTER TABLE ledgertbl
ADD COLUMN slabid VARCHAR(255) NOT NULL DEFAULT '' AFTER pcr;

DELIMITER $$

CREATE TRIGGER before_insert_ledger
BEFORE INSERT ON ledgertbl
FOR EACH ROW
BEGIN
    IF NEW.date_entry IS NOT NULL AND NEW.expiry_date IS NOT NULL THEN
        SET NEW.slabid = CONCAT(DATE_FORMAT(NEW.date_entry, '%Y%m%d%H%i%s'), DATE_FORMAT(NEW.expiry_date, '%Y%m%d'));
    END IF;
END $$

DELIMITER ;


CREATE TABLE symtbl (
    symid INT AUTO_INCREMENT PRIMARY KEY,
    ts TIMESTAMP,
    average_price INT,
    instrument_token VARCHAR(255),
    last_price INT,
    oi INT,
    symbol VARCHAR(255),
    total_buy_quantity INT,
    total_sell_quantity INT,
    volume INT
);

desc symtbl;


SELECT * FROM traderdb.ledgertbl where  strike_price in (23300,23400,23500,23600) and  expiry_date='2025-01-16' order by strike_price

<!-- Fourth Row -->
        <div class="row">
            <!-- Fourth Container (takes up full width) -->
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h4>Futures Data</h4>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <thead class="table-dark">
                                <tr>
                                    <th>TIMESTAMP</th>
                                    <th>Last Price</th>
                                    <th>Symbol</th>
                                    <th>OI</th>
                                    <th>Total Buy Quantity</th>
                                    <th>Total Sell Quantity</th>
                                    <th>Volume</th>
                                    <th>Result</th>
                                    
                                </tr>
                            </thead>
                            <tbody>
                                {% for future in futurerows %}
                                <tr>
                                    <td>{{ future.ts }}</td>
                                    <td>{{ future.last_price }}</td>
                                    <td>{{ future.symbol}}</td>
                                    <td>{{ future.oi }}</td>
                                    <td>{{ future.total_buy_quantity }}</td>
                                    <td>{{ future.total_sell_quantity }}</td>
                                    <td>{{ future.volume }}</td>
                                    <td>{{ future.result }}</td>
                                    

                                </tr>
                                {% else %}
                                <tr>
                                    <td colspan="5" class="text-center">No DATA found</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

-- Delete last month future data and archieve them into a separate table
-- Disable safe updates temporarily to allow delete
SET SQL_SAFE_UPDATES = 0;

-- Define the symbol dynamically
SET @symbol = 'NIFTY25JANFUT';

-- Step 1: Create the new table dynamically
SET @sql_query_create = CONCAT('CREATE TABLE futures_old_', @symbol, ' AS 
                                SELECT * 
                                FROM futurestbl
                                WHERE symbol = "', @symbol, '"');

-- Step 2: Delete rows from the original table
SET @sql_query_delete = CONCAT('DELETE FROM futurestbl 
                                WHERE symbol = "', @symbol, '"');

-- Execute both statements
PREPARE stmt_create FROM @sql_query_create;
EXECUTE stmt_create;
DEALLOCATE PREPARE stmt_create;

PREPARE stmt_delete FROM @sql_query_delete;
EXECUTE stmt_delete;
DEALLOCATE PREPARE stmt_delete;

-- Re-enable safe updates after the operation
SET SQL_SAFE_UPDATES = 1;
-- END code ----Delete last month future data and archieve them into a separate table

-- START code for deleting options data and archieving them into a separate table
-- Based on the expiry date
SET SQL_SAFE_UPDATES = 0;

-- Define the expiry_date dynamically
SET @expiry_date = '2025-02-06';  -- Change this to the expiry date you need

-- Step 1: Create the new table dynamically based on expiry_date
SET @sql_query_create = CONCAT('CREATE TABLE options_old_', REPLACE(@expiry_date, '-', '_'), ' AS 
                                SELECT * 
                                FROM optionstbl
                                WHERE expiry_date = "', @expiry_date, '"');

-- Step 2: Delete rows from the original table based on expiry_date
SET @sql_query_delete = CONCAT('DELETE FROM optionstbl 
                                WHERE expiry_date = "', @expiry_date, '"');

-- Execute both statements
PREPARE stmt_create FROM @sql_query_create;
EXECUTE stmt_create;
DEALLOCATE PREPARE stmt_create;

PREPARE stmt_delete FROM @sql_query_delete;
EXECUTE stmt_delete;
DEALLOCATE PREPARE stmt_delete;

-- Re-enable safe updates after the operation
SET SQL_SAFE_UPDATES = 1;


-- Re-enable safe updates after the operation
SET SQL_SAFE_UPDATES = 1;


-- Re-enable safe updates after the operation
SET SQL_SAFE_UPDATES = 1;
-- END code for deleting options data and archieving them into a separate table


--delete rows by date_entry
SET SQL_SAFE_UPDATES = 0;
DELETE FROM optionstbl WHERE DATE(date_entry) = '2025-02-17';
SET SQL_SAFE_UPDATES = 1;
--end delete rows by date_entry