#pragma once
#include <stdbool.h>
#include <stdint.h>
/* Single control-task owner; ISR only latches a timestamp for that task.
 * Mark from a board monotonic us clock. No RT allocation, I/O or printing.
 * Device/filter group delay and physical output onset require separate capture. */
enum mori_timing_stage {T_DRDY,T_WAKE,T_SPI_DONE,T_FUSION_DONE,T_CONTROL_DONE,T_WHEEL_TC,T_STAGES};
typedef struct {
 uint64_t stamp[T_STAGES]; uint32_t max_us[T_STAGES-1],last_us[T_STAGES-1];
 uint32_t histogram[T_STAGES-1][32],frames,invalid_frames,dropped_log_frames;
 uint32_t execution_max_us,period_max_us; uint64_t previous_drdy;
 unsigned next; bool valid,have_previous;
} mori_timing;
bool mori_timing_mark(mori_timing *timing,enum mori_timing_stage stage,uint64_t now_us);
