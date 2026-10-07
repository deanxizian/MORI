#include "wire.h"
uint32_t mori_crc32(const uint8_t *p,size_t n){uint32_t crc=~0u;for(size_t i=0;i<n;i++){crc^=p[i];for(int k=0;k<8;k++)crc=(crc>>1)^((0u-(crc&1))&0xedb88320u);}return ~crc;}
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
bool mori_wire_feed(mori_wire_t *d,uint8_t b,uint64_t now){
 if(d->used && now-d->started_ms>50){d->used=0;d->dropped++;}
 if(!d->used){if(b!=0xa5){d->dropped++;return false;}d->started_ms=now;}
 else if(d->used==1&&b!=0x5a){d->used=b==0xa5?1:0;d->dropped++;return false;}
 d->bytes[d->used++]=b;
 if(d->used<26)return false;
 unsigned n=d->bytes[4]|d->bytes[5]<<8;bool session=false,command=false;
 for(int i=10;i<18;i++)session|=d->bytes[i]!=0;
 for(int i=18;i<26;i++)command|=d->bytes[i]!=0;
 if(d->bytes[2]!=2||n>128||!d->bytes[3]||!le32(d->bytes+6)||le32(d->bytes+6)>0x7fffffffu||!session||!command){d->used=0;d->dropped++;return false;}
 if(d->used==n+30){d->used=0;if(mori_crc32(d->bytes,n+26)==le32(d->bytes+n+26))return true;d->dropped++;}
 return false;
}
