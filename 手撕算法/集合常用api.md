# 集合常用api

add()：  arraylist和hashset都是单值存储 所以是用add添加元素。

put() :	hashmap是把东西放在键上 用put

clear()：清空

size(): 	长度 

contains():	看是否包含这个值 arraylist和hashset都是单值存储

containsKey()：	hashmap 一般用key判断

remove(idx/obj):arraylist

remove(key):hashmap

remove(val):hashset

get(idx):arraylist

get(key):hashmap

hashset：无法取值 只能通过遍历或转数组



## **HashMap：**

- `map.getOrDefault(key, defaultVal)`：**力扣头号神技**。
  - 例子：计数时 `map.put(num, map.getOrDefault(num, 0) + 1)`。
- `map.keySet()`：获取所有的键（常用于遍历）。
- `map.entrySet()`：同时获取键和值（性能最好的遍历方式）。

## **ArrayList：**

- `list.set(index, val)`：修改指定位置的值。
- `list.add(index, val)`：在指定位置**插队**（后面元素后移）。
- `Collections.sort(list)`：给列表排序。

## **HashSet：**

- `set.add(val)` 的返回值是 **`boolean`**。
  - *妙用：* `if (!set.add(num))` 成立，说明 `num` 之前已经存在了，直接完成了“检查+存入”两步。