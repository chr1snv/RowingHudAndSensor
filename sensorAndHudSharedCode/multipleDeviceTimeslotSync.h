
#ifndef MULTDEVTIMESYNC
#define MULTDEVTIMESYNC

#include <WiFi.h>
#include "esp_wifi.h"
int staRssi;

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
//const uint8_t CHANNEL = 1; // choose channel and use same on all devices

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
bool espNowReady = false;

uint8_t sendBuff[ESP_NOW_BRDCAST_PKTLEN];
esp_err_t sendEncPacket( const uint8_t * data, size_t len ){
  if( !espNowReady )
    return 0;
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



#define MAX_STORED_NETWORKS 10


// Function to dynamically swap or update the broadcast peer layout
void UpdateEspNowPeerChannel(uint8_t newChannel) {

	if (!espNowReady) return;

	// 1. Remove the old broadcast peer if it exists
	if (esp_now_is_peer_exist(broadcastAddress)) {
		esp_now_del_peer(broadcastAddress);
	}

	// 2. Re-register the peer matching the updated Wi-Fi system channel
	esp_now_peer_info_t peerInfo = {};
	memcpy(peerInfo.peer_addr, broadcastAddress, 6);
	peerInfo.channel = newChannel; // Sync with new home channel!
	peerInfo.encrypt = false;      // Encryption must be false for broadcast

	if (esp_now_add_peer(&peerInfo) == ESP_OK) {
		Serial.printf("[ESP-NOW] Successfully synced peer configuration to Channel: %d\n", newChannel);
	} else {
		Serial.println("[ESP-NOW] Failed to update peer channel structure");
	}
}


bool InitEspNow(uint8_t channel){
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
  peerInfo.channel = channel;
  peerInfo.encrypt = false; //can't use encrypt with broadcast peer
  if( esp_now_add_peer(&peerInfo) != ESP_OK ){
    Serial.println("Failed to add peer");
    return false;
  }
  Serial.println("esp now peer added");
  espNowReady = true;
  return true;
}

//using esp now instead of wifi udp because of ap rebrodcast (and polling) are both additional overhead / slow


#endif