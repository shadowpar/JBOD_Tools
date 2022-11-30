#!/usr/bin/python3.6
from hancockJBODTools import storage_info, print_disk_list
import subprocess
from pprint import pprint


class disk_tuner():
    def __init__(self):
        self.sysctl_settings = {'vm.dirty_background_bytes':'0', 'vm.dirty_bytes':'0', 'vm.dirty_expire_centisecs':'3000', 'vm.dirty_ratio':'40', 'vm.dirty_writeback_centisecs':'500', 'vm.swappiness':'10'}
                # Dictionary that holds  the mapping between sysctl setting name and value
        self.storage = storage_info()
        self.tune_up_system()
        self.tune_up_mds()
        self.tune_up_drives()

    def tune_up_system(self):
        for setting in self.sysctl_settings:
            command = 'sysctl -w ' + setting + '=' + self.sysctl_settings[setting]
            subprocess.call(command, shell=True)
        command = 'tuned-adm profile throughput-performance'
        subprocess.call(command,shell=True)

    def tune_up_drives(self):
        for chassis in self.storage.chassis:
            for iomod in storage.chassis[chassis]['iomodules']:
                for disk in self.storage.chassis[chassis]['iomodules'][iomod]['disks']:
                    try:
                        friendlyname = disk['friendlyname']
                        with open('/sys/block/'+friendlyname+'/queue/nr_requests','w') as f:
                            f.write('2048')
                        with open('/sys/block/'+friendlyname+'/queue/read_ahead_kb', 'w') as f:
                            f.write('8192')
                    except Exception as e:
                        print(e)

    def tune_up_mds(self):
        for md in self.storage.raidInfoMapper:
            with open('/sys/block/'+md+'/md/stripe_cache_size','w') as f:
                f.write('32768')




storage = storage_info()
chassis = list(storage.chassis.keys())[0]
iomod = list(storage.chassis[chassis]['iomodules'].keys())[0]

for disk in storage.chassis[chassis]['iomodules'][iomod]['disks']:
    pprint(disk)
for md in storage.raidInfoMapper:
    pprint(md)

tuner = disk_tuner()
