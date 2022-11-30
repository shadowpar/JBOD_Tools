import wx, json, wx.grid
from hancockJBODTools import storage_info, storage_info_sim
from pprint import pprint
from .menuTypes import ledOperationMenu, diskOperationsMenu
from .menuTypes import menuMapping


class windowBase(wx.Frame):
    def __init__(self,*args,**kwargs):
        super(windowBase,self).__init__(*args,**kwargs)
        self.contentWindows = {}
    def Close(self,force=False):
        for child in self.contentWindows:
            try:
                self.contentWindows[child].Close(force=force)
            except RuntimeError as r:
                print(r)
        super(windowBase, self).Close(force=force)

class diskControllerWindow(windowBase):
    def __init__(self, *args, **kwargs):
        super(diskControllerWindow, self).__init__(*args, **kwargs)
        self.storage_info_obj = storage_info(smart=True)
        if len(self.storage_info_obj.chassis) == 0:
            self.storage_info_obj = storage_info_sim()
            self.SetTitle("DATA is a simulation only.")
            self.simulated = True
        else:
            self.simulated = False
        self.leafRef = {}
        self.SetBackgroundColour("Dark Slate Gray")
        self.SetSize(1500,1000)
        self.Show()
        self.controlsVsizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.sizer.Add(self.controlsVsizer,0,flag=wx.ALIGN_LEFT,border=wx.BORDER_DOUBLE)
        self.mainPanelSizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.controlsPanel = wx.Panel(self,-1)
        self.controlsPanel.SetBackgroundColour("Orange")
        self.mainPanel = wx.Panel(parent=self)
        self.mainPanel.SetBackgroundColour("white")
        self.mainPanel.SetSizer(self.mainPanelSizer)
        self.controlsVsizer.Add(self.controlsPanel,0,flag=wx.ALIGN_TOP)
        self.viewmode = 'Physical'
        self.viewModeToggle = wx.RadioBox(parent=self.controlsPanel, id=-1, label="View Mode Selector", pos=(0, 0), choices=['Physical', 'Logical'])
        self.viewModeToggle.Bind(wx.EVT_RADIOBOX, self.changeViewMode)
        self.viewModeToggle.SetSelection(0)
        self.sizer.Add(self.mainPanel,1,flag=wx.ALIGN_LEFT | wx.EXPAND)
        self.drawDataTree()
        self.SetSizer(self.sizer)
        self.sizer.Layout()

    def showContextMenu(self, evt):
        print("Show me the context menu!!!!")
        cMenu = wx.Menu()
        itemData = self.myTree.GetItemData(evt.GetItem())
        print(self.myTree.GetFocusedItem())
        (x, y) = self.myTree.ScreenToClient(wx.GetMousePosition())
        print(x,y)
        if type(itemData) == dict:
            if itemData['treeItemType'] == 'property':
                print("No context menu associated with properties.")
            elif itemData['treeItemType'] == 'iomodule':
                print("treeItemType is iomodule. data is",itemData)
                menuItem = wx.MenuItem(parentMenu=cMenu,id=menuMapping['View Multiple Disk Details'],text='Detailed Disk View',
                                       helpString="Open a separate window to view the detailed list of disks viewed through IOmodule: "+itemData['name'])
                cMenu.Append(menuItem)
                result = self.myTree.GetPopupMenuSelectionFromUser(menu=cMenu, pos=(x, y))
                chassis = itemData['chassis']
                iomodule = itemData['name']
                disks = self.storage_info_obj.chassis[chassis]['iomodules'][iomodule]['disks']
                if result == menuMapping['View Multiple Disk Details']:
                    self.openDiskPropertiesGridWindow(disks=disks)
            elif itemData['treeItemType'] == 'disk':
                cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=menuMapping['Copy'],text='Copy Disk Name',helpString='Copy the disk name to clipboard'))
                cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=menuMapping['Copy As Dictionary'],text='Copy All Disk Properties',helpString='Copy all disk data to clipboard.'))
                cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=wx.ID_SEPARATOR))
                cMenu.Append(wx.MenuItem(parentMenu=cMenu, id=menuMapping['View Single Disk Details'], text='View Details',helpString='Open a new window to view detailed information about this hard drive.'))
                result = self.myTree.GetPopupMenuSelectionFromUser(menu=cMenu, pos=(x, y))
                if result == menuMapping['Copy']:
                    data = wx.TextDataObject(text=str(itemData['properties']['name']))
                    if wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(data=data)
                        wx.TheClipboard.Close()
                elif result == menuMapping['Copy As Dictionary']:
                    try:
                        tempProperties = itemData['properties']
                        tempProperties['fullpath'] = str(itemData['properties']['fullpath']) #fullpath contains an object type which is not JSON serializable.
                        data = wx.TextDataObject(text=json.dumps(tempProperties))
                    except KeyError:
                        data = wx.TextDataObject(text=json.dumps(itemData['properties']))
                    if wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(data=data)
                        wx.TheClipboard.Close()
                elif result == menuMapping['View Single Disk Details']:
                    if 'detailedDisk' not in self.contentWindows:
                        self.contentWindows['detailedDisk'] = singleDiskDetailedViewWindow(parent=self,allProperties=itemData['properties'])
                    else:
                        try:
                            self.contentWindows['detailedDisk'].Close()
                        except Exception as e:
                            print(e)
                        self.contentWindows['detailedDisk'] = singleDiskDetailedViewWindow(parent=self,allProperties=itemData['properties'])

    def openDiskPropertiesGridWindow(self, disks):
        if 'disks' not in self.contentWindows:
            self.contentWindows['disks'] = diskPropertiesGridWindow(parent=self,disks=disks)
        else:
            try:
                self.contentWindows['disks'].Close()
            except Exception as e:
                print(e)
            self.contentWindows['disks'] = diskPropertiesGridWindow(parent=self,disks=disks)

    def changeViewMode(self, evt):
        selections = ['Physical','Logical']
        print("view mode changed to ", self.viewModeToggle.GetStringSelection())
        self.viewmode = self.viewModeToggle.GetStringSelection()
        self.drawDataTree()

    def drawDataTree(self):
        self.mainPanelSizer.Clear()
        for child in self.mainPanel.Children:
                try:
                    child.Destroy()
                except RuntimeError as r:
                    print(r)
        trees = {'Physical':self.drawPhysicalTree,'Logical':self.drawLogicalTree}
        trees[self.viewmode]()
        self.myTree.Bind(event=wx.EVT_TREE_ITEM_RIGHT_CLICK, handler=self.showContextMenu)


    def drawPhysicalTree(self):
        print("The size of mainpanel is",self.mainPanel.GetSize())
        self.myTree = wx.TreeCtrl(self.mainPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TR_HAS_BUTTONS)
        self.myTree.SetBackgroundColour(None)
        self.root = self.myTree.AddRoot('Chassis')
        self.myTree.Expand(self.root)
        for chassis in self.storage_info_obj.chassis:
            print(chassis)
            self.chassisTreeBuilder(chassis)
        self.myTree.ExpandAll()
        self.mainPanelSizer.Add(self.myTree, 0, wx.ALIGN_LEFT | wx.EXPAND)
        self.mainPanelSizer.Layout()
        self.sizer.Layout()

    def chassisTreeBuilder(self,chassis):
        properties = {'index': '|Index', 'slot': '|Slot', 'name': '|Name', 'mpathdmname': '|Multipath DM',
                      'mpathname': '|Multipath Friendly', 'dmraidpart': '|RAID Partition DM',
                      'dmraidpartname': '|RAID Partition Name',
                      'mdparent': '|RAID Device', 'sasaddress': '|SAS Address', 'ident': "|LED Status"}
        self.leafRef[chassis] = self.myTree.AppendItem(self.root, chassis)
        print(self.myTree.GetRootItem())
        self.leafRef[chassis+'.revision'] = self.myTree.AppendItem(self.leafRef[chassis], 'Revision: '+self.storage_info_obj.chassis[chassis]['revision'])
        self.myTree.SetItemData(item=self.leafRef[chassis+'.revision'],data={'treeItemType':'property','name':'revision','value':self.storage_info_obj.chassis[chassis]['revision']})
        self.leafRef[chassis+'.logicalid'] = self.myTree.AppendItem(self.leafRef[chassis], 'Logicalid: '+self.storage_info_obj.chassis[chassis]['logicalid'])
        self.myTree.SetItemData(item=self.leafRef[chassis + '.logicalid'],data={'treeItemType': 'property', 'name': 'logicalid','value': self.storage_info_obj.chassis[chassis]['logicalid']})
        self.leafRef[chassis+'.numslots'] = self.myTree.AppendItem(self.leafRef[chassis], '# Slots: '+str(self.storage_info_obj.chassis[chassis]['numslots']))
        self.myTree.SetItemData(item=self.leafRef[chassis + '.numslots'],data={'treeItemType': 'property', 'name': 'numslots','value': self.storage_info_obj.chassis[chassis]['numslots']})
        self.leafRef[chassis+'.model'] = self.myTree.AppendItem(self.leafRef[chassis], 'Model: '+self.storage_info_obj.chassis[chassis]['model'])
        self.myTree.SetItemData(item=self.leafRef[chassis + '.model'],data={'treeItemType': 'property', 'name': 'model','value': self.storage_info_obj.chassis[chassis]['model']})
        self.leafRef[chassis+'.iomodules'] = self.myTree.AppendItem(self.leafRef[chassis], 'IOmodules:')
        for iomodule in self.storage_info_obj.chassis[chassis]['iomodules']:
            self.leafRef[chassis+'.iomodules.'+iomodule] = self.myTree.AppendItem(self.leafRef[chassis+'.iomodules'], iomodule )
            self.myTree.SetItemData(self.leafRef[chassis+'.iomodules.'+iomodule],{'treeItemType':'iomodule','name':iomodule,'chassis':chassis})
            for item in self.storage_info_obj.chassis[chassis]['iomodules'][iomodule]:
                if item == 'disks':
                    for disk in self.storage_info_obj.chassis[chassis]['iomodules'][iomodule]['disks']:
                        self.leafRef[chassis+'.iomodules.'+iomodule+'.'+disk['name']] = self.myTree.AppendItem(self.leafRef[chassis+'.iomodules.'+iomodule],
                                                                                                               'Index: '+disk['index']+' Slot: '+disk['slot']+' Kernel Name: /dev/'+disk['name'])
                        self.myTree.SetItemData(item=self.leafRef[chassis+'.iomodules.'+iomodule+'.'+disk['name']], data={'treeItemType':'disk','properties':disk})
                else:
                    self.leafRef[chassis+'.iomodules.'+iomodule+'.'+item] = self.myTree.AppendItem(self.leafRef[chassis+'.iomodules.'+iomodule], item)
                    self.myTree.SetItemData(item=self.leafRef[chassis+'.iomodules.'+iomodule+'.'+item],data={'treeItemType':'iomodule','chassis':chassis,'name':item})


    def drawLogicalTree(self):
        self.myTree = wx.TreeCtrl(self.mainPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TR_HAS_BUTTONS)
        self.myTree.SetBackgroundColour(None)
        self.root = self.myTree.AddRoot('Server')
        self.mainPanelSizer.Add(self.myTree)
        self.myTree.Expand(self.root)

