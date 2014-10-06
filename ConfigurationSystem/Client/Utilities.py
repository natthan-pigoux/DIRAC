########################################################################
# $HeadURL$
# Author : Andrei Tsaregorodtsev
########################################################################
"""
  Utilities for managing DIRAC configuration:
  
  getCEsFromCS
  getUnusedGridCEs
  getUnusedGridSEs 
  getSiteUpdates
  getSEUpdates
"""
__RCSID__ = "$Id$"

import re
import types
from DIRAC import gConfig, gLogger, S_OK
from DIRAC.Core.Utilities import List
from DIRAC.Core.Utilities.Grid import getBdiiCEInfo, getBdiiSEInfo, ldapService
from DIRAC.Core.Utilities.SitesDIRACGOCDBmapping import getDIRACSiteName, getDIRACSesForSRM
from DIRAC.ConfigurationSystem.Client.Helpers.Path import cfgPath
from DIRAC.Core.Utilities.Pfn import pfnparse

def getCEsFromCS():
  """ Get all the CEs defined in the CS
  """
  
  knownCEs = []
  result = gConfig.getSections( '/Resources/Sites' )
  if not result['OK']:
    return result
  grids = result['Value']

  for grid in grids:
    result = gConfig.getSections( '/Resources/Sites/%s' % grid )
    if not result['OK']:
      return result
    sites = result['Value']

    for site in sites:
      opt = gConfig.getOptionsDict( '/Resources/Sites/%s/%s' % ( grid, site ) )['Value']
      ces = List.fromChar( opt.get( 'CE', '' ) )
      knownCEs += ces
      
  return S_OK( knownCEs )

def getSEsFromCS( protocol = 'srm' ):
  """ Get all the SEs defined in the CS
  """
  knownSEs = {}
  result = gConfig.getSections( '/Resources/StorageElements' )
  if not result['OK']:
    return result
  ses = result['Value']
  for se in ses:
    seSection = '/Resources/StorageElements/%s' % se 
    result = gConfig.getSections( seSection )
    if not result['OK']:
      continue
    accesses = result['Value']
    for access in accesses:
      seProtocol = gConfig.getValue( cfgPath( seSection, access, 'Protocol' ), '' )
      if seProtocol.lower() == protocol.lower() or protocol == 'any':
        host = gConfig.getValue( cfgPath( seSection, access, 'Host' ), '' )
        knownSEs.setdefault( host, [] )
        knownSEs[host].append( se )
      else:
        continue  
      
  return S_OK( knownSEs )    

def getUnusedGridCEs( vo, bdiiInfo = None, ceBlackList = None ):
  """ Get all the CEs available for a given VO and having queues in Production state
  """
  
  result = getCEsFromCS()
  if not result['OK']:
    return result
  knownCEs = result['Value']
  knownCEs = set( knownCEs )
  if ceBlackList is not None:
    knownCEs = knownCEs.union( set( ceBlackList ) )
  
  ceBdiiDict = bdiiInfo
  if bdiiInfo is None:
    result = getBdiiCEInfo( vo )
    if not result['OK']:
      return result
    ceBdiiDict = result['Value']
    
  siteDict = {}
  for site in ceBdiiDict:
    siteCEs = set( ceBdiiDict[site]['CEs'].keys() )
    newCEs = siteCEs - knownCEs
    if not newCEs:
      continue

    ceFullDict = {} 
    for ce in newCEs:
      ceDict = {}
      ceInfo = ceBdiiDict[site]['CEs'][ce]
      ceType = 'Unknown'
      ceDict['Queues'] = []
      for queue in ceInfo['Queues']:
        queueStatus = ceInfo['Queues'][queue].get( 'GlueCEStateStatus', 'UnknownStatus' )
        if 'production' in queueStatus.lower():
          ceType = ceInfo['Queues'][queue].get( 'GlueCEImplementationName', '' )
          ceDict['Queues'].append( queue )
      if not ceDict['Queues']:
        continue  
      
      ceDict['CEType'] = ceType               
      ceDict['GOCSite'] = site
      ceDict['CEID'] = ce 
      systemName = ceInfo.get( 'GlueHostOperatingSystemName', 'Unknown' )
      systemVersion = ceInfo.get( 'GlueHostOperatingSystemVersion', 'Unknown' )
      systemRelease = ceInfo.get( 'GlueHostOperatingSystemRelease', 'Unknown' )
      ceDict['System'] = ( systemName, systemVersion, systemRelease )
      
      ceFullDict[ce] = ceDict
      
    siteDict[site] = ceFullDict  
      
  result = S_OK( siteDict )        
  result['BdiiInfo'] = ceBdiiDict
  return result 
       
