from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

utcoffset = -5

Base = declarative_base()


class staticheadnode(Base):
    __tablename__ = 'staticheadnodes'
    id = Column(Integer, primary_key=True)
    name = Column('name', String(32), unique=True)
    rack = Column('rack', String(5))
    slot = Column('slot', Integer)
    datacenter = Column('datacenter', String(32))
    experiment = Column('experiment', String(32))

    def __init__(self, name, rack='error', slot=0, datacenter='error', experiment='error'):
        self.name = name
        self.rack = rack
        self.slot = slot
        self.datacenter = datacenter
        self.experiment = experiment


class staticjbod(Base):
    __tablename__ = 'staticjbods'
    id = Column(Integer, primary_key=True)
    staticheadnode = Column(Integer, ForeignKey('staticheadnodes.id'))
    name = Column('name', String(32), unique=True)
    rack = Column('rack', String(5))
    slot = Column(Integer)
    datacenter = Column('datacenter', String(32))
    model = Column('model', String(32))
    numslots = Column(Integer)

    def __init__(self, staticheadnode, name, datacenter='error', rack='error', slot=-1, model='error', numslots=-1):
        self.staticheadnode = staticheadnode
        self.name = name
        self.rack = rack
        self.slot = slot
        self.numslots = numslots
        self.model = model
        self.datacenter = datacenter


class managementinterface(Base):
    __tablename__ = 'managementinterfaces'
    id = Column(Integer, primary_key=True)
    name = Column('name', String(32))
    staticheadnode = Column(Integer)
    staticjbod = Column(Integer)

    def __init__(self, name, staticheadnode=-1, staticjbod=-1):
        self.name = name
        self.staticheadnode = staticheadnode
        self.staticjbod = staticjbod


class cpu(Base):
    __tablename__ = 'cpus'
    id = Column(Integer, primary_key=True)
    model = Column('model', String(50), unique=True)
    architecture = Column('architecture', String(10))
    bogomips = Column('bogomips', Float)
    byteorder = Column('byteorder', String(15))
    numcores = Column(Integer)
    cpufreqmhz = Column(Float)
    opmodes = Column('opmodes', String(20))
    l1dcache = Column('l1dcache', String(10))
    l1icache = Column('l1icache', String(10))
    l2cache = Column('l2cache', String(10))
    l3cache = Column('l3cache', String(10))
    threadspercore = Column(Integer)
    vendor = Column('vendor', String(32))
    virtualization = Column('virtualization', String(20))
    modified = Column('modified', DateTime)

    def __init__(self, model=None, architecture='error', bogomips=-1, byteorder='error', numcores=-1, cpufreqmhz=-1,
                 opmodes='error', l1dcache='error', l1icache='error', l2cache='error', l3cache='error',
                 threadspercore=-1, vendor='error', virtualization='error', modified=datetime.utcnow()):
        self.model = model
        self.architecture = architecture
        self.bogomips = bogomips
        self.byteorder = byteorder
        self.numcores = numcores
        self.cpufreqmhz = cpufreqmhz
        self.opmodes = opmodes
        self.l1dcache = l1dcache
        self.l1icache = l1icache
        self.l2cache = l2cache
        self.l3cache = l3cache
        self.threadspercore = threadspercore
        self.vendor = vendor
        self.virtualization = virtualization
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'model': self.model, 'architecture': self.architecture, 'bogomips': self.bogomips,
                      'byteorder': self.byteorder, 'numcores': self.numcores, 'cpufreqmhz': self.cpufreqmhz,
                      'opmodes': self.opmodes, 'l1dcache': self.l1dcache, 'l1icache': self.l1icache,
                      'l2cache': self.l2cache, 'l3cache': self.l3cache, 'threadspercore': self.threadspercore,
                      'vendor': self.vendor, 'virtualization': self.virtualization,
                      'modified': self.modified - utcoffset}
        return properties


