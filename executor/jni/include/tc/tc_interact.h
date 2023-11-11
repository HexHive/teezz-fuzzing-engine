#ifndef _TC_INTERACT_H_
#define _TC_INTERACT_H_

int tc_init(void);
//int tc_pre_execute(int status_sock);
int tc_execute(int data_sock);
//int tc_post_execute(int status_sock);
//int tc_deinit(void);

#endif // _TC_INTERACT_H_
