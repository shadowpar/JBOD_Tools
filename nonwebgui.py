import wx
import wx.grid as gridlib
from repairDisk import repairDisk

import os, re,subprocess

from hancockJBODTools import getYoungestChild, getMDparent
from pathlib import Path
from pprint import pprint
from hancockJBODTools import print_disk_list, getmdRAIDinfo, wipeRAIDsuperblock
from hancockJBODTools import storage_info

class ImagePanel(wx.Panel):
    """"""
    #----------------------------------------------------------------------
    def __init__(self, parent, backgroundImage='images/bnlLighter.png'):
        """Constructor"""
        wx.Panel.__init__(self, parent=parent)
        # self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.frame = parent
        self.backgroundImage = backgroundImage
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.image = wx.Image(self.backgroundImage)
        self.bmp = self.image.ConvertToBitmap()

    def calcBackgroundSize(self):
        windowWidth, windowHeight = self.frame.GetClientSize()
        imageWidth, imageHeight = self.image.GetSize()
        scaleByHeight = windowHeight/imageHeight
        scaleByWidth = windowWidth/imageWidth
        if scaleByHeight < scaleByWidth:
            newHeight = windowHeight
            newWidth = imageWidth * scaleByHeight
        else:
            newWidth = windowWidth
            newHeight = imageHeight * scaleByWidth

        self.SetSize(newWidth,newHeight)
        self.image.Rescale(width=windowWidth,height=newHeight,quality=wx.IMAGE_QUALITY_HIGH)

    def OnEraseBackground(self, evt):
        print("firing off erase background event")
        """
        Add a picture to the background
        """
        # yanked from ColourDB.py
        dc = evt.GetDC()

        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRegion(rect)
        dc.Clear()
        self.image = wx.Image(self.backgroundImage)
        # self.calcBackgroundSize()
        self.bmp = self.image.ConvertToBitmap()
        positionx = round(self.GetSize()[0]/2) - round(self.image.GetSize()[0]/2)
        positiony = round(self.GetSize()[1]/2) - round(self.image.GetSize()[1]/2)
        dc.DrawBitmap(self.bmp, positionx, positiony)

class prepareForRemovalWindow(wx.Frame):
        def __init__(self, parent):
            wx.Frame.__init__(self, parent=parent)
            self.panel = ImagePanel(parent=self)
            self.contentWindows = {}
            self.SetSize(1000,1000)
            self.SetBackgroundColour("Blue")
            choices = {'':self.printDiskList,
                            'Prepare Disk For Removal and Replacement.':self.completeRemovalMenu,
                               'Prepare Replaced Disk and Add to RAID Array.':self.completeRestoreMenu,
                                'Manual Disk Operations.':self.manualOperationsMenu,
                               'LED Operations.':self.diskLEDMenu,
                                'Exit':self.exit_program}
            sizer = wx.BoxSizer(wx.VERTICAL)
            for choice in choices:
                button = wx.Button(self.panel,-1,choice)
                sizer.Add(button,0,wx.ALIGN_CENTER  | wx.EXPAND,0)
                button.Bind(wx.EVT_BUTTON,choices[choice])
            self.panel.SetSizer(sizer)
        def Close(self, force=False):
            for child in self.contentWindows:
                try:
                    self.contentWindows[child].Close(force=force)
                except RuntimeError as r:
                    print(r)
            super(prepareForRemovalWindow, self).Close(force=force)


