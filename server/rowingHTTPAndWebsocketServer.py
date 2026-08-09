#webserver for
#esp32 rowing sensors / hud

#web cloud server for devices(sensors, file servers, security cameras, robots)
#the devices establish connection to the internet and to this server
#and then poll this server for commands (requests for images, movement commands, etc)
#the user browser javascript client connects to this server and 
#requests an interface page, images, and uses ajax to request the status of devices, commands, etc

#when a device is actively requested by a client, it increases its polling rate to 30/60 times per second
#vs when idle or timed out it polls / lets the server know it is operational every 1 or 10 seconds to reduce server load

import networkCommon

import asyncio
from websockets.server import serve
import pathlib

import time


#from Crypto import Random
#from Crypto.Cipher import AES
#import base64

from datetime import datetime

import threading

import http.server

import io
import re
import os
import numpy as np
#import cv2
#from requests_toolbelt.multipart import decoder

#classes representing things connected to the server
import Device, Client, FileServer

import WebsocketServerInit

#data serving request parsing, action taking, routing, fetching of data to return
import WebsocketHandler, HTTPHandler







def setKeepAlive(rqh):
	rqh.send_header("Connection", "keep-alive")
	rqh.send_header("keep-alive", "timeout=5, max=30")







####concurrent / thread for checking if interfaces / ip addresses have changed

def loopCheckIpHasChanged():
	#global networkCommon.svrIp, networkCommon.backend_thread
	backend_server = None
	webSocketSvrThread = None

	while(1):
		currentIp = networkCommon.getIp()
		if currentIp != networkCommon.svrIp:
			networkCommon.dbgPrint('ip has changed, rebinding servers...')
			networkCommon.svrIp = currentIp

			# Shutdown old servers properly
			if backend_server is not None:
				backend_server.shutdown()  # ← Proper shutdown
				networkCommon.backend_thread.join(timeout=5)  # Wait for thread to exit

			if networkCommon.stop != 0:
				networkCommon.stop.get_loop().call_soon_threadsafe(stop.set_result, 1)
				if webSocketSvrThread:
					webSocketSvrThread.join(timeout=5)

			# Start new servers
			server_address = (networkCommon.svrIp, httpPort)
			networkCommon.dbgPrint(f"starting httpAsyncServer at {server_address[0]} port {server_address[1]}")
			backend_server, networkCommon.backend_thread = networkCommon.start_http_server_in_new_thread(server_address, HTTPHandler.HTTPAsyncHandler)

			(tcp_server, webSocketSvrThread) = WebsocketServerInit.startWebsocketServer_in_new_thread(websocketPort)

		time.sleep(1)

networkCommon.dbgPrint( "test" )

#run the ip change checking loop (main program loop)
f = lambda : loopCheckIpHasChanged()
ipCheck_thread = threading.Thread(target=f)
#ipCheck_thread.daemon=True
ipCheck_thread.start()


#frayen server Code may be good template for syncronized multi boat race/regatta

