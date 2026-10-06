#include "peripherals.h"
#include "board.h"
#include "mount_config.h"
#include "mori_runtime.h"
#include "mori_telemetry.h"
#include "mori_ui.h"
#include "sdkconfig.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_app_desc.h"
#include "esp_task_wdt.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <stdio.h>
#include <inttypes.h>
#include <stdatomic.h>

static TaskHandle_t control_handle;
static QueueHandle_t logs,parse_replies,head_updates;
static portMUX_TYPE mux=portMUX_INITIALIZER_UNLOCKED;
static uint64_t imu_edge_us;static unsigned irq_fault;
static mori_runtime_t runtime;
static atomic_bool ui_fault;
static atomic_uint parse_drops;
static bool peripherals_ok;
static mori_state_t published_state=MORI_DISARMED;
static uint32_t events,frame_number,sample_missed,log_dropped;
static uint64_t frame_begin,edge,last_begin;
static mori_sample_t cached;
typedef struct {uint32_t id;mori_reason_t reason;} parse_reply_t;
typedef struct {uint64_t us;float target;bool enabled;uint32_t revision;} head_update_t;

static void IRAM_ATTR data_ready(void *arg){
 (void)arg;uint64_t now=esp_timer_get_time();
 portENTER_CRITICAL_ISR(&mux);imu_edge_us=now;portEXIT_CRITICAL_ISR(&mux);
 BaseType_t wake=pdFALSE;if(control_handle)vTaskNotifyGiveFromISR(control_handle,&wake);if(wake)portYIELD_FROM_ISR();
}
static void IRAM_ATTR fault_edge(void *arg){
 gpio_set_level(PIN_ARM,0); /* external ESTOP/watchdog gating is still mandatory */
 portENTER_CRITICAL_ISR(&mux);irq_fault|=(unsigned)(uintptr_t)arg;portEXIT_CRITICAL_ISR(&mux);
}
static uint64_t clock_now(void *ctx){(void)ctx;return esp_timer_get_time();}
static void apply(void *ctx,mori_output_t out){(void)ctx;motor_apply(out);if(!motor_io_ok())mori_trip(&runtime.core,MF_DRIVER);}
static void heartbeat_complete(void *ctx,bool level){
 (void)ctx;
 if(gpio_get_level(PIN_ESTOP)&&gpio_get_level(PIN_FAULT))gpio_set_level(PIN_HEARTBEAT,level);
 else gpio_set_level(PIN_ARM,0);
}
static void after_apply(void *ctx){
 (void)ctx;atomic_store(&ui_fault,runtime.core.state==MORI_FAULT);
 head_update_t h={.us=frame_begin,.target=runtime.head_target,.enabled=runtime.head_active,.revision=runtime.head_revision};xQueueOverwrite(head_updates,&h);
 esp_task_wdt_reset();
}
static void sample(void *ctx,mori_sample_t *s,mori_timing_t *timing){
 (void)ctx;
 /* Publish the preceding COMPLETED frame, never hold a control lock or print. */
 if(runtime.frames&&(runtime.frames%40==0||runtime.core.state!=published_state)){
  mori_log_t log;mori_log_snapshot(&log,&runtime,sample_missed,log_dropped,atomic_load(&parse_drops));
  if(xQueueSend(logs,&log,0)!=pdTRUE)log_dropped++;
  else published_state=runtime.core.state;
 }
 *s=cached;uint64_t io=esp_timer_get_time();
 unsigned irq;portENTER_CRITICAL(&mux);irq=irq_fault;irq_fault=0;portEXIT_CRITICAL(&mux);
 s->driver_ok=gpio_get_level(PIN_FAULT)&&!(irq&1)&&motor_io_ok();s->estop_ok=gpio_get_level(PIN_ESTOP)&&!(irq&2);
 if(irq)mori_trip(&runtime.core,(irq&2)?MF_ESTOP:MF_DRIVER);
 s->imu_us=edge;s->imu_ok=peripherals_ok&&events==1&&imu_read(s)==ESP_OK;
 timing->imu_io_us=esp_timer_get_time()-io;
 timing->wake_us=edge<=frame_begin?(uint32_t)(frame_begin-edge):UINT32_MAX;
 io=esp_timer_get_time();float dt=last_begin?(frame_begin-last_begin)*1e-6f:1.f/416;
 s->encoders_ok=encoders_read(s,dt);timing->encoder_us=esp_timer_get_time()-io;
 if(frame_number%8==0){io=esp_timer_get_time();s->monitor_ok=peripherals_ok&&monitors_read(s)==ESP_OK;timing->monitor_io_us=esp_timer_get_time()-io;}
 cached=*s;
}
static void head_task(void *arg){
 (void)arg;head_update_t u={0};mori_head_trajectory_t trajectory={0};mori_head_guard_t guard={0};uint64_t last=esp_timer_get_time();
 while(1){
  xQueueReceive(head_updates,&u,pdMS_TO_TICKS(20));uint64_t now=esp_timer_get_time();float dt=(now-last)*1e-6f;last=now;
  bool fresh=now>=u.us&&now-u.us<=50000&&gpio_get_level(PIN_ESTOP)&&gpio_get_level(PIN_FAULT)&&!atomic_load(&ui_fault);
  bool allowed=mori_head_guard(&guard,u.revision,u.enabled,fresh,dt);
  if(!allowed){head_disable();trajectory.velocity=0;}
  else{mori_head_step(&trajectory,u.target,dt);if(!head_set(trajectory.position)){head_disable();guard.blocked=true;guard.blocked_revision=u.revision;}}
  vTaskDelay(pdMS_TO_TICKS(20));
 }
}
static void control_task(void *arg){
 (void)arg;
 /* This task owns ALL I2C initialization and transactions, including INA219. */
 peripherals_ok=sensors_init()==ESP_OK;
 esp_log_level_set("i2c.master",ESP_LOG_NONE); /* runtime driver errors are telemetry */
 esp_log_level_set("adc_oneshot",ESP_LOG_NONE);esp_log_level_set("adc_cali",ESP_LOG_NONE);
 esp_log_level_set("pcnt",ESP_LOG_NONE);esp_log_level_set("ledc",ESP_LOG_NONE);
 const mori_mount_t mount=MORI_MOUNT_INITIALIZER;
 if(!mori_mount_valid(&mount)){peripherals_ok=false;mori_trip(&runtime.core,MF_CONFIG);}
 ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
 mori_hal_t hal={.now_us=clock_now,.sample=sample,.apply=apply,.heartbeat=heartbeat_complete,.after_apply=after_apply};
 while(1){
  events=ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(8));frame_begin=esp_timer_get_time();
  portENTER_CRITICAL(&mux);edge=imu_edge_us;portEXIT_CRITICAL(&mux);
  if(events>1)sample_missed+=events-1;
  if(!events)sample_missed++;
  mori_runtime_frame(&runtime,&hal); /* Includes UI queue copies and bookkeeping before healthy heartbeat. */
  last_begin=frame_begin;frame_number++;
 }
}
static void info(uint32_t id){
 printf("HEADER MORI/1 %s\n",MORI_CSV_HEADER);
 const esp_app_desc_t *app=esp_app_get_description();
 printf("INFO %"PRIu32" MORI/1 " MORI_SCALE_INFO_FORMAT " target=esp32s3 candidate=DevKitC-1-N8R8-v1.1 idf=%s baud=115200 sample_hz=416 telemetry_stride=40 configured_flash_mb=8 psram_enabled=0 physical=NOT_TESTED power_gate=%d balance_gate=%d head_gate=%d axes_gate=%d image_sha256=",id,MORI_SCALE_INFO_ARGS,app->idf_ver,runtime.core.cfg.power_verified,runtime.core.cfg.balance_enabled,runtime.head_verified,runtime.axes_verified);
 for(unsigned i=0;i<sizeof(app->app_elf_sha256);i++){printf("%02x",app->app_elf_sha256[i]);}
 puts("");
 const mori_mount_t mount=MORI_MOUNT_INITIALIZER;
 printf("MOUNT MORI/1 R=");for(int i=0;i<3;i++)for(int j=0;j<3;j++)printf("%s%.6f",i||j?",":"",mount.rotation[i][j]);
 printf(" encoder=%d,%d output=%d,%d axes_gate=%d\n",mount.encoder_sign[0],mount.encoder_sign[1],mount.motor_sign[0],mount.motor_sign[1],runtime.axes_verified);
}
static void logging_task(void *arg){
 (void)arg;info(0);
 while(1){
  parse_reply_t parse;while(xQueueReceive(parse_replies,&parse,0)==pdTRUE)printf("REJECT %"PRIu32" MORI/1 reason=%s\n",parse.id,mori_reason_name(parse.reason));
  mori_reply_t reply;while(mori_runtime_reply(&runtime,&reply)){
   if(reply.kind==MP_INFO&&reply.reason==MR_OK)info(reply.id);
   printf("%s %"PRIu32" MORI/1 reason=%s state=%s fault=%d\n",reply.reason==MR_OK?"ACK":"REJECT",reply.id,mori_reason_name(reply.reason),mori_state_name(reply.state),reply.fault);
  }
  mori_log_t log;if(xQueueReceive(logs,&log,pdMS_TO_TICKS(10))==pdTRUE)mori_log_print(stdout,&log);
 }
}
static void parse_reject(uint32_t id,mori_reason_t reason){
 parse_reply_t reply={id,reason};if(xQueueSend(parse_replies,&reply,0)!=pdTRUE)atomic_fetch_add(&parse_drops,1);
}
static void console_task(void *arg){
 (void)arg;mori_line_t line={0};mori_request_t req;mori_reason_t reason;uint8_t byte;
 ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0,512,0,0,NULL,0));
 while(1){
  if(uart_read_bytes(UART_NUM_0,&byte,1,pdMS_TO_TICKS(20))==1){
   if(mori_line_feed(&line,byte,esp_timer_get_time(),&req,&reason)){
    if(reason!=MR_OK)parse_reject(req.id,reason);
    else if(!mori_runtime_enqueue(&runtime,req))parse_reject(req.id,MR_QUEUE);
   }
  }
  if(mori_line_expire(&line,esp_timer_get_time(),&reason))parse_reject(0,reason);
 }
}
void mori_legacy_bench_main(void){
 motor_init(); /* First peripheral action: ARM low and every wheel input low. */
 gpio_config_t input={.pin_bit_mask=(1ULL<<PIN_FAULT)|(1ULL<<PIN_ESTOP),.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_NEGEDGE};ESP_ERROR_CHECK(gpio_config(&input));
 ESP_ERROR_CHECK(gpio_install_isr_service(0));
 ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_FAULT,fault_edge,(void*)1));ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_ESTOP,fault_edge,(void*)2));
 ESP_ERROR_CHECK(encoders_init());head_init();
 mori_config_t cfg={0};bool head=false,axes=false;
