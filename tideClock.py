import datetime
import sqlite3
from gpiozero import OutputDevice, Button
from time import sleep, time

DBPATH = '/home/pi/barnstaple_tide_heights'
STEPS = 200
HIGH = STEPS * 0.25
LOW = STEPS * 0.75
TABLE = 'Barnstable_2025_2075'
TOLERANCE = 4
SECONDS_IN_DAY = 86400
WINDOW_DAYS = 7.5

data_range = False
data_month_range = False
old_neap_spring = None


class Stepper:
    def __init__(self, motor_pin, sensor_pin):
        self.STEP = OutputDevice(motor_pin)
        self.sensor = Button(sensor_pin)
        self.MOTOR_STEPS = 200
        self.MICRO = 8
        self.MICROSTEP = 1 / self.MICRO
        self.STEPS = self.MOTOR_STEPS * self.MICRO
        self.position = 0.0  # Current position in steps
        self.triggered_steps = False
        self.triggered_start = 0
        self.triggered_stop = 0
        self.zeroed = False
        self.zero()
        
    def step(self):
        self.STEP.on()
        sleep(0.001)
        self.STEP.off()
        sleep(0.001)
        if self.position >= self.MOTOR_STEPS:
            self.position = 0.0
        else:
            self.position += self.MICROSTEP
        
        # if self.position.is_integer():
        #     print("Stepping... Current position: %.2f" % self.position)
    
    def zero(self, reset=False):
        if not self.zeroed:
            print("Zeroing stepper...")
            start = None
            stop = None
            # Make sure sensor isn't already triggered
            if not reset:
                while self.sensor.is_pressed :
                    self.step()
                # Rotate till sensor triggered
                while not self.sensor.is_pressed:
                    self.step()
            start = self.position
            print(f"Sensor triggered at position {start}")
            # If range of sensor is unknown, continue to find it
            if not self.triggered_steps:
                # Continue till sensor not triggered
                while self.sensor.is_pressed:
                    self.step()
                stop = self.position
                if stop < start:
                    stop += self.MOTOR_STEPS
                print(f"Sensor released at position {stop}")
                # Mid point is zero
                triggered_range = abs(stop - start)
                self.triggered_steps = int(triggered_range / self.MICROSTEP)
                self.triggered_start = self.MOTOR_STEPS - (self.MICROSTEP * (self.triggered_steps // 2))
                self.triggered_start -= TOLERANCE
                self.triggered_stop = 0 + (self.MICROSTEP * (self.triggered_steps // 2))
                self.triggered_stop += TOLERANCE
                print(f"Sensor triggered range is {self.triggered_steps} microsteps", f"from {self.triggered_start} to {self.triggered_stop} in motor steps")
            else:
                print(f"Sensor stop is position {start + (self.triggered_steps * self.MICROSTEP)}")
            mid = (start + (self.MICROSTEP * (self.triggered_steps // 2))) % self.MOTOR_STEPS
            print(f"Zero position set to {mid}")
            # Step to mid
            while self.position != mid:
                self.step()
                # print("self.position:", self.position, "mid:", mid)
                # sleep(0.01)
            self.position = 0.0
            self.zeroed = True
            print("Zeroing complete.")
        else:
            print("Already zeroed, moving and checking sensor...")
            while self.position != 0:
                self.step()
            if not self.sensor.is_pressed:
                print("Warning: zeroing but sensor not active!")
                self.zeroed = False
                self.zero()
                
    def earlyZeroCheck(self):
        if self.sensor.is_pressed:
            # Check both ranges either side of zero
            if (self.triggered_start <= self.position <= self.MOTOR_STEPS):
                return  
            if (0 <= self.position <= self.triggered_stop):
                return
            else:
                print("Warning: not zero target but sensor is active! Position: %.3f start: %.3f stop: %.3f" % (self.position, self.triggered_start, self.triggered_stop))
                self.zeroed = False
                if self.position > 0:
                    self.zero()
                else:
                    self.zero(reset=True)
    
    def lateZeroCheck(self):
        if not self.sensor.is_pressed:
            print("Warning: zero position but sensor not active!")
            self.zeroed = False
            self.zero()

    def moveTo(self, target):
        if target == self.position:
            return
        # Zero if needed
        if target == 0 or self.position > target:
            while self.position > 0:
                self.step()
                self.earlyZeroCheck()
            if target == 0:
                # check sensor
                self.lateZeroCheck()
                return
        # Step to position
        while self.position < target:
            self.step()
            self.earlyZeroCheck()
            

def getRange(now):
    # now = datetime.datetime.now().timestamp()
    yesterday = now - 86400
    tomorrow = now + 86400
    query = f"SELECT timestamp,date,time,height FROM {TABLE} WHERE timestamp BETWEEN {yesterday} AND {tomorrow} ORDER BY timestamp ASC"
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
        if t1 <= currentTime <= t2:
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
    else:
        print("Approaching neap")
        window_behind_time = (WINDOW_DAYS * SECONDS_IN_DAY) - time_to_neap
        window_behind = getPrevWindow(now, now - window_behind_time)
        max_index, max_row = max(enumerate(window_behind), key=lambda x: x[1][3])
        print(f"Time of spring: {max_row[1]} {max_row[2]}, Time of neap: {min_row[1]} {min_row[2]}")
        
    return min_row, max_row              

def tideStepperPos(prev, next, now):
    ebb_flow_time = next[0] - prev[0]
    time_since_prev =now - prev[0]
    proportion = time_since_prev / ebb_flow_time
    # direction!
    dir_mod = 0
    if next[3] > prev[3]:
        dir_mod = 100 # flooding
    return (int((STEPS / 2) * proportion) + dir_mod) % STEPS

if __name__ == "__main__":
    tideHeight = Stepper(motor_pin=26, sensor_pin=19)
    neapSpring = Stepper(motor_pin=13, sensor_pin=6)
    ebbFlow = Stepper(motor_pin=5, sensor_pin=11)
    CONN = sqlite3.connect(DBPATH)
    CURSOR = CONN.cursor()

    while True:
        future = time() + 60
        #Tide Height
        now = datetime.datetime.now().timestamp()
        data_range = getRange(now)
        cur_index = findPosIndex(data_range, now)
        print(f"Current time: {now}, Previous: {cur_index[0][1]} {cur_index[0][2]} height: {cur_index[0][3]}, Next: {cur_index[1][1]} {cur_index[1][2]} height: {cur_index[1][3]}")
        tideStep = tideStepperPos(cur_index[0], cur_index[1], now)
        print("Tide Step: %d" % tideStep)

        #TODO Ebb Flow - phase shift...
        
        #lunar
        
        now = datetime.datetime.now().timestamp()
        before, after = findNeapSpring(now)
        neapSpringStep = tideStepperPos(before, after, now)
        print("Neap Spring Step: %d" % neapSpringStep)
        if old_neap_spring != None:
            if neapSpringStep < old_neap_spring and neapSpringStep > 2:
                print("NEAP SPRING ERROR: Neap spring step decreased")
            elif abs(neapSpringStep - old_neap_spring) > 3:
                print("NEAP SPRING ERROR: Neap spring step changed by more than 3 steps")  
        old_neap_spring = neapSpringStep
            
        # Move steppers
        tideHeight.moveTo(tideStep)
        neapSpring.moveTo(neapSpringStep)
        # TODO ebb 
        ebbFlowVal = (tideStep - 50) % STEPS
        print("Ebb flow step: %d" % ebbFlowVal)
        ebbFlow.moveTo(ebbFlowVal)
        
        # sleep
        delay = future - time()
        if delay > 0:
            sleep(delay)
    
    
