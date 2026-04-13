#include <Wire.h>
#define MPU9250_ADDR 0x68
//#define AK8963_ADDR  0x0C
// Buffers
int16_t ax, ay, az, gx, gy, gz;
//int16_t mx, my, mz;

bool mpu_write(uint8_t addr, uint8_t reg, uint8_t val) {
	Wire.beginTransmission(addr);
	Wire.write(reg);
	Wire.write(val);
	return Wire.endTransmission() == 0;
}

bool mpu_read_bytes(uint8_t addr, uint8_t reg, uint8_t count, uint8_t *buf) {
	Wire.beginTransmission(addr);
	Wire.write(reg);
	if (Wire.endTransmission(false) != 0)
		return false;
	uint8_t got = Wire.requestFrom((int)addr, (int)count);
	if (got != count)
		return false;
	for (uint8_t i = 0; i < count; ++i)
		buf[i] = Wire.read();
	return true;
}

/*
bool initMagBypass() {  // enable I2C bypass on MPU9250
  if (!mpu_write(MPU9250_ADDR, 0x37, 0x02)){
    Serial.println("enable I2C bypass on MPU9250");
    return false; // INT_PIN_CFG |= 0x02
  }
  delay(10);

  uint8_t v=0;
  mpu_read_bytes(MPU9250_ADDR, 0x37, 1, &v);
  Serial.printf("INT_PIN_CFG=0x%02X\n", v);
  if( ! (v & 0x02) ){
    mpu_read_bytes(MPU9250_ADDR,0x37,1,&v);
    v |= 0x02;
    mpu_write(MPU9250_ADDR,0x37,v);
  }

  // verify AK8963 present
  Wire.beginTransmission(AK8963_ADDR);
  if (Wire.endTransmission()==0) 
    Serial.println("AK8963 ACK");
  else
    Serial.println("AK8963 NACK");

    //Wire.begin(SDA_pin, SCL_pin);
    for (uint8_t a=1;a<127;a++){  
      Wire.beginTransmission(a);  
      if (Wire.endTransmission()==0) 
      Serial.printf("I2C device 0x%02X\n", a);
    }

  uint8_t who = 0;
  if (!mpu_read_bytes(AK8963_ADDR, 0x00, 1, &who)){
    Serial.println("failed to read WAI (to verify AK8963 present");
    return false;
  }
  if (who != 0x48){
    Serial.println("unexpected WAI (not 0x48)");
    return false; // AK8963 WAI expected 0x48
  }

  // power down
  if (!mpu_write(AK8963_ADDR, 0x0A, 0x00)){
    Serial.println("failed to write power down to AK8963");
    return false;
  }
  delay(10);

  // (optional) read ASA: set FUSE_ACCESS mode 0x0F then read 0x10..0x12, then power down again

  // set 16-bit continuous measurement mode 2 (100Hz)
  if (!mpu_write(AK8963_ADDR, 0x0A, 0x16)){
    Serial.println("failed to write set 16-bit continuous measurement mode 2 (100Hz) to AK8963");
    return false;
  }

  delay(10);

  return true;
}
*/

/*
// This config programs MPU9250 I2C master to read AK8963 registers 0x03..0x09 into EXT_SENS_DATA registers.bool 
bool initMagViaMPU() {  
  // Reset and basic MPU config omitted — assume MPU is awake and accessible at MPU_ADDR.
  
  // Disable bypass (ensure bit1 INT_PIN_CFG = 0)  
  // Optional: read-modify-write if you previously set it.  
  // Configure MPU I2C master clock (I2C_MST_CTRL = 0x0D for 400kHz)  
  if (!mpu_write(MPU9250_ADDR, 0x24, 0x0D)) {
    Serial.println("fail Configure MPU I2C master clock (I2C_MST_CTRL = 0x0D for 400kHz)");
    return false; // I2C_MST_CTRL
  }
  // Configure Slave 0 to read from AK8963  
  // I2C_SLV0_ADDR = AK8963_ADDR | 0x80 (read)  
  if (!mpu_write(MPU9250_ADDR, 0x25, AK8963_ADDR | 0x80)){ 
    Serial.println("fail Configure Slave 0 to read from AK8963");
    return false; // I2C_SLV0_ADDR  
  }
  // I2C_SLV0_REG = start reg (0x03)  
  if (!mpu_write(MPU9250_ADDR, 0x26, 0x03)){ 
    Serial.println("fail I2C_SLV0_REG = start reg (0x03)");
    return false; // I2C_SLV0_REG  
  }
  // I2C_SLV0_CTRL: enable, read length=7  
  if (!mpu_write(MPU9250_ADDR, 0x27, 0x87)){
    Serial.println("fail I2C_SLV0_CTRL: enable, read length=7");
    return false; // EN=1, LEN=7
  }

  // (Optional) Configure slave 1 for AK8963 CNTL1 writes (e.g., set continuous mode)  
  // To set CNTL1: write AK8963_ADDR (write mode) to I2C_SLV0_ADDR, I2C_SLV0_REG=0x0A, and 
  //I2C_SLV0_DO=0x16 then enable I2C_SLV0_CTRL with EN to write once.  
  // Simpler: use direct mpu_write via bypass temporarily to set CNTL1, then disable bypass and enable master reads.
  delay(10);  
  return true;
}
*/

