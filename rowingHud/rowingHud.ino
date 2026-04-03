#include <U8g2lib.h>
#include <Wire.h>
#include <Adafruit_QMC5883P.h>


// Fill WIFI_SSID and WIFI_PASS
#include <WiFi.h>
#include <WiFiUdp.h>


// Wi-Fi placeholders
const char* WIFI_SSID = "Internet";
const char* WIFI_PASS = "4ydq9c1k";

const uint16_t UDP_PORT = 5005;
WiFiUDP Udp;


Adafruit_QMC5883P qmc;
bool magSensorWorking = false;

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_MIRROR/*_R0*/, U8X8_PIN_NONE, 6, 5);
int xOffset = 28; 
int yOffset = 24;

uint idleTimer;

void setup(void) {
  Wire.begin(5, 6);
  if (!qmc.begin()) {
    /* Handle error: sensor not found */
    magSensorWorking = false;
  }else{
    magSensorWorking = true;
  }
  u8g2.begin();
  u8g2.setContrast(10);
  u8g2.setBusClock(400000);
  u8g2.setFont(u8g2_font_micro_tr); // 5-pixel high font
  idleTimer = 0;
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

char outputStrBuff[64];
void loop(void) {

  if( idleTimer++ > 3000 ){
    u8g2.setPowerSave(true);
  }else{
    u8g2.setPowerSave(false);

    u8g2.clearBuffer();
    // Example HUD Menu
    u8g2.drawStr(xOffset + 2, yOffset + 10, "L/R: NAVIGATE");
    u8g2.drawStr(xOffset + 2, yOffset + 20, "UP: SELECT");
    u8g2.drawStr(xOffset + 2, yOffset + 30, "ROLL: EXIT");

    

    if( magSensorWorking ){
      int16_t x,y,z; // Raw values in micro-Teslas (uT)
      qmc.getRawMagnetic( &x, &y, &z);
      sprintf(outputStrBuff, "%i %i %i %i", idleTimer, x, y, z);
    }else{
      sprintf(outputStrBuff, "%i", idleTimer );
    }

    u8g2.drawStr(xOffset+0, yOffset +30, outputStrBuff);
  
    
    

    u8g2.sendBuffer();
  }

}
