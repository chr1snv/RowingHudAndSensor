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


#data serving request parsing, action taking, routing, fetching of data to return
import WebsocketHandler, HTTPHandler


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




def setKeepAlive(rqh):
	rqh.send_header("Connection", "keep-alive")
	rqh.send_header("keep-alive", "timeout=5, max=30")










########
###asyncio websocket server (concurrent event loops)
########
async def startWebsocketServer():
	global stop
	print("start websocket server init")
	ssl_context = networkCommon.get_ssl_context(networkCommon.certfile, networkCommon.keyfile)

	stop = asyncio.Future()

	print( "serving websocket at %s port %i" % (networkCommon.svrIp, websocketPort) )
	#https://stackoverflow.com/questions/67810506/websockets-exceptions-connectionclosederror-code-1011-unexpected-error-no
	async with serve(WebsocketHandler.websocketHandler, networkCommon.svrIp, websocketPort, ping_interval=30, ping_timeout=30, ssl=ssl_context) as ws:
		print('ws before await stop')
		await stop
		ws.close()
		print('ws close called')


def startWebsocketServer_in_new_thread():
	f = lambda : asyncio.run(startWebsocketServer())#, loop)
	wsThread = threading.Thread(target=f)
	wsThread.daemon=True
	wsThread.start()
	return wsThread

####concurrent / thread for checking if interfaces / ip addresses have changed

def loopCheckIpHasChanged():
	#global networkCommon.svrIp, networkCommon.backend_thread
	backend_server = None
	webSocketSvrThread = None

	while(1):
		currentIp = networkCommon.getIp()
		if currentIp != networkCommon.svrIp:
			print('ip has changed, rebinding servers...')
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
			print(f"starting httpAsyncServer at {server_address[0]} port {server_address[1]}")
			backend_server, networkCommon.backend_thread = networkCommon.start_http_server_in_new_thread(server_address, HTTPHandler.HTTPAsyncHandler)

			webSocketSvrThread = startWebsocketServer_in_new_thread()

		time.sleep(1)

#run the ip change checking loop (main program loop)
f = lambda : loopCheckIpHasChanged()
ipCheck_thread = threading.Thread(target=f)
#ipCheck_thread.daemon=True
ipCheck_thread.start()



