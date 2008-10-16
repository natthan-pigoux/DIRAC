#!/usr/bin/env python
########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/Interfaces/scripts/dirac-admin-select-requests.py,v 1.1 2008/10/16 09:21:28 paterson Exp $
# File :   dirac-admin-select-requests
# Author : Stuart Paterson
########################################################################
__RCSID__   = "$Id: dirac-admin-select-requests.py,v 1.1 2008/10/16 09:21:28 paterson Exp $"
__VERSION__ = "$Revision: 1.1 $"
import sys,string
from DIRACEnvironment import DIRAC
from DIRAC.Core.Base import Script


Script.registerSwitch( "", "JobID=", "WMS JobID for the request (if applicable)" )
Script.registerSwitch( "", "RequestID=", "ID assigned during submission of the request" )
Script.registerSwitch( "", "RequestName=", "XML request file name" )
Script.registerSwitch( "", "RequestType=", "Type of the request e.g. 'transfer'" )
Script.registerSwitch( "", "Status=", "Request status" )
Script.registerSwitch( "", "Operation=", "Request operation e.g. 'replicateAndRegister'" )
Script.registerSwitch( "", "RequestStart=", "First request to consider (start from 0 by default)" )
Script.registerSwitch( "", "Limit=", "Selection limit (default 100)")
Script.registerSwitch( "", "OwnerDN=", "DN of owner (in double quotes)")
Script.registerSwitch( "", "OwnerGroup=", "Owner group")
Script.parseCommandLine( ignoreErrors = True )

from DIRAC.Interfaces.API.DiracAdmin import DiracAdmin

args = Script.getPositionalArgs()

#Default values
jobID=None
requestID=None
requestName=None
requestType=None
status=None
operation=None
ownerDN=None
ownerGroup=None
requestStart=0
limit=100

def usage():
  print 'Usage: %s [Try -h,--help for more information]' %(Script.scriptName)
  DIRAC.exit(2)

if args:
  usage()

exitCode = 0

for switch in Script.getUnprocessedSwitches():
  if switch[0].lower()=="jobid":
    jobID=switch[1]
  elif switch[0].lower()=="requestid":
    requestID=switch[1]
  elif switch[0].lower()=="requestname":
    requestName=switch[1]
  elif switch[0].lower()=="requesttype":
    requestType=switch[1]
  elif switch[0].lower()=="status":
    status=switch[1]
  elif switch[0].lower()=="operation":
    operation=switch[1]
  elif switch[0].lower()=="requeststart":
    requestStart=switch[1]
  elif switch[0].lower()=="limit":
    limit=switch[1]
  elif switch[0].lower()=="ownerDN":
    ownerDN=switch[1]
  elif switch[0].lower()=="ownerGroup":
    ownerGroup=switch[1]

conditions = {'RequestID':requestID,'RequestName':requestName,'JobID':jobID,'OwnerDN':ownerDN,
              'OwnerGroup':ownerGroup,'RequestType':requestType,'Status':status,'Operation':operation}

diracAdmin = DiracAdmin()
result = diracAdmin.selectRequests(JobID=jobID,RequestID=requestID,RequestName=requestName,RequestType=requestType,Status=status,Operation=operation,OwnerDN=ownerDN,OwnerGroup=ownerGroup,RequestStart=requestStart,Limit=limit,printOutput=True)
if not result['OK']:
  print 'ERROR %s' %result['Message']
  exitCode = 2

DIRAC.exit(exitCode)