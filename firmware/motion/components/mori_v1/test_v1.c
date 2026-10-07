#include "mori_v1.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void le(uint8_t*p,uint64_t n,unsigned count){for(unsigned i=0;i<count;i++)p[i]=n>>(i*8);}
static mori_v1_result_t command(mori_v1_t *v,unsigned kind,uint32_t seq,uint64_t id,uint64_t now,const uint8_t *args,unsigned n){
 uint8_t b[158]={0xa5,0x5a,2,kind};le(b+4,n+10,2);le(b+6,seq,4);le(b+10,v->session,8);le(b+18,id,8);le(b+26,now,8);le(b+34,300,2);if(n)memcpy(b+36,args,n);le(b+36+n,mori_crc32(b,36+n),4);
 bool complete=false;mori_v1_result_t result=V1_REJECTED;for(unsigned i=0;i<n+40;i++)result=mori_v1_feed(v,b[i],now,&complete);assert(complete);return result;
}
int main(void){mori_v1_t v;mori_v1_init(&v,123);uint8_t yes=1;assert(!v.core.out.enable&&!v.physical_contract_verified);
 assert(command(&v,MORI_CLAIM_CONTROL,1,1,1000,&yes,1)==V1_COMPLETED);assert(v.lease_end_ms==1300);
 assert(command(&v,MORI_CLAIM_CONTROL,1,1,1100,&yes,1)==V1_COMPLETED);assert(v.lease_end_ms==1300);
 assert(command(&v,MORI_ARM,2,2,1100,&yes,1)==V1_REJECTED);assert(!v.core.out.enable);
 v.core.state=MORI_BALANCE;v.core.v_target=.1f;assert(command(&v,MORI_STOP_MOTION,3,3,1100,NULL,0)==V1_COMPLETED);assert(v.core.state==MORI_BALANCE&&v.core.v_target==0);
 v.core.v_target=.1f;mori_v1_tick(&v,1300,NULL);assert(!v.claimed&&v.core.v_target==0&&v.core.state==MORI_BALANCE);
 assert(command(&v,MORI_FAULT_STOP,1,4,1310,NULL,0)==V1_FAULT);assert(v.core.state==MORI_FAULT&&!v.core.out.enable);
 mori_v1_init(&v,456);assert(v.session==456&&v.core.state==MORI_DISARMED);
 /* Host fixtures exercise state gates; they are not physical authorization. */
 v.physical_contract_verified=true;v.head[0].verified=v.head[1].verified=true;
 assert(command(&v,MORI_CLAIM_CONTROL,1,10,1000,&yes,1)==V1_COMPLETED);
 float targets[2]={.5f,.2f};
 assert(command(&v,MORI_HEAD_TARGET,2,11,1001,(const uint8_t*)targets,8)==V1_REJECTED);
 v.core.state=MORI_BALANCE;
 assert(command(&v,MORI_HEAD_TARGET,3,12,1002,(const uint8_t*)targets,8)==V1_RUNNING);
 mori_v1_tick(&v,1003,NULL);assert(v.head[0].position>0);
 assert(command(&v,MORI_DISARM,4,13,1004,&yes,1)==V1_COMPLETED);
 float stopped=v.head[0].position;mori_v1_tick(&v,1014,NULL);
 assert(v.core.state==MORI_DISARMED&&v.head[0].position==stopped&&v.head[0].target==stopped&&v.head[0].velocity==0);
 assert(command(&v,MORI_HEARTBEAT,5,14,1020,NULL,0)==V1_COMPLETED);
 uint64_t lease_end=v.lease_end_ms;
 assert(command(&v,MORI_READ_STATUS,6,15,1030,NULL,0)==V1_COMPLETED);
 assert(command(&v,MORI_HEARTBEAT,7,14,1040,NULL,0)==V1_COMPLETED);
 assert(v.lease_end_ms==lease_end); /* A B A with a new sequence must not renew. */
 mori_v1_init(&v,789);
 mori_axis_t *a=&v.head[1];assert(!mori_axis_target(a,NAN));assert(!mori_axis_target(a,.5));assert(mori_axis_target(a,.4));float last=0;
 for(int i=0;i<300;i++){mori_axis_step(a,.01f,false);assert(fabsf(a->position-last)<=.005201f);assert(a->position<=a->maximum);last=a->position;}
 assert(fabsf(a->position-.4f)<.001f);assert(a->target==.4f);mori_axis_step(a,.01f,true);assert(a->velocity==0);
 puts("PASS V1 boot/lease/duplicate/arm gate/STOP/fault/reset/two-axis bounds and rate properties; HOST only");return 0;}
