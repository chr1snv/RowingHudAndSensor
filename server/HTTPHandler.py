import http.server

import re, os

class HTTPAsyncHandler(http.server.SimpleHTTPRequestHandler):
	def __init__(self, request, client_address, server):
		#enable http 1.1 to avoid tls and tcp setup time per request by 
		self.protocol_version = 'HTTP/1.1' #keeping connections open until calling self.finish()
		try:
			super().__init__(request, client_address, server)
		except Exception as e:
			None

	def replyWithStartFile(self, filePath):
		if filePath.startswith('theFrayen'):
			filePath = '../'+ filePath
		if filePath.startswith('scenes'):
			filePath = '../theFrayen/'+ filePath 
		filePathStr = os.getcwd() + os.path.sep + filePath
		self.send_response(200)
		print( filePathStr )
		if filePath.endswith('.jpg') or filePath.endswith('.ico') or filePath.endswith('.png') or filePath.endswith('.zip'):
			f = open(filePathStr, 'rb')
			if filePath.endswith('.ico'):
				print("sending ico")
				self.send_header('Content-type','image/x-icon')
			elif filePath.endswith('.ico'):
				print("sending jpg")
				self.send_header('Content-type','image/jpeg')
			elif filePath.endswith('.png'):
				print("sending png")
				self.send_header('Content-type','image/png')
			elif filePath.endswith('.zip'):
				print("sending zip")
				self.send_header('Content-type', 'application/zip')
			fileContents = f.read()
			self.send_header('Content-length', len(fileContents))
			self.end_headers()
			f.close()
			self.wfile.write(fileContents)
			return
		
		f = open(filePathStr)
		if filePath.endswith('.js'):
			print("sending js")
			self.send_header('Content-type','application/javascript')
		elif filePath.endswith('.css'):
			print("sending css")
			self.send_header('Content-type', 'text/css')
		else:
			print("sending text")
			self.send_header('Content-type','text/html')
		self.end_headers()
		self.wfile.write(f.read().encode('utf-8'))
		f.close()

	def replyWithEndFile(self, filePath):
		if filePath.startswith('theFrayen'):
			filePath = '../'+ filePath
		f = open(os.getcwd() + os.path.sep + filePath)
		self.wfile.write(f.read().encode('utf-8'))
		f.close()
		self.finish() #https://stackoverflow.com/questions/6594418/simplehttprequesthandler-close-connection-before-returning-from-do-post-method


	def do_GET(self):

		try:
			#print("get path " + self.path )
			parts = re.split(r"[/?&=]", self.path)
			pktAuth = ''
			getKeyValid = False
			if len(parts) > 2:
				getKey = parts[-1].encode('utf-8')
				(client,pktAuth) = ClientAndPktAuthFromGetKey( getKey )
				getKeyValid = len(pktAuth) > 0
			print('parts %s parts[-2] %s getKeyValid %i' % (str(parts), str(parts[-2]), getKeyValid) )

			if getKeyValid: #then allowed to request the following
				if parts[1] == "theFrayen.html":
					print( 'parts %s' % str(parts) )
					sceneName = parts[3]
					cliId = client.cliId
					self.replyWithStartFile( "theFrayen/theFrayenBegin.html" )
					print("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					self.replyWithEndFile( "theFrayen/theFrayenEnd.html" )

				if parts[1] == "fileViewer.html": #file server view page
					#self.path has /index.htm
					fSvrId = int(parts[3])
					cliId = int(parts[5])
					client.devId = -1
					client.fSvrId = fSvrId #switch the client to controlling file server
					print( 'setting client %i fSvrId %i' % (cliId, client.fSvrId) )
					fSvr = FileServer.GetOrAllocateFileServer( fSvrId )
					fSvr.accessingCliIds.append( cliId )
					self.replyWithStartFile( "fileViewer.html" )
					
					print("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					print("writing fSvrId %i" % (fSvrId))
					self.wfile.write(("<h2 id=\"fSvrId\">" + str(fSvrId) + "</h2>").encode('utf-8'))
					print("finishing writing fileViewer.html")
					self.finish()
					return
				elif parts[1] == "camControl.html": #device control page
					#self.path has /index.htm
					devId = int(parts[3])
					cliId = int(parts[5])
					client.fSvrId = -1
					client.devId = devId #switch the client to controlling device
					dev = Device.GetOrAllocateDevice( devId )
					dev.controlingCliId = cliId
					self.replyWithStartFile( "camControlBegin.html" )
					print("writing cliId %i" % (cliId))
					self.wfile.write(("<div id=\"cliId\" style=\"display:none;\">" + str(cliId) + "</div>").encode('utf-8'))
					print("writing devId %i" % (devId))
					self.wfile.write(("<h2 id=\"devId\">" + str(devId) + "</h2>").encode('utf-8'))
					print("finishing writing camControl.html")
					self.replyWithEndFile( "camControlEnd.html" )
					print( " camControl devId : %i cliId : %i  cli.devId : %i" % (Client.clients[cliId].devId, Client.clients[cliId].cliId, Client.clients[cliId].devId) )
					return

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
					output.write("<table><tr>")
					output.write("<td><button onclick=\"getFile(finishUrlGoto,\'devSelection.html\')\">R E F R E S H</button></td>")
					output.write("<td><h2>last refreshed  " + now.strftime("%Y-%m-%d %H:%M:%S") + "</h2></td>")
					output.write("</tr></table>")
					output.write("<table><tr>")
					output.write("<td><button onclick=\"logout()\">L O G   O U T</button></td>")
					output.write("<td><h4 style=\"margin-bottom:0px;\">Packets until auto-logout</h4></td><td><p id=\"remainingPackets\">?</p></td>")
					output.write("</tr></table>")
					print("dev selec 1")
					output.write("<h1>DEVICES</h1>")
					client = Client.activeClientLogins[pktAuth]
					cliIdStr = str( client.cliId )
					output.write("<div id=\"cliId\" style=\"display:none;\">" + cliIdStr + "</div>")
					print("dev selec 1.5")
					cleanupNonRecentConnections()
					for devId, dev in Device.devices.items():
						devIdStr = str(dev.devId)
						output.write('<tr>')
						output.write('<td><button onclick="getFile(finishUrlGoto,\'camControl.html\', [[\'devId\', ' + devIdStr + '],[\'cliId\', ' + cliIdStr + ']])">' + devIdStr + " : " + str(dev.description) + '</button></td>')
						output.write('</tr>')
					print("dev selec 2")
					output.write("<h1>FILE SERVERS</h1>")
					for fSvrId, fSvr in FileServer.fileSvrs.items():
						fSvrIdStr = str(fSvr.fSvrId)
						output.write('<tr>')
						output.write('<td><button onclick="getFile(finishUrlGoto,\'fileViewer.html\', [[\'fSvrId\', ' + fSvrIdStr + '],[\'cliId\', ' + cliIdStr + ']])">' + fSvrIdStr + " : " + str(fSvr.description) + '</button></td>')
						output.write('</tr>')
					print("dev selec 3")
					output.write("<h1>APPS</h1>")
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'rowing.html\')">Rowing Visualizer</button></td></tr>')
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'chrona.html\')">Stock Analyser Chrona</button></td></tr>')
					output.write("<h1>GAMES</h1>")
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'theFrayen.html\', [[\'scene\',\'sail\']])">SAIL</button></td></tr>')
					output.write('<tr><td><button onclick="getFile(finishUrlGoto,\'theFrayen.html\', [[\'scene\',\'iceMountian\']])">ICE MOUNTIAN</button></td></tr>')
					output.write("<h1>LOGONS</h1>")
					#list the sessions where the user is logged in so that they can be selected and logged out
					print('pktAuth %s' % pktAuth)
					output.write( '<tr>' )
					output.write( '<td><button onclick="logout()">'+ str(client.addr) + ":" + str(client.login[Client.LOGIN_REMAINING_RESPONSES_IDX])+'</button></td>')
					output.write( '</tr>' )
					output.write('</table>')
					output.write("<script>")
					output.write("function begin(){")
					output.write("thisCliId = document.getElementById(\"cliId\").innerHTML;")
					output.write("}")
					print("dev selec 4")
					output.write("window.addEventListener('load', begin, false);")
					output.write("</script>")
					output.write("</body>")
					output.write("</html>")

					self.wfile.write(output.getvalue().encode('utf-8'))
					self.finish()

					return

			elif parts[-1].endswith(".js") or parts[-1].endswith(".vsh") \
				or parts[-1].endswith(".fsh") or parts[-1].endswith(".hvtScene")\
				or parts[-1].endswith(".hvtMesh") or parts[-1].endswith(".hvtMat")\
				or parts[-1].endswith(".ico") or parts[-1].endswith(".jpg")\
				or parts[-1].endswith(".css") or parts[-1].endswith(".png") or parts[-1].endswith(".zip"):
				filePath = parts[1]
				for i in range(2,len(parts)):
					filePath += os.sep + parts[i]
				print("replying with file  %s" % filePath )
				self.replyWithStartFile(filePath)
				self.finish()


			elif parts[1].endswith("commonFunctions.js"):
				self.replyWithStartFile(self.path)
				self.finish()

			else: # the login page
				print( "reply with login.html getKeyValid %i" % getKeyValid )
				self.replyWithStartFile( "login.html" )
				self.finish()
			
			print("end get handler")

		except Exception as e:#@IOError:
			print(e)
			#self.send_error(404,'File Not Found: %s' % self.path)