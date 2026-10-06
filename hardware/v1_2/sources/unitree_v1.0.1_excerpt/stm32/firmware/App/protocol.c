#include "protocol.h"
#include "crc_ccitt.h"

#define SATURATE(_IN, _MIN, _MAX) \
	{                             \
		if ((_IN) < (_MIN))       \
			(_IN) = (_MIN);       \
		else if ((_IN) > (_MAX))  \
			(_IN) = (_MAX);       \
	}

/// @brief 将发送给电机的浮点参数(输出端数据)转换为定点类型参数
/// @param motor_s 要转换的电机指令结构体
void modify_data(MotorCmd_t *motor_s)
{
	motor_s->motor_send_data.head[0] = 0xFE;
	motor_s->motor_send_data.head[1] = 0xEE;

	SATURATE(motor_s->id, 0, 15);
	SATURATE(motor_s->mode, 0, 1);
	SATURATE(motor_s->timeout, 0, 1);
	SATURATE(motor_s->Kp, 0.0f, 2128.523254f);
	SATURATE(motor_s->Kd, 0.0f, 21.285233f);
	SATURATE(motor_s->outputTor, -36.9093f, 36.908174f);
	SATURATE(motor_s->outputSpd, -278.90143f, 278.90143f);
	SATURATE(motor_s->outputPos, -1428.018898f, 1428.018898f);

	motor_s->motor_send_data.mode.id = motor_s->id;
	motor_s->motor_send_data.mode.status = motor_s->mode;
	motor_s->motor_send_data.mode.timeout = motor_s->timeout;
	motor_s->motor_send_data.comd.k_pos = motor_s->Kp / (RATIO * RATIO) * 1280000.0f;
	motor_s->motor_send_data.comd.k_spd = motor_s->Kd / (RATIO * RATIO) * 128000000.0f;
	motor_s->motor_send_data.comd.pos_des = motor_s->outputPos * RATIO * 32768.0f / M_PI / 2.0f;
	motor_s->motor_send_data.comd.spd_des = motor_s->outputSpd * RATIO * 2.560f / M_PI / 2.0f;
	motor_s->motor_send_data.comd.tor_des = motor_s->outputTor / RATIO * 256000.0f;
	motor_s->motor_send_data.CRC32 = crc32_lookup_byte_by_byte((uint8_t *)&motor_s->motor_send_data, sizeof(motor_s->motor_send_data) - 4);
}

/// @brief 将接收到的定点类型原始数据转换为浮点参数类型(输出端数据)
/// @param motor_r 要转换的电机反馈结构体
void extract_data(MotorData_t *motor_r)
{
	if (motor_r->rxlen != (sizeof(motor_r->motor_recv_data) - 2))
	{
		motor_r->correct = 0;
		return;
	}

	if (motor_r->motor_recv_data.head[0] != 0xFC || motor_r->motor_recv_data.head[1] != 0xEE)
	{
		motor_r->correct = 0;
		return;
	}

	if (motor_r->motor_recv_data.CRC32 !=
		crc32_lookup_byte_by_byte((uint8_t *)&motor_r->motor_recv_data.mode, sizeof(motor_r->motor_recv_data) - 8))
	{
		motor_r->correct = 0;
		return;
	}
	else
	{
		motor_r->motor_id = motor_r->motor_recv_data.mode.id;
		motor_r->mode = motor_r->motor_recv_data.mode.status;
		motor_r->timeout = motor_r->motor_recv_data.mode.timeout;
		motor_r->Temp = motor_r->motor_recv_data.fbk.temp;
		motor_r->sensor = motor_r->motor_recv_data.fbk.sensor;
		motor_r->vol = (float)motor_r->motor_recv_data.fbk.vol / 2.0f;
		motor_r->MError = motor_r->motor_recv_data.fbk.MError;
		motor_r->MWarn = motor_r->motor_recv_data.fbk.ExFlag;
		motor_r->ExPos = 2 * M_PI * ((float)motor_r->motor_recv_data.fbk.OutPos) / 8192.0f;
		motor_r->outputSpd = ((float)motor_r->motor_recv_data.fbk.speed / 2.56f) * 2 * M_PI / RATIO;
		motor_r->outputTor = ((float)motor_r->motor_recv_data.fbk.torque) / 256000.0f * RATIO;
		motor_r->outputPos = 2 * M_PI * ((float)motor_r->motor_recv_data.fbk.pos) / 32768.0f / RATIO;
		motor_r->correct = 1;
		return;
	}
}
