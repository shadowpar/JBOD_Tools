#!/usr/bin/python3.6
import os, re,subprocess

from hancockJBODTools import getYoungestChild, getMDparent, newDiskOperations
from pathlib import Path
from pprint import pprint
from hancockJBODTools import print_disk_list, getmdRAIDinfo, wipeRAIDsuperblock
from hancockJBODTools import storage_info
from sys import argv
from time import sleep
# Conditions to modify
needsModding = {'mdparent':False,'dmraidpart':False,'mpathname':False,'ident':False,'fault':False}

if len(argv) != 2:

    print("You must pass in the name of a disk to use this program. For instance:")
    print("./removeDisk.py sdcr")
    exit(1)
elif    argv[1] == "--help" or argv[1] == "-h":
            print("This program automates the disk removal preparation steps. It is meant to be used for sd devices that are part of a multipath device.")
            print("Its  is further expected that partition sits on top of that multipath device and partipates in a md RAID array.")
            print("Please pass only 1 argument. That argument should be one of the 'SD' names for this disk. i.e. 'sdie'. Note that quotes are not needed.")
            print("There is a different script in this directory for removing disks from ZFS pools.")
            exit(1)
disk = argv[1].strip().strip("'").strip('"')
diskPath = Path("/sys/block").joinpath(disk)
if not diskPath.is_symlink():
    print("/dev/"+disk+" is not a valid block block device on the system.")
    exit(1)
print("\n\n-------------------Beginning remove program-------------------------------------------- ")
myinfo = storage_info()

if  myinfo.diskview[disk]['mdparent'] is not None:
    needsModding['mdparent'] = True
if myinfo.diskview[disk]['dmraidpart'] is not None:
    needsModding['dmraidpart'] = True
if myinfo.diskview[disk]['mpathname'] is not None:
    needsModding['mpathname'] = True
if myinfo.diskview[disk]['ident'] != '1':
    needsModding['ident'] = True
    needsModding['fault'] = True
#Idiot check if disk is actually faulty.
if needsModding['mdparent'] and not 'fault' in myinfo.diskview[disk]['raidrole'].lower():
    print("The disk",disk,"with RAID partition",myinfo.diskview[disk]['dmraidpart'],"is not in a faulty condition.")
    print("If you are certain this disk is faulty please manually fail it with command mdadm --fail",
    "/dev/"+myinfo.diskview[disk]['mdparent'],"/dev/"+myinfo.diskview[disk]['dmraidpart'])
    print("After this you can try to run this wizard again.")
    print("Non standard case detected. Exiting for manual control.")
    exit(1)
#--------------------------------------------------------------------------------------------------------------
while True:
    print("\n\n----------------------I will now perform the following operations--------------------------------\n")
    counter = 1
    if needsModding['mdparent']:
        print(str(counter)+": I will remove RAID partition",myinfo.diskview[disk]['dmraidpart']," which sits on disk",
        disk,"from RAID array",myinfo.diskview[disk]['mdparent'],"with this command")
        print("mdadm -r /dev/"+myinfo.diskview[disk]['mdparent'],"/dev/"+myinfo.diskview[disk]['dmraidpart'])
        counter = counter + 1
    if needsModding['dmraidpart']:
        print(str(counter)+": I will wipe the partition table on disk",disk,"with the following command")
        print("parted -s /dev/mapper/"+myinfo.diskview[disk]['mpathname']+" mklabel gpt")
        counter = counter +1
    if needsModding['mpathname']:
        print(str(counter)+": I will flush the multipath map",myinfo.diskview[disk]['mpathname'],"of which ",disk,"is a participant","with the following command:")
        print("multipath -f "+myinfo.diskview[disk]['mpathname'])
        counter = counter +1
    if needsModding['ident']:
        print(str(counter)+": I will turn on the Ident light for disk",disk,"with the following command:")
        print("sg_ses --index="+myinfo.diskview[disk]['index']+" --set Ident /dev/"+myinfo.diskview[disk]['enclosure'])
        counter = counter +1
    if needsModding['fault']:
        print(str(counter)+": I will turn on the Fault light for disk",disk,"with the following command:")
        print("sg_ses --index="+myinfo.diskview[disk]['index']+" --set Fault /dev/"+myinfo.diskview[disk]['enclosure'])
        counter = counter +1
    print("Are you CERTAIN you want to execute these commands?\n")
    answer = input("Type yes or quit.")
    if answer == 'yes':
        break
    elif answer =='quit':
        print("User chose not to continue the operation. Goodbye!")
        exit(0)
    
completedMessages = []

if needsModding['mdparent']:
    cmd = "mdadm -r /dev/"+myinfo.diskview[disk]['mdparent']+" /dev/"+myinfo.diskview[disk]['dmraidpart']
    status_code, output = subprocess.getstatusoutput(cmd)
    if status_code != 0:
        print("For some reason I failed at removing device ",myinfo.diskview[disk]['dmraidpart'],"from md RAID device",myinfo.diskview[disk]['mdparent'])
        print("Non standard case detected. Exiting for manual control.")
        print(output)
        exit(1)
    else:
        completedMessages.append(cmd)
        sleep(0.5)


if needsModding['dmraidpart']:
    cmd = "parted -s /dev/mapper/"+myinfo.diskview[disk]['mpathname']+" mklabel gpt"
    status_code, output = subprocess.getstatusoutput(cmd)
    if status_code != 0:
        print("For some reason I failed at wiping the parition table on ",disk)
        print("Non standard case detected. Exiting for manual control.")
        print(output)
        print("These commands have already been executed successfully before this error:")
        pprint(completedMessages)
        exit(1)
    else:
        completedMessages.append(cmd)
        sleep(0.5)

if needsModding['mpathname']:
    cmd = "multipath -f "+myinfo.diskview[disk]['mpathname']
    status_code, output = subprocess.getstatusoutput(cmd)
    if status_code != 0:
        print("For some reason I failed at flushing the multipath map ",myinfo.diskview[disk]['mpathname'])
        print("Non standard case detected. Exiting for manual control.")
        print(output)
        print("These commands have already been executed successfully before this error:")
        pprint(completedMessages)
        exit(1)
    else:
        completedMessages.append(cmd)
        sleep(0.5)

if needsModding['ident']:
    cmd = "sg_ses --index="+myinfo.diskview[disk]['index']+" --set Ident /dev/"+myinfo.diskview[disk]['enclosure']
    status_code, output = subprocess.getstatusoutput(cmd)
    if status_code != 0:
        print("For some reason I failed at making Ident light flash for",disk)
        print("Non standard case detected. Exiting for manual control.")
        print(output)
        print("These commands have already been executed successfully before this error:")
        pprint(completedMessages)
        exit(1)
    else:
        completedMessages.append(cmd)


if needsModding['ident']:
    cmd = "sg_ses --index="+myinfo.diskview[disk]['index']+" --set Fault /dev/"+myinfo.diskview[disk]['enclosure']
    status_code, output = subprocess.getstatusoutput(cmd)
    if status_code != 0:
        print("For some reason I failed at making Fault light flash for",disk)
        print("Non standard case detected. Exiting for manual control.")
        print(output)
        print("These commands have already been executed successfully before this error:")
        pprint(completedMessages)
        exit(1)
    else:
        completedMessages.append(cmd)

print("The following operations have been completed successfully. Goodbye!")
pprint(completedMessages)