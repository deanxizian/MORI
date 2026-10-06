#include "peripherals.h"
#include "board.h"
#include "mori_ui.h"
#include <stdatomic.h>
#include "sdkconfig.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_gc9a01.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#if CONFIG_MORI_LCD_ENABLE
static SemaphoreHandle_t complete;
static bool IRAM_ATTR sent(esp_lcd_panel_io_handle_t io,esp_lcd_panel_io_event_data_t*e,void*ctx){(void)io;(void)e;(void)ctx;BaseType_t wake=pdFALSE;xSemaphoreGiveFromISR(complete,&wake);return wake==pdTRUE;}
#endif
void display_task(void*arg){
 #if CONFIG_MORI_LCD_ENABLE
 atomic_bool *fault=arg;
 complete=xSemaphoreCreateBinary();
 spi_bus_config_t bus={.mosi_io_num=PIN_LCD_MOSI,.miso_io_num=-1,.sclk_io_num=PIN_LCD_CLK,.quadwp_io_num=-1,.quadhd_io_num=-1,.max_transfer_sz=240*8*2};
 if(spi_bus_initialize(SPI2_HOST,&bus,SPI_DMA_CH_AUTO)!=ESP_OK){ESP_LOGE("lcd","SPI init failed");vTaskDelete(NULL);return;}
 esp_lcd_panel_io_handle_t io;esp_lcd_panel_io_spi_config_t cfg={.dc_gpio_num=PIN_LCD_DC,.cs_gpio_num=PIN_LCD_CS,.pclk_hz=20000000,.lcd_cmd_bits=8,.lcd_param_bits=8,.spi_mode=0,.trans_queue_depth=2,.on_color_trans_done=sent};
 if(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST,&cfg,&io)!=ESP_OK){ESP_LOGE("lcd","IO init failed");vTaskDelete(NULL);return;}
 esp_lcd_panel_handle_t panel;esp_lcd_panel_dev_config_t dev={.reset_gpio_num=PIN_LCD_RST,.rgb_ele_order=LCD_RGB_ELEMENT_ORDER_RGB,.bits_per_pixel=16};
 if(esp_lcd_new_panel_gc9a01(io,&dev,&panel)!=ESP_OK||esp_lcd_panel_reset(panel)!=ESP_OK||esp_lcd_panel_init(panel)!=ESP_OK||esp_lcd_panel_disp_on_off(panel,true)!=ESP_OK){ESP_LOGE("lcd","panel init failed");vTaskDelete(NULL);return;}
 uint16_t *buf=heap_caps_malloc(240*8*2,MALLOC_CAP_DMA);if(!buf){vTaskDelete(NULL);return;}
 unsigned frame=0;
 while(1){
  for(int y=0;y<240;y+=8){
   for(int row=0;row<8;row++)for(int x=0;x<240;x++){
    uint16_t color=mori_face_pixel(240,240,x,y+row,atomic_load(fault),frame%40==0);
    buf[row*240+x]=(color>>8)|(color<<8);
   }
   if(esp_lcd_panel_draw_bitmap(panel,0,y,240,y+8,buf)!=ESP_OK||xSemaphoreTake(complete,pdMS_TO_TICKS(100))!=pdTRUE){ESP_LOGE("lcd","DMA timeout: display task halted");vTaskDelete(NULL);return;}
  }
  frame++;vTaskDelay(pdMS_TO_TICKS(100)); /* isolated low-priority task, <=10fps */
 }
#else
 (void)arg;
 vTaskDelete(NULL);
#endif
}
