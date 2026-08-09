import socket
import networkCommon, Device, Client, Accounts

import ClientWebsockHandler

import DeviceWebsockHandler

import Boat

import BoatWebsockHandler


import struct

import websockets

import traceback

#https://www.optimizationcore.com/coding/websocket-python-parsing-binary-frames-from-a-tcp-socket/
def msgHandler(websocket, msg, client_ip_address):
	global strSendError
	try:
		#msg = await websocket.read_message()#frame(4096)
		#print(msg[:50])
		#async for msg in websocket:
		rcvTime = networkCommon.curMillis()
		#print(dir(websocket))
		#msgOpcode = 
		msgLen = len(msg)
		if msgLen < 1:
			return
		if( type(msg) != type(b'') ):
			msg = msg.encode('utf-8')
		sync, pktIdx, devOrCliId, numCmd, fromDorC = struct.unpack("<BBHBB", msg[0:networkCommon.PACKET_HEADER_SIZE])

		networkCommon.dbgPrint( "pktIdx %i devOrCliId %s numCmd %i fromType %c" % (pktIdx, devOrCliId, numCmd, fromDorC) )
		mIdx = networkCommon.PACKET_HEADER_SIZE
		cmdIdx = 0
		
		deviceWithNewCmds = None
		
		pendingLoginUname = ''
		pktAuth = ''
		while cmdIdx < numCmd:
			networkCommon.dbgPrint(msg[mIdx : mIdx+11+20])
			datType = msg[mIdx:mIdx+11]
			networkCommon.dbgPrint("datType %s" % datType)
			mIdx += 11
			datLen = int.from_bytes( msg[mIdx : mIdx + 2], byteorder="big" )
			networkCommon.dbgPrint( "datLenBytes %s datLen %i" % ( msg[mIdx: mIdx+2],  datLen ) )
			mIdx += 2
			datStr = msg[mIdx:mIdx+datLen]
			if fromDorC == ord('d'): #data from device
				lenDevsBeforeAllocate = len( Device.devices )
				device = Device.GetOrAllocateDevice(devOrCliId)
				if len( Device.devices ) > lenDevsBeforeAllocate:
					networkCommon.dbgPrint( "requesting getDevDesc" )
					device.send( Client.svrDevId, [('getDevDesc', 0, b'')] )
				client = None
				if device.controlingCliId >= 0 and device.controlingCliId in Client.clientsById.keys():
					client = Client.clientsById[device.controlingCliId]
				cliIdNum = -2
				if client:
					cliIdNum = client.cliId
				networkCommon.dbgPrint( "from %s devId: %i datType: %s datLen: %i controllingCliId %i client %i" % (chr(fromDorC), devOrCliId, datType, datLen, device.controlingCliId, cliIdNum) )
				device.wSock = websocket #for sending data to device
				if datType.startswith(b"Stat"):
					device.fillStatus( datStr ) #read the status data in from device
					#respond with queued commands
					cmdDatArr = Device.GetCommandListBytes(device.cmds)
					if( len(cmdDatArr) > 0 ):
						networkCommon.dbgPrint("recvd Stat sending commands %s" % ( cmdDatArr ) )
						if not device.send( Client.svrDevId, cmdDatArr ):
							Device.putCmdList( deviceWithNewCmds.cmds, cmdDatArr )
					lastStatTimeStr = str(device.lastStatusTime).encode('utf-8')
					if client:
						client.send( device.devId, [('Stat', len(device.postStatus), device.postStatus), ('Time', len(lastStatTimeStr), lastStatTimeStr)] )
					else:
						networkCommon.dbgPrint("no cli to forward stat to")
				if datType.startswith(b"Set"):
					device.fillSettings( datStr, datLen )
					lastSetTimeStr = str(device.lastSettingsTime).encode('utf-8')
					if client:
						client.send( device.devId, [('Set', device.lastSettingsLen, device.lastSettings), ('Time', len(lastSetTimeStr), lastSetTimeStr)] )
					else:
						networkCommon.dbgPrint("no cli to forward set to")
					networkCommon.dbgPrint( "requesting getDevDesc" )
					device.send( Client.svrDevId, [('getDevDesc', 0, b'')] )
				if datType.startswith(b"Img"):
					device.fillImage( datStr, datLen )
					lastSetTimeStr = str(device.lastImageTime).encode('utf-8')
					#print('sending image to browser')
					if client:
						client.send( device.devId, [('Img', device.lastImageLength, device.lastImage), ('Time', len(lastSetTimeStr), lastSetTimeStr)] )
					else:
						networkCommon.dbgPrint("no cli to forward image to")
				if datType.startswith(b"cmdResults"):
					if client:
						client.send( device.devId, [ ('cmdResults', datLen, datStr) ] )
				if datType.startswith(b"DevId"):
					networkCommon.dbgPrint( "setting devDescription %s" % datStr )
					device.description = datStr
			elif fromDorC == ord('c'): #request or command from client (browser http page)
				client = None
				if datType.startswith(b'auth'):
					with Client.clients_lock:
						if datStr in Client.activeClientLogins:
							pktAuth = datStr #the auth is active/valid
							client = Client.activeClientLogins[pktAuth]
				elif datType.startswith(b'loginUname'):
						pendingLoginUname = datStr
						networkCommon.dbgPrint( 'loginUname %s' % pendingLoginUname )
				elif datType.startswith(b'loginPass'):
					loginPass = datStr
					networkCommon.dbgPrint( 'loginPass: pendingLoginUname %s loginPass %s' % (pendingLoginUname, loginPass) )
					networkCommon.acquireLocksAndRunFunction( [Client.clients_lock, Accounts.accounts_lock], Accounts.HandleLoginAuthRequest, websocket, client, pendingLoginUname, loginPass, rcvTime )
					networkCommon.dbgPrint( "aftr acquireLocksAndRunFunction" )
				elif pktAuth != '': #a valid pktAuth has been recieved for the data packet
					networkCommon.acquireLocksAndRunFunction( [Client.clients_lock, Accounts.accounts_lock], 
							ClientWebsockHandler.handleClientWebsockRequests,
							websocket,
							pktAuth,
							datType,
							datLen,
							datStr
							)
					
			elif fromDorC == ord('f'):
				networkCommon.dbgPrint("packet from file server id %i datType %s datLen %i" %(devOrCliId, datType, datLen) )
				#print( "dat type %s" %(datType) )
				#print( "datLen %i" % (datLen) )
				#print( "datStr %s" % (datStr) )
				fSvr = FileServer.GetOrAllocateFileServer( devOrCliId )
				if datType.startswith(b'numFolders'):
					fSvr.wSock = websocket
				elif datType.startswith(b'fSvrDesc'):
					fSvr.description = datStr.decode('utf-8')
				elif datType.startswith(b'fileList') or datType.startswith(b'filePart') or datType.startswith(b'fileLen'):
					fSvr.fSvrlastDat = datStr
					fSvr.fSvrlastDatLen = datLen
					fSvr.fSvrLastCmd = datType
				elif datType.startswith(b'sndLToCli'):
					cliId = int(datStr)
					if cliId in Client.clientsById.keys():
						client = Client.clientsById[cliId]
						networkCommon.dbgPrint('fwdTo cli.Id %s' % client.devId )
						client.send( devOrCliId, [(fSvr.fSvrLastCmd, fSvr.fSvrlastDatLen, fSvr.fSvrlastDat)])
				
			mIdx += datLen
			cmdIdx += 1
			#print( " mIdx %i" % mIdx )
		if deviceWithNewCmds: #send commands immediately to device instead of waiting for device to poll for them
			cmdDatArr = Device.GetCommandListBytes(deviceWithNewCmds.cmds)
			networkCommon.dbgPrint("sending immediately to %s commands %s" % ( str(deviceWithNewCmds.devId), str(cmdDatArr) ) )
			if not deviceWithNewCmds.send( Client.svrDevId, cmdDatArr ): #put back the unsent commands
				Device.putCmdList(deviceWithNewCmds.cmds, cmdDatArr)
		if len(networkCommon.strSendError) > 0:
			networkCommon.dbgPrint(networkCommon.strSendError)
			networkCommon.strSendError = ""
	
	except websockets.exceptions.ConnectionClosedError:
		# Normal: client disconnected without a close frame
		traceback.print_exc()
		networkCommon.dbgPrint(f"WebSocket connection closed from {client_ip_address}")
	except websockets.exceptions.ConnectionClosedOK:
		# Normal: client sent close frame
		networkCommon.dbgPrint(f"WebSocket closed gracefully from {client_ip_address}")
	except Exception as e:
		# Unexpected errors
		traceback.print_exc()
		networkCommon.dbgPrint(f"WebSocket handler error: {type(e).__name__}: {e}")
	finally:
		# Cleanup: remove stale device/client references if needed
		# (optional, depending on how your device/client lifecycle works)
		pass
	networkCommon.dbgPrint( "WebsocketHandler end")