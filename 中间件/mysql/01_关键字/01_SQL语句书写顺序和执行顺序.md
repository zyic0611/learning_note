

书写顺序：

`SELECT .. FROM..JOIN..ON..WHERE..GROUP BY .. HAVING..ORDER BY ..LIMIT..`

Mysql执行顺序

1 from & join。 确定数据来源 引擎会去磁盘or缓存找到对应的表 如果是多表连接 则根据on 把表连接成一个大的 虚拟基础表

2 where 粗加工过滤 把不符合条件的数据过滤掉    **由于此时还没进行分组 则不能使用sum count等针对组的聚合函数**

3 group by 按类分组 某一个字段的值来分组

4 having   针对分组后的数据进行条件过滤 可以使用聚合函数 比如说分组后的每一组数量count必须大于100  

5 select 提取所需要的字段 剔除不需要的列。  所以where不能使用select起的别名

6 order by  按照规则排序结果

7 limit 截取n个结果 剩下抛弃

