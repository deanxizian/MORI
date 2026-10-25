#include "peripherals.h"
#include "board.h"
#include "mount_config.h"
#include "driver/pulse_cnt.h"
#include <math.h>
#include "esp_check.h"
#include <stdint.h>
static pcnt_unit_handle_t units[2];
static mori_encoder_t estimator;
static const mori_mount_t mount=MORI_MOUNT_INITIALIZER;
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
bool encoders_read(mori_sample_t *s,float dt){
 int32_t counts[2];float speeds[2];
 for(int i=0;i<2;i++){int count=0;if(pcnt_unit_get_count(units[i],&count)!=ESP_OK)return false;counts[i]=count;}
 bool ok=mori_encoder_update(&estimator,counts,dt,mount.encoder_sign,speeds);
 s->encoder_count[0]=counts[0];s->encoder_count[1]=counts[1];
 s->v_left=speeds[0];s->v_right=speeds[1];return ok;
}
