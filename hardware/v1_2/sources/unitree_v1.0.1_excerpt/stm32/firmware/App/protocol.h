/**
 * @file protocol.h
 * @brief J288/S288电机驱动 通讯协议&数据包
 * @version 0.1
 * @date 2026-01-28
 *
 */

#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include <stdint.h>
#include "gpio.h"

#pragma pack(1)
/**
 * @brief 电机模式控制信息
 *
 */
typedef struct
{
    uint8_t id : 4;      // 电机ID: 0,1...,13,14 15表示向所有电机广播数据(此时无返回)
    uint8_t status : 3;  // 工作模式: 0.锁定 1.FOC闭环 2.编码器校准 3.保留
    uint8_t timeout : 1; // Master->Motor: 0.禁用超时保护 1.开启 （默认1s超时） Motor->Master: 0.没有超时 1.触发超时保护(需要控制位发0清除)
} RIS_Mode_t;            // 控制模式 1Byte

/**
 * @brief 电机状态控制信息
 *
 */
typedef struct
{
    int16_t tor_des; // 电机转子端扭矩 unit: N.m
    int16_t spd_des; // 电机转子端速度 unit: rad/s
    int32_t pos_des; // 电机转子端位置 unit: rad
    int16_t k_pos;   // 电机转子端刚度系数
    int16_t k_spd;   // 电机转子端阻尼系数

} RIS_Comd_t; // 控制参数 12Byte

/**
 * @brief 电机状态反馈信息
 *
 */
typedef struct
{
    int8_t temp;          // 壳体温度: -128~127°C
    uint8_t sensor;       // 绕组温度: 0-255°C
    uint8_t vol;          // 电机端电压 0-127.5V 255表示127.5V
    int16_t torque;       // 电机转子端扭矩 unit: N.m
    int16_t speed;        // 电机转子端速度 unit: rad/s
    int32_t pos;          // 电机转子端位置 unit: rad
    uint32_t MError;      // 电机错误标识
    uint16_t OutPos : 13; // 扩展传感器数据（输出端位置）
    uint16_t ExFlag : 3;  // 扩展标志位（警告码）
    uint8_t ExSensor2;    // 保留位
    uint8_t ExCom;        // 扩展通信位
} RIS_Fbk_t;              // 状态数据 19Byte

/**
 * @brief 控制数据包格式
 *
 */
typedef struct
{
    uint8_t head[2]; // 包头 参与CRC校验 2Byte
    RIS_Mode_t mode; // 电机控制模式  1Byte
    uint8_t res;     // 保留位  1Byte
    RIS_Comd_t comd; // 电机期望数据 12Byte
    uint32_t CRC32;  // CRC32          4Byte

} ControlData_t; // 主机控制命令     20Byte

/**
 * @brief 电机反馈数据包格式
 *
 */
typedef struct
{
    uint8_t NoUse[2]; // 通信中不存在，为了使结构体4字节对齐2Byte
    uint8_t head[2];  // 包头  不参与CRC校验 2Byte
    RIS_Mode_t mode;  // 电机控制模式  1Byte
    RIS_Fbk_t fbk;    // 电机反馈数据 19Byte
    uint32_t CRC32;   // CRC32          4Byte

} RecvData_t; // 电机返回数据     结构体大小28Byte，实际返回数据大小26Byte

#pragma pack()

/// @brief 电机指令结构体
typedef struct
{
    unsigned short id;      // 电机ID，15代表全部电机
    unsigned short mode;    // 0:空闲 1:FOC控制 2:电机标定
    unsigned short timeout; // Master->Motor: 0.禁用超时保护 1.开启 （默认1s超时）
    float outputTor;        // 电机输出端力矩(Nm)
    float outputSpd;        // 电机输出端速度(rad/s)
    float outputPos;        // 电机输出端位置(rad)
    float Kp;               // 输出端刚度系数(0-2128.523254)
    float Kd;               // 输出端阻尼系数(0-21.285233)

    ControlData_t motor_send_data; // 电机发送数据结构体

} MotorCmd_t;

/// @brief 电机反馈结构体
typedef struct
{
    uint16_t rxlen;         // 从串口接收到的字节长度
    unsigned char motor_id; // 电机ID
    unsigned char mode;     // 0:空闲 1:FOC控制 2:电机标定
    unsigned short timeout; // Motor->Master: 0.没有超时 1.触发超时保护(需要控制位发0清除)
    int8_t Temp;            // 壳体温度: -128~127°C
    uint8_t sensor;         // 绕组温度: 0-255°C
    float vol;              // 电机端电压 0-127.5V 255表示127.5V
    uint32_t MError;        // 错误码
    uint16_t MWarn;         // 警告码
    float ExPos;            // 输出端位置传感器(rad)
    float outputTor;        // 当前实际电机输出端力矩(Nm)
    float outputSpd;        // 当前实际电机输出端速度(rad/s)
    float outputPos;        // 当前电机输出端位置(rad)
    int correct;            // 接收数据是否完整(1完整，0不完整)

    RecvData_t motor_recv_data; // 电机接收数据结构体

} MotorData_t;

#define M_PI 3.14159265358979323846
#define RATIO (70070.0f / 243.0f) // 电机减速比

void modify_data(MotorCmd_t *motor_s);
void extract_data(MotorData_t *motor_r);

#endif
