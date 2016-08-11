'''
Created on Jul 31, 2016

A Python class (Grok) that facilitates the configuration of an HGS simulation via grok and a child class
that also handles folder setup (based on template) and execution of HGS.

@author: Andre R. Erler, GPL v3
'''

# external imports
import numpy as np
import os, shutil
import subprocess # launching external programs
# internal imports
from input_list import generateInputFilelist, resolveInterval
from geodata.misc import ArgumentError


## a class to handle Grok for HGS simulations
class Grok(object):
  '''
    A class that loads a grok configuration file into memory, provides functions for editing,
    saving the file, and running Grok.
  '''
  rundir = None # folder where the experiment is set up and executed
  project = None # a project designator used for file names
  input_mode = None # type of simulation (forcing data): stead-state, periodic, transient
  input_interval = None # update interval for climate forcing
  runtime = None # run time for the simulations (in seconds)
  length = None # run time in multiples of the interval length
  _lines = None # list of lines in file
  _sourcefile = None # file that the configuration was read from
  _targetfile = None # file that the configuration is written to
  
  def __init__(self, rundir=None, project=None, runtime=None, length=None, input_mode=None, input_interval=None):
    ''' initialize a Grok configuration object with some settings '''
    if not os.path.isdir(rundir): raise IOError(rundir)
    # determine end time in seconds (begin == 0) or number of intervals (length)
    length, runtime = resolveInterval(length=length, end_time=runtime, interval=input_interval)
    # assign class variables
    self.rundir = rundir
    self.project = project
    self.runtime = runtime
    self.input_mode= input_mode
    self.input_interval = input_interval
  
  def read(self, filename=None, folder=None):
    ''' Read a grok configuration file into memory (or a template to start from). '''    
    filename = filename or '{:s}.grok'.format(self.project) # or default name
    filename = '{:s}/{:s}'.format(folder or self.rundir, filename) # prepend folder
    if not os.path.isfile(filename): raise IOError(filename)
    self._sourcefile = filename # use  different file as template
    # read source file
    with open(filename, 'r') as src: # with-environment should take care of closing the file
      self._lines = src.readlines() # read all lines into list
    # strip white spaces and convert to lower case
    self._lines = [line.strip().lower() for line in self._lines]
    # apply time setting
    if self.runtime: self.setRuntime(self.runtime)
      
  def write(self, filename=None):
    ''' Write the grok configuration to a file in run dir. '''    
    filename = filename or '{:s}.grok'.format(self.project) # or default name    
    filename = '{:s}/{:s}'.format(self.rundir,filename) # prepend run dir
    self._targetfile = filename # use  different file as template
    # move existing file to backup
    if os.path.isfile(filename): shutil.move(filename, '{:s}.backup'.format(filename))
    # write configuration to file
    with open(filename, 'w') as tgt: # with-environment should take care of closing the file
      tgt.write('\n'.join(self._lines)+'\n')
      # N.B.: this is necessary, because our list does not have newlines and Python does not add them...

  def setParam(self, param, value, formatter=None, after=None, start=0):
    ''' edit a single parameter, based on the assumption that the parameter value follows in the 
        line below the one where the parameter name appears (case in-sensitive); format is a
        regular format string used to write the value '''
    if formatter: value = formatter.format(value) # apply appropriate formatting
    else: value = str(value)
    start = self._lines.index(after, start) if after else start # search offset for primary paramerter
    self._lines[self._lines.index(param.lower())+1] = value # replace value in list of lines

  def getParam(self, param, dtype=None, after=None, start=0):
    ''' read a single parameter, based on the assumption that the parameter value follows in the 
        line below the one where the parameter name appears (case in-sensitive); dtype is a 
        numpy data type to which the value string is cast '''
    start = self._lines.index(after, start) if after else start # search offset for primary paramerter
    value = self._lines[self._lines.index(param.lower(), start)+1]
    if isinstance(dtype,basestring): value = getattr(np,dtype)(value) # convert to given numpy dtype
    elif dtype: value = dtype(value) # try conversion this way...
    return value

  def replaceParam(self, old, new, formatter=None, after=None, start=0):
    ''' repalce a parameter value with a new value '''
    if formatter: 
      new = formatter.format(new) # apply appropriate formatting
      old = formatter.format(old) # apply appropriate formatting
    else:
      new = str(new); old = str(old)
    start = self._lines.index(after, start) if after else start # search offset for primary paramerter
    self._lines[self._lines.index(old.lower(), start)] = new # replace value in list of lines
    
  def editParams(self, **params):
    ''' edit a bunch of parameters, which are defined as key/values pairs using self.editParam;
        note that there is no validation and 'format' is only supported for single edits '''
    for param,value in params.iteritems():
      self.editParam(param, value, format=None)
      
  def setRuntime(self, time):
    ''' set the run time of the simulations (model time in seconds) '''
    self.runtime = time
    if self._lines:
      self.setParam('output times', time, formatter='{:.3e}', )
  
  def setInputMode(self, mode=None, interval=None):
    ''' set the type of the simulation: mean/steady-state, climatology/periodic, time-series/transient '''
    mode = mode.lower()
    if mode in ('mean','steady','steady-state') or mode[-5:] == '-mean': mode = 'steady-state'
    elif mode[:4] in ('clim','peri','climatology','periodic'): mode = 'periodic'
    elif mode in ('time-series','timeseries','trans','transient'): mode = 'transient'
    self.mode = mode
    interval = interval.lower()
    if interval[:5].lower() == 'month': interval = 'monthly'
    elif interval[:3].lower() == 'day': interval = 'daily'
    else: raise NotImplementedError(interval)
    self.interval = interval
  
  def generateInputLists(self, input_mode='PET', input_prefix=None, input_folder='../climate_forcing', 
                         input_vars=None, lvalidate=True, lcenter=True, l365=True, lFortran=True):
    ''' generate and validate lists of input files and write to appropriate files '''
    # generate default input vars
    if input_vars is None:
      if input_mode.upper() == 'PET': # liquid water + snowmelt & PET as input
        input_vars = dict(precip=('rain','liqwatflx'),  
                          pet=('potential evapotranspiration','pet'))
      elif input_mode.upper() == 'NET': # liquid water + snowmelt - ET as input
        input_vars = dict(precip=('rain','waterflx'),)
      else:
        raise ArgumentError("Invalid input_mode or input_vars missing:\n {}, {}".format(input_mode,input_vars))
    # iterate over variables and generate corresponding input lists
    for varname,val in input_vars.iteritems():
      vartype,wrfvar = val
      filename = '{}.inc'.format(varname)
      self.setParam('time raster table', 'include {}'.format(filename), after=vartype)
      input_pattern = '{}_{}_iTime_{{IDX}}.asc'.format(input_prefix, wrfvar) # IDX will be substituted
      # write file list
      generateInputFilelist(filename=filename, folder=self.rundir, input_folder=input_folder, 
                            input_pattern=input_pattern, lcenter=lcenter, 
                            lvalidate=lvalidate, units='seconds', l365=l365, lFortran=lFortran, 
                            interval=self.input_interval, end_time=self.runtime, mode=self.input_mode)

  def runGrok(self, executable='grok_premium.x', logfile='log.grok'):
    ''' run the Grok executable in the current directory '''
    os.chdir(self.rundir) # go into run Grok/HGS folder
    with open(logfile, 'a') as lf: # output and error log
      # run Grok
      subprocess.call([executable], stdout=lf, stderr=lf)
      # parse log file for errors
      lf.seek(2,2) # i.e. -3, third line from the end
      ec = ( lf.readline().strip() == '---- Normal exit ----' )
    if ec: 
      return 0
    else: 
      print("WARNING: Grok failed; inspect log-file: {}".format(logfile))
      return 1     
      