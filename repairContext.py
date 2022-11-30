import wx, json
from hancockJBODTools.windowTypes import diskControllerWindow
from hancockJBODTools import storage_info

class storage_info_sim(object):
    def __init__(self):
        self.chassis = {'oimsdaiofmsiodf':{'revision':'1',
                                           'logicalid':'logicalid1',
                                           'numslots':'5',
                                           'model':'H4102-J',
                                           'iomodules':{'sg1':{'disks':[]},
                                                        'sg104':{'disks':[]}}},
                        'imdf8ds8fs78d':{'revision':'1',
                                        'logicalid':'logicalid1',
                                        'numslots':'5',
                                        'model':'H4102-J',
                                        'iomodules':{'sg2':{'disks':[]},
                                                      'sg204':{'disks':[]}}}}
        with open('chassis') as f:
            self.chassis =  json.load(f)
    def updateData(self):
        print("I am pretending to update the data.")


def main():
    app = wx.App()
    ex = diskControllerWindow(None)
    app.MainLoop()


if __name__ == '__main__':
    main()