import concurrent.futures, subprocess
from .newDiskOperations import getSasHosts, getSEScontrollers, sortStorageDevices, getChassisInfo, getParents, getSerialNumber
from .raidOperations import getAllRaidInfo
from .slotlookup import oldjbodSASMapper
from pprint import pprint
from .newDiskOperations import getSMART
from pathlib import Path
import platform, json

class storage_info_sim(object):
    def __init__(self):
        self.chassis = {'oimsdaiofmsiodf':{'revision':'1',
                                           'logicalid':'logicalid1',
                                           'numslots':'5',
                                           'model':'H4102-J',
                                           'iomodules':{'sg1':{'disks':[]},
                                                        'sg104':{'disks':[]}}},
                        'imdf8ds8fs78d':{'revision':'1',
                                        'logicalid':'logicalid1',
                                        'numslots':'5',
                                        'model':'H4102-J',
                                        'iomodules':{'sg2':{'disks':[]},
                                                      'sg204':{'disks':[]}}}}
        with open('chassis') as f:
            self.chassis =  json.load(f)
    def updateData(self):
        print("I am pretending to update the data.")

class storage_info(object):
    def __init__(self, smart=False,debug=False,timeout=60):
        self.timeout = timeout
        self.debug = debug
        self.smart = smart
        self.PARALELL = 1
        self.hostname = platform.node()
        self.sasPortList = getSasHosts()  # this is a list of the fullpath in /sys for each SAS port on the host. These are the ports that connect SAS cables to JBOD enclosures.
        self.sesControllerMap = getSEScontrollers()  # This is a dictionary that maps the fullpath in /sys for each SCSI Enclosure Services (SES) controller to its generic SCSI name (ie.. sg1)
        self.ses2SASPortMap = {}
        self.mapSASPort2SES()
        self.iomoduleChassisMap = {}
        self.sasmaps = {enclosure: oldjbodSASMapper(iomodule=enclosure,timeout=self.timeout) for enclosure in self.ses2SASPortMap}
        self.raidInfoMapper = getAllRaidInfo()
        #  The idea is to use the fullpaths stored in diskview for each drive to figure out which drive is viewed through which SES controller. Both the controllers path and the disks path have a common root in the list of  self.sasPortList
        self.diskview = sortStorageDevices(diskview=True)
        self.addParents()
        self.lookupRAIDroles()
        self.chassis = {}
        self.createPhysicalStructure()
        self.quickSortDisks()
        if len(self.chassis) > 0:
            self.getAllDrivesLEDstatus()
            if self.smart: self.addSMARTdata()

    def dumpToJSON(self,dumpType=None,outputFile=None):
        if outputFile is None:
            outputFile = str(dumpType)+'storage_info'
        if dumpType is None:
            print("you must specific a dump type from: ['physical','logical','diskview]")
        elif dumpType == 'physical':
            for chassis in self.chassis:
                for iomod in self.chassis[chassis]['iomodules']:
                    for disk in self.chassis[chassis]['iomodules'][iomod]['disks']:
                        disk.pop('fullpath')
            with open(outputFile,'w') as f:
                json.dump(self.chassis,f)
        elif dumpType == 'logical':
            pass
        elif dumpType == 'diskview':
            with open(outputFile,'w') as f:
                json.dump(self.diskview,f)

    def loadFromJSON(self,dumpType=None,inputFile=None):
        inputFile = str(dumpType)+'storage_info'
        if dumpType is None:
            print("you must specific a dump type from: ['physical','logical','diskview]")
        elif dumpType == 'physical':
            with open(inputFile,'w') as f:
                self.chassis = json.load(f)
        elif dumpType == 'logical':
            pass
        elif dumpType == 'diskview':
            with open(inputFile,'w') as f:
                self.diskview = json.load(f)

    def generateLogicalTree(self):
        self.logicalTree = {}
        for array in self.raidInfoMapper:
            self.logicalTree[array] = {}
            self.logicalTree[array] = self.raidInfoMapper[array]

    def updateData(self):
        self.sasPortList = getSasHosts()
        self.sesControllerMap = getSEScontrollers()
        self.ses2SASPortMap = {}
        self.mapSASPort2SES()
        self.iomoduleChassisMap = {}
        self.sasmaps = {enclosure: oldjbodSASMapper(iomodule=enclosure) for enclosure in self.ses2SASPortMap}
        self.raidInfoMapper = getAllRaidInfo()
        self.diskview = sortStorageDevices(diskview=True)
        self.addParents()
        self.lookupRAIDroles()
        if self.smart: self.addSMARTdata()
        self.chassis = {}
        self.createPhysicalStructure()
        self.quickSortDisks()
        self.getAllDrivesLEDstatus()

    def addSMARTdata(self):
        siblingsMap = {}
        actionlist = []
        for item in self.diskview:
            if self.diskview[item]['devtype'] != 'sd':
                continue
            else:
                mpathdmname = self.diskview[item]['mpathdmname']
                if mpathdmname is None:
                    actionlist.append(item)
                    continue
                elif mpathdmname not in siblingsMap:
                    siblingsMap[mpathdmname] = [item]
                    actionlist.append(item)
                elif mpathdmname in siblingsMap:
                    siblingsMap[mpathdmname].append(item)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.PARALELL) as executor:
            future_run_loops = {executor.submit(getSMART, serial=getSerialNumber(scsi_device=name), sdname=name): name for name in actionlist}
            for future in concurrent.futures.as_completed(future_run_loops):
                if future.result() is not None and type(future.result()) == dict:
                    targetName = str(future_run_loops[future])
                    mpathdmname = self.diskview[targetName]['mpathdmname']
                    if mpathdmname is not None:
                        for sibling in siblingsMap[mpathdmname]:
                            self.diskview[sibling].update(future.result())
                    else:
                        self.diskview[targetName].update(future.result())
                else:
                    print("Failed to get smart attributes for",str(future))


    def getAllDrivesLEDstatus(self):
        for chassis in self.chassis:
            iomodule = list(self.chassis[chassis]['iomodules'].keys())[0]
            outputQueue = []
            command = ['sg_ses','-p','es','/dev/'+iomodule]
            outputQueue.append(command)
            output = subprocess.run(command,stdout=subprocess.PIPE).stdout.decode("UTF-8").lower().splitlines()
            outputQueue.append(output)
            sectionActive = False
            idx = None
            properties = [] #list of property dictionaries by index.
            for line in output:
                if sectionActive:
                    if 'element type:' in line and sectionActive:
                        break
                    elif 'element' in line and 'descriptor' in line:
                        idx = int(line.split()[1].strip())
                        properties.append({})
                    elif idx is not None:
                        linedata = line.split(',')
                        for item in linedata:
                            item = item.strip()
                            if '=' in item:
                                key = item.split('=')[0]
                                value = item.split('=')[1]
                                properties[idx][key] = value
                                for module in self.chassis[chassis]['iomodules']:
                                    if 'fault r' in key:
                                        key = 'fault'
                                        self.chassis[chassis]['iomodules'][module]['disks'][idx][key] = value
                                    elif key == 'ident':
                                        self.chassis[chassis]['iomodules'][module]['disks'][idx][key] = value
                                properties[idx][key] = value # for later in case we want to extract other properties associated with sg_ses -p es /dev/sg*
                elif 'Element type: Array device slot'.lower() in line:
                    sectionActive = True
                    continue
            #self.chassis[chassis][''] = properties

    def getEnergizedLEDs(self,invert=False,show=False):
        print("\n--------------------------------------------------------------------------------------------------")
        LEDstatus = {}
        if invert:
            selectState = '0'
        else:
            selectState = '1'
        self.getAllDrivesLEDstatus()
        for chassis in self.chassis:
            if show:
                print("LED status in chassis with Serial Number",chassis,"and Logical ID",self.chassis[chassis]['logicalid'])
            iomodule1 = list(self.chassis[chassis]['iomodules'].keys())[0]
            try:
                iomodule2 = list(self.chassis[chassis]['iomodules'].keys())[1]
            except KeyError:
                iomodule2 = iomodule1
            for disk in self.chassis[chassis]['iomodules'][iomodule1]['disks']:
                translation = {'1':'On','0':'Off'}
                if disk['ident'] == selectState or disk['fault'] == selectState:
                    identLight = translation[disk['ident']]
                    faultLight = translation[disk['fault']]
                    index = disk['index']
                    name = disk['name']
                    sibling = self.chassis[chassis]['iomodules'][iomodule2]['disks'][int(index)]['name']
                    if show:
                        print("\nIndex",index,"Kernel Name(s): ",name,"/",sibling,"has its locate LED",identLight,"and its Fault LED",faultLight+".")
                    LEDstatus[name] = {'fault':disk['fault'],'ident':disk['ident']}
                    LEDstatus[sibling] = {'fault': disk['fault'], 'ident': disk['ident']}
        print("\n--------------------------------------------------------------------------------------------------\n")
        return LEDstatus

    def selectItemUsingMenus(self,selectType,filters={}):
        types = ['sdNotRAID','sdRAID','mdparent','mpath','raidpart','energizedLEDs','deenergizedLEDs']
        self.updateData()
        if selectType not in types:
            print("selectItemsUsingMenus has been called with an invalid selectType")
            return (False,'not a valid selection target.')
        choices = []
        if selectType == types[0]:
            for child in self.diskview:
                if self.diskview[child]['devtype'] == 'sd' and self.diskview[child]['mdparent'] is None:
                    choices.append(child)
            if len(choices) == 0:
                return (False,'There are no drive candidates available for completeReplacement.')
        elif selectType == types[1]: #actions for when a list of disks in a RAID array are requested.
            existing = []
            if 'mdparent' in filters:
                mdparents = [filters['mdparent']]
            else:
                mdparents = list(self.raidInfoMapper.keys())
            for child in self.diskview:
                if self.diskview[child]['devtype'] == 'sd' and self.diskview[child]['mdparent'] in mdparents:
                    if self.diskview[child]['dmraidpart'] not in existing:
                        choices.append(child)
                        existing.append(self.diskview[child]['dmraidpart'])
            pprint(existing)
            pprint(choices)
            if len(choices) == 0:
                return (False,'There are no disks that are currently assigned to RAID arrays: '+str(mdparents))
        elif selectType == types[2]:
            choices = list(self.raidInfoMapper.keys())
            if len(choices) == 0:
                return (False,'There are currently no software RAID arrays in the system.')
        elif selectType == types[3]:
            print("mpath not yet implemented")
            return (False,'Not yet implemented.')
        elif selectType == types[4]:
            print("RAID part selection not yet implemented.")
            return (False,'Not yet implemented')
        elif selectType == 'energizedLEDs':
            existing = []
            choices = []
            energized = self.getEnergizedLEDs()
            for disk in energized:
                if self.diskview[disk]['mpathdmname'] not in existing and self.diskview[disk]['mpathdmname'] is not None:
                    existing.append(self.diskview[disk]['mpathdmname'])
                    choices.append(disk)
                elif self.diskview[disk]['mpathdmname'] is None:
                    choices.append(disk)

        #at this point there should be a list of choices that we can use to draw a menu for the user to select from.
        choices.append('Cancel')
        while True:
            for number, choice in enumerate(choices):
                if choice == 'Cancel' or selectType != types[1]:
                    print('\n',number,':',choice)
                else:
                    print('\n',number,':','RAID Partition',self.diskview[choice]['dmraidpart'],'Disk Kernel Name',choice,'RAID Array:',self.diskview[choice]['mdparent'],'Current Role in RAID',self.diskview[choice]['raidrole'])
            userchoice = input("Please make your selection by entering the number of your choice.\n")
            if userchoice.isdigit() and int(userchoice) < len(choices):
                print("You have chosen ",choices[int(userchoice)])
                if choices[int(userchoice)] == 'Cancel':
                    return (False,'User cancelled the operation')
                else:
                    menuchoice = choices[int(userchoice)]
                    return (True,menuchoice)
            else:
                print("That is not a valid choice.")
                continue

    def createPhysicalStructure(self):
        for item in self.sasmaps:
            enclosures = {}
            enclosures[item] = getChassisInfo(iomodule=item,timeout=self.timeout)
            if enclosures[item]['serialnumber'] not in self.chassis:
                self.chassis[enclosures[item]['serialnumber']] = {
                    'iomodules': {item: {'disks': [{} for i in range(int(enclosures[item]['numslots']))]}},
                    'logicalid': enclosures[item]['logicalid'], 'numslots': enclosures[item]['numslots'],
                    'vendor': enclosures[item]['vendor'], 'model': enclosures[item]['model'],
                    'revision': enclosures[item]['revision']}
            else:
                self.chassis[enclosures[item]['serialnumber']]['iomodules'][item] = {
                    'disks': [{} for i in range(int(enclosures[item]['numslots']))]}
        for serial in self.chassis:
            for module in self.chassis[serial]['iomodules']:
                if module not in self.iomoduleChassisMap:
                    self.iomoduleChassisMap[module] = serial

    def quickSortDisks(self):
        for item in self.diskview:
            if self.diskview[item]['devtype'] == 'sd':
                try:
                    enc = self.diskview[item]['enclosure']
                    serial = self.iomoduleChassisMap[enc]
                    index = self.diskview[item]['index']
                    name = item
                    self.diskview[item]['name'] = name
                    self.chassis[serial]['iomodules'][enc]['disks'][int(index)] = self.diskview[item]
                except KeyError as e:
                    if self.debug:
                        print("error running quicksort disks", item)
                        print(e)
                except Exception as r:
                    if self.debug:
                        print("There was an unknown error during sorting disk ", item)
                        print(r)

    def lookupRAIDroles(self):
        for item in self.diskview:
            if self.diskview[item]['devtype'] == 'sd':
                try:
                    dmraidpart = self.diskview[item]['dmraidpart']
                    if dmraidpart is None:  # handle the special case where a drive parition is added directly to raid array instead of through multipath for display purposes only.
                        partition = list(self.diskview[item]['parents'].keys())[0]
                        if item in partition:
                            dmraidpart = partition
                        else:
                            dmraidpart = None
                    mdparent = self.diskview[item]['mdparent']
                    raidmemberstatus = self.raidInfoMapper[mdparent]['components'][dmraidpart]['state']
                    self.diskview[item]['raidrole'] = raidmemberstatus
                except Exception as e:
                    if self.debug:
                        print("There was an issue getting RAID member status for ", item)
                        print(e)
                    self.diskview[item]['raidrole'] = None

    def mapSASPort2SES(self):
        for item in self.sasPortList:
            for ses in self.sesControllerMap:
                try:
                    self.sesControllerMap[ses].relative_to(item)
                    self.ses2SASPortMap[ses] = item
                except ValueError:
                    pass

    def addParents(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.PARALELL) as executor:
            future_run_loops = {executor.submit(self.dealWithParents, item=item): item for item in self.diskview}
            for future in concurrent.futures.as_completed(future_run_loops):
                pass

    def dealWithParents(self, item):
        namemap = {'md': 'mdparent', 'mpath': 'mpathdmname', 'mpathpart': 'dmraidpart', 'sasaddress': 'sasaddress'}
        expectedList = ['dmraidpart', 'dmraidpartname', 'mpathname', 'mpathdmname', 'mdparent', 'sasaddress',
                        'enclosure', 'index', 'slot']
        if self.diskview[item]['devtype'] == 'sd':
        #----------------begin processing logical device parentage.-----------------------------------------------
            try:
                result = getParents(item, storageDevices=self.diskview)
            except Exception as e:
                if self.debug:
                    print("There is a problem running getparents function on ",item)
                    print(e.args)

            self.diskview[item]['parents'] = result
            if result is not None:
                parentdata = self.walkparents(self.diskview[item]['parents'])
                for entry in parentdata:
                    if parentdata[entry] in namemap:
                        self.diskview[item][namemap[parentdata[entry]]] = entry
                try:
                    dmraidpartname = self.diskview[self.diskview[item]['dmraidpart']]['friendlyname']
                    self.diskview[item]['dmraidpartname'] = dmraidpartname
                except KeyError as k:
                    if self.debug:
                        print(k)
                        print("no dmraidpart found for ", item, "cant get dmraidpartname")
                try:
                    mpathname = self.diskview[self.diskview[item]['mpathdmname']]['friendlyname']
                    self.diskview[item]['mpathname'] = mpathname
                except KeyError as k:
                    if self.debug:
                        print(k)
                        print("no mpathdmname found for ", item, "cant get mpathname")
            #----------------end of processing logical device parentage.--------------------------------------------------------------------
            #-----------------------dealing with physical device parentage. must happen even if  there exist not "logical" parents.---------------------
            try:
                for ses in self.ses2SASPortMap:
                    try:
                        self.diskview[item]['fullpath'].relative_to(self.ses2SASPortMap[ses])
                        self.diskview[item]['enclosure'] = ses
                        break
                    except ValueError:
                        pass
            except Exception as e:
                if self.debug:
                    print("There was a problem trying to find the enclosure of a disk.")
                    print(e)
            try:
                enclosure = self.diskview[item]['enclosure']
                sasaddress = self.diskview[item]['sasaddress']
                self.diskview[item]['index'] = self.sasmaps[enclosure][sasaddress]['index']
                self.diskview[item]['slot'] = self.sasmaps[enclosure][sasaddress]['slot']

            except Exception as e:
                if self.debug:
                    print("There was a problem getting the index and slot for this device", item)
                    print(e)
            #----------end of processing physical device parentage.----------------------------

            for expected in expectedList:
                if expected not in self.diskview[item]:
                    self.diskview[item][expected] = None

    def walkparents(self, parents={}):
        mapping = {}
        for item in parents:
            if item in self.diskview:
                typeofitem = self.diskview[item]['devtype']
                if parents[item] is None:
                    return {item: typeofitem}
                elif type(parents[item]) == dict:
                    mapping.update({item: typeofitem})
                    result = self.walkparents(parents=parents[item])
                    mapping.update(result)
                    return mapping

    def getChildren(self, name):
        devroot =  self.diskview[name]['fullpath']
        childMap = {}
        slaves = devroot.joinpath('slaves')
        directchildren = [slave.name for slave in list(slaves.glob("*"))]
        if len(directchildren) == 0:
            childMap = None
            return childMap
        else:
            for child in directchildren:
                childMap[child] = self.getChildren(child)
            return childMap

    def getYoungestChild(self, name):  # function that can be passed any block device and will return a child at the lowest level in the hiearchy. (usually an sd device)
        try:
            thechildren = self.getChildren(name)
            if thechildren is None:
                return name
            else:
                child = list(thechildren.keys())[0]
                while thechildren[child] is not None:
                    thechildren = thechildren[child]
                    if type(thechildren) is not dict:
                        print("There has been an error in getYoungestChild")
                        exit(1)
                    child = list(thechildren.keys())[0]
                return child
        except Exception as e:
            print("There was an unhandled exception in getYoungestChild")
            print(e)
            return None

    def getAllSDchildren(self,name,unique=True): #gets all SD children of given block device. By default unique=True and function only returns one sd device per physical hard drive.
        SDChildren = []
        devtypeTranslator = {'sd':'sd','md': 'mdparent', 'mpath': 'mpathdmname', 'mpathpart': 'dmraidpart', 'sasaddress': 'sasaddress'}
        if name not in self.diskview:
            print("This is not a valid block device on this system.")
            return (False,'Requested device is not valid')
        devtype = self.diskview[name]['devtype']
        for chassis in self.chassis:
            if unique:
                iomodule = list(self.chassis[chassis]['iomodules'].keys())[0]
                for disk in self.chassis[chassis]['iomodules'][iomodule]['disks']:
                    if disk[devtypeTranslator[devtype]] == name:
                        SDChildren.append(disk['name'])
            else:
                for iomodule in self.chassis['iomodules']:
                    for disk in self.chassis[chassis]['iomodules'][iomodule]['disks']:
                        if disk[devtypeTranslator[devtype]] == name:
                            SDChildren.append(disk['name'])
        return SDChildren


