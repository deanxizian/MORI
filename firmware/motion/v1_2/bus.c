#include "mori12.h"
bool mori_bus_start(mori_bus *b,uint64_t now,uint32_t timeout) {
 if(!b||b->phase!=BUS_IDLE||!timeout||UINT64_MAX-now<timeout)return false;
 b->phase=BUS_TX_DMA;b->tx_enable=true;b->deadline_us=now+timeout;return true;
}
void mori_bus_dma_done(mori_bus *b){if(b&&b->phase==BUS_TX_DMA)b->phase=BUS_WAIT_TC;}
void mori_bus_tc(mori_bus *b){if(b&&b->phase==BUS_WAIT_TC){b->tx_enable=false;b->phase=BUS_RX;}}
static void next(mori_bus *b){b->tx_enable=false;b->phase=BUS_IDLE;b->wheel^=1;}
bool mori_bus_reply(mori_bus *b,uint8_t wheel,uint64_t now){
 if(!b||b->phase!=BUS_RX||wheel!=b->wheel||now>=b->deadline_us)return false;
 b->feedback_us[wheel]=now;b->valid_frames[wheel]++;next(b);return true;
}
bool mori_bus_poll(mori_bus *b,uint64_t now){
 if(!b||b->phase==BUS_IDLE||now<b->deadline_us)return false;
 b->timeouts[b->wheel]++;next(b);return true;
}
bool mori_bus_fresh(const mori_bus *b,uint64_t now,uint32_t age,uint32_t skew){
 if(!b||!b->valid_frames[0]||!b->valid_frames[1])return false;
 uint64_t a=b->feedback_us[0],c=b->feedback_us[1];
 return now>=a&&now>=c&&now-a<=age&&now-c<=age&&(a>c?a-c:c-a)<=skew;
}
