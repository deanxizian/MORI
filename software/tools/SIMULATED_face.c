#include "mori_ui.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv){
 if(argc!=3)return 2;char *end;long width=strtol(argv[1],&end,10);if(*end||width<16||width>1024)return 2;
 FILE *f=fopen(argv[2],"wb");if(!f)return 1;fprintf(f,"P6\n# SIMULATED face renderer, not final panel geometry\n%ld %ld\n255\n",width,width);
 for(unsigned y=0;y<(unsigned)width;y++)for(unsigned x=0;x<(unsigned)width;x++){
  unsigned c=mori_face_pixel(width,width,x,y,false,false);unsigned char rgb[3]={((c>>11)&31)*255/31,((c>>5)&63)*255/63,(c&31)*255/31};
  if(fwrite(rgb,1,3,f)!=3)return 1;
 }
 return fclose(f)?1:0;
}