class diskPropertiesWindow(wx.Frame):
    def __init__(self, parent=None, disks=[]):
        wx.Frame.__init__(self, parent=parent, title="Disk Properties")
        properties = {'index': 'Index', 'slot': 'Slot', 'name': 'Name', 'mpathdmname': 'Multipath DM',
                      'mpathname': 'Multipath Friendly', 'dmraidpart': 'RAID Partition DM',
                      'dmraidpartname': 'RAID Partition Name', 'raidrole': "RAID Member Status",
                      'mdparent': 'RAID Device', 'sasaddress': 'SAS Address', 'ident': "LED Status"}
        self.storage_info_obj = storage_info()
        self.contentWindows = {}
        self.SetBackgroundColour("Orange")
        self.SetSize(1800,1000)
        self.SetTitle("Disk properties.")
        # self.panel = wx.Panel(self,id=wx.ID_ANY)
        self.mylist = wx.ListCtrl(parent=self, id=-1, pos=(0,0), size=(1000,1000), style=wx.LC_REPORT)
        for col, propName in enumerate(list(properties.values())):
            self.mylist.AppendColumn(heading=propName)

        for i in range(self.mylist.GetColumnCount()):
            if i == (self.mylist.GetColumnCount()-2):
                self.mylist.SetColumnWidth(i,wx.LIST_AUTOSIZE)
            else:
                self.mylist.SetColumnWidth(i,wx.LIST_AUTOSIZE_USEHEADER)
        try:
            for disk in disks:
                propList = []
                for propName in properties:
                    propList.append(disk[propName])
                self.mylist.Append(propList)
                propList.clear()
            self.mylist.SetColumnWidth(self.mylist.GetColumnCount()-2,wx.LIST_AUTOSIZE)
            self.Show()
        except KeyError:
            print("no io modules found")
            self.Close()

    def Close(self,force=False):
        for child in self.contentWindows:
            try:
                self.contentWindows[child].Close(force=force)
            except RuntimeError as r:
                print(r)
        super(diskPropertiesWindow, self).Close(force=force)


class JBODViewWindow(wx.Frame):
    def __init__(self, title, parent=None):
        wx.Frame.__init__(self, parent=parent, title=title)
        self.contentWindows = {}
        self.panel = wx.Panel(self,wx.ID_ANY)
        self.myImage = wx.Image('images/ultrastar102.png')

    def Close(self,force=False):
        try:
            for child in self.contentWindows:
                self.contentWindows[child].Close(force=force)
        except RuntimeError as r:
            print(r)
        super(JBODViewWindow, self).Close(force=force)


