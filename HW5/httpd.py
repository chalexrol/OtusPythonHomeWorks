# -*- coding: utf-8 -*-

import argparse
import datetime
import io
import logging
import mimetypes
import os
import queue
import socket
import threading
import typing
import urllib.parse

REQUEST_MAX_SIZE = 1024 * 1024
REQUEST_CHUNK_SIZE = 1024
CLIENT_SOCKET_TIMEOUT = 5
INDEX_PAGE = 'index.html'
BASE_DIR = os.path.dirname(__file__)
DOCUMENT_ROOT = None


def file_content_length(file_descriptor) -> int:
    """
    Calculate file content length
    :param file_descriptor: file desrcriptor
    :return: int
    """
    if isinstance(file_descriptor, io.BytesIO):
        content_length = len(file_descriptor.getvalue())
    else:
        stat = os.fstat(file_descriptor.fileno())
        content_length = stat.st_size
    return content_length


def socket_read_data(client_socket: socket.socket, chunk_size: int, max_size: int) -> bytes:
    """
    Read data from socket by chunk_size and stop if data contain rnrn symbols

    :param client_socket: client socket
    :param chunk_size: size of chunk to read from socket
    :param max_size: maximum allowed size of data
    :return: binary string
    """
    data = b""
    while True:
        if len(data) > max_size:
            logging.debug('Data is too big. Break')
            break
        if b"\r\n\r\n" in data:
            logging.debug('Find end of headers in data. Break')
            break
        try:
            logging.debug('Try to read next chunk from socket ...')
            chunk = client_socket.recv(chunk_size)
            logging.debug('Read socket chunk: %s' % chunk)
            if chunk == b"":
                logging.debug('Received empty string. Break')
                break
            data += chunk
        except socket.timeout:
            msg = 'Socket lost connection by timeout: %d, socket: %s' % (client_socket.gettimeout(), str(client_socket))
            logging.error(msg)
            break
    return data


class HTTPRequest:
    """
    Implementation of HTTP request
    """

    def __init__(self, method: str, path: str, version: str, headers: list,
                 body: typing.Optional[str] = None) -> None:
        self.method = method
        self.path = path
        self.version = version
        self.headers = headers or []
        self.body = body

    def __repr__(self):
        return '<%s(method=%s, path=%s, version=%s, headers=%s, body=%s)>' % \
               (self.__class__.__name__, self.method, self.path, self.version, self.headers, self.body)

    @classmethod
    def from_raw(cls, raw: bytes, encoding: str = 'iso-8859-1') -> "HTTPRequest":
        """
        Build HTTPRequest object from bytes
        :param raw: bytes
        :param encoding: encoding
        :return: HTTPRequest
        """
        lines = raw.decode(encoding).split("\r\n")

        request_line = lines[0]
        method, path, version = request_line.split(' ')

        headers = []
        for header in lines[1:]:
            if not header:
                break
            headers.append(header)

        return cls(method=method.upper(), path=path, version=version, headers=headers)


class HTTPResponse:
    """
    Implementation of HTTP Response. Can send self via socket
    """

    def __init__(self, status: str, headers: list = None, body: str = None, content: str = None,
                 version: str = 'HTTP/1.0', encoding: str = 'iso-8859-1') -> None:
        self.version = version
        self.status = status
        self.headers = headers or ['Content-Type: text/plain']

        default_headers = [
            'Server: Python HTTP Server',
            'Date: %s' % datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Connection: close'
        ]

        self.headers += default_headers

        self.body = body
        self.content = content
        self.encoding = encoding

    def send(self, sock: socket.socket) -> None:
        """
        Calculate Content-Length
        Convert self to bytes string
        And send bytes through socket

        :param sock: Client socket through which to send the data
        :return: None
        """

        if self.content is not None:
            logging.debug('Set body as descriptor = io.BytesIO')
            descriptor = io.BytesIO(self.content.encode(self.encoding))
        elif self.body is not None:
            logging.debug('Set body as descriptor = io.open')
            descriptor = io.open(self.body, 'rb')
        else:
            logging.debug('Set body as descriptor = empty io.BytesIO')
            descriptor = io.BytesIO()

        content_length = None
        for header in self.headers:
            if header.lower().startswith('content-length'):
                _, _, content_length = header.partition(':')
                content_length = int(content_length)

        if content_length is None:
            content_length = file_content_length(descriptor)
            self.headers.append('Content-Length: %s' % content_length)

        headers = "%s %s\r\n" % (self.version, self.status)
        for header in self.headers:
            headers += header + "\r\n"
        headers += "\r\n"
        headers = headers.encode(self.encoding)

        sock.sendall(headers)
        with descriptor:
            try:
                sock.sendfile(descriptor)
            except BrokenPipeError:
                logging.exception('BrokenPipeError in sendfile')
                pass

    def __repr__(self):
        return "<%s(version=%s, status=%s, headers=%s>" % \
               (self.__class__.__name__, self.version, self.status, self.headers)


