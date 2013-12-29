# -*- coding: utf-8 -*-
from time import sleep, strftime, time
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
from java.awt import Color
from javax.swing import AbstractAction, BoxLayout, JComponent, JFrame, JLabel, KeyStroke


class MenuAction(AbstractAction):
    def __init__(self, cb, key, desc, parentMenu):
        AbstractAction.__init__(self)
        self.cb = cb
        self.key = key
        self.desc = desc
        self.parentMenu = parentMenu
    def actionPerformed(self, actionEvent):
        from java.lang import Thread, ThreadDeath
        def resetParentMenu():
            label = self.parentMenu.actionLabels[self.key]
            label.setBackground(self.parentMenu.defaultBackground)
            label.setForeground(Color.black)
            self.parentMenu.frame.title = self.parentMenu.titleBase
            self.parentMenu.actionThread = None

        if self.parentMenu.actionThread != None and self.key == "ESCAPE":
            self.parentMenu.actionThread.stop()
            resetParentMenu()
            return
        elif self.parentMenu.actionThread != None:
            return
        print "Running action:", self.desc
        self.parentMenu.frame.title = self.parentMenu.titleBase+", "+self.desc+"..."
        label = self.parentMenu.actionLabels[self.key]
        label.setBackground(Color.red)
        label.setForeground(Color.yellow)
        def runCbAndResetMenu():
            try:
                self.cb()
            except ThreadDeath:
                print "Action aborted:", self.desc
            finally:
                resetParentMenu()
        self.parentMenu.actionThread = Thread(runCbAndResetMenu)
        self.parentMenu.actionThread.start()

class ActionMenu:
    def __init__(self):
        self.titleBase = 'FF3 Monkey'
        self.frame = JFrame(self.titleBase, defaultCloseOperation = JFrame.EXIT_ON_CLOSE, size=(400,400))
        self.inputMap = self.frame.getRootPane().getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW)
        self.actionMap = self.frame.getRootPane().getActionMap()
        self.actionLabels = {}
        self.actionThread = None

        self.defaultBackground = self.frame.getBackground()
        self.frame.getContentPane().setLayout(BoxLayout(self.frame.getContentPane(), BoxLayout.Y_AXIS))

        def quit():
            from java.lang import System
            print "Quitting..."
            System.exit(0)
        self.addAction("Q", "Quit", quit)
        self.addAction("ESCAPE", "Abort current action", lambda: None)
    def addAction(self, key, desc, cb):
        if " " in key:
            strokeString = key
        else:
            strokeString = "pressed "+key

        stroke = KeyStroke.getKeyStroke(strokeString)
        if stroke == None:
            raise ValueError("Invalid key: "+str(key))
        self.inputMap.put(stroke, key)
        self.actionMap.put(key, MenuAction(cb, key, desc, self))
        self.actionLabels[key] = JLabel(key+": "+desc)
        self.actionLabels[key].setOpaque(True)
        self.frame.getContentPane().add(self.actionLabels[key])
    def run(self):
        print "Starting menu"
        self.frame.visible = True
        while True:
            sleep(300)

class GameState(object):
    MAINSTATE_COMBAT   = "main_combat"
    MAINSTATE_INSIDE   = "main_inside"
    MAINSTATE_MENU     = "main_menu"
    MAINSTATE_WORLDMAP = "main_worldmap"
    MAINSTATE_UNKNOWN  = "main_unknown"
    MAINSTATES = [MAINSTATE_COMBAT, MAINSTATE_INSIDE, MAINSTATE_MENU, MAINSTATE_WORLDMAP, MAINSTATE_UNKNOWN]

    COMBATSTATE_TURN_BEGIN = "combat_turn_begin"
    COMBATSTATE_TURN_INCOMPLETE = "combat_turn_incomplete"
    COMBATSTATE_MENU = "combat_menu"
    COMBATSTATE_VICTORY_NOTIFICATION = "combat_victory_notification"
    COMBATSTATE_UNKNOWN = "combat_unknown"
    COMBATSTATES = [ None, COMBATSTATE_TURN_BEGIN, COMBATSTATE_TURN_INCOMPLETE, COMBATSTATE_MENU, COMBATSTATE_VICTORY_NOTIFICATION, COMBATSTATE_UNKNOWN ]

    def __init__(self, mainState, combatState):
        self.mainState = mainState
        self.combatState = combatState

    def getMainState(self):
        return self._mainState
    def setMainState(self, val):
        if val not in self.MAINSTATES:
            raise ValueError("invalid mainState: "+str(val))
        self._mainState = val
    mainState = property(getMainState, setMainState)

    def getCombatState(self):
        return self._combatState
    def setCombatState(self, val):
        if val != None and self.mainState != self.MAINSTATE_COMBAT:
            raise ValueError("cannot set combatState when mainState != MAINSTATE_COMBAT")
        if val not in self.COMBATSTATES:
            raise ValueError("invalid combatState: "+str(val))
        self._combatState = val
    combatState = property(getCombatState, setCombatState)

    def __str__(self):
        return "GameState(%s, %s)" % (self.mainState, self.combatState)

