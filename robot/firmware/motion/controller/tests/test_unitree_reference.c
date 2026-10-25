/* Differential HOST_TEST, not captured/golden hardware packets.
 * Upstream protocol.c and crc_ccitt.h retain their original terms. */
#include "mori12.h"
#include "protocol.h"
#include "crc_ccitt.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static int16_t le16(const uint8_t *p){uint16_t v=p[0]|(uint16_t)p[1]<<8;return (int16_t)(v<32768?v:(int)v-65536);}
static int32_t le32(const uint8_t *p){uint32_t v=p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;return (int32_t)(v<=INT32_MAX?(int64_t)v:(int64_t)v-4294967296LL);}
int main(void){
 assert(sizeof(ControlData_t)==20&&sizeof(RecvData_t)==28);
 unsigned packets=0,rounding_differences=0;
 for(int i=-20;i<=20;i++){
  MotorCmd_t ref={0};ref.id=(unsigned)(i+20)%15;ref.mode=i!=0;ref.timeout=1;
  ref.outputTor=(float)(i*.00137);ref.outputSpd=(float)(i*.123);ref.outputPos=(float)(i*.00777);ref.Kp=2.3f;ref.Kd=.02f;
  s288_command cmd={ref.id,ref.mode,true,ref.outputTor,ref.outputSpd,ref.outputPos,ref.Kp,ref.Kd};
  uint8_t bytes[20];assert(s288_encode(&cmd,bytes));modify_data(&ref);
  assert(memcmp(bytes,&ref.motor_send_data,4)==0);
  const uint8_t *v=(const uint8_t *)&ref.motor_send_data;
  const unsigned words[]={4,6,12,14};
  for(unsigned j=0;j<4;j++){int delta=le16(bytes+words[j])-le16(v+words[j]);assert(abs(delta)<=1);rounding_differences+=delta!=0;}
  assert(llabs((long long)le32(bytes+8)-le32(v+8))<=1);
  uint32_t crc;assert(s288_crc(bytes,16,&crc));assert(crc==crc32_lookup_byte_by_byte(bytes,16));packets++;
 }
 uint8_t feedback[26]={0xfc,0xee,0x90,25,200,24,0,1,128,0,0,128,0,0,0,0,0,0,0,16,0,0};
 uint32_t crc=crc32_lookup_byte_by_byte(feedback+2,20);for(unsigned i=0;i<4;i++)feedback[22+i]=(uint8_t)(crc>>(8*i));
 MotorData_t vendor={0};vendor.rxlen=26;memcpy(vendor.motor_recv_data.head,feedback,26);extract_data(&vendor);assert(vendor.correct);
 s288_feedback own;assert(s288_decode(feedback,26,0,&own));assert(fabs(own.speed_rad_s-vendor.outputSpd)<1e-5);assert(fabs(own.torque_estimate_nm-vendor.outputTor)<1e-5);assert(own.voltage_v==vendor.vol&&own.sensor==vendor.sensor);
 printf("HOST_TEST PASS: %u synthetic commands vs unmodified Unitree C, CRC + feedback; within 1 LSB for float/double quantization (%u differing int16 fields). BENCH NOT_TESTED\n",packets,rounding_differences);
 return 0;
}
