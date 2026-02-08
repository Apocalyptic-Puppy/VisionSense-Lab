import pydirectinput
import win32gui
from pip._vendor.distlib.compat import raw_input
from datetime import datetime
import requests
import threading
import handler
import time
import random
from pynput.keyboard import Key, Controller
from PIL import ImageGrab
import pyttsx3
import os
from socket import *
pydirectinput.FAILSAFE = False
keyboard = Controller()

# Maple window name
MAPLE_WINDOW_NAME = 'MapleStory'

JUMP_KEY = 'alt'

BUFF_TIME = 33 * 1  # Seconds
LOOP_COUNT = 1
skill_3s=time.time()
skill_6s=time.time()
skill_9s=time.time()
skill_10s=time.time()
skill_15s=time.time()
skill_60s=time.time()
skill_120s=time.time()
feed_pet_time=time.time()
summon=time.time()
last_q_press=time.time()
last_attack_while_moving = 0.0
last_press_1 = time.time() - 1000
last_press_2 = time.time() - 1000
last_press_3 = time.time() - 1000
attack_thread_lock = threading.Lock()
attack_thread_active = False
pause_q_during_move = False  # Flag to pause q during skill execution in attack_while_moving
initial_skill_sync_done = False
initial_skill_sync_time = 0.0
initial_skill_sync_lock = threading.Lock()
LOOP_SLEEP_ACTIVE_MIN = 0.05  # min delay when bot is running
LOOP_SLEEP_ACTIVE_MAX = 0.1   # max delay when bot is running
LOOP_SLEEP_IDLE = 0.4         # delay when bot is paused
LOOP_SLEEP_NO_COORD = 0.15    # delay when coords are not ready

def startBot():
    # timeout skills
    buffTimeOut = time.time()
    LOOP_COUNT = 1

    time.sleep(1)
    global summon, feed_pet_time
    summon = time.time() - 61  # Force summon on first run (80s interval)
    # feed_pet_time = time.time() - 601  # Force feed_pet on first run (10 minutes in past)
    toxic_forest_1()

    while True:
        if not handler.botThread.isRunning():
            time.sleep(LOOP_SLEEP_IDLE)
            continue

        if handler.gameMonitorInstance.getPlayerCoords() is None:
            time.sleep(LOOP_SLEEP_NO_COORD)
            continue

        # Don't touch
        currentTime = time.time()
        toxic_forest_1()
        attack()
        time.sleep(random.uniform(LOOP_SLEEP_ACTIVE_MIN, LOOP_SLEEP_ACTIVE_MAX))

def attack():
    global last_q_press
    # Skip skill execution if attack_while_moving thread is active (to avoid conflicts)
    if not attack_thread_active:
        ensure_initial_skill_sync()
        skills_9s()
        skills_10s()
    # skills_60s()
    # feed_pet()
    # skills_120s()
    now = time.time()
    # Skip q if in attack_while_moving thread
    if not attack_thread_active:
        # Avoid q immediately after initial 1/2/3 sync to reduce input conflicts
        if initial_skill_sync_time and time.time() - initial_skill_sync_time < 0.3:
            return
        pydirectinput.press('q', 1, 0)


def ensure_initial_skill_sync():
    global initial_skill_sync_done, initial_skill_sync_time
    global last_press_1, last_press_2, last_press_3, skill_10s, skill_9s, skill_60s
    if initial_skill_sync_done:
        return False
    with initial_skill_sync_lock:
        if initial_skill_sync_done:
            return False
        # Press 1/2/3 once to align cooldowns at start
        pydirectinput.press('1', 1, 0)
        time.sleep(0.06)
        pydirectinput.press('2', 1, 0)
        time.sleep(0.06)
        pydirectinput.press('3', 1, 0)
        sync_time = time.time()
        last_press_1 = sync_time
        last_press_2 = sync_time
        last_press_3 = sync_time
        # Align other skill timers that also use 1/2/3
        skill_10s = sync_time
        skill_9s = sync_time
        skill_60s = sync_time
        initial_skill_sync_time = sync_time
        initial_skill_sync_done = True
        return True


