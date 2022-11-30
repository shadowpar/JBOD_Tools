from pathlib import Path
from .slotlookup import parseLVS, parseProcPartitions, parseProcDevices
import subprocess, re, json
from pprint import pprint

def getChassisInfo(iomodule,debug=False,timeout=60): #retrieves the number of slots and the logical identifier of the chassis
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

def getSerialNumber(scsi_device,debug=False,timeout=60):
    command = ['sg_inq','-p','sn','/dev/'+scsi_device]
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    output = result.stdout.decode('UTF-8').splitlines()
    if len(output) == 0:
        if debug:
            print("not a valid scsi device")
            print(output)
        return None
    else:
        data = output[1].split(':')
        data = data[1].strip()
        return data

def getSASaddress(deviceFullPath,debug=False):
    try:
        sasdevice = Path(deviceFullPath) / 'device' / 'sas_address'
        address = sasdevice.read_text().strip().lstrip('0x')
        return (True,address)
    except Exception as e:
        if debug:
            print("There was an unhandled exception trying to get SAS address for ",deviceFullPath.name)
            print(e)
        return (False,e)

def sortStorageDevices(diskview=False,debug=False):
    lvinventory = parseLVS()
    if lvinventory[0]:
        lvinventory = lvinventory[1]
    else:
        raise Exception("Failed to take inventory of logical volume devices while sorting storage hardware.")
    sortedDevices = {'physical':{'sd':{},'sdpart':{}},'virtual':{'md':{},'lv':{},'mpath':{},'mpathpart':{}}}
    devicesByName = {}
    devBlockPath = Path('/sys/dev/block')
    storageDrivers = ['sd','md','device-mapper']
    vitualpath = Path('/sys/devices/virtual')
    deviceTypes = parseProcDevices()
    deviceTypes = deviceTypes['block'] #dont care about character devices here.
    purgeList = []
    for item in deviceTypes: #generate a list of inappropriate driver moduels to remove from our dictionary.
        if deviceTypes[item]  not in storageDrivers:
            purgeList.append(item)
    for item in purgeList:
        deviceTypes.pop(item,None)
    contents = devBlockPath.glob("*")
    for item in contents:
        numbers = item.name.split(':')
        major = numbers[0].strip()
        minor = numbers[1].strip()
        if major in deviceTypes:
            fullpath = item.resolve()
            name = fullpath.name
            friendlyname = name
            devtype = deviceTypes[major]
            sasaddress = None
            try:
                fullpath.relative_to(vitualpath)
                existence = 'virtual'
                if devtype == 'device-mapper':
                    if name in lvinventory:
                        devtype = 'lv'
                        friendlyname = fullpath.joinpath('dm').joinpath('name').read_text().strip()
                    else:
                        friendlyname = fullpath.joinpath('dm').joinpath('name').read_text().strip()
                        if friendlyname[-1].isdigit():
                            devtype = 'mpathpart'
                        else:
                            devtype = 'mpath'
            except ValueError:
                existence = 'physical'
                if name[-1].isdigit():
                    devtype = 'sdpart'
                else:
                    devtype = 'sd'
                    sasaddress = getSASaddress(deviceFullPath=fullpath)
                    if sasaddress[0]:
                        sasaddress = sasaddress[1]
                    else:
                        sasaddress = None
            sortedDevices[existence][devtype][name] = {'name':name,'existence':existence,'fullpath':fullpath,'major':major,'minor':minor,'devtype':devtype,'friendlyname':friendlyname,'sasaddress':sasaddress}
            devicesByName[name] = {'name':name,'existence':existence,'fullpath':fullpath,'major':major,'minor':minor,'devtype':devtype,'friendlyname':friendlyname,'sasaddress':sasaddress}
    if not diskview:
        return sortedDevices
    else:
        return devicesByName


def getParents(name=None,storageDevices=None): #must pass in the result of sortStorageDevices with diskview=True for iterative context.
    parents = {}
    if name is None:
        return None
    if storageDevices is None:
        storageDevices = sortStorageDevices(diskview=True)
    if 'physical' in storageDevices:
        return None
    if name not in storageDevices:
        return None
    devtype = storageDevices[name]['devtype']
    if devtype == 'sd':
        holders = storageDevices[name]['fullpath'].joinpath('holders')
        rents = [item.name for item in holders.glob("*")]
        if len(rents) == 0:
            partmap = parseProcPartitions(name=name)[1]
            for partition in partmap[name]:
                partparents = getParents(name=partition,storageDevices=storageDevices)
                if partparents is None:
                    pass
                else:
                    parents[partition] = partparents
            if parents == {}:
                parents = None
        else:
            for ancestor in rents:
                result = getParents(name=ancestor,storageDevices=storageDevices)
                if result is None:
                    parents[ancestor] = None
                else:
                    parents[ancestor] = getParents(name=ancestor,storageDevices=storageDevices)
    elif devtype in ['sdpart','mpath','mpathpart','md','lv']: # in order to maintain consistency with device-mapper definition of 'holder' we consider phyiscal drives to be slaves to their partitions.
        holders = storageDevices[name]['fullpath'].joinpath('holders')
        rents = [item.name for item in holders.glob("*")]
        if len(rents) == 0:
            return None
        else:
           for ancestor in rents:
               result = getParents(name=ancestor,storageDevices=storageDevices)
               if result is None:
                   parents[ancestor] = None
               else:
                   parents[ancestor] = getParents(name=ancestor, storageDevices=storageDevices)
    else:
        return None
    return parents

