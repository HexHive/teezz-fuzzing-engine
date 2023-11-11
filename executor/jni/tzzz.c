#include <logging.h>
#include <utils.h>
#include <alloca.h>
#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <signal.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
#include <sys/stat.h>

#include <optee/optee_interact.h>
#include <executor.h>

#ifdef __ANDROID__
#include <qsee/qsee_interact.h>
#include <tc/tc_interact.h>
#include <beanpod/beanpod_interact.h>
#endif

#define TARGET_QSEE "qsee"
#define TARGET_TC "tc"
#define TARGET_OPTEE "optee"
#define TARGET_BEANPOD "beanpod"

typedef struct teezz_state
{
    uint8_t stop_soon;
} teezz_state_t;
teezz_state_t STATE = {0};

static void setup_target(char *target, teezz_ops_t *ops)
{

#ifdef __ANDROID__
    if (!strcmp(TARGET_TC, target))
    {
        ops->init = NULL;
        ops->pre_execute = NULL;
        ops->execute = tc_execute;
        ops->post_execute = NULL;
        ops->deinit = NULL;
    }
    else if (!strcmp(TARGET_QSEE, target))
    {
        ops->init = NULL;
        ops->pre_execute = NULL;
        ops->execute = qsee_execute;
        ops->post_execute = NULL;
        ops->deinit = NULL;
    }
    else if (!strcmp(TARGET_OPTEE, target))
    {
        ops->init = optee_init;
        ops->post_execute = optee_pre_execute;
        ops->execute = optee_execute;
        ops->post_execute = optee_post_execute;
        ops->deinit = optee_deinit;
    }
    else if (!strcmp(TARGET_BEANPOD, target))
    {
        ops->init = beanpod_init;
        ops->post_execute = beanpod_pre_execute;
        ops->execute = beanpod_execute;
        ops->post_execute = beanpod_post_execute;
        ops->deinit = beanpod_deinit;
    }
    else
    {
        LOGE("Target not known.");
        exit(EXIT_SUCCESS);
    }
#else
    if (!strcmp(TARGET_OPTEE, target))
    {
        ops->init = optee_init;
        ops->post_execute = optee_pre_execute;
        ops->execute = optee_execute;
        ops->post_execute = optee_post_execute;
        ops->deinit = optee_deinit;
    }
    else
    {
        LOGE("Target not known.");
        exit(EXIT_SUCCESS);
    }
#endif
}

static void handle_client(const int client_sock, teezz_ops_t *ops)
{
    int ret = 0;

    ret = ops->execute(client_sock);

    LOGD("Disconnecting client");
    close(client_sock);
    LOGD("Exit child: %d", ret);
    // die!
    _exit(ret);
}

static void handle_stop_sig(int signum)
{
    (void)signum;
    STATE.stop_soon = 1;
    LOGD("handle_stop_sig");
}

static int fsrv_setup_signal_handlers()
{
    struct sigaction sa = {0};
    sa.sa_handler = handle_stop_sig;
    sa.sa_flags = SA_RESTART;
    sigaction(SIGHUP, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
    return 0;
}

static int fsrv_serve(int status_lsock, int data_lsock, teezz_ops_t *ops)
{
    int data_addr_len = 0, status_addr_len = 0, status = 0, ret = 0;
    int data_sock = 0, status_sock = 0;
    pid_t pid = 0, wpid = 0;
    struct sockaddr_in target, forkserver;
    int end_fork = 0;

    fsrv_setup_signal_handlers();

    // TODO: handle return value
    if (ops->init)
        ret = ops->init();

    // connect status sock
    status_addr_len = sizeof(struct sockaddr_in);
    if ((status_sock = accept(status_lsock, (struct sockaddr *)&forkserver,
                              (socklen_t *)&status_addr_len)) == -1)
    {
        perror("accept");
        exit(EXIT_FAILURE);
    }

    while (!STATE.stop_soon)
    {
        if (ops->pre_execute)
            ops->pre_execute(status_lsock);

        LOGD("Waiting for incoming connections...");

        data_addr_len = sizeof(struct sockaddr_in);
        if ((data_sock = accept(data_lsock, (struct sockaddr *)&target,
                                (socklen_t *)&data_addr_len)) == -1)
        {
            perror("accept");
            exit(EXIT_FAILURE);
        }

        LOGD("Connection accepted");
        if ((pid = fork()) == -1)
        {
            close(data_sock);
            LOGE("fork failed.");
            break;
        }
        else if (pid > 0)
        {
            close(data_sock);
            // wait for the child to terminate
            wpid = wait(&status);

            if (wpid > 0)
            {
                LOGD("Child returned successfully: %d", WEXITSTATUS(status));
                if (WEXITSTATUS(status) == 130)
                {
                    LOGD("Terminating.");
                    STATE.stop_soon = true;
                }
            }
            else
            {
                LOGD("Error waiting for child.");
                LOGD("wait: %s", strerror(errno));
                STATE.stop_soon = true;
            }

            if (ops->post_execute)
                ops->post_execute(status_sock);

            continue;
        }
        else if (pid == 0)
        {
            struct sigaction sa = {0};
            sa.sa_handler = SIG_DFL;
            sigaction(SIGHUP, &sa, NULL);
            sigaction(SIGINT, &sa, NULL);
            sigaction(SIGTERM, &sa, NULL);
            handle_client(data_sock, ops);
            // should never be reached
            break;
        }
    }
    LOGD("Stopped fsrv.");

    // TODO: handle return value
    if (ops->deinit)
        ret = ops->deinit();

    return 0;
}

int daemonize()
{
    int x;

    if (chdir("/") == -1)
    {
        return errno;
    }

    if ((x = fork()) > 0)
    {
        // so that parent can return
        exit(0);
    }
    else if (x == -1)
    {
        perror("fork");
        LOGE("unable to fork new process");
        exit(1); /* we can't do anything here, so just exit. */
    }

    if (setsid() == -1)
    {
        LOGE("setsid failed");
        return errno;
    }

    if ((x = fork()) > 0)
    {
        // so that parent can return
        exit(0);
    }
    else if (x == -1)
    {
        perror("fork");
        LOGE("unable to fork new process");
        exit(1); /* we can't do anything here, so just exit. */
    }

    umask(0);

    return 0;
}

static int create_listening_sock(int port)
{
    struct sockaddr_in server;
    int sock = 0;

    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) == -1)
    {
        perror("socket");
        exit(EXIT_FAILURE);
    };

    if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) ==
        -1)
    {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(port);

    if (bind(sock, (struct sockaddr *)&server, sizeof(server)) == -1)
    {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    LOGD("bind done");

    if (listen(sock, 3) == -1)
    {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    return sock;
}

int main(int argc, char **argv)
{
    int status_lsock = 0, data_lsock = 0, status_port = 0, data_port = 0;
    char *target;
    teezz_ops_t ops = {0};

    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (argc != 3)
    {
        printf("USAGE: %s <TARGET_TEE> <PORT>\n", argv[0]);
        exit(EXIT_SUCCESS);
    }

    // daemonize();

    target = argv[1];
    status_port = atoi(argv[2]);
    data_port = status_port + 1;

    LOGD("Target is %s", target);
    setup_target(target, &ops);

    status_lsock = create_listening_sock(status_port);
    data_lsock = create_listening_sock(data_port);
    fsrv_serve(status_lsock, data_lsock, &ops);

    close(data_lsock);
    close(status_lsock);
    exit(EXIT_SUCCESS);
}
