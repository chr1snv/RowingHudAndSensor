
import Client, Device, FileServer, networkCommon
import threading

accounts_lock = threading.RLock()
validClientLogins = {}

#username(0), password(1), loginAttempts(2), loggedinAuthKey(3), remaining authorized responses(4), client instance(5), ipaddr(6)
activeGetKeys = {} #get keys are one time use keys required to obtain scripts / files through https get


def ClientAndPktAuthFromGetKey(getKey):
	with accounts_lock:
		if getKey in activeGetKeys:
			client = activeGetKeys[getKey]
			pktAuth = client.login[Client.LOGIN_AUTHKEY_IDX]
			del activeGetKeys[getKey] #use the key
			return (client,pktAuth)
		else:
			print("getKey %s not found" % str(getKey) )
			for key in activeGetKeys:
				print(str(key) )
			return (None,'')


def cleanupNonRecentConnections():
	oneAndAHalfMinsAgo = networkCommon.curMillis() - (90 * 1000)
	with Device.devices_lock:
		for dev in list(Device.devices.keys()):
			if Device.devices[dev].lastStatusTime  < oneAndAHalfMinsAgo:
				print( "cleaning up device" )
				del Device.devices[dev]

	with Client.clients_lock:
		for cliIP in list(Client.clients.keys()):
			if Client.clients[cliIP].lastCommTime < oneAndAHalfMinsAgo:
				print( "cleaning up client by ip %s" % str(cliIP) )
				del Client.clients[cliIP]
		for cliId in list(Client.clientsById.keys()):
			if Client.clientsById[cliId].lastCommTime < oneAndAHalfMinsAgo:
				print( "cleaning up client by id %s" % str(cliId) )
				del Client.clientsById[cliId]
	with FileServer.fileSvrs_lock:
		for fSrv in list(FileServer.fileSvrs.keys()):
			if FileServer.fileSvrs[fSrv].lastCommTime < oneAndAHalfMinsAgo:
				print( "cleaning up fileServer" )
				del FileServer.fileSvrs[fSrv]


def HandleLoginAuthRequest( websocket, client, loginUname, loginPass, rcvTime):
	try:
		client = Client.GetOrAllocateClient( websocket.client_address )
		nextAllowedAttemptTime = client.getAndIncrementNextLoginAttemptTime(rcvTime)
		if nextAllowedAttemptTime  > rcvTime:
			raise Exception("rate limit wait %i secs" % ((nextAllowedAttemptTime - rcvTime )/1000) )
		if not loginUname in validClientLogins.keys():
			raise Exception("username not found")
		storedLogin = validClientLogins[loginUname]
		networkCommon.dbgPrint('UserName found')
		if storedLogin[0] == loginPass:
			networkCommon.dbgPrint('loginPassMatches')
			client.wSock = websocket #for sending data to browser client
			client.addr = websocket.client_address
			networkCommon.dbgPrint("client.addr %s" % str(client.addr) )
			client.resetLoginTimeout()
			authKey = networkCommon.getRandomASCIIByteArrWithLength(16).decode('utf-8').encode('utf-8')
			
			storedLogin[Client.LOGIN_ATTEMPTS_IDX] = 0
			storedLogin[Client.LOGIN_AUTHKEY_IDX] = authKey
			storedLogin[Client.LOGIN_REMAINING_RESPONSES_IDX] = Client.NUM_PKTS_A_LOGIN_AUTHORIZES
			
			client.login = storedLogin
			networkCommon.dbgPrint("setting authKey %s as active" % authKey)
			Client.activeClientLogins[authKey] = client
			client.send( Client.svrDevId, [('auth', len(authKey), authKey)] )
			networkCommon.dbgPrint('sent auth to client and set login for cliId %s' % str(client.cliId) )
			#login success path
		else:
			networkCommon.dbgPrint("password doesn't match")
			client.send( Client.svrDevId, [('authErr', 0, b'')], True )
	except Exception as e:
		networkCommon.dbgPrint(' %s' % e)
		client.send( Client.svrDevId, [('authErr', 0, b'')], True )


