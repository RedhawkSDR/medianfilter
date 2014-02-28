#!/usr/bin/env python 
#
# This file is protected by Copyright. Please refer to the COPYRIGHT file distributed with this 
# source distribution.
# 
# This file is part of REDHAWK Basic Components medianfilter.
# 
# REDHAWK Basic Components medianfilter is free software: you can redistribute it and/or modify it under the terms of 
# the GNU Lesser General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# REDHAWK Basic Components medianfilter is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License along with this 
# program.  If not, see http://www.gnu.org/licenses/.
#
#
# AUTO-GENERATED
#
# Source: medianfilter.spd.xml
# Generated on: Mon Feb 25 12:14:09 EST 2013
# Redhawk IDE
# Version:R.1.8.2
# Build id: v201212041901
from ossie.resource import Resource, start_component
import logging

from scipy.signal import medfilt

from medianfilter_base import * 

class MedianFilterState (object):
    MAX_DATA=32*1024
    def __init__(self):
        self.oldData=[]
        self.hasRun=False
    
    def getProcessData(self, data, filtDelay):
        oldDataLen = len(self.oldData)
        dataLen=  len(data)
        doProcess = True
        if self.hasRun: 
            #keep it running at all costs here - pad oldData if we don't have enough old data here to make it work
            if oldDataLen < filtDelay:
                #need to pad data:
                missingNum = filtDelay-oldDataLen
                self.oldData = self.oldData[0]*missingNum+self.oldData
        else:
            #we haven't run yet - if we don't have enough data then just be done with this thing
            if oldDataLen+dataLen < filtDelay:
                doProcess = False
        if doProcess:
            #normal case - grab the last filtDelay elements to feed them into the filter with our new data
            processData = self.oldData[-filtDelay:]
            processData.extend(data)
            self.hasRun = True
        else:
            processData = None
        #add the data to the old Data
        self.oldData.extend(data)
        
        #make sure we are keeping enough data if user has requested a HUGE filter delay
        if filtDelay> self.MAX_DATA:
            self.MAX_DATA = filtDelay
        #don't let our old data buffer be infinitly big
        if len(self.oldData) > self.MAX_DATA:
            self.oldData = self.oldData[-self.MAX_DATA:]
        return processData
            

class medianfilter_i(medianfilter_base):
    """This is a median filter component.  It has one property - filtLen
       filtLen must be odd
       
       This component leverages scipy to do the actual median filtering operation
       because  you don't have the state of the filter in scipy we solve this problem by caching off the last
       filtLen - 1 samples to re-run through the median filter
       
       filtering introduces a delay length.  The median filter is no exception
       We account for that by adjusting the sample offset in the time code
        
    """
    def initialize(self):
        """
        This is called by the framework immediately after your component registers with the NameService.
        """
        medianfilter_base.initialize(self)
        self.state={}
        

    def process(self):
        """Process loop
        """
        data, T, EOS, streamID, sri, sriChanged, inputQueueFlushed = self.port_dataFloat_in.getPacket()
        
        if data == None:
            return NOOP
        
        if self.state.has_key(streamID) and not inputQueueFlushed:
            state=self.state[streamID]
        else:
            state = MedianFilterState()
            self.state[streamID]= state
        
        if inputQueueFlushed:
            self._log.warning("inputQueueFlushed - state reset")
        
        if sriChanged or not self.port_dataFloat_out.sriDict.has_key(streamID):
            self.port_dataFloat_out.pushSRI(sri)
        
        #make sure that the filterLen is odd
        if (self.filtLen%2==0):
            self.filtLen=self.filtLen+1 #must be odd
        
        #cache off filtLen in case the user configures it - it will be applied next loop           
        thisFiltLen = self.filtLen
        filtDelay = thisFiltLen-1
        
        if len(data)>0:
            processData = state.getProcessData(data, filtDelay)
            if processData:
                halfDelay = filtDelay/2
                #make sure we have enough data to process
                out = medfilt(processData,thisFiltLen)
                #don't include the first and last elements as there is insufficient data to get their median properly
                outputData = out[halfDelay:-halfDelay]
                #adjust the time code for the delay caused by the filtering
                T.toff = halfDelay
                #push out the data
                self.port_dataFloat_out.pushPacket(outputData.tolist(), T, EOS, sri.streamID)
        if EOS:
            self.state.pop(streamID)
        return NORMAL
        
  
if __name__ == '__main__':
    logging.getLogger().setLevel(logging.WARN)
    logging.debug("Starting Component")
    start_component(medianfilter_i)
