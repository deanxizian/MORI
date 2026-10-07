#include "mori_protocol.h"
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
const char *mori_reason_name(mori_reason_t r){
 static const char *names[]={"OK","SYNTAX","RANGE","NONFINITE","OVERFLOW","TRUNCATED","QUEUE_FULL","STATE","GATE","FAULT","CONFIG"};
 return r>=MR_OK&&r<=MR_CONFIG?names[r]:"INVALID";
}
static bool decimal(const char *s){
 if(*s=='+'||*s=='-')s++;
 unsigned digits=0;while(*s>='0'&&*s<='9'){digits++;s++;}
 if(*s=='.'){s++;while(*s>='0'&&*s<='9'){digits++;s++;}}
 if(!digits)return false;
 if(*s=='e'||*s=='E'){s++;if(*s=='+'||*s=='-')s++;unsigned n=0;while(*s>='0'&&*s<='9'){n++;s++;}if(!n)return false;}
 return *s==0;
}
mori_reason_t mori_parse(const char *line,mori_request_t *r){
 memset(r,0,sizeof(*r));size_t n=strlen(line);if(n>MORI_LINE_MAX)return MR_OVERFLOW;
 char copy[MORI_LINE_MAX+1];memcpy(copy,line,n+1);char *tokens[7];unsigned count=0;char *p=copy;
 while(*p){
  while(*p==' '){p++;}
  if(!*p)break;
  if(count==7)return MR_SYNTAX;
  tokens[count++]=p;
  while(*p&&*p!=' '){if((unsigned char)*p<33||(unsigned char)*p>126)return MR_SYNTAX;p++;}
  if(*p)*p++=0;
 }
 if(!count)return MR_SYNTAX;
 unsigned off=0;
 if(tokens[0][0]=='@'){
  const char *q=tokens[0]+1;if(!*q)return MR_SYNTAX;uint64_t id=0;
  for(;*q;q++){if(*q<'0'||*q>'9')return MR_SYNTAX;id=id*10+(unsigned)(*q-'0');if(id>UINT32_MAX)return MR_OVERFLOW;}
  if(id==0)return MR_RANGE;
  r->id=(uint32_t)id;off=1;if(count==1)return MR_SYNTAX;
 }
 char **t=tokens+off;unsigned num=count-off,arity=0;float lo[4]={0},hi[4]={0};
 r->kind=MP_CORE;
 if(!strcmp(t[0],"info"))r->kind=MP_INFO;
 else if(!strcmp(t[0],"status"))r->kind=MP_STATUS;
 else if(!strcmp(t[0],"calibrate"))r->command.type=MC_CALIBRATE;
 else if(!strcmp(t[0],"ack"))r->command.type=MC_ACK;
 else if(!strcmp(t[0],"confirm_signs"))r->command.type=MC_CONFIRM_SIGNS;
 else if(!strcmp(t[0],"stop"))r->command.type=MC_STOP;
 else if(!strcmp(t[0],"disarm"))r->command.type=MC_DISARM;
 else if(!strcmp(t[0],"arm")){
  if(num!=2)return MR_SYNTAX;
  if(!strcmp(t[1],"bench"))r->command.type=MC_ARM_BENCH;
  else if(!strcmp(t[1],"balance"))r->command.type=MC_ARM_BALANCE;else return MR_SYNTAX;
  return MR_OK;
 }else if(!strcmp(t[0],"duty")){r->command.type=MC_BENCH_DUTY;arity=2;lo[0]=lo[1]=-.12f;hi[0]=hi[1]=.12f;}
 else if(!strcmp(t[0],"move")){r->command.type=MC_MOVE;arity=2;lo[0]=-.3f;hi[0]=.3f;lo[1]=-.10f;hi[1]=.10f;}
 else if(!strcmp(t[0],"gains")){r->command.type=MC_GAINS;arity=4;hi[0]=10;hi[1]=2;hi[2]=1;hi[3]=.2f;}
 else if(!strcmp(t[0],"head")){r->kind=MP_HEAD;arity=1;lo[0]=-50;hi[0]=50;}
 else return MR_SYNTAX;
 if(num!=arity+1)return MR_SYNTAX;
 float values[4]={0};
 for(unsigned i=0;i<arity;i++){
  char *end;errno=0;float v=strtof(t[i+1],&end);
  if(!isfinite(v))return MR_NONFINITE;
  if(errno==ERANGE)return MR_OVERFLOW;
  if(*end||!decimal(t[i+1]))return MR_SYNTAX;
  if(v<lo[i]||v>hi[i])return MR_RANGE;
  values[i]=v;
 }
 if(r->kind==MP_HEAD)r->angle=values[0];
 else{r->command.a=values[0];r->command.b=values[1];r->command.c=values[2];r->command.d=values[3];}
 if(r->kind==MP_CORE&&r->command.type==MC_GAINS&&(values[0]<=0||values[1]<=0))return MR_RANGE;
 return MR_OK;
}
int mori_line_feed(mori_line_t *l,uint8_t byte,uint64_t now,mori_request_t *r,mori_reason_t *why){
 memset(r,0,sizeof(*r));
 if(byte=='\n'||byte=='\r'){
  if(!l->used&&!l->discard)return 0;
  if(l->reported){memset(l,0,sizeof(*l));return 0;}
  if(l->discard)*why=l->error;else{l->bytes[l->used]=0;*why=mori_parse(l->bytes,r);}
  memset(l,0,sizeof(*l));return 1;
 }
 if(!l->used&&!l->discard)l->started_us=now;
 if(l->discard)return 0;
 if(byte<32||byte>126){l->discard=true;l->error=MR_SYNTAX;return 0;}
 if(l->used==MORI_LINE_MAX){l->discard=true;l->error=MR_OVERFLOW;return 0;}
 l->bytes[l->used++]=(char)byte;return 0;
}
int mori_line_expire(mori_line_t *l,uint64_t now,mori_reason_t *why){
 if((l->used||l->discard)&&now>=l->started_us&&now-l->started_us>MORI_LINE_TIMEOUT_US){
  /* Keep draining until terminator: a late suffix cannot become a new command. */
  if(l->discard&&l->error==MR_TRUNCATED)return 0;
  l->discard=true;l->error=MR_TRUNCATED;l->reported=true;*why=MR_TRUNCATED;return 1;
 }
 return 0;
}
