
## insert

### 基础语法：

单条插入：

``` mysql
insert into table xx values xx
```

批量插入

```mysql
insert into table xx values xx1,xx2,xx3
```

批量操作只需要写一次Redo Log 并且只有一次网络往返 性能高。

### on duplicate key update

```mysql
insert into ... on duplicate key update
```

简单理解就是插入操作 一般得先判断有没有存在这个东西 再插入 因为有些唯一字段不允许重复插入 。如果重复插入 会报错 这个方法就是如果有重复 就不报错 转变为更新操作 覆盖
#### 高并发问题：

高并发请求涌入时  先select 再insert 容易发生幻读 导致唯一索引冲突

如果想解决上述问题 一般要采用java层面加分布式锁。

 但是会有两次网络往返 java select--> mysql mysql返回数据 java insert -->mysql mysql返回数据。

采用on duplicate key update语法  **可以直接把加锁操作下沉到mysql引擎层** 只有一次网络往返 效率高 。降低接口响应时间。

理解为锁的粒度更精细。

#### 底层原理：

1. 尝试插入：innodb引擎尝试向B+索引树汇中插入行记录
2. 冲突检测：插入过程中 索引会检查是否冲突
3. 原地转换： 发现冲突 不会报错 由执行器捕获冲突 转为更新操作

关键点：

在索引加锁的状态下完成 RR级别下 会给行or间隙 上X排他锁。 则杜绝高并发问题。

#### 平替：

可以使用insert ignore 遇到冲突直接忽略不报错 



## update

```mysql
updapte xxx(tableName) set xxx(columnName)=xxx where xxx(columnName)=xxx
```

### 底层问题：

innoDB默认隔离级别是RR 如果where字段没有建立索引 或者优化器认为走全表扫描成本更低 那么InnoDB就无法精确定位是哪一行。

走全表扫描 就会把全表所有记录和间隙 都锁住 。上表锁。 

在高并发系统中 一个没有走索引的update操作 会瞬间阻塞所有的更新和插入操作 引发线上雪崩。

### 开发铁律

**所有update和delete的where条件 必须命中索引。**



## 删除操作

### delete

dml（数据操纵）语句  逐行删除  会记录完整的binlog和undolog 事务可以回滚。

他只是在b+树上打上已删除的标记 磁盘空间没有归还。

 如果一次性delete几百万条数据 日志会暴涨 还可能引发**长事务**甚至**主从延迟**。

#### 长事务:

delete会产生大量的undo log 而事务在提交前会一直持有历史版本。

如果删除几百万行 每一行都会产生undolog 用于回滚+mvcc

删除不是立即消失 只是打上标记。

事务在提交前一直没结束 则undolog很多并且无法释放 数据的旧版本必须保留。

总结就是 长事务是因为**持有大量未提交Undolog的版本 时间过长**。

#### 主从延迟:

binlog是在事务commit的时候一次性写入的。 从库复制逻辑是IO线程拉取binlog sql线程执行binlog

1. 事务太大：

一个delete 100万行 在binlog是一个超级大的事务。

从库执行逻辑 是必须完整执行完 才能提交。无法插队。

 所后面所有的事务都要排队 则其他同步操作会被延迟了。

2. 执行时串行 

同一个事务是单线程执行 大事务无法拆分 从库卡在delete上 延迟暴涨

3. 锁竞争

delete会加大量的行锁 甚至触发间隙锁。

可能会重放这些加锁行为 阻塞其他sql。

#### 大表清理方案：

 每次limit 1000 分批次删除  或者建立新表导出数据重命名替换。

### truncate 

物理清空 ddl（数据定义）语句 直接释放整个数据页 不记录行级日志 速度快 重置自增id 不可回滚。

### drop

ddl语句 表结构 数据 索引 全部物理删除。