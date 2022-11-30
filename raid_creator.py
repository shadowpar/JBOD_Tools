#!/usr/bin/python3.6

from hancockJBODTools import storage_info, print_disk_list
import subprocess
from pprint import pprint
from pathlib import Path

storage = storage_info()
chassis = list(storage.chassis.keys())[0]
iomod = list(storage.chassis[chassis]['iomodules'].keys())[0]

raidgroups = {}
changed = False


def createLabel(name):
    command = ['parted', '-s','/dev/'+name, 'mklabel', 'gpt']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("The return code was ", proc.returncode)
    print(proc.stdout.decode())
    print(proc.stderr.decode())


def createRAIDpart(name):
    command = ['parted', '-s', '/dev/' + name, '-a', 'optimal', 'unit', 'MB', 'mkpart', 'primary', '1', '100%', 'set',
               '1', 'hidden', 'on']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("The return code was ", proc.returncode)
    print(proc.stdout.decode())
    print(proc.stderr.decode())

def createRAID6Array(partitions,raidname):
    print("Entering createRAID6Array")
    if len(partitions) == 0:
        print("not a valid array of RAID partitions")
        return
    numDisks = len(partitions)
    partString = ""
    for part in partitions:
        partString = partString+"/dev/"+part+" "
    if Path('/bitmap').is_dir():
        command = ['mdadm','-v','--create','/dev/'+raidname,'--level=6','--raid-devices='+str(numDisks),'--bitmap=/bitmap/'+raidname]
    else:
        command = ['mdadm','-v','--create','/dev/'+raidname,'--level=6','--raid-devices='+str(numDisks)]
    for part in partitions:
        command.append('/dev/'+part)
    print(command)
    proc = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print(proc.stdout.decode())
    print(proc.stderr.decode())


for disk in storage.chassis[chassis]['iomodules'][iomod]['disks']:
    if disk['dmraidpart'] is None:
        name = disk['friendlyname']
        print("Trying to format",name)
        createLabel(name)
        createRAIDpart(name)
        changed = True
if changed:
    command = ['multipath','-F']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        print(line)
    for line in proc.stderr:
        print(line)
    command = ['multipath']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        print(line)
    for line in proc.stderr:
        print(line)
storage = storage_info()
raidsize=10
parity = 2
count = 0
mdcount = 0
partitions = []
for disk in storage.chassis[chassis]['iomodules'][iomod]['disks']:
    if disk['dmraidpart'] is not None:
        index = int(disk['index'])
        dmraidpart = disk['dmraidpart']
        print("Trying to work on ",dmraidpart)
        if count < raidsize:
            partitions.append(dmraidpart)
            print("count is ",count)
            count = count + 1
        elif count == raidsize:
            print("trying to create a raid array.")
            createRAID6Array(partitions=partitions,raidname='md'+str(mdcount))
            partitions = []
            partitions.append(dmraidpart)
            count = 1
            mdcount = mdcount + 1




