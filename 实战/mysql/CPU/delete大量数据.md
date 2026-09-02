业务现象：业务做大批量数据删除，delete 删除千万级历史过期数据，delete 执行期间，业务正常读写 RT 上涨，但是磁盘 IO 并不高，慢查询没有业务 SQL，delete 本身也没进慢查询。分析现象原因，以及会带来哪些衍生故障，排查看什么指标。

delete这个操作并不是马上真实删除 而是先给数据打上删除的标签 由purge线程去删除 删除的过程中会产生大量的 undolog。

就算分批commit 每次只提交1000条 没有长事务 行锁很快就释放 化石产生大量undolog： 业务快照读 每次都要去undolog里看自己属于哪个版本 undolog长 就会导致每个快照都 耗时都变高 RT则上涨了。每条查询页额外增加CPU开销。

purge线程在删除大量数据的时候 高频访问内存里的B+树 会上大量内存锁 其他查询可能cas失败 导致CPU上升 RT上涨。

io不高 说明大量页都在bufferpool中 。

在主从环境中 大delete 产生大量binlog 从库回放压力变大 RT变高。

指标：
1、 show engine innodb statues--History list length 就是没被purge清理完成的事务版本链长度
2、看PFS里面undo相关的等待事件