def attack_while_moving(min_interval=0):
    """
    Fire continuous q attacks during movement (e.g., double jump).
    Q: every 1.0-1.2 seconds (random interval)
    Skill 1: every 8.2 seconds
    Skill 2: every 9 seconds  
    Skill 3: every 25 seconds
    Pauses q when skills are ready to avoid input conflicts.
    """
    global last_attack_while_moving, attack_thread_active, last_press_1, last_press_2, last_press_3, pause_q_during_move, initial_skill_sync_done
    now = time.time()
    with attack_thread_lock:
        if attack_thread_active:
            return
        if now - last_attack_while_moving < min_interval:
            return
        attack_thread_active = True
        last_attack_while_moving = now

    def _attack_worker():
        global attack_thread_active, last_press_1, last_press_2, last_press_3, pause_q_during_move, initial_skill_sync_done
        try:
            worker_start = time.time()
            # Schedule next q press immediately, then every 1.0-1.2s
            next_q_time = worker_start
            
            # Initial sync: press 1/2/3 once so their cooldowns start together
            if ensure_initial_skill_sync():
                # Avoid q right after the sync presses
                next_q_time = time.time() + random.uniform(1.0, 1.2)
            
            # Run for ~2.5 seconds during the double jump window
            while time.time() - worker_start < 2.5:
                now_local = time.time()
                skill_executed = False
                
                # Priority: Check and execute skills when ready
                # Skill 1: 8.2s cooldown - highest priority
                if now_local - last_press_1 >= 8.2:
                    pydirectinput.press('1', 1, 0)
                    last_press_1 = now_local
                    # Reset q timer to avoid immediate conflict
                    next_q_time = now_local + random.uniform(1.0, 1.2)
                    skill_executed = True
                
                # Skill 2: 9s cooldown - second priority
                elif now_local - last_press_2 >= 9:
                    pydirectinput.press('2', 1, 0)
                    last_press_2 = now_local
                    next_q_time = now_local + random.uniform(1.0, 1.2)
                    skill_executed = True
                
                # Skill 3: 25s cooldown - third priority
                elif now_local - last_press_3 >= 25:
                    pydirectinput.press('3', 1, 0)
                    last_press_3 = now_local
                    next_q_time = now_local + random.uniform(1.0, 1.2)
                    skill_executed = True
                
                # Only press q if no skill was just executed
                if not skill_executed and now_local >= next_q_time:
                    pydirectinput.press('q', 1, 0)
                    # Schedule next q with random interval 1.0-1.2s
                    next_q_time = now_local + random.uniform(1.0, 1.2)
                
                time.sleep(0.05)  # Small sleep to avoid busy loop
                
        finally:
            with attack_thread_lock:
                attack_thread_active = False
            pause_q_during_move = False

    threading.Thread(target=_attack_worker, daemon=True).start()


def isInRange(targetX, targetY, playerCoords, wantedRange):
    xRange = abs(targetX - playerCoords.x)
    yRange = abs(targetY - playerCoords.y)
    return xRange < wantedRange and yRange < wantedRange


