
import networkCommon

import struct

# Define your C++ struct sizes in bytes for explicit pointer sliding

STATUS_SECTION_HDR_SIZE = 12   # B H H H F B format -> 12 bytes total
MAG_SENSOR_SIZE = 6          # h h h (3 * int16) -> 6 bytes
ACCEL_SENSOR_SIZE = 6        # h h h (3 * int16) -> 6 bytes
GYRO_SENSOR_SIZE = 6         # h h h (3 * int16) -> 6 bytes


#last status
class Device:

	def __init__(self):

		self.cmds = [] #pending commands to send to the device

		self.devId = -1

		self.controlingCliId = -1

		self.description = 'Device Name'


		self.featureMask = 0

		self.devType = -1


		self.wSock = None

		self.sendPktIdx = 0

		self.lastImage = b''
		self.lastImageLength = 0
		self.lastImageTime = networkCommon.curMillis()

		self.postSettings = b''
		self.lastSettingsTime = networkCommon.curMillis()
		
		self.postStatus = b''
		self.lastStatusTime = networkCommon.curMillis()

		self.alarmArmed			= ""
		self.magAX				= ""
		self.magAY				= ""
		self.magAZ				= ""

		self.numServos			= 0
		self.servoAngles		= []

		self.staRssi			= ""
		self.lastTemperature	= ""

		self.mx					= 0
		self.my					= 0
		self.mz					= 0

		self.ax					= 0
		self.ay					= 0
		self.az					= 0

		self.gx					= 0
		self.gy					= 0
		self.gz					= 0

		self.magHeading			= ""
		self.magAlarmDiff		= ""
		self.magAlarmTriggered	= ""
		self.alarmOutput		= ""



	async def send( self, fromDevId, datInfoArr ):
		if self.wSock != None:
			#print("send to device " )
			#print(datInfoArr)
			prevPktIdx = self.sendPktIdx
			print( self.sendPktIdx )
			self.sendPktIdx = await networkCommon.sendPkt(self.wSock, self.sendPktIdx, fromDevId, datInfoArr )
			print( self.sendPktIdx ) 
			if self.sendPktIdx != prevPktIdx:
				return True
		return False


#uint16_t deviceID;   //which device this packet was from
#uint16_t featureMask;  // Bit flags indicating active payloads
#uint16_t deviceMode;   // 1 = Master HUD, 2 = IMU Sensor Node, etc
#int      staRssi;  //recieved wifi signal strength
#uint8_t lastTemperature; //temperature of the esp32

	def fillStatus( self, statBytes ):
		self.postStatus = statBytes
		self.lastStatusTime = networkCommon.curMillis()
		try:
			sidx = 0
			cmdValArr = []
			print(statBytes)
			(
				self.deviceID, 
				self.featureMask, 
				self.deviceMode, 
				self.staRssi, 
				self.lastTemperature
			) = struct.unpack( "<HHHiB", statBytes[sidx : sidx + 11] )
			sidx += 11
			print("devId %i ftMask %i devMd %i staRssi %i lastTemp %i" % 
				(self.deviceID, self.featureMask, self.deviceMode, self.staRssi, self.lastTemperature) )
			devType = firstMatchingDeviceTypeToMask(self.featureMask)
			print( "DevType: %s" % (deviceTypes[devType][0]) ) 
			
			#if maskHasBit( self.featureMask, 0 ):
			#	sidx = fillFileStatus( self, statBytes, sidx )
			#if maskHasBit( self.featureMask, 1 ):
			#	sidx = fillDistStatus( self, statBytes, sidx )
			if maskHasBit( self.featureMask, 2 ):
				sidx = fillMagStatus( self, statBytes, sidx )
			if maskHasBit( self.featureMask, 3 ):
				sidx = fillAccelStatus( self, statBytes, sidx )
			if maskHasBit( self.featureMask, 4 ):
				sidx = fillGyroStatus( self, statBytes, sidx )
			#numSrvos = int( statBytes[5:7] )
			#print("stat numSrvos %i" % numSrvos)
			#idx = 7
			#for i in range(numSrvos):
			#	cmdValArr.append( [ "angAxis"+str(i), statBytes[idx:idx+3] ] )
			#	idx += 3
				#print( "a%i %i" % (i, int(cmdValArr[-1][1])) )
			#numCmdsCleared = clearCompletedCommands(self.cmds, cmdValArr)
			#print( "cmdsCleared %i" % numCmdsCleared )
		except Exception as e:
			print( "fillValues error %s" % str(e) )

	def fillSettings(self, datStr, datStrLen ):
		self.lastSettings = datStr
		self.lastSettingsLen = datStrLen
		self.lastSettingsTime = networkCommon.curMillis()

	def fillImage(self, datStr, datStrLen):
		#print( "last image len %i datStrLen %i " % (len(datStr), datStrLen )  )
		self.lastImage = datStr
		self.lastImageLength = datStrLen
		self.lastImageTime = networkCommon.curMillis()



#def fillFileStatus():

#def fillDistStatus():

def fillMagStatus(self, statBytes, idx):
	(
		self.mx, 
		self.my,
		self.mz
	) = struct.unpack( "<HHH", statBytes[ idx : idx + 6] )
	idx += 6
	print( "mx %i my %i mz %i" % (self.mx, self.my, self.mz) )
	return idx

def fillAccelStatus(self, statBytes, idx):
	(
		self.ax, 
		self.ay,
		self.az
	) = struct.unpack( "<HHH", statBytes[ idx : idx + 6] )
	idx += 6
	print( "ax %i ay %i az %i" % (self.ax, self.ay, self.az) )
	return idx

