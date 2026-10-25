#pragma once
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_st77916.h"
#include "esp_codec_dev.h"
#include "esp_codec_dev_defaults.h"
#include "custom_io_expander_ch32v003.h"
#include "driver/spi_master.h"
#include <stdbool.h>
/* Hardware owns actual pins, FPC mapping, reset/backlight sequencing and clocks.
 * No defaults here turn an 18-pin connector into a compatible pinout. */
typedef struct {
 bool verified;
 spi_host_device_t host; spi_bus_config_t bus; int cs_gpio, reset_gpio;
 int clock_hz; const st77916_lcd_init_cmd_t *init_commands; uint16_t init_count;
 esp_lcd_panel_io_color_trans_done_cb_t done; void *context;
} mori_panel_config;
typedef struct {esp_lcd_panel_io_handle_t io;esp_lcd_panel_handle_t panel;spi_host_device_t host;} mori_panel;
esp_err_t mori_st77916_open(const mori_panel_config *config,mori_panel *panel);
/* Caller retains one internal-DMA stripe until color_trans_done; no stack/PSRAM
 * buffer handed to DMA without the caller's cache/lifetime contract. */
esp_err_t mori_st77916_stripe(mori_panel *panel,int y,int rows,const uint16_t *dma_pixels,bool buffer_verified);
void mori_st77916_close(mori_panel *panel);
esp_err_t mori_ch32_open(i2c_master_bus_handle_t bus,bool verified,esp_io_expander_handle_t *handle);
typedef struct {
 bool verified; audio_codec_i2s_cfg_t i2s; audio_codec_i2c_cfg_t adc_i2c,dac_i2c;
 int pa_gpio; float pa_voltage,codec_voltage;
} mori_audio_config;
typedef struct {
 const audio_codec_data_if_t *data; const audio_codec_gpio_if_t *gpio;
 const audio_codec_ctrl_if_t *adc_ctrl,*dac_ctrl; const audio_codec_if_t *adc,*dac;
 esp_codec_dev_handle_t mic,speaker;
} mori_audio_devices;
esp_err_t mori_codecs_open(const mori_audio_config *config,mori_audio_devices *devices);
void mori_codecs_close(mori_audio_devices *devices);
