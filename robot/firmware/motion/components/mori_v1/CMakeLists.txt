get_filename_component(MORI_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../.." ABSOLUTE)
idf_component_register(SRCS "mori_v1.c" "${MORI_ROOT}/contracts/wire.c" INCLUDE_DIRS "include" "${MORI_ROOT}/contracts" "${MORI_ROOT}/contracts/generated" REQUIRES mori_core)
