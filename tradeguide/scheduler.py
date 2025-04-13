import time
import schedule
import threading
import os
import json
from datetime import datetime, time as datetime_time
from flask import session, current_app

data_file = "data.json"

# Global variable to track if scheduler is already running
scheduler_running = False

# Function to read from the JSON file
def read_data_from_file():
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
            # Return expiry1, expiry2, expiry3, and instrumentkey from the file
            return data.get('expiry1', ''), data.get('expiry2', ''), data.get('expiry3', ''), data.get('instrumentkey', '')
    else:
        return '', '', '', ""  # Default values if the file does not exist


# Scheduler function to check for missed tasks and handle future tasks
def run_scheduler():
    while True:
        current_time = datetime.now()

        # Check if any tasks have been missed
        for job in schedule.get_jobs():
            job_time = job.next_run
            # If the current time is later than the scheduled time for a job, run it
            if current_time > job_time:
                print(f"Missed scheduled time {job_time.strftime('%H:%M')}. Running missed job.")
                job.job_func()  # Execute the missed task
                schedule.cancel_job(job)  # Remove the job after execution

        schedule.run_pending()  # Run the pending scheduled tasks
        time.sleep(1)  # Sleep for 1 second to avoid 100% CPU usage


# Function to run the job at specific times
def job(access_token):
    # Push the app context manually
    from app import app
    with app.app_context():
        print('Reached job')
        #print(access_token)

        if access_token:
            expiry1, expiry2, expiry3, instrumentkey = read_data_from_file()
            now = datetime.now()
            print(f"Now is: {now}")

            # Execute the task
            print("Executing scheduled task...")
            from app import startrecord
            startrecord(expiry1, expiry2, expiry3, instrumentkey, access_token)
        else:
            print("No access token found. Skipping job.")


# Function to schedule job at specific times
def schedule_job_times(access_token):
    # Define the times you want to run the job
    
    times = [
    "09:21", "09:26", "09:31", "09:36", "09:41", "09:46", "09:51", 
    "09:56", "10:01", "10:06", "10:11", "10:16", "10:21", "10:26", 
    "10:31", "10:36", "10:41", "10:46", "10:51", "10:56", "11:01", 
    "11:06", "11:11", "11:16", "11:21", "11:26", "11:31", "11:36", 
    "11:40", "11:46", "11:51", "11:56", "12:01", "12:06", "12:11", 
    "12:16", "12:21", "12:26", "12:31", "12:36", "12:41", "12:46", 
    "12:51", "12:56", "13:01", "13:06", "13:11", "13:16", "13:21", 
    "13:26", "13:31", "13:36", "13:41", "13:46", "13:51", "13:56", 
    "14:01", "14:06", "14:11", "14:16", "14:21", "14:26", "14:31", 
    "14:36", "14:40", "14:46", "14:50", "14:56", "15:00", "15:06", 
    "15:11", "15:15", "15:21", "15:26", "15:30", "15:35", "08:55",
    "16:00", "23:05", "23:10", "23:15", "23:20", "23:25", "23:30",
    "23:35", "23:40", "23:45", "23:50", "23:55", "00:00", "18:15",
    "09:00", "09:16"
    
    ]


    # Convert each time string to a datetime object and schedule the job
    for time_str in times:
        hour, minute = map(int, time_str.split(":"))
        schedule_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Schedule the job to run at each specified time
        schedule.every().day.at(schedule_time.strftime("%H:%M")).do(job, access_token=access_token)


# Function to start the scheduler in a separate thread
def start_scheduler():
    global scheduler_running

    # Ensure that the scheduler is only started if there's an access token and if it's not already running
    access_token = session.get('access_token', None)

    if access_token and not scheduler_running:
        print("Starting scheduler...")

        # Set the flag to True indicating scheduler is running
        scheduler_running = True

        # Schedule jobs for specific times
        schedule_job_times(access_token)

        # Start the scheduler in a new thread
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True  # Daemon thread will exit when the main program exits
        scheduler_thread.start()
    elif scheduler_running:
        print("Scheduler is already running.")
    else:
        print("No access token found, skipping scheduler startup.")
# Testing the scheduler