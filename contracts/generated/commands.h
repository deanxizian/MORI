/* Generated from command_spec.json by generate.py; do not edit. */
#pragma once
#include <stdbool.h>
#include <math.h>
typedef enum {
 MORI_READ_STATUS=1,
 MORI_CLAIM_CONTROL=2,
 MORI_RELEASE_CONTROL=3,
 MORI_HEARTBEAT=4,
 MORI_ARM=5,
 MORI_STOP_MOTION=6,
 MORI_DISARM=7,
 MORI_FAULT_STOP=8,
 MORI_ACK_FAULT=9,
 MORI_ENTER_MAINTENANCE=10,
 MORI_MAINTENANCE_ACTION=11,
 MORI_SET_VELOCITY=12,
 MORI_MOVE_DISTANCE=13,
 MORI_TURN_ANGLE=14,
 MORI_HEAD_TARGET=15,
 MORI_SET_EXPRESSION=16,
 MORI_CAMERA_MODE=17,
 MORI_SNAPSHOT=18,
 MORI_SELECT_TARGET=19,
 MORI_FOLLOW=20,
 MORI_PATROL=21,
 MORI_ACTIVE_ACTION=22,
 MORI_CANCEL=23,
 MORI_MEMORY_QUERY=24,
 MORI_MEMORY_REMEMBER=25,
 MORI_MEMORY_CORRECT=26,
 MORI_MEMORY_DELETE=27,
 MORI_MEMORY_EXPORT=28,
 MORI_MEMORY_ENABLED=29,
 MORI_VOLUME=30,
 MORI_VOICE_SESSION=31,
 MORI_BUTTON=32,
 MORI_WAKE_CONFIG=33,
} mori_v1_kind_t;
static inline bool mori_v1_numeric_valid(unsigned kind,const float *p,unsigned n){
 switch(kind){
 case MORI_READ_STATUS:return n==0;
 case MORI_RELEASE_CONTROL:return n==0;
 case MORI_HEARTBEAT:return n==0;
 case MORI_STOP_MOTION:return n==0;
 case MORI_SET_VELOCITY:return n==2 && isfinite(p[0]) && p[0] >= -0.1f && p[0] <= 0.1f && isfinite(p[1]) && p[1] >= -0.5f && p[1] <= 0.5f;
 case MORI_MOVE_DISTANCE:return n==1 && isfinite(p[0]) && p[0] >= -0.3f && p[0] <= 0.3f;
 case MORI_TURN_ANGLE:return n==1 && isfinite(p[0]) && p[0] >= -3.14159265f && p[0] <= 3.14159265f;
 case MORI_HEAD_TARGET:return n==2 && isfinite(p[0]) && p[0] >= -1.04719755f && p[0] <= 1.04719755f && isfinite(p[1]) && p[1] >= -0.34906585f && p[1] <= 0.436332313f;
 case MORI_MEMORY_EXPORT:return n==0;
 case MORI_VOLUME:return n==1 && isfinite(p[0]) && p[0] >= 0.0f && p[0] <= 1.0f;
 default:return false;
 }
}
