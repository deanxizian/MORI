#ifndef MORI12_H
#define MORI12_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* SI at the public boundary. Raw bus values remain explicitly named raw. */
#define MORI12_VERSION "1.2.0-dev.1"
#define S288_TX_BYTES 20u
#define S288_RX_BYTES 26u
#define S288_RATIO (70070.0 / 243.0)
typedef struct { uint8_t id, mode; bool timeout; double torque_nm, speed_rad_s, position_rad, kp, kd; } s288_command;
typedef struct {
 uint8_t id, mode, sensor, voltage_raw, warning; int8_t temperature_c; bool timeout_active;
 int16_t torque_raw, speed_raw; int32_t rotor_position_raw; uint32_t errors;
 uint16_t output_position_raw; double torque_estimate_nm, speed_rad_s, position_rad, absolute_output_rad, voltage_v;
} s288_feedback;
bool s288_crc(const uint8_t *bytes, size_t len, uint32_t *crc);
bool s288_encode(const s288_command *command, uint8_t out[S288_TX_BYTES]);
bool s288_decode(const uint8_t *packet, size_t len, uint8_t expected_id, s288_feedback *out);
typedef struct {int encoder_sign,output_sign;double servo_turns_per_wheel_turn,wheel_radius_m,allowed_servo_torque_nm;bool verified;} mori_wheel_cal;
bool mori_wheel_velocity(const s288_feedback *feedback,const mori_wheel_cal *calibration,double *m_s);
/* Input torque is at the S288 output, not rotor/raw PWM/independent load measurement. */
bool mori_wheel_torque_packet(uint8_t id,double servo_output_nm,const mori_wheel_cal *calibration,uint8_t packet[S288_TX_BYTES]);
typedef struct { uint8_t bytes[S288_RX_BYTES]; size_t used; uint32_t bad_frames, discarded; } s288_stream;
bool s288_feed(s288_stream *stream, uint8_t byte, uint8_t expected_id, s288_feedback *out);
typedef struct { bool valid; int32_t last; int64_t accumulated; uint64_t sampled_us; } s288_position;
bool s288_unwrap(s288_position *state, int32_t raw, uint64_t sampled_us, uint64_t max_gap_us, uint32_t max_delta);
bool mori_uart_divider(uint32_t clock_hz, uint32_t baud, uint32_t max_error_ppm, uint16_t *brr, double *actual_baud);

/* DMA completion is NOT end-of-wire. Release the TX driver only on UART TC.
 * One request per wheel per cycle, no retries inside a control frame. */
typedef enum { BUS_IDLE, BUS_TX_DMA, BUS_WAIT_TC, BUS_RX } mori_bus_phase;
typedef struct {
 mori_bus_phase phase; uint8_t wheel; uint64_t deadline_us, feedback_us[2];
 uint32_t timeouts[2], valid_frames[2]; bool tx_enable;
} mori_bus;
bool mori_bus_start(mori_bus *bus, uint64_t now_us, uint32_t timeout_us);
void mori_bus_dma_done(mori_bus *bus);
void mori_bus_tc(mori_bus *bus);
bool mori_bus_reply(mori_bus *bus, uint8_t wheel, uint64_t now_us);
bool mori_bus_poll(mori_bus *bus, uint64_t now_us);
bool mori_bus_fresh(const mori_bus *bus, uint64_t now_us, uint32_t max_age_us, uint32_t max_skew_us);

typedef struct { uint8_t id, error, voltage_raw, temperature_c; uint16_t position_raw; int speed_raw, load_raw; } scs_feedback;
size_t scs_read_feedback(uint8_t id, uint8_t out[8]);
bool scs_write_position(uint8_t id, uint16_t position, uint16_t time_ms, uint16_t speed_raw, uint8_t out[13]);
bool scs_decode_feedback(const uint8_t *packet, size_t len, uint8_t id, scs_feedback *out);
typedef struct { double zero_raw, rad_per_count, min_rad, max_rad; int sign; bool verified; } mori_joint_cal;
bool scs_joint_angle(const scs_feedback *fb, const mori_joint_cal *cal, double *angle_rad);
typedef struct { double angle[2], velocity[2]; } mori_head;
typedef bool (*mori_head_region)(double yaw, double pitch, void *context);
bool mori_head_step(mori_head *head, const double target[2], double dt_s, double max_speed, double max_accel,
                    mori_head_region reachable, void *context, bool inhibited);

typedef struct { double accel_m_s2[3], gyro_rad_s[3], temperature_c; uint64_t sampled_us; bool valid; } mori_imu;
bool icm42688_identity(uint8_t who_am_i);
bool mori_rotation_valid(const double rotation[9]);
/* Bank 0 burst 0x1D..0x2A; big-endian, explicit range from verified configuration. */
bool icm42688_decode(const uint8_t *burst, size_t len, double accel_range_g, double gyro_range_deg_s,
                    const double rotation[9], uint64_t sampled_us, mori_imu *out);

typedef enum { M_BOOT, M_SELF_TEST, M_DISARMED, M_ARMED_IDLE, M_MOVING, M_AUTONOMY, M_MAINTENANCE, M_FAULT } mori_state;
typedef enum { F_NONE, F_IMU, F_WHEEL, F_TILT, F_POWER, F_ESTOP, F_SATURATION, F_CONTROL_TIMEOUT, F_INPUT, F_QUEUE } mori_fault;
typedef struct {
 bool physical_verified, axes_verified, parameters_verified;
 double wheel_radius_m, torque_limit_nm, kp_pitch, kd_pitch, kp_speed, ki_speed, max_pitch_ref_rad;
 double severe_tilt_rad; uint32_t imu_age_us, wheel_age_us, skew_us, max_control_gap_us, saturation_us;
 uint32_t version;
} mori_parameters;
typedef struct {
 double pitch_rad, pitch_rate_rad_s, velocity_m_s; uint64_t imu_us, wheel_us[2];
 bool imu_valid, wheel_valid[2], power_ok, estop_ok, low_battery, head_valid;
} mori_sample;
typedef struct {
 mori_state state; mori_fault fault; mori_parameters parameters;
 uint64_t last_frame_us, lease_end_us, saturated_since_us; bool have_frame, saturating;
 bool drive_requested, external_inhibit_requested, heartbeat_edge, head_inhibited;
 double target_v, target_turn_nm, limited_v, integral, pitch_reference_rad, left_nm, right_nm;
 uint32_t healthy_frames;
} mori_motion;
void mori_motion_init(mori_motion *motion);
bool mori_parameters_valid(const mori_parameters *parameters);
bool mori_motion_configure(mori_motion *motion, const mori_parameters *parameters, bool supported);
bool mori_motion_arm(mori_motion *motion, const mori_sample *sample, uint64_t now_us, bool local_confirm);
bool mori_motion_target(mori_motion *motion, double v_m_s, double turn_nm, uint64_t now_us, uint32_t lease_us);
void mori_motion_stop(mori_motion *motion);
void mori_motion_fault(mori_motion *motion, mori_fault fault);
bool mori_motion_ack(mori_motion *motion, bool supported, bool manual_confirm);
bool mori_motion_disarm(mori_motion *motion, bool supported);
void mori_motion_step(mori_motion *motion, const mori_sample *sample, uint64_t now_us);
#endif
