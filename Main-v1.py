import sys,atexit,thread,time,os,ConfigParser

import serial
from PyQt4 import QtCore,QtGui


from LaserControl import Ui_MainWindow
try:
    _fromUtf8 = QtCore.Qstring._fromUtf8
except AttributeError:
    _fromUtf8 = lambda s:s

class mainApp(QtGui.QMainWindow, Ui_MainWindow):
    logfile = None
    """docstring for mainApp"""
    def __init__(self, parent=None):
        super(mainApp, self).__init__(parent)
        self.setupUi(self)

        # Load configuration file
        #cfgpath=os.path.split(os.path.abspath(__file__))[0]
        if '__file__' in dir():
            cfgpath=os.path.split(os.path.abspath(__file__))[0]
        else: # fix for py2exe
            cfgpath=sys.prefix
        cfgpath=os.path.join(cfgpath, "cfg.txt")
        self.cfg=ConfigParser.ConfigParser()
        self.cfg.readfp(open(cfgpath))

        # Detect number of laser lines
        sections = self.cfg.sections()
        if "serial port" not in sections:
            raise Exception, "invalid configuration file"
        self.laserlabels = sections
        self.laserlabels.remove("serial port")
        self.laserlabels.sort()
        self.nlines=len(self.laserlabels)
        self._power=[0]*self.nlines
        self._shutter=[0]*self.nlines

        # define close event
        QtCore.QObject.connect(self, QtCore.SIGNAL('triggered()'), self.closeEvent)

        # bind signal and slot
        for n in xrange(5):
            if n == 0:
                QtCore.QObject.connect(self.laserLine1Shutter,
                QtCore.SIGNAL(_fromUtf8("stateChanged(int)")),
                self.actionShutterLaserLine1)
                QtCore.QObject.connect(self.laserLine1PowerSlider,
                QtCore.SIGNAL(_fromUtf8("valueChanged(int)")),
                self.actionPowerSliderLaserLine1)
                QtCore.QObject.connect(self.laserLine1PowerEdit,
                QtCore.SIGNAL(_fromUtf8("returnPressed")),
                self.actionPowerEditLaserLine1)
                QtCore.QObject.connect(self.laserLine1Pulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionPulseLaserLine1)
            elif n == 1:
                QtCore.QObject.connect(self.laserLine2Shutter,
                QtCore.SIGNAL(_fromUtf8("stateChanged(int)")),
                self.actionShutterLaserLine2)
                QtCore.QObject.connect(self.laserLine2PowerSlider,
                QtCore.SIGNAL(_fromUtf8("valueChanged(int)")),
                self.actionPowerSliderLaserLine2)
                QtCore.QObject.connect(self.laserLine2PowerEdit,
                QtCore.SIGNAL(_fromUtf8("returnPressed")),
                self.actionPowerEditLaserLine2)
                QtCore.QObject.connect(self.laserLine2Pulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionPulseLaserLine2)
            elif n == 2:
                QtCore.QObject.connect(self.laserLine3Shutter,
                QtCore.SIGNAL(_fromUtf8("stateChanged(int)")),
                self.actionShutterLaserLine3)
                QtCore.QObject.connect(self.laserLine3PowerSlider,
                QtCore.SIGNAL(_fromUtf8("valueChanged(int)")),
                self.actionPowerSliderLaserLine3)
                QtCore.QObject.connect(self.laserLine3PowerEdit,
                QtCore.SIGNAL(_fromUtf8("returnPressed")),
                self.actionPowerEditLaserLine3)
                QtCore.QObject.connect(self.laserLine3Pulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionPulseLaserLine3)
            elif n == 3:
                QtCore.QObject.connect(self.laserLine4Shutter,
                QtCore.SIGNAL(_fromUtf8("stateChanged(int)")),
                self.actionShutterLaserLine4)
                QtCore.QObject.connect(self.laserLine4PowerSlider,
                QtCore.SIGNAL(_fromUtf8("valueChanged(int)")),
                self.actionPowerSliderLaserLine4)
                QtCore.QObject.connect(self.laserLine4PowerEdit,
                QtCore.SIGNAL(_fromUtf8("returnPressed")),
                self.actionPowerEditLaserLine4)
                QtCore.QObject.connect(self.laserLine4Pulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionPulseLaserLine4)
            elif n == 4:
                QtCore.QObject.connect(self.laserLine5Shutter,
                QtCore.SIGNAL(_fromUtf8("stateChanged(int)")),
                self.actionShutterLaserLine5)
                QtCore.QObject.connect(self.laserLine5PowerSlider,
                QtCore.SIGNAL(_fromUtf8("valueChanged(int)")),
                self.actionPowerSliderLaserLine5)
                QtCore.QObject.connect(self.laserLine5PowerEdit,
                QtCore.SIGNAL(_fromUtf8("returnPressed")),
                self.actionPowerEditLaserLine5)
                QtCore.QObject.connect(self.laserLine5Pulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionPulseLaserLine5)
        QtCore.QObject.connect(self.startRepeatPulse,
                QtCore.SIGNAL(_fromUtf8("clicked()")),
                self.actionStartPulsing)

        # Prepare threads and initialize AOTF connection
        self.lock=thread.allocate_lock()
        #   note, on PySerial lib the serial ports are N-1, so serial 2 will be represented by 1
        self.nserial=self.cfg.getint("serial port", "number")-1
        if self.nserial == -1: # Emulation mode
            self.aotfcmd_ = lambda cmd: 1
        else: # Not emulating
            self.aotf=serial.Serial(self.nserial, 19200, timeout=1)
            atexit.register(self.aotf.close)
            self.aotfcmd_('i0')
        self._lastcmd_=time.time()
        for n in range(self.nlines):
            self.shutter(n+1,0)
            self.power(n+1,0)
        thread.start_new(self.__repeatPulsing__, ())

    def aotfcmd_(self, cmd, wait = 0):
        self.lock.acquire()
        self.aotf.write(cmd+"\r")
        if wait:
            msg=''
            for n in xrange(10000):
                c=self.aotf.read()
                msg+=c
                if c=='?': break
        self.lock.release()
        self._lastcmd_=time.time() 
    def shutter(self, channel=1,on=True):
        if self._shutter[channel-1]==on: 
            return 
        self.aotfcmd_("x%d" % (channel), 1)
