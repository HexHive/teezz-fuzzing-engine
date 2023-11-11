#!/usr/bin/env python3
import telnetlib
import logging
import codecs


logging.basicConfig(level=logging.DEBUG)


def test(data):
    l = len(data)
    p.send(codecs.encode(data, 'hex') + b'\n')
    rdata = p.recv(l)
    if rdata != data:
        logging.error("error")
        logging.error("%s != %s" % (data, rdata))


def main():
    data = b"foo"
    test(data)
    logging.info("We're good!")


if __name__ == "__main__":

    HOST = "127.0.0.1"
    PORT = 31337
    t = telnetlib.Telnet(HOST, PORT)
    p = t.get_socket()
    main()