def getSiteUpdates( vo, bdiiInfo = None, log = None ):
  """ Get all the necessary updates for the already defined sites and CEs
  """  
  
  def addToChangeSet( entry, changeSet ):
    _section, _option, value, new_value = entry
    if new_value and new_value != value:
      changeSet.add( entry )

  if log is None:
    log = gLogger  
    
  ceBdiiDict = bdiiInfo
  if bdiiInfo is None:
    result = getBdiiCEInfo( vo )    
    if not result['OK']:
      return result
    ceBdiiDict = result['Value']

  changeSet = set()
  gConfig.forceRefresh()

  for site in ceBdiiDict:
    result = getDIRACSiteName( site )
    if not result['OK']:
      continue
    siteNames = result['Value']
    for siteName in siteNames:
      siteSection = cfgPath( '/Resources', 'Sites', siteName.split('.')[0], siteName )
      result = gConfig.getOptionsDict( siteSection )
      if not result['OK']:
        continue
      siteDict = result['Value']
      # Current CS values
      coor = siteDict.get( 'Coordinates', 'Unknown' )
      mail = siteDict.get( 'Mail', 'Unknown' ).replace( ' ','' )
      description = siteDict.get( 'Description', 'Unknown' )
  
      longitude = ceBdiiDict[site].get( 'GlueSiteLongitude', '' ).strip()
      latitude = ceBdiiDict[site].get( 'GlueSiteLatitude', '' ).strip()
  
      # Current BDII value
      newcoor = ''
      if longitude and latitude:
        newcoor = "%s:%s" % ( longitude, latitude )
      newmail = ceBdiiDict[site].get( 'GlueSiteSysAdminContact', '' ).replace( 'mailto:', '' ).strip()
      newdescription = ceBdiiDict[site].get( 'GlueSiteDescription', '' ).strip()
      # Adding site data to the changes list
      addToChangeSet( ( siteSection, 'Coordinates', coor, newcoor ), changeSet )
      addToChangeSet( ( siteSection, 'Mail', mail, newmail ), changeSet )
      addToChangeSet( ( siteSection, 'Description', description, newdescription ), changeSet )
  
      ces = gConfig.getValue( cfgPath( siteSection, 'CE' ), [] )
      for ce in ces:
        ceSection = cfgPath( siteSection, 'CEs', ce )
        ceDict = {}
        result = gConfig.getOptionsDict( ceSection )
        if result['OK']:
          ceDict = result['Value']
        else:
          if ceBdiiDict[site]['CEs'].get( ce, None ):
            log.notice( "Adding new CE %s to site %s/%s" % (ce, siteName, site) )
        ceInfo = ceBdiiDict[site]['CEs'].get( ce, None )
        if ceInfo is None:
          ceType = ceDict.get( 'CEType', '')
          continue
  
        # Current CS CE info
        arch = ceDict.get( 'architecture', 'Unknown' )
        OS = ceDict.get( 'OS', 'Unknown' )
        si00 = ceDict.get( 'SI00', 'Unknown' )
        ceType = ceDict.get( 'CEType', 'Unknown' )
        ram = ceDict.get( 'HostRAM', 'Unknown' )
        submissionMode = ceDict.get( 'SubmissionMode', 'Unknown' )
  
        # Current BDII CE info
        newarch = ceBdiiDict[site]['CEs'][ce].get( 'GlueHostArchitecturePlatformType', '' ).strip()
        systemName = ceInfo.get( 'GlueHostOperatingSystemName', '' ).strip()
        systemVersion = ceInfo.get( 'GlueHostOperatingSystemVersion', '' ).strip()
        systemRelease = ceInfo.get( 'GlueHostOperatingSystemRelease', '' ).strip()
        newOS = ''
        if systemName and systemVersion and systemRelease:
          newOS = '_'.join( ( systemName, systemVersion, systemRelease ) )
        newsi00 = ceInfo.get( 'GlueHostBenchmarkSI00', '' ).strip()
        newCEType = 'Unknown'
        for queue in ceInfo['Queues']:
          queueDict = ceInfo['Queues'][queue]
          newCEType = queueDict.get( 'GlueCEImplementationName', '' ).strip()
          if newCEType:
            break
        if newCEType=='ARC-CE':
          newCEType = 'ARC'
        if newCEType in ['ARC','CREAM']:
          newSubmissionMode = "Direct" 
        newRAM = ceInfo.get( 'GlueHostMainMemoryRAMSize', '' ).strip()
  
        # Adding CE data to the change list
        addToChangeSet( ( ceSection, 'architecture', arch, newarch ), changeSet )
        addToChangeSet( ( ceSection, 'OS', OS, newOS ), changeSet )
        addToChangeSet( ( ceSection, 'SI00', si00, newsi00 ), changeSet )
        addToChangeSet( ( ceSection, 'CEType', ceType, newCEType ), changeSet )
        addToChangeSet( ( ceSection, 'HostRAM', ram, newRAM ), changeSet )
        if submissionMode == "Unknown":
          addToChangeSet( ( ceSection, 'SubmissionMode', submissionMode, newSubmissionMode ), changeSet )
  
        queues = ceInfo['Queues'].keys()
        for queue in queues:
          queueSection = cfgPath( ceSection, 'Queues', queue )
          queueDict = {}
          result = gConfig.getOptionsDict( queueSection )
          if result['OK']:
            queueDict = result['Value']
          else:
            log.notice( "Adding new queue %s to CE %s" % (queue, ce) )
          queueInfo = ceInfo['Queues'][queue]
          queueStatus = queueInfo['GlueCEStateStatus']
          if queueStatus.lower() != "production":
            continue
  
          # Current CS queue info
          maxCPUTime = queueDict.get( 'maxCPUTime', 'Unknown' )
          si00 = queueDict.get( 'SI00', 'Unknown' )
          maxTotalJobs = queueDict.get( 'MaxTotalJobs', 'Unknown' )
  
          # Current BDII queue info
          newMaxCPUTime = queueInfo.get( 'GlueCEPolicyMaxCPUTime', '' )
          newSI00 = ''
          caps = queueInfo['GlueCECapability']
          if type( caps ) == type( '' ):
            caps = [caps]
          for cap in caps:
            if 'CPUScalingReferenceSI00' in cap:
              newSI00 = cap.split( '=' )[-1]
  
          # Adding queue info to the CS
          addToChangeSet( ( queueSection, 'maxCPUTime', maxCPUTime, newMaxCPUTime ), changeSet )
          addToChangeSet( ( queueSection, 'SI00', si00, newSI00 ), changeSet )
          if maxTotalJobs == "Unknown":
            newTotalJobs =  min( 1000, int( int( queueInfo.get( 'GlueCEInfoTotalCPUs', 0 ) )/2 ) )
            newWaitingJobs =  max( 2, int( newTotalJobs * 0.1 ) )
            newTotalJobs = str( newTotalJobs )
            newWaitingJobs = str( newWaitingJobs )
            addToChangeSet( ( queueSection, 'MaxTotalJobs', '', newTotalJobs ), changeSet )
            addToChangeSet( ( queueSection, 'MaxWaitingJobs', '', newWaitingJobs ), changeSet )
            
          # Updating eligible VO list
          VOs = set()
          if queueDict.get( 'VO', '' ):
            VOs = set( [ q.strip() for q in queueDict.get( 'VO', '' ).split( ',' ) if q ] )
          if not vo in VOs:   
            newVOs = ','.join( VOs.add( vo ) )
            addToChangeSet( ( queueSection, 'VO', '', newVOs ), changeSet ) 
    
  return S_OK( changeSet )  

