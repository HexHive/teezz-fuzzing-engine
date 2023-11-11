#include <utils.h>
#include <logging.h>
#include <tc/tc.h>
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>

uint32_t ZERO = 0;

data_stream_t *ds_init(uint32_t sz) {
    data_stream_t *ds = NULL;
    ds = calloc(1, sizeof(data_stream_t));
    if (ds == NULL)
        return NULL;
    ds->sz = sz;
    ds->data = calloc(1, sz);
    if (ds->data == NULL) {
        free(ds);
        return NULL;
    }
    return ds;
}

data_stream_t *ds_init_from_buf(char* buf, uint32_t sz) {
    data_stream_t *ds = NULL;
    ds = calloc(1, sizeof(data_stream_t));
    if (ds == NULL)
        return NULL;
    ds->sz = sz;
    ds->data = buf;
    return ds;
}

void ds_deinit(data_stream_t *ds) {
    if (ds->data)
        free(ds->data);
    free(ds);
}

void ds_reset(data_stream_t *ds) {
    bzero(ds->data, ds->sz);
    ds->pos = 0;
}

char* ds_read(data_stream_t *ds, uint32_t n) {
    char* ret = NULL;
    if ((ds->pos + n) <= ds->sz) {
        ret = &ds->data[ds->pos];
        ds->pos += n;
    } else {
        LOGE("%d > %d", (ds->pos + n), ds->sz);
    }
    return ret;
}

char* ds_write(data_stream_t *ds, char* buf, uint32_t n) {
    char* ret = NULL;
    if ((ds->pos + n) > ds->sz) {
        // allocate more space if data does not fit
        ds->data = realloc(ds->data, ds->sz+n);
        if (!ds->data) {
            LOGE("realloc: %s", strerror(errno));
            goto err;
        }
        ds->sz += n;
    }

    //hexdump("ds_write: ", buf, n);

    memcpy(&ds->data[ds->pos], buf, n);
    ret = &ds->data[ds->pos];
    ds->pos += n;
    return ret;
err:
    return NULL;
}

/* Read exactly sz bytes from `sock` and store it in `buf`.
 *
 * \param `sock` socket to recv data from
 * \param `buf` data is stored in this buffer
 * \param `sz` size of buf
 * \param return 0 on success, -1 on error
 */
int recv_buf(int sock, char *buf, size_t sz) {
    int ret = 0;
    int idx = 0;
    ssize_t nread = 0;

    while (1) {
        nread = recv(sock, &buf[idx], sz - idx, 0);

        if (nread == -1) {
            LOGE("recv: %s", strerror(errno));
            ret = -1;
            break;
        }

        idx += nread;
        if (idx == sz) {
            break;
        } else if (nread == 0) {
            LOGE("EOF");
            ret = -1;
            break;
        }
    }

    return ret;
}

/* Writes sz bytes from buf to socket sock.
 *
 * \param sock output goes to this socket
 * \param buf contains the data which will be written to sock
 * \param sz size of buf
 * \param return number of bytes written, -1 on error */
ssize_t send_buf(int sock, char *buf, size_t sz) {
    size_t nwrite = 0;

    while (nwrite < sz) {
        if (write(sock, &buf[nwrite], 1) == -1) {
            perror("write");
            return -1;
        }
        nwrite++; 
    }
    return nwrite;
}


/* Receive length-value-encoded data from `ds` */
ssize_t parse_lv(data_stream_t *ds, char **val) {
    char *data_p = NULL;
    uint32_t sz = 0;

    // parse size
    data_p = ds_read(ds, sizeof(uint32_t));
    if (data_p == NULL) {
        LOGE("ds_read: error reading length");
        goto err;
    }
    sz = *(uint32_t*) data_p;

    // parse buffer
    data_p = ds_read(ds, sz);
    if (data_p == NULL) {
        LOGE("ds_read: error reading buffer of length %d", sz);
        goto err;
    }
    *val = data_p;
    return (ssize_t)sz;
err:
    return -1;
}

