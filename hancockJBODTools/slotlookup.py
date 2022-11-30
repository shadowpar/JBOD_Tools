import re, subprocess
import concurrent.futures
from pprint import pprint
from os import readlink
from pathlib import Path
from string import digits as DIGITS



slotLookupMethod = {'84BAY EBOD':'sasmap','H4102-J':'direct','ScaleApex 4U102':'direct','SS8412':'sasmap','SP-3584-E12EBD':'sasmap','60BAY EBOD':'sasmap','60BAY_EBOD':'sasmap'}

def parseProcDevices():
    type = None
    devices = {'character':{},'block':{}}
    with open('/proc/devices','r') as f:
        contents = f.read().lower().splitlines()
    for line in contents:
        if 'character devices:' in line:
            type = 'character'
        elif 'block devices:' in line:
            'Turn on block devices'
            type = 'block'
        elif line.strip() == '':
            continue
        else:
            data = line.split()
            majornum = data[0].strip()
            driver = data[1].strip()
            devices[type][majornum] = driver
    return devices

def parseLVS():
    data = {}
    command = ['lvs','--aligned']
    try:
        result = subprocess.run(command,stdout=subprocess.PIPE,timeout=30)
    except FileNotFoundError as f:
        print("Program LVS not found. Assuming there are no logical volumes",f)
        return (True,{})
    if result.returncode != 0:
        return (False,{})
    output = result.stdout.decode("UTF-8").splitlines()
    try:
        if output[0].split()[0].strip() == 'LV':
            del output[0]
            for line in output:
                lineparts = line.split()
                lvname = lineparts[0].strip()
                vgname = lineparts[1].strip()
                attributes = lineparts[2].strip()
                logicalsize = lineparts[3].strip()
                try:
                    dmname = readlink('/dev/mapper/'+vgname+'-'+lvname).split('/')[-1]
                except Exception as e:
                    print(e)
                    dmname = 'error'
                data[dmname] =  {'lvname':lvname,'vgname':vgname,'attributes':attributes,'logicalsize':logicalsize, 'dmname':dmname}
        else:
            return (False,{})
        return (True,data)
    except IndexError as i:
        print("There appear to be no logical volumes present.",i)
        return (True,{})

def generateSlotStatusMap(iomodule):
    command = ['sg_ses', '-p', 'es', '/dev/' + iomodule]
    result = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
    result = result.stdout.decode("UTF-8").lower().splitlines()
    startdrives = False
    datadict = {}
    elementNumber = None

    for line in result:
        if not startdrives and 'element type: array device slot' in line:
            startdrives = True
            continue
        elif startdrives:
            if 'element type: ' in line:
                break
            elif 'element' in line and 'descriptor' in line:
                elementNumber = line.split()[1]
                datadict[elementNumber] = {}
            elif elementNumber is not None:
                linedata = line.strip().split(',')
                for item in linedata:
                    if ':' in item:
                        # print(item)
                        itemdata = item.split(':')
                        datadict[elementNumber][itemdata[0].strip()] = itemdata[1].strip()
                    else:
                        # print(item)
                        itemdata = item.split('=')
                        datadict[elementNumber][itemdata[0].strip()] = itemdata[1].strip()
    datalist = [{} for i in range(len(datadict))]
    for item in datadict:
        datalist[int(item)] = datadict[item]
    return datalist

def parseED(sgname='sg1'): #function for ultrastar102 JBODs, or any JBOD that reports the serial number as part of the element descriptor for array slot elements. creats a map of  hard drive serial number and their index and slot.
    try:
        mydata = subprocess.run(['sg_ses','-p','ed','/dev/'+sgname],stderr=subprocess.DEVNULL,stdout=subprocess.PIPE,encoding='utf-8',timeout=45)
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

def getSlotInfo(indexNumber,sgtarget):
    print("Get slot info called on index",indexNumber,"of enclosure",sgtarget)
    SESTIMEOUT = 45
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

def oldjbodSASMapper(iomodule,timeout=30):
    command = ['sg_ses','-p','aes','/dev/'+iomodule]
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=timeout)
    result = result.stdout.decode("UTF-8").lower().splitlines()
    startdrives = False
    enddrives = False
    driveLines = []
    sasmap = {}
    for line in result:
        if 'element type: array device slot' in line:
            startdrives = True
            continue
        elif startdrives and not enddrives:
            if 'element type: ' in line:
                enddrives = True #not needed at the moment but included for completeness.
                break
            else:
                driveLines.append(line)
    startdrives = False
    enddrives = False
    index, slot, sasaddress = -1,-1,'error'
    for line in driveLines:
        if not startdrives and 'element index:' in line:
            startdrives = True
            index = line.split()[2]
            continue
        elif startdrives and 'device slot number:' in line:
            slot = line.split()[-1].strip()
            continue
        elif startdrives and 'attached sas address' in line:
            attachpoint = line.split()[-1].strip().lstrip('0x')
            continue
        elif startdrives and 'sas address' in line:
            sasaddress = line.split()[-1].strip().lstrip('0x')
            sasmap[sasaddress] = {'index':index,'slot':slot}
            startdrives = False
            continue
    return sasmap






def getSASMapping(iomodule, model='4102-J'):
    pass

def parseProcPartitions(name=None):
    procpartPath = Path('/proc/partitions')
    data = procpartPath.read_text().splitlines()
    del data[0]
    del data[0]
    results = {}
    if name is not None:
        for line in data:
            if name in line:
                linedata = line.split()
                base = linedata[-1].strip().rstrip(DIGITS)
                if base not in results:
                    results[base] = []
                else:
                    results[base].append(linedata[-1].strip())
    else:
        for line in data:
            linedata = line.split()
            base = linedata[-1].strip().rstrip(DIGITS)
            if base not in results:
                results[base] = []
            else:
                results[base].append(linedata[-1].strip())
    return (True,results)





