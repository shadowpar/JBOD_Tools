import subprocess
from pathlib import Path
import os, re
import concurrent.futures
from .slotlookup import oldjbodSASMapper, generateSlotStatusMap, parseLVS, parseProcDevices
from .raidOperations import getAllRaidInfo
from pprint import pprint
from pathlib import Path
# The purpose of this file is to house functions related to disk operations.

def identifyBlockDevClass(blockDevName, sdBlockDevices=None, lvBlockDevices=None):
    classes = ['sdhd','sdpart','md','mpath','mpathpart','lv']
    blockpath = Path('/sys/block/')
    if sdBlockDevices is None: #optionally you can pass in list of sd block devices and lv block devices to make command run faster for many iterations.
        sdBlockDevices = [item.name for item in list(blockpath.glob("sd*"))]
    if lvBlockDevices is None: #the parseLVS() command can ber run outside of this once and passed in instead of running again fro every device.
        lvBlockDevices = parseLVS()
    driverMap = parseProcDevices()
    devFile = blockpath.joinpath(blockDevName).joinpath('dev')
    with devFile.open('r') as f:
        data = f.read().strip().split(':')
        majorNum = data[0]
        minorNum = data[1]
    driver = driverMap['block'][majorNum]
    if driver =='md':
        return classes[2]
    elif driver == 'sd':
        if blockDevName in sdBlockDevices:
            return classes[0]
        else:
            return classes[1]
    elif driver == 'device-mapper':
        if blockDevName in lvBlockDevices:
            return classes[5]
        with Path('/sys/block').joinpath(blockDevName).joinpath('dm').joinpath('name').open('r') as f:
            name = f.read().strip()
            check = re.search(r'.*\d+$',name)
            if check:
                return classes[4]
            else:
                return classes[3]


def prepareAddReplacementDisk(blockDevName, mdname,timeout=60):
    diskinfo = getBlockDevInfo([blockDevName], diskview=True,timeout=timeout)
    if diskinfo[blockDevName]['mdparent'] is not None:
        print("This disk is not eligible for this function. It is already part of:", diskinfo[blockDevName]['mdparent'])
        return (False,"This disk is not eligible for this function. It is already part of:",diskinfo[blockDevName]['mdparent'])
    elif diskinfo[blockDevName]['dmraidpart'] is not None:
        print("It appears this disk already has a raid parititon on it. Perhaps it was part of another raid array?")
        print("If you continue, the existing superblock will be destroyed. This will wipe all data on the disk.")
        answers = {'c':True,'b':False}
        while True:
            fromuser = input("Please type 'c' to continue or 'b' to cancel the request and return to the previous menu.")
            if fromuser not in answers:
                print("That is not a valid entry. Please try again.")
                continue
            else:
                if not fromuser:
                    print("Cancelling action.")
                    return (False,"User chose to cancel the action.")
                elif fromuser:
                    print("Overwriting existing structures.")
                    break
    flushresult = flushMultipath(blockDevName)
    if flushresult[0]:
        print("succeded in flushing multipath map:", diskinfo[blockDevName]['mpathname'])
    else:
        print("Failed to flush multipath map.")
        print(flushresult[1])
        return (False,'Failed to flsuh multipath map.')
    #Now we will create the RAID parition.
    raidpartinfo = createRAIDpartition(blockDevName)
    if not raidpartinfo[0]:
        print("There was an error creating the RAID partition.")
        print(raidpartinfo[1])
    elif raidpartinfo[0]:
        print("RAID partition creation sucessful.")
        print("The raid parition has dm name ",raidpartinfo[1][0],'and friendly name',raidpartinfo[1][1])
    handlempath = buildMultipathMaps(blockDevName)
    if not handlempath[0]:
        print("There was an error creating the multipath device.")
        print(handlempath[1])
        return (False,'There was a problem creating the multipath device.')
    else:
        print("Sucessfully created mpath device",handlempath[1])
        addraidinfo = addDriveToRAID(blockDevName=blockDevName, mdname=mdname)
        if not addraidinfo[0]:
            print("There was an error adding the disk to the raid")
            print(addraidinfo[1])
            return (False,'There was a problem adding the disk to the raid array.')
        elif addraidinfo[0]:
            return (True,'The disk has been prepared and added to the raid array.')




