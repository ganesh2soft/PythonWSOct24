import time
import schedule
import threading
import os
import json
from datetime import datetime, time as datetime_time
from flask import session, current_app

data_file = "data.json"

# Function to read from the JSON file
def read_data_from_file():
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Return expiry1, expiry2, expiry3, and instrumentkey from the file
            return data.get('expiry1', ''), data.get('expiry2', ''), data.get('expiry3', ''), data.get('instrumentkey', '')
    else:
        return '', '', '', ""  # Default values if the file does not exist

def job(access_token):
    # We manually push an app context in this background job to allow usage of `current_app`
    from app import app  # Import your Flask app instance here
    with app.app_context():  # Manually push the app context
        print('Reached job ')
        print(access_token)

        if access_token:
            expiry1, expiry2, expiry3, instrumentkey = read_data_from_file()
            now = datetime.now()
            print(f"Now is: {now}")

            # Define the time window as datetime.time objects for comparison
            start_time = datetime_time(0, 10)  # 01:55 AM
            end_time = datetime_time(23, 50)   # 08:30 PM

            # Check if current time is within the window (1:55 AM to 8:30 PM)
            if start_time <= now.time() <= end_time:
                print("Scheduled task triggered!")
                # Import your startrecord function and execute it
                from app import startrecord
                startrecord(expiry1, expiry2, expiry3, instrumentkey,access_token)
            else:
                print("Outside of scheduled time window.")
        else:
            print("No access token found. Skipping job.")
# Scheduler function to run every 2 minutes
def run_scheduler():
    while True:
        schedule.run_pending()  # Run the pending scheduled tasks
        time.sleep(1)  # Sleep for 1 second to avoid 100% CPU usage

# Function to start the scheduler in a separate thread
def start_scheduler():
    print('start scheduler block reached')
    # Ensure that the scheduler is only started if there's an access token in the session
    access_token = session.get('access_token', None)

    if access_token:
        print("Starting scheduler...")

        # Schedule the job function to run every 2 minutes
        #schedule.every(2).minutes.do(job(access_token))  # Correctly schedule the job here
        
        schedule.every(10).minutes.do(lambda: job(access_token))

        # Start the scheduler in a new thread
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True  # Daemon thread will exit when the main program exits
        scheduler_thread.start()
    else:
        print("No access token found, skipping scheduler startup.")
