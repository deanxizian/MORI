#pragma once
#include "esp_err.h"
#include "esp_camera.h"
#include "esp_afe_sr_iface.h"
#include "esp_afe_sr_models.h"
#include "model_path.h"
#include "lvgl.h"
esp_err_t mori_camera_start(const camera_config_t *config,bool verified);
camera_fb_t *mori_camera_capture(bool authorized);
void mori_camera_release(camera_fb_t *frame);
esp_afe_sr_data_t *mori_afe_start(srmodel_list_t *models,bool verified,esp_afe_sr_iface_t **interface);
lv_obj_t *mori_eyes_canvas(lv_obj_t *parent,uint16_t *pixels,int width,int height);