def addDriveToRAID(blockDevName,mdname,timeout=60):
    outputQueue = []
    diskinfo = getBlockDevInfo(blockDevName,timeout=timeout)
    if diskinfo[blockDevName]['dmraidpart'] is None:
        return (False,'No dm raid partition detected. Cannot add device to ',mdname)
    else:
        command = ['mdadm','-a','/dev/'+mdname,'/dev/'+diskinfo[blockDevName]['dmraidpart']]
        print("Running command",command)
        outputQueue.append(command)
        result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
        output = result.stdout.decode("UTF-8")
        outputQueue.append(output)
    # Now check if the disk was sucessfully added.
    mdparentinfo = getMDparent(blockDevName)
    if mdparentinfo is None:
        print("Failed to add drive",blockDevName,"to md device",mdname)
        return (False,outputQueue)
    else:
        print("Sucessfully added",blockDevName,"to md device",mdname)
        return (True,mdparentinfo)

def buildMultipathMaps(blockDevName,timeout=60):
    outputQueue = []
    if '/dev/' in blockDevName:
        blockDevName = blockDevName.lstrip('/dev/')
    child = getYoungestChild(blockDevName)
    command = ['multipath']
    outputQueue.append(command)
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    output = result.stdout.decode("UTF-8")
    outputQueue.append(output)
    #check if multipath device for this blockdevice exists.
    mpathinfo = getMpathParent(child)
    if mpathinfo is None:
        print("There was an error building the multipath map for ",blockDevName)
        return (False,outputQueue)
    else:
        print(blockDevName,'is now part of multipath device:',mpathinfo)
        return (True,mpathinfo)



def createRAIDpartition(blockDevName,timeout=60):
    outputQueue = []
    if '/dev/' in blockDevName:
        blockDevName = blockDevName.lstrip('/dev/')
    child = getYoungestChild(blockDevName)
    command = ['parted','-s','/dev/'+child,'mklabel','gpt']
    print("Running command",command)
    outputQueue.append(command)
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    output = result.stdout.decode("UTF-8")
    outputQueue.append(output)
    command = ['parted','-s','/dev/'+child,'-a','optimal','unit','MB','mkpart','primary','1','100%','set','1','hidden','on']
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    output = result.stdout.decode("UTF-8")
    outputQueue.append(output)
    #now check if the RAID parition was creatied sucessfully.
    raidpart = getRAIDpartition(child)
    if raidpart is None:
        print("Failed to create RAID partition.")
        return (False,outputQueue)
    else:
        print("Succeded in creating a RAID partition.")
        return (True,raidpart) #returned raidpart is a tuple containing the dm-name and friendly name of the RAID partition.


def flushMultipath(child,timeout=60):
    outputQueue = []
    diskview = getBlockDevInfo([child], diskview=True,timeout=timeout)
    attrs = diskview[child]
    if attrs['mpathname'] is not None:
        command = ['multipath','-f',attrs['mpathname']]
        print("I am executing this command",command)
        outputQueue.append(command)
        proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
        output = proc.stdout.decode("UTF-8").strip()
        outputQueue.append(output)

    mpathname = getMpathParent(blockDeviceName=child)
    if mpathname is not None:
        print("The utility failed to flush multipath device",mpathname)
        return (False,outputQueue) # for temporary non destructive testing.
    else:
        return (True,outputQueue)

def getChildren(blockDevName):
    sysroot =Path('/sys/block')
    devroot = sysroot.joinpath(blockDevName)
    childMap = {}
    slaves = devroot.joinpath('slaves')
    directchildren = os.listdir(slaves.resolve())
    if len(directchildren) == 0:
        childMap = None
        return childMap
    else:
        for child in directchildren:
            childMap[child] = getChildren(child)
        return childMap

def getYoungestChild(blockDevName): # function that can be passed any block device and will return a child at the lowest level in the hiearchy. (usually an sd device)
    try:
        thechildren = getChildren(blockDevName)
        if thechildren is None:
            return blockDevName
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




