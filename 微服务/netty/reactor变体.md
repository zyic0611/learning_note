单线程reactor 就是io线程和worker线程是同一个线程 一个线程既负责接受io连接 也负责执行业务。

多线程reactor 就是分开了 io线程是单线程 worker线程是多线程 可以用线程池实现 1:n的关系

主从reactor n:m的关系 多个io线程 多个worker线程 所以可以有2个线程池