class GameStateDetector:
    def __init__(self, monkeydevice):
        self.device = monkeydevice

        self.lunethLPixels = [((753,y), 0xffffff) for y in range(575, 593)]

        # subImageDetectionSpecs: (BufferedImage, (x,y,w,h), requiredSimilarityPercent)
        self.worldmapDetection = (self.readImg("map_text.png"), (938,35,82,41), 99.8)
        self.insideDetection = (self.readImg("menu_button_e.png"), (1133,46,20,20), 99.8)
        self.menuDetection = (self.readImg("menu_back_text.png"), (608,672,35,24), 99.8)
        self.combatMainDetection = (self.readImg("lower_left_menu_upper_left_corner.png"), (88,444,12,4), 99.9)
        self.combatMenuDetection = (self.readImg("combat_menu_explanation_frame.png"), (254,53,5,5), 99.9)
        self.combatBackButtonDetection = (self.readImg("combat_back_button_frame.png"), (46,1,5,6), 99.9)
        self.combatVictoryDetection = (self.readImg("combat_victory_notification_frame.png"), (53,52,5,5), 99.99)

    @staticmethod
    def readImg(filename):
        from java.io import File
        from javax.imageio import ImageIO
        import sys, os
        scriptDir = os.path.dirname(sys.argv[0])
        return ImageIO.read(File(os.path.join(scriptDir, filename)))

    def checkPixelColors(self, pixelColors, requiredSimilarityPercent=100.0, shot=None):
        shot = shot or self.device.takeSnapshot()
        maxAllowedDissimilarity = max(0, len(pixelColors)*0xff*3 * (100.0-requiredSimilarityPercent)/100.0)
        dissimilarity = 0
        for pixelCoords,expectedColor in pixelColors:
            pixelCoordsInScreenshot = self.horizontalCoordsToScreenshotCoords(pixelCoords, 720)
            actualColor = shot.getRawPixelInt(*pixelCoordsInScreenshot) & 0xffffff
            dissimilarity += self.getPixelDissimilarity(actualColor, expectedColor)
            if dissimilarity > maxAllowedDissimilarity:
                break
        #print "Dissimilarity %.1f/%.1f" % (dissimilarity, maxAllowedDissimilarity)
        return dissimilarity <= maxAllowedDissimilarity

    @staticmethod
    def horizontalCoordsToScreenshotCoords(coords, origHeight):
        return (origHeight-coords[1]-1, coords[0])

    @staticmethod
    def horizontalRectToScreenshotRect(rect):
        return GameStateDetector.horizontalCoordsToScreenshotCoords((rect[0], rect[1]+rect[3]-1), 720) + (rect[3], rect[2])

    def checkSubImage(self, subImageDetectionSpec, shot=None):
        shot = shot or self.device.takeSnapshot()
        imagedata, rect, requiredSimilarityPercent = subImageDetectionSpec
        subImageOnScreen = shot.getSubImage(self.horizontalRectToScreenshotRect(rect))

        maxAllowedDissimilarity = max(0, rect[2]*rect[3]*0xff*3 * (100.0-requiredSimilarityPercent)/100.0)
        dissimilarity = 0
        for y in range(rect[3]):
            for x in range(rect[2]):
                screenshotCoords = self.horizontalCoordsToScreenshotCoords((x,y), rect[3])
                screenPixel = subImageOnScreen.getRawPixelInt(*screenshotCoords) & 0xffffff
                subImagePixel = imagedata.getRGB(x,y) & 0xffffff
                #print "comparing image %s 0x%x with screen %s 0x%x" % ((x,y), subImagePixel, screenshotCoords, screenPixel)
                dissimilarity += self.getPixelDissimilarity(screenPixel, subImagePixel)
                if dissimilarity > maxAllowedDissimilarity:
                    break
        #print "Dissimilarity %.1f/%.1f" % (dissimilarity, maxAllowedDissimilarity)
        return dissimilarity <= maxAllowedDissimilarity

    @staticmethod
    def getPixelDissimilarity(color1, color2):
        dissimilarity = 0
        for component in range(3):
            componentVal1 = GameStateDetector.getColorComponent(color1, component)
            componentVal2 = GameStateDetector.getColorComponent(color2, component)
            dissimilarity += abs(componentVal1 - componentVal2)
        return dissimilarity
    @staticmethod
    def getColorComponent(color, componentNumber):
            return (color & (0xff << (componentNumber*8))) >> (componentNumber*8)

    def detectMonsters(self):
        return None

    def _isInCombat(self, shot):
        if self.checkSubImage(self.combatMainDetection, shot): return True
        elif self.checkSubImage(self.combatMenuDetection, shot): return True
        elif self.checkSubImage(self.combatVictoryDetection, shot): return True
        else: return False

    def getMainState(self, shot=None):
        shot = shot or self.device.takeSnapshot()
        if self.checkSubImage(self.worldmapDetection, shot): return GameState.MAINSTATE_WORLDMAP
        elif self.checkSubImage(self.insideDetection, shot): return GameState.MAINSTATE_INSIDE
        elif self._isInCombat(shot): return GameState.MAINSTATE_COMBAT
        elif self.checkSubImage(self.menuDetection, shot): return GameState.MAINSTATE_MENU
        else: return GameState.MAINSTATE_UNKNOWN

    def isCombatHpListOnScreen(self, shot=None):
        shot = shot or self.device.takeSnapshot()
        return self.checkPixelColors(self.lunethLPixels, 99.95, shot)

    def getCombatState(self, shot=None):
        shot = shot or self.device.takeSnapshot()
        lowerLeftMenuPresent = self.checkSubImage(self.combatMainDetection, shot)
        if lowerLeftMenuPresent and not self.checkSubImage(self.combatBackButtonDetection, shot):
            return GameState.COMBATSTATE_TURN_BEGIN
        elif lowerLeftMenuPresent:
            return GameState.COMBATSTATE_TURN_INCOMPLETE

        combatVictoryFramePresent = self.checkSubImage(self.combatVictoryDetection, shot)
        if self.checkSubImage(self.combatMenuDetection, shot) and not combatVictoryFramePresent:
            return GameState.COMBATSTATE_MENU
        elif combatVictoryFramePresent and not self.isCombatHpListOnScreen(shot):
            return GameState.COMBATSTATE_VICTORY_NOTIFICATION
        else:
            return GameState.COMBATSTATE_UNKNOWN

    def getGameState(self):
        shot = self.device.takeSnapshot()
        mainState = self.getMainState(shot)
        combatState = mainState==GameState.MAINSTATE_COMBAT and self.getCombatState(shot) or None
        return GameState(mainState, combatState)

