#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "eyes.h"
#include "audio.h"
#include "adapters.h"
static uint16_t *pixels;
static mori_eyes_t eyes;
/* No physical peripherals started until V1 board/power contract is supplied. */
void app_main(void){
 lv_init();
 ESP_LOGI("MORI","MORI V1.2 / MORI/2; SKU33700 + ST77916 candidate; peripherals BLOCKED pending signed pins; custom wake BLOCKED");
 pixels=heap_caps_calloc(360*360,sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
 if(!pixels){ESP_LOGE("MORI","360x360 PSRAM allocation failed; display disabled");return;}
 int64_t largest=0;
 for(;;){int64_t begin=esp_timer_get_time();mori_eye_t frame[2];
  if(mori_eyes_sample(&eyes,(float)(begin/1000)/1000.f,0,frame))mori_eyes_render(frame,pixels,360,360);
  int64_t elapsed=esp_timer_get_time()-begin;if(elapsed>largest)largest=elapsed;
  /* A real panel adapter will submit bounded DMA stripes here. No motor lock exists in this domain. */
  vTaskDelay(pdMS_TO_TICKS(40)); /* 25 fps requested; actual time NOT_TESTED */
 }
}
