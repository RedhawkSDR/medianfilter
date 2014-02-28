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
import unittest
import ossie.utils.testing
from ossie.utils import sb
import os
from omniORB import any
import time
from ossie.cf import CF
from omniORB import CORBA
import math

class ComponentTests(ossie.utils.testing.ScaComponentTestCase):
    """Test for all component implementations in fcalc"""

    #utility methods to help with SCA set up and tear down for testing

    def setProps(self, filtLen=None):
        myProps=[]
        if filtLen!=None:
            self.filtLen = filtLen
            myProps.append(CF.DataType(id='filtLen',value=CORBA.Any(CORBA.TC_ushort, self.filtLen)))

        if myProps:

            #configure it
            self.comp.configure(myProps)

    def setUp(self):
        """Set up the unit test - this is run before every method that starts with test
        """
        ossie.utils.testing.ScaComponentTestCase.setUp(self)
        self.src = sb.DataSource()
        self.sink = sb.DataSink()
        
        #setup my components
        self.setupComponent()
        
        self.setProps(filtLen = 7)
        
        self.comp.start()
        self.src.start()
        self.sink.start()
        
        #do the connections
        self.src.connect(self.comp)        
        self.comp.connect(self.sink,'floatIn')
        self.output={}
        
    def tearDown(self):
        """Finish the unit test - this is run after every method that starts with test
        """
        self.comp.stop()
        #######################################################################
        # Simulate regular component shutdown
        self.comp.releaseObject()
        self.sink.stop()      
        ossie.utils.testing.ScaComponentTestCase.tearDown(self)

    def setupComponent(self):
        """Standard start-up for testing the component
        """
        #######################################################################
        # Launch the component with the default execparams
        execparams = self.getPropertySet(kinds=("execparam",), modes=("readwrite", "writeonly"), includeNil=False)
        execparams = dict([(x.id, any.from_any(x.value)) for x in execparams])
        self.launch(execparams, initialize=True)
        
        #######################################################################
        # Verify the basic state of the component
        self.assertNotEqual(self.comp, None)
        self.assertEqual(self.comp.ref._non_existent(), False)
        self.assertEqual(self.comp.ref._is_a("IDL:CF/Resource:1.0"), True)
       # self.assertEqual(self.spd.get_id(), self.comp.ref._get_identifier())
        
        #######################################################################
        # Simulate regular component startup
        # Verify that initialize nor configure throw errors
        #self.comp.initialize()
        configureProps = self.getPropertySet(kinds=("configure",), modes=("readwrite", "writeonly"), includeNil=False)
        self.comp.configure(configureProps)
        
        #######################################################################
        # Validate that query returns all expected parameters
        # Query of '[]' should return the following set of properties
        expectedProps = []
        expectedProps.extend(self.getPropertySet(kinds=("configure", "execparam"), modes=("readwrite", "readonly"), includeNil=True))
        expectedProps.extend(self.getPropertySet(kinds=("allocate",), action="external", includeNil=True))
        props = self.comp.query([])
        props = dict((x.id, any.from_any(x.value)) for x in props)
        # Query may return more than expected, but not less
        for expectedProp in expectedProps:
            self.assertEquals(props.has_key(expectedProp.id), True)
        
        #######################################################################
        # Verify that all expected ports are available
        for port in self.scd.get_componentfeatures().get_ports().get_uses():
            port_obj = self.comp.getPort(str(port.get_usesname()))
            self.assertNotEqual(port_obj, None)
            self.assertEqual(port_obj._non_existent(), False)
            self.assertEqual(port_obj._is_a("IDL:CF/Port:1.0"),  True)
            
        for port in self.scd.get_componentfeatures().get_ports().get_provides():
            port_obj = self.comp.getPort(str(port.get_providesname()))
            self.assertNotEqual(port_obj, None)
            self.assertEqual(port_obj._non_existent(), False)
            self.assertEqual(port_obj._is_a(port.get_repid()),  True)

                
    def testOne(self):
        """Send a simple ramp threw the filter and note the filter delay
        """
        input = [float(x) for x in range(20)] 
        self.main(input)
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput)

    def testTwo(self):
        """Send the same ramp threw the filter but send it one sample at a time to ensure filtering works properly
           with transitions regardless of transfer length
        """
        input = [float(x) for x in range(20)] 
        for val in input:
            self.src.push([val])
        self.main()
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput)    
    
    def testThree(self):
        """Send the same ramp threw the filter but send it a few samples at a time to ensure filtering works properly
           with transitions regardless of transfer length
        """
        input = [float(x) for x in range(20)] 
        numSamples = 4
        numPushes = (len(input)+numSamples-1)/numSamples
        for i in xrange(numPushes):
            inData = input[i*numSamples:(i+1)*numSamples]
            self.src.push(inData)
        self.main()
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput)  
    
    def testChangeFiltLenSmaller(self):
        
        input = [float(x) for x in range(20)] 
        self.main(input)
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput)
        
        self.setProps(filtLen = 5)
        self.output={}
        self.main(input)
        delay = (self.filtLen)/2
        #the filter is already primed  so we have two extra samples at the front
        #filter values will be as follows:
        #[16,17,18,19,0] -> 17; 
        #[17,18,19,0,1] -> 17; 
        #[18,19,0,1,2] -> 2; 
        #[19,0,1,2,3] -> 2 
        expectedOutput = [17, 17, 2.0, 2.0]
        expectedOutput.extend(input[delay:-delay])
        self.checkResults(expectedOutput)

    def testChangeFiltLenLarger(self):
        
        input = [float(x) for x in range(20)] 
        self.main(input)
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput)
        
        self.setProps(filtLen = 9)
        self.output={}
        self.main(input)
        delay = (self.filtLen)/2
        #the filter is already primed  so we have extra samples at the front
        #filter values will be as follows:s
        #[12,13,14,15,16,17,18,19,0] -> 15; 
        #[13,14,15,16,17,18,19,0,1] -> 15; 
        #[14,15,16,17,18,19,0,1,2] -> 15
        #[15,16,17,18,19,0,1,2,3] -> 15;
        #[16,17,18,19,0,1,2,3,4] - > 4;
        #[17,18,19,0,1,2,3,4,5] - > 4;
        #[18,19,0,1,2,3,4,5,6] - > 4;
        #[19,0,1,2,3,4,5,6,7] - > 4;
        expectedOutput = [15.0, 15.0, 15.0, 15.0, 4.0, 4.0,4.0,4.0]
        expectedOutput.extend(input[delay:-delay])
        self.checkResults(expectedOutput)
        
    def testSinWave(self):
        f = .01
        input = [math.sin(2*math.pi*f*i) for i in xrange(int(2/f))]
        self.main(input)
        delay = (self.filtLen)/2
        expectedOutput = []
        outData = self.output.values()[0]
        maxVal = max(outData)
        minVal = min(outData)
        #just chop off the top and bottom part of the sin wave 
        for x in input[delay:-delay]:
            if x>maxVal:
                expectedOutput.append(maxVal)
            elif x<minVal:
                expectedOutput.append(-maxVal)
            else:
                expectedOutput.append(x) 
                       
        self.checkResults(expectedOutput)   
    
    def testEos(self):
        """Verify the end of stream is working properly
        """
        input = [float(x) for x in range(20)] 
        self.main(input)
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.output={}
        self.main(input,True)
        for x, y in zip(expectedOutput, self.output.values()[0]):
                self.assertNotAlmostEqual(x,y)
        self.output={}
        self.main(input)
        self.checkResults(expectedOutput)      

    def testMultiStream(self):
        """Verify the end of stream is working properly
        """
        input = [float(x) for x in range(20)] 
        numSamples = 4
        numPushes = (len(input)+numSamples-1)/numSamples
        #sadly ... need to do this as two seperate transactions do to a limitation in the sink
        for i in xrange(numPushes):
            inData = input[i*numSamples:(i+1)*numSamples]
            self.src.push(inData, streamID='stream1')
        self.main()
        for i in xrange(numPushes):
            inData = input[i*numSamples:(i+1)*numSamples]
            self.src.push(inData, streamID='stream2')
        self.main()
        delay = (self.filtLen)/2
        expectedOutput = input[delay:-delay]
        self.checkResults(expectedOutput, 'stream2')  
        
    def main(self,inData=None, eos=False):
        """The main engine for all the test cases - configure the equation, push data, and get output
           As applicable
        """
        #data processing is asynchronos - so wait until the data is all processed
        count=0
        if inData:
            self.src.push(inData, EOS=eos)
        while True:
            newData = self.sink.getData()
            if newData:
                streamID = self.sink.sri().streamID
                oldData = self.output.setdefault(self.sink.sri().streamID,[])
                oldData.extend(newData)
                count=0
            else:
                count+=1
                time.sleep(.01)
                count+=1
            if count==40:
                break

    
    def checkResults(self, expectedOutput,streamID=None):
        if streamID==None and len(self.output)==1:
            output = self.output.values()[0]
        else:
            output = self.output[streamID]
                   
        self.assertEqual(len(expectedOutput), len(output))
        if expectedOutput:
            for x, y in zip(expectedOutput, output):
                self.assertAlmostEqual(x,y)
   
if __name__ == "__main__":
    ossie.utils.testing.main("../medianfilter.spd.xml") # By default tests all implementations
