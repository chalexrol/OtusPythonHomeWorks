#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import traceback
import uuid
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from config import DEBUG
from scoring import get_score, get_interests
from checker import date_checker, email_checker

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}

UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class CharField(object):

    def __init__(self, name, required, nullable):
        self.name = "_" + name
        self.default = None
        self.required = required
        self.nullable = nullable

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):

        value = value or self.default

        if value is not None:
            if isinstance(value, str):
                setattr(instance, self.name, value)
            else:
                setattr(instance, self.name, '')
        else:
            setattr(instance, self.name, None)


class EmailField(CharField):

    def __init__(self, name, required=False, nullable=True):
        self.name = "_" + name
        self.required = required
        self.nullable = nullable
        self.default = None

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if not hasattr(self, self.name):

            # check - value is email with @ and mathc with regexp

            if value is not None and email_checker(value) is not None:
                setattr(instance, self.name, value)
            else:
                setattr(instance, self.name, self.default)


class PhoneField(object):

    def __init__(self, name, required=False, nullable=True):
        self.name = "_" + name
        self.required = required
        self.nullable = nullable
        self.default = None

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if not hasattr(self, self.name):
            if value is not None and value != '':
                str_val = str(value)
                first_digit = str_val[0]
                if len(str_val) == 11 and first_digit == '7':
                    setattr(instance, self.name, value)
                else:
                    setattr(instance, self.name, self.default)
            else:
                setattr(instance, self.name, value)


class BirthDayField(object):
    def __init__(self, name, required=False, nullable=True):
        self.name = "_" + name
        self.required = required
        self.nullable = nullable
        self.default = None

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if not hasattr(self, self.name):

            value = value or self.default

            is_correct_date = date_checker(value)

            if value is not None:
                if is_correct_date:
                    setattr(instance, self.name, value)
                else:
                    # User too old :( for this scoring API
                    setattr(instance, self.name, '')
            else:
                setattr(instance, self.name, None)


class GenderField(object):
    def __init__(self, name, required=False, nullable=True):
        self.name = "_" + name
        self.required = required
        self.nullable = nullable
        self.default = ''

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):

        if not hasattr(self, self.name):
            if value is not None:

                if value in [0, 1, 2]:
                    setattr(instance, self.name, value)
                else:
                    setattr(instance, self.name, self.default)
            else:
                setattr(instance, self.name, None)


class ClientIDsField(object):
    def __init__(self, name, required):
        self.name = "_" + name
        self.default = None
        self.required = required

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, values):

        values = values or self.default

        if isinstance(values, list):
            if self.required:
                if values is not None:
                    is_digits = list({True if isinstance(d, int) else False for d in values})
                    if len(is_digits) == 1 and True in is_digits:
                        setattr(instance, self.name, values)
                    else:
                        setattr(instance, self.name, self.default)
                else:
                    setattr(instance, self.name, values)
            else:
                setattr(instance, self.name, self.default)
        else:
            setattr(instance, self.name, self.default)


class DateField(object):
    def __init__(self, name, required=False, nullable=True):
        self.name = "_" + name
        self.required = required
        self.nullable = nullable
        self.default = None

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if not hasattr(self, self.name):
            if self.required:
                if value is not None and date_checker(value):
                    setattr(instance, self.name, value)

                elif value is None:
                    setattr(instance, self.name, None)

            else:
                if value is not None:
                    if date_checker(value):
                        setattr(instance, self.name, value)
                    else:
                        setattr(instance, self.name, '')

                elif value is None:
                    setattr(instance, self.name, self.default)


class ClientsInterestsRequest(object):
    client_ids = ClientIDsField('client_ids', required=True)
    date = DateField('date', required=False, nullable=True)

    def __init__(self, client_ids, date):
        self.client_ids = client_ids
        self.date = date

    def __get__(self, instance, cls):
        return getattr(instance, self.name)

    def has_clients_Ids(self):
        if hasattr(self, 'client_ids'):
            if self.client_ids is not None and len(self.client_ids) > 0:
                return True
            else:
                return False
        else:
            return False

    def get_interests(self):

        if self.has_clients_Ids():
            if self.date or self.date is None:
                return {str(client_id): get_interests(client_id) for client_id in self.client_ids}, 200
            else:
                return {"error": ERRORS[INVALID_REQUEST]}, 422
        else:
            return {"error": ERRORS[INVALID_REQUEST]}, 422


