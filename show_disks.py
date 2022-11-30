#!/usr/bin/python3.6

from hancockJBODTools import storage_info, print_disk_list
from pprint import pprint
from sys import argv
from subprocess import TimeoutExpired

kwargs = {}
if len(argv) > 1:
    params = argv[1:]
    kwargs = {param.split('=')[0]:int(param.split('=')[1]) for param in params if '=' in param}
    lswitches = [param for param in params if param.startswith('--')]
    sswitches = [param for param in params if param.startswith('-') and len(param) == 2]
    if '--debug' in lswitches:
        print("I detected the following keyword params.")
        print("kwargs")
        pprint(kwargs)
        print('Long switches')
        pprint(lswitches)
        print('Short Switches')
        pprint(sswitches)
else:
    kwargs = {}
    lswitches = []
    sswitches = []
try:
    if 'timeout' in kwargs:
        storage = storage_info(timeout=kwargs['timeout'])
    else:
        storage = storage_info()
    if '--unique' in lswitches:
        print_disk_list(storage.chassis,singlepath=True)
    else:
        print_disk_list(storage.chassis)
except TimeoutExpired as t:
    print(t)
    print("\nYour SES controlleres are taking forever to respond. The default timeout is 60 seconds. Try increasing this value to 90 seconds or more and get some popcorn.")
    print("\nYou can increase this timeout value (in seconds) by passing a keyword argument to ./show_disks.py such as : ./show_disks.py timeout=90 ")

