#include <logging.h>
#include <utils.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>


#include <executor.h>
#include <optee/optee_interact.h>


int (*tz_interact)(int);

void setup_target(char *target) {

    if (!strcmp(TARGET_OPTEE, target)) {
        tz_interact = &optee_interact;
    } else {
        LOGE("Target not known.\n");
        exit(EXIT_SUCCESS);
    }
}

int handle_client(int sock) {
    int ret = 0;

    ret = tz_interact(sock);

    LOGD("Disconnecting client\n");
    close(sock);

    if (ret == -1) {
        LOGE("tz_interact failed\n");
        exit(EXIT_FAILURE);
    }

    LOGD("Exit child\n");
    exit(EXIT_SUCCESS);
}

int main(int argc, char **argv) {
    int sockfd, client_sock, c, ret;
    ssize_t nread, msg;
    struct sockaddr_in server, client;
    char* target = NULL;

    if (argc != 3) {
        printf("USAGE: %s <TEE> <PORT>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    target = argv[1];
    LOGD("Target is %s\n", target);
    setup_target(target);

    if ((sockfd = socket(AF_INET, SOCK_STREAM, 0)) == -1) {
        perror("socket");
        exit(EXIT_FAILURE);
    };

    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) ==
        -1) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(atoi(argv[2]));

    if (bind(sockfd, (struct sockaddr *)&server, sizeof(server)) == -1) {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    LOGD("bind done\n");

    if (listen(sockfd, 3) == -1) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    LOGD("Waiting for incoming connections...\n");

    c = sizeof(struct sockaddr_in);

    if ((client_sock = accept(sockfd, (struct sockaddr *)&client,
                              (socklen_t *)&c)) == -1) {
        perror("accept");
        exit(EXIT_FAILURE);
    }

    LOGD("Connection accepted\n");

    ret = handle_client(client_sock);

    if (ret == 0) {
        LOGD("Disconnecting client\n");
        fflush(stdout);
        close(client_sock);
    } else if (ret == -1) {
        close(client_sock);
        exit(EXIT_FAILURE);
    }

    exit(EXIT_SUCCESS);
}
