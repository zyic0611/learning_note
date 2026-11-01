首先区别于常规Agent架构的三层记忆模式

一个loop需要有一个state 来保证任务的执行。（核心是因为llm是无状态的）

## 传统模式

也是我基础里的笔记中

state的构建是从本地持久化的history中恢复需要的会话历史 以及 长期记忆（向量库or摘要文本库）使用检索算法召回 构建出state 再投影到context。

长期 Memory（向量库/摘要）──检索──┐  
History（持久化对话）──恢复──→ State（内存运行态）──投影──→ Context

并且history是一个线性的对话历史 一般以文本的形式本地持久化。 长期记忆考检索算法注入。

## Pi

首先并没有单独的长期记忆memory 长期记忆就是session本身。 但是并不是检索式的 长期记忆只会做压缩 旧消息会直接被压缩 原文直接丢失 所以信息丢失就是丢失。 所以session里的摘要 必须保留路径、函数名等重要信息。

Session（唯一持久层，树）  
   │ 投影：选分支 + 压缩边界过滤  
   ↓  
Agent State（投影的副本 + 运行增量）  
   │   
   ↓  
Model Context（这一轮请求）

state的第一次构建 完全是由session投影而来 这是和常规模式最大的区别

context是由state构造而来 和常规模式一样

### session

可以理解为 session是完整的会话历史 想实现多轮对话 就需要有一个东西来保存完整历史 在常规模式中是history实现的。 在Pi中是Session来保存。

Session的核心作用并不是让模型记住更多的信息 而是让一次coding工作成为 可恢复 可导航 可审计的对象。

首先它支持中断恢复 但是这一点线性的history也支持。

特殊的 它的结构是 **追加式历史树** 支持 **分支能力** 是树状结构

它可以回退到某一步 并且保留旧路线 恢复的时候可以选择其中一条分支进行恢复 投影其分支为state 恢复agent运行态。

### state 、context

可以理解为 一个用户发出的消息对应一个loop 一个loop就需要有一个state来保证任务状态的记录 修改。因为一个loop里的一个turn是无状态的。

而一个turn送入llm的内容就是context 所以context就是一个state的投影。

所以开始一个loop的时候 会用session投影出一个state 然后开始loop

loop的每一个turn 都会用state构造一份context输入llm

llm的输出会改变state 也会写入session

因为state以session为主 如果发生更改分支、压缩 这两个操作会改变session

所以state此时就必须重新投影。