class OnlineScoreRequest(object):
    first_name = CharField('first_name', required=False, nullable=True)
    last_name = CharField('last_name', required=False, nullable=True)
    email = EmailField('email', required=False, nullable=True)
    phone = PhoneField('phone', required=False, nullable=True)
    birthday = BirthDayField('birthday', required=False, nullable=True)
    gender = GenderField('gender', required=False, nullable=True)

    def __init__(self, phone, email, first_name, last_name, birthday, gender):
        self.phone = phone
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.birthday = birthday
        self.gender = gender

    def has_phone_email_fields(self):
        return True if self.phone is not None and self.email is not None else False

    def has_first_last_name_fields(self):
        return True if self.last_name is not None and self.first_name is not None else False

    def has_gender_birthday_fields(self):
        return True if self.gender is not None and self.birthday != '' else False

    def get_score(self):

        # Check we have correct arguments != '' 
        is_correct_values = {False if self.__dict__[key] in [''] else True for key in [*self.__dict__]}

        if len(is_correct_values) == 1 and True in is_correct_values:

            if self.has_phone_email_fields():
                return {'score': get_score(self.phone, self.email)}, 200

            if self.has_first_last_name_fields():
                return {'score': get_score(None, None, last_name=self.last_name, first_name=self.first_name)}, 200

            if self.has_gender_birthday_fields():
                return {'score': get_score(None, None, gender=self.gender, birthday=self.birthday)}, 200

            else:
                return {"error": ERRORS[INVALID_REQUEST]}, 422

        else:
            return {"error": ERRORS[INVALID_REQUEST]}, 422


class MethodRequest(object):
    account = CharField('account', required=False, nullable=True)
    login = CharField('login', required=True, nullable=True)
    token = CharField('token', required=True, nullable=True)
    method = CharField('method', required=True, nullable=False)

    def __init__(self, account, login, token, method):
        self.account = account
        self.login = login
        self.token = token
        self.method = method

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def hash_encoder(arr):
    return b''.join([x.encode('utf-8') for x in arr])


def check_auth(account_request):
    user_is_admin = account_request.is_admin

    # UTF-8 ENCODE REQUIRED 
    if user_is_admin:
        hash_admin_parts = [datetime.datetime.now().strftime("%Y%m%d%H"), ADMIN_SALT]
        digest = hashlib.sha512(hash_encoder(hash_admin_parts)).hexdigest()

    elif not user_is_admin:

        hash_parts = [account_request.account, account_request.login, SALT]
        digest = hashlib.sha512(hash_encoder(hash_parts)).hexdigest()

    if digest == account_request.token:
        return True

    return False


def request_handler(account_request, request_args, ctx):
    if account_request.method == 'online_score' and account_request.login != 'admin':
        requires_fields = ['phone', 'email', 'first_name', 'last_name', 'birthday', 'gender']
        attrs = [request_args[x] if x in [*request_args] else None for x in requires_fields]
        score = OnlineScoreRequest(*attrs)

        # UPDATE CONTEXT HAS
        ctx.update({'has': [attr for attr in requires_fields if attr in [*request_args]]})

        result = score.get_score()

        return result, ctx

    elif account_request.method == 'online_score' and account_request.login == 'admin':
        return {'score': 42}, OK

    elif account_request.method == 'clients_interests':
        requires_fields = ['client_ids', 'date']
        attrs = [request_args[x] if x in [*request_args] else None for x in requires_fields]
        interests = ClientsInterestsRequest(*attrs)

        # UPDATE CONTEXT nclients
        ctx.update({'nclients': len(interests.client_ids) if interests.client_ids is not None else 0})

        interests_result = interests.get_interests()

        return interests_result, ctx

    else:
        # Unknown method
        raise AttributeError('Unknown method')


def method_handler(request, ctx, store):
    params = request['body']

    try:
        request_args = request['body']['arguments']
    except KeyError:
        return {"error": ERRORS[INVALID_REQUEST]}, 422

    requires_fields = ['account', 'login', 'token', 'method']

    for field in requires_fields:
        if field not in [*params]:
            return {"error": ERRORS[INVALID_REQUEST]}, 422

    account_request = MethodRequest(params['account'],
                                    params['login'],
                                    params['token'],
                                    params['method'])

    if not check_auth(account_request):
        return {"error": ERRORS[FORBIDDEN]}, FORBIDDEN

    elif check_auth(account_request) and account_request.login == 'admin':
        return {'score': 42}, OK

    elif not check_auth(account_request) and account_request.login == 'admin':
        return {"error": ERRORS[FORBIDDEN]}, FORBIDDEN

    else:
        result, ctx = request_handler(account_request, request_args, ctx)
        return result


class MainHTTPHandler(BaseHTTPRequestHandler):
    """Method -> this is an URL like in http://localhost:8080/method """

    router = {
        "method": method_handler
    }

    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):

        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None

        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")

            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))

            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)

                except AttributeError:
                    logging.error('Unexpected error - Invalid request')
                    code = INVALID_REQUEST

                except Exception as e:
                    logging.error(f'Unexpected error -> {traceback.format_exc()}') if DEBUG else logging.error(
                        f'Unexpected error -> {e}')
                    code = INTERNAL_ERROR

            else:
                code = NOT_FOUND

        # ADD RESP CODE
        self.send_response(code)
        # ADD HEADER
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}

        # ADD CONTAINS
        context.update(r)
        logging.info(context)

        byte_resp = bytes(json.dumps(r), 'utf-8')
        self.wfile.write(byte_resp)

        return

def is_file(file_path):
    return True if file_path and os.path.isfile(file_path) else False



if __name__ == "__main__":

    print('START SERVER') if DEBUG else None

    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    print(opts.log)
    if (opts.log == None) :
       logging.basicConfig(filename='./opts.log', level=logging.INFO,
                 format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    else:
        logging.basicConfig(filename=opts.log, level=logging.INFO,
                            format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        pass

    server.server_close()
