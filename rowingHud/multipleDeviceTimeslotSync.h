
#include <WiFi.h>
//#include <WiFiUdp.h>
//#include "mbedtls/aes.h"
#include <esp_now.h>

#pragma pack(push,1)
typedef struct {
  uint8_t device_id;
  uint32_t t;       // millis()
  int16_t ax, ay, az;
  int16_t gx, gy, gz;
  int16_t mx, my, mz;
} pkt_t;
#pragma pack(pop)
pkt_t sendPkt;
pkt_t rcvPkt;




const unsigned long sampleIntervalUs = 10000; // 100 Hz -> 10,000 us (change to 1000 for 1kHz)


//#define SYNC_PORT 6006 //use one port for sync and data packets (only one wifi channel radio in esp32 c3 and is half duplex anyway)

// Device identification (unique per node)
const uint8_t device_id = 0; // change for each sensor board (1..18)

//for synchronization of broadcast
const uint8_t NUM_DEVICES = 18;
volatile uint32_t sync_epoch = 0;
volatile uint32_t sync_interval = 0;
bool have_sync = false;


volatile unsigned long nextTxTime = 999999999999;


uint8_t broadcastAddress[] = { 0xFF,0xFF,0xFF,0xFF,0xFF,0xFF };
const uint8_t CHANNEL = 1; // choose channel and use same on all devices

#define ESP_NOW_BRDCAST_PKTLEN 128

//javascript random c uint8_t initalizer generator
//function randomCInitializer(bytes) {  const arr = new Uint8Array(bytes);  crypto.getRandomValues(arr);  return '{ ' + Array.from(arr).map(b => '0x' + b.toString(16).padStart(2, '0')).join(', ') + ', }';}
uint8_t txCtr = 0;
uint8_t txKey[] = { 0xe9, 0x3a, 0xbd, 0x89, 0xb9, 0xae, 0xcb, 0x41, 0x41, 0x6d, 0x4a, 0xfa, 0x54, 0xef, 0x64, 0x1d };

static uint8_t rand8(uint16_t offset){
  uint32_t x = offset;
  x = (x ^ 0xDEADBEEF) + 0x9E3779B1u;
  x ^= x >> 13;
  x *= 0x85EBCA6Bu;
  x ^= x >> 16;
  return (uint8_t)(x & 0xFF);
}

uint8_t sendBuff[ESP_NOW_BRDCAST_PKTLEN];
esp_err_t sendEncPacket( const uint8_t * data, size_t len ){
  sendBuff[ESP_NOW_BRDCAST_PKTLEN-2] = txCtr & 0x0F;
  sendBuff[ESP_NOW_BRDCAST_PKTLEN-1] = (txCtr & 0xF0) >> 4;
  for( int i = 0; i < ESP_NOW_BRDCAST_PKTLEN-2; ++i ){
    uint8_t c = 0;
    if( i < len)
      c = data[i];
    sendBuff[i] = c ^ (rand8(txCtr+i) + txKey[i]);
  }
  txCtr += 1;
  return esp_now_send(broadcastAddress, sendBuff, ESP_NOW_BRDCAST_PKTLEN);//(uint8_t *) &myData, sizeof(myData));
  
}

char recvData[ESP_NOW_BRDCAST_PKTLEN];
bool rcvDecryptPacket( const uint8_t * data, size_t len ){
  if(len != ESP_NOW_BRDCAST_PKTLEN)
    return false;
  uint8_t rxCtr = data[ESP_NOW_BRDCAST_PKTLEN-2] & 0x0F;
  rxCtr |= (data[ESP_NOW_BRDCAST_PKTLEN-1] & 0x0F) << 4;
  

  for( int i = 0; i < ESP_NOW_BRDCAST_PKTLEN-2; ++i ){
    uint8_t c = data[i];
    recvData[i] = c ^ (rand8(rxCtr+i) + txKey[i]);
  }
  recvData[ESP_NOW_BRDCAST_PKTLEN-1] = 0;
  //Serial.print("ctr "); Serial.print( rxCtr ); Serial.print(" data "); Serial.println(recvData);
  return true;
}

// callback for send status
void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status){  
  // optional: check status
  //Serial.print("\r\nLast Packet Send Status:\t");
  //Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void onDataRecv(const esp_now_recv_info *macAndInfo, const uint8_t *data, int len){  
  // handle received data
  //memcpy( recvData, data, len);
  rcvDecryptPacket( data, len );
  if ( strncmp(recvData, "sync", 4) == 0 ){
    have_sync = true;
    nextTxTime = millis() + ( (sampleIntervalUs / NUM_DEVICES) * (1 + device_id) );
    //Serial.println("sync rcvd");
  }else{
    //Serial.print("recvd: "); Serial.println( recvData );
    memcpy(&rcvPkt, recvData, sizeof(rcvPkt));
  }
}



// Wi-Fi placeholders
const char* WIFI_SSID = "Internet";
const char* WIFI_PASS = "4ydq9c1k";

const uint16_t UDP_PORT = 5005;

//WiFiUDP Udp;


void wifiConnect(){
  WiFi.mode(WIFI_STA); // STA mode is typical for ESP-NOW
  WiFi.setChannel(CHANNEL); // one radio, set channel for both wifi and esp32-now
  while (!WiFi.STA.started()) {
    delay(100);
  }
  Serial.println(WiFi.macAddress());
  esp_now_init();
  while (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
  }
  Serial.println("esp now setup");
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataRecv);
  // register broadcast peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = CHANNEL;
  peerInfo.encrypt = false; //can't use encrypt with broadcast peer
  if( esp_now_add_peer(&peerInfo) != ESP_OK ){
    Serial.println("Failed to add peer");
    return;
  }
  Serial.println("esp now peer added");
  /*
  WiFi.begin(WIFI_SSID, WIFI_PASS); //udp brodcast (255.255.255.255) or multicast is not radio level, the ap has to re transmit it
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED &&
          millis() - t0 < 20000) {
    Serial.print("reattempting connection to wifi ");
    Serial.println(WIFI_SSID);
    delay(200);
  }
  
  Serial.print("Connected to to wifi "); Serial.println(WIFI_SSID);
  // start UDP
  Udp.begin(UDP_PORT);
  Serial.print("Udp listener started on port "); Serial.println( UDP_PORT );
  */
}



/* //not using wifi udp because of ap rebrodcast (and polling) are both additional overhead / slow
// call regularly from loop() or a dedicated task
void pollSyncPacket(){
  int sz = Udp.parsePacket();
  if (sz >= 8) {
    uint8_t buf[8];
    Udp.read(buf,8);
    uint32_t epoch, interval;
    memcpy(&epoch, buf, 4);
    memcpy(&interval, buf+4,4);    // accept if reasonable
    if (interval > 0 && epoch != 0) {
      sync_epoch = epoch;
      sync_interval = interval;
      have_sync = true;
      nextTxTime = millis();
    }
  }
}
*/