def goTo(targetX, targetY, rangeFromCoords, isRune=False):
    WANTED_RANGE = rangeFromCoords
    if handler.gameMonitorInstance.getPlayerCoords() is not None:

        # Get the updated coordinates from the monitor gui
        currentPlayerLocation = handler.gameMonitorInstance.getPlayerCoords()

        xDistance = targetX - currentPlayerLocation.x
        while abs(xDistance) > WANTED_RANGE and handler.botThread.isRunning():  # Check the X axis
            goToDirection('RIGHT', xDistance) if xDistance > 0 else goToDirection('LEFT', xDistance)
            currentPlayerLocation = handler.gameMonitorInstance.getPlayerCoords()
            xDistance = targetX - currentPlayerLocation.x

        yDistance = targetY - currentPlayerLocation.y
        time.sleep(0.3)
        while abs(yDistance) > WANTED_RANGE and handler.botThread.isRunning():  # Check the Y Axis
            if yDistance > 0:
                goDown()
                wait_for_descent_settle()
            else:
                # try to go up; if goUp returns False (failed within timeout),
                # attempt to correct X position first then retry going up
                success = goUp(targetY)
                if not success:
                    # attempt to correct X until within WANTED_RANGE, then retry
                    currentPlayerLocation = handler.gameMonitorInstance.getPlayerCoords()
                    xDistance = targetX - currentPlayerLocation.x
                    while abs(xDistance) > WANTED_RANGE and handler.botThread.isRunning():
                        goToDirection('RIGHT', xDistance) if xDistance > 0 else goToDirection('LEFT', xDistance)
                        currentPlayerLocation = handler.gameMonitorInstance.getPlayerCoords()
                        xDistance = targetX - currentPlayerLocation.x
                    # after X correction, continue loop which will call goUp again
                else:
                    wait_for_descent_settle()
            time.sleep(0.1)
            if isRune:
                time.sleep(0.85)
            currentPlayerLocation = handler.gameMonitorInstance.getPlayerCoords()
            yDistance = targetY - currentPlayerLocation.y


def goToDirection(direction, distance):
    pydirectinput.PAUSE = 0.005
    if abs(distance) >= 25:  # Check if this is long enough for double jump
        pydirectinput.keyDown(direction.lower())
        # pydirectinput.press(JUMP_KEY, 1, 0.05)
        pydirectinput.press(JUMP_KEY, 1, 0)
        time.sleep(0.2)
        pydirectinput.press(JUMP_KEY, 1, 0)
        threading.Thread(target=attack_while_moving, daemon=True).start()
        # pydirectinput.press(TP_KEY) - Use me if you are using teleport (Kanna, Mage...)
        pydirectinput.keyUp(direction.lower())
    else:
        # change hold time based on distance
        # the closer the distance, the shorter the hold time
        hold_time = min(0.25, max(0.05, abs(distance) / 100)) 
        holdKey(direction.lower(), hold_time)

# Movements
def holdKey(key, hold_time):
    # Hold a key for the requested duration without busy-waiting.
    pydirectinput.keyDown(key)
    time.sleep(hold_time)
    pydirectinput.keyUp(key)

def goUp(targetY):
    """
    Try to move the player up toward targetY. If movement toward targetY
    succeeds within 10 seconds, return True. If not, return False so caller
    can attempt X-correction and retry.
    """
    start = time.time()
    # read initial position
    current = handler.gameMonitorInstance.getPlayerCoords()
    if current is None:
        return False
    prev_y = current.y
    # Try for up to 10 seconds
    while time.time() - start < 10 and handler.botThread.isRunning():
        # recompute distance to target
        current = handler.gameMonitorInstance.getPlayerCoords()
        if current is None:
            return False
        distance = targetY - current.y
        # if already within small epsilon, success
        if abs(distance) < 1:
            return True

        # If distance magnitude is reasonably large, try rope lift
        # if abs(distance) >= 5 and abs(distance) < 20:
        #     pydirectinput.keyDown('up')
        #     pydirectinput.press(JUMP_KEY) # Adele upjump
        #     time.sleep(0.3)
        #     pydirectinput.press(JUMP_KEY) # Adele upjump
        #     pydirectinput.keyUp('up')
        if abs(distance) >= 5:
            pydirectinput.press('x') #rope lift
            time.sleep(1.0)
        else:
            pydirectinput.press("alt")

        # brief pause then re-check position
        time.sleep(0.15)
        current = handler.gameMonitorInstance.getPlayerCoords()
        if current is None:
            return False
        # success if moved closer to targetY
        if abs(targetY - current.y) < abs(targetY - prev_y):
            return True
        prev_y = current.y

    # timed out
    return False

def goDown():
    sleep_duration = random.uniform(0.8, 0.9)
    pydirectinput.keyDown('down')
    pydirectinput.press(JUMP_KEY)
    time.sleep(0.3)
    pydirectinput.keyUp('down')
    sleep_duration = random.uniform(0.5, 0.6)
    time.sleep(sleep_duration)