"""
import asyncio
from websockets.server import serve
from enum import Enum
import queue
import time
import pathlib
import ssl
import traceback

class GameState(Enum):
	GatheringPlayers = 0
	InProgress       = 1
	Completed        = 2

openGames = queue.Queue()

inProgressGames = {}

class Game:
	def __init__(self):
		self.initTime   = time.time() #seconds since epoch
		self.svrUid     = 0
		self.maxPlayers = 0
		self.clients    = []
		self.status     = GameState.GatheringPlayers
	def toStr(self):
		cliStr = str( len(self.clients) ) + ","
		for cli in self.clients:
			cliStr += str(cli[1]) + ','
		return "game %s %i %s %i" % (self.svrUid, self.maxPlayers, cliStr, int(self.status.value))
	async def updateClient( self, cliUid, hdg=-1, x=-1, y=-1, wayps=-1, nextWayPDist=-1, compTime=-1 ):
		for cli in self.clients:
			if cli[1] == cliUid:
				if hdg != -1:
					cli[2] = hdg
				if x != -1:
					cli[3] = x
				if y != -1:
					cli[4] = y
				if wayps != -1:
					cli[5] = wayps
				if nextWayPDist != -1:
					cli[6] = nextWayPDist
				if compTime != -1:
					cli[7] = compTime
				await NotifyGameClients(self, "cliUpd %i %f %f %f %i %f %f" % 
					(cliUid, hdg, x, y, wayps, nextWayPDist, compTime) )

async def NotifyGameClients( game, msgStr ):
	notifStr = "gmInf " + msgStr
	print( "notifying numClients %i %s" % (len(game.clients), msgStr) )
	idx = 0
	for client in game.clients:
		print( "client %i %i" % (idx, client[1]) ) 
		idx += 1
		try:
			print( "sending" )
			await client[0].send( notifStr )
		except Exception as e: #the client disconnected
			print("error sending status to %i excpt: %s" % (client[1],e) )
			try:
				game.clients.remove(client)
				print( "succesfully removed disconnected client %i" % client[1] )
			except Exception as e:
				print(e)
	return ( len(game.clients) > 1 )
	print( "notify game clients end" )


async def clientAppendToGame( game, cliWebSocket, cliUid ):
	cliInfo    = [0] * 7
	cliInfo[0] = cliWebSocket
	cliInfo[1] = cliUid
	print( "len cliInfo %i" % (len(cliInfo)) )
	game.clients.append( cliInfo ) #append to game players
	plrJoinedNotifStr = "joined %i %s" % ( cliUid, game.toStr() )
	return await NotifyGameClients( game, plrJoinedNotifStr )


#add the client uid to the first avaliable open game
#and notify the players
#when the game is full move it to in progress games
#return the game server uid for lookup

async def clientJoinFirstOpenGame( clientWebsocket, clientUid ):
	statusStr = "clnt joined "
	try:
		plrsInGame = False
		while( not plrsInGame ):
			opnGame = openGames.queue[0]
			plrsInGame = await clientAppendToGame( opnGame, clientWebsocket, clientUid )
			if( len( opnGame.clients ) > opnGame.maxPlayers ):
				opnGame.status = GameState.InProgress
				openGames.get() #remove from queue
			if not plrsInGame:
				openGames.get() #players left remove game
		statusStr += "%i %s" % ( clientUid, opnGame.toStr() )
	except IndexError:
		statusStr += "-1" #no openGames (games waiting for players)
	await clientWebsocket.send( statusStr )
	print( "clientJoinFirstOpenGame end" )



async def echo(websocket):
	async for message in websocket:
		print("rcvd msg: %s" % (message))
		try:
			msgParts = message.split(" ")
			nextIsNumPlayers = False
			clientUid = 0
			nextIsUid = False
			newGameState = None
			clientFoundGameSvrUid = -1
			if msgParts[0] == "cliUpdS":
				svrUid    = int(msgParts[1])
				cliUid    = int(msgParts[2])
				game = inProgressGames.get( svrUid )
				cliBotHdg         = float(msgParts[3])
				cliBoatX          = float(msgParts[4])
				cliBoatY          = float(msgParts[5])
				cliBouysRounded   = int(msgParts[6])
				cliDistToNextBouy = float(msgParts[7])
				cliCompTime       = float(msgParts[8])
				await game.updateClient( cliUid, cliBotHdg, cliBoatX, cliBoatY,
					cliBouysRounded, cliDistToNextBouy, cliCompTime )
			elif msgParts[0] == "clientStarted":
				clientLookingForGame = True
				clientUid = int(msgParts[2])
				await clientJoinFirstOpenGame( websocket, clientUid )
			elif msgParts[0] == "serverStarted":
				newGameState = Game()
				newGameState.svrUid = int(msgParts[4])
				newGameState.maxPlayers = int(msgParts[2])
				openGames.put( newGameState )
				inProgressGames.setdefault( newGameState.svrUid, newGameState )
				plrsInGame = await clientAppendToGame( newGameState, websocket, newGameState.svrUid )
				str = ( 'svr newGameSvrId %i %s' % 
					(newGameState.svrUid, 
					newGameState.toStr()) )
				print( str )
				await websocket.send( str )
			elif msgParts[0] == "svrStartGame":
				game = inProgressGames.get( int(msgParts[1]) )
				game.status =  GameState.InProgress
				startedNotifStr = "gameStarted"
				await NotifyGameClients(game, startedNotifStr)
		except Exception as e:
			print( "error handling input %s" % e)
			print( traceback.format_exc() )
	print("echo func end")

from http import HTTPStatus

def health_check(connection, request):
	if request.path == "/test":
		return connection.respond(HTTPStatus.OK, b"OK\n")
#import logging
async def main():
	print("starting server")
	ip = "172.26.2.219"
	port = 3479

	#logging.basicConfig(
	#    format="%(message)s",
	#    level=logging.DEBUG,
	#)

	#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
	ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
	#localhost_pem =  pathlib.Path(__file__).with_name("privkey.pem")
	localhost_pem =  pathlib.Path(__file__).with_name("mycert.pem")
	print(localhost_pem)
	ssl_context.load_cert_chain(localhost_pem)
	#ssl_context.load_verify_locations(localhost_pem)

	async with serve(echo, ip, port, ssl=ssl_context):
		print( "serving at %s port %i" % (ip, port) )
		await asyncio.get_running_loop().create_future()

asyncio.run(main())
"""