class diskInfoTree(wx.Frame):
    def __init__(self,*args,**kwargs):
        wx.Frame.__init__(self,parent=None,title='diskInfoPrinter',*args, **kwargs)
        print("Starting setup of diskinfoprinter class")
        self.SetSize(1000,1000)
        self.Bind(event=wx.EVT_SIZE,handler=self.updateWindow)
        self.viewMode = 'physical'
        self.panel = wx.Panel(self)
        self.panel = ImagePanel(self)
        self.leafRef = {}
        # self.panel.SetBackgroundColour("White")
        self.contentWindows = {}
        self.storage_info_obj = storage_info()
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.myTree = wx.TreeCtrl(self.panel,wx.ID_ANY,wx.DefaultPosition,wx.DefaultSize, wx.TR_HAS_BUTTONS)
        self.myTree.SetBackgroundColour(None)
        self.modeSelectorRadio = wx.RadioBox(parent=self.myTree,id=-1,label="View Mode Selector", pos=(round(self.GetClientSize()[0] / 2 - 12), 0),choices=['Physical','Logical'],)
        self.root = self.myTree.AddRoot('Chassis')
        for chassis in self.storage_info_obj.chassis:
            self.chassisTreeBuilder(chassis)
        self.myTree.Expand(self.root)
        self.myTree.SetBackgroundColour(None)
        self.myTree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.openDiskPropertiesWindow, id=-1)
        self.sizer.Add(self.myTree, 1, wx.EXPAND)
        self.panel.SetSizer(self.sizer)
        self.Show()
    def updateWindow(self, evt):
        windowHeight = self.GetClientSize()[1]
        windowWidth = self.GetClientSize()[0]
        self.panel.SetSize(self.GetClientSize())
        self.modeSelectorRadio.SetPosition((round(windowWidth / 2 - 12), 0))


    def openDiskPropertiesWindow(self,evnt):
        if 'disks' not in self.contentWindows:
            self.contentWindows['disks'] = diskPropertiesWindow(parent=self,disks=self.myTree.GetItemData(evnt.GetItem()))
        else:
            try:
                self.contentWindows['disks'].Close()
            except Exception as e:
                print(e)
            self.contentWindows['disks'] = diskPropertiesWindow(parent=self,disks=self.myTree.GetItemData(evnt.GetItem()))

    def chassisTreeBuilder(self,chassis):
        diskGrids = {}
        properties = {'index': '|Index', 'slot': '|Slot', 'name': '|Name', 'mpathdmname': '|Multipath DM',
                      'mpathname': '|Multipath Friendly', 'dmraidpart': '|RAID Partition DM',
                      'dmraidpartname': '|RAID Partition Name',
                      'mdparent': '|RAID Device', 'sasaddress': '|SAS Address', 'ident': "|LED Status"}
        self.leafRef[chassis] = self.myTree.AppendItem(self.root, chassis)
        self.leafRef[chassis+'.revision'] = self.myTree.AppendItem(self.leafRef[chassis], 'Revision: '+self.storage_info_obj.chassis[chassis]['revision'])
        self.leafRef[chassis+'.logicalid'] = self.myTree.AppendItem(self.leafRef[chassis], 'Logicalid: '+self.storage_info_obj.chassis[chassis]['logicalid'])
        self.leafRef[chassis+'.numslots'] = self.myTree.AppendItem(self.leafRef[chassis], '# Slots: '+str(self.storage_info_obj.chassis[chassis]['numslots']))
        self.leafRef[chassis+'.model'] = self.myTree.AppendItem(self.leafRef[chassis], 'Model: '+self.storage_info_obj.chassis[chassis]['model'])
        self.leafRef[chassis+'.iomodules'] = self.myTree.AppendItem(self.leafRef[chassis], 'IOmodules:')
        for iomodule in self.storage_info_obj.chassis[chassis]['iomodules']:
            self.leafRef[chassis+'.iomodules.'+iomodule] = self.myTree.AppendItem(self.leafRef[chassis+'.iomodules'], iomodule )
            for item in self.storage_info_obj.chassis[chassis]['iomodules'][iomodule]:
                self.leafRef[chassis+'.iomodules.'+iomodule+'.'+item] = self.myTree.AppendItem(self.leafRef[chassis+'.iomodules.'+iomodule], item)
                if item == 'disks':
                    self.myTree.SetItemData(self.leafRef[chassis+'.iomodules.'+iomodule+'.'+item],self.storage_info_obj.chassis[chassis]['iomodules'][iomodule]['disks'])

    def Close(self,force=False):
        for child in self.contentWindows:
            try:
                self.contentWindows[child].Close(force=force)
            except RuntimeError as r:
                print(r)
        super(diskInfoTree, self).Close(force=force)

