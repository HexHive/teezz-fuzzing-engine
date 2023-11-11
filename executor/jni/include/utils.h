#ifndef _UTILS_H_
#define _UTILS_H_

#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>

#define MEMBER_SIZE(type, member) sizeof(((type *)0)->member)

extern uint32_t ZERO;

typedef struct __attribute__((__packed__)) type_length {
    char type;
    uint32_t length;
} type_length_t;



typedef struct data_stream {
    char* data;
    uint32_t sz;
    uint32_t pos;
} data_stream_t;

/* Receive type-length-value data from `sock`.
 *
 * \param sock socket we receive data from
 * \param tlv_type type of message
 * \param tlv_sz size of message
 * \param tlv_buf content of message
 * \param return 0 on success, -1 on error
 */
int recv_tlv(const int sock, char *tlv_type, uint32_t *tlv_sz, char **tlv_buf);

/* Returns a pointer to a freshly created `data_stream_t` with a size of `sz`.
 *
 * \param sz the size of the ds' buffer
 * \param return pointer to the ds
*/
data_stream_t *ds_init(uint32_t sz);
data_stream_t *ds_init_from_buf(char* buf, uint32_t sz);

/* Reset the data. Sets position to zero and zeroes the buffer */
void ds_reset(data_stream_t *ds); 

/* Free the dynamically allocated memory occupied by `ds` */
void ds_deinit(data_stream_t *ds);

/* Return a pointer to the current position of data stream `ds` and advance
 * its position by `n`.
 *
 * \param ds data stream to be read from
 * \param n number of bytes requested
 * \param return pointer to the current position of data stream `ds` or NULL on
 * error.
*/
char* ds_read(data_stream_t *ds, uint32_t n);

/* Appends `n` bytes of `buf` to `ds`.
 *
 * \param ds data stream to be appended to
 * \param buf buffer to be copied from
 * \param n number of bytes to be copied
 * \param return pointer to the position where data has been inserted or NULL on
 * error.
*/
char* ds_write(data_stream_t *ds, char* buf, uint32_t n);

ssize_t recv_item_by_name_exact(data_stream_t *ds, char *exp_item_name, char *item, size_t exp_item_sz);
ssize_t recv_item_by_name(data_stream_t *ds, char *exp_item_name, char *item, size_t exp_item_sz);

ssize_t send_len_val(int sock, char *buf, size_t sz);
ssize_t send_buf(int sock, char *buf, size_t sz);

ssize_t parse_lv(data_stream_t *ds, char **val);
int recv_buf(int sock, char *buf, size_t sz);

/* Same as read_data, but with "enhanced" logging
 * \see read_data
 *
 * \param message printed in debug log
 */
ssize_t read_data_log(const char *message, int sock, char **buf);

/* Same as write_data, but with "enhanced" logging
 * \see write_data
 *
 * \param message printed in debug log
 */
ssize_t write_data_log(const char *message, int sock, char *buf, size_t sz);

/* Reads hex encoded data from socket sock and decodes it.
 * A chunk is allocated for the decoded data and its address stored in buf.
 * The size of the allocated memory is stored in sz.
 * buf[0] must be freed by the caller.
 *
 * On error no buffer is allocated.
 *
 * \param sock from this socket the data is read
 * \param buf must point to writable memory. In buf[0] the address of the
 * allocated memory is stored. buf[0] must be freed by the caller
 * \param return size of the allocated buffer pointed to by buf[0], -1 on error
 *
 * \opt remove last argument
 */
ssize_t read_data(int sock, char **buf);

/* Writes sz bytes from buf to socket sock. Output is hex-encoded.
 *
 * \param sock output goes to this socket
 * \param buf contains the data which will be written to sock
 * \param sz size of buf
 * \param return number of bytes written, -1 on error
 */
ssize_t write_data(int sock, char *buf, size_t sz);

#endif //_UTILS_H_
