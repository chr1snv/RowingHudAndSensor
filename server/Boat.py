

import networkCommon

import struct # to get info on struct.unpack formatting
#help( struct )
import threading

import Device


class Boat:
	def __init__(self):
		self.name = ""

		self.devicesById 		= {}
		self.devicesByLocation	= {}
		self.deviceHierarchy 	= {
										"type": "location",
										"locations": {},
										"devices": {}
									}
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
	"Server"					:0,
	"ESPNOWMasterAccelGyroMag"	:1,
	"HUD"						:2,
	"STBOarAccelGyroMag"		:3,
	"STBOarForce"				:4,
	"PORTOarAccelGyroMag"		:5,
	"PORTOarForce"				:6,
	"SeatPositonSensor"			:7,
	"SeatForceSensor"			:8,
	"Microphone"				:9,
	"Sonar"						:10,
	"Radar"						:11,
	"Lidar"						:12,
	"CameraRGBD"				:13,
	"CameraThermal"				:14,
	"CameraInfared"				:15,
	"CameraRGB"					:16,
	"CameraUV"					:17,
	"MassSpec"					:18,
	"BreathCO2"					:19,
	"BreathO2"					:20,
	"EKG"						:21,
	"ECG"						:22,
	"BloodGlucose"				:23,
	"BloodO2"					:24,
	"SkinConductivity"			:25
}
IDX_TO_DEV_ROLE = list(DEV_ROLE_TO_IDX.keys())


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

def colapseLocIdx( locIdx ): #merge seats 1-8 to 1 for lookup in ALLOWED_ROLES_AT_LOCATION , MASTER_DEV_FOR_LOCATION , LOCATION_PARENTS
	if locIdx >= 4:
		return 4
	return locIdx

ALLOWED_ROLES_AT_LOCATION = {
	"Coach" :	[1 																		 ], #HUD
	 "Hull" :	[0, 8, 9, 10, 11, 12, 13, 14, 15, 16									 ], #MasterIMU, Mic, Sonar, Radar, Lidar, Cameras
	"Coxan" :	[1, 8, 15																 ], #HUD, Mic, Camera
		"1" :	[ 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] #HUD, oar, seat, camera, physiology and chem sensors
}

UPLINK_TYPES = {
	"WEBCERT"	: 0,
	"ESPNOW"	: 1
}
IDX_TO_UPLINK_TYPE = list(UPLINK_TYPES.keys())

#how do devices that are children of a location or a location under a location communicate status/frame data
PARENT_UPLINK_TYPE = {
	"Boat" : "WEBCERT",
	"Hull" : "ESPNOW"
}

