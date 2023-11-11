#!/usr/bin/env python

'''
 Authorization tags each have an associated type.  This enumeration facilitates tagging each with
 a type, by using the high four bits (of an implied 32-bit unsigned enum value) to specify up to
 16 data types.  These values are ORed with tag IDs to generate the final tag ID values.
'''
# keymaster_tag_type_t
KM_INVALID = 0 << 28
KM_ENUM = 1 << 28
KM_ENUM_REP = 2 << 28
KM_UINT = 3 << 28
KM_UINT_REP = 4 << 28
KM_ULONG = 5 << 28
KM_DATE = 6 << 28
KM_BOOL = 7 << 28
KM_BIGNUM = 8 << 28
KM_BYTES = 9 << 28
KM_ULONG_REP = 10 << 28

# keymaster_tag_t
KM_TAG_INVALID = KM_INVALID | 0
'''
 Tags that must be semantically enforced by hardware and software implementations.
'''
# /* Crypto parameters */
KM_TAG_PURPOSE = KM_ENUM_REP | 1
KM_TAG_ALGORITHM = KM_ENUM | 2
KM_TAG_KEY_SIZE = KM_UINT | 3
KM_TAG_BLOCK_MODE = KM_ENUM_REP | 4
KM_TAG_DIGEST = KM_ENUM_REP | 5
KM_TAG_PADDING = KM_ENUM_REP | 6
KM_TAG_CALLER_NONCE = KM_BOOL | 7
KM_TAG_MIN_MAC_LENGTH = KM_UINT | 8
KM_TAG_KDF = KM_ENUM_REP | 9
KM_TAG_EC_CURVE = KM_ENUM | 10
# /* Algorithm-specific. */
KM_TAG_RSA_PUBLIC_EXPONENT = KM_ULONG | 200
KM_TAG_ECIES_SINGLE_HASH_MODE = KM_BOOL | 201
KM_TAG_INCLUDE_UNIQUE_ID = KM_BOOL | 202 
# /* Other hardware-enforced. */
KM_TAG_BLOB_USAGE_REQUIREMENTS = KM_ENUM | 301
KM_TAG_BOOTLOADER_ONLY = KM_BOOL | 302
'''
* Tags that should be semantically enforced by hardware if possible and will otherwise be
* enforced by software (keystore).
'''
#/* Key validity period */
KM_TAG_ACTIVE_DATETIME = KM_DATE | 400
KM_TAG_ORIGINATION_EXPIRE_DATETIME = KM_DATE | 401
KM_TAG_USAGE_EXPIRE_DATETIME = KM_DATE | 402
KM_TAG_MIN_SECONDS_BETWEEN_OPS = KM_UINT | 403
KM_TAG_MAX_USES_PER_BOOT = KM_UINT | 404
# /* User authentication */
KM_TAG_ALL_USERS = KM_BOOL | 500
KM_TAG_USER_ID = KM_UINT | 501
KM_TAG_USER_SECURE_ID = KM_ULONG_REP | 502
KM_TAG_NO_AUTH_REQUIRED = KM_BOOL | 503
KM_TAG_USER_AUTH_TYPE = KM_ENUM | 504
KM_TAG_AUTH_TIMEOUT = KM_UINT | 505
KM_TAG_ALLOW_WHILE_ON_BODY = KM_BOOL | 506
# /* Application access control */
KM_TAG_ALL_APPLICATIONS = KM_BOOL | 600
KM_TAG_APPLICATION_ID = KM_BYTES | 601
KM_TAG_EXPORTABLE = KM_BOOL | 602
'''
* Semantically unenforceable tags, either because they have no specific meaning or because
* they're informational only.
'''
KM_TAG_APPLICATION_DATA = KM_BYTES | 700
KM_TAG_CREATION_DATETIME = KM_DATE | 701
KM_TAG_ORIGIN = KM_ENUM | 702
KM_TAG_ROLLBACK_RESISTANT = KM_BOOL | 703
KM_TAG_ROOT_OF_TRUST = KM_BYTES | 704
KM_TAG_OS_VERSION = KM_UINT | 705
KM_TAG_OS_PATCHLEVEL = KM_UINT | 706
KM_TAG_UNIQUE_ID = KM_BYTES | 707
KM_TAG_ATTESTATION_CHALLENGE = KM_BYTES | 708
KM_TAG_ATTESTATION_APPLICATION_ID = KM_BYTES | 709
KM_TAG_ATTESTATION_ID_BRAND = KM_BYTES | 710
KM_TAG_ATTESTATION_ID_DEVICE = KM_BYTES | 711
KM_TAG_ATTESTATION_ID_PRODUCT = KM_BYTES | 712
KM_TAG_ATTESTATION_ID_SERIAL = KM_BYTES | 713
KM_TAG_ATTESTATION_ID_IMEI = KM_BYTES | 714
KM_TAG_ATTESTATION_ID_MEID = KM_BYTES | 715
KM_TAG_ATTESTATION_ID_MANUFACTURER = KM_BYTES | 716
KM_TAG_ATTESTATION_ID_MODEL = KM_BYTES | 717
# /* Tags used only to provide data to or receive data from operations */
KM_TAG_ASSOCIATED_DATA = KM_BYTES | 1000
KM_TAG_NONCE = KM_BYTES | 1001
KM_TAG_AUTH_TOKEN = KM_BYTES | 1002
KM_TAG_MAC_LENGTH = KM_UINT | 1003
KM_TAG_RESET_SINCE_ID_ROTATION = KM_BOOL | 1004


