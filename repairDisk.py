#!/usr/bin/python3.6
import os, re,subprocess

from hancockJBODTools import getYoungestChild, getMDparent
from pathlib import Path
from pprint import pprint
from hancockJBODTools import print_disk_list, getmdRAIDinfo, wipeRAIDsuperblock
from hancockJBODTools import storage_info

class repairDisk(object):
    def __init__(self,command_line=True):
        self.storage_info_obj = storage_info()
        self.gatherFreshInformation()
        print("command line is",command_line)
        if command_line:
            print("entering command line is true")
            self.mainmenu()
        else:
            print("Entering command line is false.")
            pass

    def gatherFreshInformation(self):
        self.storage_info_obj.updateData()

    def mainmenu(self):
        os.system("clear")
        choices = {'1': '1) Prepare Disk For Removal and Replacement.',
                   '2': '2) Prepare Replaced Disk and Add to RAID Array.', '3': '3) Manual Disk Operations.',
                   '4': '4) LED Operations.', '5': '5) Exit'}
        actions = {'1': self.completeRemovalMenu, '2': self.completeRestoreMenu, '3': print, '4': self.diskLEDMenu,'5':-1}
        while True:
            print("\nWelcome to the Main Menu.".center(os.get_terminal_size()[0]))
            print('\n\n')
            for item in list(choices.keys()):
                print(choices[item])
            choice = str(input("Choose your desired operation or submenu.\n"))
            if choice not in list(choices.keys()):
                print("\nYou entered an invalid entry. Please try again.\n")
            else:
                result = actions[choice]
                if callable(result):
                    result()
                elif result == -1:
                    print("\nThanks for playing.\n")
                    break

    def diskLEDMenu(self):
        choices = {'1':"1) Show LED Status Menu",'2':"2) Turn off LEDs Menu",'3':"3) Turn on LEDs Menu",'4':"4) Return to Previous Menu"}
        actions = {'1':self.showLEDstatusMenu,'2':self.turnOffLEDsMenu,'3':self.turnOnLEDsMenu,'4':-1}
        while True:
            print("\nWelcome to the Disk LED Menu.\n")
            for choice in choices.values():
                print(choice,'\n')
            choice = input("Please select a submenu from the above choices. Enter the number corresponding to your choice.\n")
            choice = choice.strip()
            if choice not in choices:
                print("\nThat is not a valid choice. Please try again.\n")
                continue
            if actions[choice] == -1:
                return
            else:
                actions[choice]()
                continue

    def showLEDstatusMenu(self):
        choices = {'1':'1) Show all LED statuses.','2':'2) Show energized LEDs.','3':'3) Show deenergized LEDs.',
                   '4':'4) Get LED status for a specific drive by typing the name.','5':'5) Get LED status for a specific drive by using menus.','6':'6) Return to the previous menu.'}
        actions = {'1':self.refreshandprint,'2':self.storage_info_obj.getEnergizedLEDs,'3':self.storage_info_obj.getEnergizedLEDs,'4':print,
                   '5':print,'6':-1}

        while True:
            print("\nWelcome to the Disk LED Status Menu.\n")
            for choice in choices.values():
                print(choice,'\n')
            choice = input("Please select a submenu from the above choices. Enter the number corresponding to your choice.\n")
            choice = choice.strip()
            if choice not in choices:
                print("\nThat is not a valid choice. Please try again.\n")
                continue
            if actions[choice] == -1:
                return
            elif choice == '1':
                actions[choice]()
            elif choice == '2':
                actions[choice](invert=False,show=True)
            elif choice == '3':
                actions[choice](invert=True,show=True)
            elif choice == '4':
                target = input("Please type the name of the device on which you want to view LED status.\n").strip()
                self.getSDchildrenLEDstatus(target=target)
            elif choice == '5':
                actions[choice]('NOT YET IMPLEMENTED!')

    def getSDchildrenLEDstatus(self,target,show=False):
        if target not in self.storage_info_obj.diskview:
            return (False,'Not a valid block device.')
        else:
            targets = self.storage_info_obj.getAllSDchildren(name=target,unique=True)
        blinking = self.storage_info_obj.getEnergizedLEDs(invert=False, show=False)
        nonblinking = self.storage_info_obj.getEnergizedLEDs(invert=True, show=False)
        ledstatusbyname = {}

        print("\nThe following drives have at least one LED illuminated.\n")
        count = 1
        for target in targets:
                if target in blinking:
                    print(str(count)+") ",target,blinking[target],"\n")
                    ledstatusbyname[target] = blinking[target]
                    count = count +1
        print("\nThe following drives have their LEDs off.\n")
        count = 1
        for target in targets:
                if target in nonblinking:
                    print(str(count)+") ",target,"\n")
                    ledstatusbyname[target] = nonblinking[target]
                    count = count +1
                if target not in ledstatusbyname:
                    ledstatusbyname[target] = {'ident':None,'fault':None}
        return (ledstatusbyname)

    def turnOffLEDsMenu(self):
        print("Put turn off the LEDs menu here.")
        return

    def turnOnLEDsMenu(self):
        choices = {'1':"1) Show list of all disk information",'2':"2) Enter a name that represents the disk or partition.",'3':"3) Select disk using menus.",'4':'4) Go to previous menu.'}
        while True:
            choice = input("Which would you like to do?\n1) List all disks and their current LED status.\n2) Type the name of a disk. 3) Select a disk from a menu of those currently deenergized.\n4) Return to the previous menu.\n")
            choice = str(choice).strip()
            if choice not in choices:
                print("I'm sorry but that is not a valid option. Make sure you are entering a number from the menu.")
                continue
            if choice == '1':
                self.refreshandprint()
                continue
            elif choice == '2':
                self.manualNameEnter()

    def completeRestoreMenu(self):
        choices = {'1':"1) Show list of all disk information",'2':"2) Enter a name that represents the disk or partition.",'3':"3) Select disk using menus.",'4':'4) Go to previous menu.'}
        actions = {'1':self.refreshandprint,'2':self.manualNameEnter,'3':self.storage_info_obj.selectItemUsingMenus,'4':-1}
        while True:
            print("Welcome to the restore replacement disk menu.".center(os.get_terminal_size()[0]))
            print('\n\n')
            for item in list(choices.keys()):
                print(choices[item])
            choice = str(input("Choose your desired operation or submenu.\n"))
            if choice not in list(choices.keys()):
                print("Invalid Selection please try again.")
                continue
            else:
                result = actions[choice]
                if result == self.refreshandprint:
                    self.refreshandprint()
                elif result == self.manualNameEnter:
                    self.manualNameEnter(action='completeRestore')
                elif result == self.storage_info_obj.selectItemUsingMenus:
                    sdchoice = self.storage_info_obj.selectItemUsingMenus(selectType='sdNotRAID')
                    if not sdchoice[0]:
                        print("There was an issue selecting items")
                        print(sdchoice[1])
                    else:
                        self.manualNameEnter(action='completeRestore',name=sdchoice[1])
                elif result == -1:
                    return 0

    def completeRemovalMenu(self):
        os.system("clear")
        choices = {'1':"1) Show list of all disk information",'2':"2) Enter a name that represents the disk or partition.",'3':"3) Select disk using menus.",'4':'4) Go to previous menu.'}
        actions = {'1':self.refreshandprint,'2':self.manualNameEnter,'3':self.storage_info_obj.selectItemUsingMenus,'4':-1}
        while True:
            print("Welcome to the Prepare for Removal Menu .".center(os.get_terminal_size()[0]))
            print('\n\n')
            for item in list(choices.keys()):
                print(choices[item])
            choice = str(input("Choose your desired operation or submenu.\n"))
            if choice not in list(choices.keys()):
                print("Invalid Selection please try again.")
                continue
            else:
                result = actions[choice]
                if result == self.refreshandprint:
                    self.refreshandprint()
                elif result == self.manualNameEnter:
                    self.manualNameEnter(action='completeRemoval')
                elif result == self.storage_info_obj.selectItemUsingMenus:
                    mdchoice = self.storage_info_obj.selectItemUsingMenus(selectType='mdparent')
                    if not mdchoice[0]:
                        print("There was an issue selecting items")
                        print(mdchoice[1])
                    else:
                        sdchoice = self.storage_info_obj.selectItemUsingMenus(selectType='sdRAID',filters={'mdparent':mdchoice[1]})
                        if not sdchoice[0]:
                            print("There was an issue selecting items")
                            print(mdchoice[1])
                        else:
                            self.manualNameEnter(action='completeRemoval',name=sdchoice[1])
                elif result == -1:
                    return 0

    def manualNameEnter(self,action,name=None):
        print("I was passed the action",action)
        actions = {'completeRemoval':self.prepareAndRemoveDisk,'completeRestore':self.completeReplace,'turnOnLED':self.setDriveBlinking,'turnOffLED':self.clearDriveBlinking}
        if action not in actions:
            return None
        try:
            if name is None:
                messages = {'completeRemoval':"\nPlease type one of the representative names for the device you want to prepare for removal. i.e. sdy, dm-38, etc.\n",
                            'completeRestore':"\nPlease type the name for the device you want to prepare and add to RAID array. i.e. sdy, dm-38, etc.\n"}
                name = input(messages[action])
                name = name.strip().split('/')[-1].lower()
            self.storage_info_obj.updateData()
            if name not in self.storage_info_obj.diskview:
                print("That is not a block device on this system.")
                return None
            try:
                devtype = self.storage_info_obj.diskview[name]['devtype']
                if devtype == 'md':
                    result = True
                else:
                    result = False
            except KeyError:
                print("That is not a block device on this system.")
                return None
            except Exception as e:
                print("There was an unknown exception in manualNameEnter.")
                print(e)
                return None
            if result:
                print("This function cannot accept md device names because these are not unique to a physical hard drive on the system.")
                return None
            else:
                child = getYoungestChild(name)
                if child is None:
                    print("There was an error trying to find the youngest child in the hiearchy.")
                    return None
                else:
                    complete = actions[action](child)
                    # complete = self.prepareAndRemoveDisk(child=child)
                    if complete[0]:
                        print("It is done.")
                        print(complete[1])
                    else:
                        print("Something went wrong in the automagic machinery.")
                        print(complete[1])

        except Exception as e:
            print("There was a problem trying to manually enter name. make sure you are entering the kernel name of an sd device, a multipath device, or a RAID partition.")
            print(e)
            return None
    def completeReplace(self,child):
        print("Enter complete replace")
        outputQueue = []
        #first make sure the disk is not currently in a RAID array or mounted anywhere.
        self.storage_info_obj.updateData()
        if child not in self.storage_info_obj.diskview:
            print("Not a valid block device.")
            return (False,'This does not appear to be a valid block device.')
        mdparent = self.storage_info_obj.diskview[child]['mdparent']
        dmraidpart = self.storage_info_obj.diskview[child]['dmraidpart']
        mpathdmname = self.storage_info_obj.diskview[child]['mpathdmname']
        if mdparent is not None:
            print("This device is already part of the RAID array",mdparent," Unable to continue.")
            return (False,['This device is already part of a RAID array.'])
        if dmraidpart is None and mpathdmname is not None: #handles the common case where there disk is already part of a multipath device but otherwise ready to setup.
            print("Detected that ",child,"is already part of a multipath device but has not RAID partition.")
            print("Attempting to flush multipath device.")
            result = self.flushMultipath(child)
            if not result[0]:
                print("Failed to flush multipath device")
                print(result[1])
                return (False,['Failed to flush existing multipath device.'])

        #begin the main work of preparing the disk.
        print("Entering mainloop completeReplace")
        self.storage_info_obj.updateData()
        choices = {str(x):y for x,y in enumerate(self.storage_info_obj.raidInfoMapper.keys())}
        pprint(choices)
        choices[str(len(choices))] = "Cancel"
        while True:
            print("Entering while loop of choices in completeReplace.")
            for choice in choices:
                print(choice,')',choices[choice])
            userchoice = input("Please select the RAID array you want to add to from the list above by entering its number.")
            if userchoice not in choices:
                print("That is not a valid choice.")
                continue
            elif choices[userchoice] == "Cancel":
                return (False,['User cancelled instead of selecting a target RAID array'])
            else:
                break
        targetMD = choices[userchoice]

        try:
            command = ['parted','-s','/dev/'+child,'mklabel','gpt']
            outputQueue.append(command)
            output = subprocess.run(command,stdout=subprocess.PIPE).stdout
            outputQueue.append(output)
            command = ['parted', '-s', '/dev/'+child,'-a','optimal','unit','MB','mkpart','primary','1','100%','set','1','hidden','on']
            outputQueue.append(command)
            output = subprocess.run(command, stdout=subprocess.PIPE).stdout
            outputQueue.append(output)
            self.storage_info_obj.updateData()
            expectedNewpart = child+'1'
            if expectedNewpart not in self.storage_info_obj.diskview:
                print("Failed to create new partition on disk using parted. Please manually investigate")
                return (False,outputQueue)
            command = ['multipath']
            outputQueue.append(command)
            output = subprocess.run(command,stdout=subprocess.PIPE).stdout
            outputQueue.append(output)
            self.storage_info_obj.updateData()
            if self.storage_info_obj.diskview[child]['mpathdmname'] is None:
                print("There was an error creating the multipath device for ",child)
                return (False,outputQueue)
            self.storage_info_obj.updateData()
            dmraidpart = self.storage_info_obj.diskview[child]['dmraidpart']
            if dmraidpart is None:
                print("There was an error finding out the name of the partition on top of the multipath device.")
                print("Please investigate manually.")
                return (False,outputQueue)
            command = ['mdadm','--add-spare','/dev/'+targetMD,'/dev/'+dmraidpart]
            outputQueue.append(command)
            output = subprocess.run(command, stdout=subprocess.PIPE).stdout
            outputQueue.append(output)
            self.storage_info_obj.updateData()
            mdparent = self.storage_info_obj.diskview[child]['mdparent']
            if mdparent is None:
                print("There was an issue adding ",dmraidpart,"as a spare to ",targetMD)
                print("Please investigate manually.")
                return (False,outputQueue)
            else:
                print(dmraidpart,"was successfully added to",mdparent)
            print("Ensuring that the fault and locate LEDs are turned off.")
            result = self.clearDriveBlinking(name=child)
            if not result[0]:
                return (False,'Everything else is done, but I was unable to stop the light from blinking on the drive. See below:\n'+result[1])
            else:
                print("The drive ",child,"has been added to ",self.storage_info_obj.diskview[child]['mdparent'],"and the fault/locator lights have been turned off.")
                return (True,"The drive ",child,"has been added to ",self.storage_info_obj.diskview[child]['mdparent'],"and the fault/locator lights have been turned off.")



        except Exception as e:
            print("There was an issue with the automatic complete Replace")
            outputQueue.append(e)
            return (False,outputQueue)


    def prepareAndRemoveDisk(self,child): #
        result = self.smartRemoveRAIDmember(child=child)
        if not result[0]:
            print("Failed at removing the RAID member. Manual intervention is required.")
            return result
        else:
            print("Succeeded at removing RAID member")
            print("Trying to wipe the RAID superblock off RAID partition.")
            try:
                result = wipeRAIDsuperblock(self.storage_info_obj.diskview[child]['dmraidpart'])
                if not result[0]:
                    print("I was unable to wipe the raid superblock from ",child,"but this process will continue.")
            except Exception as e:
                print("There was an issue wiping the RAID superblock but the process of removing,"+child+"will continue.")
                print(e)
            result = self.flushMultipath(child=child)
            if not result[0]:
                print("Failed at flushing the multipath map. Disk is already removed from RAID.")
                return result
            else:
                print("Succeeded in flushing the multipath map.")
                result = self.setDriveBlinking(name=child)
                if not result[0]:
                    print("There was an issue setting the disk to blinking.")
                    return result
                else:
                    return (True,'The disk is ready for withdrawal')

    def smartRemoveRAIDmember(self,child):
        output = 'NO recorded output smartRemove RAID member'
        # diskview = getBlockDevInfo([child], diskview=True)
        self.storage_info_obj.updateData()
        attrs = self.storage_info_obj.diskview[child]
        if attrs['mdparent'] is not None:
            print("Entering determine raid role disk")
            print("md parent is ",attrs['mdparent'])
            mdmemberInfo = getmdRAIDinfo(attrs['mdparent'])
            if mdmemberInfo[0]:
                mdmemberInfo = mdmemberInfo[1]
                memberstatus = mdmemberInfo['components'][attrs['dmraidpart']]['state']
            else:
                return (False,"There was an error determineing the raid member status")
            if memberstatus == 'spare':
                print("it seems that member status is spare")
                output = self.removeRAIDmember(attrs=attrs)
            elif memberstatus == 'faulty':
                print("It seems that member status is faulty")
                output = self.removeRAIDmember(attrs=attrs)
            else:
                while True:
                    self.refreshandprint()
                    print("This disk does not appear to be marked as faulty or spare.")
                    print("The member is still active in the array as .", memberstatus)
                    verifystring = "Are you sure you want to mark "+attrs['dmraidpart']+" as faulty and remove it from array "+attrs['mdparent']+"? Please type 'yes' or 'no'"
                    choices = {'yes':True,'no':False}
                    verify = input(verifystring)
                    if verify.lower() not in list(choices.keys()):
                        print("Invalid entry. Please enter 'yes' or 'no'")
                        continue
                    elif choices[verify.lower()]:
                        break
                    elif not choices[verify.lower()]:
                        return(False,'User chose not to continue with operation.')
                output = self.failThenRemoveRAIDmember(attrs=attrs)
        self.storage_info_obj.updateData()
        mdparent = self.storage_info_obj.diskview[child]['mdparent']
        if mdparent is not None:
            print("The smart remove disk utility failed to remove",child,"from",mdparent,'Manual intervention is required.')
            return (False,output)
        else:
            return (True,output)

    def removeRAIDmember(self,attrs=None):
        if attrs is None:
            return False
        else:
            outputQueue = []
            command = ['mdadm','-r','/dev/'+attrs['mdparent'],'/dev/'+attrs['dmraidpart']]
            print("I am executing this command", command)
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)
            return outputQueue

    def failThenRemoveRAIDmember(self,attrs=None):
        if attrs is None:
            return False
        else:
            outputQueue = []
            #first we fail the drive in the raid array so it can be hot removed.
            command = ['mdadm','--fail','/dev/'+attrs['mdparent'],'/dev/'+attrs['dmraidpart']]
            print("I am executing this command", command)
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

            #now we hot remove the drive from the RAID array
            command = ['mdadm','-r','/dev/'+attrs['mdparent'],'/dev/'+attrs['dmraidpart']]
            print("I am executing this command", command)
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)
            return outputQueue

    def destroySuperBlock(self,attrs=None):
        if attrs is not None:
            command = ['dd','if=/dev/zero','of=/dev/'+attrs['name'],'bs=1M','count=2048']
            print("I will execute the following command.",command)

    def refreshandprint(self):
        self.gatherFreshInfomation()
        print_disk_list(inventory=self.storage_info_obj.chassis)

    def flushMultipath(self,child):
        outputQueue = []
        self.storage_info_obj.updateData()
        if self.storage_info_obj.diskview[child]['mpathdmname'] is not None:
            command = ['multipath', '-f', self.storage_info_obj.diskview[child]['mpathname']]
            print("I am executing this command", command)
            outputQueue.append(command)
            proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
            output = proc.stdout.decode("UTF-8").strip()
            outputQueue.append(output)

        self.storage_info_obj.updateData()

        if self.storage_info_obj.diskview[child]['mpathname'] is not None:
            print("The utility failed to flush multipath device", self.storage_info_obj.diskview[child]['mpathname'])
            return (False, outputQueue)  # for temporary non destructive testing.
        else:
            return (True, outputQueue)

    def setDriveBlinking(self,name):
        if name not in self.storage_info_obj.diskview or self.storage_info_obj.diskview[name]['devtype'] != 'sd':
            print("This is not an sd device on the system.")
            return (False, name + ' is not an sd device on the system.')
        else:
            try:
                self.storage_info_obj.updateData()
                outputQueue = []
                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--set', 'ident', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                outputQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)

                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--set', 'fault', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                outputQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)

                lightStatus = self.checkDriveBlinking(name=name)
                if lightStatus[0]:
                    if lightStatus[1] == {'ident': '1', 'fault': '1'}:
                        return (True, outputQueue)
                    else:
                        return (False, outputQueue)
            except Exception as e:
                print("There was an unhandled exception while trying to set blinking lights.")
                print(e)
                return (False, e)

    def checkDriveBlinking(self,name):

        if name not in self.storage_info_obj.diskview or self.storage_info_obj.diskview[name]['devtype'] != 'sd':
            print("This is not an sd device on the system.")
            return (False, "This is not an sd device on the system.")
        else:
            try:
                self.storage_info_obj.updateData()
                result = {'ident': None, 'fault': None}
                commandQueue = []
                outputQueue = []
                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--get', 'ident', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                outputQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)
                if output == '1':
                    result['ident'] = '1'
                elif output == '0':
                    result['ident'] = '0'
                else:
                    return (False, outputQueue)
                # now check the state of the fault field
                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--get', 'fault', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                commandQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)
                if output == '1':
                    result['fault'] = '1'
                elif output == '0':
                    result['fault'] = '0'
                else:
                    return (False, outputQueue)
                return (True, result)
            except Exception as e:
                print("There was an unknown issue checking disk light status")
                return (False, str(e))

    def clearDriveBlinking(self,name):
        if name not in self.storage_info_obj.diskview or self.storage_info_obj.diskview[name]['devtype'] != 'sd':
            print("This is not an sd device on the system.")
            return (False, "This is not an sd device on the system.")
        else:
            try:
                outputQueue = []
                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--clear', 'ident', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                outputQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)

                command = ['sg_ses', '--index=0,' + self.storage_info_obj.diskview[name]['index'], '--clear', 'fault', '/dev/' + self.storage_info_obj.diskview[name]['enclosure']]
                outputQueue.append(command)
                proc = subprocess.run(command, stdout=subprocess.PIPE, timeout=30)
                output = proc.stdout.decode("UTF-8").strip()
                outputQueue.append(output)

                lightStatus = self.checkDriveBlinking(name=name)
                if lightStatus[0]:
                    if lightStatus[1] == {'ident': '0', 'fault': '0'}:
                        return (True, outputQueue)
                    else:
                        return (False, outputQueue)
            except Exception as e:
                print("There was an unhandled exception while trying to clear blinking lights.")
                return (False, e)

# myrepair = repairDisk()




