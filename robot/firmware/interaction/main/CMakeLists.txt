idf_component_register(SRCS "main.c" "adapters.c" "board_v12.c" "../core/eyes.c" "../core/audio.c"
  INCLUDE_DIRS "." "../core" REQUIRES esp_timer esp_driver_gpio esp_driver_i2s esp_wifi nvs_flash esp_http_client)
