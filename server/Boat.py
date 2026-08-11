

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
	"HUD"				:0,
	"STBOar"			:1,
	"PORTOar"			:2,
	"SeatSlideSensor"	:3,
	"MasterIMU"			:4,
	"Radar"				:5,
	"Camera"			:6
}
IDX_TO_BOAT_DEV_ROLES = list(DEV_ROLE_TO_IDX.keys())


DEV_LOCATION_TO_IDX = {
	"Coach"	:0,
	"Hull"	:1,
	"Coxan"	:2,
	1		:3,
	2		:4,
	3		:5,
	4		:6,
	5		:7,
	6		:8,
	7		:9,
	8		:10
}
IDX_TO_DEV_LOCATION_TYPES = list(DEV_LOCATION_TO_IDX.keys())

ALLOWED_ROLES_AT_LOCATION = {
	"Coach":	[ DEV_ROLE_TO_IDX["HUD"] 																																],
	 "Hull":	[ DEV_ROLE_TO_IDX["MasterIMU"],	DEV_ROLE_TO_IDX["Radar"],	DEV_ROLE_TO_IDX["Camera"]																	],
	"Coxan":	[ DEV_ROLE_TO_IDX["HUD"],		DEV_ROLE_TO_IDX["Camera"]																								],
		"1":	[ DEV_ROLE_TO_IDX["HUD"],		DEV_ROLE_TO_IDX["STBOar"],	DEV_ROLE_TO_IDX["PORTOar"], DEV_ROLE_TO_IDX["SeatSlideSensor"], DEV_ROLE_TO_IDX["Camera"]	]
}

LOCATION_PARENTS = {
	"Coxan" : "Hull",
	"1"		: "Hull"
}

LOCATION_CHILDREN = {
	"Hull"	: "Coxan",
	"Hull"	: "1"
}




def removeDeviceAtLocationAndRoleFromBoat( boatId, datBytes ):
	(
		devId,
		roleIdx,
		locationIdx
	) = struct.unpack( "<IBB", datBytes )
	selBoat = boatsById[boatId]
	networkCommon.dbgPrint( "removeDeviceAtLocationAndRoleFromBoat %i %i %i" % (devId, roleIdx, locationIdx) )
	
	if not (locationIdx in selBoat.devicesByLocation):
		return
	devLocDevices = selBoat.devicesByLocation[locationIdx]
	if not (roleIdx in devLocDevices):
		return
	del devLocDevices[roleIdx]
	selBoat.numDevices -= 1


def assignDeviceToLocationWithRole( boatId, datBytes ):
	selBoat = boatsById[boatId]
	#dev, role
	#boat.devices[role] = dev
	(
		devId,
		devRoleIdx,
		devLocationIdx
	) = struct.unpack( "<IBB", datBytes )
	
	
	
	
	#add to devices by location
	if not (devLocationIdx in selBoat.devicesByLocation):
		selBoat.devicesByLocation[devLocationIdx] = {}
	devLocDevices = selBoat.devicesByLocation[devLocationIdx]
	
	existingDevice = None
	if devRoleIdx in devLocDevices:
		existingDevice = devLocDevices[devRoleIdx]
	
	devLocDevices[devRoleIdx] = devId
	
	
	
	
	#add to deivces by id
	selBoat.devicesById[devId] = [devRole, devLocation]
	
	
	
	
	#add to device hierarchy
	devParent = None
	if ( devLocationIdx in LOCATION_PARENTS ):
		devParent = DEV_LOCATION_TO_IDX[ LOCATION_PARENTS[devLocationIdx] ]
	
	selBoat.deviceHierarchy[devParent][devLocationIdx] = { "DEV_ROLE":devRoleIdx }
	
	
	
	if existingDevice == None:
		selBoat.numDevices += 1


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