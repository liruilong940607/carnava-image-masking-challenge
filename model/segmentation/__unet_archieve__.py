# @lhc
class UNet1024_dropout (nn.Module):
    def __init__(self, in_shape):
        super(UNet1024_dropout, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4 = StackEncoder(128,  256, kernel_size=3)   # 64
        self.down5 = StackEncoder(256,  512, kernel_size=3)   # 32
        self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16

        self.center = nn.Sequential(
            ConvBnRelu2d(768, 768, kernel_size=3, padding=1, stride=1 ),
        )

        # 8
        # x_big_channels, x_channels, y_channels
        self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.drop = nn.Dropout2d(0.5)
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024
        out = self.drop(out)

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_GCN_baseline (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_baseline, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder(256, 512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  1024, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = GCN(1024,128,ks=7)
        #self.center = resnet_GCN(512, 128, 512)
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
        )


        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder(1024,1024, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out



class UNet1024_GCN_k15 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder(256, 512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  1024, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = GCN(1024,128,ks=7)
        self.center = resnet_GCN(512, 128, 512, ks=15)


        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder(1024,1024, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out



class UNet1024_GCN_k15_02 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15_02, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder(256, 512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  1024, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''

        self.gcn1 = resnet_GCN(24,24,24)
        self.gcn2 = resnet_GCN(64,32,64)
        self.gcn3 = resnet_GCN(128,32,128)
        self.gcn4 = resnet_GCN(256,64,256)
        self.gcn5 = resnet_GCN(512,128,512)
        #self.center = resnet_GCN(512, 128, 512, ks=15)
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
            resnet_GCN(512, 128, 512)
        )

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder(1024,1024, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)   #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5(self.gcn5( down5), out)
        out = self.up4(self.gcn4( down4), out)
        out = self.up3(self.gcn3( down3), out)
        out = self.up2(self.gcn2( down2), out)
        out = self.up1(self.gcn1( down1), out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_GCN_k15_03 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15_03, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder_GCN(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder_GCN(256, 512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  1024, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = resnet_GCN(512, 128, 512, ks=15)
        self.center = nn.Sequential(
            ConvBnRelu2d( 512, 512, kernel_size=3, padding=1, stride=1),
            resnet_GCN(512, 128, 512),
        )

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder(1024,1024, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #1024
        down2,out = self.down2(out)   #;print('down2',down2.size())  #512
        down3,out = self.down3(out)   #;print('down3',down3.size())  #256
        down4,out = self.down4(out)   #;print('down4',down4.size())  #128
        down5,out = self.down5(out)   #;print('down5',down5.size())  #64
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)        #32
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_GCN_k15_04 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15_04, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder_GCN(256, 512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  1024, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = resnet_GCN(512, 128, 512, ks=15)
        self.center = nn.Sequential(
            #ConvBnRelu2d( 512, 512, kernel_size=3, padding=1, stride=1),
            resnet_GCN(512, 128, 512),
        )

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder(1024,1024, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #1024
        down2,out = self.down2(out)   #;print('down2',down2.size())  #512
        down3,out = self.down3(out)   #;print('down3',down3.size())  #256
        down4,out = self.down4(out)   #;print('down4',down4.size())  #128
        down5,out = self.down5(out)   #;print('down5',down5.size())  #64
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)        #32
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_GCN_k15_05 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15_05, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder_GCN(256, 512, kernel_size=3)   # 32
        self.down6 = StackEncoder_GCN(512, 768, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = resnet_GCN(512, 128, 512, ks=15)
        self.center = nn.Sequential(
            #ConvBnRelu2d( 512, 512, kernel_size=3, padding=1, stride=1),
            resnet_GCN(768, 192, 768),
        )

        # 8
        # x_big_channels, x_channels, y_channels
        self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #1024
        down2,out = self.down2(out)   #;print('down2',down2.size())  #512
        down3,out = self.down3(out)   #;print('down3',down3.size())  #256
        down4,out = self.down4(out)   #;print('down4',down4.size())  #128
        down5,out = self.down5(out)   #;print('down5',down5.size())  #64
        down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)        #32
        out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_GCN_k15_07 (nn.Module): #Large kernel matters
    def __init__(self, in_shape):
        super(UNet1024_GCN_k15_07, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,  24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,  64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64, 128, kernel_size=3)   #128
        self.down4 = StackEncoder(128, 256, kernel_size=3)   # 64
        self.down5 = StackEncoder_GCN(256, 512, kernel_size=3)   # 32
        self.down6 = StackEncoder_GCN(512, 768, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        #self.center = resnet_GCN(512, 128, 512, ks=15)
        self.center = nn.Sequential(
            ConvBnRelu2d( 768, 768, kernel_size=3, padding=1, stride=1),
            #resnet_GCN(768, 192, 768),
        )

        # 8
        # x_big_channels, x_channels, y_channels
        self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #1024
        down2,out = self.down2(out)   #;print('down2',down2.size())  #512
        down3,out = self.down3(out)   #;print('down3',down3.size())  #256
        down4,out = self.down4(out)   #;print('down4',down4.size())  #128
        down5,out = self.down5(out)   #;print('down5',down5.size())  #64
        down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)        #32
        out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_ASPP (nn.Module):
    def __init__(self, in_shape):
        super(UNet1024_ASPP, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4 = StackEncoder(128,  256, kernel_size=3)   # 64
        self.down5 = StackEncoder(256,  512, kernel_size=3)   # 32
        self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16
        
        '''
        self.center = nn.Sequential(
            ConvBnRelu2d(1024, 1024, kernel_size=3, padding=1, stride=1 ),
        )
        '''
        self.center = ASPP(768, 768, 768, [6,12,18], [6,12,18])

        # 8
        # x_big_channels, x_channels, y_channels
        self.up6 = StackDecoder(768,768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_ASPP_03 (nn.Module):
    def __init__(self, in_shape):
        super(UNet1024_ASPP_03, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4_aspp = StackEncoder_ASPP(128,  256, kernel_size=3)   # 64
        self.down5_aspp = StackEncoder_ASPP(256,  512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16
        
        
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
        )
        
        #self.center = ASPP(768, 768, 768, [6,12,18], [6,12,18])

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5_aspp = StackDecoder_ASPP( 512, 512, 256, kernel_size=3)  # 32
        self.up4_aspp = StackDecoder_ASPP( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.aspp_out = ASPP(24, 24, 24, [6,12,18], [6,12,18])
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4_aspp(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5_aspp(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5_aspp(down5, out)
        out = self.up4_aspp(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024
        out = self.aspp_out(out)

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_ASPP_04 (nn.Module): #与03的区别是去掉了最后classify前的aspp，03的训练时间是～30min/epoch

    def __init__(self, in_shape):
        super(UNet1024_ASPP_04, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4_aspp = StackEncoder_ASPP(128,  256, kernel_size=3)   # 64
        self.down5_aspp = StackEncoder_ASPP(256,  512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16
        
        
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
        )
        
        #self.center = ASPP(768, 768, 768, [6,12,18], [6,12,18])

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5_aspp = StackDecoder_ASPP( 512, 512, 256, kernel_size=3)  # 32
        self.up4_aspp = StackDecoder_ASPP( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        #self.aspp_out = ASPP(24, 24, 24, [6,12,18], [6,12,18])
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4_aspp(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5_aspp(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5_aspp(down5, out)
        out = self.up4_aspp(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024
        #out = self.aspp_out(out)

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_ASPP_05 (nn.Module):
    def __init__(self, in_shape):
        super(UNet1024_ASPP_05, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4 = StackEncoder(128,  256, kernel_size=3)   # 64
        self.down5 = StackEncoder_ASPP(256,  512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16
        
        
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
        )
        
        #self.center = ASPP(768, 768, 768, [6,12,18], [6,12,18])

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder_ASPP( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        self.aspp_out = ASPP(24, 24, 24, [6,12,18], [6,12,18])
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        out = self.aspp_out(out)

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

class UNet1024_ASPP_06 (nn.Module):
    def __init__(self, in_shape):
        super(UNet1024_ASPP_06, self).__init__()
        C,H,W = in_shape
        #assert(C==3)

        #1024
        self.down1 = StackEncoder(  C,   24, kernel_size=3)   #512
        self.down2 = StackEncoder( 24,   64, kernel_size=3)   #256
        self.down3 = StackEncoder( 64,  128, kernel_size=3)   #128
        self.down4 = StackEncoder(128,  256, kernel_size=3)   # 64
        self.down5 = StackEncoder_ASPP(256,  512, kernel_size=3)   # 32
        #self.down6 = StackEncoder(512,  768, kernel_size=3)   # 16
        
        
        self.center = nn.Sequential(
            ConvBnRelu2d(512, 512, kernel_size=3, padding=1, stride=1 ),
        )
        
        #self.center = ASPP(768, 768, 768, [6,12,18], [6,12,18])

        # 8
        # x_big_channels, x_channels, y_channels
        #self.up6 = StackDecoder( 768, 768, 512, kernel_size=3)  # 16
        self.up5 = StackDecoder_ASPP( 512, 512, 256, kernel_size=3)  # 32
        self.up4 = StackDecoder( 256, 256, 128, kernel_size=3)  # 64
        self.up3 = StackDecoder( 128, 128,  64, kernel_size=3)  #128
        self.up2 = StackDecoder(  64,  64,  24, kernel_size=3)  #256
        self.up1 = StackDecoder(  24,  24,  24, kernel_size=3)  #512
        #self.aspp_out = ASPP(24, 24, 24, [6,12,18], [6,12,18])
        self.classify = nn.Conv2d(24, 1, kernel_size=1, padding=0, stride=1, bias=True)


    def forward(self, x):

        out = x                       #;print('x    ',x.size())
                                      #
        down1,out = self.down1(out)  #;print('down1',down1.size())  #256
        down2,out = self.down2(out)   #;print('down2',down2.size())  #128
        down3,out = self.down3(out)   #;print('down3',down3.size())  #64
        down4,out = self.down4(out)   #;print('down4',down4.size())  #32
        down5,out = self.down5(out)   #;print('down5',down5.size())  #16
        #down6,out = self.down6(out)   #;print('down6',down6.size())  #8
        #pass                          #;print('out  ',out.size())

        out = self.center(out)
        #out = self.up6(down6, out)
        out = self.up5(down5, out)
        out = self.up4(down4, out)
        out = self.up3(down3, out)
        out = self.up2(down2, out)
        out = self.up1(down1, out)
        #1024

        #out = self.aspp_out(out)

        out = self.classify(out)
        out = torch.squeeze(out, dim=1)
        return out

