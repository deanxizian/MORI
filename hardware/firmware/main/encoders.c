#include "peripherals.h"
#include "board.h"
#include "driver/pulse_cnt.h"
#include <math.h>
#include "esp_check.h"
#include <stdint.h>
static pcnt_unit_handle_t units[2];static int32_t last[2];
static int delta_window[2][8],index_n,n;static float elapsed_window[8];
esp_err_t encoders_init(void){
 int pins[2][2]={{PIN_ENC_LA,PIN_ENC_LB},{PIN_ENC_RA,PIN_ENC_RB}};
 for(int i=0;i<2;i++){
  pcnt_unit_config_t c={.low_limit=-30000,.high_limit=30000,.flags.accum_count=true};ESP_RETURN_ON_ERROR(pcnt_new_unit(&c,&units[i]),"enc","unit");
  pcnt_glitch_filter_config_t f={.max_glitch_ns=1000};ESP_RETURN_ON_ERROR(pcnt_unit_set_glitch_filter(units[i],&f),"enc","filter");
  for(int k=0;k<2;k++){
   pcnt_channel_handle_t ch;pcnt_chan_config_t cc={.edge_gpio_num=pins[i][k],.level_gpio_num=pins[i][1-k]};ESP_RETURN_ON_ERROR(pcnt_new_channel(units[i],&cc,&ch),"enc","channel");
   ESP_RETURN_ON_ERROR(pcnt_channel_set_edge_action(ch,k?PCNT_CHANNEL_EDGE_ACTION_DECREASE:PCNT_CHANNEL_EDGE_ACTION_INCREASE,k?PCNT_CHANNEL_EDGE_ACTION_INCREASE:PCNT_CHANNEL_EDGE_ACTION_DECREASE),"enc","edge");
   ESP_RETURN_ON_ERROR(pcnt_channel_set_level_action(ch,PCNT_CHANNEL_LEVEL_ACTION_INVERSE,PCNT_CHANNEL_LEVEL_ACTION_KEEP),"enc","level");
  }
  ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(units[i],30000),"enc","watch");ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(units[i],-30000),"enc","watch");
  ESP_RETURN_ON_ERROR(pcnt_unit_enable(units[i]),"enc","enable");ESP_RETURN_ON_ERROR(pcnt_unit_clear_count(units[i]),"enc","clear");ESP_RETURN_ON_ERROR(pcnt_unit_start(units[i]),"enc","start");
 }
 return ESP_OK;
}
bool encoders_read(float*vl,float*vr,float dt){
 bool ok=isfinite(dt)&&dt>0&&dt<.02;int sum[2]={0};float elapsed=0;
 for(int i=0;i<2;i++){int count=0;if(pcnt_unit_get_count(units[i],&count)!=ESP_OK)return false;
  int32_t delta=(int32_t)((uint32_t)count-(uint32_t)last[i]);last[i]=count;
  if(delta>80||delta< -80){ok=false;}
  delta_window[i][index_n]=delta;}
 elapsed_window[index_n]=dt;index_n=(index_n+1)%8;if(n<8)n++;
 for(int k=0;k<n;k++){elapsed+=elapsed_window[k];for(int i=0;i<2;i++)sum[i]+=delta_window[i][k];}
 *vl=elapsed>0?sum[0]*WHEEL_M_PER_COUNT/elapsed*ENCODER_LEFT_SIGN:0;
 *vr=elapsed>0?sum[1]*WHEEL_M_PER_COUNT/elapsed*ENCODER_RIGHT_SIGN:0;
 return ok;
}
