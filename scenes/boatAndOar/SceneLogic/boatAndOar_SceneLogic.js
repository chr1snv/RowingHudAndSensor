//# sourceURL=SceneLogic/boatAndOar/boatAndOar_sceneLogic.js

function boatAndOar_sceneSpecificLoad(){
	console.log("boatAndOar_sceneSpecificLoad");
	

	//MDL_RemoveFromOctTree( oarMdl )
	
	ldScnLdCmpCb();
}

lastBoatStatusReqTime = 0;
boatStatusReqInterval = 1.0/30.0; //30 fps

boatDeviceStatuses = []



function computeEulerFromIMU(sensors) {
	let roll = 0, pitch = 0, yaw = 0;

	if (sensors.accel) {
		let ax = sensors.accel.ax;
		let ay = sensors.accel.ay;
		let az = sensors.accel.az;

		// Calculate Roll and Pitch from gravity vector
		roll = Math.atan2(ay, az);
		pitch = Math.atan2(-ax, Math.sqrt(ay * ay + az * az));
	}

	if (sensors.mag && sensors.accel) {
		let mx = sensors.mag.mx;
		let my = sensors.mag.my;
		let mz = sensors.mag.mz;

		// Tilt compensation using Accel angles
		let cosR = Math.cos(roll), sinR = Math.sin(roll);
		let cosP = Math.cos(pitch), sinP = Math.sin(pitch);

		let Xh = mx * cosP + my * sinR * sinP + mz * cosR * sinP;
		let Yh = my * cosR - mz * sinR;

		// Yaw angle (Heading relative to magnetic North)
		yaw = Math.atan2(-Yh, Xh);
	}

	return [roll, pitch, yaw]; // Array matching Matrix_SetEulerTransformation layout
}


// Hardcoded sensor-to-body layout correction. 
// If your magnetometer is physically rotated 90 deg relative to the accel, remap axes here!
function getCalibratedVectors(sensors) {
	let acc = [sensors.accel.ax, sensors.accel.ay, sensors.accel.az];
	// MPU_x = Mag_y
	// MPU_y = Mag_x
	// MPU_z = -Mag_z
	let mag = [sensors.mag.my, sensors.mag.mx, -sensors.mag.mz]; 

	// Normalize accelerometer vector (Gravity)
	let aLen = Math.sqrt(acc[0]*acc[0] + acc[1]*acc[1] + acc[2]*acc[2]);
	if (aLen > 0) { acc = [acc[0]/aLen, acc[1]/aLen, acc[2]/aLen]; }

	// Normalize magnetometer vector
	let mLen = Math.sqrt(mag[0]*mag[0] + mag[1]*mag[1] + mag[2]*mag[2]);
	if (mLen > 0) { mag = [mag[0]/mLen, mag[1]/mLen, mag[2]/mLen]; }
	
	console.log( "acc " + acc[0].toFixed(4) + ":" + acc[1].toFixed(4) + ":" + acc[2].toFixed(4) );
	console.log( "mag " + mag[0].toFixed(4) + ":" + mag[1].toFixed(4) + ":" + mag[2].toFixed(4) );
	
	return { acc, mag };
}

