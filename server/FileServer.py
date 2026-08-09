
import networkCommon

import threading

class FileServer:
	def __init__(self):
		self.fSvrId = -1 #the id of the fileserver
		
		self.accessingCliIds = []
		
		fSvr.fSvrlastDat = ''
		fSvr.fSvrlastDatLen = 0
		fSvr.fSvrLastCmd = ''
		
		self.description = ''
		self.sendPktIdx = 0
		self.wSock = None
		self.addr = None
		self.lastCommTime = None


	def send( self, fromDevId, datInfoArr ):
		if self.wSock != None:
			self.sendPktIdx = networkCommon.sendPkt(self.wSock, self.sendPktIdx, fromDevId, datInfoArr )

fileSvrs_lock = threading.RLock()

fileSvrs = {}

def GetOrAllocateFileServer( fSvrId ):
	with fileSvrs_lock:
		if not ( fSvrId in fileSvrs.keys() ):
			fSvr = FileServer()
			fSvr.fSvrId = fSvrId
			fileSvrs[fSvrId] = fSvr
		fileSvrs[fSvrId].lastCommTime = networkCommon.curMillis()
		return fileSvrs[fSvrId]
