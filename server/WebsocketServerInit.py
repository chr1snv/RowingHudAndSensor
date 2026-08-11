import socketserver
import socket
import threading
import struct

import networkCommon
import Client
import Accounts

import WebsocketHandler

import hashlib
import base64

class ThreadedBinaryTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	"""Native OS-level threaded TCP server. Automatically spawns a private thread per connection."""
	allow_reuse_address = True
	
	def __init__(self, server_address, RequestHandlerClass, ssl_context=None):
		self.ssl_context = ssl_context
		super().__init__(server_address, RequestHandlerClass)

	def get_request(self):
		"""Intercepts the connection and wraps it in SSL securely."""
		newsock, fromaddr = self.socket.accept()
		if self.ssl_context:
			try:
				# Atomically upgrade the connection to an SSL/TLS socket
				newsock = self.ssl_context.wrap_socket(newsock, server_side=True)
			except Exception as e:
				print(f"SSL Handshake failed for client {fromaddr} (Likely browser ssl cert rejection): {e}")
				# Properly clean up the socket if the handshake aborts
				try:
					newsock.close()
				except:
					pass
				# Return a dummy dead socket to allow socketserver to cycle without breaking
				dummy_sock = socket.socket()
				dummy_sock.close()
				return dummy_sock, fromaddr
		return newsock, fromaddr

class BinaryRequestHandler(socketserver.StreamRequestHandler):
	"""Handles data transmission frames for an individual rowing machine / client connection."""

	def handle(self):
		print(f"New connection interface established from: {self.client_address}")
		self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

		try:
			# 1. CAPTURE THE HTTP UPGRADE HANDSHAKE
			# Read until the standard HTTP header termination double-newline sequence (\r\n\r\n)
			handshake_data = b""
			while b"\r\n\r\n" not in handshake_data:
				chunk = self.rfile.read(1)
				if not chunk:
					return
				handshake_data += chunk
				if len(handshake_data) > 4096: # Emergency buffer overflow sanity guard
					return

			handshake_text = handshake_data.decode('utf-8', errors='ignore')
			#print(handshake_text)
			
			# 2. EXTRACT THE WEBSOCKET SECURITY KEY
			ws_key = None
			for line in handshake_text.split("\r\n"):
				if line.lower().startswith("sec-websocket-key:"):
					# Split on the first colon and strip all leading/trailing spaces
					ws_key = line.split(":", 1)[1].strip()
					break

			if not ws_key:
				print("Aborting: Connection request did not contain a valid Sec-WebSocket-Key.")
				return

			# 3. CALCULATE THE RESPONSE KEY (RFC 6455 Spec Requirement)
			GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
			accept_input = ws_key + GUID
			sha1_hash = hashlib.sha1(accept_input.encode('utf-8')).digest()
			accept_key = base64.b64encode(sha1_hash).decode('utf-8')

			# 4. SEND THE VALID VALIDATION RESPONSE KEY TO CLIENT
			response_headers = (
				"HTTP/1.1 101 Switching Protocols\r\n"
				"Upgrade: websocket\r\n"
				"Connection: Upgrade\r\n"
				f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
			)
			self.request.sendall(response_headers.encode('utf-8'))
			print(f"Handshake complete! Connection upgraded to WebSocket cleanly for {self.client_address}")

			# 5. ENTER THE WEBSOCKET FRAMING DECODER LOOP
			while True:
				# Read exactly 2 bytes for the header
				head_bytes = self.rfile.read(2)

				# CRITICAL FIX: If head_bytes is empty, the client disconnected!
				# Break the loop cleanly so the thread can shut down.
				if not head_bytes or len(head_bytes) == 0:
					print("Client disconnected socket cleanly.")
					break
					
				# Handle fragmented network delivery safely
				while len(head_bytes) < 2:
					more = self.rfile.read(2 - len(head_bytes))
					if not more:
						return # Socket died midway
					head_bytes += more

				b1, b2 = head_bytes[0], head_bytes[1]
				
				# Check fin flag, and track data format opcodes (Text=0x1, Binary=0x2, Close=0x8)
				fin = (b1 >> 7) & 1
				opcode = b1 & 0x0F
				
				if opcode == 0x8: # Client initiated a clean disconnect close frame request
					print(f"Client sent connection close frame opcode.")
					break

				# The spec mandates that client-to-server frames must always be masked
				is_masked = (b2 >> 7) & 1
				payload_len = b2 & 0x7F

				# Parse extended message data length fields based on spec sizes
				if payload_len == 126:
					ext_len_bytes = self.rfile.read(2)
					payload_len = struct.unpack("!H", ext_len_bytes)[0]
				elif payload_len == 127:
					ext_len_bytes = self.rfile.read(8)
					payload_len = struct.unpack("!Q", ext_len_bytes)[0]

				# Extract the 4-byte cryptographic masking key array
				mask_key = b""
				if is_masked:
					mask_key = self.rfile.read(4)

				# Fetch the raw encrypted payload data array blocks
				raw_payload = b""
				remaining = payload_len
				while remaining > 0:
					chunk = self.rfile.read(min(remaining, 4096))
					if not chunk:
						return
					raw_payload += chunk
					remaining -= len(chunk)

				# Unmask the binary bytes payload array using the key via XOR slicing
				unmasked_payload = bytearray(payload_len)
				if is_masked:
					for i in range(payload_len):
						unmasked_payload[i] = raw_payload[i] ^ mask_key[i % 4]
				else:
					unmasked_payload = raw_payload

				# 6. PASS CLEAN BINARY MESSAGE TO ROUTER
				# This executes natively inside a private thread! 
				# You can use standard threading.RLock here smoothly!
				msg_bytes = bytes(unmasked_payload)
				
				WebsocketHandler.msgHandler(self, msg_bytes, self.client_address)

		except Exception as e:
			print(f"Threaded WebSocket socket routing crash for {self.client_address}: {e}")
		finally:
			print(f"Thread connection socket safely closed for client: {self.client_address}")

def startWebsocketServer_in_new_thread(port):
	"""Spins up the threaded binary networking core on its own background thread."""
	server_address = (networkCommon.svrIp, port)

	# Optional SSL Context layer wrapping for native secure TLS streams
	context = networkCommon.get_ssl_context(networkCommon.certfile, networkCommon.keyfile)

	tcp_server = ThreadedBinaryTCPServer(server_address, BinaryRequestHandler, ssl_context=context)

	# Run the socket loop inside a dedicated background daemon thread
	server_thread = threading.Thread(target=tcp_server.serve_forever)
	server_thread.daemon = True
	server_thread.start()
	networkCommon.dbgPrint(f"starting WebsocketServer at {server_address[0]} port {server_address[1]}")
	return tcp_server, server_thread
