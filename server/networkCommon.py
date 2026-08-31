from netifaces import interfaces, ifaddresses, AF_INET

import base64

import threading

import http.server

import ssl
import sys
from datetime import datetime, timezone

from random import random

import socket
import threading

print_lock = threading.RLock()
def dbgPrint(strn, *args):
	with print_lock:
		if args:
			print( strn, *args )
		else:
			print( strn )
		sys.stdout.flush()

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


PACKET_HEADER_SIZE = 6        # B B H B B format -> 6 bytes total

strSendError = ""


import struct

def sendPkt(wSocket, pktNum, fromDevId, datInfoArr, fromDevType='s'):
	"""Synchronous version of sendPkt for a threaded custom WebSocket environment."""
	global strSendError
	if pktNum >= 256:
		pktNum = 0
		
	# 1. Ensure fromDevType is always a bytes object
	if isinstance(fromDevType, str):
		fromDevType_bytes = fromDevType.encode('utf-8')
	else:
		fromDevType_bytes = fromDevType

	# 2. FIX: Since lPadStr outputs bytes, do NOT call .encode() on them!
	# Concatenate them natively as bytes directly.
	sendHdr_bytes = lPadStr(3, str(pktNum)) + lPadStr(4, str(fromDevId))
	num_items_bytes = str(len(datInfoArr)).encode('utf-8')

	# Combined cleanly as raw binary bytes
	text_header_bytes = sendHdr_bytes + num_items_bytes + fromDevType_bytes

	# 3. Compile the custom protocol data array payload
	sendBytes = b''
	for dInf in datInfoArr:
		datType = dInf[0]
		datLen = dInf[1]
		dat = dInf[2]
		
		# Ensure elements are safely typed as bytes
		if isinstance(datType, str):
			datType_bytes = datType.encode('utf-8')
		else:
			datType_bytes = datType
		
		datLen_bytes = lPadStr(6, str(datLen))
		
		if isinstance(dat, str):
			dat_bytes = dat.encode('utf-8')
		else:
			dat_bytes = dat
		
		# Decode only for the padding wrapper helper if it requires a string input
		datType_str = datType_bytes.decode('utf-8', errors='ignore')
		
		# Combine the padded data block chunk
		sendBytes += rPadStr(11, datType_str) + datLen_bytes + dat_bytes
		
	try:
		# 4. Merge text headers and body payload bytes
		raw_payload_data = text_header_bytes + sendBytes
		payload_len = len(raw_payload_data)
		
		# 5. BUILD THE REQUIRED WEBSOCKET FRAME ENVELOPE (RFC 6455 Spec)
		ws_frame_header = bytearray()
		ws_frame_header.append(0x82) # Fin bit = 1, Opcode = 2 (Binary Frame)
		
		if payload_len <= 125:
			ws_frame_header.append(payload_len)
		elif payload_len <= 65535:
			ws_frame_header.append(126)
			ws_frame_header.extend(struct.pack("!H", payload_len))
		else:
			ws_frame_header.append(127)
			ws_frame_header.extend(struct.pack("!Q", payload_len))
		
		complete_ws_frame = bytes(ws_frame_header) + raw_payload_data
		
		# 6. Transmit down the network interface socket
		if hasattr(wSocket, 'request'):
			wSocket.request.sendall(complete_ws_frame)
		else:
			wSocket['handler'].request.sendall(complete_ws_frame)
		
		#dbgPrint("sendPkt completed synchronously and sent frame data")
		pktNum += 1
	except Exception as e:
		strSendError = str(e)
		dbgPrint(f"sendPkt error: {strSendError}")
		import traceback
		traceback.print_exc()
		
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

#https://stackoverflow.com/questions/50120102/python-http-server-keep-connection-alive


backend_thread = None
webSocketSvrThread = None
stop = 0


import threading
import time

def acquireLocksAndRunFunction(locks, func, *args, **kwargs):
	"""
	Safely acquires an arbitrary list of threading.RLocks across multiple ports.
	"""
	acquired_locks = []
	success = False

	while not success:
		try:
			for lock in locks:
				# 1. To safely check if another separate thread is holding the lock:
				# RLock exposes an internal counter tracking ownership.
				# If a different thread holds it, we must roll back to avoid cross-port deadlocks.
				if lock._is_owned() and threading.get_ident() != lock._owner:
					raise BlockingIOError("Lock is currently held by a different thread")
				
				# 2. Acquire normally since it belongs to us or is free
				lock.acquire()
				acquired_locks.append(lock)
				
			success = True
		
		except BlockingIOError:
			# Release held items in reverse order to clear the queue
			for lock in reversed(acquired_locks):
				lock.release()
			acquired_locks.clear()

			# Pause briefly (5 milliseconds) to let competing threads finish their operations
			time.sleep(0.005)
	
	try:
		# Execute your shared state payload safely now that protection is verified
		return func(*args, **kwargs)
	finally:
		# ALWAYS release every single lock in reverse order
		for lock in reversed(acquired_locks):
			try:
				lock.release()
			except RuntimeError:
				pass