def getUnusedGridSEs( vo, bdiiInfo = None, seBlackList = None ):
  """ Get all the SEs available for a given VO 
  """
  seBdiiDict = bdiiInfo
  if bdiiInfo is None:
    result = getBdiiSEInfo( vo )
    if not result['OK']:
      return result
    seBdiiDict = result['Value']

  result = getSEsFromCS()
  if not result['OK']:
    return result
  knownSEs = result['Value']   
    
  siteDict = {}
  for site in seBdiiDict:
    for gridSE in seBdiiDict[site]['SEs']:
      seDict = seBdiiDict[site]['SEs'][gridSE]
      
      #if "lhcb" in seDict['GlueSAName']: 
      #  print '+'*80
      #  print gridSE
      #  for k,v in seDict.items():
      #    print k,'\t',v 
        
    
      if not gridSE in knownSEs:
        siteDict.setdefault( site, {} )
        if type( seDict['GlueSAAccessControlBaseRule'] ) == types.ListType:
          voList = [ re.sub( '^VO:', '', s ) for s in seDict['GlueSAAccessControlBaseRule'] ]
        else:
          voList = [ re.sub( '^VO:', '', seDict['GlueSAAccessControlBaseRule'] ) ]  
        siteDict[site][gridSE] = { 'GridSite': seDict['GlueSiteUniqueID'],
                                   'BackendType': seDict['GlueSEImplementationName'],
                                   'Description': seDict.get( 'GlueSEName', '-' ),
                                   'VOs': voList
                                 } 
    
  result = S_OK( siteDict )
  result['BdiiInfo'] = seBdiiDict
  return result
  
