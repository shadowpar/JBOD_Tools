from pprint import pprint

def print_disk_list(inventory,singlepath=False):
    for chassis in inventory:
        printedAlready = False
        print('\n\nEnclosures inside the chassis with serial number:',chassis ,'and logical ID:',inventory[chassis]['logicalid'])
        for encl_sg_name in inventory[chassis]['iomodules']:
            if singlepath and printedAlready:
                continue
            print('\n-----------------------------Start of disks in enclosure', encl_sg_name
                  ,'----------------------------------------------------\n')
            print('|' + 'Index'.center(5) + '|' + 'Slot'.center(5) + '|' + 'Disk Name'.center(10) + '|' + 'Multipath Device'.center(16) + '|' + 'RAID Partition'.center(18) + '|' + 'md RAID'.center(7) + '|'+ 'RAID role'.center(17)+'|'+ 'SAS Address'.center(19)+'|'+'Ident'.center(7)+'|')
            # for idx in self.drive_dict:
            for attributes in inventory[chassis]['iomodules'][encl_sg_name]['disks']:
                for item in attributes:
                    if attributes[item] is None:
                        attributes[item] = 'error'
                try:
                    print(''.ljust(113, '-'))
                    col1 = str(attributes['index'])
                    col2 = str(attributes['slot']).lstrip('0')
                    if col2 == '':
                        col2 = '0'
                    col3 = str(attributes['name'])
                    col4 = str(attributes['mpathdmname'] + '/' + attributes['mpathname'])
                    col5 = str(attributes['dmraidpart'] + '/' + attributes['dmraidpartname'])
                    col6 = str(attributes['mdparent'])
                    col7 = str(attributes['raidrole'])
                    col8 = str(attributes['sasaddress'])
                    if(attributes['ident'] == '1'):
                        col9 = "True"
                    else:
                        col9 = "False"
                    print('|' + col1.center(5) + '|' + col2.center(5) + '|' + col3.center(10) + '|' + col4.center(
                        16) + '|' + col5.center(18) + '|' + col6.center(7) + '|' + col7.center(17) + '| '+ col8.center(18) + '|'+col9.center(7)+'|')
                except Exception as e:
                    print('There was an error printing this disk list')
                    pprint(attributes)
                    print(e.args)
                    print(e)
            print(''.ljust(113, '-'))
            printedAlready = True