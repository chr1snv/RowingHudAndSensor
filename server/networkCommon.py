from netifaces import interfaces, ifaddresses, AF_INET

import base64

import threading

import http.server

import ssl
import sys
from datetime import datetime, timezone

from random import random

import socket

#import os
#import getpass

#import json

certfile = "/home/bitnami/rowingDevs/certs/client.crt"
keyfile = "/home/bitnami/rowingDevs/certs/client.key"

def get_ssl_context(certfile, keyfile):
	context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
	#print(getpass.getuser())
	context.load_cert_chain(certfile, keyfile)
	context.set_ciphers("@SECLEVEL=1:ALL")
	return context



#data is sent over the websocket in the format
	#|numData(1) | dataTypeStr (12) | deviceId(4) | dataLen(6) | data
#commands are recieved in the format
	# | num commands(1)    ||| cmd name(12) | cmd length(4) | cmd value(cmd length) |||
	#||| - |||| repeats num commands times up to CMD_BUFF_MAX_LEN

#everything except the login.html and commonFunctions.js require a vaild authorization to access
#i.e. num commands 2 with the first command being auth and a non timed out key
#auth keys are used to identify connections, if a hashed auth key is copied,
#the copied one will be one behind and disallowed access

#https://stackoverflow.com/questions/30990129/encrypt-in-python-decrypt-in-javascript


def getRandomASCIIByteArrWithLength( leng ):
	buf = bytearray()
	numRange   = b'9'[0] - b'0'[0]
	upperRange = b'Z'[0] - b'A'[0]
	lowerRange = b'z'[0] - b'a'[0]
	ovrAllRange = numRange + upperRange + lowerRange
	for i in range( 0, leng ):
		c = round( random() * ovrAllRange )
		if c <= numRange:
			buf.append( c + b'0'[0] )
		elif ( c <= numRange + upperRange ):
			buf.append( (c - numRange) + b'A'[0] )
		else:
			buf.append( (c - (numRange + upperRange) ) + b'a'[0] )
	return buf #b.decode('utf-8')



#ascii to int reverse iteration for n characters
#input is end of number (1's place)
#counts up in significance (x10), decrementing string index from start index
def atoir_n( c, n ):
	accum = 0
	mult = 1
	#print( "atoir_n d " )
	for i in range(n) :
		d = c[n-1-i]
		if( d >= ord('0') and d <= ord('9') ):
			accum += (d - b'0'[0])*mult
		else:
			break
		mult *= 10
		#print( " %c acum %i d " % ( d, accum ) )
	#print(" accum %i " % (accum) )
	return accum

#print( "atoir_n( \" 12\", 3 ) %i\n" % atoir_n( " 12", 3 ) )

def lPadStr(n, chars):
	bStr = str(chars).encode('utf-8') #left pad, another option may be str.rjust(10, '0')
	return bytes(n-len(bStr)) + bStr
	
def rPadStr(n, chars):
	if type(chars) == type(b''):
		bStr = chars
	else:
		bStr = str(chars).encode('utf-8') #left pad, another option may be str.rjust(10, '0')
	#print("bStr %s len %i" % (bStr, len(bStr)) )
	return bStr + bytes(n-len(bStr))


strSendError = ""

async def sendPkt(wSocket, pktNum, fromDevId, datInfoArr, fromDevType='s' ):
	global strSendError
	if( pktNum >= 256 ):
		pktNum = 0
	sendHdr = lPadStr( 3, str(pktNum) ) + lPadStr(4, str(fromDevId) )
	sendBytes = b''
	for dInf in datInfoArr: #datInfoArr datType, datLen, dat
		#print(dInf)
		datType = dInf[0]
		datLen = dInf[1]
		dat = dInf[2]
		sendBytes += rPadStr(11, datType) + lPadStr(6, str(datLen)) + dat
	try:
		await wSocket.send( sendHdr + str(len(datInfoArr)).encode('utf-8') + fromDevType.encode('utf-8') + sendBytes )
		pktNum += 1
	except Exception as e:
		strSendError = str(e)
		#None#print("sendPkt error: %s" % str(e) )
	return pktNum

def curMillis():
	return int(datetime.now(tz=timezone.utc).timestamp() * 1000)



svrIp = '127.0.0.1'
def getIp():
	currentIp = '127.0.0.1'
	for ifaceName in interfaces():
		addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
		if addresses[0] != '127.0.0.1' and addresses[0] != 'No IP addr' and  not addresses[0].startswith('10.8.0'):
			currentIp = addresses[0]
		#print ('%s: %s' % (ifaceName, ', '.join(addresses)))
	return currentIp




############
#concurrent / threaded http server for serving the html page
############

class HTTPServerWithShutdown(http.server.ThreadingHTTPServer):
    """HTTP server with proper shutdown and SO_REUSEADDR."""
    daemon_threads = True  # Threads exit when main thread exits
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.daemon_threads = True

def start_http_server_in_new_thread(server_address, requestHandler):
	backend_server = HTTPServerWithShutdown(server_address, requestHandler)
	context = get_ssl_context(certfile, keyfile)
	backend_server.socket = context.wrap_socket(backend_server.socket, server_side=True)

	def serve():
		try:
			backend_server.serve_forever()
		finally:
			backend_server.server_close()  # ← Properly close

	backend_thread = threading.Thread(target=serve)
	backend_thread.daemon = True
	backend_thread.start()
	return backend_server, backend_thread  # Return server so we can shutdown
"""
#https://stackoverflow.com/questions/50120102/python-http-server-keep-connection-alive
def start_http_server_in_new_thread(server_address,requestHandler):
	backend_server = http.server.ThreadingHTTPServer(server_address, requestHandler)
	context = get_ssl_context(certfile, keyfile)
	backend_server.socket = context.wrap_socket(backend_server.socket, server_side=True)
	f = lambda : backend_server.serve_forever()
	backend_thread = threading.Thread(target=f)
	backend_thread.daemon=True
	backend_thread.start()
	return backend_thread
"""

backend_thread = None
webSocketSvrThread = None
stop = 0


