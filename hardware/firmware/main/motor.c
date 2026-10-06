#include "peripherals.h"
#include "board.h"
#include "driver/ledc.h"
#include "esp_timer.h"
#include "sdkconfig.h"
#include <math.h>
static bool enabled;static int64_t wake;
void motor_disable(void){
 gpio_set_level(PIN_ARM,0);enabled=false;
 for(int i=0;i<4;i++)ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,i,0,0);
}
void motor_init(void){
 gpio_config_t g={.pin_bit_mask=(1ULL<<PIN_ARM)|(1ULL<<PIN_HEARTBEAT),.mode=GPIO_MODE_OUTPUT,.pull_down_en=true};ESP_ERROR_CHECK(gpio_config(&g));
 gpio_set_level(PIN_ARM,0);gpio_set_level(PIN_HEARTBEAT,0);
 ledc_timer_config_t t={.speed_mode=LEDC_LOW_SPEED_MODE,.duty_resolution=LEDC_TIMER_10_BIT,.timer_num=LEDC_TIMER_0,.freq_hz=20000,.clk_cfg=LEDC_AUTO_CLK};ESP_ERROR_CHECK(ledc_timer_config(&t));
 int pins[]={PIN_AIN1,PIN_AIN2,PIN_BIN1,PIN_BIN2};
 for(int i=0;i<4;i++){ledc_channel_config_t c={.gpio_num=pins[i],.speed_mode=LEDC_LOW_SPEED_MODE,.channel=i,.timer_sel=LEDC_TIMER_0,.duty=0};ESP_ERROR_CHECK(ledc_channel_config(&c));}
 motor_disable();
}
static void set_pair(int base,float duty){
 duty=fminf(.65f,fmaxf(-.65f,duty));uint32_t d=(uint32_t)(fabsf(duty)*1023);
 /* Set the previously active input low first; never momentarily assert both. */
 ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,base,0,0);ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,base+1,0,0);
 if(d)ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,base+(duty<0),d,0);
}
void motor_apply(mori_output_t o){
 if(!o.enable||!isfinite(o.left)||!isfinite(o.right)){motor_disable();return;}
 if(!enabled){gpio_set_level(PIN_ARM,1);enabled=true;wake=esp_timer_get_time()+2000;}
 if(esp_timer_get_time()<wake)return; /* driver requires up to 1ms after nSLEEP */
 set_pair(0,o.left*MOTOR_LEFT_SIGN);set_pair(2,o.right*MOTOR_RIGHT_SIGN);
}
static bool head_started;
void head_init(void){
 ledc_timer_config_t t={.speed_mode=LEDC_LOW_SPEED_MODE,.duty_resolution=LEDC_TIMER_14_BIT,.timer_num=LEDC_TIMER_1,.freq_hz=50,.clk_cfg=LEDC_AUTO_CLK};ESP_ERROR_CHECK(ledc_timer_config(&t));
 ledc_channel_config_t c={.gpio_num=PIN_HEAD,.speed_mode=LEDC_LOW_SPEED_MODE,.channel=LEDC_CHANNEL_4,.timer_sel=LEDC_TIMER_1,.duty=0};ESP_ERROR_CHECK(ledc_channel_config(&c));head_started=true;
}
bool head_set(float deg){
#ifndef CONFIG_MORI_HEAD_VERIFIED
 (void)deg;return false;
#else
 if(!head_started||!isfinite(deg)||fabsf(deg)>50)return false; /* ±60 design, ±50 commissioning */
 /* SER0037 nominal 270deg/2000us; head gear radii 8:14.
    External gears reverse direction: sign must be measured before enabling. */
 float us=1500-deg*(14.0f/8.0f)*(2000.0f/270.0f);
 return ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_4,(uint32_t)(us/20000*16383),0)==ESP_OK;
#endif
}
void head_disable(void){if(head_started)ledc_set_duty_and_update(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_4,0,0);}
