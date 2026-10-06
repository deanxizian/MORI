idf_component_register(SRCS "main.c" "v1_main.c" "motor.c" "encoders.c" "sensors.c" "display.c"
    INCLUDE_DIRS "." REQUIRES mori_core mori_v1 esp_driver_gpio esp_driver_ledc esp_driver_pcnt
    esp_driver_i2c esp_driver_spi esp_adc esp_timer esp_lcd esp_system esp_driver_uart esp_app_format)