class HTTPHandler:
    """
    Implementation of HTTP Handler
    """

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.request = None

    def handle(self) -> None:
        """
        Read bytes data from socket
        Build HTTPRequest
        Process request
        Build HTTPResponse
        And send HTTPResponse via socket
        :return: None
        """
        with self.sock:
            self.sock.settimeout(CLIENT_SOCKET_TIMEOUT)
            socket_data = socket_read_data(self.sock, chunk_size=REQUEST_CHUNK_SIZE, max_size=REQUEST_MAX_SIZE)
            logging.debug('Read data from socket: %s' % socket_data)
            if socket_data == b"":
                logging.info('Client sock lost connection')
                self.sock.close()
            else:
                try:
                    self.request = HTTPRequest.from_raw(socket_data)
                    logging.info('Request: %s' % str(self.request))
                except Exception:
                    logging.exception('Cant parse request from socket data: %s' % socket_data)
                    http_response = self.handle_bad_request()
                else:
                    handler_name = 'handle_%s' % self.request.method.lower()
                    if not hasattr(self, handler_name):
                        handler = self.handle_method_not_allowed
                    else:
                        handler = getattr(self, handler_name)
                    http_response = handler()

                logging.info('Response: %s' % str(http_response))
                http_response.send(self.sock)

    def handle_bad_request(self) -> "HTTPResponse":
        return HTTPResponse(
            status='400 Bad Request',
            content='Bad Request'
        )

    def handle_method_not_allowed(self) -> "HTTPResponse":
        return HTTPResponse(
            status='405 Method Not Allowed',
            content='Method Not Allowed'
        )

    def handle_not_found(self) -> "HTTPResponse":
        return HTTPResponse(
            status='404 Not Found',
            content='Not Found'
        )

    def handle_head(self) -> "HTTPResponse":
        return self._handle_file()

    def handle_get(self) -> "HTTPResponse":
        return self._handle_file()

    def _handle_file(self) -> "HTTPResponse":
        """
        Get HTTPRequest.path and check if file exists in DOCUMENT ROOT
        Calculate Content-Length
        And return HTTPResponse
        :return: HTTPResponse
        """
        url = urllib.parse.urlparse(urllib.parse.unquote(self.request.path))
        path = url.path.strip('/')
        if not path:
            path = INDEX_PAGE

        filepath = os.path.normpath(os.path.join(DOCUMENT_ROOT, path))
        if not filepath.startswith(DOCUMENT_ROOT):
            logging.error('Bad request path: "%s"' % filepath)
            return self.handle_not_found()

        if os.path.isdir(filepath):
            filepath = os.path.join(filepath, INDEX_PAGE)

        if not os.path.exists(filepath):
            logging.error('File not exists: "%s"' % filepath)
            return self.handle_not_found()

        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = 'application/octet-stream'
        if encoding is not None:
            content_type += '; charset=%s' % encoding

        with open(filepath, 'rb') as fr:
            content_length = file_content_length(fr)

        headers = [
            'Content-Type: %s' % content_type,
            'Content-Length: %s' % content_length
        ]

        body = filepath if self.request.method == 'GET' else None
        return HTTPResponse(
            status='200 OK',
            headers=headers,
            body=body
        )


class HTTPWorker(threading.Thread):
    """
    Implementation of Worker
    """

    def __init__(self, connection_queue: queue.Queue) -> None:
        super(HTTPWorker, self).__init__(daemon=True)
        self.connection_queue = connection_queue
        self.running = False
        logging.debug('Worker %s has been created' % str(self))

    def stop(self) -> None:
        logging.debug('Worker %s has been stopped' % str(self))
        self.running = False

    def run(self) -> None:
        """
        Try to get socket from queue and call HTTPHandler to process request
        :return: None
        """
        logging.debug('Worker %s is run now' % str(self))
        self.running = True
        while self.running:
            try:
                client_socket, client_addr = self.connection_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                logging.debug('Worker %s received socket' % str(self))
                handler = HTTPHandler(client_socket)
                handler.handle()
            except Exception:
                logging.exception('Cant handle socket')
                continue
            finally:
                self.connection_queue.task_done()


class HTTPServer:
    """
    Implementation of HTTP Server
    """

    def __init__(self, host: str, port: int, num_workers: int, backlog: int, client_socket_timeout: int) -> None:
        self.host = host
        self.port = port
        self.backlog = backlog
        self.num_workers = num_workers
        self.client_socket_timeout = client_socket_timeout
        self.connection_queue = queue.Queue(self.num_workers * self.backlog)

    def serve_forever(self) -> None:
        """
        Build N HTTPWorker
        Initialize server socket
        Put client connections to queue
        :return: None
        """
        workers = []
        for _ in range(self.num_workers):
            worker = HTTPWorker(self.connection_queue)
            worker.start()
            workers.append(worker)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(self.num_workers * self.backlog)
            logging.info('Start server on %s' % str(server_socket.getsockname()))

            while True:
                try:
                    self.connection_queue.put(server_socket.accept())
                except KeyboardInterrupt:
                    logging.info('Stop server now...')
                    break

        for worker in workers:
            worker.stop()

        for worker in workers:
            worker.join(timeout=15)
        logging.info('Sever is shutdown')


def main(args):
    logging.info('Start app with arguments %s' % str(args))
    server = HTTPServer(
        host=args.address,
        port=args.port,
        backlog=args.backlog,
        num_workers=args.num_workers,
        client_socket_timeout=CLIENT_SOCKET_TIMEOUT
    )
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', type=str, default='127.0.0.1', help='Server address. Default=127.0.0.1')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port. Default=8080')
    parser.add_argument('-w', '--num_workers', type=int, default=20, help='Number of workers. Default=20')
    parser.add_argument('-b', '--backlog', type=int, default=10, help='Backlog for each worker. Default=10')
    parser.add_argument('-d', '--documentroot', type=str, default='DOCUMENT_ROOT', help='Directory with static files')

    args = parser.parse_args()

    if not args.documentroot.startswith('/'):
        args.documentroot = os.path.join(BASE_DIR, args.documentroot)

    if not os.path.exists(args.documentroot):
        print('Invalid -d argument. This path %s does not exists' % args.documentroot)
        exit()
    elif not os.path.isdir(args.documentroot):
        print('Invalid -d argument. This path %s must be a directory' % args.documentroot)
        exit()
    else:
        DOCUMENT_ROOT = args.documentroot

    logging.basicConfig(
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level=logging.INFO
    )
    main(args)
