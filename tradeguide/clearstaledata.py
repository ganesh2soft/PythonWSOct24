import json
import sys

# Function to remove stale data (pcr_set entries with a specific expiry date)
def remove_pcr_entry_by_expiry(file_path, expiry_date):
    # Load the data from the trend.json file
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Filter out pcr_set entries where expiry matches the provided expiry_date
    filtered_pcr_set = [entry for entry in data["pcr_set"] if entry["expiry"] != expiry_date]

    # Update the pcr_set with the filtered list
    data["pcr_set"] = filtered_pcr_set

    # Save the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"Entries with expiry {expiry_date} have been removed from pcr_set.")

# Main function to accept command-line arguments
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clearstaledata.py <file_path> <expiry_date>")
        sys.exit(1)

    file_path = sys.argv[1]  # Path to the trend.json file
    expiry_date = sys.argv[2]  # Expiry date to remove, e.g., '2025-03-20'

    # Call the function to remove stale data
    remove_pcr_entry_by_expiry(file_path, expiry_date)
