#include <Arduino.h>
#include <Preferences.h> //for non volitile memory storage
extern Preferences preferences;

uint16_t devId=0;

bool lightLedValue = false;

bool hasFileServer =0;

bool hasDistSensor=0;

bool hasMagSensor=1;
bool hasAccelSensor=1;
bool hasGyroSensor=1;
bool hasMicSensor=0;
bool hasCameraSensor=0;

bool hasDisplay_Out=1;
bool hasLight_Out=0;
bool hasSpeaker_Out=0;

void genFeatureMask( uint16_t & featureMask, 
    bool hasFileServer, bool hasDistSensor, 
    bool hasMagSensor, bool hasAccelSensor, bool hasGyroSensor, 
    bool hasMicSensor, bool hasCameraSensor, 
    bool hasDisplayOut, 
    bool hasLightOut, bool hasSpeakerOut ){
	featureMask = 0;
  if( hasFileServer )
		featureMask |= 0x01;
	featureMask <<= 1;

  if( hasDistSensor )
		featureMask |= 0x01;
	featureMask <<= 1;

	if( hasMagSensor )
		featureMask |= 0x01;
	featureMask <<= 1;
  if( hasAccelSensor )
		featureMask |= 0x01;
	featureMask <<= 1;
  if( hasGyroSensor )
		featureMask |= 0x01;
	featureMask <<= 1;

	if( hasMicSensor )
		featureMask |= 0x01;
	featureMask <<= 1;
  if( hasCameraSensor )
		featureMask |= 0x01;
	featureMask <<= 1;

  if( hasDisplayOut )
		featureMask |= 0x01;
	featureMask <<= 1;
	if( hasLightOut )
		featureMask |= 0x01;
	featureMask <<= 1;
	if( hasSpeakerOut )
		featureMask |= 0x01;
}





  //read config
void readPreferncesStoredConfig(){
	preferences.begin("storedVals", true);
		devId = preferences.getUChar( "devId" );
		hasLight_Out = preferences.getBool( "hasLight" );
		Serial.print("hasLight "); Serial.println( hasLight_Out );
		hasMagSensor = preferences.getBool( "hasMagSensor" );
		Serial.print("hasMagSensor "); Serial.println( hasMagSensor );
		hasMicSensor = preferences.getBool( "hasMic" );
		Serial.print("hasMicSensor "); Serial.println( hasMicSensor );
		hasSpeaker_Out = preferences.getBool( "hasSpkr" );
		Serial.print("hasSpeaker "); Serial.println( hasSpeaker_Out );
	preferences.end();
}