def getblockPCIpath(blockDevName):
    sysroot =Path('/sys/block')
    devroot = sysroot.joinpath(blockDevName)
    deviceroot = devroot.joinpath('device')
    pcipath = deviceroot.resolve()
    return pcipath

def getSasHosts():
    sysroot = Path('/sys/class/sas_host')
    sas_hosts = list(sysroot.glob('*'))
    hostsMap = []
    for sas_host in sas_hosts:
        sas_host = sas_host / 'device'
        ports = list(sas_host.glob("port*"))
        for port in ports:
            hostsMap.append(port.resolve().as_posix())
    return hostsMap

def getSEScontrollers():
    sysroot = Path('/sys/class/scsi_generic')
    devs = list(sysroot.glob('*/device/type'))
    ses = {}
    for dev in devs:
        text = dev.read_text(encoding='UTF-8').strip()
        if text == '13':
            ses[dev.parent.parent.resolve().as_posix()] = dev.parent.parent.name
    return ses

def parseED(sgname='sg1',timeout=60): #function for ultrastar102 JBODs, or any JBOD that reports the serial number as part of the element descriptor for array slot elements. creats a map of  hard drive serial number and their index and slot.
    try:
        mydata = subprocess.run(['sg_ses','-p','ed','/dev/'+sgname],stderr=subprocess.DEVNULL,stdout=subprocess.PIPE,encoding='utf-8',timeout=timeout)
    except subprocess.TimeoutExpired as t:
        print('sg device',sgname,'failed to respond in a timely manner')
        slotmap = {}
        return slotmap
    except Exception as e:
        print("There was some exception besides subprocess timeout")
        print(e)
        return {}
    mydata = mydata.stdout.splitlines()
    first = 0
    last = 101
    entered = False
    for idx, line in enumerate(mydata):
        if 'Element type: Array device slot' in line:
            first = idx+2
            entered = True
        elif 'Element type:' in line:
            if entered:
                last = idx
                break
    mydata = mydata[first:last]
    slotmap = {}
    for item in mydata:
        result = re.search(r'^\s*Element ([0-9]*) descriptor: SLOT ([0-9]*),(.*)\s*$',item)
        if result:
            idx = str(result.group(1)).strip()
            slot = str(result.group(2)).strip()
            serial = str(result.group(3)).strip()
            slotmap[serial] = {'index':int(idx),'slot':int(slot)}
    return slotmap

def getChassisInfo(iomodule,timeout=60): #retrieves the number of slots and the logical identifier of the chassis
    command = ['sg_ses','-p','cf','/dev/'+iomodule]
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    result = result.stdout.decode("UTF-8").lower().splitlines()
    info = {'logicalid':'error','numslots':-1,'vendor':'error','model':'error','revision':'error','serialnumber':'error'}
    info['serialnumber'] = getSerialNumber(iomodule)
    nextlineFlag = False
    for line in result:
        if 'enclosure logical identifier' in line:
            info['logicalid'] = line.split()[-1].strip()
        elif 'enclosure vendor' in line:
            data = re.search(r'^.*vendor:(.*)product:(.*)rev:(.*)$',line)
            if data:
                info['vendor'] = data[1].strip()
                info['model'] = data[2].strip()
                info['revision'] = data[3].strip()
        elif 'element type: array device slot' in line:
            nextlineFlag = True
        elif nextlineFlag is True and 'number of possible elements' in line:
            info['numslots'] = int(line.split()[-1])
            break
    return info



def generateSASMap(iomodule, numslots): #parallel function that builds a map between index, slot, and sas address
    sasmap = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_run_loops = {executor.submit(getSlotInfo, indexNumber=index,sgtarget=iomodule): index for index in range(0,numslots)}
        for future in concurrent.futures.as_completed(future_run_loops):
            if future.result() is not None:
                sasmap[future.result()[0]] = {}
                sasmap[future.result()[0]]['index'] = future.result()[1]
                sasmap[future.result()[0]]['slot'] = future.result()[2]
            else:
                print("I was unable to find the slot number for some indexes.")
    return sasmap