#        self.aotfcmd_("x" + str(channel), 1)
#        self.aotfcmd_("x1", 1)
        if on: 
            self.aotfcmd_("o1", 1)
        else: 
            self.aotfcmd_("o0",1)
        self._shutter[channel-1]=on
       
    def power(self, channel, percentage):
        if self._power[channel-1]==percentage: return
        p=(float(percentage)/100.)*1023
        if p>1023: p=1023
        elif p<0: p=0
        p=int(round(p))
        self.aotfcmd_("l%dp%s\n\n" % (channel, str(p).zfill(4)))
        self._power[channel-1]=percentage
    ####
#    def power(self,channel,value):
#        if self._power[channel-1]==value: return
#        if value>1023: value = 1023
#        elif value<0: value = 0
#        value = int(round(value))
#        self.aotfcmd_("l%dp%s\n\n" % (channel, str(p).zfill(4)))
#        self._power[channel-1]=value
    ##define laser 1#########################
    def actionShutterLaserLine1(self):
        self.shutter(1,self.laserLine1Shutter.checkState())
        msg = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[0],time.time(),int(self.laserLine1PowerEdit.text()),\
        self.laserLine1Shutter.checkState())
        self.msg(msg)
    def actionPowerSliderLaserLine1(self):
        #self._power[0] = self.laserLine1PowerSlider.value()
        self.power(1, self.laserLine1PowerSlider.value())
        self.laserLine1PowerEdit.setText(str(self._power[0]))
    def actionPowerEditLaserLine1(self):
        self._power[0] = int(self.actionPowerEditLaserLine1.text())
        self.power(1,self._power[0])
        self.actionPowerSliderLaserLine1.setValue(self._power[0])
    def actionPulseLaserLine1(self):
        waitTime = float(self.laserLine1PulseDuration.text())
        start = time.time()
        self.shutter(1, 1)
        time.sleep(waitTime)
        self.shutter(1,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[0],time.time(),int(self.laserLine1PowerEdit.text()),\
        self.laserLine1Shutter.checkState())
        self.msg(msg)
    ### end define laser 1 ##########################
    ##define laser 2#########################
    def actionShutterLaserLine2(self):
        self.shutter(2,self.laserLine2Shutter.checkState())
        msg = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[1],time.time(),int(round(float(self.laserLine2PowerEdit.text()))),\
        self.laserLine2Shutter.checkState())
        self.msg(msg)
    def actionPowerSliderLaserLine2(self):
        #self._power[1] = self.laserLine2PowerSlider.value()
        self.power(2, self.laserLine2PowerSlider.value())
        self.laserLine2PowerEdit.setText(str(self._power[1]))
    def actionPowerEditLaserLine2(self):
        self._power[1] = int(self.actionPowerEditLaserLine2.text())
        self.power(2,self._power[1])
        self.actionPowerSliderLaserLine2.setValue(self._power[1])
    def actionPulseLaserLine2(self):
        waitTime = float(self.laserLine2PulseDuration.text())
        start = time.time()
        self.shutter(2,1)
        time.sleep(waitTime)
        self.shutter(2,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[1],time.time(),int(round(float(self.laserLine2PowerEdit.text()))),\
        self.laserLine2Shutter.checkState())
        self.msg(msg)
    ### end define laser 2 ##########################
    ##define laser 3#########################
    def actionShutterLaserLine3(self):
        self.shutter(3,self.laserLine3Shutter.checkState())
        msg = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[2],time.time(),int(self.laserLine3PowerEdit.text()),\
        self.laserLine3Shutter.checkState())
        self.msg(msg)
    def actionPowerSliderLaserLine3(self):
        #self._power[2] = self.laserLine3PowerSlider.value()
        self.power(3, self.laserLine3PowerSlider.value())
        self.laserLine3PowerEdit.setText(str(self._power[2]))
    def actionPowerEditLaserLine3(self):
        self._power[2] = int(self.actionPowerEditLaserLine3.text())
        self.power(3,self._power[2])
        self.actionPowerSliderLaserLine3.setValue(self._power[2])
    def actionPulseLaserLine3(self):
        waitTime = float(self.laserLine3PulseDuration.text())
        start = time.time()
        self.shutter(3,1)
        time.sleep(waitTime)
        self.shutter(3,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[2],time.time(),int(round(float(self.laserLine3PowerEdit.text()))),\
        self.laserLine3Shutter.checkState())
        self.msg(msg)
    ### end define laser 3 ##########################
    ##define laser 4#########################
    def actionShutterLaserLine4(self):
        self.shutter(4,self.laserLine4Shutter.checkState())
        msg = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[3],time.time(),int(round(float(self.laserLine4PowerEdit.text()))),\
        self.laserLine4Shutter.checkState())
        self.msg(msg)
    def actionPowerSliderLaserLine4(self):
        #self._power[3] = self.laserLine4PowerSlider.value()
        self.power(4, self.laserLine4PowerSlider.value())
        self.laserLine4PowerEdit.setText(str(self._power[3]))
    def actionPowerEditLaserLine4(self):
        self._power[3] = int(self.actionPowerEditLaserLine4.text())
        self.power(4,self._power[3])
        self.actionPowerSliderLaserLine4.setValue(self._power[3])
    def actionPulseLaserLine4(self):
        waitTime = float(self.laserLine4PulseDuration.text())
        start = time.time()
        self.shutter(4,1)
        time.sleep(waitTime)
        self.shutter(4,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[3],time.time(),int(round(float(self.laserLine4PowerEdit.text()))),\
        self.laserLine4Shutter.checkState())
        self.msg(msg)
    ### end define laser 4 ##########################
    ##define laser 5#########################
    def actionShutterLaserLine5(self):
        self.shutter(5,self.laserLine5Shutter.checkState())
        msg = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[4],time.time(),int(round(float(self.laserLine5PowerEdit.text()))),\
        self.laserLine5Shutter.checkState())
        self.msg(msg)
    def actionPowerSliderLaserLine5(self):
        #self._power[4] = self.laserLine5PowerSlider.value()
        self.power(5, self.laserLine5PowerSlider.value())
        self.laserLine5PowerEdit.setText(str(self._power[4]))
    def actionPowerEditLaserLine5(self):
        self._power[4] = int(self.actionPowerEditLaserLine5.text())
        self.power(5,self._power[4])
        self.actionPowerSliderLaserLine5.setValue(self._power[4])
    def actionPulseLaserLine5(self):
        waitTime = float(self.laserLine5PulseDuration.text())
        start = time.time()
        self.shutter(5,1)
        time.sleep(waitTime)
        self.shutter(5,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % \
        (self.laserlabels[4],time.time(),int(round(float(self.laserLine5PowerEdit.text()))),\
        self.laserLine5Shutter.checkState())
        self.msg(msg)
    ### end define laser 3 ##########################
    
    def actionPulse(self,n):
        if (n==1):
            waitTime = float(self.laserLine1PulseDuration.text())
            power    = int(self.laserLine1PowerEdit.text())
        elif (n==2):
            waitTime = float(self.laserLine2PulseDuration.text())
            power    = int(self.laserLine2PowerEdit.text())
        elif n==3:
            waitTime = float(self.laserLine3PulseDuration.text())
            power    = int(self.laserLine3PowerEdit.text())
        elif n==4:
            waitTime = float(self.laserLine4PulseDuration.text())
            power    = int(self.laserLine4PowerEdit.text())
        elif n==5:
            waitTime = float(self.laserLine5PulseDuration.text())
            power    = int(self.laserLine4PowerEdit.text())
        else :
            return
        start = time.time()
        self.shutter(1,1)
        time.sleep(waitTime)
        self.shutter(1,0)
        stop = time.time()
        msg  = 'SHUTTER %s: TIME %.8f AOTF %.2f' % (self.laserlabels[n],time.time(),power)
        self.msg(msg)
    def actionStartPulsing(self, event):
        if event: event.Skip()
        pass

    def __repeatPulsing__(self):
        if self.repeatPulseIndicator.checkState():
            self.repeatPulseIndicator.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.repeatPulseIndicator.setCheckState(QtCore.Qt.Checked)
        while 1:
            try:
                if self.repeatPulseIndicator.checkState():
                    interval = float(self.repeatPulseDuration.text())
                    n = self.laserlabels.index(self.selectLaserLine.currentIndex())
                    self.actionPulse(n)
                    time.sleep(interval)
            except:
                time.sleep(0.1)
    def closeEvent(self, event):
        self.aotf.close()
        self.destroy()
    def msg(self,text):
        if self.logfile!=None:
            open(self.logfile,'a').write(txt+'\n')
            self.status.setText(text)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = mainApp()
    myapp.show()
    sys.exit(app.exec_())    