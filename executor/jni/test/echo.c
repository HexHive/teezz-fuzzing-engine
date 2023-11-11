#include "logging.h"
#include "mytc.h"
#include "utils.h"
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

int handle_client(int sock) {
    char *buf = NULL;
    size_t sz = 0;

    read_data(sock, &buf, &sz);

    printf("size: %lu\n", sz);

    send(sock, buf, sz, 0);
    return 0;
}

int main(int argc, char **argv) {
    int sockfd, client_sock, c, ret;
    ssize_t nread, msg;
    struct sockaddr_in server, client;

    if (argc != 2) {
        printf("USAGE: %s <PORT>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

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
    server.sin_port = htons(atoi(argv[1]));

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
