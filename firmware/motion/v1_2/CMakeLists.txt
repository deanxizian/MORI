set(REFS "${CMAKE_CURRENT_LIST_DIR}/../../../refs/v1_2")
set(CMSIS "${REFS}/cmsis-device-f4")
set(HAL "${REFS}/stm32f4xx-hal-driver")
set(MORI12 "${CMAKE_CURRENT_LIST_DIR}")
option(MORI_POWER_STAGE_VERIFIED "Bench-qualified V1.2 power stage" OFF)
option(MORI_BALANCE_ENABLED "Bench-qualified V1.2 balancing" OFF)
if(MORI_POWER_STAGE_VERIFIED OR MORI_BALANCE_ENABLED)
 message(FATAL_ERROR "V1.2 physical release BLOCKED: signed GPIO/clock/power/calibration port required. Do not bypass this gate.")
endif()
add_executable(mori_motion.elf
 ${MORI12}/stm32/main.c ${MORI12}/s288.c ${MORI12}/bus.c ${MORI12}/sensors.c ${MORI12}/motion.c ${MORI12}/timing.c
 ${CMSIS}/Source/Templates/gcc/startup_stm32f413xx.s
 ${CMSIS}/Source/Templates/system_stm32f4xx.c
 ${HAL}/Src/stm32f4xx_hal.c ${HAL}/Src/stm32f4xx_hal_cortex.c
 ${HAL}/Src/stm32f4xx_hal_rcc.c ${HAL}/Src/stm32f4xx_hal_rcc_ex.c
 ${HAL}/Src/stm32f4xx_hal_gpio.c ${HAL}/Src/stm32f4xx_hal_dma.c
 ${HAL}/Src/stm32f4xx_hal_uart.c ${HAL}/Src/stm32f4xx_hal_spi.c
 ${MORI12}/../../../contracts/wire.c)
target_include_directories(mori_motion.elf PRIVATE ${MORI12}/include ${MORI12}/stm32 ${CMSIS}/Include ${HAL}/Inc ${REFS}/CMSIS_5/CMSIS/Core/Include ${MORI12}/../../../contracts)
target_compile_definitions(mori_motion.elf PRIVATE STM32F413xx USE_HAL_DRIVER)
target_compile_options(mori_motion.elf PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra)
target_link_options(mori_motion.elf PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -nostartfiles --specs=nano.specs --specs=nosys.specs "-T${MORI12}/stm32/STM32F413RG.ld" -Wl,--gc-sections -Wl,-Map=mori_motion.map -Wl,--print-memory-usage)
target_link_libraries(mori_motion.elf PRIVATE m)
add_custom_command(TARGET mori_motion.elf POST_BUILD COMMAND arm-none-eabi-objcopy -O binary $<TARGET_FILE:mori_motion.elf> mori_motion.bin COMMAND arm-none-eabi-size $<TARGET_FILE:mori_motion.elf>)
