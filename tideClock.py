import datetime
import sqlite3

DBPATH = '/home/rob/local_work/TideClock/barnstaple_tide_heights'
STEPS = 200
HIGH = STEPS * 0.25
LOW = STEPS * 0.75
CONN = sqlite3.connect(DBPATH)
TABLE = 'barnstaple2025'
CURSOR = CONN.cursor()

data_range = False
data_month_range = False

def getRange():
    now = datetime.datetime.now().timestamp()
    yesterday = now - 86400
    tomorrow = now + 86400
    query = f"SELECT timestamp,date,time,height FROM {TABLE} WHERE timestamp BETWEEN {yesterday} AND {tomorrow} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def getMonthRange():
    now = datetime.datetime.now().timestamp()
    month_ago = now - (2592000/2)
    month_ahead = now + (2592000/2)
    query = f"SELECT timestamp,date,time,height_diff FROM {TABLE} WHERE timestamp BETWEEN {month_ago} AND {month_ahead} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def findPosIndex(data, currentTime):
    for i in range(len(data)-1):
        t1 = data[i][0]
        t2 = data[i+1][0]
        if t1 <= currentTime <= t2:
            return data[i], data[i+1], i
    return None

def findNeapSpring(data, currentIndex):
    before = data[0:currentIndex]
    after = data[currentIndex:]
    max_index_before, max_row_before = max(enumerate(before), key=lambda x: x[1][3])
    max_index_after, max_row_after = max(enumerate(after), key=lambda x: x[1][3])
    # Is nearest spring before or after?
    if abs(data[currentIndex][0] - max_row_before[0]) < abs(data[currentIndex][0] - max_row_after[0]):
        max_index = max_index_before
        max_row = max_row_before
        min_index, min_row = min(enumerate(after), key=lambda x: x[1][3])
        min_index += len(before)
        
    else:
        max_index = max_index_after + len(before)
        max_row = max_row_after
        min_index, min_row = min(enumerate(before), key=lambda x: x[1][3])
    
    print(f"Max height_diff: { max_row} at index {max_index}, {data[max_index]}")
    print(f"Min height_diff: { min_row} at index {min_index}, {data[min_index]}")
    return min_row, max_row

        
        

def tideStepperPos(prev, next):
    ebb_flow_time = next[0] - prev[0]
    time_since_prev = datetime.datetime.now().timestamp() - prev[0]
    proportion = time_since_prev / ebb_flow_time
    # direction!
    dir_mod = 0
    if next[3] > prev[3]:
        dir_mod = 100 # flooding
    return int((STEPS / 2) * proportion) + dir_mod

if __name__ == "__main__":
    if not data_range:
        data_range = getRange()
    if not data_month_range:
        data_month_range = getMonthRange()
    now = datetime.datetime.now().timestamp()
    cur_index = findPosIndex(data_range, now)
    print(cur_index)
    month_index = findPosIndex(data_month_range, now)
    
    if cur_index:
        tideStep = tideStepperPos(cur_index[0], cur_index[1])
        print(tideStep)
    
    if month_index:
        before, after = findNeapSpring(data_month_range, month_index[2])
        neapSpringStep = tideStepperPos(before, after)
        print(neapSpringStep)
