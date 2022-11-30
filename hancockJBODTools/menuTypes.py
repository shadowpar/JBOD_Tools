import wx


class diskOperationsMenu(wx.Menu):
    def __init__(self,*args,**kwargs):
        super(diskOperationsMenu, self).__init__(*args,**kwargs)
        self.ledOperationsMenu = ledOperationMenu()
        self.Append(wx.MenuItem(parentMenu=self,id=wx.ID_ANY,text='LED Operations',helpString='Turn disk LEDs on or off',subMenu=self.ledOperationsMenu))

class ledOperationMenu(wx.Menu):
    def __init__(self,*args,**kwargs):
        super(ledOperationMenu, self).__init__(*args,**kwargs)
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn On Both LEDs'],text='Turn on Both LEDs'))
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn Off Both LEDs'],text='Turn off Both LEDs'))
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn On Fault LED'],text='Turn on Fault LEDs'))
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn Off Fault LED'],text='Turn off Fault LED'))
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn On Locate LED'],text='Turn on Locate LED'))
        self.Append(wx.MenuItem(parentMenu=self,id=menuMapping['Turn Off Locate LED'],text='Turn off Locate LED'))


menuMapping = {'Copy':10,'Copy As List':'11','Copy As Dictionary':12,
               'Turn Off Both LEDs':20, 'Turn On Both LEDs':21,'Turn Off Fault LED':22,'Turn On Fault LED':23, 'Turn Off Locate LED':24,'Turn On Locate LED':25,
               'Full Removal':30,'Full Addition':31,
               'Mark Faulty':40,'Remove From RAID':41,'Add To RAID':42,
               'Run Short SMART Test':50,'Run Long SMART Test':52,'Show SMART Information':53,
               'Destroy Superblock':60,'Create RAID Partition':61,'Flush Multipath Device':62,'Check New Multipath Devices':63,
               'View Single Disk Details':70,'View Multiple Disk Details':71}
