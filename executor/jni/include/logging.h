
#ifndef _LOGGING_H_
#define _LOGGING_H_

#include <stdio.h>
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define AT __FILE__ ":" TOSTRING(__LINE__)

#define LOGD(fmt, args...) printf("[+] %16s -- " fmt "\n", AT, ##args)
#define LOGI(fmt, args...) printf("[*] %16s -- " fmt "\n", AT, ##args)
#define LOGE(fmt, args...) fprintf(stdout, "[-] %16s -- " fmt "\n", AT, ##args)

void hexdump(char *desc, void *addr, int len);

#endif // _LOGGING_H_
