/* MORI adapters; dependency APIs checked against pinned vendor components.
 * CAM BSP reference is Apache-2.0, revision recorded in THIRD_PARTY_V1_2.md.
 * This is one interaction loop, not a copy of the vendor demonstration main. */
#include "board_v12.h"
#include "sdkconfig.h"
#include <string.h>
#include <math.h>
static bool display_gate(void){
#if CONFIG_MORI_ENABLE_PHYSICAL_DISPLAY && CONFIG_MORI_INTERACTION_BOARD_VERIFIED
 return true;
#else
 return false;
#endif
}
static bool audio_gate(void){
#if CONFIG_MORI_ENABLE_PHYSICAL_AUDIO && CONFIG_MORI_INTERACTION_BOARD_VERIFIED
 return true;
#else
 return false;
#endif
}
void mori_st77916_close(mori_panel *p){if(!p)return;if(p->panel)esp_lcd_panel_del(p->panel);if(p->io)esp_lcd_panel_io_del(p->io);if(p->panel||p->io)spi_bus_free(p->host);memset(p,0,sizeof(*p));}
esp_err_t mori_st77916_open(const mori_panel_config *c,mori_panel *p){
 if(!c||!p||!c->verified||!display_gate())return ESP_ERR_NOT_SUPPORTED;
 if(c->clock_hz<=0||c->clock_hz>40000000||!c->init_commands||!c->init_count||!c->done||c->bus.max_transfer_sz<360*16*2)return ESP_ERR_INVALID_ARG;
 memset(p,0,sizeof(*p));p->host=c->host;
 esp_err_t e=spi_bus_initialize(c->host,&c->bus,SPI_DMA_CH_AUTO);if(e!=ESP_OK)return e;
 esp_lcd_panel_io_spi_config_t io=ST77916_PANEL_IO_QSPI_CONFIG(c->cs_gpio,c->done,c->context);io.pclk_hz=c->clock_hz;io.trans_queue_depth=1;
 e=esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)c->host,&io,&p->io);
 if(e!=ESP_OK){spi_bus_free(c->host);return e;}
 st77916_vendor_config_t v={.init_cmds=c->init_commands,.init_cmds_size=c->init_count,.flags.use_qspi_interface=1};
 esp_lcd_panel_dev_config_t cfg={.reset_gpio_num=c->reset_gpio,.rgb_ele_order=LCD_RGB_ELEMENT_ORDER_RGB,.bits_per_pixel=16,.vendor_config=&v};
 e=esp_lcd_new_panel_st77916(p->io,&cfg,&p->panel);
 if(e==ESP_OK)e=esp_lcd_panel_reset(p->panel);
 if(e==ESP_OK)e=esp_lcd_panel_init(p->panel);
 if(e==ESP_OK)e=esp_lcd_panel_disp_on_off(p->panel,true);
 if(e!=ESP_OK)mori_st77916_close(p);
 return e;
}
esp_err_t mori_st77916_stripe(mori_panel *p,int y,int rows,const uint16_t *pixels,bool dma_verified){
 if(!display_gate()||!p||!p->panel||!pixels||!dma_verified)return ESP_ERR_INVALID_STATE;
 if(y<0||rows<1||rows>16||y>360-rows)return ESP_ERR_INVALID_ARG;
 return esp_lcd_panel_draw_bitmap(p->panel,0,y,360,y+rows,pixels);
}
esp_err_t mori_ch32_open(i2c_master_bus_handle_t bus,bool verified,esp_io_expander_handle_t *handle){
 if(!verified||!display_gate()||!bus||!handle)return ESP_ERR_NOT_SUPPORTED;
 return custom_io_expander_new_i2c_ch32v003(bus,CUSTOM_IO_EXPANDER_I2C_CH32V003_ADDRESS,handle);
}
void mori_codecs_close(mori_audio_devices *d){
 if(!d)return;
 if(d->mic){esp_codec_dev_close(d->mic);esp_codec_dev_delete(d->mic);}
 if(d->speaker){esp_codec_dev_close(d->speaker);esp_codec_dev_delete(d->speaker);}
 if(d->adc)audio_codec_delete_codec_if(d->adc);
 if(d->dac)audio_codec_delete_codec_if(d->dac);
 if(d->adc_ctrl)audio_codec_delete_ctrl_if(d->adc_ctrl);
 if(d->dac_ctrl)audio_codec_delete_ctrl_if(d->dac_ctrl);
 if(d->data)audio_codec_delete_data_if(d->data);
 if(d->gpio)audio_codec_delete_gpio_if(d->gpio);
 memset(d,0,sizeof(*d));
}
esp_err_t mori_codecs_open(const mori_audio_config *c,mori_audio_devices *d){
 if(!c||!d||!c->verified||!audio_gate())return ESP_ERR_NOT_SUPPORTED;
 if(!c->i2s.tx_handle||!c->i2s.rx_handle||!c->adc_i2c.bus_handle||!c->dac_i2c.bus_handle||!isfinite(c->pa_voltage)||c->pa_voltage<=0||!isfinite(c->codec_voltage)||c->codec_voltage<=0)return ESP_ERR_INVALID_ARG;
 memset(d,0,sizeof(*d));audio_codec_i2s_cfg_t data=c->i2s;audio_codec_i2c_cfg_t adc=c->adc_i2c,dac=c->dac_i2c;
 d->data=audio_codec_new_i2s_data(&data);d->gpio=audio_codec_new_gpio();d->adc_ctrl=audio_codec_new_i2c_ctrl(&adc);d->dac_ctrl=audio_codec_new_i2c_ctrl(&dac);
 if(!d->data||!d->gpio||!d->adc_ctrl||!d->dac_ctrl)goto fail;
 es8311_codec_cfg_t cfg={.ctrl_if=d->dac_ctrl,.gpio_if=d->gpio,.codec_mode=ESP_CODEC_DEV_WORK_MODE_DAC,.pa_pin=c->pa_gpio,.use_mclk=true,.hw_gain={.pa_voltage=c->pa_voltage,.codec_dac_voltage=c->codec_voltage}};
 es7210_codec_cfg_t mic={.ctrl_if=d->adc_ctrl};d->dac=es8311_codec_new(&cfg);d->adc=es7210_codec_new(&mic);if(!d->dac||!d->adc)goto fail;
 esp_codec_dev_cfg_t output={.dev_type=ESP_CODEC_DEV_TYPE_OUT,.codec_if=d->dac,.data_if=d->data};
 esp_codec_dev_cfg_t input={.dev_type=ESP_CODEC_DEV_TYPE_IN,.codec_if=d->adc,.data_if=d->data};
 d->speaker=esp_codec_dev_new(&output);d->mic=esp_codec_dev_new(&input);if(!d->speaker||!d->mic)goto fail;
 /* Open sample format and physical I2S routing are a separate signed bench step.
  * No inferred microphone/reference ordering; AEC remains unverified. */
 return ESP_OK;
fail:mori_codecs_close(d);return ESP_FAIL;
}