class singleDiskDetailedViewWindow(windowBase):
    def __init__(self, parent=None, allProperties={}):
        print("Creating a disk details window.!!")
        super(singleDiskDetailedViewWindow, self).__init__(parent=parent, title="Disk Properties")
        self.SetTitle('Detailed Properties View for /dev/' + allProperties['name'])
        self.properties = {'index': 'Index', 'slot': 'Slot', 'name': 'Name', 'mpathdmname': 'Multipath DM',
                           'mpathname': 'Multipath Friendly', 'dmraidpart': 'RAID Partition DM',
                           'dmraidpartname': 'RAID Partition Name', 'raidrole': "RAID Member Status",
                           'mdparent': 'RAID Device', 'sasaddress': 'SAS Address', 'ident': " Locate LED Status",
                           'fault': 'Fault LED Status', 'devtype': 'Device Driver',
                           'enclosure': 'Input/Output Module', 'parents': 'Device Hiearchy',
                           'minor': 'Device Minor Number', 'major': 'Device Major Number'}
        self.inverseProperties = {self.properties[key]: key for key in self.properties}
        self.otherProperties = {key: allProperties[key] for key in allProperties if
                                key not in self.properties.keys()}
        self.myGrid = wx.grid.Grid(parent=self, id=wx.ID_ANY)
        self.myGrid.CreateGrid(numRows=len(self.properties) + len(self.otherProperties), numCols=1)
        self.myGrid.SetColLabelSize(0)
        self.myGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.showContextMenu)
        # Adding rows from self.properties translation matrix.
        for idx, property in enumerate(self.properties.values()):
            self.myGrid.SetRowLabelValue(idx, property)
        for idx, property in enumerate(self.properties.keys()):
            self.myGrid.SetCellValue(idx, 0, str(allProperties[property]))
        # Adding rows for properties outside the translation matrix.
        nextRowIndex = len(self.properties.keys())
        for idx, property in enumerate(self.otherProperties.keys()):
            print(idx, property)
            idxx = nextRowIndex + idx
            self.myGrid.SetRowLabelValue(row=idxx, value=property)
            self.myGrid.SetCellValue(idxx, 0, str(self.otherProperties[property]))

        self.myGrid.EnableEditing(False)
        self.myGrid.AutoSizeColumn(0)
        self.myGrid.SetRowLabelSize(wx.grid.GRID_AUTOSIZE)
        self.myGrid.Show()
        self.Show()
        totalWidth = self.myGrid.GetRowLabelSize() + self.myGrid.GetColSize(0)
        totalHeight = 0
        for i in range(self.myGrid.GetNumberRows()):
            totalHeight = totalHeight + self.myGrid.GetRowSize(i)
        totalHeight = 1000
        self.SetSize(totalWidth, totalHeight)

    def showContextMenu(self, evt):
        cMenu = wx.Menu()
        diskOpMenu = diskOperationsMenu()
        eventRow = evt.GetRow()
        eventCol = evt.GetCol()
        colLabel = self.myGrid.GetColLabelValue(eventCol)
        itemData = self.myGrid.GetCellValue(eventRow,eventCol)
        #Set up context menu options
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=menuMapping['Copy'],text='Copy Cell Data',helpString='Copy the contents of a cell to the clipboard.'))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=wx.ID_SEPARATOR))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=wx.ID_ANY,text='Disk Operations',subMenu=diskOpMenu))
        result = self.myGrid.GetPopupMenuSelectionFromUser(cMenu,self.myGrid.ScreenToClient(wx.GetMousePosition()))
        if result == menuMapping['Copy']:
            data = wx.TextDataObject(text=str(itemData))
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data=data)
                wx.TheClipboard.Close()
        elif result == menuMapping['Turn On Both LEDs']:
            pass
        else:
            message = wx.MessageDialog(parent=self,message='Not yet implemented!',caption='Error',style=wx.OK | wx.ICON_ERROR)
            message.ShowModal()
            message.Destroy()
        print("The user selected menu item with id", result)


