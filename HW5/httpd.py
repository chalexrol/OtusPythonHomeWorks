import socket
from process import HTTPHandler
from process import args_parse


import threading
import sys
import random


class HTTPWorkerThread(threading.Thread):
    """ Thread for requests """
    def __init__(self, thread_name, thread_id):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_id = thread_id

    def run(self):
        print("START THREAD", str(self.thread_id))

    def perform(self, connection, root_dir):
        res = HTTPHandler(connection, root_dir)
        if not res:
            pass
        else:
            connection.sendall(res)
            connection.close()


class MainWorker(object):
    def __init__(self, host, port):
        self.isWorking = True
        self.args = args_parse(sys.argv[1:])
        self.port = port
        self.host = host
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.default_workers = 3

    def startServer(self):
        root_dir, workers = self.args.r, self.args.w if self.args.w is not None else self.default_workers

        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(workers)

        threads = []

        for x in range(workers):
            thread = HTTPWorkerThread(x, x)
            thread.start()
            threads.append(thread)

        while True:
            if self.isWorking:
                connection, _ = self._server.accept()

                handler = random.choice(threads)
                handler.perform(connection, root_dir)
            else:
                [t.join() for t in threads]

        self._server.close()

    def stopServer(self):
        self.isWorking = False


def main(host="localhost", port=80):
    print("SERVER STARTED")
    try:
        MW = MainWorker(host, port)
        MW.startServer()

    except KeyboardInterrupt:
        print("SERVER STOPPED")
        MW.stopServer()


if __name__ == "__main__":
    main("localhost", 80)
