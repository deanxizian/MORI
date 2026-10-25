#include "stm32f4xx_hal.h"
#include "mori12.h"
/* Compile/bench bring-up image. No board has a signed pin/clock/power contract.
 * Therefore no GPIO, UART, SPI, head or wheel rail is initialized here. External
 * inhibit must be held by hardware at reset, not by an invented software pin.
 * Debugger-visible status is NOT sensor evidence or an automatic ARM path. */
volatile unsigned mori_board_contract_missing=1;
mori_motion motion;
int main(void){
 HAL_Init(); /* vendor reset HSI = 16 MHz; deliberately insufficient for 6 Mbps */
 mori_motion_init(&motion);
 for(;;){__WFI();}
}
void SysTick_Handler(void){HAL_IncTick();}
void _init(void){}
void _fini(void){}
void HardFault_Handler(void){mori_motion_fault(&motion,F_CONTROL_TIMEOUT);for(;;){__WFI();}}
