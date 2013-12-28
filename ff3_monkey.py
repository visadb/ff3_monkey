# -*- coding: utf-8 -*-
from time import sleep, strftime, time
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
from java.awt import Color
from javax.swing import AbstractAction, JComponent, JFrame, JTextArea, KeyStroke, Timer


class MenuAction(AbstractAction):
    def __init__(self, cb, desc, parentMenu):
        AbstractAction.__init__(self)
        self.cb = cb
        self.desc = desc
        self.parentMenu = parentMenu
    def actionPerformed(self, actionEvent):
        self.parentMenu.frame.title = self.parentMenu.titleBase+", "+self.desc+"..."
        label = self.parentMenu.actionLabel
        label.setBackground(Color.yellow)
        def runCbAndResetMenu(action):
            self.cb()
            label.setBackground(self.parentMenu.defaultBackground)
            self.parentMenu.frame.title = self.parentMenu.titleBase
        t = Timer(0, runCbAndResetMenu)
        t.setRepeats(False)
        t.start()

class ActionMenu:
    def __init__(self):
        self.titleBase = 'FF3 Monkey'
        self.frame = JFrame(self.titleBase, defaultCloseOperation = JFrame.EXIT_ON_CLOSE, size=(400,400))
        self.inputMap = self.frame.getRootPane().getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW)
        self.actionMap = self.frame.getRootPane().getActionMap()

        self.actionLabel = JTextArea("Actions:", editable=False)
        self.frame.add(self.actionLabel)
        self.defaultBackground = self.actionLabel.getBackground()

        def quit():
            from java.lang import System
            print "Quitting..."
            System.exit(0)
        self.addAction("Q", "Quit", quit)
    def addAction(self, key, desc, cb):
        self.inputMap.put(KeyStroke.getKeyStroke("pressed "+key), key)
        self.actionMap.put(key, MenuAction(cb, desc, self))
        self.actionLabel.setText(self.actionLabel.getText()+"\n"+key+": "+desc)
    def run(self):
        print "Starting menu"
        self.frame.visible = True
        while True:
            sleep(300)

class GameState(object):
    MAINSTATE_COMBAT   = "combat"
    MAINSTATE_INSIDE   = "inside"
    MAINSTATE_MENU     = "menu"
    MAINSTATE_WORLDMAP = "worldmap"
    MAINSTATE_UNKNOWN  = "unknown"
    MAINSTATES = [MAINSTATE_COMBAT, MAINSTATE_INSIDE, MAINSTATE_MENU, MAINSTATE_WORLDMAP, MAINSTATE_UNKNOWN]

    def __init__(self, mainState):
        self.mainState = mainState

    #@property
    def getMainState(self):
        return self._mainState
    #@mainState.setter
    def setMainState(self, val):
        if val not in GameState.MAINSTATES:
            raise ValueError("invalid mainState: "+str(val))
        self._mainState = val
    mainState = property(getMainState, setMainState)

    def __str__(self):
        return "GameState(%s)" % self.mainState