bool mpu9250_init() {
	Wire.begin(/*sda=*/7, /*scl=*/9); // use GPIO7 for SDA
	Wire.setClock(400000); // try 400kHz
  delay(10);

	// Wake device
	if (!mpu_write(MPU9250_ADDR, 0x6B, 0x00))
		return false; // PWR_MGMT_1 = 0

	// Configure accel/gyro (optional: set ranges, filters)
	mpu_write(MPU9250_ADDR, 0x1B, 0x00); // gyro FS = ±250dps
	mpu_write(MPU9250_ADDR, 0x1C, 0x00); // accel FS = ±2g
	mpu_write(MPU9250_ADDR, 0x1A, 0x03); // DLPF ~44Hz (tune as needed)

  //initMagBypass();
  //initMagViaMPU();
/*
	// Enable I2C bypass to talk to AK8963 directly
	if (!mpu_write(MPU9250_ADDR, 0x37, 0x02))
		return false; // INT_PIN_CFG = 0x02 (bypass enabled)

	// Configure AK8963: power down -> enter fuse read -> set continuous mode
	// (Read ASA if you need sensitivity adjustments; omitted here for brevity)
	if (!mpu_write(AK8963_ADDR, 0x0A, 0x00))
		return false; // power down
	delay(10);
	if (!mpu_write(AK8963_ADDR, 0x0A, 0x16))
		return false; // continuous measurement 2 (100Hz), 16-bit output
	delay(10);
  */

	return true;
}

bool read_accel_gyro() {
	uint8_t buf[14];
	if (!mpu_read_bytes(MPU9250_ADDR, 0x3B, 14, buf))
		return false;
	ax = (int16_t)((buf[0] << 8) | buf[1]);
	ay = (int16_t)((buf[2] << 8) | buf[3]);
	az = (int16_t)((buf[4] << 8) | buf[5]);
	// skip temp buf[6..7]
	gx = (int16_t)((buf[8] << 8) | buf[9]);
	gy = (int16_t)((buf[10] << 8) | buf[11]);
	gz = (int16_t)((buf[12] << 8) | buf[13]);
	return true;
}
/*
// To read magnetometer data when using MPU master mode:
bool readMagViaMPU() {  
  uint8_t buf[7];  
  // EXT_SENS_DATA starts at 0x49 (EXT_SENS_DATA_00) on MPU9250  
  if (!mpu_read_bytes(MPU9250_ADDR, 0x49, 7, buf)) 
    return false;  
  if (buf[6] & 0x08) 
    return false; // overflow  
  mx = (int16_t)((buf[1] << 8) | buf[0]);  
  my = (int16_t)((buf[3] << 8) | buf[2]);  
  mz = (int16_t)((buf[5] << 8) | buf[4]);  
  return true;
}


bool read_mag_via_bypass() {
	// Read 7 bytes from AK8963 starting at 0x03
	uint8_t buf[7];
	if (!mpu_read_bytes(AK8963_ADDR, 0x03, 7, buf)){
    Serial.println("!mpu_read_bytes(AK8963_ADDR, 0x03, 7,");
		return false;
  }
  uint8_t st = buf[6];
	if (st & 0x08){ 
    Serial.println("magnetic sensor overflow");
    return false; // magnetic sensor overflow
  }
	// Note: AK8963 outputs little-endian (low, high)
	mx = (int16_t)((buf[1] << 8) | buf[0]);
	my = (int16_t)((buf[3] << 8) | buf[2]);
	mz = (int16_t)((buf[5] << 8) | buf[4]);
	return true;
}
*/
