
遇到OOM 必须考 Dump文件和MAT工具 

遇到OOM宕机 排查思路为 事前配置 和事后分析

1. 在生产环境的JVM启动参加上 堆内存溢出的时候到处内存快照【dump文件
2. 拿到dump文件后导入MAT memory analyzer tool 分析
3. 先看leak suspects 内存泄漏嫌疑人报告 饼图
4. 看dominator tree支配树 找到内存排名前几名的 找到大对象【大list or 无界的阻塞队列
5. 查看gc roots 忽略弱引用和软引用  顺者强引用链 找到具体的java业务代码行号 解决问题