def getSlotInfo(indexNumber,sgtarget,timeout=60):
    print("Get slot info called on index",indexNumber,"of enclosure",sgtarget)
    SESTIMEOUT = timeout
    slotNumber = None
    sasaddress = None
    try:
        results = subprocess.run(['sg_ses','-p','aes','--index=0,'+str(indexNumber),'/dev/'+sgtarget],encoding='UTF-8',stderr=subprocess.DEVNULL,stdout=subprocess.PIPE,timeout=SESTIMEOUT)
        results = results.stdout.splitlines(keepends=False)
    except subprocess.TimeoutExpired as t:
        results = []
        print("Timeout expired for",sgtarget,"index number",indexNumber,"after this many seconds:",SESTIMEOUT)
    for line in results:
        if 'device slot number' in line:
            slotNumber = line.split(' ')[-1]

        if 'SAS address: 0x' in line:
            if 'attached' not in line:
                sasaddress = line.split('x')[-1]
    if slotNumber is not None and sasaddress is not None:
        return (sasaddress,indexNumber,slotNumber)
    else:
        print("It seems i failed to find the slot number or sas address")
        return None

def makePortMapping():
    sashosts = getSasHosts()
    sescontrollers = getSEScontrollers()
    portmapping = {}
    for port in sashosts:
        for item in sescontrollers:
            if port in item:
                portmapping[port] = sescontrollers[item]
    return portmapping #this is a dictionary that mapps the pci path to a hba port as a key to a the generic scsi name of the SES controllers for commands like sg_ses --join --index=65 /dev/sg1

def getDiskIndex(blockDevName,sasMapper):
    sasfile = Path('/sys/block') / blockDevName / 'device' / 'sas_address'
    with sasfile.open('r') as f:
        address = f.read().strip().lstrip('0x')
    index = sasMapper[address]['index']
    return index

def getDiskSlot(blockDevName,sasMapper):
    sasfile = Path('/sys/block') / blockDevName / 'device' / 'sas_address'
    with sasfile.open('r') as f:
        address = f.read().strip().lstrip('0x')
    slot = sasMapper[address]['slot']
    return slot

def getSASinformation(blockDevName,sasMapper):
    sasfile = Path('/sys/block') / blockDevName / 'device' / 'sas_address'
    with sasfile.open('r') as f:
        address = f.read().strip().lstrip('0x')
        index = sasMapper[address]['index']
        slot = sasMapper[address]['slot']
    return {'sasaddress':address,'index':index,'slot':slot}

def getDiskEnclosure(blockDevName,portmapper):

    blockpath = getblockPCIpath(blockDevName=blockDevName).as_posix()
    sescontroller = None
    for item in portmapper:
        if item in blockpath:
            sescontroller = portmapper[item]
    return sescontroller

def getRAIDpartition(blockDeviceName):
    try:
        rents = os.listdir('/sys/block/' + blockDeviceName + '/holders')
    except FileNotFoundError as e:
        print("Tried to find the RAID partition for a block device that does not exist.")
        return None
    if len(rents) != 0:
        try:
            with open('/sys/block/'+rents[0]+'/dm/name') as f:
                name = f.read().strip()
                if 'mpath' in name:
                    result = re.search(r'(mpath.*\d)',name)
                    if result:
                        return (rents[0],name)
                    else:
                        return getRAIDpartition(blockDeviceName=rents[0])
                else:
                    return getRAIDpartition(blockDeviceName=rents[0])
        except FileNotFoundError:
            print('This parent does not appear to be a dm device.')
            return None
    else:
        return None

def getMDparent(blockDeviceName):
    rents = os.listdir('/sys/block/'+blockDeviceName+'/holders')
    result = None
    if len(rents) != 0: # that is there is an entry in the holders directory.
        if not 'md' in rents[0]:
            result = getMDparent(rents[0])
        elif 'md' in rents[0]:
            result = str(rents[0])
            return result
    elif len(rents) == 0:
        result = None
        return result
    return result

def getMDparentNoMpath(blockDeviceName):
    mypath = Path('/proc/partitions')
    with mypath.open('r') as f:
        lines = f.read().splitlines()