def fillGyroStatus(self, statBytes, idx):
	(
		self.gx, 
		self.gy,
		self.gz
	) = struct.unpack( "<HHH", statBytes[ idx : idx + 6] )
	idx += 6
	print( "gx %i gy %i gz %i" % (self.gx, self.gy, self.gz) )
	return idx
#def fillMicStatus():

#def fillCamStatus():

#def fillDispStatus():

#def fillLightStatus():

#def fillSpeakerStatus():


featureBitToString = \
			['File', 'Dist', 'Mag', 'Accel', 'Gyro', 'Mic', 'Cam', 'Disp', 'Light', 'Speaker' ]
deviceTypes = [ \
[ 'HUD', 	 	0,	     0,		1,		1,		1,		0,		0,		1,		0,		0], \
[ 'IMU_Pod',	0,	     0,		1,		1,		1,		0,		0,		0,		0,		0]  ]

def maskHasBit(mask, n):
	#used to check if a mask has a feature
	return bool(mask & (1 << n))

def maskHasBits(mask, bitArr):
	#helper function for firstMatchingDeviceTypeToMask (compares feature masks )
	for n in range(len(bitArr)):
		if not bool(mask & (bool(bitArr[n] << n))):
			return False
	return True

def firstMatchingDeviceTypeToMask(mask):
	#find the type of the device from the feature mask
	for i in range(len(deviceTypes)):
		devType = deviceTypes[i]
		if maskHasBits(mask, devType[1:] ):
			return i
	return -1










def GetCommandListBytes(cmds):
	#get queued commands to send to device
	#output = io.BytesIO()
	numCmdsToSend = min(9, len(cmds))
	print( "numCmds in getList %i" % numCmdsToSend )
	#output.write( str(numCmdsToSend).encode('utf-8') ) #number of commands
	#output.write( b's' ) #commands are from server
	retArr = []
	for cmdIdx in range(0,numCmdsToSend):
		cmd = cmds[cmdIdx]
		cmdPart = (cmd[0])[:11]
		#output.write( cmdPart + bytes(11-len(cmdPart)) ) #command
		#output.write( bytes(4-1) + b'0') #device id
		#lenDat = str(len(cmd[1])).encode('utf-8')
		#output.write( bytes(6-len(lenDat))+lenDat)
		dat = (cmd[1])
		#output.write( dat )
		print( "cmd %s dat %s" % (cmdPart, dat) )
		try:
			retArr.append( (cmdPart, len(dat), dat) )
		except Exception as e:
			print( "error retArr.append( (cmdPart, len(dat), dat) ) %s" % str(e) )
	#in python "assigning something to elements of that list, will change the original list ( reason for [:] (selection of all elements of the list))"
	#cmds[:] = cmds[numCmdsToSend:] #should add wait for device to confirm recept of commands, though clearing it here now for simplicity
	#outBytes = output.getvalue()#.encode('utf-8')
	#print( 'sending Cmds %s' % outBytes )
	return retArr#outBytes

def putCmdList(cmds, cmdDatArr):
	#add a command to list of not yet executed commands
	#allow only 1 (most recent instance of command) 
	#i.e. if angle commanded, only keep most recent one
	print("putting cmds")
	notPutNewCmdIdxs = []
	for newCmdIdx in range(len(cmdDatArr)):
		newCmd = cmdDatArr[newCmdIdx]
		cmdPut = False
		for i in range(len(cmds)):
			queuedCmd = cmds[i]
			if queuedCmd[0] == newCmd[0]:
				cmds[i] = newCmd
				cmdPut = True
		if not cmdPut:
			notPutNewCmdIdxs.append( newCmdIdx )
	for i in range(len(notPutNewCmdIdxs)):
		newCmd = cmdDatArr[notPutNewCmdIdxs[i]]
		print("appendingCmd %s" % newCmd[0])
		if len(cmds) < 1:
			cmds[:] = [ newCmd ]
		else:
			cmds.append( newCmd )
	print(len(cmds))

def clearCompletedCommands(cmds, cmdValArr):
	#check most recent recieved statuses from device (in corresponding command format)
	#to find if commands have been applied or if they need to be sent again
	numCmdsCleared = 0
	
	#clear non servo position commands (could check command types later)
	numCmds = len(cmds)
	i = 0
	while i < numCmds:
		cmd = cmds[i]
		if cmd[0][:7] != b'angAxis': #not an angAxis command
			print("clearing %s" % str(cmd[0][:7]) )
			del cmds[i]
			numCmds -= 1
			numCmdsCleared += 1
		i += 1
	
	#clear servo commanded positions if met
	for newValIdx in range(len(cmdValArr)):
		newVal = cmdValArr[newValIdx]
		for cmdIdx in range(len(cmds)):
			cmd = cmds[cmdIdx]
			newCmdType = bytes(newVal[0], 'utf8')
			print( "cmp %s | %s || %s | %s" % (newCmdType, cmd[0], newVal[1], cmd[1]) )
			if newCmdType == cmd[0]:
				try:
					if ( int(newVal[1]) == int(cmd[1]) or len(newVal[1]) == 0 ):
						#( len(newVal[1]) == len(cmd[1]) and \
						#print( "clear match %s %s" % ( str(cmd), str(newVal) ) )
						del cmds[cmdIdx]
						numCmdsCleared += 1
						break
				except:
					None #likely newVal is of a type that doesn't have len() function
	
	#return a count of how many cleared (to know if things changed)
	return numCmdsCleared




devices = {}

def GetOrAllocateDevice( devId ):
	if not ( devId in devices.keys() ):
		dev = Device()
		dev.devId = devId
		devices[devId] = dev
	return devices[devId]

