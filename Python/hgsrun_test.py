'''
Created on Aug 11, 2016

Unittests for hgsrun components.

@author: Andre R. Erler, GPL v3
'''

import unittest
import numpy as np
import os, sys, gc, shutil


# import modules to be tested
from setup import Grok, GrokError, HGS, HGSError

# work directory settings ("global" variable)
data_root = os.getenv('DATA_ROOT', '')
# test folder either RAM disk or data directory
RAM = bool(os.getenv('RAMDISK', '')) # whether or not to use a RAM disk
# N.B.: the environment variable RAMDISK contains the path to the RAM disk
workdir = os.getenv('RAMDISK', '') if RAM else '{:s}/test/'.format(data_root)
if not os.path.isdir(workdir): raise IOError(workdir)
# other settings
NP = 2 # for parallel tests
ldebug = False # additional debug output
lbin = False # run executables

## tests for Grok class
class GrokTest(unittest.TestCase):  
  # some Grok test data
  hgs_template = data_root+'/HGS/Templates/GRW-test/' 
  hgs_testcase = 'grw_omafra' # name of test project (for file names)
  rundir       = '{}/grok_test/'.format(workdir,) # test folder
  grok_bin     = 'grok_premium.x' # Grok executable
   
  def setUp(self):
    ''' initialize a Grok instance '''
    if not os.path.isdir(self.hgs_template): 
      raise IOError("HGS Template for testing not found:\n '{}'".format(self.hgs_template))
    #if os.path.isdir(self.rundir): shutil.rmtree(self.rundir)
    #os.mkdir(self.rundir)
    if not os.path.isdir(self.rundir): os.mkdir(self.rundir)
    # grok test files
    self.grok_input  = '{}/{}.grok'.format(self.hgs_template,self.hgs_testcase)
    self.grok_output = '{}/{}.grok'.format(self.rundir,self.hgs_testcase)
    # some grok settings
    self.runtime = 5*365*24*60*60 # two years in seconds
    self.input_interval = 'monthly'
    self.input_mode = 'periodic'
    # create Grok instance
    self.grok = Grok(rundir=self.rundir, project=self.hgs_testcase, runtime=self.runtime,
                     input_mode=self.input_mode, input_interval=self.input_interval)
    # load a config file from template
    if not os.path.isfile(self.grok_input):
      raise IOError("Grok configuration file for testing not found:\n '{}'".format(self.grok_input))
    self.grok.read(folder=self.hgs_template)
    assert isinstance(self.grok._lines, list), self.grok._lines
      
  def tearDown(self):
    ''' clean up '''
    self.grok.write()
    del self.grok
    gc.collect()
    #shutil.rmtree(self.rundir)
 
  def testClass(self):
    ''' test instantiation of class '''    
    # instantiation done in self.setUp()
    assert self.grok.rundir, self.grok.rundir
    assert os.path.isdir(self.grok.rundir), self.grok.rundir
    
  def testInputLists(self):
    ''' test writing of input list files with climate forcings '''
    grok = self.grok  
    # write lists for fictional scenario
    grok.generateInputLists(input_mode='PET', input_prefix='test', 
                            input_folder=self.rundir, lvalidate=False,)
    # convert config file list into string and verify
    output = ''.join(grok._lines) # don't need newlines 
    assert 'precip.inc' in output
    assert 'pet.inc' in output    
    
  def testRunGrok(self):
    ''' test the Grok runner command (will fail, because other inputs are missing) '''
    grok = self.grok  
    exe = '{}/{}'.format(self.hgs_template,self.grok_bin)
    logfile = '{}/log.grok'.format(grok.rundir)
    # run Grok
    if not os.path.isfile(exe): raise IOError(exe)
    try: ec = grok.runGrok(executable=exe, logfile=logfile)
    except GrokError: ec = 1
    # check output
    batchpfx = '{}/batch.pfx'.format(self.rundir)
    assert os.path.isfile(batchpfx), batchpfx
    assert os.path.isfile(logfile), logfile
    assert ec > 0, ec
    
  def testSetTime(self):
    ''' test setting the run time variable in Grok config file '''
    grok = self.grok
    time = 24*60*60 # in seconds, i.e. one day
    # set run time
    grok.setRuntime(time)
    # test
    assert grok.runtime == time
    # convert config file list into string and verify
    output = ''.join(grok._lines) # don't need newlines 
    #print(output)
    assert '{:.3e}'.format(time) in output, '{:.3e}'.format(time)
    
  def testWrite(self):
    ''' load config file from template and write to rundir (on disk) '''
    grok = self.grok
    grok._lines = None # delete already loaded file contents
    # read from template
    assert os.path.isfile(self.grok_input), self.grok_input 
    grok.read(folder=self.hgs_template)
    assert isinstance(grok._lines, list), grok._lines
    # write to rundir
    grok.write() 
    assert os.path.isfile(self.grok_output), self.grok_output
    