class headnode(Base):
    __tablename__ = 'headnodes'
    id = Column(Integer, primary_key=True)
    name = Column('name', String(32), unique=True)
    cpu = Column(Integer)
    model = Column('model', String(32))
    datacenter = Column('datacenter', String(32))
    rack = Column('rack', String(5))
    slot = Column('slot', Integer)
    experiment = Column('experiment', String(32))
    numsockets = Column(Integer)
    numtotalthreads = Column(Integer)
    modified = Column('modified', DateTime)
    jbods = relationship("jbod")
    raidarrays = relationship("raidarray")
    harddrives = relationship("harddrive")

    def __init__(self, name, cpu=-1, model='error', datacenter='error', rack='error', slot=-1, experiment='error',
                 numsockets=-1, numtotalthreads=-1, modified=datetime.utcnow()):
        self.name = name
        self.cpu = cpu
        self.model = model
        self.datacenter = datacenter
        self.rack = rack
        self.slot = slot
        self.experiment = experiment
        self.numsockets = numsockets
        self.numtotalthreads = numtotalthreads
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'name': self.name, 'cpu': self.cpu, 'model': self.model, 'datacenter': self.datacenter,
                      'rack': self.rack, 'experiment': self.experiment, 'numsockets': self.numsockets,
                      'numtotalthreads': self.numtotalthreads, 'modified': self.modified - utcoffset}
        return properties


class jbod(Base):
    __tablename__ = 'jbods'
    id = Column(Integer, primary_key=True)
    headnode = Column(Integer, ForeignKey('headnodes.id'))
    name = Column('name', String(32))
    manufacturer = Column('manufacturer', String(32))
    model = Column('model', String(32))
    serialnumber = Column('serialnumber', String(32), unique=True)
    health = Column('health', String(32))
    datacenter = Column('datacenter', String(32))
    rack = Column('rack', String(5))
    slot = Column('slot', Integer)
    numslots = Column('numslots', Integer)
    logicalid = Column('logicalid', String(32))
    managementmaca = Column('managementmaca', String(17))
    managementstatusa = Column('managementlinkstatusa', String(32))
    managementipa = Column('managementipa', String(16))
    managementmacb = Column('managementmacb', String(17))
    managementstatusb = Column('managementlinkstatusb', String(32))
    managementipb = Column('managementipb', String(16))
    modified = Column('modified', DateTime)

    def __init__(self, headnodeid, name, manufacturer='', model='', serialnumber='', health='unknown', datacenter='',
                 rack='', slot=0, numslots=0, logicalid='',
                 managementipa='', managementstatusa='', managementmaca='', managementipb='', managementstatusb='',
                 managementmacb='', modified=datetime.utcnow()):
        self.name = name
        self.model = model
        self.serialnumber = serialnumber
        self.headnode = headnodeid
        self.manufacturer = manufacturer
        self.datacenter = datacenter
        self.health = health
        self.rack = rack
        self.slot = slot
        self.numslots = numslots
        self.logicalid = logicalid
        self.managementmaca = managementmaca
        self.managementipa = managementipa
        self.managementstatusa = managementstatusa
        self.managementmacb = managementmacb
        self.managementipb = managementipb
        self.managementstatusb = managementstatusb
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'name': self.name, 'model': self.model, 'serialnumber': self.serialnumber,
                      'headnode': self.headnode,
                      'manufacturer': self.manufacturer, 'datacenter': self.datacenter, 'health': self.health,
                      'rack': self.rack, 'slot': self.slot,
                      'numslots': self.numslots, 'logicalid': self.logicalid, 'managementmaca': self.managementmaca,
                      'managementipa': self.managementipa,
                      'managementstatusa': self.managementstatusa, 'managementmacb': self.managementmacb,
                      'managementipb': self.managementipb,
                      'managementstatusb': self.managementstatusb, 'modified': self.modified - utcoffset}
        return properties


