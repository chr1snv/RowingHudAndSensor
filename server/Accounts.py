
import Client, Device, FileServer, networkCommon

validClientLogins = {}

#username(0), password(1), loginAttempts(2), loggedinAuthKey(3), remaining authorized responses(4), client instance(5), ipaddr(6)
activeGetKeys = {} #get keys are one time use keys required to obtain scripts / files through https get


def ClientAndPktAuthFromGetKey(getKey):
	if getKey in activeGetKeys:
		client = activeGetKeys[getKey]
		pktAuth = client.login[Client.LOGIN_AUTHKEY_IDX]
		del activeGetKeys[getKey] #use the key
		return (client,pktAuth)
	else:
		return (None,'')
		
		
def cleanupNonRecentConnections():
	oneAndAHalfMinsAgo = networkCommon.curMillis() - (90 * 1000)
	for dev in list(Device.devices.keys()):
		if Device.devices[dev].lastStatusTime  < oneAndAHalfMinsAgo:
			print( "cleaning up device" )
			del Device.devices[dev]

	for cliIP in list(Client.clients.keys()):
		if Client.clients[cliIP].lastCommTime < oneAndAHalfMinsAgo:
			print( "cleaning up client by ip %s" % str(cliIP) )
			del Client.clients[cliIP]
	for cliId in list(Client.clientsById.keys()):
		if Client.clientsById[cliId].lastCommTime < oneAndAHalfMinsAgo:
			print( "cleaning up client by id %s" % str(cliId) )
			del Client.clientsById[cliId]
			
	for fSrv in list(FileServer.fileSvrs.keys()):
		if FileServer.fileSvrs[fSrv].lastCommTime < oneAndAHalfMinsAgo:
			print( "cleaning up fileServer" )
			del FileServer.fileSvrs[fSrv]