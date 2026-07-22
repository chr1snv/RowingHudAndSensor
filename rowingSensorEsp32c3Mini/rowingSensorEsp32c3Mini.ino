

int16_t mx,my,mz;
int16_t pmx,pmy,pmz; //previous loop magnetic values
// Sensor on the same TwoWire instance as 9250 accel gyro (only 1 i2c interface on esp32-c3)
#include <MPU9250Faster.h> //accelerometer and gyro reading
#include <Adafruit_QMC5883P.h>
Adafruit_QMC5883P qmc = Adafruit_QMC5883P();

#define blueStatusLEDPin    8



#include <GlobalDefinesAndFunctions.h>
#include <storedConfig.h>
#include <morseCode.h>
#include <wifiConnection.h>
#include <multipleDeviceTimeslotSync.h>
#include <cloudConnection.h>
#include <APWebConfig.h>


char lastCsiInfoStr[CSI_INF_STR_LEN];

void setup() {
	Serial.begin(115200);
  delay(5000);
  for(int i = 0; i < 100; ++i)
    Serial.println("Serial output to syncronize");





  hasDisplay_Out=0;


	if (!mpu9250_init()) { //!mpu9250_begin()){ //
		Serial.println("MPU9250 init failed");
		//while (1) delay(1000);
	}
	Serial.println("MPU9250 init OK");

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

  //turn on status led
  Serial.print(" init status led ");
	pinMode(blueStatusLEDPin, OUTPUT);
	digitalWrite(blueStatusLEDPin, HIGH);

  digitalWrite(blueStatusLEDPin, LOW);


  //try to join saved network (phone wifi hotspot ap)
  Serial.print(" init wifi ");
	connectWiFi(wifi_scanNetworks());


  if(!joinedWifiNetwork){ //if couldn't join, start local ap and config webserver

    startAPWebConfig();
  }
}



#define sP(x)  (Serial.print(x))
#define sPln(x) (Serial.println(x))



void sensorTask(){  
  
 
  // timestamp and read sensors immediately 
  uint32_t ts = millis();

  // read sensors and send UDP broadcast
  // send CSV (or binary) with device_id and ts
  bool sampleReadError = false;
	// Read accel/gyro (required each sample)
	if (!read_accel_gyro()) {
		// handle error
    sampleReadError = true;
	}
/*
	// Read magnetometer (AK8963 continuous mode; quick read)
	if (!readMagViaMPU()){//read_mag_via_bypass()) {
		// handle error or skip mag this sample
    sampleReadError = true;
	}
  */
  int16_t mx,my,mz;
  qmc.getRawMagnetic(&mx,&my,&mz);

  if( !sampleReadError ){
    // Convert raw values to g / dps / uT as needed, apply calibration
    // print raw values



    // Timestamp and CSV: deviceid,ms, ax,ay,az, gx,gy,gz, mx,my,mz
    uint32_t t = millis();
    /*
    char out[ESP_NOW_BRDCAST_PKTLEN-2];
    int len = snprintf(out, sizeof(out), "d%i, t%lu, a%i,%i,%i, g%i,%i,%i, m%i,%i,%i",
              device_id, (unsigned long)t,
              ax, ay, az,   //g's
              gx, gy, gz,   //degrees per second
              mx, my, mz ); //micro tesla

    sPln(out);
    */

    sendPkt.device_id = device_id;
    sendPkt.t = t;
    sendPkt.ax = ax;
    sendPkt.ay = ay;
    sendPkt.az = az;
    sendPkt.gx = gx;
    sendPkt.gy = gy;
    sendPkt.gz = gz;
    sendPkt.mx = mx;
    sendPkt.my = my;
    sendPkt.mz = mz;

    /* //udp brodcast (255.255.255.255) or multicast is not radio level, the ap has to re transmit it
    // Transmit over WiFi / ESP32 tasks: push to queue or send via async methods to avoid blocking
    // Broadcast to 255.255.255.255:UDP_PORT
    Udp.beginPacket("255.255.255.255", UDP_PORT);
    Udp.write((uint8_t*)out, len);
    Udp.endPacket();
    */
    // Send message via ESP-NOW

    esp_err_t result = sendEncPacket( (uint8_t *) &(sendPkt), sizeof(pkt_t));
    if (result == ESP_OK) {
      //Serial.println("Sent with success");
    }
    else {
      Serial.println("Error sending the data");
    }
  }

}


unsigned long lastMicros = 0;
unsigned long lastCloudStatusSendMicros = 0;

uint8_t mainLoopDelayMillis = 10;

void loop() {
	unsigned long now = micros();
	if (now - lastMicros < sampleIntervalUs)
		return;
  /*
  pollSyncPacket(); //using esp-now instead of udp
  */

  if( now - lastCloudStatusSendMicros > cloudSendStatusIntervalMillis && joinedWifiNetwork ){

    PostAndFetchDataFromCloudServer(DEV_STATUS);
    lastCloudStatusSendMicros = now;
  }

  if( have_sync && now >= nextTxTime ){
    //Serial.println("reading sensor and sending pkt");
    sensorTask();
    have_sync = false;
  }


  lastMicros = now;
  delay(mainLoopDelayMillis);
}