MASTER_DEV_FOR_LOCATION = {
	"Boat"	: "Server",
	"Coach" :  None,
	"Hull"  : "ESPNOWMasterAccelGyroMag",
	"Coxan" :  None,
	"1"		:  None
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

#[Boat (Root)]  <-- (WEBCERT / Wi-Fi)
#       ▲
#       ├── [Coach] (HUD)
#       └── [Hull] (Master IMU, Sonar, Radar) <-- (ESPNOW)
#               ▲
#               ├── [Coxan] (HUD, Mic, Camera)
#               └── [1] (Oar, Seat, Physiology Sensors)


def removeDeviceAtLocationAndRoleFromBoat( boatId, datBytes ):
	(
		devId,
		roleIdx,
		locationIdx
	) = struct.unpack( "<IBB", datBytes )
	selBoat = boatsById[boatId]
	networkCommon.dbgPrint( "removeDeviceAtLocationAndRoleFromBoat boatId: %i numDevs: %i devId: %i  role: %i  location: %i" % (boatId, selBoat.numDevices, devId, roleIdx, locationIdx) )
	
	boats_lock.acquire()
	selBoat = boatsById[boatId]
	if locationIdx in selBoat.devicesByLocation:
		devLocDevices = selBoat.devicesByLocation[locationIdx]
		if roleIdx in devLocDevices:
			del devLocDevices[roleIdx]
			selBoat.numDevices -= 1
	boats_lock.release()
	
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


def followRevPathInHierarch( revPath, curHierarch ):
	# Start at the reverse iteration direction because path is leaf to root.
	# Exclude the root node itself (path[-1]) and work down to the target location leaf (path[0]).
	for i in range(len(revPath) - 2, -1, -1):
		curLocIdx = revPath[i]
		
		networkCommon.dbgPrint("curLocIdx %i curHierarch %s" % (curLocIdx, str(curHierarch)))
		
		# Ensure we are traversing through locations safely
		sub_locs = curHierarch.setdefault("locations", {})
		
		# Initialize the sub-location node with explicit schema if it doesn't exist
		if curLocIdx not in sub_locs:
			sub_locs[curLocIdx] = {
				"type": "location",
				"locations": {},
				"devices": {}
			}
		
		curHierarch = sub_locs[curLocIdx]

	return curHierarch
	
def addToBoatDevicesByLocation( selBoat, devId, devRoleIdx, devLocationIdx ):
	#add to devices by location
	devLocDevices = selBoat.devicesByLocation.setdefault(devLocationIdx, {})
	
	existingDevice = None
	if devRoleIdx in devLocDevices:
		existingDevice = devLocDevices[devRoleIdx]
		networkCommon.dbgPrint( "existing device in devLocDevs %i" % devRoleIdx )
	else:
		selBoat.numDevices += 1
	
	networkCommon.dbgPrint( "assigining to devicesByLocation devLocationIdx %i  devLocDevs devRoleIdx: %i devId: %i" % (devLocationIdx, devRoleIdx, devId) )
	devLocDevices[devRoleIdx] = devId
	
def addToBoatDevicesById( selBoat, devId, devRoleIdx, devLocationIdx ):
	#add to deivces by id
	selBoat.devicesById[devId] = [devRoleIdx, devLocationIdx]
	networkCommon.dbgPrint( "assigned to devicesById devId: %i  [ devRoleIdx: %i , devLocationIdx: %i ]" % (devId, devRoleIdx, devLocationIdx) )
	
def addToBoatDevicesByHierarchy( selBoat, devId, devRoleIdx, devLocationIdx ):
	#add to device hierarchy
	#Location Node: {"type": "location", "locations": {}, "devices": {}}
	#Device Node:   {"type": "device", "devId": int, "devices": []}
	
	#find the path of the device location
	path = []
	findPathOfLocation( path, 0, devLocationIdx )
	networkCommon.dbgPrint("devHierarchPath %s" % str(path) ) 
	
	"""
	if not selBoat.deviceHierarchy:
		selBoat.deviceHierarchy = {
			"type": "location",
			"locations": {},
			"devices": {}
		}
	"""
	
	curHierarch = followRevPathInHierarch( path, selBoat.deviceHierarchy )
	
	
	#assign the dev id at the obtained location in the device heriarchy
	devSubDevs = []
	curHierarch["devices"][devRoleIdx] = {
		"type": "device",
		"devId": devId,
		"devices": devSubDevs
	}
	
	
	networkCommon.dbgPrint( "assigned to deviceHierarchy: curHierarch %s devRoleIdx %i devId %i" % (str(curHierarch), devRoleIdx, devId) )
	printDeviceHierarchy( selBoat.deviceHierarchy )


def printDeviceHierarchy(deviceHierarchy, indent_level=0):
	"""
	Recursively pretty-prints the structured device hierarchy to debug logs.

	Args:
		deviceHierarchy (dict): The current node dictionary in the hierarchy tree.
		indent_level (int): Current depth level for visual spacing.
	"""
	spacing = "    " * indent_level

	# Safety check if an empty dictionary or invalid object is passed
	if not isinstance(deviceHierarchy, dict) or "type" not in deviceHierarchy:
		networkCommon.dbgPrint(f"{spacing}[Malformed or Empty Node: {str(deviceHierarchy)}]")
		return

	node_type = deviceHierarchy.get("type")
	
	if node_type == "location":
		# Check if this is the root node or a nested location
		networkCommon.dbgPrint(f"{spacing}📍 Location Node:")

		# 1. Print devices attached to this specific location
		devices = deviceHierarchy.get("devices", {})
		if devices:
			networkCommon.dbgPrint(f"{spacing}  ├─ 🛠️  Attached Devices:")
			for role_idx, dev_node in devices.items():
				networkCommon.dbgPrint(f"{spacing}  │    [{IDX_TO_DEV_ROLE[role_idx]}] Role -> DevID: {dev_node.get('devId')}")
				# Recursively handle any nested sub-devices if they exist
				sub_devs = dev_node.get("devices", [])
				if sub_devs:
					networkCommon.dbgPrint(f"{spacing}  │         └─ Sub-Devices: {str(sub_devs)}")
		
		# 2. Print child locations nested under this location
		locations = deviceHierarchy.get("locations", {})
		if locations:
			networkCommon.dbgPrint(f"{spacing}  └─ 📁 Sub-Locations:")
			for loc_idx, loc_node in locations.items():
				networkCommon.dbgPrint(f"{spacing}       [{IDX_TO_DEV_LOCATION[loc_idx]}] Location:")
				printDeviceHierarchy(loc_node, indent_level + 2)
	
	elif node_type == "device":
		# Alternative standalone print structure for an isolated device node evaluation
		dev_id = deviceHierarchy.get("devId")
		sub_devs = deviceHierarchy.get("devices", [])
		networkCommon.dbgPrint(f"{spacing}🛠️ Device Node (ID: {dev_id}, Sub-Devices: {sub_devs})")



def getUplinkTypeAndParentDevForLocation(selBoat, locIdx):
	"""
	Resolves uplink characteristics and returns integer-compatible routing parameters.
	"""
	parentLoc    = IDX_TO_DEV_LOCATION[locIdx] #prime the up hierarchy walk
	mastrDevLoc  = parentLoc
	mastrDevRole = None #always go 1 up from current location to prevent uplink to self
	mastrDevId   = 0
	#keep going up the hierarchy until finding a master device
	while mastrDevRole is None:
		networkCommon.dbgPrint("getUplinkType mastrDevRole is None   parentLoc %s mastrDevLoc %s mastrDevRole %s mastrDevId %s" % 
			(parentLoc, mastrDevLoc, mastrDevRole, mastrDevId) )
		parentLoc = LOCATION_PARENTS.get(parentLoc) #go 1 up the hierarchy
		
		locIdx = DEV_LOCATION_TO_IDX[parentLoc]
		
		cloapLocIdx = colapseLocIdx(locIdx) #seats 1-8 -> 1
		mastrDevLoc = IDX_TO_DEV_LOCATION[cloapLocIdx]
		
		mastrDevRole = MASTER_DEV_FOR_LOCATION.get(mastrDevLoc)
		
	networkCommon.dbgPrint("getUplinkType mastrDevLoc %s mastrDevRole %s mastrDevId %s" % 
			(mastrDevLoc, mastrDevRole, mastrDevId) )
	
	# Lookup the protocol integer code from UPLINK_TYPES dict mapping
	uplinkType = PARENT_UPLINK_TYPE.get(parentLoc)
	upLnkTypeIdx = UPLINK_TYPES.get(uplinkType, 0)
	
	#lookup the master device id
	mastrDevLocIdx  = DEV_LOCATION_TO_IDX[mastrDevLoc]
	mastrDevRoleIdx = DEV_ROLE_TO_IDX[mastrDevRole]
	
	networkCommon.dbgPrint("getUplinkType mastrDevLocIdx %s mastrDevRoleIdx %s mastrDevId %s" % 
			(mastrDevLocIdx, mastrDevRoleIdx, mastrDevId) )
	
	networkCommon.dbgPrint( "getUplinkType selBoat.devicesByLocation %s" % str(selBoat.devicesByLocation) )
	if mastrDevRole == "Server":
		mastrDevId = 0
	else:
		mastrDevId = selBoat.devicesByLocation[mastrDevLocIdx][mastrDevRoleIdx]
	
	
	return [upLnkTypeIdx, mastrDevLocIdx, mastrDevRoleIdx, mastrDevId]

def notifyDevOfParentAndChildrenLinkTypesAndRecurse(selBoat, curNode, curLocIdx, serverDevId):
	"""
	Streamlined recursive tree walker.
	Determines protocol contexts and transmits synchronization profiles to sub-units.
	"""
	if not isinstance(curNode, dict) or curNode.get("type") != "location":
		return 0

	devices_notified_count = 0
	attached_devices = curNode.get("devices", {})
	sub_locations = curNode.get("locations", {})

	if curLocIdx != 0: #dont try to notify the root ("boat")
		# 1. Resolve communication requirements for this specific location block
		[upLnkTypeIdx, mastrDevLocIdx, mastrDevRoleIdx, mastrDevId] = getUplinkTypeAndParentDevForLocation(selBoat, curLocIdx)

		# 2. Process all hardware definitions residing at this tier
		for devRoleIdx, devData in attached_devices.items():
			devId = devData.get("devId")
			
			device = Device.GetOrAllocateDevice(devId)

			networkCommon.dbgPrint( "uplink_flag %s parent_master_id %s devRoleIdx %s" % (str(upLnkTypeIdx), str(mastrDevId), str(devRoleIdx)) )

			configPayload = struct.pack("<BBBBH", devRoleIdx, upLnkTypeIdx, mastrDevLocIdx, mastrDevRoleIdx, mastrDevId)

			device.send(
				fromDevId=serverDevId,
				datInfoArr=[('CfgStatLink', len(configPayload), configPayload)]
			)
			
			networkCommon.dbgPrint(
				f"Configured DevID {devId} at Loc {IDX_TO_DEV_LOCATION[curLocIdx]} [Role {IDX_TO_DEV_ROLE[devRoleIdx]}]: "
				f"UplinkType={IDX_TO_UPLINK_TYPE[upLnkTypeIdx]}, SendToMasterID={mastrDevId} MasterRole={IDX_TO_DEV_ROLE[mastrDevRoleIdx]} MasterLoc={IDX_TO_DEV_LOCATION[mastrDevLocIdx]}"
			)
			devices_notified_count += 1

	# 3. Compact recursion loop over downstream sub-location instances
	for child_loc_idx, child_loc_node in sub_locations.items():
		devices_notified_count += notifyDevOfParentAndChildrenLinkTypesAndRecurse(
			selBoat,
			child_loc_node,
			child_loc_idx,
			serverDevId
		)

	return devices_notified_count

def notifyBoatDevicesOfParentAndChildrenLinkTypes(selBoat, serverDevId=0):
	"""
	Root system hook to trigger down-tree protocol configuration sweeps.
	"""
	rootNode = selBoat.deviceHierarchy
	if not rootNode or not isinstance(rootNode, dict):
		return
		
	networkCommon.dbgPrint("--- Beginning Hierarchy Network Link Type Distribution Loop ---")

	total_processed = notifyDevOfParentAndChildrenLinkTypesAndRecurse(
		selBoat,
		rootNode, 
		curLocIdx=0, 
		serverDevId=serverDevId
	)

	networkCommon.dbgPrint(f"Distribution complete. Synchronized {total_processed} devices.")



def assignDeviceToLocationWithRole( boatId, datBytes ):
	selBoat = boatsById[boatId]
	#unpack the message
	(
		devId,
		devRoleIdx,
		devLocationIdx
	) = struct.unpack( "<IBB", datBytes )
	
	networkCommon.dbgPrint( "addDeviceAtLoc boatId: %i devId: %i devRoleIdx %i devLocationIdx %i " % (boatId, devId, devRoleIdx, devLocationIdx) )
	
	
	addToBoatDevicesByLocation( selBoat, devId, devRoleIdx, devLocationIdx )
	
	addToBoatDevicesById( selBoat, devId, devRoleIdx, devLocationIdx )
	
	addToBoatDevicesByHierarchy( selBoat, devId, devRoleIdx, devLocationIdx )
	
	
	notifyBoatDevicesOfParentAndChildrenLinkTypes( selBoat )



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