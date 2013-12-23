import time
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
            time.sleep(300)

class Dir:
    up = (0, -1)
    right = (1, 0)
    down = (0, 1)
    left = (-1, 0)

class MonkeyActions:
    def __init__(self):
        self.device = MonkeyRunner.waitForConnection(1)

    def run(self, dir, duration=1.0):
        dragDistance = 100
        startX, startY = 150, 150
        endX, endY = startX + dragDistance*dir[0], startY + dragDistance*dir[1]
        self.device.touch(startX, startY, MonkeyDevice.DOWN)
        time.sleep(0.05)
        self.device.touch(endX, endY, MonkeyDevice.DOWN)
        time.sleep(duration)
        self.device.touch(endX, endY, MonkeyDevice.UP)

    def screenshot(self):
        import tempfile
        import os
        shot = self.device.takeSnapshot()
        filename = time.strftime("%Y-%m-%d_%H%M%S.png")
        dirPath = os.path.join(tempfile.gettempdir(), "ff3_monkey")
        pathToFile = os.path.join(dirPath, filename)
        if not os.path.exists(dirPath):
            os.mkdir(dirPath)

        shot.writeToFile(pathToFile)

    def attack(self, enemy=1):
        targetCoords = {1:(240,490), 2:(240,580), 3:(240,670)}
        targetCoords = targetCoords

    def addMenuActions(self, menu):
        menu.addAction("H", "Run left", lambda: self.run(Dir.left))
        menu.addAction("J", "Run down", lambda: self.run(Dir.down))
        menu.addAction("K", "Run up", lambda: self.run(Dir.up))
        menu.addAction("L", "Run right", lambda: self.run(Dir.right))
        menu.addAction("S", "Take screenshot", self.screenshot)
        menu.addAction("A", "Attack first enemy", lambda: self.attack(1))
        menu.addAction("1", "Attack Grenade Grenade Drake", lambda: time.sleep(1))
        menu.addAction("2", "Attack Drake Drake Drake", lambda: time.sleep(1))
        menu.addAction("3", "Attack Drake Grenade", lambda: time.sleep(1))


def main():
    menu = ActionMenu()
    ma = MonkeyActions()
    ma.addMenuActions(menu)
    menu.run()

main()
