

import networkCommon

import struct # to get info on struct.unpack formatting
#help( struct )
import threading


class Boat:
	def __init__(self):
		self.name = ""

		self.devicesById 		= {}
		self.devicesByLocation	= {}
		self.deviceHierarchy 	= {}
		self.numDevices = 0

		self.boatName				= ""	#								(32 chars)
		self.boatLength				= 1		#meters 						(float32)
		self.RigDstFromCntrLineElm	= 1		#meters							(float32)
		self.StrokeSide				= True	#true starboard, false port		(bool)
		self.OarsPerSeat			= 2		#1 or 2							(uint8)
		self.OarLen					= 5		#meters							(float32)
		self.CollarDistFromHndlEnd	= 1		#meters							(float32)
		self.NumSeats				= 1		#1-8							(uint8)
		self.StrkDstStrn			= 5		#meters							(float32)



DEV_ROLE_TO_IDX = {
	"MasterAccelGyroMag"	:0,
	"HUD"					:1,
	"STBOarAccelGyroMag"	:2,
	"STBOarForce"			:3,
	"PORTOarAccelGyroMag"	:4,
	"PORTOarForce"			:5,
	"SeatPositonSensor"		:6,
	"SeatForceSensor"		:7,
	"Microphone"			:8,
	"Sonar"					:9,
	"Radar"					:10,
	"Lidar"					:11,
	"CameraRGBD"			:12,
	"CameraThermal"			:13,
	"CameraInfared"			:14,
	"CameraRGB"				:15,
	"CameraUV"				:16,
	"MassSpec"				:17,
	"BreathCO2"				:18,
	"BreathO2"				:19,
	"EKG"					:20,
	"ECG"					:21,
	"BloodGlucose"			:22,
	"BloodO2"				:23,
	"SkinConductivity"		:24
}
IDX_TO_BOAT_DEV_ROLES = list(DEV_ROLE_TO_IDX.keys())


DEV_LOCATION_TO_IDX = {
	"Boat"	:0,
	"Coach"	:1,
	"Hull"	:2,
	"Coxan"	:3,
	"1"		:4,
	"2"		:5,
	"3"		:6,
	"4"		:7,
	"5"		:8,
	"6"		:9,
	"7"		:10,
	"8"		:11
}
IDX_TO_DEV_LOCATION = list(DEV_LOCATION_TO_IDX.keys())

ALLOWED_ROLES_AT_LOCATION = {
	"Coach":	[1 																		 ], #HUD
	 "Hull":	[0, 8, 9, 10, 11, 12, 13, 14, 15, 16									 ], #MasterIMU, Mic, Sonar, Radar, Lidar, Cameras
	"Coxan":	[1, 8, 15																 ], #HUD, Mic, Camera
		"1":	[ 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] #HUD, oar, seat, camera, physiology and chem sensors
}

#every location can have one parent
LOCATION_PARENTS = {
	"Coach" : "Boat",
	"Hull"	: "Boat",
	"Coxan" : "Hull",
	"1"		: "Hull"
}
#locations may have multiple children
LOCATION_CHILDREN = {
	"Boat"	: [ "Coach", "Hull" ],
	"Hull"	: [ "Coxan", "1" ]
}


def removeDeviceAtLocationAndRoleFromBoat( boatId, datBytes ):
	(
		devId,
		roleIdx,
		locationIdx
	) = struct.unpack( "<IBB", datBytes )
	selBoat = boatsById[boatId]
	networkCommon.dbgPrint( "removeDeviceAtLocationAndRoleFromBoat boatId: %i numDevs: %i devId: %i  role: %i  location: %i" % (boatId, selBoat.numDevices, devId, roleIdx, locationIdx) )
	
	if locationIdx in selBoat.devicesByLocation:
		devLocDevices = selBoat.devicesByLocation[locationIdx]
		if roleIdx in devLocDevices:
			del devLocDevices[roleIdx]
			selBoat.numDevices -= 1
	print( "numDevs after remove attempt %i " % selBoat.numDevices )
	


def findPathOfLocation( path, rootIdx, locIdx ):
	print( "findPath rootIdx %i locIdx %i" % (rootIdx, locIdx) )
	path.append( locIdx )
	curIdx = locIdx
	while curIdx != rootIdx:
		devLocStr 	= IDX_TO_DEV_LOCATION[ curIdx ]
		parent 		= LOCATION_PARENTS [ devLocStr ]
		parentIdx 	= DEV_LOCATION_TO_IDX [ parent ]
		print( "devLocStr %s parent %s parentIdx %i" % (devLocStr, parent, parentIdx) )
		curIdx = parentIdx
		path.append( curIdx )
	#list(reversed(path)) #to get parent -> leaf order

