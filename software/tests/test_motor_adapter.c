/* A contract stub of IDF v5.5.2 LEDC: synchronous duty-update requires fade service.
 * Based on local driver lines 1307..1332, 1579..1593. No real device IO. */
#include "peripherals.h"
#include "board.h"
#include "driver/ledc.h"
#include <stdio.h>
#include <stdlib.h>
static bool service,fail_io;static int failures,levels[49];static uint32_t duty[5];static int64_t clock_us;
static unsigned checks;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"FAIL %s\n",#c);exit(1);}}while(0)
int64_t esp_timer_get_time(void){return clock_us;}
esp_err_t gpio_config(const gpio_config_t *c){(void)c;return ESP_OK;}
esp_err_t gpio_set_level(int p,int level){levels[p]=level;return ESP_OK;}
int gpio_get_level(int p){return levels[p];}
esp_err_t ledc_timer_config(const ledc_timer_config_t *c){(void)c;return ESP_OK;}
esp_err_t ledc_channel_config(const ledc_channel_config_t *c){duty[c->channel]=c->duty;return ESP_OK;}
esp_err_t ledc_fade_func_install(int flags){(void)flags;service=true;return ESP_OK;}
esp_err_t ledc_set_duty_and_update(int mode,int channel,uint32_t value,uint32_t hpoint){
 (void)mode;(void)hpoint;
 if(!service||fail_io){failures++;return ESP_FAIL;}duty[channel]=value;return ESP_OK;
}
int main(void){
 levels[PIN_FAULT]=levels[PIN_ESTOP]=1;motor_init();
 CHECK(failures==0);CHECK(!levels[PIN_ARM]);CHECK(motor_io_ok());
 for(int i=0;i<4;i++)CHECK(duty[i]==0);
 mori_output_t out={.enable=true,.left=.1f,.right=.1f};
#ifdef MORI_TEST_LOCKED
 motor_apply(out);clock_us=2500;motor_apply(out);CHECK(!levels[PIN_ARM]);head_init();CHECK(!head_set(10));CHECK(duty[4]==0);
 printf("PASS %u assertions; SIMULATED default-locked motor/head adapter\n",checks);return 0;
#endif
 motor_apply(out);CHECK(levels[PIN_ARM]);
 clock_us=2500;motor_apply(out);CHECK(duty[0]>0&&duty[1]==0&&duty[2]==0&&duty[3]>0);
 out.left=-.1f;motor_apply(out);CHECK(duty[0]==0&&duty[1]>0);
 levels[PIN_ESTOP]=0;motor_apply(out);CHECK(!levels[PIN_ARM]);for(int i=0;i<4;i++)CHECK(duty[i]==0);
 levels[PIN_ESTOP]=1;head_init();CHECK(duty[4]==0);CHECK(head_set(10));CHECK(duty[4]>0);head_disable();CHECK(duty[4]==0);
 fail_io=true;motor_apply(out);clock_us+=2500;motor_apply(out);CHECK(!motor_io_ok());CHECK(!levels[PIN_ARM]);
 fail_io=false;motor_apply(out);CHECK(!levels[PIN_ARM]);
 printf("PASS %u assertions; SIMULATED IDF motor adapter contract (not physical timing)\n",checks);return 0;
}
