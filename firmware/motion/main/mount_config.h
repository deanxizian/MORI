#pragma once
#include "mori_io.h"
/* PROTOTYPE / UNVALIDATED. Replace after six-face + manual forward-pitch test.
 * R maps IMU raw axes to control x forward, y left, z up, NOT from PCB silk.
 * Blender to control: (-Y, X, Z). This identity is ONLY a bench placeholder.
 * Signs remain unmeasured candidate values through HW-SW-0.4.
 * Control left = Blender Wheel_R/Motor_R (+X); control right = model L.
 * Both A/B are inverted by 3.3V-powered LVC14; this does not change phase order.
 * Record any sign or matrix edit in interface requests; never infer from labels.
 */
#define MORI_MOUNT_INITIALIZER { .rotation={{1,0,0},{0,1,0},{0,0,1}}, .encoder_sign={1,-1}, .motor_sign={1,-1} }
