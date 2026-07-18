#ifndef CLOUD_CONNECTION
#define CLOUD_CONNECTION


#include "esp_http_server.h"
//#include "esp_http_client.h"
#include "HTTPClient.h"

#include "GlobalDefinesAndFunctions.h"
Preferences preferences;

httpd_handle_t camera_httpd = NULL;

unsigned long cloudSendStatusIntervalMillis = 200000;


uint16_t serverUrlLen = 0;
uint16_t serverCertLen = 0;
char serverUrl[MAX_SVR_URL_LEN] = {'\0'};
char serverCert[SVR_CERT_MAX_LEN] = {'\0'};

uint16_t devId;


#define MIN_STATUS_RESPONSE_LENGTH 68 //(2+2+5+5+5){19} +(5+5+5+5+5){25} +(10+5+2+2+2){21} + 2
#define LIGHT_STATUS_LEN 2
#define MAG_SENSOR_LEN 51


void ObfsucatePass(char *str, uint8_t len){
	for(uint16_t i = 0; i < len; ++i){
		if(str[i] != '\0')
			str[i] = '*';
	}
}



uint8_t sendPktNum = 0;
uint8_t fillPktHdr(char * outputBytes){
	//if( self.sendPktIdx >= 256 ):
	//	self.sendPktIdx = 0
	uint8_t idx = 0;
	snprintf( &(outputBytes[idx]), 3+1, "%3i", sendPktNum ); idx += 3;
	snprintf( &(outputBytes[idx]), 4+1, "% 4d", devId ); idx += 4;
	//fill header
	outputBytes[idx] = '1'; idx += 1;
	outputBytes[idx] = 'd'; idx += 1;
	sendPktNum++; //rollover at 255 because of uint8_t data type
	return idx; //return offset in packet header
}



#define MIN_STATUS_RESPONSE_LENGTH 68 //(2+2+5+5+5){19} +(5+5+5+5+5){25} +(10+5+2+2+2){21} + 2
#define LIGHT_STATUS_LEN 2
#define MAG_SENSOR_LEN 51
uint16_t fillStatusString(char * outStr){
	//+1's to snprintf lengths because of \0 null terminator always appended

	uint16_t idx = 0;

	//fill header
	snprintf( &(outStr[idx]), 11+1, "Stat" ); idx += 11;
	snprintf( &(outStr[idx]), 6+1, "% 6d", MIN_STATUS_RESPONSE_LENGTH ); idx += 6;

	//fill data

	//snprintf( &(outStr[idx]), 3+1,  "% 3u", activelyCommanded); idx += 3;

	uint8_t featureMask;
	genFeatureMask( featureMask, hasMagSensor, hasMicSensor, hasLight_Out, hasSpeaker_Out );
	snprintf( &(outStr[idx]), 2+1,  "% 2u", featureMask); idx += 2;


	snprintf( &(outStr[idx]), 5+1,  "% 5i", staRssi); idx += 5;
	snprintf( &(outStr[idx]), 5+1,  "% 5d", lastTemperature); idx += 5;

	if(hasLight_Out)
		snprintf( &(outStr[idx]), 2+1,  "% 2u", (int)lightLedValue); idx += 2;

	if( hasMagSensor ){
		//snprintf( &(outStr[idx]), 2+1,  "% 2u", alarmArmed); idx += 2;
		//snprintf( &(outStr[idx]), 5+1,  "% 5i", magAX); idx += 5; //alarmInit_magSample.X);
		//snprintf( &(outStr[idx]), 5+1,  "% 5i", magAY); idx += 5; //alarmInit_magSample.Y);
		//snprintf( &(outStr[idx]), 5+1,  "% 5i", magAZ); idx += 5; //alarmInit_magSample.Z);

		snprintf( &(outStr[idx]), 5+1,  "% 5i", pmx); idx += 5; //compass.magSample.X);
		snprintf( &(outStr[idx]), 5+1,  "% 5i", pmy); idx += 5; //compass.magSample.Y);
		snprintf( &(outStr[idx]), 5+1,  "% 5i", pmz); idx += 5; //compass.magSample.Z);

		//snprintf( &(outStr[idx]), 10+1, "% 10f", magHeading); idx += 10;
		//snprintf( &(outStr[idx]), 5+1,  "% 5i", magAlarmDiff); idx += 5;
		//snprintf( &(outStr[idx]), 2+1,  "% 2u", magAlarmTriggered); idx += 2;
		//snprintf( &(outStr[idx]), 2+1,  "% 2u", alarmOutput); idx += 2;
	}
	
	//memset() //snprintf will set a \0 at end so don't need to memset
	return idx+1;
}

