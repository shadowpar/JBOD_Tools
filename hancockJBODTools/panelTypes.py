import wx

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