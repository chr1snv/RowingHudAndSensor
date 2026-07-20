
import networkCommon

svrDevId = 1

#used once a client is logged in
activeClientLogins = {} #dictionary key is authKey obtained from valid username password login

NUM_PKTS_A_LOGIN_AUTHORIZES = 10000

LOGIN_USERNAME_IDX				= 0
LOGIN_PASSWORD_IDX				= 1
LOGIN_ATTEMPTS_IDX				= 2
LOGIN_AUTHKEY_IDX				= 3
LOGIN_REMAINING_RESPONSES_IDX	= 4


async def logoutClient(client):
	login = client.login
	login[LOGIN_REMAINING_RESPONSES_IDX] = 0
	client.sendPktIdx = await networkCommon.sendPkt(client.wSock, client.sendPktIdx, svrDevId, [('logout', 0, b'')] )
	del activeClientLogins[login[LOGIN_AUTHKEY_IDX]]

class Client:
	def __init__(self):
		self.cliId = -1 #the id of the users browser session
		
		self.devId = -1 #the selected device to control
		self.fSvrId = -1 #the selected file server to read
		
		self.sendPktIdx = 0
		self.wSock = None
		self.login = None
		self.addr = None
		self.loginAttempts = 0
		self.nextAllowedLoginAttemptTime = networkCommon.curMillis()
		self.lastCommTime = None

	def getAndIncrementNextLoginAttemptTime(self, time):
		ret = self.nextAllowedLoginAttemptTime
		if time > self.nextAllowedLoginAttemptTime:
			self.nextAllowedLoginAttemptTime = self.nextAllowedLoginAttemptTime + pow(10,self.loginAttempts)
			self.loginAttempts += 1
		return ret

	def resetLoginTimeout(self):
		self.loginAttempts = 0
		self.nextAllowedLoginAttemptTime = networkCommon.curMillis() + 1000

	async def send( self, fromDevId, datInfoArr, sendWithoutAuth=False): #, auth ):
		okToSend = False
		if self.wSock != None:
			if sendWithoutAuth:
				okToSend = True
			elif self.login != None: #should it be checked that self.login[LOGIN_AUTHKEY_IDX] == auth: ?
				if self.login[LOGIN_REMAINING_RESPONSES_IDX] > 0:
					self.login[LOGIN_REMAINING_RESPONSES_IDX] -= 1
					okToSend = True
				else:
					await logoutClient(self)
					self.login = None #not sure if necessary because this client instance would then be garbage collected
			else:
				print("no login for cli not okToSend")
		else:
			print( "cant send to cliId %i without wSock" % self.cliId )

		if okToSend:
			if not sendWithoutAuth:
				remPkts = str(self.login[LOGIN_REMAINING_RESPONSES_IDX]).encode('utf-8')
				datInfoArr.append( ('remPkts', len(remPkts), remPkts) )
			print("sending to %s %i" % (self.wSock.remote_address, self.sendPktIdx) )
			self.sendPktIdx = await networkCommon.sendPkt(self.wSock, self.sendPktIdx, fromDevId, datInfoArr )
			if self.login != None:
				self.login[LOGIN_REMAINING_RESPONSES_IDX] -= 1

#list of clients by ip address
#used when logging in with username/password
clients = {}
clientsById = {}
lastAllocatedClientId = -1

def GetOrAllocateClient( ipAddr ):
	global lastAllocatedClientId
	if ipAddr not in clients:
		lastAllocatedClientId += 1
		print("allocating client %i" % lastAllocatedClientId)
		cli = Client()
		cli.cliId = lastAllocatedClientId
		clientsById[cli.cliId] = cli
		clients[ipAddr] = cli
	clients[ipAddr].lastCommTime = networkCommon.curMillis()
	print( "returning cliId %i" % clients[ipAddr].cliId )
	return clients[ipAddr]
