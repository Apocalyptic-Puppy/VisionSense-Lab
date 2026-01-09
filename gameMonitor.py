import os
from pathlib import Path
from PIL import Image
import screenManager
import gui
import handler
import utils
import numpy
import requests
import time
_LAST_MINIMAP_SAVE_TS = 0
from datetime import datetime

MINIMAP_DUMP_DIR = "minimap_dumps"
MINIMAP_DUMP_INTERVAL_SECONDS = 30
_LAST_MINIMAP_DUMP_TS = 0

BASE_DIR = Path(__file__).resolve().parent
playerIcon = Image.open(BASE_DIR / 'pics' / 'playerIcon.png')
doorIcon = Image.open(BASE_DIR / 'pics' / 'door.png')
runeIcon = Image.open(BASE_DIR / 'pics' / 'runeIcon.png')
ICON_CHECK_INTERVAL_SECONDS = 1.0
DOOR_NOTIFY_COOLDOWN_SECONDS = 90
RUNE_NOTIFY_COOLDOWN_SECONDS = 90
DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://canary.discord.com/api/webhooks/1451374880582008883/01h659Z2IyemSoRuMTXl0ZWD5bg7NE9vYZUZ2tiwJX8I8naz2IPHDM_KmlT5a9aTa3Ad",
)

class GameMonitor:
    def __init__(self, currentHp=None, currentPlayerCoords=None):
        self.currentPlayerCoords = currentPlayerCoords
        self.runeCoords = None
        self._lastDoorCheck = 0
        self._lastDoorNotification = 0
        self._lastRuneCheck = 0
        self._lastRuneNotification = 0

    def setPlayerCoords(self, currentPlayerCoords):
        self.currentPlayerCoords = currentPlayerCoords

    def getPlayerCoords(self):
        return self.currentPlayerCoords


    def start(self):

        while True:
            if handler.gameMonitorThread.isRunning():  # While the running flag is True
                # Player Coords
                currentPlayerLocation = findCoordsOfColor()
                if currentPlayerLocation is not None:
                    self.setPlayerCoords(currentPlayerLocation)
                    gui.updateCurrentCoordinate(currentPlayerLocation)  # Update the live coords in gui
                self._checkIconOnMiniMap(
                    icon=doorIcon,
                    last_check_attr="_lastDoorCheck",
                    last_notify_attr="_lastDoorNotification",
                    cooldown=DOOR_NOTIFY_COOLDOWN_SECONDS,
                    label="Door",
                )
                self._checkIconOnMiniMap(
                    icon=runeIcon,
                    last_check_attr="_lastRuneCheck",
                    last_notify_attr="_lastRuneNotification",
                    cooldown=RUNE_NOTIFY_COOLDOWN_SECONDS,
                    label="Rune",
                )
                time.sleep(0.08)
            else:
                time.sleep(0.3)

    def _checkIconOnMiniMap(self, icon, last_check_attr, last_notify_attr, cooldown, label):
        """Look for a specific icon on the minimap and send a notification once per cooldown window."""
        now = time.time()
        last_check = getattr(self, last_check_attr)
        if now - last_check < ICON_CHECK_INTERVAL_SECONDS:
            return

        setattr(self, last_check_attr, now)
        coords = findCoordsOnMiniMap(icon)
        if coords is None:
            return

        last_notify = getattr(self, last_notify_attr)
        if now - last_notify < cooldown:
            return

        setattr(self, last_notify_attr, now)
        message = f"{label} detected on minimap at ({coords.x}, {coords.y})"
        send_discord_notification(message)

def findCoordsOnMiniMap(innerIcon):
    global _LAST_MINIMAP_DUMP_TS

    miniMapImage = screenManager.getMiniMapScreenshot()
    if miniMapImage is None:
        return None

    # DEBUG: 每 30 秒存一張 minimap 截圖
    # now = time.time()
    # if now - _LAST_MINIMAP_DUMP_TS >= MINIMAP_DUMP_INTERVAL_SECONDS:
    #     os.makedirs(MINIMAP_DUMP_DIR, exist_ok=True)
    #     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     path = os.path.join(MINIMAP_DUMP_DIR, f"minimap_{ts}.png")
    #     miniMapImage.save(path)
    #     print(f"[DEBUG] saved minimap -> {path}")
    #     _LAST_MINIMAP_DUMP_TS = now

    if miniMapImage.mode != innerIcon.mode:
        innerIcon = innerIcon.convert(miniMapImage.mode)
    innerIconArr = numpy.asarray(innerIcon)
    miniMapArr = numpy.asarray(miniMapImage)

    innerIconArr_y, innerIconArr_x = innerIconArr.shape[:2]
    miniMapArr_y, miniMapArr_x = miniMapArr.shape[:2]

    stopX = miniMapArr_x - innerIconArr_x + 1
    stopY = miniMapArr_y - innerIconArr_y + 1

    for x in range(0, stopX):
        for y in range(0, stopY):
            x2 = x + innerIconArr_x
            y2 = y + innerIconArr_y
            pic = miniMapArr[y:y2, x:x2]
            test = (pic == innerIconArr)
            if test.all():
                return utils.Point(x, y)
    return None

def findCoordsOfColor(target_color=(255, 239, 0), tolerance=10):
    miniMapImage = screenManager.getMiniMapScreenshot()
    if miniMapImage is None:
        return None
    miniMapArr = numpy.asarray(miniMapImage)

    # Ensure target color is a NumPy array
    target_color = numpy.array(target_color)

    # Calculate the absolute difference for each channel
    diff = numpy.abs(miniMapArr - target_color)

    # Find pixels where all differences are within the tolerance
    match = numpy.all(diff <= tolerance, axis=-1)

    # Get the indices of the first match
    coords = numpy.argwhere(match)

    if coords.size > 0:
        y, x = coords[0]  # First matching pixel
        return utils.Point(x, y)

    return None


def send_discord_notification(content):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL not set; skipping Discord notification.")
        return False
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=5)
        response.raise_for_status()
        print("Discord notification sent.")
        return True
    except Exception as exc:
        print(f"Failed to send Discord notification: {exc}")
        return False