from pathlib import Path
import subprocess
import os


# def getmdRAIDinfo(mdname):
#     try:
#         memberInfo = {}
#         blockpath = Path('/sys/block')
#         mdpath = blockpath / mdname / 'md'
#         if mdpath.exists():
#             members = mdpath.glob("dev-*")
#         else:
#             return (False,'md does not exist.')
#         for item in members:
#             membername = item.joinpath('block').resolve().name
#             memberInfo[membername] = {}
#             with item.joinpath('state').open(mode='r') as f:
#                 state = f.read().strip()
#                 memberInfo[membername]['state'] = state
#             with item.joinpath('slot').open(mode='r') as f:
#                 raidrole = f.read().strip()
#                 memberInfo[membername]['raidrole'] = raidrole
#         return (True,memberInfo)
#     except Exception as e:
#         print("There was an error getting information about raid ",mdname)
#         return (False,e)

def getmdRAIDinfo(mdname):
    try:
        memberInfo = {'components':{}}
        blockpath = Path('/sys/block')
        mdpath = blockpath / mdname / 'md'
        if mdpath.exists():
            members = mdpath.glob("dev-*")
        else:
            return (False,'md does not exist.')
        for item in members:
            membername = item.joinpath('block').resolve().name
            memberInfo['components'][membername] = {}
            with item.joinpath('state').open(mode='r') as f:
                state = f.read().strip()
                memberInfo['components'][membername]['state'] = state
            with item.joinpath('slot').open(mode='r') as f:
                raidrole = f.read().strip()
                memberInfo['components'][membername]['raidrole'] = raidrole
        #gather other properties about the RAID array aside from its member components.
        memberInfo['chunksize'] = mdpath.joinpath('chunk_size').read_text().strip()
        return (True,memberInfo)
    except Exception as e:
        print("There was an error getting information about raid ",mdname)
        return (False,e)

def getAllRaidInfo():
    raidpath = Path('/sys/block').glob("md*")
    targets = [target.name for target in raidpath]
    raidinfo = {}
    for target in targets:
        result = getmdRAIDinfo(target)
        if result[0]:
            raidinfo[target] = result[1]
        elif not result[0]:
            print("There was an issue running getmdRAID info against target",target)
    return raidinfo

def wipeRAIDsuperblock(mdraidpart):
    outputQueue = []
    command = ['mdadm','--zero-superblock','/dev/'+mdraidpart]
    outputQueue.append(command)
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=30)
    output = result.stdout.decode("UTF-8")
    outputQueue.append(output)
    #check if wiping raid superblock succeeded
    command = ['mdadm','-E','/dev/'+mdraidpart]
    command = ['mdadm','--zero-superblock','/dev/'+mdraidpart]
    outputQueue.append(command)
    result = subprocess.run(command,stdout=subprocess.PIPE,timeout=30)
    output = result.stdout.decode("UTF-8")
    outputQueue.append(output)
    if 'No md superblock detected' in output:
        print("Succesfully wiped md raid superblock.")
        return (True,outputQueue)
    else:
        return (False,outputQueue)