class raidarray(Base):
    __tablename__ = 'raidarrays'
    id = Column(Integer, primary_key=True)
    headnode = Column(Integer, ForeignKey('headnodes.id'))
    name = Column('name', String(32))
    active = Column('active', Boolean)
    totalnumdisks = Column('totalnumdisks', Integer)
    activenumdisks = Column('activenumdisks', Integer)
    resyncstatus = Column('resyncstatus', String(10))
    raidlevel = Column('raidlevel', Integer)
    bitmapfile = Column('bitmapfile', String(100))
    chunksize = Column('chunksize', String(10))
    alldrivessynced = Column('alldrivessynced', Boolean)
    mountpoint = Column('mountpoint', String(32))
    filesystem = Column('filesystem', String(32))
    size = Column('size', BigInteger)
    uuid = Column('uuid', String(40))
    modified = Column('modified', DateTime)

    def __init__(self, headnodeid, name, active='', totalnumdisks=0, activenumdisks=0, resyncstatus='', raidlevel=0,
                 bitmapfile='', chunksize='', alldrivessynced=False, mountpoint='', filesystem='', size=0, uuid='',
                 modified=datetime.utcnow()):
        self.headnode = headnodeid
        self.name = name
        self.active = active
        self.totalnumdisks = totalnumdisks
        self.activenumdisks = activenumdisks
        self.resyncstatus = resyncstatus
        self.raidlevel = raidlevel
        self.bitmapfile = bitmapfile
        self.chunksize = chunksize
        self.alldrivessynced = alldrivessynced
        self.mountpoint = mountpoint
        self.filesystem = filesystem
        self.size = size
        self.uuid = uuid
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'headnode': self.headnode, 'active': self.active, 'name': self.name,
                      'totalnumdisks': self.totalnumdisks, 'activenumdisks': self.activenumdisks,
                      'resyncstatus': self.resyncstatus,
                      'raidlevel': self.raidlevel, 'bitmapfile': self.bitmapfile, 'chunksize': self.chunksize,
                      'alldrivessynced': self.alldrivessynced, 'mountpoint': self.mountpoint,
                      'filesystem': self.filesystem, 'size': self.size, 'uuid': self.uuid,
                      'modified': self.modified - utcoffset}
        return properties


class harddrive(Base):
    __tablename__ = 'harddrives'
    id = Column(Integer, primary_key=True)
    headnode = Column(Integer, ForeignKey('headnodes.id'))
    # raidarray = Column(Integer, ForeignKey('raidarrays.id'))  #Removed foreign key constraint because disks are not always part of a raid array.
    raidarray = Column(Integer)
    jbod = Column(Integer, ForeignKey('jbods.id'))
    vendor = Column('vendor', String(32))
    model = Column('model', String(32))
    firmware = Column('firmware', String(32))
    name = Column('name', String(32))
    serialnumber = Column('serialnumber', String(32), unique=True)
    temperature = Column(Integer)
    smartstatus = Column('smartstatus', String(32))
    growndefects = Column(Integer)
    uncorrectedreads = Column(Integer)
    uncorrectedwrites = Column(Integer)
    uncorrectedverify = Column(Integer)
    rotationrate = Column(Integer)
    capacity = Column(BigInteger)
    protocol = Column('protocol', String(10))
    health = Column('health', String(32))
    indicatorled = Column(Boolean)
    index = Column(Integer)
    slot = Column(Integer)
    raidarrayrole = Column(Integer)
    modified = Column('modified', DateTime)

    def __init__(self, headnodeid, name, serialnumber, index=0, slot=1, jbodid=None, raidarrayid=None, vendor='',
                 model='', firmware='', temperature=0, smartstatus='', raidarrayrole=-1,
                 growndefects=0, uncorrectedreads=0, uncorrectedwrites=0, uncorrectedverfiy=0, rotationrate=0,
                 capacity=0, protocol='', health='', indicatorled=False, modified=datetime.utcnow()):
        self.headnode = headnodeid
        self.name = name
        self.serialnumber = serialnumber
        self.jbod = jbodid
        self.raidarray = raidarrayid
        self.vendor = vendor
        self.model = model
        self.firmware = firmware
        self.temperature = temperature
        self.smartstatus = smartstatus
        self.growndefects = growndefects
        self.uncorrectedreads = uncorrectedreads
        self.uncorrectedwrites = uncorrectedwrites
        self.uncorrectedverify = uncorrectedverfiy
        self.rotationrate = rotationrate
        self.capacity = capacity
        self.protocol = protocol
        self.health = health
        self.indicatorled = indicatorled
        self.index = index
        self.slot = slot
        self.raidarrayrole = raidarrayrole
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'slot': self.slot, 'serialnumber': self.serialnumber, 'smartstatus': self.smartstatus,
                      'index': self.index,
                      'name': self.name, 'vendor': self.vendor, 'model': self.model, 'firmware': self.firmware,
                      'temperature': self.temperature, 'raidarrayrole': self.raidarrayrole,
                      'growndefects': self.growndefects, 'uncorrectedreads': self.uncorrectedreads,
                      'uncorrectedwrites': self.uncorrectedwrites, 'uncorrectedverify': self.uncorrectedverify,
                      'rotationrate': self.rotationrate, 'capacity': self.capacity, 'protocol': self.protocol,
                      'health': self.health, 'indicatorled': self.indicatorled, 'modified': self.modified - utcoffset,
                      'raidarray': self.raidarray}
        return properties


