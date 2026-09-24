CPU 不高、磁盘 IO 打满、RT 上涨，没有慢 SQL、没有大量回表（排除 CPU 型开销）

IO瓶颈的本质就是Mysql要向磁盘写数据 或者读数据 await飙升 CPU空闲。 理解为io密集型业务

所以分为两类 写IO和读IO

写IO：
1、Buffer Pool里 脏页过多 --业务大量更新 触发强制刷盘 在磁盘随机IO 
2、RedoLog日志满了 必须刷盘 写事务阻塞 等待redolog刷入
3、BinLog写入 如果配置了同步刷入 则每次提交事务的时候Binlog都强制刷盘 IO大

读IO
1、Buffer Pool 太小，要读的页面在磁盘
2、读冷数据 在磁盘内
