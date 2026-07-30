#include <Arduino.h>
#include <Preferences.h> //for non volitile memory storage
extern Preferences preferences;

uint16_t devId=0;
uint8_t devMode=0;

bool lightLedValue = false;

bool hasFileServer =0;

bool hasDistSensor=0;

bool hasMagSensor=1;
bool hasAccelSensor=1;
bool hasGyroSensor=1;
bool hasMicSensor=0;
bool hasCameraSensor=0;

bool hasSrvos_Out=0;
bool hasDisplay_Out=1;
bool hasLight_Out=0;
bool hasSpeaker_Out=0;

void genFeatureMask( uint16_t & featureMask, 
	bool hasFileServer, bool hasDistSensor, 
	bool hasMagSensor, bool hasAccelSensor, bool hasGyroSensor, 
	bool hasMicSensor, bool hasCameraSensor, 
	bool hasSrvosOut, bool hasDisplayOut, 
	bool hasLightOut, bool hasSpeakerOut ){
	featureMask = 0;

	if( hasFileServer )   featureMask |= (1 << 0);
	if( hasDistSensor )   featureMask |= (1 << 1);
	if( hasMagSensor )    featureMask |= (1 << 2);
	if( hasAccelSensor )  featureMask |= (1 << 3);
	if( hasGyroSensor )   featureMask |= (1 << 4);
	if( hasMicSensor )    featureMask |= (1 << 5);
	if( hasCameraSensor ) featureMask |= (1 << 6);
	if( hasSrvosOut )     featureMask |= (1 << 7);
	if( hasDisplayOut )   featureMask |= (1 << 8);
	if( hasLightOut )     featureMask |= (1 << 9);
	if( hasSpeakerOut )   featureMask |= (1 << 10);
}





  //read config
void readPreferncesStoredConfig(){
	preferences.begin("storedVals", true);
	/*
		devId = preferences.getUChar( "devId" );
		hasLight_Out = preferences.getBool( "hasLight" );
		Serial.print("hasLight "); Serial.println( hasLight_Out );
		hasMagSensor = preferences.getBool( "hasMagSensor" );
		Serial.print("hasMagSensor "); Serial.println( hasMagSensor );
		hasMicSensor = preferences.getBool( "hasMic" );
		Serial.print("hasMicSensor "); Serial.println( hasMicSensor );
		hasSpeaker_Out = preferences.getBool( "hasSpkr" );
		Serial.print("hasSpeaker "); Serial.println( hasSpeaker_Out );
	*/
	preferences.end();
}