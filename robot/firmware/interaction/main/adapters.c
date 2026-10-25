#include "adapters.h"
#include "sdkconfig.h"
/* No candidate GPIOs are fabricated. Caller must supply a hardware-signed board contract. */
esp_err_t mori_camera_start(const camera_config_t *config,bool verified){
#if CONFIG_MORI_ENABLE_PHYSICAL_CAMERA
 if(!verified||!config)return ESP_ERR_INVALID_STATE;
 return esp_camera_init(config);
#else
 (void)config;(void)verified;return ESP_ERR_NOT_SUPPORTED;
#endif
}
camera_fb_t *mori_camera_capture(bool authorized){
#if CONFIG_MORI_ENABLE_PHYSICAL_CAMERA
 return authorized?esp_camera_fb_get():NULL;
#else
 (void)authorized;return NULL;
#endif
}
void mori_camera_release(camera_fb_t *frame){if(frame)esp_camera_fb_return(frame);}
esp_afe_sr_data_t *mori_afe_start(srmodel_list_t *models,bool verified,esp_afe_sr_iface_t **interface){
#if CONFIG_MORI_ENABLE_PHYSICAL_AUDIO
 if(!verified||!models||!interface)return NULL;
 afe_config_t *config=afe_config_init("MR",models,AFE_TYPE_SR,AFE_MODE_LOW_COST);
 *interface=esp_afe_handle_from_config(config);
 esp_afe_sr_data_t *data=(*interface)->create_from_config(config);
 afe_config_free(config);return data;
#else
 (void)models;(void)verified;(void)interface;return NULL;
#endif
}
lv_obj_t *mori_eyes_canvas(lv_obj_t *parent,uint16_t *pixels,int w,int h){lv_obj_t *canvas=lv_canvas_create(parent);lv_canvas_set_buffer(canvas,pixels,w,h,LV_COLOR_FORMAT_RGB565);lv_obj_center(canvas);return canvas;}