## tests for HGS class
class HGSTest(GrokTest):  
  # some HGS test data
  rundir       = '{}/hgs_test/'.format(workdir,) # test folder
  hgs_bin      = 'hgs_premium.x' # HGS executable
  hgsdir       = os.getenv('HGSDIR',) # HGS license file
   
  def setUp(self):
    ''' initialize an HGS intance '''
    if not os.path.isdir(self.hgs_template): 
      raise IOError("HGS Template for testing not found:\n '{}'".format(self.hgs_template))
    #if os.path.isdir(self.rundir): shutil.rmtree(self.rundir)
    #os.mkdir(self.rundir)
    if not os.path.isdir(self.rundir): os.mkdir(self.rundir)
    # grok test files
    self.grok_input  = '{}/{}.grok'.format(self.hgs_template,self.hgs_testcase)
    self.grok_output = '{}/{}.grok'.format(self.rundir,self.hgs_testcase)
    # some grok settings
    self.runtime = 5*365*24*60*60 # two years in seconds
    self.input_interval = 'monthly'
    self.input_mode = 'periodic'
    # HGS settings
    self.NP = NP
    # create Grok instance
    self.hgs = HGS(rundir=self.rundir, project=self.hgs_testcase, runtime=self.runtime,
                     input_mode=self.input_mode, input_interval=self.input_interval, 
                     NP=self.NP)
    self.grok = self.hgs
    # load a config file from template
    if not os.path.isfile(self.grok_input):
      raise IOError("Grok configuration file for testing not found:\n '{}'".format(self.grok_input))
    self.grok.read(folder=self.hgs_template)
    assert isinstance(self.hgs._lines, list), self.hgs._lines

  def testParallelIndex(self):
    ''' test writing of parallelindex file '''
    hgs = self.hgs
    pidx_file = self.rundir+hgs.pidx_file
    # write parallelindex file to rundir
    hgs.writeParallelIndex(NP=1, parallelindex=pidx_file) 
    assert os.path.isfile(pidx_file), pidx_file
  
  def testRunGrok(self):
    ''' test the Grok runner command and check if flag is set correctly '''
    hgs = self.hgs  
    exe = '{}/{}'.format(self.hgs_template,self.grok_bin) # run folder not set up
    logfile = '{}/log.grok'.format(hgs.rundir)
    assert hgs.grokOK is None, hgs.grokOK
    # run Grok
    if not os.path.isfile(exe): raise IOError(exe)
    ec = hgs.runGrok(executable=exe, logfile=logfile, lerror=False)
    # check output
    batchpfx = self.rundir+hgs.batchpfx
    assert os.path.isfile(batchpfx), batchpfx
    assert os.path.isfile(logfile), logfile
    assert ec > 0, ec
    # check flag
    assert hgs.grokOK is False, hgs.grokOK

  def testRunHGS(self):
    ''' test the HGS runner command (will fail without proper folder setup) '''
    hgs = self.hgs  
    exe = '{}/{}'.format(self.hgs_template,self.hgs_bin) # run folder not set up
    logfile = '{}/log.hgs_run'.format(hgs.rundir)
    assert hgs.grokOK is None, hgs.grokOK
    # set environment variable for license file
    print('\nHGSDIR: {}\n'.format(self.hgsdir))
    # attempt to run HGS
    if not os.path.isfile(exe): raise IOError(exe)
    try: ec = hgs.runHGS(executable=exe, logfile=logfile, skip_grok=True)
    except HGSError: ec = 1
    # check output
    pidx_file = self.rundir+hgs.pidx_file
    assert os.path.isfile(pidx_file), pidx_file
    assert os.path.isfile(logfile), logfile
    assert ec > 0, ec
    # check flag
    assert hgs.grokOK is None, hgs.grokOK

  def testSetup(self):
    ''' test copying of a run folder from a template '''
    hgs = self.hgs
    # run setup
    hgs.setupRundir(template=None, bin_folder=None)
    # check that all items are there
    
    
if __name__ == "__main__":

    
    specific_tests = []
#     specific_tests += ['Class']
#     specific_tests += ['InputLists']
#     specific_tests += ['ParallelIndex']
#     specific_tests += ['RunGrok']
#     specific_tests += ['SetTime']
#     specific_tests += ['Write']

    lbin = True # execute binaries to test runner methods
#     lbin = False # don't execute binaries (takes very long)

    # list of tests to be performed
    tests = [] 
    # list of variable tests
    tests += ['Grok']
    tests += ['HGS']    

    # construct dictionary of test classes defined above
    test_classes = dict()
    local_values = locals().copy()
    for key,val in local_values.iteritems():
      if key[-4:] == 'Test':
        test_classes[key[:-4]] = val


    # run tests
    report = []
    for test in tests: # test+'.test'+specific_test
      if len(specific_tests) > 0: 
        test_names = ['hgsrun_test.'+test+'Test.test'+s_t for s_t in specific_tests]
        s = unittest.TestLoader().loadTestsFromNames(test_names)
      else: s = unittest.TestLoader().loadTestsFromTestCase(test_classes[test])
      report.append(unittest.TextTestRunner(verbosity=2).run(s))
      
    # print summary
    runs = 0; errs = 0; fails = 0
    for name,test in zip(tests,report):
      #print test, dir(test)
      runs += test.testsRun
      e = len(test.errors)
      errs += e
      f = len(test.failures)
      fails += f
      if e+ f != 0: print("\nErrors in '{:s}' Tests: {:s}".format(name,str(test)))
    if errs + fails == 0:
      print("\n   ***   All {:d} Test(s) successfull!!!   ***   \n".format(runs))
    else:
      print("\n   ###     Test Summary:      ###   \n" + 
            "   ###     Ran {:2d} Test(s)     ###   \n".format(runs) + 
            "   ###      {:2d} Failure(s)     ###   \n".format(fails)+ 
            "   ###      {:2d} Error(s)       ###   \n".format(errs))
    