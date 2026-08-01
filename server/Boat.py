


class Boat:
	self.name = ""

	self.devices = []

boats = {}

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