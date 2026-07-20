#ifndef STOREDCONFIG
#define STOREDCONFIG

extern bool lightLedValue;

extern bool hasFileServer;

extern bool hasDistSensor;

extern bool hasMagSensor;
extern bool hasAccelSensor;
extern bool hasGyroSensor;
extern bool hasMicSensor;
extern bool hasCameraSensor;

extern bool hasDisplay_Out;
extern bool hasLight_Out;
extern bool hasSpeaker_Out;


void genFeatureMask( uint16_t & featureMask, 
    bool hasFileServer, bool hasDistSensor, 
    bool hasMagSensor, bool hasAccelSensor, bool hasGyroSensor, 
    bool hasMicSensor, bool hasCameraSensor, 
    bool hasDisplayOut, 
    bool hasLightOut, bool hasSpeakerOut );



void readPreferncesStoredConfig();


#endif