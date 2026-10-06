#include "peripherals.h"
#include "board.h"
#include "driver/i2c_master.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include <math.h>
static i2c_master_dev_handle_t imu,ina;static adc_oneshot_unit_handle_t adc;static adc_cali_handle_t cal;
static esp_err_t rd(i2c_master_dev_handle_t d,uint8_t r,uint8_t*b,size_t n){return i2c_master_transmit_receive(d,&r,1,b,n,1);}
static esp_err_t wr(i2c_master_dev_handle_t d,uint8_t r,uint8_t v){uint8_t b[]={r,v};return i2c_master_transmit(d,b,2,10);}
esp_err_t sensors_init(void){
 i2c_master_bus_handle_t bus;i2c_master_bus_config_t b={.i2c_port=I2C_NUM_0,.sda_io_num=PIN_SDA,.scl_io_num=PIN_SCL,.clk_source=I2C_CLK_SRC_DEFAULT,.glitch_ignore_cnt=7,.flags.enable_internal_pullup=false};ESP_RETURN_ON_ERROR(i2c_new_master_bus(&b,&bus),"sensor","bus");
 i2c_device_config_t d={.dev_addr_length=I2C_ADDR_BIT_LEN_7,.device_address=0x6a,.scl_speed_hz=400000};ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus,&d,&imu),"sensor","imu");
 d.device_address=0x40;ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus,&d,&ina),"sensor","ina");
 uint8_t id=0;ESP_RETURN_ON_ERROR(rd(imu,0x0f,&id,1),"sensor","whoami");if(id!=0x6c)return ESP_ERR_INVALID_RESPONSE;
 ESP_RETURN_ON_ERROR(wr(imu,0x12,0x01),"sensor","reset");vTaskDelay(pdMS_TO_TICKS(20));
 ESP_RETURN_ON_ERROR(wr(imu,0x12,0x44),"sensor","BDU IF_INC");
 ESP_RETURN_ON_ERROR(wr(imu,0x10,0x60),"sensor","acc 416Hz 2g");
 ESP_RETURN_ON_ERROR(wr(imu,0x11,0x64),"sensor","gyro 416Hz 500dps");
 ESP_RETURN_ON_ERROR(wr(imu,0x0d,0x02),"sensor","INT1 gyro DRDY active high");
 uint8_t cfg[]={0x00,0x39,0x9f}; /* INA219 32V, +/-320mV, 12-bit shunt+bus continuous */
 ESP_RETURN_ON_ERROR(i2c_master_transmit(ina,cfg,3,10),"sensor","ina config");
 adc_oneshot_unit_init_cfg_t ai={.unit_id=ADC_UNIT_1};ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&ai,&adc),"sensor","adc");
 adc_oneshot_chan_cfg_t ac={.atten=ADC_ATTEN_DB_12,.bitwidth=ADC_BITWIDTH_DEFAULT};
 int channels[]={ADC_CHANNEL_0,ADC_CHANNEL_1,ADC_CHANNEL_3};for(int i=0;i<3;i++)ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(adc,channels[i],&ac),"sensor","adc channel");
 adc_cali_curve_fitting_config_t cf={.unit_id=ADC_UNIT_1,.atten=ADC_ATTEN_DB_12,.bitwidth=ADC_BITWIDTH_DEFAULT};
 ESP_RETURN_ON_ERROR(adc_cali_create_scheme_curve_fitting(&cf,&cal),"sensor","calibration unavailable: inhibit arming");
 return ESP_OK;
}
esp_err_t imu_read(mori_sample_t*s){
 uint8_t status=0,data[12];ESP_RETURN_ON_ERROR(rd(imu,0x1e,&status,1),"sensor","status");if((status&3)!=3)return ESP_ERR_INVALID_STATE;
 ESP_RETURN_ON_ERROR(rd(imu,0x22,data,12),"sensor","sample");
 int16_t gy=(int16_t)((uint16_t)data[2]|((uint16_t)data[3]<<8));s->gy=gy*.0175f*(3.141592654f/180);
 float *out[]={&s->ax,&s->ay,&s->az};for(int i=0;i<3;i++){int k=6+2*i;int16_t raw=(int16_t)((uint16_t)data[k]|((uint16_t)data[k+1]<<8));*out[i]=raw*.000061f*9.80665f;}
 return ESP_OK;
}
static esp_err_t voltage(int channel,float*volts){int raw,mv;ESP_RETURN_ON_ERROR(adc_oneshot_read(adc,channel,&raw),"sensor","adc read");if(raw<10||raw>4080)return ESP_ERR_INVALID_RESPONSE;ESP_RETURN_ON_ERROR(adc_cali_raw_to_voltage(cal,raw,&mv),"sensor","adc mv");*volts=mv*.001f;return ESP_OK;}
static bool ntc(float v,float*t){
 /* Pull-up 10k to 3.3V, Murata NCP18XH103F03RB 10k/B3380 to GND. */
 if(v<.08f||v>3.05f){return false;}
 float r=10000*v/(3.3f-v);*t=1/(1/298.15f+logf(r/10000)/3380)-273.15f;return isfinite(*t);
}
esp_err_t monitors_read(mori_sample_t*s){
 uint8_t b[2];ESP_RETURN_ON_ERROR(rd(ina,0x01,b,2),"sensor","shunt");int16_t shunt=(int16_t)((uint16_t)b[0]<<8|b[1]);s->bus_a=shunt*.0001f;
 float v;ESP_RETURN_ON_ERROR(voltage(ADC_CHANNEL_0,&v),"sensor","battery");s->battery_v=v*4; /*30k /10k divider*/
 ESP_RETURN_ON_ERROR(voltage(ADC_CHANNEL_1,&v),"sensor","NTC L");if(!ntc(v,&s->temp_left_c))return ESP_ERR_INVALID_RESPONSE;
 ESP_RETURN_ON_ERROR(voltage(ADC_CHANNEL_3,&v),"sensor","NTC R");if(!ntc(v,&s->temp_right_c))return ESP_ERR_INVALID_RESPONSE;
 s->monitor_us=esp_timer_get_time();return ESP_OK;
}