def getMpathParent(blockDeviceName):
    try:
        rents = os.listdir('/sys/block/' + blockDeviceName + '/holders')
    except FileNotFoundError as e:
        print("Tried to find the mpath parent for a block device that does not exist.")
        return None

    if len(rents) != 0:
        try:
            with open('/sys/block/'+rents[0]+'/dm/name') as f:
                name = f.read().strip()
                if 'mpath' in name:
                    result = re.search(r'(mpath[a-zA-Z]+)',name)
                    if result:
                        return (rents[0],name)
                    else:
                        return getMpathParent(blockDeviceName=rents[0])
                else:
                    return getMpathParent(blockDeviceName=rents[0])
        except FileNotFoundError:
            print('This parent does not appear to be a dm device.')
            return None
    else:
        return None

def getSerialNumber(scsi_device):
    command = ['sg_inq','-p','sn','/dev/'+scsi_device]
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=10)
    output = result.stdout.decode('UTF-8').splitlines()
    if len(output) == 0:
        print("not a valid scsi device")
        print(output)
        return None
    else:
        data = output[1].split(':')
        data = data[1].strip()
        return data
# Bornalibra7October!1992

def getRAIDmemberStatus(member):
    if '/dev/' in member:
        member = member.lstrip('/dev/')
    command = ['mdadm','-E','/dev/'+member]
    result = subprocess.run(command,stdout=subprocess.PIPE)
    result = result.stdout.decode("UTF-8").lower().splitlines()
    for line in result:
        if 'no md superblock detected' in line:
            print("This is not a RAID member")
            return None
        elif 'cannot open' in line:
            print("This is not a valid block device")
            return None
        elif 'device role' in line:
            status= line.split(':')[-1].strip()
            return str(status)

def setDriveBlinking(name,timeout=60):
    sdblocks = [item.name for item in list(Path('/sys/block').glob("sd*"))]
    if name not in sdblocks:
        print("This is not an sd device on the system.")
        return (False,name+' is not an sd device on the system.')
    else:
        try:
            diskinfo = getBlockDevInfo(disks=[name],diskview=True,timeout=timeout)
            attrs = diskinfo[name]
            outputQueue = []
            command = ['sg_ses','--index=0,'+attrs['index'],'--set','ident','/dev/'+attrs['enclosure']]
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

            command = ['sg_ses','--index=0,'+attrs['index'],'--set','fault','/dev/'+attrs['enclosure']]
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

            lightStatus = checkDriveBlinking(name=name)
            if lightStatus[0]:
                if lightStatus[1] == {'ident':'1','fault':'1'}:
                    return (True,outputQueue)
                else:
                    return (False,outputQueue)
        except Exception as e:
            print("There was an unhandled exception while trying to set blinking lights.")
            print(e)
            return (False,e)

def checkDriveBlinking(name,timeout=60):
    sdblocks = [item.name for item in list(Path('/sys/block').glob("sd*"))]
    if name not in sdblocks:
        print("This is not an sd device on the system.")
        return (False,"This is not an sd device on the system.")
    else:
        try:
            diskinfo = getBlockDevInfo(disks=[name],diskview=True,timeout=timeout)
            attrs = diskinfo[name]
            result= {'ident':None,'fault':None}
            commandQueue = []
            outputQueue = []
            command = ['sg_ses','--index=0,'+attrs['index'],'--get','ident','/dev/'+attrs['enclosure']]
            outputQueue.append(command)
            proc = subprocess.run(command,stdout=subprocess.PIPE,timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)
            if output == '1':
                result['ident'] = '1'
            elif output == '0':
                result['ident'] = '0'
            else:
                return (False,outputQueue)
            # now check the state of the fault field
            command = ['sg_ses','--index=0,'+attrs['index'],'--get','fault','/dev/'+attrs['enclosure']]
            commandQueue.append(command)
            proc = subprocess.run(command,stdout=subprocess.PIPE,timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)
            if output == '1':
                result['fault'] = '1'
            elif output == '0':
                result['fault'] = '0'
            else:
                return (False,outputQueue)
            return (True,result)
        except Exception as e:
            print("There was an unknown issue checking disk light status")
            return (False,str(e))

