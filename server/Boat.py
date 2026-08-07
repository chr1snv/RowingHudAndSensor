

import networkCommon

import struct # to get info on struct.unpack formatting
#help( struct )
import threading


class Boat:
	def __init__(self):
		self.name = ""

		self.devices = {}
		self.numDevices = 0

		self.boatName				= ""	#								(32 chars)
		self.boatLength				= 1		#meters 						(float32)
		self.RigDstFromCntrLineElm 	= 1 	#meters							(float32)
		self.StrokeSide				= True	#true starboard, false port		(bool)
		self.OarsPerSeat			= 2 	#1 or 2							(uint8)
		self.OarLen					= 5		#meters							(float32)
		self.CollarDistFromHndlEnd	= 1		#meters							(float32)
		self.NumSeats				= 1		#1-8							(uint8)
		self.StrkDstStrn			= 5		#meters							(float32)


"""
boatDevTypes = {
	HUD		:0,
	STBOar	:1,
	PORTOar	:2
}


const devLocationTypes = Object.freeze({
	Coach	:0,
	Hull	:1,
	Coxan	:2,
	1		:3,
	2		:4,
	3		:5,
	4		:6,
	5		:7,
	6		:8,
	7		:9,
	8		:10
});
"""



def assignDeviceToBoat( boatId, datBytes ):
	selBoat = boatsById[boatId]
	#dev, role
	#boat.devices[role] = dev
	(
		devId,
		devRole,
		devLocation
	) = struct.unpack( "<IBB", datBytes )
	
	if not (devLocation in selBoat.devices):
		selBoat.devices[devLocation] = {}
	devLocDevices = selBoat.devices[devLocation]
	#if not (devRole in devLocDevices):
	devLocDevices[devRole] = devId
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

boats_lock = threading.Lock()
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