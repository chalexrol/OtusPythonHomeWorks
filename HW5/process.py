from log import get_log
import datetime
import os
import re
from urllib.parse import unquote
import argparse


def HTTPRequestParser(http_request):
    OPT_FIELDS_NAMES = [
        "User-Agent",
        "Accept",
        "Cache-Control",
        "Host",
        "Accept-Encoding",
        "Accept-Language",
        "If-Modified-Since",
        "If-None_match",
        "Referer",
        "Connection",
        "Cookie",
        "Content-Length",
    ]

    http_response = http_request.decode("utf-8") if not None else ""
    http_response_parsed = http_response.split("\r\n")
    request_type, request_parameters = http_response_parsed[0], http_response_parsed[1:]

    request_dict = {"Request": request_type.split(" ")}

    for opt in request_parameters:
        try:
            opt_name, opt_value = opt.split(": ")

            if opt_name in OPT_FIELDS_NAMES:
                request_dict.update({opt_name: opt_value})

            else:
                pass

        except ValueError:
            pass

    return request_dict


def header_maker(status, content_length=None, content_type=None, response_type=None):
    response_status = "HTTP/1.0 %s\r\n" % status

    if response_type != "HEAD":
        """ Date, Server, Content-Length, Content-Type, Connection """
        date = "Date: %s\r\n" % datetime.datetime.now().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        content_length = (
            "Content-Length: %s\r\n" % content_length if content_length else ""
        )
        content_type = "Content-Type: %s\r\n" % content_type if content_type else ""
        connection = "Connection: close\r\n"
        server = "Server: ChAlex-HTTP-server\r\n\n"
        result_arr = [
            response_status,
            date,
            content_length,
            content_type,
            connection,
            server,
        ]

    else:
        result_arr = [response_status, "Content-Length: 38\r\n\r\n"]

    res = [ra.encode() for ra in result_arr]

    return b"".join(res)


class HTTPResponseMaker(object):
    __slots__ = ["GET", "HEAD", "POST", "URL", "root_dir"]

    def __init__(self, request_type, url=None, root_dir=None):
        self.GET = request_type if request_type == "GET" else None
        self.HEAD = request_type if request_type == "HEAD" else None
        self.POST = request_type if request_type == "POST" else None
        self.URL = url
        self.root_dir = root_dir

    def __call__(self):
        try:
            parsed_url = URLParser(self.URL, root_dir=self.root_dir)
        except AttributeError:
            return header_maker("405 Method Not Allowed")

        url_status, file_type, file_length, file_content = parsed_url.url_analyzer()

        if self.GET:
            if url_status:
                get_log("Request GET -  %s, Response 200 OK" % self.URL, "info")

                header = header_maker("200 OK", file_length, file_type)

                full_response = header + file_content

                return full_response

            else:
                get_log("Request GET -  %s, Response 404 Not Found" % self.URL, "error")
                return header_maker("404 Not Found")

        elif self.HEAD:
            if url_status:
                get_log("Request HEAD, Response 200 OK", "info")
                return header_maker(
                    "200 OK", file_length, file_type, response_type="HEAD"
                )
            else:
                return header_maker("404 Not Found")

        elif self.POST:
            get_log("Request POST, Response 403 Forbidden", "error")
            return header_maker("403 Forbidden")

        else:
            get_log("Request OTHER, 405 Method Not Allowed", "error")
            return header_maker("405 Method Not Allowed")


def type_file_encoder(type_file):
    """.html,.css, js, jpg,.jpeg,.png,.gif,.swf"""
    if type_file == "html":
        return "text/html"
    elif type_file == "txt":
        return "text/plain"
    elif type_file == "css":
        return "text/css"
    elif type_file == "js":
        return "text/javascript"
    elif type_file == "jpg":
        return "image/jpeg"
    elif type_file == "jpeg":
        return "image/jpeg"
    elif type_file == "png":
        return "image/png"
    elif type_file == "gif":
        return "image/gif"
    elif type_file == "swf":
        return "application/x-shockwave-flash"
    else:
        return None


