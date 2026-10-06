#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef enum { MORI_DISARMED, MORI_CALIBRATING, MORI_READY, MORI_BENCH, MORI_BALANCE, MORI_FAULT } mori_state_t;
typedef enum { MF_NONE, MF_SENSOR, MF_ESTOP, MF_DRIVER, MF_LOW_VOLTAGE, MF_OVERVOLTAGE, MF_CURRENT, MF_TEMPERATURE, MF_TILT, MF_ENCODER, MF_SATURATION, MF_TIMING } mori_fault_t;
typedef struct {
    uint64_t now_us, imu_us, monitor_us;
    float ax,ay,az,gy; /* m/s^2, rad/s; robot X forward, Y left, Z up */
    float v_left,v_right, battery_v,bus_a,temp_left_c,temp_right_c;
    bool imu_ok,monitor_ok,encoders_ok,driver_ok,estop_ok;
} mori_sample_t;
typedef struct { bool power_verified,balance_enabled; float kp,kd,kv,ki; } mori_config_t;
typedef struct { float left,right; bool enable,low_battery,request_support; } mori_output_t;
typedef enum { MC_CALIBRATE, MC_ACK, MC_ARM_BENCH, MC_ARM_BALANCE, MC_BENCH_DUTY, MC_MOVE, MC_STOP, MC_DISARM, MC_GAINS, MC_CONFIRM_SIGNS } mori_command_type_t;
typedef struct { mori_command_type_t type; float a,b,c,d; } mori_command_t;
typedef struct {
    mori_state_t state; mori_fault_t fault; mori_config_t cfg;
    float theta,bias,v_target,v_ref,yaw_target,velocity_i,bench_left,bench_right;
    bool calibrated,signs_confirmed,have_sample;
    uint64_t previous_us,last_command_us,bench_deadline_us,saturation_us,stall_left_us,stall_right_us;
    unsigned calibration_count; double gyro_sum,gyro_sum2;
    mori_sample_t latest; mori_output_t out;
} mori_t;
void mori_init(mori_t *m,mori_config_t cfg);
void mori_trip(mori_t *m,mori_fault_t fault);
bool mori_command(mori_t *m,mori_command_t cmd);
mori_output_t mori_step(mori_t *m,const mori_sample_t *sample);
const char *mori_state_name(mori_state_t state);