uint8_t numStoredSvrs = 0;
uint8_t numStoredNetworks = 0;
#define SETTINGS_RESPONSE_LENGTH 20+((NETWORK_NAME_LENGTH*2)*MAX_STORED_NETWORKS)+(MAX_STORED_NETWORKS*NETWORK_NAME_LENGTH)
uint16_t fillSettingsString( char * outputStr ){

	uint16_t oIdx = 0;

	//fill header
	snprintf( &(outputStr[oIdx]), 11+1, "Set" ); oIdx += 11;
	snprintf( &(outputStr[oIdx]), 6+1, "% 6d", SETTINGS_RESPONSE_LENGTH ); oIdx += 6;

	//fill mag threshold, cam quality, cam resolution, tx power
	//snprintf( &(outputStr[oIdx]),  5, "%i\n", MAG_ALARM_DELTA_THRESHOLD); oIdx += 5;
	//sensor_t * s = esp_camera_sensor_get();
	//snprintf( &(outputStr[oIdx]),  5, "%i\n", s->status.quality); oIdx += 5;
	//snprintf( &(outputStr[oIdx]), 5, "%i\n", s->status.framesize); oIdx += 5;
	int8_t txPower;
	esp_wifi_get_max_tx_power(&txPower);
	snprintf( &(outputStr[oIdx]), 5, "%i\n", txPower); oIdx += 5;

	//oIdx = 37 (11+6+5+5+5) + 32 = 69

	Serial.println("fSS storedVals");
	preferences.begin("storedVals", true);

		char networkInfo[NETWORK_NAME_LENGTH];

		//server urls
		for( uint8_t i = 0; i < MAX_NUM_SVRS; ++i ){
			memset( networkInfo, '\0', NETWORK_NAME_LENGTH );
			preferences.getBytes("svrUrl"+i, networkInfo, NETWORK_NAME_LENGTH);
			memcpy( &(outputStr[oIdx]), networkInfo, NETWORK_NAME_LENGTH ); oIdx += NETWORK_NAME_LENGTH;
		}

		//oIdx = 357 oIdx (37) += ( MAX_NUM_SVRS (10) * NETWORK_NAME_LEN (32) ) (320) = 389

		//networks and passwords
		//Serial.println("svrUrl");
		uint16_t storedNetworksSettingsStrStart = oIdx;
		for( uint8_t i = 0; i < MAX_STORED_NETWORKS; ++i ){
			snprintf(storedPrefKey, 8,"net%i", i );
			memset( networkInfo, '\0', NETWORK_NAME_LENGTH );
				preferences.getBytes(storedPrefKey, &networkInfo[0], NETWORK_NAME_LENGTH);
				memcpy( &(outputStr[oIdx]), networkInfo, NETWORK_NAME_LENGTH ); oIdx += NETWORK_NAME_LENGTH;
				//Serial.print("net");Serial.println(i);
				snprintf(storedPrefKey, 8,"pass%i", i );
			memset( networkInfo, '\0', NETWORK_NAME_LENGTH );
				preferences.getBytes(storedPrefKey, &networkInfo[0], NETWORK_NAME_LENGTH);
				ObfsucatePass(networkInfo, NETWORK_NAME_LENGTH);
				memcpy( &(outputStr[oIdx]), networkInfo, NETWORK_NAME_LENGTH ); oIdx += NETWORK_NAME_LENGTH;
				//Serial.print("pass");Serial.println(i);
		}

	preferences.end();
	memset( &(outputStr[oIdx]), '\0', 1 ); oIdx += 1;//prevent segfault reboot from missing \0

	return oIdx;
}

