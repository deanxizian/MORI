#pragma once
#include "mori_core.h"
#include <stddef.h>
#define MORI_PROTOCOL "MORI/1"
#define MORI_LINE_MAX 119
#define MORI_LINE_TIMEOUT_US 250000

typedef enum { MP_CORE, MP_HEAD, MP_INFO, MP_STATUS } mori_request_kind_t;
typedef struct { uint32_t id; mori_request_kind_t kind; mori_command_t command; float angle; } mori_request_t;
typedef enum { MR_OK, MR_SYNTAX, MR_RANGE, MR_NONFINITE, MR_OVERFLOW, MR_TRUNCATED, MR_QUEUE, MR_STATE, MR_GATE, MR_FAULT, MR_CONFIG } mori_reason_t;
const char *mori_reason_name(mori_reason_t reason);
mori_reason_t mori_parse(const char *line,mori_request_t *request);
typedef struct { char bytes[MORI_LINE_MAX+1]; size_t used; bool discard,reported; uint64_t started_us; mori_reason_t error; } mori_line_t;
/* 0=waiting, 1=complete; error is reported once at newline/timeout, never parses a suffix. */
int mori_line_feed(mori_line_t *line,uint8_t byte,uint64_t now,mori_request_t *request,mori_reason_t *reason);
int mori_line_expire(mori_line_t *line,uint64_t now,mori_reason_t *reason);