'''
 * Algorithms that may be provided by keymaster implementations.  Those that must be provided by all
 * implementations are tagged as "required".
'''
# keymaster_algorithm_t
# /* Asymmetric algorithms. */
KM_ALGORITHM_RSA = 1
#// KM_ALGORITHM_DSA = 2, -- Removed, do not re-use value 2.
KM_ALGORITHM_EC = 3
#/* Block ciphers algorithms */
KM_ALGORITHM_AES = 32
#/* MAC algorithms */
KM_ALGORITHM_HMAC = 128


'''
 * Symmetric block cipher modes provided by keymaster implementations.
'''
# keymaster_block_mode_t
KM_MODE_ECB = 1
KM_MODE_CBC = 2
KM_MODE_CTR = 3
KM_MODE_GCM = 32

# keymaster_padding_t
KM_PAD_NONE = 1
KM_PAD_RSA_OAEP = 2
KM_PAD_RSA_PSS = 3
KM_PAD_RSA_PKCS1_1_5_ENCRYPT = 4
KM_PAD_RSA_PKCS1_1_5_SIGN = 5
KM_PAD_PKCS7 = 64


# keymaster_digest_t
KM_DIGEST_NONE = 0
KM_DIGEST_MD5 = 1
KM_DIGEST_SHA1 = 2
KM_DIGEST_SHA_2_224 = 3
KM_DIGEST_SHA_2_256 = 4
KM_DIGEST_SHA_2_384 = 5
KM_DIGEST_SHA_2_512 = 6

# keymaster_kdf_t
KM_KDF_NONE = 0,
KM_KDF_RFC5869_SHA256 = 1,
KM_KDF_ISO18033_2_KDF1_SHA1 = 2,
KM_KDF_ISO18033_2_KDF1_SHA256 = 3,
KM_KDF_ISO18033_2_KDF2_SHA1 = 4,
KM_KDF_ISO18033_2_KDF2_SHA256 = 5,

# keymaster_ec_curve_t
KM_EC_CURVE_P_224 = 0
KM_EC_CURVE_P_256 = 1
KM_EC_CURVE_P_384 = 2
KM_EC_CURVE_P_521 = 3

# keymaster_key_origin_t
KM_ORIGIN_GENERATED = 0
KM_ORIGIN_DERIVED = 1
KM_ORIGIN_IMPORTED = 2
KM_ORIGIN_UNKNOWN = 3


# keymaster_purpose_t
KM_PURPOSE_ENCRYPT = 0
KM_PURPOSE_DECRYPT = 1
KM_PURPOSE_SIGN = 2
KM_PURPOSE_VERIFY = 3
KM_PURPOSE_DERIVE_KEY = 4

'''
typedef struct {
    keymaster_tag_t tag;
    union {
        uint32_t enumerated;   /* KM_ENUM and KM_ENUM_REP */
        bool boolean;          /* KM_BOOL */
        uint32_t integer;      /* KM_INT and KM_INT_REP */
        uint64_t long_integer; /* KM_LONG */
        uint64_t date_time;    /* KM_DATE */
        keymaster_blob_t blob; /* KM_BIGNUM and KM_BYTES*/
    };
} keymaster_key_param_t;
'''
