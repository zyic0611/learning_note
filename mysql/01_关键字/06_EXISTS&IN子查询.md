# 子查询

子查询性能很差。 能用join尽量用join

比如相关子查询 

```mysql
-- 危险的写法（相关子查询）
SELECT * FROM users u 
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.id
);
```

采用的逻辑是先执行外层查询 查出所有的user 再对外层的每一行 去执行一次内层的子查询。

```mysql
-- 高效的写法（隐式驱动表优化）
SELECT DISTINCT u.* FROM users u 
INNER JOIN orders o ON u.id = o.user_id;
```

使用join

优化器自动介入 判断谁做驱动表 并且用INLJ算法 被驱动表走索引 只需要执行一次查询计划



## IN&EXISTS

核心依旧是小表驱动大表。

IN是先执行内层子查询 把结果拿出来 再执行外层 适合内表小 

EXISTS 反过来 先执行外面 再把外面的结果一行行带入内层去验证 适合外表小 内表大。