#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

# Copyright (c) 2018,2019,2020,2021, Stephen Goadhouse <sgoadhouse@virginia.edu>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#-------------------------------------------------------------------------------
#  HP/Agilent/Keysight specific SCPI commands
#-------------------------------------------------------------------------------

# For future Python3 compatibility:
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from . import Oscilloscope
except Exception:
    from oscilloscope import Oscilloscope

from time import sleep
from datetime import datetime
from quantiphy import Quantity
from sys import version_info
import pyvisa as visa

class Keysight(Oscilloscope):
    """Child class of Oscilloscope for controlling and accessing a HP/Agilent/Keysight Oscilloscope with PyVISA and SCPI commands"""

    def __init__(self, resource, maxChannel, wait=0):
        """Init the class with the instruments resource string

        resource   - resource string or VISA descriptor, like TCPIP0::172.16.2.13::INSTR
        maxChannel - number of channels of this oscilloscope
        wait       - float that gives the default number of seconds to wait after sending each command
        """
        # NOTE: maxChannel is accessible in this package via parent as: self._max_chan
        super(Keysight, self).__init__(resource, maxChannel, wait,
                                       cmd_prefix=':',
                                       read_strip='\n',
                                       read_termination='',
                                       write_termination='\n'
        )

        # Return list of valid analog channel strings. These are numbers.
        self._chanAnaValidList = [str(x) for x in range(1,self._max_chan+1)]

        # list of ALL valid channel strings.
        #
        # NOTE: Currently, only valid values are a CHAN+numerical string for
        # the analog channels, POD1 for digital channels 0-7 or POD2 for
        # digital channels 8-15
        self._chanAllValidList = [self.channelStr(x) for x in range(1,self._max_chan+1)] + [str(x) for x in ['POD1','POD2']]

        # This will store annotation text if that feature is used
        self._annotationText = ''
        self._annotationColor = 'ch1' # default to Channel 1 color

        
    def annotate(self, text, color=None, background='TRAN'):
        """ Add an annotation with text, color and background to screen

            text - text of annotation. Can include \n for newlines (two characters)

            color - see annotateColor for possible strings

            background - string, one of TRAN - transparent, OPAQue or INVerted (ignored unless sw version <= 2.60)
        """

        # Save annotation text because may need it if change color
        self._annotationText = text

        # Next, if <= 2.60, set color first. if > 2.60,
        # annotateColor() also displays the annotation. Also handles
        # case of color is None.
        self.annotateColor(color)
        
        if (self._version <= 2.60):
            # Legacy commands for annotations
            #
            # Add an annotation to the screen
            self._instWrite("DISPlay:ANN:BACKground {}".format(background))   # transparent background - can also be OPAQue or INVerted
            self._instWrite('DISPlay:ANN:TEXT "{}"'.format(text))
            self._instWrite("DISPlay:ANN ON")
            
    ## Use to convert legacy color names
    _colorNameOldtoNew = {
        'ch1':    'CHAN1',
        'ch2':    'CHAN2',
        'ch3':    'CHAN3',
        'ch4':    'CHAN4',
        'ch5':    'CHAN5',
        'ch6':    'CHAN6',
        'ch7':    'CHAN7',
        'ch8':    'CHAN8',
        'dig':    'DCH',
        'math':   'FUNC1',
        'ref':    'WMEM',
        'marker': 'MARK',
        'white':  'FUNC14',         # closest match
        'red':    'FUNC12'          # no good match
    }
            
    def annotateColor(self, color):
        """ Change screen annotation color """

        ## NOTE: Only certain values are allowed. These are legacy names (<= 2.60)
        # {CH1 | CH2 | CH3 | CH4 | DIG | MATH | REF | MARK | WHIT | RED}
        #
        # The scope will respond with an error if an invalid color string is passed along
        #
        # If > 2.60, will translate color names
        
        if (self._version > 2.60):
            if (color is not None):
                # save color
                self._annotationColor = color

            # Place Bookmark in top left of grid
            self._instWrite("DISPlay:BOOKmark1:XPOSition 0.015")
            self._instWrite("DISPlay:BOOKmark1:YPOSition 0.06")

            #@@@#print("Current Location of Bookmark 1: {},{}".format(
            #@@@#    self._instQuery("DISPlay:BOOKmark1:XPOSition?"), self._instQuery("DISPlay:BOOKmark1:YPOSition?")))
            
            # Always use the first Bookmark to implement similar annotation to 3000 series
            self._instWrite('DISPlay:BOOKmark1:SET NONE,\"{}\",{},\"{}\"'.format(
                self._annotationText,
                self._colorNameOldtoNew[self._annotationColor],
                self._annotationText))
            
        elif (color is not None):
            # If legacy and color is None, ignore
            self._instWrite("DISPlay:ANN:COLor {}".format(color))

    def annotateOff(self):
        """ Turn off screen annotation """

        if (self._version > 2.60):
            self._instWrite("DISPlay:BOOKmark1:DELete")
        else:
            self._instWrite("DISPlay:ANN OFF")
        

    def channelLabel(self, label, channel=None):
        """ Add a label to selected channel (or default one if None)

            label - text of label
        """

        # If a channel value is passed in, make it the
        # current channel
        if channel is not None and type(channel) is not list:
            self.channel = channel

        # Make sure channel is NOT a list
        if type(self.channel) is list or type(channel) is list:
            raise ValueError('Channel cannot be a list for CHANNEL LABEL!')

        # Check channel value
        if (self.channel not in self._chanAnaValidList):
            raise ValueError('INVALID Channel Value for CHANNEL LABEL: {}  SKIPPING!'.format(self.channel))
            
        self._instWrite('CHAN{}:LABel "{}"'.format(self.channel, label))
        self._instWrite('DISPlay:LABel ON')

    def channelLabelOff(self):
        """ Turn off channel labels """

        self._instWrite('DISPlay:LABel OFF')


    def setupAutoscale(self, channel=None):
        """ Autoscale desired channel, which is a string. channel can also be a list of multiple strings"""

        # If a channel value is passed in, make it the
        # current channel and process the list, viewing only these channels
        if channel is not None:
            self.channel = channel

            # Make channel a list even if it is a single value
            if type(self.channel) is not list:
                chanlist = [self.channel]
            else:
                chanlist = self.channel

            # Turn off all channels
            self.outputOffAll()
            
            # Turn on selected channels
            chanstr = ''
            for chan in chanlist:                        
                # Check channel value
                if (chan not in self._chanAllValidList):
                    print('INVALID Channel Value for AUTOSCALE: {}  SKIPPING!'.format(chan))
                else:
                    self._instWrite("VIEW {}".format(chan))
                    
        # Make sure Autoscale is only autoscaling displayed channels
        #@@@#self._instWrite("AUToscale:CHANnels DISPlayed")

        # Issue autoscale
        self.autoscale()

    def polish(self, value, measure=None):
        """ Using the QuantiPhy package, return a value that is in apparopriate Si units.

        If value is >= self.OverRange, then return the invalid string instead of a Quantity().

        If the measure string is None, then no units are used by the SI suffix is.

        """

        if (value >= self.OverRange):
            pol = '------'
        else:
            try:
                pol = Quantity(value, self._measureTbl[measure][0])
            except KeyError:
                # If measure is None or does not exist
                pol = Quantity(value)

        return pol


    def _measureStatistics(self):
        """Returns data from the current statistics window.
        """

        # tell Results? return all values (as opposed to just one of them)
        self._instWrite("MEASure:STATistics ON")

        # create a list of the return values, which are seperated by a comma
        statFlat = self._instQuery("MEASure:RESults?").split(',')

        # Return flat, uninterpreted data returned from command
        return statFlat
    

    def _readDVM(self, mode, channel=None, timeout=None, wait=0.5):
        """Read the DVM data of desired channel and return the value.

        channel: channel, as a string, to set to DVM mode and return its
        reading - becomes the default channel for future readings

        timeout: if None, no timeout, otherwise, time-out in seconds
        waiting for a valid number

        wait: Number of seconds after select DVM mode before trying to
        read values. Set to None for no waiting (not recommended)
        """

        # If a channel value is passed in, make it the
        # current channel
        if channel is not None and type(channel) is not list:
            self.channel = channel

        # Make sure channel is NOT a list
        if type(self.channel) is list or type(channel) is list:
            raise ValueError('Channel cannot be a list for DVM!')

        # Check channel value
        if (self.channel not in self._chanAnaValidList):
            raise ValueError('INVALID Channel Value for DVM: {}  SKIPPING!'.format(self.channel))
            
        # First check if DVM is enabled
        if (not self.DVMisEnabled()):
            # It is not enabled, so enable it
            self.enableDVM(True)
            
        # Next check if desired DVM channel is the source, if not switch it
        #
        # NOTE: doing it this way so as to not possibly break the
        # moving average since do not know if buffers are cleared when
        # the SOURCE command is sent even if the channel does not
        # change.
        src = self._instQuery("DVM:SOURce?")
        #print("Source: {}".format(src))
        if (self._chanNumber(src) != self.channel):
            # Different channel value so switch it
            #print("Switching to {}".format(self.channel))
            self._instWrite("DVM:SOURce {}".format(self.channelStr(self.channel)))

        # Select the desired DVM mode
        self._instWrite("DVM:MODE {}".format(mode))

        # wait a little before read value to make sure everything is switched
        if (wait):
            sleep(wait)

        # Read value until get one < +9.9E+37 (per programming guide suggestion)
        startTime = datetime.now()
        val = self.OverRange
        while (val >= self.OverRange):
            duration = datetime.now() - startTime
            if (timeout is not None and duration.total_seconds() >= timeout):
                # if timeout is a value and have been waiting that
                # many seconds for a valid DVM value, stop waiting and
                # return this self.OverRange number.
                break

            val = self._instQueryNumber("DVM:CURRent?")

        # if mode is frequency, read and return the 5-digit frequency instead
        if (mode == "FREQ"):
            val = self._instQueryNumber("DVM:FREQ?")

        return val

    def DVMisEnabled(self):
        """Return True is DVM is enabled, else False"""

        en = self._instQuery("DVM:ENABle?")
        return self._1OR0(en)

    def enableDVM(self, enable=True):
        """Enable or Disable DVM

        enable: If True, Enable (turn on) DVM mode, else Disable (turn off) DVM mode
        """

        if (enable):
            self._instWrite("DVM:ENABLE ON")
        else:
            self._instWrite("DVM:ENABLE OFF")

        
    def measureDVMacrms(self, channel=None, timeout=None, wait=0.5):
        """Measure and return the AC RMS reading of channel using DVM
        mode.

        AC RMS is defined as 'the root-mean-square value of the acquired
        data, with the DC component removed.'

        channel: channel, as a string, to set to DVM mode and return its
        reading - becomes the default channel for future readings

        timeout: if None, no timeout, otherwise, time-out in seconds
        waiting for a valid number - if timeout, returns self.OverRange
        """

        return self._readDVM("ACRM", channel, timeout, wait)

    def measureDVMdc(self, channel=None, timeout=None, wait=0.5):
        """ Measure and return the DC reading of channel using DVM mode.

        DC is defined as 'the DC value of the acquired data.'

        channel: channel, as a string, to set to DVM mode and return its
        reading - becomes the default channel for future readings

        timeout: if None, no timeout, otherwise, time-out in seconds
        waiting for a valid number - if timeout, returns self.OverRange
        """

        return self._readDVM("DC", channel, timeout, wait)

    def measureDVMdcrms(self, channel=None, timeout=None, wait=0.5):
        """ Measure and return the DC RMS reading of channel using DVM mode.

        DC RMS is defined as 'the root-mean-square value of the acquired data.'

        channel: channel, as a string, to set to DVM mode and return its
        reading - becomes the default channel for future readings

        timeout: if None, no timeout, otherwise, time-out in seconds
        waiting for a valid number - if timeout, returns self.OverRange
        """

        return self._readDVM("DCRM", channel, timeout, wait)

    def measureDVMfreq(self, channel=None, timeout=3, wait=0.5):
        """ Measure and return the FREQ reading of channel using DVM mode.

        FREQ is defined as 'the frequency counter measurement.'

        channel: channel, as a string, to set to DVM mode and return its
        reading - becomes the default channel for future readings

        timeout: if None, no timeout, otherwise, time-out in seconds
        waiting for a valid number - if timeout, returns self.OverRange

        NOTE: If the signal is not periodic, this call will block until
        a frequency is measured, unless a timeout value is given.
        """

        return self._readDVM("FREQ", channel, timeout, wait)

    def _measure(self, mode, para=None, channel=None, wait=0.25, install=False):
        """Read and return a measurement of type mode from channel

           para - parameters to be passed to command

           channel - channel to be measured starting at 1. Must be a string, ie. '1'

           wait - if not None, number of seconds to wait before querying measurement

           install - if True, adds measurement to the statistics display
        """

        # If a channel value is passed in, make it the
        # current channel
        if channel is not None and type(channel) is not list:
            self.channel = channel

        # Make sure channel is NOT a list
        if type(self.channel) is list or type(channel) is list:
            raise ValueError('Channel cannot be a list for MEASURE!')

        # Check channel value
        if (self.channel not in self._chanAllValidList):
            raise ValueError('INVALID Channel Value for MEASURE: {}  SKIPPING!'.format(self.channel))
            
        # Next check if desired channel is the source, if not switch it
        #
        # NOTE: doing it this way so as to not possibly break the
        # moving average since do not know if buffers are cleared when
        # the SOURCE command is sent even if the channel does not
        # change.
        src = self._instQuery("MEASure:SOURce?")
        #print("Source: {}".format(src))
        if (src != self.channel):
            # Different channel so switch it
            #print("Switching to {}".format(self.channel))
            self._instWrite("MEASure:SOURce {}".format(self.channel))

        if (para):
            # Need to add parameters to the write and query strings
            strWr = "MEASure:{} {}".format(mode, para)
            strQu = "MEASure:{}? {}".format(mode, para)
        else:
            strWr = "MEASure:{}".format(mode)
            strQu = "MEASure:{}?".format(mode)

        if (install):
            # If desire to install the measurement, make sure the
            # statistics display is on and then use the command form of
            # the measurement to install the measurement.
            self._instWrite("MEASure:STATistics:DISPlay ON")
            self._instWrite(strWr)

        # wait a little before read value, if wait is not None
        if (wait):
            sleep(wait)

        # query the measurement (do not have to install to query it)
        val = self._instQuery(strQu)

        return float(val)


    def measureBitRate(self, channel=None, wait=0.25, install=False):
        """Measure and return the bit rate measurement.

        This measurement is defined as: 'measures all positive and
        negative pulse widths on the waveform, takes the minimum value
        found of either width type and inverts that minimum width to
        give a value in Hertz'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display

        """

        return self._measure("BRATe", channel=channel, wait=wait, install=install)

    def measureBurstWidth(self, channel=None, wait=0.25, install=False):
        """Measure and return the bit rate measurement.

        This measurement is defined as: 'the width of the burst on the
        screen.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("BWIDth", channel=channel, wait=wait, install=install)

    def measureCounterFrequency(self, channel=None, wait=0.25, install=False):
        """Measure and return the counter frequency

        This measurement is defined as: 'the counter frequency.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - issues if install, so this paramter is ignored
        """

        # NOTE: The programmer's guide suggests sending a :MEASURE:CLEAR
        # first because if COUNTER is installed for ANY channel, this
        # measurement will fail. Note doing the CLEAR, but if COUNTER
        # gets installed, this will fail until it gets manually CLEARed.

        return self._measure("COUNter", channel=channel, wait=wait, install=False)

    def measurePosDutyCycle(self, channel=None, wait=0.25, install=False):
        """Measure and return the positive duty cycle

        This measurement is defined as: 'The value returned for the duty
        cycle is the ratio of the positive pulse width to the
        period. The positive pulse width and the period of the specified
        signal are measured, then the duty cycle is calculated with the
        following formula:

        duty cycle = (+pulse width/period)*100'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("DUTYcycle", channel=channel, wait=wait, install=install)

    def measureFallTime(self, channel=None, wait=0.25, install=False):
        """Measure and return the fall time

        This measurement is defined as: 'the fall time of the displayed
        falling (negative-going) edge closest to the trigger
        reference. The fall time is determined by measuring the time at
        the upper threshold of the falling edge, then measuring the time
        at the lower threshold of the falling edge, and calculating the
        fall time with the following formula:

        fall time = time at lower threshold - time at upper threshold'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("FALLtime", channel=channel, wait=wait, install=install)

    def measureRiseTime(self, channel=None, wait=0.25, install=False):
        """Measure and return the rise time

        This measurement is defined as: 'the rise time of the displayed
        rising (positive-going) edge closest to the trigger
        reference. For maximum measurement accuracy, set the sweep speed
        as fast as possible while leaving the leading edge of the
        waveform on the display. The rise time is determined by
        measuring the time at the lower threshold of the rising edge and
        the time at the upper threshold of the rising edge, then
        calculating the rise time with the following formula:

        rise time = time at upper threshold - time at lower threshold'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("RISetime", channel=channel, wait=wait, install=install)

    def measureFrequency(self, channel=None, wait=0.25, install=False):
        """Measure and return the frequency of cycle on screen

        This measurement is defined as: 'the frequency of the cycle on
        the screen closest to the trigger reference.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("FREQ", channel=channel, wait=wait, install=install)

    def measureNegDutyCycle(self, channel=None, wait=0.25, install=False):
        """Measure and return the negative duty cycle

        This measurement is defined as: 'The value returned for the duty
        cycle is the ratio of the negative pulse width to the
        period. The negative pulse width and the period of the specified
        signal are measured, then the duty cycle is calculated with the
        following formula:

        -duty cycle = (-pulse width/period)*100'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("NDUTy", channel=channel, wait=wait, install=install)

    def measureFallEdgeCount(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen falling edge count

        This measurement is defined as: 'the on-screen falling edge
        count'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("NEDGes", channel=channel, wait=wait, install=install)

    def measureFallPulseCount(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen falling pulse count

        This measurement is defined as: 'the on-screen falling pulse
        count'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("NPULses", channel=channel, wait=wait, install=install)

    def measureNegPulseWidth(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen falling/negative pulse width

        This measurement is defined as: 'the width of the negative pulse
        on the screen closest to the trigger reference using the
        midpoint between the upper and lower thresholds.

        FOR the negative pulse closest to the trigger point:

        width = (time at trailing rising edge - time at leading falling edge)'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("NWIDth", channel=channel, wait=wait, install=install)

    def measureOvershoot(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen voltage overshoot in percent

        This measurement is defined as: 'the overshoot of the edge
        closest to the trigger reference, displayed on the screen. The
        method used to determine overshoot is to make three different
        vertical value measurements: Vtop, Vbase, and either Vmax or
        Vmin, depending on whether the edge is rising or falling.

        For a rising edge:

        overshoot = ((Vmax-Vtop) / (Vtop-Vbase)) x 100

        For a falling edge:

        overshoot = ((Vbase-Vmin) / (Vtop-Vbase)) x 100

        Vtop and Vbase are taken from the normal histogram of all
        waveform vertical values. The extremum of Vmax or Vmin is taken
        from the waveform interval right after the chosen edge, halfway
        to the next edge. This more restricted definition is used
        instead of the normal one, because it is conceivable that a
        signal may have more preshoot than overshoot, and the normal
        extremum would then be dominated by the preshoot of the
        following edge.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("OVERshoot", channel=channel, wait=wait, install=install)

    def measurePreshoot(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen voltage preshoot in percent

        This measurement is defined as: 'the preshoot of the edge
        closest to the trigger, displayed on the screen. The method used
        to determine preshoot is to make three different vertical value
        measurements: Vtop, Vbase, and either Vmin or Vmax, depending on
        whether the edge is rising or falling.

        For a rising edge:

        preshoot = ((Vmin-Vbase) / (Vtop-Vbase)) x 100

        For a falling edge:

        preshoot = ((Vmax-Vtop) / (Vtop-Vbase)) x 100

        Vtop and Vbase are taken from the normal histogram of all
        waveform vertical values. The extremum of Vmax or Vmin is taken
        from the waveform interval right before the chosen edge, halfway
        back to the previous edge. This more restricted definition is
        used instead of the normal one, because it is likely that a
        signal may have more overshoot than preshoot, and the normal
        extremum would then be dominated by the overshoot of the
        preceding edge.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("PREShoot", channel=channel, wait=wait, install=install)

    def measureRiseEdgeCount(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen rising edge count

        This measurement is defined as: 'the on-screen rising edge
        count'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("PEDGes", channel=channel, wait=wait, install=install)

    def measureRisePulseCount(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen rising pulse count

        This measurement is defined as: 'the on-screen rising pulse
        count'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("PPULses", channel=channel, wait=wait, install=install)

    def measurePosPulseWidth(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen falling/positive pulse width

        This measurement is defined as: 'the width of the displayed
        positive pulse closest to the trigger reference. Pulse width is
        measured at the midpoint of the upper and lower thresholds.

        IF the edge on the screen closest to the trigger is falling:

        THEN width = (time at trailing falling edge - time at leading rising edge)

        ELSE width = (time at leading falling edge - time at leading rising edge)'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("PWIDth", channel=channel, wait=wait, install=install)

    def measurePeriod(self, channel=None, wait=0.25, install=False):
        """Measure and return the on-screen period

        This measurement is defined as: 'the period of the cycle closest
        to the trigger reference on the screen. The period is measured
        at the midpoint of the upper and lower thresholds.

        IF the edge closest to the trigger reference on screen is rising:

        THEN period = (time at trailing rising edge - time at leading rising edge)

        ELSE period = (time at trailing falling edge - time at leading falling edge)'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("PERiod", channel=channel, wait=wait, install=install)

    def measureVoltAmplitude(self, channel=None, wait=0.25, install=False):
        """Measure and return the vertical amplitude of the signal

        This measurement is defined as: 'the vertical amplitude of the
        waveform. To determine the amplitude, the instrument measures
        Vtop and Vbase, then calculates the amplitude as follows:

        vertical amplitude = Vtop - Vbase'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VAMPlitude", channel=channel, wait=wait, install=install)

    def measureVoltAverage(self, channel=None, wait=0.25, install=False):
        """Measure and return the Average Voltage measurement.

        This measurement is defined as: 'average value of an integral
        number of periods of the signal. If at least three edges are not
        present, the oscilloscope averages all data points.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VAVerage", para="DISPlay", channel=channel, wait=wait, install=install)

    def measureVoltRMS(self, channel=None, wait=0.25, install=False):
        """Measure and return the DC RMS Voltage measurement.

        This measurement is defined as: 'the dc RMS value of the
        selected waveform. The dc RMS value is measured on an integral
        number of periods of the displayed signal. If at least three
        edges are not present, the oscilloscope computes the RMS value
        on all displayed data points.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VRMS", para="DISPlay", channel=channel, wait=wait, install=install)

    def measureVoltBase(self, channel=None, wait=0.25, install=False):
        """Measure and return the Voltage base measurement.

        This measurement is defined as: 'the vertical value at the base
        of the waveform. The base value of a pulse is normally not the
        same as the minimum value.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VBASe", channel=channel, wait=wait, install=install)

    def measureVoltTop(self, channel=None, wait=0.25, install=False):
        """Measure and return the Voltage Top measurement.

        This measurement is defined as: 'the vertical value at the top
        of the waveform. The top value of the pulse is normally not the
        same as the maximum value.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VTOP", channel=channel, wait=wait, install=install)

    def measureVoltMax(self, channel=None, wait=0.25, install=False):
        """Measure and return the Maximum Voltage measurement.

        This measurement is defined as: 'the maximum vertical value
        present on the selected waveform.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VMAX", channel=channel, wait=wait, install=install)


    def measureVoltMin(self, channel=None, wait=0.25, install=False):
        """Measure and return the Minimum Voltage measurement.

        This measurement is defined as: 'the minimum vertical value
        present on the selected waveform.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VMIN", channel=channel, wait=wait, install=install)


    def measureVoltPP(self, channel=None, wait=0.25, install=False):
        """Measure and return the voltage peak-to-peak measurement.

        This measurement is defined as: 'the maximum and minimum
        vertical value for the selected source, then calculates the
        vertical peak-to-peak value and returns that value. The
        peak-to-peak value (Vpp) is calculated with the following
        formula:

        Vpp = Vmax - Vmin

        Vmax and Vmin are the vertical maximum and minimum values
        present on the selected source.'

        If the returned value is >= self.OverRange, then no valid value
        could be measured.

        channel: channel, as string, to be measured - default channel
        for future readings

        wait - if not None, number of seconds to wait before querying measurement

        install - if True, adds measurement to the statistics display
        """

        return self._measure("VPP", channel=channel, wait=wait, install=install)

    ## This is a dictionary of measurement labels with their units and
    ## method to get the data from the scope.
    _measureTbl = {
        'Bit Rate': ['Hz', measureBitRate],
        'Burst Width': ['s', measureBurstWidth],
        'Counter Freq': ['Hz', measureCounterFrequency],
        'Frequency': ['Hz', measureFrequency],
        'Period': ['s', measurePeriod],
        'Duty': ['%', measurePosDutyCycle],
        'Neg Duty': ['%', measureNegDutyCycle],
        'Fall Time': ['s', measureFallTime],
        'Rise Time': ['s', measureRiseTime],
        'Num Falling': ['', measureFallEdgeCount],
        'Num Neg Pulses': ['', measureFallPulseCount],
        'Num Rising': ['', measureRiseEdgeCount],
        'Num Pos Pulses': ['', measureRisePulseCount],
        '- Width': ['s', measureNegPulseWidth],
        '+ Width': ['s', measurePosPulseWidth],
        'Overshoot': ['%', measureOvershoot],
        'Preshoot': ['%', measurePreshoot],
        'Amplitude': ['V', measureVoltAmplitude],
        'Top': ['V', measureVoltTop],
        'Base': ['V', measureVoltBase],
        'Maximum': ['V', measureVoltMax],
        'Minimum': ['V', measureVoltMin],
        'Pk-Pk': ['V', measureVoltPP],
        'V p-p': ['V', measureVoltPP],
        'Average - Full Screen': ['V', measureVoltAverage],
        'RMS - Full Screen': ['V', measureVoltRMS],
        }

    