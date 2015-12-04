#!/usr/bin/python

from ConfigParser import ConfigParser
from os import sys, path, listdir

if len(sys.argv) == 2 and sys.argv[1] == 'install':
	cp = ConfigParser()
	cp.optionxform = str
	cp.add_section('Unit')
	cp.set('Unit', 'Description', 'VIRTUALBOX start/stop script');
	cp.set('Unit', 'After', 'networking.service vboxdrv.service ssh.service');
	cp.add_section('Service')
	cp.set('Service', 'Type', 'simple');
	cp.set('Service', 'ExecStart', '/root/vboxdepstart.py');
	cp.set('Service', 'TimeoutSec', '1200');
	cp.add_section('Install')
	cp.set('Install', 'WantedBy', 'multi-user.target');
	with open('vboxdepstart.service', 'wb') as configfile:
	    cp.write(configfile)
	print 'SystemD script installed.'
	exit(0)

from subprocess import call
from time import sleep
import signal

def signal_handler(signal, frame):
        pass

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class VirtualMachine(object):
	uuid = None
	startafter = None
	finishtype = None # poweroff, savestate, acpipowerbutton
	finishwait = None
	order = None
	user = None

	def __init__(self, user, uuid, order, startafter, finishtype, finishwait):
		self.uuid = uuid
		self.startafter = startafter
		self.finishtype = finishtype
		self.finishwait = finishwait
		self.order = order
		self.user = user

	def __repr__(self):
		return self.uuid
	
	def __str__(self):
		return "UUID = " + self.uuid + ", from user " + self.user
	
	def start(self):
		sleep(self.startafter)
		cmd = "su - " + self.user + " -- VBoxManage startvm --type headless " + self.uuid
		print "Running '", cmd, '"'
		call(cmd, shell=True)
	
	def stop(self):
		operation = "poweroff"
		if self.finishtype in ["acpipowerbutton", "savestate", "poweroff"]:
			operation = self.finishtype
		
		cmd = "su - " + self.user + " -- VBoxManage controlvm " + self.uuid + " " + operation
		print "Running '", cmd, '"'
		call(cmd, shell=True)
		if self.finishtype == "acpipowerbutton":
			sleep(self.finishwait)

cp_path = "/root/vboxdepstart.d"

cp = ConfigParser()
cp.readfp(open(path.join(cp_path, "main.conf")))
if not cp.has_section('depstart'):
	print "Invalid config file!"
	exit(1)

ds_enabled = cp.getboolean('depstart', 'enabled')
if not ds_enabled:
	print "VirtualBox Dependency-based Starter disabled!"
	exit(1)

arrVMs = []
starton = cp.getint('depstart', 'startorder')
stopat = cp.getint('depstart', 'stoporder')
if starton > stopat:
	print "Are you kiddin'?"
	exit(1)

for n in range(starton, stopat + 1):
	arrVMs.insert(0, [])

vms = [f for f in listdir(cp_path) if path.isfile(path.join(cp_path, f)) and f.endswith('.vm')]
for vm in vms:
	cpvm = ConfigParser()
	cpvm.readfp(open(path.join(cp_path, vm)))
	if not cpvm.has_section('vm'):
		continue
	
	if cpvm.getint('vm', 'enabled') == 0:
		continue
	
	vOrder = cpvm.getint('vm', 'order')
	if vOrder > stopat or vOrder < starton:
		continue
		
	vUser = cpvm.get('vm', 'user')
	vUuid = cpvm.get('vm', 'uuid')
	vStartafter = cpvm.getint('vm', 'startafter')
	vFinishtype = cpvm.get('vm', 'finishtype')
	vFinishwait = cpvm.get('vm', 'finishwait')

	obj = VirtualMachine(vUser, vUuid, vOrder, vStartafter, vFinishtype, vFinishwait)
	arrVMs[vOrder - starton].insert(0, obj)

print "Starting up virtual machines..."

for iVMs in arrVMs:
	for VM in iVMs:
		VM.start()

signal.pause()

print "Signal received, stopping/saving virtual machines..."

for iVMs in arrVMs:
	for VM in iVMs:
		VM.stop()