class Dir:
    up = (0, -1)
    right = (1, 0)
    down = (0, 1)
    left = (-1, 0)

class MonkeyActions:
    def __init__(self):
        self.device = MonkeyRunner.waitForConnection(1)
        self.gameStateDetector = GameStateDetector(self.device)

    def screenshot(self):
        import tempfile
        import os
        shot = self.device.takeSnapshot()
        filename = strftime("%Y-%m-%d_%H%M%S.png")
        dirPath = os.path.join(tempfile.gettempdir(), "ff3_monkey")
        pathToFile = os.path.join(dirPath, filename)
        if not os.path.exists(dirPath):
            os.mkdir(dirPath)

        print "Writing screenshot to", pathToFile
        shot.writeToFile(pathToFile)

    def touch(self, coords, delayAfter=0.010, type=MonkeyDevice.DOWN_AND_UP):
        #print "Touching "+str(coords)+" (type="+str(type)+") and sleeping "+str(delayAfter)+"s"
        self.device.touch(coords[0], coords[1], type)
        sleep(delayAfter)

    def tapScreen(self, delayAfter=0.150, coords=(640,360)):
        self.touch(coords, delayAfter, MonkeyDevice.DOWN_AND_UP)

    def pressBack(self, delayAfter=0.150):
        self.device.press("KEYCODE_BACK", MonkeyDevice.DOWN_AND_UP)
        sleep(delayAfter)

    def run(self, dir, duration=1.0):
        dragDistance = 100
        startCoords = (150, 150)
        endCoords = (startCoords[0] + dragDistance*dir[0], startCoords[1] + dragDistance*dir[1])
        self.touch(startCoords, 0.050, MonkeyDevice.DOWN)
        self.touch(endCoords, duration, MonkeyDevice.DOWN)
        self.touch(endCoords, 0.050, MonkeyDevice.UP)

    def selectItemFromLowerLeftMenu(self, item, delayAfter=0.150):
        zeroBasedItem = item - 1
        VISIBLE_ROWS = 3
        scrollsNeeded = zeroBasedItem/VISIBLE_ROWS
        lowerLeftMenuDownButtonCoords = (430, 650)
        for i in range(scrollsNeeded):
            self.touch(lowerLeftMenuDownButtonCoords, 0.200)

        TOP_ITEM_COORDS = (240,490)
        ITEM_COORD_DELTA = 90
        yCoord = TOP_ITEM_COORDS[1] + (zeroBasedItem%VISIBLE_ROWS)*ITEM_COORD_DELTA
        self.touch((TOP_ITEM_COORDS[0], yCoord), delayAfter)

    def selectEnemy(self, enemy):
        self.selectItemFromLowerLeftMenu(enemy, 0.200)
        if enemy != 1:
            self.selectItemFromLowerLeftMenu(enemy, 0.100)
        sleep(0.500)

    def selectItemFromLargeMenu(self, itemPos, cols, firstItemCol, delayAfter=0.150):
        zeroBasedItemPos = (itemPos[0]-1, itemPos[1]-1)
        VISIBLE_ROWS = 4
        scrollsNeeded = max(itemPos[1]-VISIBLE_ROWS, 0)
        DOWN_ARROW_COORDS = (1193, 689)
        for i in range(scrollsNeeded):
            self.touch(DOWN_ARROW_COORDS, 0.200)

        MENU_WIDTH=1180
        MENU_OFFSET_X=47
        ITEM_COORD_DELTAS = (MENU_WIDTH/cols, 108)
        TOP_LEFT_ITEM_COORDS = (MENU_WIDTH/cols/2 + MENU_OFFSET_X + ITEM_COORD_DELTAS[0]*(firstItemCol-1), 350)
        xCoord = TOP_LEFT_ITEM_COORDS[0] + ITEM_COORD_DELTAS[0]*zeroBasedItemPos[0]
        yCoord = TOP_LEFT_ITEM_COORDS[1] + ITEM_COORD_DELTAS[1]*(min(zeroBasedItemPos[1], VISIBLE_ROWS-1))

        if itemPos != (1,1):
            self.touch((xCoord, yCoord), 0.200)
        self.touch((xCoord, yCoord), delayAfter)

    def selectItemFromItemMenu(self, itemPos, delayAfter=0.150):
        self.selectItemFromLargeMenu(itemPos, 2, 1, delayAfter)

    def attack(self, enemy):
        self.selectItemFromLowerLeftMenu(1, 0.150)
        self.selectEnemy(enemy)

    def useRod(self, rodRow, rodCol, enemy):
        self.selectItemFromLowerLeftMenu(4, 0.300)
        self.selectItemFromItemMenu((rodCol, rodRow), 0.200)
        self.selectEnemy(enemy)

    def castAttackSpell(self, spellLevel, spellNumber, enemy):
        self.selectItemFromLowerLeftMenu(2, 0.400)
        self.selectItemFromLargeMenu((spellNumber, spellLevel), 4, 2, 0.400)
        self.selectEnemy(enemy)

    def fightDrakeDrakeDrake(self):
        self.attack(1) # Luneth kills drake#1
        self.attack(2) # Arc damages drake#2 but doesn't kill it
        self.castAttackSpell(6, 1, 3) # Refia kills drake#3
        self.useRod(1, 1, 2) # Ingus finishes off drake#2

    def fightGrenadeGrenadeDrake(self):
        self.attack(3) # Luneth kills drake
        self.attack(1) # Arc damages/kills grenade#1
        self.useRod(1, 2, 1) # Refia finishes off grenade#1 with ice rod
        self.useRod(1, 2, 2) # Ingus finishes off grenade#2 with ice rod

    def fightDrakeGrenade(self):
        self.attack(1) # Luneth kills drake#1
        self.attack(2) # Arc damages/kills grenade
        self.useRod(1, 2, 2) # Refia finishes off drake#2 with ice rod
        self.useRod(1, 2, 2) # Ingus finishes off drake#2 with ice rod

    def fightDefault(self):
        self.attack(1)
        self.attack(1)
        self.useRod(1, 2, 1)
        self.useRod(1, 2, 1)

    def automaticCombat(self):
        turnsFought = 0
        print "=== Automatic Combat ==="
        while True:
            gameState = self.gameStateDetector.getGameState()
            mainState = gameState.mainState
            if mainState in [GameState.MAINSTATE_INSIDE, GameState.MAINSTATE_WORLDMAP]:
                print "Fight finished, yay"
                break
            elif mainState == GameState.MAINSTATE_COMBAT:
                combatState = gameState.combatState
                if combatState == GameState.COMBATSTATE_TURN_BEGIN:
                    if turnsFought == 0:
                        self.selectItemFromLowerLeftMenu(1, 0.200)
                        monsters = self.gameStateDetector.detectMonsters()
                        self.pressBack(0.200)
                        print "Detected monsters:", monsters
                        if monsters == ["Drake", "Drake", "Drake"]: self.fightDrakeDrakeDrake()
                        elif monsters == ["Drake", "Grenade"]: self.fightDrakeGrenade()
                        elif monsters == ["Grenade", "Grenade", "Drake"]: self.fightGrenadeGrenadeDrake()
                        else: self.fightDefault()
                    else:
                        self.fightDefault()
                    sleep(8.0)
                    turnsFought += 1
                elif combatState == GameState.COMBATSTATE_TURN_INCOMPLETE:
                    print "Turn in incomplete state, backing up..."
                    self.pressBack(2.0)
                elif combatState == GameState.COMBATSTATE_MENU:
                    print "In combat menu, backing up..."
                    self.pressBack(2.0)
                elif combatState == GameState.COMBATSTATE_VICTORY_NOTIFICATION:
                    print "In victory notification, tapping screen..."
                    self.tapScreen(1.0)
                else:
                    print "Unexpected combat state=%s, will wait and try again" % combatState
                    sleep(0.5)
            elif mainState == GameState.MAINSTATE_MENU:
                print "In menu, backing up..."
                self.pressBack(2.0)
            else:
                print "Unexpected state=%s, will wait and try again" % mainState
                sleep(0.5)

    def castCureOutsideOfCombat(self):
        self.touch((1154, 57), 1.500) # Menu button
        self.touch((1130, 66), 0.300) # Magic button
        self.touch((470, 410), 0.500) # Choose Refia
        self.touch((506, 200), 0.300) # Choose Cure
        self.touch((951, 541), 0.300) # Choose All Party Members
        self.touch((951, 541), 0.400) # Confirm All Party Members
        self.touch((951, 541), 0.400) # Cast cure a second time
        self.pressBack(0.200) # back to spell choise
        self.pressBack(0.200) # back to main menu
        self.pressBack(1.200) # back to game view

    def restInInvincibleAndReturn(self):
        startTime = time()
        print "=== Rest in Invincible ==="
        print "Exiting Bahamut's lair..."
        self.run(Dir.up, 1.5)
        while True:
            mainState = self.getMainState()
            if mainState == GameState.MAINSTATE_WORLDMAP:
                print "We are outside, yay"
                break
            elif mainState == GameState.MAINSTATE_COMBAT:
                print "We got into a fight, trying to run away"
                self.runAwayFromCombat()
                continue
            elif mainState == GameState.MAINSTATE_INSIDE:
                print "Still inside, running up..."
                self.run(Dir.up, 2.0)
                continue
            elif mainState == GameState.MAINSTATE_MENU:
                print "In menu, backing up"
                self.pressBack(2.0)
                continue
            else:
                print "Unexpected state=%s, will wait and try again" % mainState
                sleep(0.5)
                continue
        print "Entering Invincible and running to the bed..."
        self.tapScreen(2.100)
        self.run(Dir.up, 1.000)
        self.run(Dir.left, 1.500)
        self.run(Dir.down, 0.650)
        self.run(Dir.right, 0.150)
        sleep(0.200) # wait for exclamation bubble
        print "Sleeping..."
        self.tapScreen(1.000) #use bed
        self.touch((640,520), 14.500) #tap Yes
        self.tapScreen(1.200) #slept like a log...
        self.tapScreen(0.200) #HP and MP restored
        print "Running back to the cave..."
        self.run(Dir.up, 0.900)
        self.run(Dir.right, 1.350)
        self.run(Dir.down, 1.050)
        self.run(Dir.left, 1.200)
        sleep(1.1) # wait for exit
        self.run(Dir.up, 1.5)  # enter Bahamut's lair
        sleep(1.0) # wait for entry
        self.run(Dir.down, 1.0) # run to the hunting spot
        # TODO: make sure we did not get into a fight
        print "Done resting, took %.1fs" % ((time()-startTime))

    def enterCombat(self):
        print "=== Enter combat ==="
        while True:
            mainState = self.getMainState()
            if mainState == GameState.MAINSTATE_COMBAT:
                print "We are in combat, yay"
                break
            elif mainState == GameState.MAINSTATE_MENU:
                print "In menu, backing up"
                self.pressBack(2.0)
            elif mainState in [GameState.MAINSTATE_WORLDMAP, GameState.MAINSTATE_INSIDE]:
                print "Running around"
                for i in range(5):
                    self.run(Dir.left, 0.25)
                    self.run(Dir.right, 0.25)
                sleep(1.0) # wait for the Menu button to reappear
            else:
                print "Unexpected state=%s, will wait and try again" % mainState
                sleep(0.5)

    def runAwayFromCombat(self):
        runAwayButtonCoords = (1130,45)
        for i in range(4):
            self.touch(runAwayButtonCoords, 1.0)
        sleep(5.0)

    def getMainState(self):
        return self.gameStateDetector.getMainState()

    def printCurrentState(self):
        print self.gameStateDetector.getGameState()

    def addMenuActions(self, menu):
        runDurationNormal = 0.5
        runDurationShort = 0.2
        menu.addAction("S", "Take screenshot", self.screenshot)
        menu.addAction("MINUS", "Print game state to stdout", self.printCurrentState)
        menu.addAction("H", "Run left", lambda: self.run(Dir.left, runDurationNormal))
        menu.addAction("J", "Run down", lambda: self.run(Dir.down, runDurationNormal))
        menu.addAction("K", "Run up", lambda: self.run(Dir.up, runDurationNormal))
        menu.addAction("L", "Run right", lambda: self.run(Dir.right, runDurationNormal))
        menu.addAction("alt H", "Run left a little", lambda: self.run(Dir.left, runDurationShort))
        menu.addAction("alt J", "Run down a little", lambda: self.run(Dir.down, runDurationShort))
        menu.addAction("alt K", "Run up a little", lambda: self.run(Dir.up, runDurationShort))
        menu.addAction("alt L", "Run right a little", lambda: self.run(Dir.right, runDurationShort))
        menu.addAction("B", "Back", self.pressBack)
        menu.addAction("T", "Tap the screen", self.tapScreen)
        menu.addAction("1", "Fight Drake Drake Drake", self.fightDrakeDrakeDrake)
        menu.addAction("2", "Fight Grenade Grenade Drake", self.fightGrenadeGrenadeDrake)
        menu.addAction("3", "Fight Drake Grenade", self.fightDrakeGrenade)
        menu.addAction("C", "Cure outside of combat", self.castCureOutsideOfCombat)
        menu.addAction("R", "Rest in Invincible", self.restInInvincibleAndReturn)
        menu.addAction("A", "Attack first enemy", lambda: self.attack(1))
        menu.addAction("0", "Use first rod on first enemy", lambda: self.useRod(1, 1, 1))
        menu.addAction("N", "eNter combat", self.enterCombat)
        menu.addAction("E", "Escape from combat", self.runAwayFromCombat)
        menu.addAction("A", "Automatic combat", self.automaticCombat)

def main():
    menu = ActionMenu()
    ma = MonkeyActions()
    ma.addMenuActions(menu)
    menu.run()

main()
