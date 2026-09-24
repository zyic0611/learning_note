explain 执行计划。 mysql就不会去执行这条sql 而是返回一个报告。

1. type 查询类型 
2. key 实际用到的索引 为null 说明全盘扫描
3. extra 使用了什么方式
4. rows 优化器估计会扫描了多少行
5. filtered 10% 优化器统计 返回的数据占比

## type：

- all 全盘扫描 所有数据 
- index 全索引扫描 没扫全表 但是查全部索引树。 通常查询字段都在二级索引树上 就直接全部扫索引树了 不需要回表。
- range 范围查找 `between > < in()` 走索引的范围查找 在索引树上范围查找很快
- ref 非唯一索引树上的等值查找 可能命中多个节点。 由于可能不是唯一的 会查出多条数据 
- **eq_ref  连接查询** 
	- 在使用join的时候 主表在从表中只会最多匹配到一条记录 通常是 从表使用了主键/唯一索引 作为关联条件。
	- `SELECT * FROM a JOIN b ON a.id = b.a_id`;。
	- 官方的核心理解是 每读驱动表一行  被驱动表（主表）最多返回一行数据 
	- 本质原因是关联字段具有 PRIMARY KEY 或 UNIQUE 约束，
	- 因此索引查找天然唯一，在二级索引上 最多只会命中一个节点。
	- 若需要回表，也最多回表一次。
- const 极速匹配 在一级索引树上 通过主键或者唯一索引 由于是唯一确定的 扫描到一条就停止。
- system 表里只有一行数据 const的特例

性能从低到高排序

## extra

- using index: 覆盖索引 查询所有列均来自索引树 不需要回表
- using index condition 索引下推 回表了 但是在二级索引上预先过滤一批索引里的字段
- using where 在mysql 的 server做where过滤  不一定没用索引 有可能用了索引  但是可能只过滤出来了部分条件。有些字段可能不在索引树里能做出判断， 还需要丢给server层走where条件再过滤一次。 using where 不一定就很慢 比如where id=1 也是using where 因为mysql还会在server层过滤一次id=1
- using filesort ：mysql无法利用索引排序 只能把数据读取到内存中 在server层进行一次排序 非常耗CPU和内存
  - SELECT * FROM user WHERE age = 20 ORDER BY create_time
  - 只有age是单列索引 扫出来数据后 create_time是乱序的
  - 解决方法：建立联合索引 就天然有序了
- using temporary 使用临时表 为了完成查询 得建立一张内部临时表来存放中间结果 用完之后要删除
  - distinct 去重： 数据无序的话 mysql就必须把数据都读到一个 带有唯一约束的临时表里 重复的插入不进去
	  - 解决方案：如果有索引 想用的记录挨在一起 遇到重复的就不输出 就不用临时表
  - 多表join 再order by：必须用临时表记录join结果 再使用using filesort进行文件排序 
	  - join操作 是一个双层for循环 拿外层循环的数据 遍历内层循环 找到where匹配的 做连接 外层叫做驱动表 内层叫做被驱动表。
	  - 如果orderby条件在驱动表上  并且驱动表做了索引 那么join后的数据一定是按照orderby条件有序 不会产生文件排序。其他情况都要文件排序 都是无序的
  - group by:聚合操作 在这个阶段 主要是由于group by无法利用索引完成分组操作。 比如接的是select gender count(\*) 就必须使用一个临时表 在临时表中完成分组 再计算count。
	  - 只要让gender属性走索引 就顺序读取索引树就好了


## 总结

1.先看type 
	如果是All 说明走了全盘扫描 优先考虑设计索引 避免全盘扫描
2.看key
	如果是null 说明完全没用索引 可能是索引设计错误
3.看rows
	也就是实际扫描的行树 如果rows很小 根本不需要优化。 rows实际上比type更有说明力。
4.看extra
	重点看有没有using filesort、using temporary 说明排序 分组 去重需要优化
5、结合sql语句分析
	看是不是可以设计联合索引