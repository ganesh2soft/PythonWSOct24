use traderdb;
SET SQL_SAFE_UPDATES = 0;

-- Define the expiry_date dynamically
SET @expiry_date = '2025-03-20';  -- Change this to the expiry date you need

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