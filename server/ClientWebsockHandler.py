import Client
import Accounts
import networkCommon
import BoatWebsockHandler
import DeviceWebsockHandler

def handleClientWebsockRequests(websocket, pktAuth, datType, datLen, datStr):
	client = Client.activeClientLogins[pktAuth]
	client.wSock = websocket
	networkCommon.dbgPrint('pktAuth valid datType %s' % datType)
	#the following requests are allowed
	authDCmdRequested = False
	if client.login == None:
		networkCommon.dbgPrint("shouldn't happen, pktAuth is valid though client doesn't have a login")
	elif datType.startswith(b'getKey'): #generate a get key make it active and return it
		authDCmdRequested = True
		getKey = networkCommon.getRandomASCIIByteArrWithLength(16).decode('utf-8').encode('utf-8');
		Accounts.activeGetKeys[getKey] = client
		print("getKey %s client.websocket.remote_address %s" % (getKey, str(client.wSock.client_address)) )
		client.send(Client.svrDevId, [('getKey', len(getKey), getKey)])
	elif datType.startswith(b'logout'):
		authDCmdRequested = True
		key = datStr
		if key == client.login[Client.LOGIN_AUTHKEY_IDX]: #only allow user to logout themselves
			Client.logoutClient(client)

	elif datType.startswith(b'Boat'):
		networkCommon.dbgPrint("Handle client Boat request")
		BoatWebsockHandler.handleWebSockClientDeviceRequests( client, datType, datStr )

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
				fSvr.send( client.cliId, [(datType, datLen, datStr)] )
		else:
			networkCommon.dbgPrint( "fSvrId %i not in fileSvrs" % client.fSvrId )