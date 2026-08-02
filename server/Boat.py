

import networkCommon

import struct # to get info on struct.unpack formatting
#help( struct )


class Boat:
	def __init__(self):
		self.name = ""

		self.devices = []
		
		self.boatName				= ""	#								(32 chars)
		self.boatLength				= 1		#meters 						(float32)
		self.RigDstFromCntrLineElm 	= 1 	#meters							(float32)
		self.StrokeSide				= True	#true starboard, false port		(bool)
		self.OarsPerSeat			= 2 	#1 or 2							(uint8)
		self.OarLen					= 5		#meters							(float32)
		self.CollarDistFromHndlEnd	= 1		#meters							(float32)
		self.NumSeats				= 1		#1-8							(uint8)
		self.StrkDstStrn			= 5		#meters							(float32)
	

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


boats = {}
boatsById = {}
lastAllocatedBoatId = -1

def GetOrAllocateBoat( boatName ):
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