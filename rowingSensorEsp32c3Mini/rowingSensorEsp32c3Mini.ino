//#include "MPU9250_minimal.h"
#include "MPU9250Faster.h" //accelerometer and gyro reading

#include <WiFi.h>
#include <WiFiUdp.h>


// Wi-Fi placeholders
const char* WIFI_SSID = "Internet";
const char* WIFI_PASS = "4ydq9c1k";

const uint16_t UDP_PORT = 5005;

WiFiUDP Udp;


#define blueStatusLEDPin    8
#include "morseCode.h"


// Device identification (unique per node)
const uint8_t device_id = 1; // change for each sensor board (1..18)

#include "multipleDeviceTimeslotSync.h"



void wifiConnect(){  
  WiFi.mode(WIFI_STA);  
  WiFi.begin(WIFI_SSID, WIFI_PASS);  
  unsigned long t0 = millis();  
  while (WiFi.status() != WL_CONNECTED && 
          millis() - t0 < 20000) {    
    Serial.print("reattempting connection to wifi ");
    Serial.println(WIFI_SSID);
    delay(200);
  }  
  // start UDP  
  Udp.begin(UDP_PORT);
}



void setup() {
	Serial.begin(115200);
  delay(5000);
  for(int i = 0; i < 100; ++i)
    Serial.println("Serial output to syncronize");
	if (!mpu9250_init()) { //!mpu9250_begin()){ //
		Serial.println("MPU9250 init failed");
		//while (1) delay(1000);
	}
	Serial.println("MPU9250 init OK");

  //turn on status led
  Serial.print(" init status led ");
	pinMode(blueStatusLEDPin, OUTPUT);
	digitalWrite(blueStatusLEDPin, HIGH);

  digitalWrite(blueStatusLEDPin, LOW);

  wifiConnect();
}


unsigned long lastMicros = 0;
const unsigned long sampleIntervalUs = 10000; // 100 Hz -> 10,000 us (change to 1000 for 1kHz)

#define sP(x)  (Serial.print(x))
#define sPln(x) (Serial.println(x))

void loop() {
	unsigned long now = micros();
	if (now - lastMicros < sampleIntervalUs)
		return;
	lastMicros = now;
	
  
}

void sensorTask(void*){  
  
  const int sensor_sample_ms = 10; // sample time inside slot if needed  
  // wait until have_sync    
  while(!have_sync) vTaskDelay(pdMS_TO_TICKS(10));
  uint32_t now = millis();
  uint32_t start = computeNextSlotStart(now);
  int32_t wait = (int32_t)(start - now);
  if (wait > 0) {
    vTaskDelay(pdMS_TO_TICKS(wait));
  } else {
    // if negative, yield briefly 
    vTaskDelay(pdMS_TO_TICKS(1));
  }    // small jitter guard: busy-wait last 2 ms for accuracy
  while ((int32_t)(start - millis()) > 2)
    vTaskDelay(pdMS_TO_TICKS(0));
  while ((int32_t)(start - millis()) > 0)
  { /* spin */ }


  // timestamp and read sensors immediately 
  uint32_t ts = millis();

  // read sensors (same reads as before) and send UDP broadcast
  // send CSV or binary with device_id and ts
  bool sampleReadError = false;
	// Read accel/gyro (required each sample)
	if (!read_accel_gyro()) {
		// handle error
    sampleReadError = true;
	}

	// Read magnetometer (AK8963 continuous mode; quick read)
	if (!readMagViaMPU()){//read_mag_via_bypass()) {
		// handle error or skip mag this sample
    sampleReadError = true;
	}

  if( !sampleReadError ){
    // Convert raw values to g / dps / uT as needed, apply calibration
    // print raw values

    // Timestamp and CSV: deviceid,ms, ax,ay,az, gx,gy,gz, mx,my,mz
    uint32_t t = millis();
    char out[200];
    int len = snprintf(out, sizeof(out), "d%i, t%lu, a%i,%i,%i, g%i,%i,%i, m%i,%i,%i",
              device_id, (unsigned long)t,
              ax, ay, az,   //g's
              gx, gy, gz,   //degrees per second
              mx, my, mz ); //micro tesla

    sPln(out);

    // Transmit over WiFi / ESP32 tasks: push to queue or send via async methods to avoid blocking
    // Broadcast to 255.255.255.255:UDP_PORT
    Udp.beginPacket("255.255.255.255", UDP_PORT);
    Udp.write((uint8_t*)out, len);
    Udp.endPacket();
  }
	
  // After sending, loop to compute next slot (computeNextSlotStart will advance)

}

/*
uint16_t loopCtr = 0;
void loop() {
  // put your main code here, to run repeatedly:

  mpu9250_read9(&ax,&ay,&az,&gx,&gy,&gz,&mx,&my,&mz)  ; 
    sP("A:");sP(ax);sP(',');sP(ay);sP(',');sPln(az);
    sP("G:");sP(gx);sP(',');sP(gy);sP(',');sPln(gz);
    sP("M:");sP(mx);sP(',');sP(my);sP(',');sPln(mz);
  
  delay(200);

  //if( loopCtr % 100  == 0)
  //  queueStringForMorseLedOutput("mainLoop", 8 );
  //morseOutputLedUpdate( blueStatusLEDPin, true );
  //delay(10);
  loopCtr++;
}
*/