ssize_t send_len_val(int sock, char *buf, size_t sz) {
    size_t nwrite = 0;

    LOGD("Sending chunk of sz %zd", sz);
    if (send_buf(sock, (char*)&sz, sizeof(size_t)) != sizeof(size_t)) 
        goto err;
    if (send_buf(sock, buf, sz) != sz) 
        goto err;

    return sz;
err:
    return -1;
}

int recv_tlv(const int sock, char *tlv_type, uint32_t *tlv_sz, char **tlv_buf) {
        int ret = 0;

        type_length_t tl = { 0 };
        ret = recv_buf(sock, (char*) &tl, sizeof(type_length_t));
        if (!ret) {
            *tlv_type = tl.type;
            *tlv_sz = tl.length;
            *tlv_buf = realloc(*tlv_buf, *tlv_sz);
            if (*tlv_buf == NULL) {
                LOGE("realloc: allocation failed");
                ret = -1;
            } else {
                bzero(*tlv_buf, *tlv_sz);
                ret = recv_buf(sock, *tlv_buf, *tlv_sz);
            }
        }
        return ret;
}


/* Reads hex encoded data from socket sock and decodes it.
 * A chunk is allocated for the decoded data and its address stored in buf.
 * The size of the allocated memory is returned.
 * buf[0] must be freed by the caller.
 *
 * On error no buffer is allocated.
 *
 * \param sock from this socket the data is read
 * \param buf must point to writable memory. In buf[0] the address of the
 * allocated memory is stored. buf[0] must be freed by the caller
 * \param return size of the allocated buffer pointed to by buf[0], -1 on error
 */
static ssize_t read_hex(int sock, char **buf) {
    size_t TMPBUF_SIZE = 1024;
    char *hexbuf = NULL;

    ssize_t nread = 0;
    ssize_t total_nread = 0;
    int iteration = 0;

    size_t retbuf_len = 0;

    assert(buf != NULL);

    while (1) {
        iteration++;

        hexbuf =
            (char *)realloc(hexbuf, iteration * TMPBUF_SIZE * sizeof(char));
        if (!hexbuf) {
            LOGE("realloc: %s", strerror(errno));
        }

        memset(&hexbuf[(iteration - 1) * TMPBUF_SIZE], '\x00', TMPBUF_SIZE);
        if ((nread = recv_buf(sock, &hexbuf[total_nread], TMPBUF_SIZE - 1)) ==
            -1) {
            LOGE("recv_buf error");
            free(hexbuf);
            return -1;
        }

        if (nread == 0) {
            LOGE("EOF");
            free(hexbuf);
            return -1;
        }

        total_nread += nread;
        assert(hexbuf[total_nread] == '\x00');

        if (strstr(&hexbuf[(iteration - 1) * TMPBUF_SIZE], "\n")) {
            break;
        }
    }

    // replace '\n' with '\x00'
    hexbuf[strlen(hexbuf) - 1] = '\x00';

    if (strlen(hexbuf) % 2 != 0) {
        LOGE("malformed hex msg: even number of bytes");
        free(hexbuf);
        return -1;
    }

    retbuf_len = strlen(hexbuf) / 2;
    *buf = (char *)calloc(1, retbuf_len * sizeof(char));
    if (*buf == NULL) {
        LOGE("calloc returned NULL.");
        perror("calloc");
    }

    for (size_t i = 0; i < retbuf_len; i++) {
        if (sscanf(&hexbuf[i * 2], "%2hhx", &(*buf)[i]) != 1) {
            LOGE("sscanf error");
            free(*buf);
            free(hexbuf);
            return -1;
        }
    }

    free(hexbuf);
    return retbuf_len;
}

/* Writes sz bytes from buf to socket sock. Output is hex-encoded.
 *
 * \param sock output goes to this socket
 * \param buf contains the data which will be written to sock
 * \param sz size of buf
 * \param return number of bytes written, -1 on error
 */