class URLParser(object):
    ERROR_FILLER = False, "", "", ""
    EXIST_FILE_CONFIRMATION = b"bingo, you found it\n"

    def __init__(self, url, root_dir=None):
        self.URL = [url_part for url_part in url.split("/") if url_part != ""]
        self.url_dir = os.listdir(root_dir)
        self.isDir = True if url[-1] == "/" else False
        self.args = url.split("?")[-1] if len(url.split("?")) == 2 else None

        self.root_dir = "./DOCUMENT_ROOT" if root_dir is None else root_dir

    def file_performer(self, full_patch):

        file_name = full_patch.split("/")[-1]
        file_size = os.path.getsize(full_patch)
        qualified_file_type = self.file_type_checker(file_name)
        correct_file_type = type_file_encoder(qualified_file_type)

        if correct_file_type is not None:

            with open(full_patch, "rb") as file:
                file_content = file.read()

            return True, correct_file_type, file_size, file_content

        else:
            return True, "text/html", file_size, self.EXIST_FILE_CONFIRMATION

    def file_type_checker(self, file_name):
        try:
            if not self.isDir:
                spl = file_name.split(".")

                if re.search(r"[..]{0}".format(spl[-1]), file_name):
                    _, file_type = ".", spl[-1]
                else:
                    _, file_type = spl

                return file_type

            else:
                return "html"

        except ValueError:
            return None

    def url_analyzer(self):

        try:

            # Using unquote for  %70%61%67%65%2e%68%74%6d%6c -> page.html
            if self.args is None:

                path_to_file, file_name = (
                    self.root_dir + "/" + "/".join(self.URL[:-1]),
                    unquote(self.URL[-1]),
                )

            else:
                path_to_file, file_name = (
                    self.root_dir + "/" + "/".join(self.URL[:-1]),
                    unquote(self.URL[-1]),
                )
                file_name = file_name.split("?")[0]

            full_patch = path_to_file + "/" + file_name
            isExistFile = os.path.exists(full_patch)

            # File exists and it is not a directory like /blabla/dir and not ARGS
            if isExistFile and not self.isDir and self.args is None:

                return self.file_performer(full_patch)

            # File exists and it is not a directory like /blabla/dir and ARGS
            elif isExistFile and not self.isDir and self.args is not None:

                return self.file_performer(full_patch)

            # It is  a directory like /blabla/dir
            elif isExistFile and self.isDir:

                try:
                    list_files = os.listdir(full_patch)

                    if "index.html" in list_files:
                        full_patch_to_index = full_patch + "/" + "index.html"
                        return self.file_performer(full_patch_to_index)

                    else:
                        return self.ERROR_FILLER

                # Suddenly - it is not a directory
                except NotADirectoryError:
                    return self.ERROR_FILLER

            # Did not find any dir or files
            else:
                return self.ERROR_FILLER

        except IndexError:
            return self.ERROR_FILLER

        except FileNotFoundError:
            return self.ERROR_FILLER


def args_parse(args):
    arg_parser = argparse.ArgumentParser(description="Set specific parameters")
    arg_parser.add_argument("--r", type=str, help="Way to specific root dir")
    arg_parser.add_argument("--w", type=int, help="Quantity of workers")

    return arg_parser.parse_args(args)


def header_checker(header):
    try:
        request_type, url, _ = header
        return request_type, url, _
    except ValueError:
        return "TEST", "/", ""


def HTTPHandler(connection, root_dir):
    while True:
        data = connection.recv(1024)

        if not data:
            return False

        else:
            request = HTTPRequestParser(data)
            request_main = request["Request"]
            request_type, url, _ = header_checker(request_main)
            response = HTTPResponseMaker(request_type, url=url, root_dir=None)
            resp = response()

        return resp