class logicaldisk(Base):
    __tablename__ = 'logicaldisks'
    id = Column(Integer, primary_key=True)
    name = Column('name', String(10))
    harddrive = Column(Integer, ForeignKey('harddrives.id'))
    sasaddress = Column('sasaddress', String(32))
    scsiaddress = Column('scsiaddress', String(16))
    iomodule = Column('iomodule', String(10))
    modified = Column('modified', DateTime)

    def __init__(self, harddrive, name, sasaddress, scsiaddress, iomodule, modified=datetime.utcnow()):
        self.harddrive = harddrive
        self.name = name
        self.sasaddress = sasaddress
        self.scsiaddress = scsiaddress
        self.iomodule = iomodule
        self.modified = modified

    def returnImportantProperties(self):
        properties = {'harddrive': self.harddrive, 'name': self.name, 'sasaddress': self.sasaddress,
                      'scsiaddress': self.scsiaddress, 'iomodule': self.iomodule, 'modified': self.modified - utcoffset}
        return properties


class currentfailures(Base):
    __tablename__ = 'currentfailures'
    id = Column(Integer, primary_key=True)
    failtype = Column('failtype', String(32))  # one of ['server','swraid',''hwraid','jbod','managementinterface']
    failtest = Column('failedtest', String(32))  # specific to failtype
    failheadnodename = Column('headnodename', String(32))
    failcomponentid = Column('failcomponentid', String(32))  # server name, jbod serial, hard drive serial, etc.
    failstarttime = Column('failstarttime', DateTime)  # time when component entered faield status
    failcleartime = Column('failcleartime', DateTime)  # time when component left failed status

    def __init__(self, failtype, failtest, failheadnodename, failcomponentid, failstarttime, failcleartime):
        self.failtype = failtype
        self.failtest = failtest
        self.failheadnodename = failheadnodename
        self.failcomponentid = failcomponentid
        self.failstarttime = failstarttime
        self.failcleartime = failcleartime

    def returnImportantProperties(self):
        properties = {'failtype': self.failtype, 'failtest': self.failtest, 'failheadnodename': self.failheadnodename,
                      'failcomponentid': self.failcomponentid, 'failstarttime': self.failstarttime - utcoffset,
                      'failcleartime': self.failcleartime - utcoffset}
        return properties


class pastfailures(Base):
    __tablename__ = 'pastfailures'
    id = Column(Integer, primary_key=True)
    failtype = Column('failtype', String(32))  # one of ['server','swraid',''hwraid','jbod','managementinterface']
    failtest = Column('failedtest', String(32))  # specific to failtype
    failheadnodename = Column('headnodename', String(32))
    failcomponentid = Column('failcomponentid', String(32))  # server name, jbod serial, hard drive serial, etc.
    failstarttime = Column('failstarttime', DateTime)  # time when component entered faield status
    failcleartime = Column('failcleartime', DateTime)  # time when component left failed status

    def __init__(self, failtype, failtest, failheadnodename, failcomponentid, failstarttime, failcleartime):
        self.failtype = failtype
        self.failtest = failtest
        self.failheadnodename = failheadnodename
        self.failcomponentid = failcomponentid
        self.failstarttime = failstarttime
        self.failcleartime = failcleartime

    def returnImportantProperties(self):
        properties = {'failtype': self.failtype, 'failtest': self.failtest, 'failheadnodename': self.failheadnodename,
                      'failcomponentid': self.failcomponentid, 'failstarttime': self.failstarttime - utcoffset,
                      'failcleartime': self.failcleartime - utcoffset}
        return properties













