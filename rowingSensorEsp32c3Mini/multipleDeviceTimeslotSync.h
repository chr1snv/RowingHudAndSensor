
#define SYNC_PORT 6006

//for synchronization of broadcast
const uint8_t NUM_DEVICES = 18;
volatile uint32_t sync_epoch = 0;
volatile uint32_t sync_interval = 0;
volatile bool have_sync = false;

void setupSyncNode(){  
  Udp.begin(SYNC_PORT);
}

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
    }  
  }
}

// compute next slot start ms (relative to millis())
uint32_t computeNextSlotStart(uint32_t now_ms){
  // slot duration within full interval cycle
  uint32_t slot_ms = sync_interval / NUM_DEVICES;
  // base cycle start = sync_epoch (ms)
  // find last cycle start <= now_ms: cycle = sync_epoch + k*sync_interval
  int64_t diff = (int64_t)now_ms - (int64_t)sync_epoch;
  int64_t k = diff >= 0 ? diff / sync_interval : -1 + (diff+1)/sync_interval;
  int64_t cycle_start = (int64_t)sync_epoch + k * (int64_t)sync_interval;
  if (cycle_start > now_ms) cycle_start -= sync_interval;
  uint32_t slot_start = (uint32_t)(cycle_start + (device_id - 1) * (int64_t)slot_ms);  // if slot_start <= now_ms, advance by sync_interval until in future
  while (slot_start <= now_ms)
    slot_start += sync_interval;
  return slot_start;
}