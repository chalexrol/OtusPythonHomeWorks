Result of ApacheBench:

C:\httpd-2.4.46-win64-VS16\Apache24\bin>ab -n 50000 -c 100 -r http://localhost/httptest/dir2/page.html
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


Server Software:        ChAlex-HTTP-server
Server Hostname:        localhost
Server Port:            80

Document Path:          /httptest/dir2/page.html
Document Length:        38 bytes

Concurrency Level:      100
Time taken for tests:   6329.874 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      9250000 bytes
HTML transferred:       1900000 bytes
Requests per second:    7.90 [#/sec] (mean)
Time per request:       12659.747 [ms] (mean)
Time per request:       126.597 [ms] (mean, across all concurrent requests)
Transfer rate:          1.43 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0  126 219.2      1    2043
Processing:     6 12517 427.2  12707   15320
Waiting:        2 6397 3544.9   6590   14298
Total:          7 12644 394.2  12728   15323

Percentage of the requests served within a certain time (ms)
  50%  12728
  66%  12740
  75%  12747
  80%  12752
  90%  12764
  95%  12774
  98%  12788
  99%  12799
 100%  15323 (longest request)