def wait_for_descent_settle(max_wait=1.5, stable_checks=3, check_interval=0.12, idle_threshold=1):
    """
    After triggering a drop, wait until Y movement settles so we do not spam goDown.
    """
    start = time.time()
    prev = handler.gameMonitorInstance.getPlayerCoords()
    stable_count = 0
    while time.time() - start < max_wait and handler.botThread.isRunning():
        time.sleep(check_interval)
        current = handler.gameMonitorInstance.getPlayerCoords()
        if current is None or prev is None:
            prev = current
            continue
        if abs(current.y - prev.y) <= idle_threshold:
            stable_count += 1
            if stable_count >= stable_checks:
                break
        else:
            stable_count = 0
        prev = current

def jumpDown():
    sleep_duration = random.uniform(0.8, 0.9)
    pydirectinput.keyDown('down')
    pydirectinput.press(JUMP_KEY)
    time.sleep(0.3)
    pydirectinput.keyUp('down')
    sleep_duration = random.uniform(0.5, 0.6)
    time.sleep(sleep_duration)

# Skills
def skills_10s():
    global skill_10s
    current_time = time.time()
    if current_time - skill_10s >= 9:
        sleep_duration = random.uniform(0.29, 0.39)
        time.sleep(sleep_duration)
        pydirectinput.press('1', 1, 0)
        skill_10s = time.time()
        try:
            global last_press_1
            last_press_1 = time.time()
        except NameError:
            pass
def skills_9s():
    global skill_9s
    current_time = time.time()
    if current_time - skill_9s >= 11:
        sleep_duration = random.uniform(0.29, 0.39)
        time.sleep(sleep_duration)
        pydirectinput.press('2', 1, 0)
        skill_9s = time.time()
        try:
            global last_press_2
            last_press_2 = time.time()
        except NameError:
            pass
def skills_15s():
    global skill_15s
    current_time = time.time()
    if current_time - skill_15s >= 15:
        sleep_duration = random.uniform(0.29, 0.39)
        time.sleep(sleep_duration)
        pydirectinput.press('4', 1, 0)
        skill_15s = time.time()
def skills_60s():
    global skill_60s
    current_time = time.time()
    # repurposed to 24s cooldown for key '3'
    if current_time - skill_60s >= 24:
        sleep_duration = random.uniform(1.0, 1.5)
        time.sleep(sleep_duration)
        pydirectinput.press('3', 1, 0)
        skill_60s = time.time()
        try:
            global last_press_3
            last_press_3 = time.time()
        except NameError:
            pass
def skills_120s():
     global skill_120s
     current_time = time.time()
     if current_time - skill_120s >= 120:
        sleep_duration = random.uniform(1, 1.2)
        time.sleep(sleep_duration)
        pydirectinput.press('g', 1, 0)
        time.sleep(sleep_duration)
        pydirectinput.press('h', 1, 0)
        skill_120s = time.time()
def feed_pet():
    global feed_pet_time
    current_time = time.time()
    if current_time - feed_pet_time >= 600:
        for _ in range(6):  # press 6 times
            pydirectinput.press('f', 1, 0)
            time.sleep(0.05) 
        feed_pet_time = time.time()

# def shiesty():
#      global summon
#      current_time = time.time()
#      if current_time - summon >= 60:
#         sleep_duration = random.uniform(0.29, 0.39)
#         time.sleep(sleep_duration)
#         #pydirectinput.press('3', 1, 0)
#         time.sleep(0.5)
#         jumpDown()
#         time.sleep(0.8)
#         pydirectinput.press('s')
#         time.sleep(1)
#         pydirectinput.press('up')
#         time.sleep(1)
#         pydirectinput.press('3')
#         time.sleep(1)
#         summon = time.time()

# harsh winter 4
        # goTo(29,72,1) bot left
        # goTo(31,43,1) top left
