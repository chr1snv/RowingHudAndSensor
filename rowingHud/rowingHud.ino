#include <U8g2lib.h>
#include <Wire.h>


#include "multipleDeviceTimeslotSync.h"


// Sensor on the same TwoWire instance as oled (only 1 i2c interface on esp32-c3)
#include <Adafruit_QMC5883P.h>

Adafruit_QMC5883P qmc = Adafruit_QMC5883P();


U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0/*MIRROR*/, U8X8_PIN_NONE, 6, 5);
int xOffset = 28; //x 28px start offset + (3 * 5 + 3) 18 chars wide * 3px (72px wide)
int yOffset = 29; //y 29px start offset + (6        )  6 lines high * 7px (42px high)

uint idleTimer;



void setup(void) {
  Serial.begin(115200);
  //delay(5000);
  for(int i = 0; i < 10; ++i){
    Serial.println("Serial output to syncronize");
  }

  pinMode(5, INPUT_PULLUP); //software i2c bus pullups
  pinMode(6, INPUT_PULLUP);
  Wire.begin(5, 6, 400000);
  //scan and print found devices
  for (uint8_t a=1;a<127;a++){  
    Wire.beginTransmission(a);  
    if (Wire.endTransmission()==0) 
    Serial.printf("I2C device 0x%02X\n", a);
  }
  delay(10);

  Serial.println(" init magSensor ");
  // IMPORTANT: Tell the library to use your chip's specific address
  if (!qmc.begin()) { 
    Serial.println("Could not find a valid QMC5883P sensor, check wiring!");
  } else {
    // Wake the chip up!
    qmc.setMode(QMC5883P_MODE_CONTINUOUS); // Start continuous measurement
    qmc.setRange(QMC5883P_RANGE_8G);       // Set magnetic range (2G, 8G, etc)
    qmc.setODR(QMC5883P_ODR_100HZ); // Fast updates
    qmc.setDSR(QMC5883P_DSR_4);
    Serial.println("QMC5883P Configured Successfully");
  }
  
  //start connection to the i2c screen (same bus as accel gyro and magnetometer)
  u8g2.begin();
  u8g2.setContrast(10);
  //u8g2.setBusClock(400000);
  u8g2.setFont(u8g2_font_micro_tr); // 5-pixel high font
  idleTimer = 0;

  wifiConnect();
}

/*
void mirrorScreen(bool mirror) {
  if (mirror) {
    u8g2.sendF("c", 0xA1); // Column Address 127 is mapped to SEG0 (Mirrored)
  } else {
    u8g2.sendF("c", 0xA0); // Column Address 0 is mapped to SEG0 (Normal)
  }
}
u8g2.sendF("c", 0xC8); // Flip vertically
*/

typedef enum {
  P_DOWN, //Pitch
  P_UP,
  R_RIGHT, //Roll
  R_LEFT,
  Y_RIGHT, //Yaw
  Y_LEFT
} GESTURE;
GESTURE lastGesture;


unsigned long lastMicros = 0;

int16_t pmx,pmy,pmz; //previous loop magnetic values

#define LINESPACING 7

uint8_t screenNum = 0;
#define MIN_SCREEN_NUM 0
#define MAX_SCREEN_NUM 2

