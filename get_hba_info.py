#!/usr/bin/python3
import subprocess
from pathlib import Path, PosixPath
from pprint import pprint
from subprocess import run, PIPE

#type can be either SAS or FC
def get_hbas(hbatype):
    options = {'FC':Path('/sys/class/fc_host'),'SAS':Path('/sys/class/sas_host')}
    if hbatype not in options:
        print("You must provide one of the following types when calling this function.",options)
        return None
    leads = {}
    hbahostsdir = options[hbatype]
    if not hbahostsdir.is_dir():
        print("No Fibre Channel HBAs detected.")
        return None
    hbas = {item.name:item.resolve() for item in hbahostsdir.iterdir()}

    for hba in hbas:
        lead = Path(hbas[hba].as_posix().split(hba)[0])
        if lead in leads:
            leads[lead]['hbas'].append(hba)

            continue

        leads[lead] = {'lead':lead,'hba_hosts':[hba],'physicalslot':None}
        parts = list(lead.parts)
        while leads[lead]['physicalslot'] is None:
            pciaddr = parts[-1]
            if 'pci' in pciaddr:
                print("Unable to find physical slot for this lead: ",lead)
                break
            else:
                command = ['lspci','-v','-s',pciaddr]
                proc = subprocess.run(command,stdout=PIPE,stderr=PIPE)
                if proc.returncode != 0:
                    print("There was a problem running: ",command)
                    return None
                results = proc.stdout.decode().splitlines()
                for line in results:
                    if 'physical slot' in line.lower():
                        leads[lead]['physicalslot'] = line.strip()
                        break
                parts.pop()
    if leads == {}:
        return None
    else:
        return leads

def getfcdata(lead=Path('/'),hbahost='randommess'):
    infopath = lead.joinpath(hbahost).joinpath('fc_host').joinpath(hbahost)
    if not infopath.is_dir():
        return None
    stats = ['port_id','port_name','port_type','speed','supported_speeds']
    data = {stat:None for stat in stats}
    for stat in data:
        try:
            statdata = infopath.joinpath(stat).read_text().strip()
            data[stat] = statdata
        except FileNotFoundError as e:
            pass
        except Exception as t:
            print(t)
    return data

def compareDisksToHBAs(hbalookup=None):
    if hbalookup is None:
        return None
    disksByPhysicalSlot = {hbalookup[lead]['physicalslot']:{} for lead in hbalookup}
    sd = [item.resolve() for item in Path('/sys/block').glob('sd*')]
    for scsidisk in sd:
        for lead in hbalookup:
            try:
                tail = scsidisk.relative_to(lead)
                fcdata = getfcdata(lead=lead,hbahost=tail.parts[0])
                if fcdata is None:
                    disksByPhysicalSlot[hbalookup[lead]['physicalslot']][scsidisk.name] = tail
                else:
                    disksByPhysicalSlot[hbalookup[lead]['physicalslot']][scsidisk.name] = fcdata
            except Exception as e:
                pass
    return disksByPhysicalSlot

fcres = get_hbas("FC")
sasres = get_hbas("SAS")

print("\n----------------------Results of SAS devices---------------------------------------------")
result = compareDisksToHBAs(hbalookup=sasres)
pprint(result)
if result is not None:
    for item in result:
        print(item,"has this many disks attached to it",len(result[item]))
print("\n----------------------Results of Fibre Channel devices---------------------------------------------")
result = compareDisksToHBAs(hbalookup=fcres)
pprint(result)