uint8_t doCommand( const char * cmd, uint16_t valLen, const char * value ){

	uint8_t sucessfulyHandledCmd = 0;


	/*
	if ( !strncmp(cmd, "mainDelay", 9) ){
		uint8_t del = atoir_n(&value[valLen-1], valLen);
		Serial.print("mainDelay"); Serial.println(del);
		del = max( min((uint8_t)100, del), (uint8_t)10 ); //clamp setting to between 10 and 100 millis
		mainLoopDelayMillis = del;
		sucessfulyHandledCmd = 5;
	}

	else*/ if(!strncmp(cmd, "setDevDesc", 10)){
		preferences.begin("storedVals", false);
			uint16_t storLen = min( valLen, (uint16_t)MAX_SVR_URL_LEN );
			preferences.putBytes("devDescrip", value, storLen );
			Serial.print(" storing devDescrip");
			printPayload( 0, storLen, value );
			Serial.print(" len ");Serial.println(storLen);
		preferences.end();
		sucessfulyHandledCmd = 6;
	}

	
	
	else if(!strncmp(cmd, "txPower", 7)){
		atoir_n(&value[valLen-1], valLen);
		sucessfulyHandledCmd = 14;
	}
	else if(!strncmp(cmd, "svrUrl", 6)){
		preferences.begin("storedVals", false);
			uint8_t urlNum = cmd[6] - '0';
			uint16_t storLen = min( valLen, (uint16_t)MAX_SVR_URL_LEN );
			preferences.putBytes("svrUrl"+urlNum, value, storLen );
			Serial.print(" storing svrUrl");Serial.print(urlNum);Serial.print(" len ");Serial.println(storLen);
		preferences.end();
		sucessfulyHandledCmd = 15;
	}
	else if(!strncmp(cmd, "svrCertLen", 10)){
		uint8_t certNum = cmd[10] - '0';
		preferences.begin("storedVals", false);
			uint16_t certLen = atoir_n(&value[valLen-1], valLen );
			if( certLen > SVR_CERT_MAX_LEN)
				certLen = SVR_CERT_MAX_LEN;
			preferences.putInt( "svrCertLen"+certNum, certLen );
			Serial.print("storing svrCert len num "); Serial.print(certNum); Serial.println(" len ");Serial.println(certLen);
		preferences.end();
		sucessfulyHandledCmd = 16;
	}
	else if(!strncmp(cmd, "svrCert", 7)){
		uint8_t certNum = cmd[7] - '0';
		uint8_t certPartIdx = cmd[9] - '0';
		if( certPartIdx * SVR_CERT_PART_LENGTH < SVR_CERT_MAX_LEN ){ //only write a cert if within acceptable length
			preferences.begin("storedVals", false);
				uint16_t storLen = min( valLen, (uint16_t)SVR_CERT_PART_LENGTH );
				snprintf( storedPrefKey, 10+1,"svrCert%i_%i", certNum,certPartIdx );
				preferences.putBytes( storedPrefKey, value, storLen );
				Serial.print("storing svrCert "); Serial.print(certNum);
				Serial.print("_"); Serial.print(certPartIdx);
				Serial.print(" len ");Serial.println(storLen);
			preferences.end();
			sucessfulyHandledCmd = 17;
		}
	}
	else if(!strncmp(cmd, "net", 3)){
		uint8_t netNum = cmd[3] -'0';
		preferences.begin("storedVals", false);
		uint16_t len = min( valLen, (uint16_t)NETWORK_NAME_LENGTH );
			snprintf( storedPrefKey, 8, "net%i", netNum );
			preferences.putBytes( storedPrefKey, value, len );
			Serial.print( "storing at |" ); Serial.print( storedPrefKey ); 
			Serial.print( "| |" ); Serial.print( value );
			Serial.print("| ");Serial.println(len);
		preferences.end();
		sucessfulyHandledCmd = 18;
	}
	else if(!strncmp(cmd, "pass", 4)){
		uint8_t netNum = cmd[4] -'0';
		preferences.begin("storedVals", false);
		uint16_t len = min( valLen, (uint16_t)NETWORK_NAME_LENGTH );
			snprintf( storedPrefKey, 8, "pass%i", netNum );
			preferences.putBytes( storedPrefKey, value, len );
			Serial.print( "storing at |" ); Serial.print( storedPrefKey ); 
			Serial.print( "| |" ); Serial.print( value );
			Serial.print("| ");Serial.println(len);
		preferences.end();
		sucessfulyHandledCmd = 19;
	}
	else if(!strncmp(cmd, "getSettings", 11)){
		uint16_t pktIdx = fillPktHdr(lastCsiInfoStr);
		pktIdx += fillSettingsString(&lastCsiInfoStr[pktIdx]);
		Serial.print("sendingSettings ");Serial.println(pktIdx);
		esp_websocket_client_send_bin(webSockClient, (const char *)&(lastCsiInfoStr[0]), pktIdx, portMAX_DELAY);
		sucessfulyHandledCmd = 20;
	}
	else if(!strncmp(cmd, "getStatus", 9)){
		uint16_t pktIdx = fillPktHdr(lastCsiInfoStr);
		pktIdx += fillStatusString(&lastCsiInfoStr[pktIdx]);
		Serial.print("sendingStatus ");Serial.println(pktIdx);
		esp_websocket_client_send_bin(webSockClient, (const char *)&(lastCsiInfoStr[0]), pktIdx, portMAX_DELAY);
		sucessfulyHandledCmd = 22;
	}

	/*
	else if(!strncmp(cmd, "cfgHasLght", 10)){
		preferences.begin("storedVals", false);
			bool hasLight = atoir_n(value, valLen);
			preferences.putBool("hasLight", hasLight );
			Serial.print(" storing hasLight");Serial.println(hasLight);
		preferences.end();
		if( hasLight_Out )
			initLight();
		sucessfulyHandledCmd = 24;
	}
  */
	
	else if(!strncmp(cmd, "cfgHasMic", 9)){
		preferences.begin("storedVals", false);
			bool hasMic = atoir_n(value, valLen);
			preferences.putBool("hasMic", hasMic );
			Serial.print(" storing hasMic");Serial.println(hasMic);
		preferences.end();
		sucessfulyHandledCmd = 26;
	}
	else if(!strncmp(cmd, "cfgHasSpkr", 10)){
		preferences.begin("storedVals", false);
			bool hasSpkr = atoir_n(value, valLen);
			preferences.putBool("hasSpkr", hasSpkr );
			Serial.print(" storing hasSpkr");Serial.println(hasSpkr);
		preferences.end();
		sucessfulyHandledCmd = 27;
	}
	else if(!strncmp(cmd, "cfgIsUltSnd", 11)){
		preferences.begin("storedVals", false);
			bool isUltSnd = atoir_n(value, valLen);
			preferences.putBool("isUltSnd", isUltSnd );
			Serial.print(" storing isUltSnd");Serial.println(isUltSnd);
		preferences.end();
		sucessfulyHandledCmd = 28;
	}
	else if(!strncmp(cmd, "setDevId", 8)){
		preferences.begin("storedVals", false);
			uint8_t newDevId = atoir_n(value, valLen);
			preferences.putUChar("devId", newDevId);
			Serial.print(" storing devId "); Serial.println(newDevId);
			devId = newDevId;
		preferences.end();
		sucessfulyHandledCmd = 29;
	}

	else if(!strncmp(cmd, "getDevDesc", 10)){
		preferences.begin("storedVals", true);
			uint16_t pktIdx = fillPktHdr(lastCsiInfoStr);
			snprintf( &(lastCsiInfoStr[pktIdx]), 11+1, "DevId" ); pktIdx += 11;
			uint8_t descripLen = preferences.getBytes("devDescrip", &(lastCsiInfoStr[pktIdx+6]), MAX_SVR_URL_LEN );
			uint8_t firstChar = lastCsiInfoStr[pktIdx+6];
			snprintf( &(lastCsiInfoStr[pktIdx]), 6+1, "% 6d", descripLen ); 
			lastCsiInfoStr[pktIdx+6] = firstChar; pktIdx += 6 + descripLen;
			Serial.print("sendingDevId ");Serial.println(pktIdx); pktIdx += descripLen;
			esp_websocket_client_send_bin(webSockClient, (const char *)&(lastCsiInfoStr[0]), pktIdx, portMAX_DELAY);
		preferences.end();
		sucessfulyHandledCmd = 30;
	}

	return sucessfulyHandledCmd;
}