def harsh_winter_4():
     global summon
     current_time = time.time()
     if current_time - summon >= 60:
        sleep_duration = random.uniform(0.9, 1.05)
        time.sleep(sleep_duration)
        jumpDown()
        goTo(32,72,1)
        pydirectinput.press("2")
        time.sleep(sleep_duration)
        jumpDown()
        time.sleep(sleep_duration)
        pydirectinput.press("3")
        time.sleep(sleep_duration)
        pydirectinput.press("up")
        time.sleep(sleep_duration)
        pydirectinput.press("3")
        time.sleep(sleep_duration)
        jumpDown()
        time.sleep(sleep_duration)
        goTo(132,58,1)
        pydirectinput.press("3")
        goTo(82,58,1)
        summon = time.time()

# eastern_outskirts
        # goTo(33,71,1) bot left
        # goTo(75,71,1) mid bot
        # goTo(110,71,1) bot right
        # goTo(88,41,1) top right
        # goTo(34,38,1) top left
        # goTo(37,54,1) mid left(attack here)


def eastern_outskirts():
    global summon
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    if current_time - summon >= 60:
        sleep_duration = random.uniform(0.9, 1.05)
        goTo(36,71,1)
        goTo(75,71,1)
        pydirectinput.press("3")
        goTo(110,71,1)
        pydirectinput.press("3")
        goTo(88,41,1)
        pydirectinput.press("3")
        goTo(32,38,1)
        pydirectinput.press("2")
        time.sleep(sleep_duration)
        # timeout check
        if time.time() - start_time > timeout:
            print("Timeout! Moving to safe point")
        goTo(36,54,1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        summon = time.time()

# giant coral colony 2
        # goTo(30,36,1) top left
        # goTo(72,35,1) top mid
        # goTo(138,33,1) top right
        # goTo(112,53,1) mid right
        # goTo(47,67,1) bot left (attack here)
        
def gcc2():
     global summon
     current_time = time.time()
     if current_time - summon >= 60:
        sleep_duration = random.uniform(0.9, 1.05)
        goTo(30,36,1)
        pydirectinput.press("3")
        goTo(72,35,1)
        pydirectinput.press("3")
        goTo(138,33,1)
        pydirectinput.press("3")
        goTo(112,53,1)
        pydirectinput.press("2")
        # time.sleep(sleep_duration)
        goTo(47,67,1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        summon = time.time() 

# def enfolding_forest_1()


def bottom_deck_3():
    global summon
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    if current_time - summon >= 60:
        sleep_duration = random.uniform(0.4, 0.5)
        goTo(40,78,1)
        pydirectinput.press("3")
        goTo(50,49,1)
        pydirectinput.press("3")
        goTo(64,49,1)
        goTo(96,49,1)
        pydirectinput.press("3")
        goTo(140,51,1)
        pydirectinput.press("2")
        goTo(145,78,1)
        goTo(118,78,1)
        # timeout check
        if time.time() - start_time > timeout:
            print("Timeout! Moving to safe point")
            goTo(118,78,1)
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('left')
        summon = time.time()


def lower_path():
    global summon
    current_time = time.time()
    timeout = 30  
    start_time = time.time()
    if current_time - summon >= 60:
        summon = current_time  # Start the 80s countdown at the moment tt_1 begins
        goTo(188,39,1)
        pydirectinput.press("w")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(201, 39, 1)
        goTo(98, 39, 1)


def toxic_forest_1():
    global summon
    current_time = time.time()
    timeout = 30  
    start_time = time.time()
    if current_time - summon >= 60:
        summon = current_time  # Start the 80s countdown at the moment tt_1 begins
        goTo(194,13,1)
        pydirectinput.press("w")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(194, 47, 1)
        goTo(51, 47, 1)

def labyrinth_core_6():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skillsw
    current_time = time.time()
    timeout = 30  # seconds1q
    start_time = time.time()
    
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(138, 39, 1)
        pydirectinput.press("w")
        goTo(114, 39, 1)
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('left')
        pydirectinput.press("e")
        goTo(145, 58, 1)
        goTo(120, 58, 1)
        goTo(74, 58, 1)
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(47, 76, 1)
        time.sleep(random.uniform(0.2, 0.3))
        goTo(153, 76, 1)
        time.sleep(random.uniform(0.2, 0.3))

def library_6():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(39, 36, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")
        goTo(64, 36, 1)
        time.sleep(random.uniform(0.1, 0.2))
        goTo(96, 36, 1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        time.sleep(random.uniform(1.2, 1.3))
        pydirectinput.press("e")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(158, 69, 1)
        goTo(15, 69, 1)

def theater_3():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(39, 35, 1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        time.sleep(random.uniform(1, 1.1))
        pydirectinput.press("e")
        
        goTo(127, 42, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(159, 73, 1)
        goTo(40, 73, 1)

def alley_4():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(46, 42, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")

        goTo(90, 43, 1)
        time.sleep(random.uniform(0.1, 0.2))    
        pydirectinput.press(JUMP_KEY, 1, 0)
        time.sleep(random.uniform(0.1, 0.12))    
        pydirectinput.press('c', 1, 0)
        goTo(116, 40, 1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        time.sleep(random.uniform(1, 1.1))
        pydirectinput.press("e")
        goTo(160, 57, 1)
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(160, 72, 1)
        goTo(32, 72, 1)

def lab_4():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(44, 49, 1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        time.sleep(random.uniform(0.5, 0.6))
        pydirectinput.press("e")

        goTo(167, 49, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(167, 77, 1)
        goTo(44, 77, 1)

def summer_4():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(31, 33, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")

        goTo(105, 34, 1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        time.sleep(random.uniform(0.5, 0.6))
        pydirectinput.press("e")

    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(160, 64, 1)
        goTo(29, 64, 1)

def autumn_4():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(43, 39, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")

        goTo(112, 39, 1)
        time.sleep(random.uniform(0.5, 0.6))

        goTo(156, 37, 1)
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('left')
        time.sleep(random.uniform(0.5, 0.6))
        pydirectinput.press("e")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(164, 68, 1)
        goTo(28, 68, 1)

def winter_4():
    global summon
    # Run continuously: every 60 seconds, restart the cycle from skills
    current_time = time.time()
    timeout = 30  # seconds
    start_time = time.time()
    # Execute skills and then loop for 60 seconds
    if current_time - summon >= 60:
        summon = time.time()  # Reset timer immediately after triggering
    
    # Always check if we should execute skills again (every 60s)
    if time.time() - summon < 5:  # First 5 seconds after trigger: execute skills
        goTo(37, 43, 1)
        time.sleep(random.uniform(0.3, 0.4))
        pydirectinput.press("w")

        goTo(104, 43, 1)
        time.sleep(random.uniform(0.5, 0.6))

        goTo(161, 43, 1)
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('left')
        time.sleep(random.uniform(0.5, 0.6))
        pydirectinput.press("e")
    else:
        # Rest of the 60 seconds: keep moving between two points
        goTo(169, 72, 1)
        goTo(15, 72, 1)


def calm_beach_2():
    global summon
    current_time = time.time()
    timeout = 30  
    start_time = time.time()
    if current_time - summon >= 70:
        summon = time.time()  # Reset timer immediately after triggering
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.2, 0.3))
        pydirectinput.keyUp('left')
        pydirectinput.press('3', 1, 0)
        goTo(36,35,1)
        goTo(146,51,1)
        pydirectinput.press("w")
        goTo(102,48,1)
        pydirectinput.press("w")
        goTo(68,48,1)
        pydirectinput.press("w")
        goTo(29,48,1)
        pydirectinput.keyDown('right')
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.keyUp('right')
        summon = time.time()


def tt_1():
    global summon
    current_time = time.time()
    timeout = 30  
    start_time = time.time()
    if current_time - summon >= 75:
        summon = current_time  # Start the 80s countdown at the moment tt_1 begins
        pydirectinput.press('3', 1, 0)
        goTo(32,82,1)
        pydirectinput.press("w")
        goTo(79,80,1)
        pydirectinput.press("w")
        goTo(127,69,1)
        pydirectinput.press("w")
        goTo(145,94,1)
        pydirectinput.keyDown('left')
        time.sleep(random.uniform(0.1, 0.11))
        pydirectinput.keyUp('left')

