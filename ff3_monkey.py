from time import sleep
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
        filename = time.strftime("%Y-%m-%d_%H%M%S.png")
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

    def run(self, dir, duration=1.0):
        dragDistance = 100
        startCoords = (150, 150)
        endCoords = (startCoords[0] + dragDistance*dir[0], startCoords[1] + dragDistance*dir[1])
        self.touch(startCoords, 0.050, MonkeyDevice.DOWN)
        self.touch(endCoords, duration, MonkeyDevice.DOWN)
        self.touch(endCoords, 0.050, MonkeyDevice.UP)

    def selectEnemy(self, enemy):
        self.selectItemFromLowerLeftMenu(enemy, 0.150)
        if enemy != 1:
            self.selectItemFromLowerLeftMenu(enemy, 0.150)

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

    def selectItemFromLargeMenu(self, itemPos, cols, delayAfter=0.150):
        zeroBasedItemPos = (itemPos[0]-1, itemPos[1]-1)
        VISIBLE_ROWS = 4
        scrollsNeeded = zeroBasedItemPos[1]/VISIBLE_ROWS
        DOWN_ARROW_COORDS = (1193, 689)
        for i in range(scrollsNeeded):
            self.touch(DOWN_ARROW_COORDS, 0.200)

        TOP_LEFT_ITEM_COORDS = (350, 350)
        ITEM_COORD_DELTAS = (1260/cols, 108)
        xCoord = TOP_LEFT_ITEM_COORDS[0] + ITEM_COORD_DELTAS[0]*zeroBasedItemPos[0]
        yCoord = TOP_LEFT_ITEM_COORDS[1] + ITEM_COORD_DELTAS[1]*(zeroBasedItemPos[1] % VISIBLE_ROWS)
        self.touch((xCoord, yCoord), delayAfter)

    def selectItemFromItemMenu(self, itemPos, delayAfter=0.150):
        self.selectItemFromLargeMenu(itemPos, 2, delayAfter)

    def selectItemFromSpellMenu(self, itemPos, delayAfter=0.150):
        self.selectItemFromLargeMenu(itemPos, 4, delayAfter)

    def attack(self, enemy):
        self.selectItemFromLowerLeftMenu(1, 0.150)
        self.selectEnemy(enemy)

    def useRod(self, rodPos, enemy):
        self.selectItemFromLowerLeftMenu(4, 0.300)
        self.selectItemFromItemMenu(rodPos, 0.200)
        self.selectEnemy(enemy)

    def castSpell(self, spellPos):
        pass

    def fightDrakeDrakeDrake(self):
        self.attack(1) # Ingus kills First drake


    def addMenuActions(self, menu):
        menu.addAction("H", "Run left", lambda: self.run(Dir.left))
        menu.addAction("J", "Run down", lambda: self.run(Dir.down))
        menu.addAction("K", "Run up", lambda: self.run(Dir.up))
        menu.addAction("L", "Run right", lambda: self.run(Dir.right))
        menu.addAction("S", "Take screenshot", self.screenshot)
        menu.addAction("A", "Attack first enemy", lambda: self.attack(1))
        menu.addAction("R", "Use first rod on first enemy", lambda: self.useRod((1,1), 1))
        menu.addAction("1", "Fight Grenade Grenade Drake", lambda: time.sleep(1))
        menu.addAction("2", "Fight Drake Drake Drake", self.fightDrakeDrakeDrake)
        menu.addAction("3", "Fight Drake Grenade", lambda: time.sleep(1))

def main():
    menu = ActionMenu()
    ma = MonkeyActions()
    ma.addMenuActions(menu)
    menu.run()

main()