class GameStateDetector:
    def __init__(self, monkeydevice):
        self.device = monkeydevice
        self.worldmapDetectionSubImage = (self.readImageFile("map_text.png"), (938,35,82,41))
        self.insideDetectionSubImage = (self.readImageFile("menu_button_e.png"), (1133,46,20,20))
        self.menuDetectionSubImage = (self.readImageFile("menu_back_text.png"), (608,672,35,24))
        self.combatDetectionSubImage = (self.readImageFile("lower_left_menu_upper_left_corner.png"), (88,444,12,4))

    @staticmethod
    def readImageFile(filename):
        from java.io import File
        from javax.imageio import ImageIO
        import sys, os
        scriptDir = os.path.dirname(sys.argv[0])
        return ImageIO.read(File(os.path.join(scriptDir, filename)))

    def checkPixelColors(self, pixelColors, screenshot=None):
        screenshot = screenshot or self.device.takeSnapshot()
        for pixelCoords,expectedColor in pixelColors:
            pixelCoordsInScreenshot = self.horizontalCoordsToScreenshotCoords(pixelCoords, 720)
            actualColor = screenshot.getRawPixel(*pixelCoordsInScreenshot)
            if actualColor != expectedColor:
                return False
        return True

    @staticmethod
    def horizontalCoordsToScreenshotCoords(coords, origHeight):
        return (origHeight-coords[1]-1, coords[0])

    @staticmethod
    def horizontalRectToScreenshotRect(rect):
        return GameStateDetector.horizontalCoordsToScreenshotCoords((rect[0], rect[1]+rect[3]-1), 720) + (rect[3], rect[2])

    def isSubImageOnScreen(self, subImage, requiredSimilarityPercent=99.8, screenshot=None):
        screenshot = screenshot or self.device.takeSnapshot()
        imagedata, rect = subImage
        subImageOnScreen = screenshot.getSubImage(self.horizontalRectToScreenshotRect(rect))
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

    def getMainState(self):
        screenshot = self.device.takeSnapshot()
        if self.isSubImageOnScreen(self.combatDetectionSubImage, 99.9, screenshot=screenshot):
            return GameState.MAINSTATE_COMBAT
        elif self.isSubImageOnScreen(self.worldmapDetectionSubImage, screenshot=screenshot):
            return GameState.MAINSTATE_WORLDMAP
        elif self.isSubImageOnScreen(self.insideDetectionSubImage, screenshot=screenshot):
            return GameState.MAINSTATE_INSIDE
        elif self.isSubImageOnScreen(self.menuDetectionSubImage, screenshot=screenshot):
            return GameState.MAINSTATE_MENU
        else:
            return GameState.MAINSTATE_UNKNOWN

    def getCurrentState(self):
        return GameState(self.getMainState())

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
        #TODO: see if combat ends. if combat continues, do a fight+rod round
        #TODO: if combat ends, tap screen until we are really outside combat

    def fightDrakeGrenade(self):
        self.attack(1) # Luneth kills drake#1
        self.attack(2) # Arc damages/kills grenade
        self.useRod(1, 2, 2) # Refia finishes off drake#2 with ice rod
        self.useRod(1, 2, 2) # Ingus finishes off drake#2 with ice rod

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

    def runAwayFromCombat(self):
        runAwayButtonCoords = (1130,45)
        for i in range(4):
            self.touch(runAwayButtonCoords, 1.0)
        sleep(5.0)

    def getMainState(self):
        return self.gameStateDetector.getCurrentState().mainState

    def printCurrentState(self):
        print self.gameStateDetector.getCurrentState()

    def addMenuActions(self, menu):
        runDuration = 0.5
        menu.addAction("S", "Take screenshot", self.screenshot)
        menu.addAction("MINUS", "Print game state to stdout", self.printCurrentState)
        menu.addAction("H", "Run left", lambda: self.run(Dir.left, runDuration))
        menu.addAction("J", "Run down", lambda: self.run(Dir.down, runDuration))
        menu.addAction("K", "Run up", lambda: self.run(Dir.up, runDuration))
        menu.addAction("L", "Run right", lambda: self.run(Dir.right, runDuration))
        menu.addAction("B", "Back", self.pressBack)
        menu.addAction("T", "Tap the screen", self.tapScreen)
        menu.addAction("1", "Fight Drake Drake Drake", self.fightDrakeDrakeDrake)
        menu.addAction("2", "Fight Grenade Grenade Drake", lambda: sleep(1))
        menu.addAction("3", "Fight Drake Grenade", self.fightDrakeGrenade)
        menu.addAction("C", "Cure outside of combat", self.castCureOutsideOfCombat)
        menu.addAction("R", "Rest in Invincible", self.restInInvincibleAndReturn)
        menu.addAction("A", "Attack first enemy", lambda: self.attack(1))
        menu.addAction("0", "Use first rod on first enemy", lambda: self.useRod(1, 1, 1))
        menu.addAction("E", "Escape from combat", self.runAwayFromCombat)

def main():
    menu = ActionMenu()
    ma = MonkeyActions()
    ma.addMenuActions(menu)
    menu.run()

main()