def clearDriveBlinking(name,timeout=60):
    sdblocks = [item.name for item in list(Path('/sys/block').glob("sd*"))]
    if name not in sdblocks:
        print("This is not an sd device on the system.")
        return (False, name + ' is not an sd device on the system.')
    else:
        try:
            diskinfo = getBlockDevInfo(disks=[name], diskview=True,timeout=timeout)
            attrs = diskinfo[name]
            outputQueue = []
            command = ['sg_ses', '--index=0,' + attrs['index'], '--clear', 'ident', '/dev/' + attrs['enclosure']]
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

            command = ['sg_ses', '--index=0,' + attrs['index'], '--clear', 'fault', '/dev/' + attrs['enclosure']]
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

            lightStatus = checkDriveBlinking(name=name)
            if lightStatus[0]:
                if lightStatus[1] == {'ident': '0', 'fault': '0'}:
                    return (True, outputQueue)
                else:
                    return (False, outputQueue)
        except Exception as e:
            print("There was an unhandled exception while trying to clear blinking lights.")
            return (False,e)

def getBlockDevInfo(disks=[],diskview=False,timeout=60): #returns a dictionary of the form {diskname1:{'slot':integer,'index':integer,'enclosure':string}
    diskinfo = {}
    chassis = {}
    enclosures = {}
    ses_enclosure_port_mapper = makePortMapping() # a dictionary that maps pci port path to sg name for ses enclosure devices.
    sasMapper = {}
    raidMapper = getAllRaidInfo()
    slotPropertyMapper = {}


    for item in list(ses_enclosure_port_mapper.values()):
        enclosures[item] = getChassisInfo(iomodule=item,timeout=timeout)
        if enclosures[item]['serialnumber'] not in chassis:
            chassis[enclosures[item]['serialnumber']] = {'iomodules':{item:{'disks':[{} for i in range(int(enclosures[item]['numslots']))]}},'logicalid':enclosures[item]['logicalid'],'numslots':enclosures[item]['numslots'],
                                                       'vendor':enclosures[item]['vendor'],'model': enclosures[item]['model'],'revision':enclosures[item]['revision']}
        else:
            chassis[enclosures[item]['serialnumber']]['iomodules'][item] = {'disks':[{} for i in range(int(enclosures[item]['numslots']))]}

        # sasMapper[item] = generateSASMap(iomodule=item,numslots=enclosures[item]['numslots'])
        sasMapper[item] = oldjbodSASMapper(item)
        slotPropertyMapper[item] = generateSlotStatusMap(iomodule=item)
    # for disk in disks:
    def getInfo(disk):
        ses_enclosure = getDiskEnclosure(disk,ses_enclosure_port_mapper)
        #get multiipath deivce info about disk
        multipathinfo = getMpathParent(disk)
        if multipathinfo is not None:
            mpathname = multipathinfo[1]
            mpathdmname = multipathinfo[0]
        else:
            mpathname = None
            mpathdmname = None

        #get raid parition info about disk
        raidpartinfo = getRAIDpartition(disk)
        if raidpartinfo is not None:
            dmraidpart = raidpartinfo[0]
            dmraidpartname = raidpartinfo[1]
        else:
            dmraidpart = None
            dmraidpartname = None
        #get md device info
        mdname = getMDparent(disk) # returns the name of md device to which disk belongs if present.
        if mdname is not None:
            mdparent = mdname
        else:
            mdparent = None

        if ses_enclosure is None:
            diskinfo[disk] = None
            diskinfo.pop(disk,None) #handles system disk not handled by an SCSI Enclosure Services device by removing them.
            return None
        else:
            sasdata = getSASinformation(disk,sasMapper[ses_enclosure])
            diskinfo[disk] = {'slot':sasdata['slot'],'enclosure':ses_enclosure,'index':sasdata['index'],'mdparent':mdparent,'dmraidpart':dmraidpart,'dmraidpartname':dmraidpartname,
                              'mpathname':mpathname,'mpathdmname':mpathdmname,'sasaddress':sasdata['sasaddress'],'name':disk}
        return disk
 # --------------------------------------------------------concurrent operations speedup area -------------------------------------------

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_run_loops = {executor.submit(getInfo, disk=disk): disk for disk in disks}
        for future in concurrent.futures.as_completed(future_run_loops):
            pass
