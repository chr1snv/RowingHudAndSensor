
import struct

import Boat, Device, Client

import networkCommon

"""
	reason for device hierarchy in boat affects how packets are routed
	how is the tree of devices sent? depth first, breadth first?
	depth first is simpler
"""


def sendBoatInfo(client, boatId):
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
		curHierarch = selBoat.deviceHierarchy
		
		
		def sendBotInfoRecur( locIdx, curHierarch ):
			retBytes = b''
			curLocs = curHierarch['locations']
			curDevs = curHierarch['devices']
			networkCommon.dbgPrint( "packing info for location %s curHierarch %s" % ( locIdx, curHierarch ) )
			
			for devRole in curDevs:				
				dev   = curDevs[devRole]
				networkCommon.dbgPrint( "dev %s" % dev )
				devId = dev['devId']
				devNumSubDevs = len(dev['devices'])
				devMsgBytes = struct.pack("<IBBB",
					devId,
					locIdx,
					devRole,
					devNumSubDevs )
				retBytes += devMsgBytes
				networkCommon.dbgPrint( "packedDevice role: %i bytes: %i totalBytes: %i" % ( devRole, len(devMsgBytes), len(selectedBoatMsgBytesToClient)) )
			
			for loc in curLocs:
				subLoc = curLocs[loc]
				
				retBytes += sendBotInfoRecur( loc, subLoc )
			
			return retBytes
			
		selectedBoatMsgBytesToClient += sendBotInfoRecur( 0, curHierarch )
		client.send(Client.svrDevId, [('BoatSelBoat', len(selectedBoatMsgBytesToClient), selectedBoatMsgBytesToClient)])


def sendBoatStatus(client, boatId):
	# Send the most recent frame of the boat position
	selBoat = Boat.boatsById[boatId] # Get the boat using its ID

	# 1. Initialize the base payload header with the current boat footprint
	selectedBoatMsgBytesToClient = struct.pack(
		"<IB", 
		boatId, 
		selBoat.numDevices
	)

	networkCommon.dbgPrint("selBoat.deviceHierarchy %s" % str(selBoat.deviceHierarchy))

	# 2. Recursive layout engine to trace down location blocks safely
	def collect_device_bytes(node, current_loc_idx=0):
		bytes_accumulator = b''
		
		if not isinstance(node, dict):
			return bytes_accumulator
		
		if node.get("type") == "location":
			devLocDevices = node.get("devices", {})

			networkCommon.dbgPrint(
				"packing info for location %i len(devLocDevices): %i devLocDevices %s" % 
				(current_loc_idx, len(devLocDevices), str(devLocDevices))
			)

			for devRole, dev_node in devLocDevices.items():
				devId = dev_node["devId"]
				
				# Fetching the structural arrays to track device counts correctly
				subDevs = dev_node.get("devices", [])  
				devNumSubDevs = len(subDevs)
				
				# FIX: Look up the device driver instance inside the global `devices` dictionary, 
				# NOT out of the empty sub-devices list tree definition tracking array.
				device = Device.GetOrAllocateDevice( devId )
				
				# Format: I=DevID, B=LocIdx, B=RoleIdx, B=SubDevCount, H=PacketLength
				devMsgBytes = struct.pack(
					"<IBBBH",
					devId,
					current_loc_idx,
					devRole,
					devNumSubDevs,
					len(device.lastStatusPkt)
				)
				bytes_accumulator += devMsgBytes
				bytes_accumulator += device.lastStatusPkt
				
				networkCommon.dbgPrint(
					"packedDevice role: %i bytes: %i totalBytes: %i" % 
					(devRole, len(devMsgBytes), len(bytes_accumulator))
				)

			# Recurse down into all nested sub-locations
			sub_locations = node.get("locations", {})
			for sub_loc_idx, sub_loc_node in sub_locations.items():
				bytes_accumulator += collect_device_bytes(sub_loc_node, sub_loc_idx)
		
		return bytes_accumulator

	# 3. Compile the structural byte sequence and deliver it down to the socket layer
	selectedBoatMsgBytesToClient += collect_device_bytes(selBoat.deviceHierarchy, current_loc_idx=0)

	client.send(
		Client.svrDevId, 
		[('BoatStatus', len(selectedBoatMsgBytesToClient), selectedBoatMsgBytesToClient)]
	)



def handleWebSockClientDeviceRequests( client, datType, datStr ):

	if datType.startswith(b'BoatNew'): #request to create a new boat system/structure/machine
		print("create new boat")
		(boatName,) = struct.unpack( "<32s", datStr[:32] )
		newBoat = Boat.GetOrAllocateBoat( boatName.decode('utf-8') )
		Boat.fillNewBoatVals( newBoat, datStr )
		client.selectedBoatId = newBoat.boatId
		sendBoatInfo(client, client.selectedBoatId)

	elif datType.startswith(b'BoatAddDev'): #add selected device id device to boat with role
		Boat.assignDeviceToLocationWithRole(client.selectedBoatId, datStr)
		sendBoatInfo(client, client.selectedBoatId)

	elif datType.startswith(b'BoatRemDev'): #remove selected device
		Boat.removeDeviceAtLocationAndRoleFromBoat( client.selectedBoatId, datStr )
		sendBoatInfo(client, client.selectedBoatId)

	elif datType.startswith(b'BoatSelBoat'):
		(boatId,) = struct.unpack( "<I", datStr[:4] )
		client.selectedBoatId = boatId
		
		sendBoatInfo(client, boatId)

	elif datType.startswith(b'BoatStatus'):
		networkCommon.dbgPrint( "handle BoatStatus" )
		try:
			sendBoatStatus( client, client.selectedBoatId )
		except Exception as e:
			print( "sendBoatStatus error %s" % str(e) )
