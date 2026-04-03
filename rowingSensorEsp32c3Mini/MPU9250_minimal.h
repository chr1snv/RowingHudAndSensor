#pragma once
#include <Wire.h>
#define MPU9250_ADDR 0x68
#define AK8963_ADDR  0x0C
bool mpu9250_begin() {
  Wire.begin(/*sda=*/7, /*scl=*/9); // use GPIO7 for SDA
  Wire.setClock(100000); // try 400kHz
  delay(10);
	//Wire.begin();
	Wire.beginTransmission(MPU9250_ADDR);
	Wire.write(0x6B); // PWR_MGMT_1
	Wire.write(0x00); // wake
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

int16_t ax,ay,az,gx,gy,gz,mx,my,mz;

bool mpu9250_read9(
          int16_t *ax,
					int16_t *ay,
					int16_t *az,
					int16_t *gx,
					int16_t *gy,
					int16_t *gz,
					int16_t *mx,
					int16_t *my,
					int16_t *mz)
{
		// read accel(0x3B) .. gyro(0x48)
		Wire.beginTransmission(MPU9250_ADDR);
		Wire.write(0x3B);
    uint8_t endTCode = Wire.endTransmission(false);
		if (endTCode != 0){
      Serial.print(endTCode);
      Serial.println(" fail to addr 0x3B");
			return false;
    }
		Wire.requestFrom(MPU9250_ADDR, (uint8_t)14);
		if (Wire.available() < 14){ 
      Serial.println("14 bytes not avaliable from accel");
      return false;
    }
		*ax = (Wire.read() << 8) | Wire.read();
		*ay = (Wire.read() << 8) | Wire.read();
		*az = (Wire.read() << 8) | Wire.read();
		Wire.read(); Wire.read(); // temp
		*gx = (Wire.read() << 8) | Wire.read();
		*gy = (Wire.read() << 8) | Wire.read();
		*gz = (Wire.read() << 8) | Wire.read();
		
		// Read magnetometer via AK8963 (requires enabling bypass)

    //write user ctrl (disable i2c master)
    Wire.beginTransmission(MPU9250_ADDR);
		Wire.write(0x6A); Wire.write(0x00);
    endTCode = Wire.endTransmission();
		if (endTCode != 0){
      Serial.print( endTCode );
      Serial.println("failed to disable i2c master");
			return false;
    }
    //read back user ctrl to confirm active
    uint8_t v=0;
    mpu_read_bytes(MPU9250_ADDR, 0x6A, 1, &v);
    Serial.printf("MPU9250_ADDR user ctrl 0x6A =0x%02X\n", v);

		// enable bypass
		Wire.beginTransmission(MPU9250_ADDR);
		Wire.write(0x37); Wire.write(0x22);
    endTCode = Wire.endTransmission();
		if (endTCode != 0){
      Serial.print( endTCode );
      Serial.println("fail to enable mpu i2c bypass");
			return false;
    }
    delay(30);
    //read back bypass to confirm active
    v=0;
    mpu_read_bytes(MPU9250_ADDR, 0x37, 1, &v);
    Serial.printf("i2c_bypass_CFG=0x%02X\n", v);

    // verify AK8963 present
    for( int i = 0; i < 3; ++i){

      delay(20);

      for( int j = 0; j < 5; ++j ){

        //read back user ctrl to confirm active
        uint8_t v=0;
        mpu_read_bytes(MPU9250_ADDR, 0x6A, 1, &v);
        Serial.printf("MPU9250_ADDR user ctrl 0x6A =0x%02X\n", v);
        //read back bypass to confirm active
        v=0;
        mpu_read_bytes(MPU9250_ADDR, 0x37, 1, &v);
        Serial.printf("i2c_bypass_CFG=0x%02X\n", v);


        Wire.beginTransmission(AK8963_ADDR);
        if (Wire.endTransmission()==0) 
          Serial.println("AK8963 ACK");
        else
          Serial.println("AK8963 NACK");
      }

      //Wire.begin(SDA_pin, SCL_pin);
      for (uint8_t a=1;a<127;a++){  
        Wire.beginTransmission(a);
        endTCode = Wire.endTransmission();
        if (endTCode==0) 
          Serial.printf("%i I2C device 0x%02X\n", endTCode, a);
        delay(10);
      }

      //read who am i of MPU
      v=0;
      mpu_read_bytes(MPU9250_ADDR, 0x75, 1, &v);
      Serial.printf("MPU9250_ADDR who am i 0x75 =0x%02X\n", v);


      //read who am i of AK8963 magnetometer
      uint8_t who = 0;
      if (!mpu_read_bytes(AK8963_ADDR, 0x00, 1, &who)){
        Serial.println("failed to read WAI (to verify AK8963 present");
        return false;
      }
      if (who != 0x48){
        Serial.printf("0x%02X unexpected WAI (not 0x48)\n", who);
        return false; // AK8963 WAI expected 0x48
      }

    }


		// set AK8963 to continuous measurement 1
		Wire.beginTransmission(AK8963_ADDR); Wire.write(0x0A); Wire.write(0x16);
    endTCode = Wire.endTransmission();
		if (endTCode != 0){
      Serial.print( endTCode );
      Serial.println(" fail to set AK8963 to continuous measurement 1");
			return false;
    }
		delay(10);
		Wire.beginTransmission(AK8963_ADDR); Wire.write(0x03);
    endTCode = Wire.endTransmission();
		if (endTCode != 0){
      Serial.print(endTCode);
      Serial.print("fail write to AK8963_ADDR 0x03");
			return false;
    }
		Wire.requestFrom(AK8963_ADDR, (uint8_t)7);
		if (Wire.available() < 7)
			return false;
		uint8_t sx = Wire.read(), sy = Wire.read(), sz = Wire.read();
		uint8_t st = Wire.read();
		if (st & 0x08) return false; // overflow
		*mx = (Wire.read() | (Wire.read() << 8));
		*my = (Wire.read() | (Wire.read() << 8));
		*mz = (Wire.read() | (Wire.read() << 8));
		return true;
}