#---------------------------end concurrent operations --------------------------------------------
    #create a mapping from iomodule sg name to chassis serial number
    iomoduleChassisMap = {}
    for serial in chassis:
        for module in chassis[serial]['iomodules']:
            if module not in iomoduleChassisMap:
                iomoduleChassisMap[module] = serial
    #----map completed. Below we will use the map to sort disks into appropriate enclosures.

    #use multithreaded processing to grab raid array role for each disk.
    def lookupRAIDrole(disk):
        try:
            dmraidpart = diskinfo[disk]['dmraidpart']
            mdparent = diskinfo[disk]['mdparent']
            raidmemberstatus = raidMapper[mdparent][dmraidpart]['state']
            return raidmemberstatus
        except Exception as e:
            print("There was an issue getting RAID member status for ",disk)
            print(e)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_run_loops = {executor.submit(lookupRAIDrole, disk=disk): disk for disk in diskinfo}
        for future in concurrent.futures.as_completed(future_run_loops):
            diskname = future_run_loops[future]
            if future is not None:
                diskinfo[diskname]['raidrole'] = future.result()
            else:
                print("unable to find status of raidpart assciated with ",diskname)
                diskinfo[diskname]['raidrole'] = None
# start a multithreaded approach to looking up LED light status for each disk.
    def lookupLightStatus(disk):
        try:
            enclosure = diskinfo[disk]['enclosure']
            index = int(diskinfo[disk]['index'])
            ident = slotPropertyMapper[enclosure][index]['ident']
            fault = slotPropertyMapper[enclosure][index]['fault reqstd']
            lightStatus = (ident,fault)
            lightStatus = {('0','0'):'Off',('0','1'):'Mixed',('1','0'):'Mixed',('1','1'):'On'}[lightStatus]
            return lightStatus
        except Exception as e:
            print("There was an issue getting the locator LED status for ",disk)
            print(e)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_run_loops = {executor.submit(lookupLightStatus, disk=disk): disk for disk in diskinfo}
        for future in concurrent.futures.as_completed(future_run_loops):
            diskname = future_run_loops[future]
            if future is not None:
                diskinfo[diskname]['ledstatus'] = future.result()
            else:
                print("unable to find status of raidpart assciated with ",diskname)
                diskinfo[diskname]['ledstatus'] = None



    # special case where datashould be returned from the the disk perspective instead of chassis perspective.
    def generatediskview(disk):
        try:
            enc = diskinfo[disk]['enclosure']
            jbodserial = iomoduleChassisMap[enc]
            index = diskinfo[disk]['index']
            name = disk
            diskinfo[disk]['name'] = name
            diskinfo[disk]['jbodserial'] = jbodserial
            diskinfo[disk]['index'] = index
            diskinfo[disk]['enclosure'] = enc
            return True
        except KeyError as e:
            print("error running generatediskview",disk)
            print(e)
            return False
        except Exception as r:
            print("There was an unknown error during generate disk view ",disk)
            print(r)
            return r

    # -------------------------end special case.----------------------------
    def quickSortDisks(disk):
        try:
            enc = diskinfo[disk]['enclosure']
            serial = iomoduleChassisMap[enc]
            index = diskinfo[disk]['index']
            name = disk
            diskinfo[disk]['name'] = name
            chassis[serial]['iomodules'][enc]['disks'][int(index)] = diskinfo[disk]
            return True
        except KeyError as e:
            print("error running quicksort disks",disk)
            print(e)
            return False
        except Exception as r:
            print("There was an unknown error during sorting disk ",disk)
            print(r)
            return r


    if not diskview:
    #multithreaded disk sorting.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_run_loops = {executor.submit(quickSortDisks, disk=disk): disk for disk in diskinfo}
            for future in concurrent.futures.as_completed(future_run_loops):
                if future.result():
                    pass
                else:
                    print("Failed in adding disk")
                    print(future.result())
        return chassis
    elif diskview:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_run_loops = {executor.submit(generatediskview, disk=disk): disk for disk in diskinfo}
            for future in concurrent.futures.as_completed(future_run_loops):
                if future.result():
                    pass
                else:
                    print("Failed in adding disk")
                    print(future.result())
        return diskinfo

