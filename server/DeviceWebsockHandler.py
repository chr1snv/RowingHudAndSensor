import Device
import Client

async def handleWebSockClientDeviceRequests(client, datType, datStr):
	print('client.devId %s' % client.devId )
	if client.devId in Device.devices.keys():
		device = Device.devices[client.devId]
		if datType.startswith(b'status'):
			#print( 'sending status to browser' + str(len(device.postStatus)) )
			timeStr = str(device.lastStatusTime).encode('utf-8')
			await client.send( device.devId, [('Stat', len(device.postStatus), device.postStatus), ('Time', len(timeStr), timeStr)] )
		elif datType.startswith(b'settings'):
			#setLen = str(len(device.postSettings)).encode('utf-8')
			print( 'req settings from dev' )
			await device.send( Client.svrDevId, [('getSettings', 0, b'')] )
			print( 'sending last settings to browser' )
			lastSetTimeStr = str(device.lastSettingsTime).encode('utf-8')
			await client.send( device.devId, [('Set', len(device.postSettings), device.postSettings), ('Time', len(lastSetTimeStr), lastSetTimeStr)] )
		elif datType.startswith(b'image'):
			#print( 'sending img to browser' )
			await client.send( device.devId, [('Img', len(device.lastImage), device.lastImage)]  )
		else:
			cmd = datType.strip()
			val = datStr
			print( 'action: ' + str(cmd) + ':' + str(val) + "|" )
			Device.putCmdList( device.cmds, [ [cmd, val] ] )
			deviceWithNewCmds = device
	else:
		print( "dev %i not in devices" % client.devId )