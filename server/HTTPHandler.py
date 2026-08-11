import http.server

import networkCommon

import Accounts, Client, Device, FileServer

import Boat

import re, os, io

from datetime import datetime

from http.cookies import SimpleCookie

class HTTPAsyncHandler(http.server.SimpleHTTPRequestHandler):
	def __init__(self, request, client_address, server):
		#self.timeout = 10
		#request.settimeout(10)
		#enable http 1.1 to avoid tls and tcp setup time per request by 
		self.protocol_version = 'HTTP/1.1' #keeping connections open until calling self.finish()
		networkCommon.dbgPrint("HTTPAsyncHandler __init__")
		try:
			super().__init__(request, client_address, server)
		except Exception as e:
			None

	def replyWithStartFile(self, filePath, closeConn=False):
		if filePath.startswith('theFrayen'):
			filePath = '../'+ filePath
		if filePath.startswith('scenes'):
			filePath = '../theFrayen/'+ filePath 
		filePathStr = os.getcwd() + os.path.sep + filePath
		self.send_response(200)
		networkCommon.dbgPrint( filePathStr )
		if filePath.endswith('.jpg') or filePath.endswith('.ico') or filePath.endswith('.png') or filePath.endswith('.zip'):
			f = open(filePathStr, 'rb')
			if filePath.endswith('.ico'):
				networkCommon.dbgPrint("sending ico")
				self.send_header('Content-type','image/x-icon')
			elif filePath.endswith('.ico'):
				networkCommon.dbgPrint("sending jpg")
				self.send_header('Content-type','image/jpeg')
			elif filePath.endswith('.png'):
				networkCommon.dbgPrint("sending png")
				self.send_header('Content-type','image/png')
			elif filePath.endswith('.zip'):
				networkCommon.dbgPrint("sending zip")
				self.send_header('Content-type', 'application/zip')
			fileContents = f.read()
			self.send_header('Content-length', len(fileContents))
			if closeConn:
				self.send_header("Connection", "close")
			self.end_headers()
			f.close()
			self.wfile.write(fileContents)
			#if closeConn:
			#	self.close_connection = True
			#	try:
			#		self.wfile.flush()
			#		self.request.close() 
			#	except Exception as e:
			#		networkCommon.dbgPrint( e )
			return
		
		f = open(filePathStr)
		if filePath.endswith('.js'):
			networkCommon.dbgPrint("sending js")
			self.send_header('Content-type','application/javascript')
		elif filePath.endswith('.css'):
			networkCommon.dbgPrint("sending css")
			self.send_header('Content-type', 'text/css')
		else:
			networkCommon.dbgPrint("sending text")
			self.send_header('Content-type','text/html')
		self.end_headers()
		self.wfile.write(f.read().encode('utf-8'))
		f.close()

	def replyWithFile(self, filePath, finish=False):
		if filePath.startswith('theFrayen'):
			filePath = '../'+ filePath
		f = open(os.getcwd() + os.path.sep + filePath)
		self.wfile.write(f.read().encode('utf-8'))
		f.close()
		self.finish() #https://stackoverflow.com/questions/6594418/simplehttprequesthandler-close-connection-before-returning-from-do-post-method


	def do_GET(self):

		try:
			networkCommon.dbgPrint("get path " + self.path )
			parts = re.split(r"[/?&=]", self.path)
			
			pktAuth = ''
			getKeyValid = False
			
			
			if len(parts) > 2:
				getKey = parts[-1].encode('utf-8')
				(client,pktAuth) = Accounts.ClientAndPktAuthFromGetKey( getKey )
				getKeyValid = len(pktAuth) > 0
			
			# Look for the cookie in the incoming HTTP request headers
			elif "Cookie" in self.headers:
				cookie = SimpleCookie(self.headers["Cookie"])
				if "auth_key" in cookie:
					cookie_key = cookie["auth_key"].value.encode('utf-8')
					
					# Validate the token
					(client, pktAuth) = Accounts.ClientAndPktAuthFromGetKey(cookie_key)
					if pktAuth:
						getKeyValid = True
			
			networkCommon.dbgPrint('parts %s parts[-2] %s getKeyValid %i' % (str(parts), str(parts[-2]), getKeyValid) )


			if getKeyValid: #then allowed to request the following
				if parts[1] == "theFrayen.html":
					networkCommon.dbgPrint( 'parts %s' % str(parts) )
					sceneName = parts[3]
					cliId = client.cliId
					self.replyWithStartFile( "theFrayen/theFrayenBegin.html" )
					networkCommon.dbgPrint("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					self.replyWithFile( "theFrayen/theFrayenEnd.html", True )

				if parts[1] == "fileViewer.html": #file server view page
					#self.path has /index.htm
					fSvrId = int(parts[3])
					cliId = int(parts[5])
					client.devId = -1
					client.fSvrId = fSvrId #switch the client to controlling file server
					networkCommon.dbgPrint( 'setting client %i fSvrId %i' % (cliId, client.fSvrId) )
					fSvr = FileServer.GetOrAllocateFileServer( fSvrId )
					fSvr.accessingCliIds.append( cliId )
					self.replyWithStartFile( "fileViewer.html" )
					
					networkCommon.dbgPrint("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					networkCommon.dbgPrint("writing fSvrId %i" % (fSvrId))
					self.wfile.write(("<h2 id=\"fSvrId\">" + str(fSvrId) + "</h2>").encode('utf-8'))
					networkCommon.dbgPrint("finishing writing fileViewer.html")
					self.finish()
					#return
				elif parts[1] == "camControl.html": #device control page
					#self.path has /index.htm
					devId = int(parts[3])
					cliId = int(parts[5])
					client.fSvrId = -1
					client.devId = devId #switch the client to controlling device
					dev = Device.GetOrAllocateDevice( devId )
					dev.controlingCliId = cliId
					self.replyWithStartFile( "camControlBegin.html" )
					networkCommon.dbgPrint("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					networkCommon.dbgPrint("writing devId %i" % (devId))
					self.wfile.write(("<h2 id=\"devId\">" + str(devId) + "</h2>").encode('utf-8'))
					networkCommon.dbgPrint("finishing writing camControl.html")
					self.replyWithFile( "camControlEnd.html", True )
					networkCommon.dbgPrint( " camControl devId : %i cliId : %i  cli.devId : %i" % (Client.clients[cliId].devId, Client.clients[cliId].cliId, Client.clients[cliId].devId) )
					#return

				elif parts[1] == "rowing.html": #device control page
					
					self.replyWithStartFile( "rowing.html" )
					cliId = client.cliId
					networkCommon.dbgPrint("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					networkCommon.dbgPrint( "writing boats to rowing page" )
					output = io.StringIO()
					with Boat.boats_lock:
						for boatId, boat in Boat.boatsById.items():
							boatIdStr = str(boat.boatId)
							output.write('<tr>')
							output.write('<td><button onclick="selectBoat( \'' + boatIdStr + '\' )">' + \
										boatIdStr + \
										" : " + boat.name + '</button></td></tr>' )
					self.wfile.write(output.getvalue().encode('utf-8'))
					self.replyWithFile( "rowingMid.html" )

					networkCommon.dbgPrint( "writing devices to rowing page" )
					output = io.StringIO()
					with Device.devices_lock:
						for devId, dev in Device.devices.items():
							devIdStr = str(dev.devId)
							output.write('<tr>')
							output.write('<td><button onclick="addDeviceToBoat( \'' + devIdStr + '\' )">' + \
										devIdStr + \
										" : " + str(dev.description) + \
										" : " + str(Device.deviceTypes[dev.devType][0]) + '</button>'+ \
										'</td>')
							output.write('</tr>')
							networkCommon.dbgPrint( "device " + devIdStr )
					self.wfile.write(output.getvalue().encode('utf-8'))
					self.replyWithFile( "rowingEnd.html", True )
					networkCommon.dbgPrint("finishing writing rowing.html")
					#print( " rowing devId : %i cliId : %i  cli.devId : %i" % (Client.clients[cliId].devId, Client.clients[cliId].cliId, Client.clients[cliId].devId) )
					#return

				elif parts[1] == "devSelection.html": #the index / device selection / overview page
					self.send_response(200)
					self.send_header('Content-type','text/html')
					self.end_headers()

					now = datetime.now()

					output = io.StringIO()
					output.write("<html style=\"color-scheme: dark; font-family: sans;\"><head>")
					output.write("<style type=\"text/css\">")
					output.write("font-family: sans;")
					output.write("</style>")
					output.write("<script src='commonFunctions.js'></script>")
					output.write("<body style=\"background:black; background-image:url('starFieldTileBackground.jpg'); color:white; font-family:sans;\">")
					output.write("<p id=\"networkAuthText\"></p>")
					output.write("<a id=\"networkAuthLink\"></a>")
					output.write("<table><tr>")
					output.write("<td><button onclick=\"getFile(finishUrlGoto,\'devSelection.html\')\">R E F R E S H</button></td>")
					output.write("<td><h2>last refreshed  " + now.strftime("%Y-%m-%d %H:%M:%S") + "</h2></td>")
					output.write("</tr></table>")
					output.write("<table><tr>")
					output.write("<td><button onclick=\"logout()\">L O G   O U T</button></td>")
					output.write("<td><h4 style=\"margin-bottom:0px;\">Packets until auto-logout</h4></td><td><p id=\"remainingPackets\">?</p></td>")
					output.write("</tr></table>")
					networkCommon.dbgPrint("dev selec 1")
					output.write("<h1>DEVICES</h1>")
					with Client.clients_lock:
						client = Client.activeClientLogins[pktAuth]
						cliIdStr = str( client.cliId )
						output.write("<div id=\"cliId\" style=\"display:none;\">" + cliIdStr + "</div>")
					networkCommon.dbgPrint("dev selec 1.5")
					Accounts.cleanupNonRecentConnections()
					with Device.devices_lock:
						for devId, dev in Device.devices.items():
							devIdStr = str(dev.devId)
							output.write('<tr>')
							output.write('<td><button onclick="getFile(finishUrlGoto,\'camControl.html\', [[\'devId\', ' + devIdStr + '],[\'cliId\', ' + cliIdStr + ']])">' + \
										devIdStr + \
										" : " + str(dev.description) + \
										" : " + str(Device.deviceTypes[dev.devType][0]) + '</button></td>')
							output.write('</tr>')
					networkCommon.dbgPrint("dev selec 2")
					output.write("<h1>FILE SERVERS</h1>")
					with FileServer.fileSvrs_lock:
						for fSvrId, fSvr in FileServer.fileSvrs.items():
							fSvrIdStr = str(fSvr.fSvrId)
							output.write('<tr>')
							output.write('<td><button onclick="getFile(finishUrlGoto,\'fileViewer.html\', [[\'fSvrId\', ' + fSvrIdStr + '],[\'cliId\', ' + cliIdStr + ']])">' + fSvrIdStr + " : " + str(fSvr.description) + '</button></td>')
							output.write('</tr>')
					networkCommon.dbgPrint("dev selec 3")
					output.write("<h1>APPS</h1>")
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'rowing.html\')">Rowing Visualizer</button></td></tr>')
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'chrona.html\')">Stock Analyser Chrona</button></td></tr>')
					output.write("<h1>GAMES</h1>")
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'theFrayen.html\', [[\'scene\',\'sail\']])">SAIL</button></td></tr>')
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'theFrayen.html\', [[\'scene\',\'iceMountian\']])">ICE MOUNTIAN</button></td></tr>')
					output.write("<h1>LOGONS</h1>")
					#list the sessions where the user is logged in so that they can be selected and logged out
					networkCommon.dbgPrint('pktAuth %s' % pktAuth)
					output.write( '<tr>' )
					output.write( '<td><button onclick="logout()">'+ str(client.addr) + ":" + str(client.login[Client.LOGIN_REMAINING_RESPONSES_IDX])+'</button></td>')
					output.write( '</tr>' )
					output.write('</table>')
					output.write("<script>")
					output.write("function begin(){")
					output.write("thisCliId = document.getElementById(\"cliId\").innerHTML;")
					output.write("}")
					networkCommon.dbgPrint("dev selec 4")
					output.write("window.addEventListener('load', begin, false);")
					output.write("</script>")
					output.write("</body>")
					output.write("</html>")

					self.wfile.write(output.getvalue().encode('utf-8'))
					self.finish()

					#return

			elif parts[-1].endswith(".js") or parts[-1].endswith(".vsh") \
				or parts[-1].endswith(".fsh") or parts[-1].endswith(".hvtScene")\
				or parts[-1].endswith(".hvtMesh") or parts[-1].endswith(".hvtMat")\
				or parts[-1].endswith(".ico") or parts[-1].endswith(".jpg")\
				or parts[-1].endswith(".css") or parts[-1].endswith(".png") or parts[-1].endswith(".zip"):
				filePath = parts[1]
				for i in range(2,len(parts)):
					filePath += os.sep + parts[i]
				networkCommon.dbgPrint("replying with file  %s" % filePath )
				self.replyWithStartFile(filePath, True)
				self.finish()


			elif parts[1].endswith("commonFunctions.js"):
				self.replyWithStartFile(self.path, True)
				self.finish()

			else: # the login page
				networkCommon.dbgPrint( "reply with login.html getKeyValid %i" % getKeyValid )
				self.replyWithStartFile( "login.html", True )
				#self.close_connection = True
				self.finish()



		except Exception as e:#@IOError:
			networkCommon.dbgPrint(e)
			#self.send_error(404,'File Not Found: %s' % self.path)
		
		#other function exits / returns should be commented out so connection is always closed
		self.close_connection = True
		self.wfile.flush()
		#self.request.close()
		networkCommon.dbgPrint("end get handler")