function computeQuaternionFQA(sensors) {
	if (!sensors.accel || !sensors.mag) return [0, 0, 0, 1]; // Identity quaternion [x,y,z,w]

	let { acc, mag } = getCalibratedVectors(sensors);

	// 1. Calculate Pitch Quaternion (Rotation about Y axis)
	let sinP = acc[0]; 
	sinP = Math.max(-1, Math.min(1, sinP)); // Clamp boundaries
	let cosP = Math.sqrt(1 - sinP * sinP);

	let s_halfP = sinP >= 0 ? Math.sqrt((1 - cosP) / 2) : -Math.sqrt((1 - cosP) / 2);
	let c_halfP = Math.sqrt((1 + cosP) / 2);
	let q_pitch = [0, s_halfP, 0, c_halfP]; // [x, y, z, w]

	// 2. Calculate Roll Quaternion (Rotation about X axis)
	let sinR = 0, cosR = 1;
	if (cosP !== 0) {
		sinR = -acc[1] / cosP;
		cosR = -acc[2] / cosP;
	}
	let s_halfR = sinR >= 0 ? Math.sqrt((1 - cosR) / 2) : -Math.sqrt((1 - cosR) / 2);
	let c_halfR = Math.sqrt((1 + cosR) / 2);
	let q_roll = [s_halfR, 0, 0, c_halfR];

	// Combine Pitch and Roll to get the tilt-quaternion
	// q_tilt = q_pitch * q_roll
	let q_tilt = [
		q_pitch[3]*q_roll[0] + q_pitch[1]*q_roll[2], // x
		q_pitch[1]*q_roll[3] + q_pitch[3]*q_roll[1], // y
		q_pitch[3]*q_roll[2] - q_pitch[1]*q_roll[0], // z
		q_pitch[3]*q_roll[3] - q_pitch[1]*q_roll[1]  // w
	];

	// 3. Calculate Yaw Quaternion (Tilt-Compensated Heading about Z axis)
	// Project Magnetometer vector onto the horizontal plane using tilt components
	let hx = mag[0]*cosP + mag[1]*sinR*sinP + mag[2]*cosR*sinP;
	let hy = mag[1]*cosR - mag[2]*sinR;
	let hLen = Math.sqrt(hx*hx + hy*hy);

	let cosY = hLen > 0 ? hx / hLen : 1;
	let sinY = hLen > 0 ? -hy / hLen : 0;

	let s_halfY = sinY >= 0 ? Math.sqrt((1 - cosY) / 2) : -Math.sqrt((1 - cosY) / 2);
	let c_halfY = Math.sqrt((1 + cosY) / 2);
	let q_yaw = [0, 0, s_halfY, c_halfY];
 
	// 4. Final Orientation Quaternion (q_final = q_yaw * q_tilt)
	return [
		q_yaw[3]*q_tilt[0] - q_yaw[2]*q_tilt[1], // x
		q_yaw[3]*q_tilt[1] + q_yaw[2]*q_tilt[0], // y
		q_yaw[3]*q_tilt[2] + q_yaw[2]*q_tilt[3], // z
		q_yaw[3]*q_tilt[3] - q_yaw[2]*q_tilt[2]  // w
	];
}




function boatAndOar_update(time, cam, rb2DTris, rb3DTris_array, rb3DLines_array){
	//console.log("boatAndOar1_update");
	
	if( time - lastBoatStatusReqTime > boatStatusReqInterval ){
		lastBoatStatusReqTime = time;
		sendCmd( "BoatStatus" );
	}
	
	MDL_RemoveFromOctTree( mainScene.modelNames["oarBladeReference"] );
	MDL_RemoveFromOctTree( mainScene.modelNames["Oar"] );
	
	//Matrix_SetEulerTransformation( retMat,  scale, rot, trans )
	let pOarMdl = mainScene.modelNames["PortOar"];
	let sOarMdl = mainScene.modelNames["STBOar"];
	
	if (typeof latestOarData === 'undefined')
		return;
	
	imuQuatAngle = computeQuaternionFQA( latestOarData.sensors );
	
	Matrix_SetQuatTransformation( pOarMdl.optTransMat, 
				[1,1,1],
				imuQuatAngle, //[-1*Math.cos(time), 0, 1*Math.sin(time)],
				pOarMdl.origin );
	pOarMdl.optTransformUpdated = true;
	
	Matrix_SetEulerTransformation( sOarMdl.optTransMat, 
				[1,1,1],
				[1*Math.cos(time), 0, (Math.PI)+(-1)*Math.sin(time)],
				sOarMdl.origin );
	sOarMdl.optTransformUpdated = true;
	
	FlyingCameraControlInput( time );
	GatherModelsToDrawForDefaultMainCam();
}