def getSasHosts():
    sysroot = Path('/sys/class/sas_host')
    sas_hosts = list(sysroot.glob('*'))
    hostsMap = []
    for sas_host in sas_hosts:
        sas_host = sas_host / 'device'
        ports = list(sas_host.glob("port*"))
        for port in ports:
            hostsMap.append(port.resolve())
    return hostsMap

def getSEScontrollers():
    sysroot = Path('/sys/class/scsi_generic')
    devs = list(sysroot.glob('*/device/type'))
    ses = {}
    for dev in devs:
        text = dev.read_text().strip()
        if text == '13':
            ses[dev.parent.parent.name] = dev.parent.parent.resolve()
    return ses

def getMounts():
    mountPath = Path('/proc/mounts')
    contents = mountPath.read_text().splitlines()
    devMounts = {}
    for line in contents:
        print(line)
        data = line.split()
        if '/dev/' in data[0]:
            try:
                devMounts[data[0]] = {'name':data[0].split('/')[-1],'mountpoint':data[1],'filesystem':data[2],'options':data[3]}
            except Exception as e:
                print("There was an issue mining mount data for ",data[0])
    return devMounts

def getSMART(serial,sdname):
    proc = subprocess.run(['smartctl','-a','--json','/dev/'+sdname],encoding='UTF-8',stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20)
    data = proc.stdout
    jdata = json.loads(data)
    properties = {}
    properties['serialnumber'] = serial
    try:
        properties['protocol'] = jdata['device']['protocol']
    except KeyError as e:
        properties['protocol'] = ''
    try:
        if jdata['smart_status']['passed']:
            properties['smartstatus'] = 'passed'
        else:
            properties['smartstatus'] = 'failed'
    except KeyError as e:
        properties['smartstatus'] = ''
    try:
        properties['temperature'] = jdata['temperature']['current']
    except KeyError as e:
        properties['temperature'] = -1
    try:
       properties['capacity'] = jdata['user_capacity']['bytes']
    except KeyError as e:
        properties['capacity'] = -1
    try:
        properties['rotationrate'] = jdata['rotation_rate']
    except KeyError as e:
        properties['rotationrate'] = -1
    if properties['protocol'] == 'ATA':
        ATAproperties = getSMARTata(jdata=jdata)
        properties.update(ATAproperties)
        scsiempty = getSMARTscsi()
        properties.update(scsiempty)
    elif properties['protocol'] == 'SCSI':
        scsiproperties = getSMARTscsi(jdata=jdata)
        properties.update(scsiproperties)
        ataempty = getSMARTata()
        properties.update(ataempty)
# Items below this are not actually provided by smartctl -a --json but are included in the properties dictionary for later filling from other sources.
    try:
        properties['health'] = ''
    except KeyError as e:
        properties['health'] = ''
    try:
        properties['indicatorled'] = False
    except KeyError as e:
        properties['indicatorled'] = False
    # try:
    #     properties['index'] = -1
    # except KeyError as e:
    #     properties['index'] = -1
    # try:
    #     properties['slot'] = -1
    # except KeyError as e:
    #     properties['slot'] = -1
    return properties

def getSMARTata(jdata={}):
    try:
        ATAattributes = {item['name']: item['value'] for item in jdata['ata_smart_attributes']['table']}
    except KeyError as k:
        ATAattributes = {}
    try:
        ATAattributes['firmware'] = jdata['firmware_version']
    except KeyError as k:
        pass
    try:
        ATAattributes['model'] = jdata['model_name']
    except KeyError as k:
        pass
    try:
        ATAattributes['vendor'] = jdata['model_family']
    except KeyError as k:
        pass
    return ATAattributes

def getSMARTscsi(jdata={}):
    properties = {}
    try:
        properties['vendor'] = jdata['vendor']
    except KeyError as e:
        print("Key error on vendor scsi",e)
        properties['vendor'] = ''
    try:
        properties['model'] = jdata['product']
    except KeyError as e:
        print("Key error on model scsi", e)
        properties['model'] = ''
    try:
        properties['firmware'] = jdata['revision']
    except KeyError as e:
        properties['firmware'] = ''
    try:
        properties['growndefects'] = jdata['scsi_grown_defect_list']
    except KeyError as e:
        properties['growndefects'] = -1
    try:
        properties['uncorrectedreads'] = jdata['scsi_error_counter_log']['read']['total_uncorrected_errors']
    except KeyError as e:
        properties['uncorrectedreads'] = -1
    try:
        properties['uncorrectedwrites'] = jdata['scsi_error_counter_log']['write']['total_uncorrected_errors']
    except KeyError as e:
        properties['uncorrectedwrites'] = -1
    try:
        properties['uncorrectedverify'] = jdata['scsi_error_counter_log']['verify']['total_uncorrected_errors']
    except KeyError as e:
        properties['uncorrectedverify'] = -1
    return  properties
