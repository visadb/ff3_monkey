from time import sleep, strftime
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
        self.frame = JFrame(self.titleBase, defaultCloseOperation = JFrame.EXIT_ON_CLOSE, size=(400,300))
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

class Dir:
    up = (0, -1)
    right = (1, 0)
    down = (0, 1)
    left = (-1, 0)

class MonkeyActions:
    def __init__(self):
        self.device = MonkeyRunner.waitForConnection(1)

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

    def addMenuActions(self, menu):
        menu.addAction("S", "Take screenshot", self.screenshot)
        menu.addAction("H", "Run left", lambda: self.run(Dir.left, 1.0))
        menu.addAction("J", "Run down", lambda: self.run(Dir.down, 1.0))
        menu.addAction("K", "Run up", lambda: self.run(Dir.up, 1.0))
        menu.addAction("L", "Run right", lambda: self.run(Dir.right, 1.0))
        menu.addAction("B", "Back", self.pressBack)
        menu.addAction("1", "Fight Drake Drake Drake", self.fightDrakeDrakeDrake)
        menu.addAction("2", "Fight Grenade Grenade Drake", lambda: sleep(1))
        menu.addAction("3", "Fight Drake Grenade", lambda: sleep(1))
        menu.addAction("C", "Cure outside of combat", self.castCureOutsideOfCombat)
        menu.addAction("A", "Attack first enemy", lambda: self.attack(1))
        menu.addAction("0", "Use first rod on first enemy", lambda: self.useRod(1, 1, 1))

def main():
    menu = ActionMenu()
    ma = MonkeyActions()
    ma.addMenuActions(menu)
    menu.run()

main()
