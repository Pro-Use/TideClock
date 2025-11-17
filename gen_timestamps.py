import sqlite3
import datetime

def generate_timestamps(db_path, table_name):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to retrieve timestamps from the specified table and column
    query = f"SELECT date,time FROM {table_name}"
    cursor.execute(query)

    # Fetch all timestamps
    date_times = cursor.fetchall()
    for date, time in date_times:
        dt = datetime.datetime.strptime(f"{date} {time}", "%d/%m/%y %H:%M:%S")
        ts = int(dt.timestamp())
        # print(dt.timestamp())
        insert = f"UPDATE {table_name} SET timestamp = {ts} WHERE date = '{date}' AND time = '{time}'"
        # print(insert)
        cursor.execute(insert)
        conn.commit()

    # Close the database connection
    conn.close()
    
def genHeightDiffs(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f"SELECT height, timestamp FROM {table_name} ORDER BY timestamp ASC"
    cursor.execute(query)

    heights = cursor.fetchall()
    prev_height = None
    for (height, timestamp) in heights:
        if prev_height is not None:
            diff = abs(height - prev_height)
            print(f"Height: {height}, Difference from previous: {diff}, Timestamp: {timestamp}")
            cursor.execute(f"UPDATE {table_name} SET height_diff = {diff} WHERE timestamp = {timestamp}")
        else:
            print(f"Height: {height}, Difference from previous: N/A, Timestamp: {timestamp}")
        prev_height = height
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_path = 'barnstaple_tide_heights'
    table_name = 'barnstaple2025'

    # timestamps = generate_timestamps(db_path, table_name)
    genHeightDiffs(db_path, table_name)