#include "sdkconfig.h"
#include "mori_v1.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_log.h"
#include <inttypes.h>
static mori_v1_t device;
void mori_legacy_bench_main(void);
void app_main(void){
#ifdef CONFIG_MORI_LEGACY_BENCH_PROFILE
 mori_legacy_bench_main();
#else
 uint64_t session=((uint64_t)esp_random()<<32)|esp_random();mori_v1_init(&device,session?session:1);
 ESP_LOGI("MORI","MORI/2 V1 motion: boot DISARMED, session=%"PRIu64"; physical board contract BLOCKED; no peripheral GPIO initialized",device.session);
 /* Link parser and four-actuator core compile here. Hardware task must supply signed
    UART pins, electrical isolation, sensor profile and both head mappings before bind. */
 for(;;){mori_v1_tick(&device,esp_timer_get_time()/1000,NULL);vTaskDelay(pdMS_TO_TICKS(10));}
#endif
}
