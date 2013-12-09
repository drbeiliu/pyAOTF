#!/usr/bin/env python
# Laser Control for QuickPALM
# Copyright (c) 2010, Ricardo Henriques
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the author nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

import wx, atexit, thread, serial, time, sys, os, ConfigParser

class LCFrame(wx.Frame):
    logfile=None
    show_log_gui = False

    def __init__(self, *args, **kwds):
        # Load configuration file
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
                
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.panel_2 = wx.Panel(self, -1)
        self.panel_1 = wx.Panel(self, -1)
        self.frame_1_statusbar = self.CreateStatusBar(1, 0)

        self.wxLabel=[]
        self.wxShutter=[]
        self.wxPower=[]
        self.wxPulse=[]
        self.wxPulseD=[]
        
        for laserlabel in self.laserlabels:
            self.wxLabel.append(wx.StaticText(self.panel_1, -1, laserlabel))
            self.wxShutter.append(wx.ToggleButton(self.panel_1, -1, "Shutter"))
            self.wxPower.append(wx.Slider(self.panel_1, -1, 0, 0, 100, style=wx.SL_HORIZONTAL|wx.SL_LABELS))
            self.wxPulseD.append(wx.TextCtrl(self.panel_1, -1, "0.01", style=wx.TE_CENTRE))
            self.wxPulse.append(wx.Button(self.panel_1, -1, "Pulse"))

        self.label_5 = wx.StaticText(self.panel_2, -1, " Repetitive pulsing... ")
        self.combo_box_1 = wx.ComboBox(self.panel_2, -1, choices=self.laserlabels, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.text_ctrl_2 = wx.TextCtrl(self.panel_2, -1, "1", style=wx.TE_CENTRE)
        self.button_2 = wx.ToggleButton(self.panel_2, -1, "Start pulsing")
        self.path = wx.TextCtrl(self, -1, "Copy directory root here...")
        self.prefix = wx.TextCtrl(self, -1, "Copy name prefix here...")
        self.button_1 = wx.ToggleButton(self, -1, "Observe Acquisition")

        self.__set_properties()
        self.__do_layout()
        
        mybind = lambda evt, f, n, obj: self.Bind(evt, lambda e: f(n), obj)
        for n in xrange(len(self.laserlabels)):
            mybind(wx.EVT_TOGGLEBUTTON, self.actionShutter, n, self.wxShutter[n])
            mybind(wx.EVT_COMMAND_SCROLL, self.actionPower, n, self.wxPower[n])
            mybind(wx.EVT_COMMAND_SCROLL_ENDSCROLL, self.actionPower, n, self.wxPower[n])
            mybind(wx.EVT_BUTTON, self.actionPulse, n, self.wxPulse[n])

        self.Bind(wx.EVT_TOGGLEBUTTON, self.actionStartPulsing, self.button_2)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.actionObserveAcquisition, self.button_1)

        # Prepare threads and initialize AOTF connection
        self.lock=thread.allocate_lock()
        #   note, on PySerial lib the serial ports are N-1, so serial 2 will be represented by 1
        self.nserial=self.cfg.getint("serial port", "number")-1
        if self.nserial == -1: # Emulation mode
            self.aotfcmd = lambda cmd: 1
        else: # Not emulating
            self.aotf=serial.Serial(self.nserial, 19200, timeout=1)
            atexit.register(self.aotf.close)
            self.aotfcmd('i0')
        self._lastcmd_=time.time()
        for n in range(self.nlines):
            self.shutter(n+1,0)
            self.power(n+1,0)
        thread.start_new(self.__pulsing__, ())
        
    def aotfcmd(self, cmd, wait = 0):
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
            
    def shutter(self, channel=1, on=True):
        if self._shutter[channel-1]==on:
            return
        self.aotfcmd("x%d" % (channel), 1)  
        if on: self.aotfcmd("o1", 1)
        else: self.aotfcmd("o0", 1)
        self._shutter[channel-1]=on
        
    def power(self, channel, percentage):
        if self._power[channel-1]==percentage: return
        p=(float(percentage)/100.)*1023
        if p>1023: p=1023
        elif p<0: p=0
        p=int(round(p))
        self.aotfcmd("l%dp%s\n\n" % (channel, str(p).zfill(4)))
        self._power[channel-1]=percentage
            
    def __set_properties(self):
        self.SetTitle("Laser Control for QuickPALM V1.0")
        self.frame_1_statusbar.SetStatusWidths([-1])
        # statusbar fields
        frame_1_statusbar_fields = ["Copyright Ricardo Henriques @ Pasteur - 2010"]
        for i in range(len(frame_1_statusbar_fields)):
            self.frame_1_statusbar.SetStatusText(frame_1_statusbar_fields[i], i)
            
        for n in range(self.nlines):
            self.wxShutter[n].SetToolTipString(self.laserlabels[n]+" shutter")
            self.wxPower[n].SetToolTipString("change power")
            self.wxPulseD[n].SetToolTipString("pulse duration in seconds")
            self.wxPulse[n].SetToolTipString("make a single pulse")

        self.combo_box_1.SetToolTipString("laser that will pulse")
        self.combo_box_1.SetSelection(0)
        self.text_ctrl_2.SetToolTipString("pulse interval in seconds")
        self.button_2.SetToolTipString("Rock and Roll!!!")

    def __do_layout(self):
        sizer_1 = wx.FlexGridSizer(5, 1, 0, 0)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer_1 = wx.GridSizer(self.nlines, 4, 0, 0)

        for n in range(self.nlines):
            grid_sizer_1.Add(self.wxLabel[n], 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 0)
            grid_sizer_1.Add(self.wxShutter[n], 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.SHAPED, 0)
            grid_sizer_1.Add(self.wxPower[n], 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.SHAPED, 0)
            pulsesizer = wx.BoxSizer(wx.VERTICAL)
            pulsesizer.Add(self.wxPulseD[n], 0, wx.EXPAND, 0)
            pulsesizer.Add(self.wxPulse[n], 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.SHAPED, 0)
            grid_sizer_1.Add(pulsesizer, 1, wx.EXPAND, 0)
 
        self.panel_1.SetSizer(grid_sizer_1)
        sizer_1.Add(self.panel_1, 1, wx.EXPAND, 0)
        sizer_3.Add(self.label_5, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_3.Add(self.combo_box_1, 1, 0, 0)
        sizer_3.Add(self.text_ctrl_2, 0, 0, 0)
        sizer_3.Add(self.button_2, 0, 0, 0)
        self.panel_2.SetSizer(sizer_3)
        sizer_1.Add(self.panel_2, 1, wx.EXPAND, 0)
        #sizer_1.Add(self.path, 0, wx.EXPAND, 0)
        #sizer_1.Add(self.prefix, 0, wx.EXPAND, 0)
        #sizer_1.Add(self.button_1, 0, wx.EXPAND, 0)
        if not self.show_log_gui:
            self.path.Hide()
            self.prefix.Hide()  
            self.button_1.Hide()
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.AddGrowableRow(0)
        self.Layout()
 
    def actionShutter(self, n):
        line = self.cfg.getint(self.laserlabels[n], "line")
        self.shutter(line, self.wxShutter[n].GetValue())
        msg='SHUTTER %s: TIME %.8f AOTF %.2f STATUS %d' % (self.laserlabels[n], time.time(), self.wxPower[n].GetValue(), self.wxShutter[n].GetValue())
        self.msg(msg)

    def actionPower(self, n):
        line = self.cfg.getint(self.laserlabels[n], "line")
        power= self.wxPower[n].GetValue()
        self.power(line, power)
        if self.wxShutter[n].GetValue():
            msg='POWER %s: TIME %.8f AOTF %.2f' % (self.laserlabels[n], time.time(), power)
            self.msg(msg)

    def actionPulse(self, n):
        line = self.cfg.getint(self.laserlabels[n], "line")
        wait=float(self.wxPulseD[n].GetValue())
        start=time.time()
        self.shutter(line, 1)
        time.sleep(wait)
        self.shutter(line, 0)
        stop=time.time()
        msg='PULSE %s: START %.8f STOP %.8f DURATION %.8f' % (self.laserlabels[n], start, stop, stop-start)
        self.msg(msg)

    def actionStartPulsing(self, event):
        if event: event.Skip()
        pass
        
    def __pulsing__(self):
        while 1:
            try:
                if self.button_2.GetValue():
                    interval=float(self.text_ctrl_2.GetValue())
                    n=self.laserlabels.index(self.combo_box_1.GetValue())
                    self.actionPulse(n)
                    time.sleep(interval)
            except:
                time.sleep(0.1)
            
    def actionObserveAcquisition(self, event):
        if event: event.Skip()
        if self.button_1.GetValue():
            targetdir=None
            path=self.path.GetValue()
            files = os.listdir(path)
            files.sort(lambda x,y:cmp(os.path.getmtime(os.path.join(path, x)),os.path.getmtime(os.path.join(path, y))))
            files.reverse()
            for filename in files:
                if self.prefix.GetValue() in filename and os.path.isdir(os.path.join(path, filename)):
                    targetdir=os.path.join(path, filename)
                    break
            if targetdir!=None:
                self.SetStatusText('Observing %s' % targetdir)
                self.logfile=os.path.join(targetdir, 'aotflog.txt')
                started=os.path.getctime(targetdir)
                msg='STARTED: TIME %.8f ' % started
                self.msg(msg)
                for n in range(self.nlines):
                    self.actionPower(n)                
        else:
            path=os.path.split(self.logfile)[0]
            filetimes={}
            for filename in os.listdir(path):
                if '.tif' in filename:
                    filepath=os.path.join(path, filename)
                    mtime=os.path.getmtime(filepath)
                    filetimes[mtime]=filename

            self.logfile=None
        
    def msg(self, txt):
        if self.logfile!=None:
            open(self.logfile, 'a').write(txt+'\n')
        self.SetStatusText(txt)

if __name__ == "__main__":
    PALMControl = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    try:
        frame_1 = LCFrame(None, -1, "")
        PALMControl.SetTopWindow(frame_1)
        frame_1.Show()
        PALMControl.MainLoop()
    except Exception, err:
        msg=wx.MessageDialog(None, str(err), "Error: "+str(type(err)), style=wx.ICON_ERROR)
        msg.ShowModal()
        raise Exception, msg