def getUnusedSRMs( vo ):  
  
  result = ldapService( serviceType = 'SRM', vo = vo )
  if not result['OK']:
    return result
  srmBdiiDict = result['Value']

  siteSRMDict = {}
  for srm in srmBdiiDict:
    
    endPoint = srm.get( 'GlueServiceEndpoint', '')
    srmHost = ''
    if endPoint:
      result = pfnparse( endPoint )
      if not result['OK']:
        continue
      srmHost = result['Value']['Host']
    if not srmHost:
      continue  
    
    result = getDIRACSesForSRM( srmHost )
    if not result['OK']:
      return result
    diracSEs = result['Value']
    if not diracSEs:
      # This is a new SRM service
      site = srm.get( 'GlueForeignKey', '' ).replace( 'GlueSiteUniqueID=', '' )     
      siteSRMDict.setdefault( site, {} )
      siteSRMDict[site][srmHost] = srm
      
  result = getBdiiSEInfo( vo )
  if not result['OK']:
    return result
  seBdiiDict = result['Value']
 
  srmSeDict = {}  
  for site in siteSRMDict:
    srms = siteSRMDict[site].keys()
    for srm in srms:
      if seBdiiDict.get( site, {} ).get( 'SEs', {} ).get( srm, {} ):
        srmSeDict.setdefault( site, {} )
        srmSeDict[site].setdefault( srm, {} )
        srmSeDict[site][srm]['SRM'] = siteSRMDict[site][srm]
        srmSeDict[site][srm]['SE'] = seBdiiDict[site]['SEs'][srm]    
      
  return S_OK( srmSeDict ) 
  
  