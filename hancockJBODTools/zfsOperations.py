from pprint import pprint
from pathlib import Path
import subprocess

def parseZfsConfigBranch(branchText: str):
    headerloc = branchText.find(":\n")
    if headerloc != -1:
        print("Recurse again ",headerloc+2,"with string of length",len(branchText[headerloc+2:]),"and header value",branchText[:headerloc])
        return {branchText[:headerloc]:parseZfsConfigBranch(branchText=branchText[headerloc+2:])}
    else:
        print("not recursing this time.",branchText)
        lines = branchText.splitlines()
        data = {}
        for line in lines:
            linedata = line.strip().split(":")
            data[linedata[0].strip()] = linedata[1].strip()
        return data



def parseZDBout():
    cmd = ['zdb']
    proc = subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if proc.returncode == 127:
        print("zdb command not found")
        return None
    elif proc.returncode != 0:
        print("Unknown error occured. Cannot parse ZDB output.")
        print(proc.stderr.decode())
        return None
    data = proc.stdout.decode()
    jdata = {}
    jdata = parseZfsConfigBranch(branchText=data)
    pprint(jdata)


parseZDBout()






