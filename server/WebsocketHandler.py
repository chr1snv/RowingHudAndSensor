import socket
import networkCommon, Device, Client, Accounts

import DeviceWebsockHandler

import Boat

import BoatWebsockHandler


import struct

import websockets

#https://www.optimizationcore.com/coding/websocket-python-parsing-binary-frames-from-a-tcp-socket/
async def websocketHandler(websocket):
	# Gain access to the underlying python transport socket
	writer = websocket.transport.get_extra_info('socket')
	if writer:
	    # Disable Nagle's algorithm on the server backend
	    writer.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

	global strSendError
	try:
		async for msg in websocket:#for _ in range(3):
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
						await device.send( Client.svrDevId, [('getDevDesc', 0, b'')] )
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
							if not await device.send( Client.svrDevId, cmdDatArr ):
								Device.putCmdList( deviceWithNewCmds.cmds, cmdDatArr )
						lastStatTimeStr = str(device.lastStatusTime).encode('utf-8')
						if client:
							await client.send( device.devId, [('Stat', len(device.postStatus), device.postStatus), ('Time', len(lastStatTimeStr), lastStatTimeStr)] )
						else:
							networkCommon.dbgPrint("no cli to forward stat to")
					if datType.startswith(b"Set"):
						device.fillSettings( datStr, datLen )
						lastSetTimeStr = str(device.lastSettingsTime).encode('utf-8')
						if client:
							await client.send( device.devId, [('Set', device.lastSettingsLen, device.lastSettings), ('Time', len(lastSetTimeStr), lastSetTimeStr)] )
						else:
							networkCommon.dbgPrint("no cli to forward set to")
						networkCommon.dbgPrint( "requesting getDevDesc" )
						await device.send( Client.svrDevId, [('getDevDesc', 0, b'')] )
					if datType.startswith(b"Img"):
						device.fillImage( datStr, datLen )
						lastSetTimeStr = str(device.lastImageTime).encode('utf-8')
						#print('sending image to browser')
						if client:
							await client.send( device.devId, [('Img', device.lastImageLength, device.lastImage), ('Time', len(lastSetTimeStr), lastSetTimeStr)] )
						else:
							networkCommon.dbgPrint("no cli to forward image to")
					if datType.startswith(b"cmdResults"):
						if client:
							await client.send( device.devId, [ ('cmdResults', datLen, datStr) ] )
					if datType.startswith(b"DevId"):
						networkCommon.dbgPrint( "setting devDescription %s" % datStr )
						device.description = datStr
				elif fromDorC == ord('c'): #request or command from client (browser http page)
					client = None
					if datType.startswith(b'auth'):
						if datStr in Client.activeClientLogins:
							pktAuth = datStr #the auth is active/valid
							client = Client.activeClientLogins[pktAuth]
					elif datType.startswith(b'loginUname'):
							pendingLoginUname = datStr
							networkCommon.dbgPrint( 'loginUname %s' % pendingLoginUname )
					elif datType.startswith(b'loginPass'):
						loginPass = datStr
						networkCommon.dbgPrint( 'loginPass: pendingLoginUname %s loginPass %s' % (pendingLoginUname, loginPass) )
						try:
							client = Client.GetOrAllocateClient( websocket.remote_address )
							nextAllowedAttemptTime = client.getAndIncrementNextLoginAttemptTime(rcvTime)
							if nextAllowedAttemptTime  > rcvTime:
								raise Exception("rate limit wait %i secs" % ((nextAllowedAttemptTime - rcvTime )/1000) )
							if not pendingLoginUname in Accounts.validClientLogins.keys():
								raise Exception("username not found")
							storedLogin = Accounts.validClientLogins[pendingLoginUname]
							networkCommon.dbgPrint('UserName found')
							if storedLogin[0] == loginPass:
								networkCommon.dbgPrint('loginPassMatches')
								client.wSock = websocket #for sending data to browser client
								client.addr = websocket.remote_address
								networkCommon.dbgPrint("client.addr %s" % str(client.addr) )
								client.resetLoginTimeout()
								authKey = networkCommon.getRandomASCIIByteArrWithLength(16).decode('utf-8').encode('utf-8')
								
								storedLogin[Client.LOGIN_ATTEMPTS_IDX] = 0
								storedLogin[Client.LOGIN_AUTHKEY_IDX] = authKey
								storedLogin[Client.LOGIN_REMAINING_RESPONSES_IDX] = Client.NUM_PKTS_A_LOGIN_AUTHORIZES
								
								client.login = storedLogin
								networkCommon.dbgPrint("setting authKey %s as active" % authKey)
								Client.activeClientLogins[authKey] = client
								await client.send( Client.svrDevId, [('auth', len(authKey), authKey)] )
								networkCommon.dbgPrint('sent auth to client and set login for cliId %s' % str(client.cliId) )
							else:
								networkCommon.dbgPrint("password doesn't match")
								await client.send( Client.svrDevId, [('authErr', 0, b'')], True )
						except Exception as e:
							networkCommon.dbgPrint(' %s' % e)
							await client.send( Client.svrDevId, [('authErr', 0, b'')], True )
					elif pktAuth != '': #a valid pktAuth has been recieved for the data packet
						client = Client.activeClientLogins[pktAuth]
						client.wSock = websocket
						networkCommon.dbgPrint('pktAuth valid')
						#the following requests are allowed
						authDCmdRequested = False
						if client.login == None:
							networkCommon.dbgPrint("shouldn't happen, pktAuth is valid though client doesn't have a login")
						elif datType.startswith(b'getKey'): #generate a get key make it active and return it
							authDCmdRequested = True
							getKey = networkCommon.getRandomASCIIByteArrWithLength(16).decode('utf-8').encode('utf-8');
							Accounts.activeGetKeys[getKey] = client
							#print("getKey 2 client.wSock %s client.websocket.remote_address %s" % (str(client.wSock), str(client.wSock.remote_address)) )
							await client.send(Client.svrDevId, [('getKey', len(getKey), getKey)])
						elif datType.startswith(b'logout'):
							authDCmdRequested = True
							key = datStr
							if key == client.login[Client.LOGIN_AUTHKEY_IDX]: #only allow user to logout themselves
								await Client.logoutClient(client)

						elif datType.startswith(b'Boat'):
							await BoatWebsockHandler.handleWebSockClientDeviceRequests( client, datType, datStr )

						#device = None
						elif not authDCmdRequested and client.devId >= 0:
							networkCommon.dbgPrint("client.devId %i client.fSvrId %i" % (client.devId, client.fSvrId) )
							DeviceWebsockHandler.handleWebSockClientDeviceRequests(client, datType, datStr)

						elif client.fSvrId >= 0:
							networkCommon.dbgPrint('client.devId %s' % client.devId )
							if client.fSvrId in FileServer.fileSvrs.keys():
								fSvr = FileServer.fileSvrs[client.fSvrId]
								if datType.startswith(b'fileList') or datType.startswith(b'fileLen') or datType.startswith(b'fetchFile'):
									networkCommon.dbgPrint('%s requested from client for fSvrId %i fldr %s' % (datType, client.fSvrId,datStr))
									await fSvr.send( client.cliId, [(datType, datLen, datStr)] )
							else:
								networkCommon.dbgPrint( "fSvrId %i not in fileSvrs" % client.fSvrId )
						
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
							await client.send( devOrCliId, [(fSvr.fSvrLastCmd, fSvr.fSvrlastDatLen, fSvr.fSvrlastDat)])
					
				mIdx += datLen
				cmdIdx += 1
				#print( " mIdx %i" % mIdx )
			if deviceWithNewCmds: #send commands immediately to device instead of waiting for device to poll for them
				cmdDatArr = Device.GetCommandListBytes(deviceWithNewCmds.cmds)
				networkCommon.dbgPrint("sending immediately to %s commands %s" % ( str(deviceWithNewCmds.devId), str(cmdDatArr) ) )
				if not await deviceWithNewCmds.send( Client.svrDevId, cmdDatArr ): #put back the unsent commands
					Device.putCmdList(deviceWithNewCmds.cmds, cmdDatArr)
			if len(networkCommon.strSendError) > 0:
				networkCommon.dbgPrint(networkCommon.strSendError)
				networkCommon.strSendError = ""
	
	except websockets.exceptions.ConnectionClosedError:
		# Normal: client disconnected without a close frame
		networkCommon.dbgPrint(f"WebSocket connection closed from {websocket.remote_address}")
	except websockets.exceptions.ConnectionClosedOK:
		# Normal: client sent close frame
		networkCommon.dbgPrint(f"WebSocket closed gracefully from {websocket.remote_address}")
	except Exception as e:
		# Unexpected errors
		networkCommon.dbgPrint(f"WebSocket handler error: {type(e).__name__}: {e}")
	finally:
		# Cleanup: remove stale device/client references if needed
		# (optional, depending on how your device/client lifecycle works)
		pass