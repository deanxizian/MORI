/* Simulated serial source using the exact firmware state machine + fake HAL.
 * Fixed virtual execution costs are stimuli, NEVER real timing measurements. */
#include "sim_hal.h"
#include "mori_telemetry.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 if(argc!=3){fprintf(stderr,"usage: SIMULATED_device frames normal|estop|imu_missing|reset\n");return 2;}
 char *end;long frames=strtol(argv[1],&end,10);if(*end||frames<1||frames>1000000)return 2;
 const char *scenario=argv[2];if(strcmp(scenario,"normal")&&strcmp(scenario,"estop")&&strcmp(scenario,"imu_missing")&&strcmp(scenario,"reset"))return 2;
 sim_hal_t s;mori_runtime_t r;sim_hal_init(&s);mori_runtime_init(&r,(mori_config_t){0},false,false);
 printf("INFO 0 MORI/1 " MORI_SCALE_INFO_FORMAT " source=SIMULATED physical=NOT_TESTED telemetry_stride=1 timing=INJECTED power_gate=0 balance_gate=0 head_gate=0 axes_gate=0\n",MORI_SCALE_INFO_ARGS);
 printf("HEADER MORI/1 %s\n",MORI_CSV_HEADER);
 for(long i=0;i<frames;i++){
  if(i==frames/2){
   if(!strcmp(scenario,"estop"))s.sample.estop_ok=false;
   if(!strcmp(scenario,"imu_missing"))s.sample.imu_ok=false;
   if(!strcmp(scenario,"reset")){sim_hal_init(&s);mori_runtime_init(&r,(mori_config_t){0},false,false);}
  }
  sim_tick(&s,&r);mori_log_t log;mori_log_snapshot(&log,&r,0,0,0);mori_log_print(stdout,&log);
 }
 return 0;
}