class diskPropertiesGridWindow(windowBase):
    def __init__(self, parent=None, disks=[]):
        super(diskPropertiesGridWindow, self).__init__(parent=parent, title="Disk Properties Grid")
        self.properties = {'index': 'Index', 'slot': 'Slot', 'name': 'Name', 'mpathdmname': 'Multipath DM',
                      'mpathname': 'Multipath Friendly', 'dmraidpart': 'RAID Partition DM',
                      'dmraidpartname': 'RAID Partition Name', 'raidrole': "RAID Member Status",
                      'mdparent': 'RAID Device', 'sasaddress': 'SAS Address', 'ident': "LED Status"}
        self.inverseProperties = {self.properties[key]:key for key in self.properties}
        self.disks = disks
        # self.contentWindows = {}
        self.SetBackgroundColour("Orange")
        self.SetTitle("Disk properties.")
        self.myGrid = wx.grid.Grid(self,-1)
        self.myGrid.CreateGrid(numRows=len(disks),numCols=len(self.properties))
        self.myGrid.EnableEditing(False)
        self.myGrid.Bind(event=wx.grid.EVT_GRID_CELL_RIGHT_CLICK,handler=self.showContextMenu)
        self.myGrid.SetRowLabelSize(0)
        print('the size of the grid is',self.myGrid.GetSize())
        idy = 0

        for property in self.properties:
            print('Trying to set the table headings.')
            # self.myGrid.SetCellValue(0,idy,properties[property])
            self.myGrid.SetColLabelValue(idy,self.properties[property])
            idy = idy + 1
        for idx, disk in enumerate(disks):
            for idy, property in enumerate(self.properties.keys()):
                self.myGrid.SetCellValue(idx,idy,disk[property])
                self.myGrid.SetCellBackgroundColour(idx,idy,self.propertyValueTest(property=property,value=disk[property]))
        totalwidth = 0
        for i in range(self.myGrid.GetNumberCols()):
            self.myGrid.AutoSizeColumn(i)
            print(i)
            print("total width before",totalwidth)
            totalwidth = totalwidth + self.myGrid.GetColSize(i)
            print("Total width after",totalwidth)

        self.myGrid.Show()
        self.SetSize(totalwidth,1000)
        self.Show()


    def propertyValueTest(self,property,value):
        good = '#42f548'
        caution = '#ffaa00'
        bad = 'red'
        neutral = '#afb0a7'
        if property == 'mdparent':
            if 'md' in value:
                return good
            else:
                return bad
        elif property == 'ident':
            if value == '0' or value == 0:
                return good
            elif value == 'error':
                return bad
            else:
                return caution
        else:
            if value == 'error':
                return bad
            else:
                return good
    def showContextMenu(self, evt):
        cMenu = wx.Menu()
        eventRow = evt.GetRow()
        eventCol = evt.GetCol()
        colLabel = self.myGrid.GetColLabelValue(eventCol)
        itemData = self.myGrid.GetCellValue(eventRow,eventCol)
        print("Right clicked on row ",colLabel)
        print(itemData)
        print(self.myGrid.GetSelectedRows())
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=20000,text='Copy Cell Data',helpString='Copy the contents of a cell to the clipboard.'))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu, id=20001, text='Copy Row Data Without Labels',helpString='Copy the contents of the entire row to the clipboard as a JSON string without labels.'))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu, id=20002, text='Copy Row Data With Labels',helpString='Copy the contents of the entire row to the clipboard as a JSON string with labels.'))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=wx.ID_SEPARATOR))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu, id=20003, text='Show Expanded Disk Properties',helpString='Show all disk properties.'))
        cMenu.Append(wx.MenuItem(parentMenu=cMenu,id=20004,text='Disk Operations'))
        result = self.myGrid.GetPopupMenuSelectionFromUser(cMenu,self.myGrid.ScreenToClient(wx.GetMousePosition()))
        if result == 20000:
            data = wx.TextDataObject(text=str(itemData))
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data=data)
                wx.TheClipboard.Close()
        elif result == 20001:
            data = []
            for i in range(self.myGrid.NumberCols):
                data.append(self.myGrid.GetCellValue(eventRow,i))
            data = wx.TextDataObject(text=json.dumps(data))
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data=data)
                wx.TheClipboard.Close()
        elif result == 20002:
            data = {}
            for i in range(self.myGrid.NumberCols):
                label = self.inverseProperties[self.myGrid.GetColLabelValue(i)]
                data[label] = self.myGrid.GetCellValue(eventRow,i)
            data = wx.TextDataObject(text=json.dumps(data))
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data=data)
                wx.TheClipboard.Close()

        elif result == 20003:
            if 'detailedDisk' not in self.contentWindows:
                self.contentWindows['detailedDisk'] = singleDiskDetailedViewWindow(parent=self,
                                                                                   allProperties=self.disks[int(self.myGrid.GetCellValue(eventRow,0))])
            else:
                try:
                    self.contentWindows['detailedDisk'].Close()
                except Exception as e:
                    print(e)
                self.contentWindows['detailedDisk'] = singleDiskDetailedViewWindow(parent=self,allProperties=self.disks[int(self.myGrid.GetCellValue(eventRow,0))])