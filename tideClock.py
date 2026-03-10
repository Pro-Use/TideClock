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

data_range = False
data_month_range = False


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
    tideHeight = Stepper(motor_pin=26, sensor_pin=19)
    neapSpring = Stepper(motor_pin=13, sensor_pin=6)
    ebbFlow = Stepper(motor_pin=5, sensor_pin=11)
    CONN = sqlite3.connect(DBPATH)
    CURSOR = CONN.cursor()

    while True:
        future = time() + 60
        #Tide Height
        data_range = getRange()
        now = datetime.datetime.now().timestamp()
        cur_index = findPosIndex(data_range, now)
        print(f"Current time: {datetime.datetime.now()}, Previous: {cur_index[0][1]} {cur_index[0][2]} height: {cur_index[0][3]}, Next: {cur_index[1][1]} {cur_index[1][2]} height: {cur_index[1][3]}")
        tideStep = tideStepperPos(cur_index[0], cur_index[1])
        print("Tide Step: %d" % tideStep)

        #TODO Ebb Flow - phase shift...
        
        #lunar
        data_month_range = getMonthRange()
        now = datetime.datetime.now().timestamp()
        month_index = findPosIndex(data_month_range, now)
        before, after = findNeapSpring(data_month_range, month_index[2])
        neapSpringStep = tideStepperPos(before, after)
        print("Neap Spring Step: %d" % neapSpringStep)
        
        # Move steppers
        tideHeight.moveTo(tideStep)
        neapSpring.moveTo(neapSpringStep)
        # TODO ebb 
        ebbFlowVal = (tideStep - 50) % STEPS
        ebbFlow.moveTo(ebbFlowVal)
        
        # sleep
        delay = future - time()
        if delay > 0:
            sleep(delay)
    
    
