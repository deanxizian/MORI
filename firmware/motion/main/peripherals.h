#pragma once
#include "esp_err.h"
#include "mori_core.h"
void motor_init(void);
void motor_apply(mori_output_t out);
void motor_disable(void);
bool motor_io_ok(void);
void head_init(void);
bool head_set(float degrees);
void head_disable(void);
esp_err_t sensors_init(void);
esp_err_t imu_read(mori_sample_t *sample);
esp_err_t monitors_read(mori_sample_t *sample);
esp_err_t encoders_init(void);
bool encoders_read(mori_sample_t *sample,float dt);
void display_task(void *arg);
