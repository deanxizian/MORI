#pragma once
#include "esp_err.h"
#include <stdint.h>
#define LEDC_LOW_SPEED_MODE 0
#define LEDC_TIMER_10_BIT 10
#define LEDC_TIMER_14_BIT 14
#define LEDC_TIMER_0 0
#define LEDC_TIMER_1 1
#define LEDC_AUTO_CLK 0
#define LEDC_CHANNEL_4 4
typedef struct{int speed_mode,duty_resolution,timer_num,freq_hz,clk_cfg;} ledc_timer_config_t;
typedef struct{int gpio_num,speed_mode,channel,timer_sel;uint32_t duty;} ledc_channel_config_t;
esp_err_t ledc_timer_config(const ledc_timer_config_t *);
esp_err_t ledc_channel_config(const ledc_channel_config_t *);
esp_err_t ledc_fade_func_install(int);
esp_err_t ledc_set_duty_and_update(int,int,uint32_t,uint32_t);