//read the stored server cert back from preferences
void readSvrCert(uint8_t num, uint16_t & length, char * svrCert ){
	Serial.print("readSvrCert len ");
	preferences.begin("storedVals", true);
		length = preferences.getInt( "svrCertLen"+num );
		Serial.println( length );
		uint16_t partIdx;
		uint16_t partLen;
		for( uint8_t i = 0; i < NUM_SVR_CERT_PARTS; ++i ){
			partIdx = i*SVR_CERT_PART_LENGTH;
			uint16_t remLen = length - partIdx;
			partLen = min( (uint16_t)SVR_CERT_PART_LENGTH, remLen);
			Serial.print( " partIdx " );Serial.print(i);Serial.print(" ");Serial.print( partIdx );
			Serial.print( " remLen " ); Serial.print(remLen); Serial.print( " partLen " );Serial.println( partLen );
			if( partLen <=0 )
				break;
			snprintf( storedPrefKey, 10+1,"svrCert%i_%i", num,i );
			preferences.getBytes(storedPrefKey, &svrCert[i*SVR_CERT_PART_LENGTH], partLen );
		}
		svrCert[length] = '\0';
	preferences.end();
	//printPayload( 0, 50, svrCert );
}

#include "webSocketClient.h"


bool isAUrl(String str){
	int strLen = str.length();
	if( strLen < 1 )
		return false;
	for( uint8_t i = 0; i < strLen; ++i )
		if( str[i] != ' ' && str[i] != '\0')
			return true;
}