char outputStrBuff[64];
void loop(void) {

  unsigned long now = micros();

  if(device_id == 0){
    if ((now - lastMicros) > sampleIntervalUs){ //sync pulse / start update transmit of all devices
      //Serial.println("Sending sync");
      //Udp.beginMulticast(IPAddress a, uint16_t p);
      esp_err_t result = sendEncPacket( (uint8_t *) "sync", 4);
      if (result == ESP_OK) {
        //Serial.println("Sent sync");
      }
      else {
        Serial.println("Error sending sync");
      }
      lastMicros = now;
    }
  }

  //qmc.read();
  int16_t mx,my,mz;
  qmc.getRawMagnetic(&mx,&my,&mz);


  //calculate delta from previous loop
  int mxD = mx-pmx;
	int myD = my-pmy;
	int mzD = mz-pmz;

  //update previous loop values
  pmx = mx;
  pmy = my;
  pmz = mz;

  //overall compass change (to initiate screen wakeup or input)
	int delta = sqrt( mxD*mxD + myD*myD + mzD*mzD );

	if( delta > 120 ){
    idleTimer = 0; //wake screen up

    // Detect direction based on which axis had the biggest change
    int absX = abs(mxD);
    int absY = abs(myD);
    int absZ = abs(mzD);

    if (absX > absY && absX > absZ) {
        // X changed most: likely an Up/Down pitch
        if( mxD > 0 ){
          Serial.println( "PITCH DOWN" );
          lastGesture = P_DOWN;
        }else{
          Serial.println( "PITCH UP" );
          lastGesture = P_UP;
        }
    } 
    else if (absY > absX && absY > absZ) {
        // Y changed most: likely a Roll / side to side-tilt
        if( myD > 0 ){
          Serial.println( "ROLL RIGHT" );
          lastGesture = R_RIGHT;
        }else{
          Serial.println( "ROLL LEFT" );
          lastGesture = R_LEFT;
        }
    }
    else if (absZ > absX && absZ > absY) {
        // Z changed most: likely a Left/Right or Forward/Back tilt
        if( mzD > 0 ){
          Serial.println( "RIGHT / FORWARD" );
          lastGesture = Y_RIGHT;
          if( screenNum < MAX_SCREEN_NUM )
            screenNum += 1;
        }else{
          Serial.println( "LEFT / BACK" );
          lastGesture = Y_LEFT;
          if( screenNum > MIN_SCREEN_NUM )
            screenNum -= 1;
        }

    }
  }


  if( idleTimer++ > 3000 ){
    u8g2.setPowerSave(true);
  }else{

    u8g2.setPowerSave(false);

    u8g2.clearBuffer();

    if(screenNum == 0){
      // Example HUD Menu
      u8g2.drawStr(xOffset + 2, yOffset + 0*LINESPACING, "L/R YAW: NAVIGATE");
      u8g2.drawStr(xOffset + 2, yOffset + 2*LINESPACING, "UP: SELECT");
      u8g2.drawStr(xOffset + 2, yOffset + 3*LINESPACING, "ROLL: EXIT");
    }else if(screenNum == 1){
      //screen off counter, compass values
      u8g2.drawStr(xOffset + 2, yOffset + 0*LINESPACING, "HUD SENSOR");
      sprintf(outputStrBuff, "%4i %4i %4i %4i", idleTimer, mx, my, mz);
      u8g2.drawStr(xOffset+0, yOffset +1*LINESPACING, outputStrBuff);
      
      //overall movement, movement components
      sprintf(outputStrBuff, "%4i %4i %4i %4i", delta, mxD, myD, mzD);
      u8g2.drawStr(xOffset+0, yOffset +2*LINESPACING, outputStrBuff);

    }else{
      
      //recieved data from oar sensor
      u8g2.drawStr(xOffset + 2, yOffset + 0*LINESPACING, "OAR SENSOR");
      //uint8_t device_id;
      //uint32_t t;       // millis()
      //int16_t ax, ay, az;
      //int16_t gx, gy, gz;
      //int16_t mx, my, mz;
      sprintf(outputStrBuff, "%4i %4i %4i %4i %4i", 
                rcvPkt.device_id, 
                (unsigned)(rcvPkt.t & 0xFFFF) & 0x0FFF); // low 12 bits -> fits 4 chars (0-4095)
      u8g2.drawStr(xOffset+0, yOffset +1*LINESPACING, outputStrBuff);
      sprintf(outputStrBuff, "%4i %4i %4i", 
                rcvPkt.ax, rcvPkt.ay, rcvPkt.az);
      u8g2.drawStr(xOffset+0, yOffset +2*LINESPACING, outputStrBuff);
      sprintf(outputStrBuff, "%4i %4i %4i", rcvPkt.gx, rcvPkt.gy, rcvPkt.gz );
      u8g2.drawStr(xOffset+0, yOffset +3*LINESPACING, outputStrBuff);
      sprintf(outputStrBuff, "%4i %4i %4i", rcvPkt.mx, rcvPkt.my, rcvPkt.mz );
      u8g2.drawStr(xOffset+0, yOffset +4*LINESPACING, outputStrBuff);
    }

    u8g2.sendBuffer();
  }

}