def assignDeviceToLocationWithRole( boatId, datBytes ):
	selBoat = boatsById[boatId]
	#dev, role
	#boat.devices[role] = dev
	(
		devId,
		devRoleIdx,
		devLocationIdx
	) = struct.unpack( "<IBB", datBytes )
	
	networkCommon.dbgPrint( "addDeviceAtLoc boatId: %i devId: %i devRoleIdx %i devLocationIdx %i " % (boatId, devId, devRoleIdx, devLocationIdx) )
	
	
	#add to devices by location
	if not (devLocationIdx in selBoat.devicesByLocation):
		selBoat.devicesByLocation[devLocationIdx] = {}
	devLocDevices = selBoat.devicesByLocation[devLocationIdx]
	
	existingDevice = None
	if devRoleIdx in devLocDevices:
		existingDevice = devLocDevices[devRoleIdx]
		networkCommon.dbgPrint( "existing device in devLocDevs %i" % devRoleIdx )
	
	networkCommon.dbgPrint( "assigining to devicesByLocation devLocationIdx %i  devLocDevs devRoleIdx: %i devId: %i" % (devLocationIdx, devRoleIdx, devId) )
	devLocDevices[devRoleIdx] = devId
	
	if existingDevice == None:
		selBoat.numDevices += 1
	
	
	#add to deivces by id
	selBoat.devicesById[devId] = [devRoleIdx, devLocationIdx]
	networkCommon.dbgPrint( "assigned to devicesById devId: %i  [ devRoleIdx: %i , devLocationIdx: %i ]" % (devId, devRoleIdx, devLocationIdx) )
	
	
	
	#add to device hierarchy
	
	#find the path of the device location
	path = []
	findPathOfLocation( path, 0, devLocationIdx )
	networkCommon.dbgPrint("devHierarchPath %s" % str(path) ) 
	
	curHierarch = selBoat.deviceHierarchy
	
	#start at the root(exclude boat) and work down to the leaf (one before devLocationIdx)
	for i in range(len(path) - 2, -1, -1):
		curLocIdx = path[i]
		#curLeafIdx = path[i-1]
		
		networkCommon.dbgPrint( "curLocIdx %i" % (curLocIdx) )
		
		#add the curLoc and curLeaf (if doesn't already exist)
		hierarchPar = curHierarch.setdefault(curLocIdx, {})

		curHierarch = hierarchPar
	
	#assign the dev id at the obtained location in the device heriarchy
	devSubDevs = []
	curHierarch[devRoleIdx] = [devId, devSubDevs]
	
	networkCommon.dbgPrint( "assigned to deviceHierarchy: curHierarch %s devRoleIdx %i devId %i" % (str(curHierarch), devRoleIdx, devId) )
	networkCommon.dbgPrint( "selBoat.deviceHierarchy %s" % str(selBoat.deviceHierarchy) ) 


def fillNewBoatVals( newBoat, valBytes ):
	newBoat.createTime = networkCommon.curMillis()
	try:
		sidx = 0
		cmdValArr = []


		#32+4+4+1+1+4+4+1+4 => 55
		print(valBytes)
		(
			newBoat.boatName,
			newBoat.boatLength,
			newBoat.RigDstFromCntrLineElm, 
			newBoat.StrokeSide,
			newBoat.OarsPerSeat,
			newBoat.OarLen,
			newBoat.CollarDistFromHndlEnd,
			newBoat.NumSeats,
			newBoat.StrkDstStrn,
		) = struct.unpack( "<32sff?BffBf", valBytes[sidx : sidx + 55] )
		sidx += 55
		print( "boatName %s boatLength %f RigDstFromCntrLineElm %f StrokeSide %s OarsPerSeat %i OarLen %f CollarDistFromHndlEnd %f NumSeats %i StrkDstStrn %f" % 
			(newBoat.boatName, newBoat.boatLength, newBoat.RigDstFromCntrLineElm, newBoat.StrokeSide, newBoat.OarsPerSeat, newBoat.OarLen, newBoat.CollarDistFromHndlEnd,
			newBoat.NumSeats, newBoat.StrkDstStrn) )



	except Exception as e:
		print( "fillValues error %s" % str(e) )

boats_lock = threading.RLock()
boats = {}
boatsById = {}
lastAllocatedBoatId = -1

def GetOrAllocateBoat( boatName ):
	with boats_lock:
		global lastAllocatedBoatId
		if boatName not in boats:
			lastAllocatedBoatId += 1
			print("allocating boat %i" % lastAllocatedBoatId)
			boat = Boat()
			boat.boatId = lastAllocatedBoatId
			boat.name = boatName
			boatsById[boat.boatId] = boat
			boats[boatName] = boat
		boats[boatName].lastAccessTime = networkCommon.curMillis()
		print( "returning boatId %i" % boats[boatName].boatId )
		return boats[boatName]