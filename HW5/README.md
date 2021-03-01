## Python HTTP Server

### Что делает
- Умеет понимать GET, HEAD запросы
- Отдавать файлы из DOCUMENT_ROOT
- На все остальные запросы возвращает 400 Bad Request, 405 Method Not Allowed, 404 Not Found в зависимости от ситуации
- Масштабироваться на несколько воркеров

### Принцип работы
- На старте заранее создаются N воркеров (threading.Thread), которые слушают очередь (queue.Queue)
- Сервер складывает коннекшены в очередь, которую в свою очередь разгребают воркеры
- Воркер вызывает HTTPHandler, который умеет распарсить инфо в HTTPRequest и сформировать HTTPResponse

### Как запускать

python httpd.py -a HOST -p PORT -w NUM WORKERS -b BACKLOG -d DOCUMENTROOT 
```

#### Опции
- -a - host, default = 127.0.0.1
- -p - port, default = 8080
- -w - num of workers, default = 20
- -b - queue size for each worker, default = 10
- -d - document root, default = static

### Тесты
 python -m unittest -v tests.unit.test_httpd
```



Result of ApacheBench:

C:\httpd-2.4.46-win64-VS16\Apache24\bin>ab -n 50000 -c 100 -r http://localhost:8080/httptest/dir2/page.html
This is ApacheBench, Version 2.3 <$Revision: 1879490 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        Python
Server Hostname:        localhost
Server Port:            8080

Document Path:          /httptest/dir2/page.html
Document Length:        38 bytes

Concurrency Level:      100
Time taken for tests:   53.863 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      9300000 bytes
HTML transferred:       1900000 bytes
Requests per second:    928.28 [#/sec] (mean)
Time per request:       107.726 [ms] (mean)
Time per request:       1.077 [ms] (mean, across all concurrent requests)
Transfer rate:          168.61 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.4      0       2
Processing:    31  103  18.1    101     499
Waiting:        2  102  18.0    100     497
Total:         32  103  18.1    101     500

Percentage of the requests served within a certain time (ms)
  50%    101
  66%    105
  75%    108
  80%    110
  90%    116
  95%    121
  98%    127
  99%    132
 100%    500 (longest request)

C:\httpd-2.4.46-win64-VS16\Apache24\bin>