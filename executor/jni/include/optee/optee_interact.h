#ifndef _OPTEE_INTERACT_H_
#define _OPTEE_INTERACT_H_

int optee_init(void);
int optee_pre_execute(int status_sock);
int optee_execute(int data_sock);
int optee_post_execute(int status_sock);
int optee_deinit(void);

#endif // _OPTEE_INTERACT_H_
