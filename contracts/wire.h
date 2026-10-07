#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define MORI_WIRE_MAX 158
/* Little endian 26-byte header + <=128 payload + CRC32. Feed one byte at a time. */
typedef struct {uint8_t bytes[MORI_WIRE_MAX];size_t used;uint64_t started_ms;uint32_t dropped;} mori_wire_t;
uint32_t mori_crc32(const uint8_t *p,size_t n);
bool mori_wire_feed(mori_wire_t *d,uint8_t b,uint64_t now_ms);
