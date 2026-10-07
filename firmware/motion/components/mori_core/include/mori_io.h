#pragma once
#include <stdbool.h>
#include <stdint.h>
#define MORI_SOFTWARE_VERSION "SW-0.4"
#define MORI_REQUIREMENTS_BASELINE "HW-SW-0.4"
#define MORI_SOURCE_SNAPSHOT "HW-SW-0.4"
#define MORI_WORKSPACE_ORIGIN "HW-SW-0.3"
/* Pololu #4863: decoded A/B edges, ALREADY x4. One runtime source of scale. */
#define MORI_MOTOR_ENCODER_CPR 48.0
#define MORI_GEAR_RATIO (22.0 * 22.0 * 22.0 * 23.0 / (12.0 * 1000.0))
#define MORI_BELT_RATIO 1.0
#define MORI_WHEEL_COUNTS_PER_TURN (MORI_MOTOR_ENCODER_CPR * MORI_GEAR_RATIO * MORI_BELT_RATIO)
/* Wheel diameter mirrors authoritative root params.json, never a competing CAD definition. */
#define MORI_WHEEL_M_PER_COUNT (3.14159265358979323846 * .095 / MORI_WHEEL_COUNTS_PER_TURN)
/* INFO uses the same constants in both device and simulated sources. */
#define MORI_SCALE_INFO_FORMAT "firmware=" MORI_SOFTWARE_VERSION " requirements=" MORI_REQUIREMENTS_BASELINE " snapshot=" MORI_SOURCE_SNAPSHOT " origin=" MORI_WORKSPACE_ORIGIN " wheel_counts_per_turn=%.3f wheel_m_per_count=%.12f"
#define MORI_SCALE_INFO_ARGS (double)MORI_WHEEL_COUNTS_PER_TURN,(double)MORI_WHEEL_M_PER_COUNT
typedef struct { float rotation[3][3]; int encoder_sign[2],motor_sign[2]; } mori_mount_t;
bool mori_mount_valid(const mori_mount_t *mount);
void mori_rotate(const mori_mount_t *mount,const float raw[3],float control[3]);
bool mori_adc_voltage(int raw,int calibrated_mv,float *v);
bool mori_ntc(float v,float *temperature);
float mori_shunt_current(uint8_t high,uint8_t low);
typedef struct { uint32_t last[2]; int32_t delta[2][8]; float elapsed[8]; unsigned index,count; } mori_encoder_t;
bool mori_encoder_update(mori_encoder_t *encoder,const int32_t count[2],float dt,const int signs[2],float speed[2]);