typedef enum{
	DEV_STATUS   ,
	DEV_SETTINGS ,
	IMAGE    
} PostType;
uint16_t mainLoopsSinceWebSockStartedConnecting = 0;
uint8_t svrIdx = 0;

void ReadNextSvrInfo(){
	preferences.begin("storedVals", true);
	serverUrlLen = 0;
	do{
		Serial.print("reading svrUrl");Serial.println(svrIdx);
		serverUrlLen = preferences.getBytesLength("svrUrl"+svrIdx);
		memset( serverUrl, '\0', MAX_SVR_URL_LEN );
		preferences.getBytes("svrUrl"+svrIdx, serverUrl, serverUrlLen);
		Serial.print( "svrUrl " ); Serial.print( serverUrl ); Serial.print( " len " ); Serial.println( serverUrlLen );
		readSvrCert( svrIdx, serverCertLen, serverCert );
		svrIdx ++;
	}while(serverUrlLen < 4 && svrIdx < MAX_NUM_SVRS);
	preferences.end();
}
void PostAndFetchDataFromCloudServer(PostType postType){
	
		if(mainLoopsSinceWebSockStartedConnecting > 100  || svrIdx >= MAX_NUM_SVRS){
			if(webSockClient != NULL ){
				Serial.println("freeing websocket client");
				esp_websocket_client_stop(webSockClient);
				esp_websocket_client_destroy(webSockClient);
				
				Serial.print("finished freeing webSockClient "); Serial.println((int)webSockClient);
				webSockClient = NULL;
			}
			if(svrIdx >= MAX_NUM_SVRS){
				svrIdx = 0;
			}
		}

	if( webSockClient == NULL ){//|| !esp_websocket_client_is_connected(webSockClient) && mainLoopsSinceWebSockStartedConnecting > 10000 ){
		//attempt connection to server
		Serial.println("attempt websocket connection");
		mainLoopsSinceWebSockStartedConnecting = 0;

		ReadNextSvrInfo();
		
		if( isAUrl(serverUrl) ){

			if( webSockClient != NULL ){
				esp_websocket_client_destroy(webSockClient);
				Serial.println("esp_websocket_client_destroy");
			}

			//https://docs.espressif.com/projects/esp-protocols/esp_websocket_client/docs/latest/index.html
			Serial.print( "WebSock to " ); Serial.print( serverUrl ); Serial.print( "|" ); Serial.println( serverUrlLen );
			Serial.print( "Cert Len ");
			//Serial.print( serverCert );
			Serial.print("|"); Serial.println( serverCertLen );
			const esp_websocket_client_config_t ws_cfg = {
				.uri = serverUrl,//"wss://echo.websocket.org",
				//.port = 4567,
				.cert_pem = (const char *)serverCert,
				.cert_len = serverCertLen + 1, //+1 for null terminator
				//.subprotocol = 
				.transport = WEBSOCKET_TRANSPORT_OVER_SSL,
				.skip_cert_common_name_check = true,
				
			};
			webSockClient = esp_websocket_client_init(&ws_cfg);
			Serial.println( "webSock cli inited");
				esp_err_t wEvts = esp_websocket_register_events(webSockClient, WEBSOCKET_EVENT_ANY, websocket_event_handler, (void *)webSockClient);
				Serial.print( "webSock reg " ); Serial.println( wEvts );
				wEvts = esp_websocket_client_start(webSockClient);
			Serial.print("free heap "); Serial.print(esp_get_free_heap_size());
				Serial.print( "webSock start " ); Serial.println( wEvts );

		}
	}

	if( esp_websocket_client_is_connected(webSockClient) ){
		//send a message to server 
		Serial.print( " to Wss " );
		int httpResponseCode;
		uint8_t hdrOffset = fillPktHdr(lastCsiInfoStr);
		if( postType == DEV_STATUS ){
			uint16_t statLen = fillStatusString(&lastCsiInfoStr[hdrOffset]);
			//printPayload(hdrOffset, hdrOffset+statLen, lastCsiInfoStr );
			httpResponseCode = esp_websocket_client_send_bin(webSockClient, (const char *)&(lastCsiInfoStr[0]), hdrOffset+statLen, portMAX_DELAY);
		}else if( postType == DEV_SETTINGS ){
			uint16_t setLen = fillSettingsString(&lastCsiInfoStr[hdrOffset]);
			httpResponseCode = esp_websocket_client_send_bin(webSockClient, (const char *)&(lastCsiInfoStr[0]), hdrOffset+setLen, portMAX_DELAY);
		}
		

		Serial.print( " resp: " );
		Serial.println(httpResponseCode);
	}

	//cloudHttp.end();
}

#endif
