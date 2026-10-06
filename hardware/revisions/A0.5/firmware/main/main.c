#include "peripherals.h"
#include "board.h"
#include "mori_core.h"
#include "sdkconfig.h"
#include "esp_timer.h"
#include "esp_task_wdt.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
static TaskHandle_t control_handle;static QueueHandle_t commands,logs;
static portMUX_TYPE mux=portMUX_INITIALIZER_UNLOCKED;
static volatile uint64_t imu_edge_us;static volatile unsigned irq_fault;
static bool peripherals_ok;
typedef struct{mori_command_t cmd;bool head;float angle;} app_command_t;
typedef struct{uint64_t us;int state,fault;float angle,v,battery,current,tl,tr,ul,ur;uint32_t run_us,latency_us,max_run_us,max_latency_us,period_jitter_us,max_jitter_us,dropped;bool command_rejected;int cal_count;} log_t;
static void IRAM_ATTR data_ready(void*arg){(void)arg;uint64_t now=esp_timer_get_time();portENTER_CRITICAL_ISR(&mux);imu_edge_us=now;portEXIT_CRITICAL_ISR(&mux);BaseType_t w=pdFALSE;if(control_handle)vTaskNotifyGiveFromISR(control_handle,&w);if(w)portYIELD_FROM_ISR();}
static void IRAM_ATTR fault_edge(void*arg){(void)arg;gpio_set_level(PIN_ARM,0);portENTER_CRITICAL_ISR(&mux);irq_fault=1;portEXIT_CRITICAL_ISR(&mux);}
static float limit(float v,float lo,float hi){return fminf(hi,fmaxf(lo,v));}
static void control_task(void*arg){
 (void)arg;mori_t m;mori_config_t cfg={0};
#ifdef CONFIG_MORI_POWER_STAGE_VERIFIED
 cfg.power_verified=true;
#endif
#ifdef CONFIG_MORI_ENABLE_BALANCE
 cfg.balance_enabled=true;
#endif
 mori_init(&m,cfg);mori_sample_t s={0};
 ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
 uint64_t last=esp_timer_get_time();uint32_t max_run=0,max_latency=0,max_jitter=0,dropped=0;unsigned frame=0;bool heartbeat=false,head_active=false;
 float head_target=0,head_position=0,head_velocity=0;
 while(1){
  uint32_t events=ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(8));uint64_t begin=esp_timer_get_time(),edge;
  portENTER_CRITICAL(&mux);edge=imu_edge_us;unsigned irq=irq_fault;irq_fault=0;portEXIT_CRITICAL(&mux);
  float dt=(begin-last)*1e-6f;uint64_t period=begin-last;last=begin;
  s.now_us=begin;s.imu_us=edge;
  s.driver_ok=gpio_get_level(PIN_FAULT)&&motor_io_ok();s.estop_ok=gpio_get_level(PIN_ESTOP);
  if(irq&&(m.state==MORI_BENCH||m.state==MORI_BALANCE))mori_trip(&m,s.estop_ok?MF_DRIVER:MF_ESTOP);
  s.imu_ok=peripherals_ok&&events==1&&imu_read(&s)==ESP_OK;
  if(events>1)dropped+=events-1;
  s.encoders_ok=encoders_read(&s.v_left,&s.v_right,dt);
  if(frame%8==0){s.monitor_ok=peripherals_ok&&monitors_read(&s)==ESP_OK;}
  /* The monitoring timestamp can be later than begin. Use completion time for freshness,
     while retaining actual DRDY timestamp to measure scheduling and bus latency. */
  s.now_us=esp_timer_get_time();
  mori_output_t out=mori_step(&m,&s);
  bool rejected=false;app_command_t ac; /* commands only after current health sample */
  for(int k=0;k<2&&xQueueReceive(commands,&ac,0)==pdTRUE;k++){
   if(ac.head){
#ifndef CONFIG_MORI_HEAD_VERIFIED
    rejected=true;
#else
    if(m.state==MORI_FAULT||m.state==MORI_CALIBRATING||!s.estop_ok||!s.monitor_ok||!isfinite(ac.angle)||fabsf(ac.angle)>50)rejected=true;
    else{head_target=ac.angle;head_active=true;}
#endif
   }else if(!mori_command(&m,ac.cmd))rejected=true;
  }
  /* Re-read state after commands. Arming begins on next healthy sample; disarming is immediate. */
  if(m.state!=MORI_BALANCE&&m.state!=MORI_BENCH)out.enable=false;
  if(m.state==MORI_FAULT||!s.estop_ok){head_disable();head_active=false;}
  if(head_active&&frame%8==0){
   float hd=8.0f/416,desired_v=limit((head_target-head_position)*2,-30,30);
   head_velocity+=limit(desired_v-head_velocity,-60*hd,60*hd);head_position=limit(head_position+head_velocity*hd,-50,50);head_set(head_position);
  }
  uint32_t runtime=esp_timer_get_time()-begin;
  if(runtime>2404&&(m.state==MORI_BALANCE||m.state==MORI_BENCH)){mori_trip(&m,MF_TIMING);out.enable=false;}
  motor_apply(out);
  if(!motor_io_ok()){mori_trip(&m,MF_DRIVER);motor_disable();out.enable=false;}
  runtime=esp_timer_get_time()-begin;
  if(runtime>2404&&(m.state==MORI_BALANCE||m.state==MORI_BENCH)){mori_trip(&m,MF_TIMING);motor_disable();out.enable=false;}
  if(s.imu_ok&&s.monitor_ok&&s.encoders_ok&&s.estop_ok&&s.driver_ok&&runtime<=2404){heartbeat=!heartbeat;gpio_set_level(PIN_HEARTBEAT,heartbeat);}
  else gpio_set_level(PIN_ARM,0);
  esp_task_wdt_reset();
  runtime=esp_timer_get_time()-begin;uint32_t latency=(edge<=begin)?begin-edge:0;
  uint32_t jitter=(period>2404)?period-2404:2404-period;
  if(runtime>max_run){max_run=runtime;}
  if(latency>max_latency){max_latency=latency;}
  if(jitter>max_jitter){max_jitter=jitter;}
  if(frame%80==0||rejected||m.state==MORI_FAULT){log_t l={.us=begin,.state=m.state,.fault=m.fault,.angle=m.theta,.v=(s.v_left+s.v_right)/2,.battery=s.battery_v,.current=s.bus_a,.tl=s.temp_left_c,.tr=s.temp_right_c,.ul=out.enable?out.left:0,.ur=out.enable?out.right:0,.run_us=runtime,.latency_us=latency,.max_run_us=max_run,.max_latency_us=max_latency,.period_jitter_us=jitter,.max_jitter_us=max_jitter,.dropped=dropped,.command_rejected=rejected,.cal_count=m.calibration_count};xQueueOverwrite(logs,&l);}
  frame++;
 }
}
static void logging_task(void*arg){(void)arg;log_t l;puts("us,state,fault,pitch_rad,v_m_s,bat_V,motor_bus_A,TL_C,TR_C,uL,uR,run_us,wake_us,max_run_us,max_wake_us,jitter_us,max_jitter_us,dropped,rejected,cal_count");while(1)if(xQueueReceive(logs,&l,portMAX_DELAY))printf("%llu,%s,%d,%.5f,%.4f,%.3f,%.4f,%.1f,%.1f,%.4f,%.4f,%u,%u,%u,%u,%u,%u,%u,%d,%d\n",(unsigned long long)l.us,mori_state_name(l.state),l.fault,l.angle,l.v,l.battery,l.current,l.tl,l.tr,l.ul,l.ur,(unsigned)l.run_us,(unsigned)l.latency_us,(unsigned)l.max_run_us,(unsigned)l.max_latency_us,(unsigned)l.period_jitter_us,(unsigned)l.max_jitter_us,(unsigned)l.dropped,l.command_rejected,l.cal_count);}
static void parse_line(char*line){
 app_command_t c={0};bool valid=true;
 if(!strcmp(line,"calibrate"))c.cmd.type=MC_CALIBRATE;
 else if(!strcmp(line,"ack"))c.cmd.type=MC_ACK;
 else if(!strcmp(line,"arm bench"))c.cmd.type=MC_ARM_BENCH;
 else if(!strcmp(line,"arm balance"))c.cmd.type=MC_ARM_BALANCE;
 else if(!strcmp(line,"confirm_signs"))c.cmd.type=MC_CONFIRM_SIGNS;
 else if(!strcmp(line,"stop"))c.cmd.type=MC_STOP;
 else if(!strcmp(line,"disarm"))c.cmd.type=MC_DISARM;
 else if(sscanf(line,"duty %f %f",&c.cmd.a,&c.cmd.b)==2)c.cmd.type=MC_BENCH_DUTY;
 else if(sscanf(line,"move %f %f",&c.cmd.a,&c.cmd.b)==2)c.cmd.type=MC_MOVE;
 else if(sscanf(line,"gains %f %f %f %f",&c.cmd.a,&c.cmd.b,&c.cmd.c,&c.cmd.d)==4)c.cmd.type=MC_GAINS;
 else if(sscanf(line,"head %f",&c.angle)==1)c.head=true;
 else valid=false;
 if(!valid)puts("REJECT syntax; calibrate | arm bench | duty L R | confirm_signs | gains kp kd kv ki | arm balance | move m/s yaw_duty | stop | disarm | ack | head deg");
 else if(xQueueSend(commands,&c,0)!=pdTRUE)puts("REJECT command queue full");
}
static void console_task(void*arg){
 (void)arg;char line[120];size_t used=0;bool overflow=false;uint8_t ch;
 ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0,512,0,0,NULL,0));
 while(1)if(uart_read_bytes(UART_NUM_0,&ch,1,pdMS_TO_TICKS(100))==1){
  if(ch=='\n'||ch=='\r'){if(overflow)puts("REJECT line too long");else if(used){line[used]=0;parse_line(line);}used=0;overflow=false;}
  else if(used<sizeof(line)-1)line[used++]=ch;else overflow=true;
 }
}
void app_main(void){
 motor_init(); /* first hardware action, before any sensor/UI initialization */
 gpio_config_t inputs={.pin_bit_mask=(1ULL<<PIN_FAULT)|(1ULL<<PIN_ESTOP),.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_NEGEDGE};ESP_ERROR_CHECK(gpio_config(&inputs));
 ESP_ERROR_CHECK(gpio_install_isr_service(0));ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_FAULT,fault_edge,NULL));ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_ESTOP,fault_edge,NULL));
 ESP_ERROR_CHECK(encoders_init());head_init();
 peripherals_ok=sensors_init()==ESP_OK;
 gpio_config_t ir={.pin_bit_mask=1ULL<<PIN_IMU_INT,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_POSEDGE};ESP_ERROR_CHECK(gpio_config(&ir));ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_IMU_INT,data_ready,NULL));
 commands=xQueueCreate(8,sizeof(app_command_t));logs=xQueueCreate(1,sizeof(log_t));configASSERT(commands&&logs);
 xTaskCreatePinnedToCore(control_task,"balance_io",6144,NULL,23,&control_handle,1);
 portENTER_CRITICAL(&mux);imu_edge_us=esp_timer_get_time();portEXIT_CRITICAL(&mux);xTaskNotifyGive(control_handle); /* clears pending initial DRDY */
 xTaskCreatePinnedToCore(logging_task,"log",4096,NULL,2,NULL,0);
 xTaskCreatePinnedToCore(console_task,"console",4096,NULL,3,NULL,0);
 xTaskCreatePinnedToCore(display_task,"lcd",4096,NULL,1,NULL,0);
 printf("MORI PROTOTYPE / UNVALIDATED; peripherals=%s; motors disabled; Wi-Fi not initialized\n",peripherals_ok?"initialized (NOT physical PASS)":"FAILED");
}
