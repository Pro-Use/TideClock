import datetime
import sqlite3
from time import sleep, time

DBPATH = './barnstaple_tide_heights'
STEPS = 200
HIGH = STEPS * 0.25
LOW = STEPS * 0.75
TABLE = 'Barnstable_2025_2075'
TOLERANCE = 4

data_range = False
data_month_range = False


def getRange(diff=0):
    now = datetime.datetime.now().timestamp() - diff
    yesterday = now - 86400
    tomorrow = now + 86400
    query = f"SELECT timestamp,date,time,height FROM {TABLE} WHERE timestamp BETWEEN {yesterday} AND {tomorrow} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def getMonthRange(now):
    # now = datetime.datetime.now().timestamp()
    nine_days_ago = now - (1209600/2)
    nine_days_ahead = now + (1209600/2)
    query = f"SELECT timestamp,date,time,height_diff FROM {TABLE} WHERE timestamp BETWEEN {nine_days_ago} AND {nine_days_ahead} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def findPosIndex(data, currentTime):
    for i in range(len(data)-1):
        t1 = data[i][0]
        t2 = data[i+1][0]
        if t1 < currentTime <= t2:
            print(f"Found position index: {i}, {data[i]} and {data[i+1]}")
            return data[i], data[i+1], i
    return None

def findNeapSpring(data, currentIndex, now):
    if now > data[currentIndex][0]:
        currentIndex += 1 # adjust for same day/time
    before = data[0:currentIndex]
    after = data[currentIndex:]
    max_index_before, max_row_before = max(enumerate(before), key=lambda x: x[1][3])
    max_index_after, max_row_after = max(enumerate(after), key=lambda x: x[1][3])
    max_index_after += len(before)
    print(f"Max height_diff before at index {max_index_before}, {data[max_index_before]}")
    print(f"Max height_diff after at index {max_index_after}, {data[max_index_after]}")
    # Is nearest spring before or after?
    time_before = abs(now - max_row_before[0])
    time_after = abs(now - max_row_after[0])
    print(f"Time before: {time_before}, Time after: {time_after}")
    if time_before < time_after:
        print("Nearest spring is before")
        max_index = max_index_before
        max_row = max_row_before
        min_index, min_row = min(enumerate(after), key=lambda x: x[1][3])
        min_index += len(before)
        print(f"Max height_diff: { max_row} at index {max_index}, {data[max_index]}")
        print(f"Min height_diff: { min_row} at index {min_index}, {data[min_index]}")
        return max_row, min_row   
        
    else:
        print("Nearest spring is after")
        max_index = max_index_after
        max_row = max_row_after
        min_index, min_row = min(enumerate(before), key=lambda x: x[1][3])
        print(f"Max height_diff: { max_row} at index {max_index}, {data[max_index]}")
        print(f"Min height_diff: { min_row} at index {min_index}, {data[min_index]}")
        return min_row, max_row   
    
            

def tideStepperPos(prev, next, now):
    ebb_flow_time = next[0] - prev[0]
    time_since_prev = now - prev[0]
    proportion = time_since_prev / ebb_flow_time
    # direction!
    dir_mod = 0
    if next[3] > prev[3]:
        dir_mod = 100 # flooding
    return (int((STEPS / 2) * proportion) + dir_mod) % STEPS

if __name__ == "__main__":
    CONN = sqlite3.connect(DBPATH)
    CURSOR = CONN.cursor()

    #Tide Height
    data_range = getRange()
    now = datetime.datetime.now().timestamp()
    cur_index = findPosIndex(data_range, now)
    print(f"Current time: {datetime.datetime.now()}, Previous: {cur_index[0][1]} {cur_index[0][2]} height: {cur_index[0][3]}, Next: {cur_index[1][1]} {cur_index[1][2]} height: {cur_index[1][3]}")
    tideStep = tideStepperPos(cur_index[0], cur_index[1], now)
    print("Tide Step: %d" % tideStep)

    #TODO Ebb Flow - phase shift...
    
    #lunar
    # now = datetime.datetime.now().timestamp()
    now = datetime.datetime.strptime("19/04/2026 06:58:00", "%d/%m/%Y %H:%M:%S").timestamp()
    data_month_range = getMonthRange(now)
    month_index = findPosIndex(data_month_range, now)
    before, after = findNeapSpring(data_month_range, month_index[2], now)
    neapSpringStep = tideStepperPos(before, after, now)
    print("Neap Spring Step: %d" % neapSpringStep)
        
    
    
