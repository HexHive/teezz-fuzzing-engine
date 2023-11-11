#ifndef _BEANPOD_INTERACT_H_
#define _BEANPOD_INTERACT_H_

int beanpod_init(void);
int beanpod_pre_execute(int status_sock);
int beanpod_execute(int data_sock);
int beanpod_post_execute(int status_sock);
int beanpod_deinit(void);

#endif // _BEANPOD_INTERACT_H_
