
import struct

import Boat, Client


async def sendSelectedBoatInfo(client, boatId):
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
		for devLoc in selBoat.devices:
			devLocDevices = selBoat.devices[devLoc]
			for devRole in devLocDevices:
				devId = devLocDevices[devRole]
				devMsgBytes = struct.pack("<IBB",
					devId,
					devLoc,
					devRole )
			selectedBoatMsgBytesToClient += devMsgBytes
		await client.send(Client.svrDevId, [('BoatSelBoat', len(selectedBoatMsgBytesToClient), selectedBoatMsgBytesToClient)])

async def handleWebSockClientDeviceRequests( client, datType, datStr ):

	if datType.startswith(b'BoatNew'): #request to create a new boat system/structure/machine
		print("create new boat")
		(boatName,) = struct.unpack( "<32s", datStr[:32] )
		newBoat = Boat.GetOrAllocateBoat( boatName.decode('utf-8') )
		Boat.fillNewBoatVals( newBoat, datStr )
		client.selectedBoat = newBoat.boatId
		await sendSelectedBoatInfo(client, client.selectedBoat)

	elif datType.startswith(b'BoatAddDev'): #add selected device id device to boat with role
		Boat.assignDeviceToBoat(client.selectedBoat, datStr)
		await sendSelectedBoatInfo(client, client.selectedBoat)

	elif datType.startswith(b'BoatSelBoat'):
		(boatId,) = struct.unpack( "<I", datStr[:4] )
		client.selectedBoat = boatId
		
		await sendSelectedBoatInfo(client, boatId)