#ifdef CONFIG_MORI_POWER_STAGE_VERIFIED
 cfg.power_verified=true;
#endif
#ifdef CONFIG_MORI_ENABLE_BALANCE
 cfg.balance_enabled=true;
#endif
#ifdef CONFIG_MORI_HEAD_VERIFIED
 head=true;
#endif
#ifdef CONFIG_MORI_AXES_VERIFIED
 axes=true;
#endif
 mori_runtime_init(&runtime,cfg,head,axes);atomic_init(&ui_fault,false);atomic_init(&parse_drops,0);
 logs=xQueueCreate(16,sizeof(mori_log_t));parse_replies=xQueueCreate(16,sizeof(parse_reply_t));head_updates=xQueueCreate(1,sizeof(head_update_t));configASSERT(logs&&parse_replies&&head_updates);
 gpio_config_t ir={.pin_bit_mask=1ULL<<PIN_IMU_INT,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_POSEDGE};ESP_ERROR_CHECK(gpio_config(&ir));ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_IMU_INT,data_ready,NULL));
 configASSERT(xTaskCreatePinnedToCore(control_task,"balance_io",6144,NULL,23,&control_handle,1)==pdPASS);
 configASSERT(xTaskCreatePinnedToCore(logging_task,"log",4096,NULL,2,NULL,0)==pdPASS);
 configASSERT(xTaskCreatePinnedToCore(console_task,"console",4096,NULL,3,NULL,0)==pdPASS);
 configASSERT(xTaskCreatePinnedToCore(head_task,"head",3072,NULL,2,NULL,0)==pdPASS);
 configASSERT(xTaskCreatePinnedToCore(display_task,"lcd",4096,&ui_fault,1,NULL,0)==pdPASS);
 /* No synthetic DRDY. An absent sensor remains unhealthy and cannot unlock. */
}
