#! /usr/bin/env python
########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/Interfaces/scripts/dirac-admin-set-site-protocols.py,v 1.1 2008/10/16 09:21:28 paterson Exp $
# File :   dirac-admin-set-site-protocols
# Author : Stuart Paterson
########################################################################
__RCSID__   = "$Id: dirac-admin-set-site-protocols.py,v 1.1 2008/10/16 09:21:28 paterson Exp $"
__VERSION__ = "$Revision: 1.1 $"
from DIRACEnvironment import DIRAC
from DIRAC.Core.Base import Script

Script.registerSwitch( "", "Site=", "Site for which protocols are to be set (protocols are standard arguments)" )
Script.parseCommandLine( ignoreErrors = True )

site = None
for switch in Script.getUnprocessedSwitches():
  if switch[0].lower()=="site":
    site = switch[1]

args = Script.getPositionalArgs()

from DIRAC.Interfaces.API.DiracAdmin                         import DiracAdmin

def usage():
  print 'Usage: %s <PROTOCOL> [<PROTOCOL>] --Site=<DIRAC SITE NAME> [Try -h,--help for more information]' %(Script.scriptName)
  DIRAC.exit(2)

if not site or not args:
  usage()

diracAdmin = DiracAdmin()
exitCode = 0
result = diracAdmin.setSiteProtocols(site,args,printOutput=True)
if not result['OK']:
  print 'ERROR: %s' %result['Message']
  exitCode=2

DIRAC.exit(exitCode)