static ssize_t write_hex(int sock, char *buf, size_t sz) {
    char *hexbuf = 0;

    if (buf == NULL) {
        LOGE("buf is NULL");
        return -1;
    }

    if (sz == 0) {
        LOGE("sz is 0x00");
        return -1;
    }

    hexbuf = (char *)calloc(1, sz * 2 + 1); // +1 cuz of '\x00'
    int nhexed = 0;
    for (size_t i = 0; i < sz; i++) {

        if ((nhexed = snprintf(&hexbuf[i * 2], 3, "%02x", buf[i])) < 0) {
            LOGE("error hexing buf");
            free(hexbuf);
            return -1;
        }

        if (nhexed != 2) {
            LOGE("number of written hex bytes wrong");
            free(hexbuf);
            return -1;
        }
    }

    if (strlen(hexbuf) != (sz * 2)) {
        LOGE("hexbuf len is wrong");
        free(hexbuf);
        return -1;
    }
    send_buf(sock, hexbuf, strlen(hexbuf));
    free(hexbuf);
    return sz;
}

// Implementation of the functions provided by utils.h starts here

ssize_t read_data_log(const char *message, int sock, char **buf) {
    ssize_t nread = 0;
    if ((nread = read_data(sock, buf)) == -1) {
        LOGE("error reading %s", message);
        return -1;
    }
    return nread;
}

ssize_t write_data_log(const char *message, int sock, char *buf, size_t sz) {
    ssize_t nread = 0;
    if ((nread = write_data(sock, buf, sz)) == -1) {
        LOGE("error writing %s", message);
        return -1;
    } else if (nread == 0) {
        LOGE("no %s written", message);
        return -1;
    }
    return nread;
}

ssize_t read_data(int sock, char **buf) {
    ssize_t nread = 0;
    if ((nread = read_hex(sock, buf)) == -1) {
        LOGE("error reading data");
        return -1;
    }
    return nread;
}

ssize_t write_data(int sock, char *buf, size_t sz) {
    ssize_t nwrite = 0;
    if ((nwrite = write_hex(sock, buf, sz)) == -1) {
        LOGE("error writing data");
        return -1;
    }
    return nwrite;
}

ssize_t recv_item_by_name_exact(data_stream_t *ds, char *exp_item_name, char *item, size_t exp_item_sz) {
    ssize_t sz = recv_item_by_name(ds, exp_item_name, item, exp_item_sz);

    if (exp_item_sz != sz)
        goto err;

    return sz;
err:
    return -1;
}

ssize_t recv_item_by_name(data_stream_t *ds, char *exp_item_name, char *item, size_t max_item_sz)
{

    char name[256] = {0};
    char name_sz = 0;
    ssize_t item_sz = 0;
    char *data = NULL;
    // first we expect the name of the item we are receiving
    // get the size of this item
    data = ds_read(ds, 1);
    if (!data) {
        LOGE("ds_read: error parsing `name_sz`");
        goto err;
    }

    name_sz = *data;
    LOGD("sz is %d", name_sz);

    data = ds_read(ds, name_sz);
    if (!data) {
        LOGE("ds_read: error parsing `name`");
        goto err;
    }
    memcpy(name, data, name_sz);
    LOGD("name is %s", name);

    if (strncmp(name, exp_item_name, 256)) {
        LOGE("expecting `%s` but got `%s`", exp_item_name, name);
        goto err;
    }

    data = ds_read(ds, sizeof(uint32_t));
    if (!data) {
        LOGE("ds_read: error parsing `item_sz`");
        goto err;
    }
    item_sz = *(uint32_t*)data;

    LOGD("item_sz is %zd", item_sz);
    LOGD("max_item_sz is %zd", max_item_sz);

    if (max_item_sz < item_sz) {
        LOGE("max item size exceeded.");
        goto err;
    }

    data = ds_read(ds, item_sz);
    if (!data) {
        LOGE("ds_read: error parsing `item`");
        goto err;
    }
    memcpy(item, data, item_sz);
    return item_sz;
err:
    return -1;
}
