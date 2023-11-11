/**
 * @file tee_client_type.h
 *
 * Copyright(C), 2008-2013, Huawei Tech. Co., Ltd. ALL RIGHTS RESERVED. \n
 *
 * 描述：定义基本数据类型和数据结构\n
 */

/**
 * @ingroup TEEC_COMMON_DATA
 * 无符号整型定义
 */
typedef unsigned int uint32_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 有符号整型定义
 */
typedef signed int int32_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 无符号短整型定义
 */
typedef unsigned short uint16_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 有符号短整型定义
 */
typedef signed short int16_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 无符号字符型定义
 */
typedef unsigned char uint8_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 有符号字符型定义
 */
typedef signed char int8_t;
/**
 * @ingroup TEEC_COMMON_DATA
 * 布尔类型定义
 */
#ifndef bool
#define bool uint8_t
#endif

/**
 * @ingroup TEEC_COMMON_DATA
 * true值的定义
 */
#ifndef true
#define true 1
#endif

/**
 * @ingroup TEEC_COMMON_DATA
 * false值的定义
 */
#ifndef false
#define false 0
#endif

/**
 * @ingroup TEEC_COMMON_DATA
 * NULL值的定义
 */
#ifndef NULL
#define NULL 0
#endif

/**
 * @ingroup TEEC_COMMON_DATA
 * 函数返回值类型定义
 *
 * 用于表示函数返回结果
 */
//typedef uint32_t TEEC_Result;

/**
 * @ingroup TEEC_COMMON_DATA
 * UUID类型定义
 *
 * UUID类型遵循RFC4122 [2]，用于标识安全服务
 */

// typedef struct {
//     uint32_t timeLow;          /**< 时间戳的低4字节  */
//     uint16_t timeMid;          /**< 时间戳的中2字节  */
//     uint16_t timeHiAndVersion; /**< 时间戳的高2字节与版本号的组合  */
//     uint8_t clockSeqAndNode[8]; /**< 时钟序列与节点标识符的组合  */
// } TEEC_UUID;