class repairDiskGUI(wx.Frame):

    def __init__(self, *args, **kwargs):
        super(repairDiskGUI, self).__init__(*args, **kwargs)
        self.SetSize(1000,1000)
        self.SetTitle("JBOD Tools - Main Menu")
        self.panel = wx.Panel(self,id=wx.ID_ANY)
        # self.panel.SetSize(self.GetSize())
        self.panel.SetBackgroundColour("Blue")
        self.contentWindows = {}
        self.storage_info_obj = storage_info()
        self.storage_info_obj.chassis = {'19js0dfjsd90903':{},'dklmsfdopm33445':{}}
        self.mainMenu()

    def mainMenu(self):
        choices = {'Show all disk info':self.printDiskList,
                'Prepare Disk For Removal and Replacement.':self.completeRemovalMenu,
                   'Prepare Replaced Disk and Add to RAID Array.':self.completeRestoreMenu,
                    'Manual Disk Operations.':self.manualOperationsMenu,
                   'LED Operations.':self.diskLEDMenu,
                    'Exit':self.exit_program}
        # actions = {'1': self.completeRemovalMenu, '2': self.completeRestoreMenu, '3': print, '4': self.diskLEDMenu,'5':-1}
        sizer = wx.BoxSizer(wx.VERTICAL)
        for choice in choices:
            button = wx.Button(self.panel,-1,choice)
            sizer.Add(button,0,wx.ALIGN_CENTER  | wx.EXPAND,0)
            button.Bind(wx.EVT_BUTTON,choices[choice])
        self.panel.SetSizer(sizer)

    def completeRemovalMenu(self,*args,**kwargs):
        pass
        # newContentWindow = contentFrame(title='Prepare Drive for Removal')
        # newContentWindow.SetSize((500,500))
        # panel = wx.Panel(newContentWindow)
        # panel.SetBackgroundColour("Red")
        # self.contentWindows.append(newContentWindow)
        # frameNumber = self.contentWindows.index(newContentWindow)
        # self.contentWindows[frameNumber].Show()
    def completeRestoreMenu(self,*args,**kwargs):
        pass
        # newContentWindow = contentFrame(title='Prepare New Drive and Add to RAID')
        # newContentWindow.SetSize((500,500))
        # panel = wx.Panel(newContentWindow)
        # panel.SetBackgroundColour("Green")
        # self.contentWindows.append(newContentWindow)
        # frameNumber = self.contentWindows.index(newContentWindow)
        # self.contentWindows[frameNumber].Show()
    def manualOperationsMenu(self,*args,**kwargs):
        pass
        # newContentWindow = contentFrame(title='Manual Drive Operations')
        # newContentWindow.SetSize((500,500))
        # panel = wx.Panel(newContentWindow)
        # panel.SetBackgroundColour("Yellow")
        # self.contentWindows.append(newContentWindow)
        # frameNumber = self.contentWindows.index(newContentWindow)
        # self.contentWindows[frameNumber].Show()
    def diskLEDMenu(self,*args,**kwargs):
        pass
        # newContentWindow = contentFrame(title='LED Operations')
        # newContentWindow.SetSize((500,500))
        # panel = wx.Panel(newContentWindow)
        # panel.SetBackgroundColour("Orange")
        # self.contentWindows.append(newContentWindow)
        # frameNumber = self.contentWindows.index(newContentWindow)
        # self.contentWindows[frameNumber].Show()
    def exit_program(self,*args,**kwargs):
        print("Thanks for playing")
        self.Close()
    def printDiskList(self,*args,**kwargs):
        if 'diskInfoPrinter' not in self.contentWindows:
            self.contentWindows['diskInfoPrinter'] = diskInfoTree()
        else:
            try:
                self.contentWindows['diskInfoPrinter'].Close()
            except Exception as e:
                print(e)
            self.contentWindows['diskInfoPrinter'] = diskInfoTree()

        # if 'printer' not in self.contentWindows:
        #     self.contentWindows['printer'] = contentFrame(title='Equipment Status Tree')
        #     self.contentWindows['printer'].SetSize((500,1000))
        #     panel = wx.Panel(self.contentWindows['printer'])
        #     panel.SetBackgroundColour("Grey")
        #     self.contentWindows['printer'].Show()
        #     # self.storage_info_obj.updateData()
        # else:
        #     self.contentWindows['printer']
        #     contentFrame.
        # myTree = wx.TreeCtrl(panel,wx.ID_ANY,wx.DefaultPosition,wx.DefaultSize, wx.TR_HAS_BUTTONS)
        # root = myTree.AddRoot('Chassis')
        # myTree.AppendItem(root,'Item 1')
        # myTree.AppendItem(root, 'item 2')
        # myTree.Expand(root)
        # sizer = wx.BoxSizer(wx.VERTICAL)
        # sizer.Add(myTree, 0, wx.EXPAND)
        # panel.SetSizer(sizer)
    def Close(self,force=False):
        for child in self.contentWindows:
            try:
                self.contentWindows[child].Close(force=force)
            except RuntimeError as r:
                print(r)
        super(repairDiskGUI, self).Close(force=force)



def main():
    app = wx.App()
    ex = repairDiskGUI(None)
    ex.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()