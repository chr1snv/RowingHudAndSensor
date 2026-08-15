
import struct

import Boat, Client

import networkCommon

"""
#assign the device to that location
	hierarchDevPar = None
	if devParentIdx in selBoat.deviceHierarchy:
		 hierarchDevPar = selBoat.deviceHierarchy[devParentIdx]
	else:
		hierarchDevPar = {}
		selBoat.deviceHierarchy[devParentIdx] = hierarchDevPar
	
	
	if not (devLocationIdx in hierarchDevPar):
		hierarchDevPar[devLocationIdx] = { devRoleIdx:devId }
	else:
		hierarchDevPar[devLocationIdx][devRoleIdx] = devId #get the devLocationIdx dictionary because there may be multiple devRoles there
		
	need to know the hierarchy because it will affect how packets are routed
	how is the tree of devices sent? depth first, breadth first?
	depth first is simpler (
"""


def sendSelectedBoatInfo(client, boatId):
		selBoat = Boat.boatsById[boatId] #get the boat using it's id
		#gather info about the boat
		selectedBoatMsgBytesToClient = struct.pack( "<32sIf?BB", 
			selBoat.name.encode('utf-8'), 
			boatId, 
			selBoat.boatLength, 
			selBoat.StrokeSide, 
			selBoat.NumSeats,
			selBoat.numDevices )
		#gather info about each device in the boat
		networkCommon.dbgPrint( "selBoat.deviceHierarchy %s" % str(selBoat.deviceHierarchy)  )
		for devLoc in selBoat.deviceHierarchy:
			devLocDevices = selBoat.deviceHierarchy[devLoc]
			networkCommon.dbgPrint( "packing info for location %i len(devLocDevices): %i devLocDevices %s" % ( devLoc, len(devLocDevices), devLocDevices ) )
			for devRole in devLocDevices:
				[devId, subDevs] = devLocDevices[devRole]
				devNumSubDevs = len(subDevs)
				devMsgBytes = struct.pack("<IBBB",
					devId,
					devLoc,
					devRole,
					devNumSubDevs )
				selectedBoatMsgBytesToClient += devMsgBytes
				networkCommon.dbgPrint( "packedDevice role: %i bytes: %i totalBytes: %i" % ( devRole, len(devMsgBytes), len(selectedBoatMsgBytesToClient)) )
		client.send(Client.svrDevId, [('BoatSelBoat', len(selectedBoatMsgBytesToClient), selectedBoatMsgBytesToClient)])

def handleWebSockClientDeviceRequests( client, datType, datStr ):

	if datType.startswith(b'BoatNew'): #request to create a new boat system/structure/machine
		print("create new boat")
		(boatName,) = struct.unpack( "<32s", datStr[:32] )
		newBoat = Boat.GetOrAllocateBoat( boatName.decode('utf-8') )
		Boat.fillNewBoatVals( newBoat, datStr )
		client.selectedBoat = newBoat.boatId
		sendSelectedBoatInfo(client, client.selectedBoat)

	elif datType.startswith(b'BoatAddDev'): #add selected device id device to boat with role
		Boat.assignDeviceToLocationWithRole(client.selectedBoat, datStr)
		sendSelectedBoatInfo(client, client.selectedBoat)
		
	elif datType.startswith(b'BoatRemDev'): #remove selected device
		Boat.removeDeviceAtLocationAndRoleFromBoat( client.selectedBoat, datStr )
		sendSelectedBoatInfo(client, client.selectedBoat)

	elif datType.startswith(b'BoatSelBoat'):
		(boatId,) = struct.unpack( "<I", datStr[:4] )
		client.selectedBoat = boatId
		
		sendSelectedBoatInfo(client, boatId)
