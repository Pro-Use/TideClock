import datetime
import sqlite3
from time import sleep, time

DBPATH = './barnstaple_tide_heights'
STEPS = 200
HIGH = STEPS * 0.25
LOW = STEPS * 0.75
TABLE = 'Barnstable_2025_2075'
TOLERANCE = 4
SECONDS_IN_DAY = 86400
WINDOW_DAYS = 7.5

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
    four_days_ago = now - (691200/2)
    four_days_ahead = now + (691200/2)
    query = f"SELECT timestamp,date,time,height_diff FROM {TABLE} WHERE timestamp BETWEEN {four_days_ago} AND {four_days_ahead} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def getNextWindow(now):
    windowAhead = now + (WINDOW_DAYS * SECONDS_IN_DAY)
    bufferBehind = now - SECONDS_IN_DAY
    query = f"SELECT timestamp,date,time,height_diff FROM {TABLE} WHERE timestamp BETWEEN {bufferBehind} AND {windowAhead} ORDER BY timestamp ASC"
    CURSOR.execute(query)
    rows = CURSOR.fetchall()
    return rows

def getPrevWindow(now, tsBehind):
    query = f"SELECT timestamp,date,time,height_diff FROM {TABLE} WHERE timestamp BETWEEN {tsBehind} AND {now} ORDER BY timestamp ASC"
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

def findNeapSpring(now):
    window_Ahead = getNextWindow(now)
    max_index, max_row = max(enumerate(window_Ahead), key=lambda x: x[1][3])
    min_index, min_row = min(enumerate(window_Ahead), key=lambda x: x[1][3])
    print(f"Max height_diff overall at index {max_index}, {window_Ahead[max_index]}")
    print(f"Min height_diff overall at index {min_index}, {window_Ahead[min_index]}")
    time_to_spring = max_row[0] - now
    time_to_neap = min_row[0] - now
    print(f"Time to Spring: {time_to_spring},Time to Neap: {time_to_neap}")
    # Are we nearer to the spring or neap?
    if time_to_neap < 0 or time_to_spring < time_to_neap and time_to_spring > 0:
        print("Approaching spring")
        window_behind_time = (WINDOW_DAYS * SECONDS_IN_DAY) - time_to_spring
        window_behind = getPrevWindow(now, now - window_behind_time)
        min_index, min_row = min(enumerate(window_behind), key=lambda x: x[1][3])
        print(f"Time of neap: {min_row[1]} {min_row[2]}, Time of spring: {max_row[1]} {max_row[2]}")
        return min_row, max_row   
    else:
        print("Approaching neap")
        window_behind_time = (WINDOW_DAYS * SECONDS_IN_DAY) - time_to_neap
        window_behind = getPrevWindow(now, now - window_behind_time)
        max_index, max_row = max(enumerate(window_behind), key=lambda x: x[1][3])
        print(f"Time of spring: {max_row[1]} {max_row[2]}, Time of neap: {min_row[1]} {min_row[2]}")
        return max_row, min_row   
        
    
    
            

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

    # #Tide Height
    # data_range = getRange()
    # now = datetime.datetime.now().timestamp()
    # cur_index = findPosIndex(data_range, now)
    # print(f"Current time: {datetime.datetime.now()}, Previous: {cur_index[0][1]} {cur_index[0][2]} height: {cur_index[0][3]}, Next: {cur_index[1][1]} {cur_index[1][2]} height: {cur_index[1][3]}")
    # tideStep = tideStepperPos(cur_index[0], cur_index[1], now)
    # print("Tide Step: %d" % tideStep)

    # #TODO Ebb Flow - phase shift...
    
    #lunar
    now = datetime.datetime.now().timestamp()
    now = datetime.datetime.strptime("2026-04-19 10:59:02.571717", "%Y-%m-%d %H:%M:%S.%f").timestamp()
    print(f"Now: {datetime.datetime.fromtimestamp(now)}")
    before, after = findNeapSpring(now)
    neapSpringStep = tideStepperPos(before, after, now)
    print("Neap Spring Step: %d" % neapSpringStep)
        
    
    
