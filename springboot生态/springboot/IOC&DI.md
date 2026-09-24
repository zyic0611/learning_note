

## 没有依赖注入 

需要一个对象 就需要实例化一个对象。

带来高度耦合的问题：

- xxservice服务层 既需要写业务逻辑 又需要制造一个xx对象 
- 并且制造对象就必然带来需要构造函数 构造函数需要传参数
- 如果xx的对象的内容变了 或者构造函数的参数变了
- 就必须修改xx对象的代码 并且还要去修改服务层的new的构造参数

## 使用DI

需要什么 只需要使用@Autowired注解 

springboot启动并且实例化xxservice 看到这个注解

就会去容器内找到对应的依赖 自动注入到这个变量里



- 依赖  service需要xx bean才能工作 这个bean就是其依赖
- 注入 不需要手动new对象 spring框架把依赖bean从容器内取出来 注入变量

优点：

解耦： 业务逻辑只需要做自己的事 组件的创建和组装 全部由spring容器实现。



## IOC

inversion of control

- 正转：需要对象 手动new 则控制权在具体的业务对象里
- 反转： 把创建和管理对象的控制权 交给了spring容器 只需要 写一个@autowired注解 需要什么 spring框架就给什么 



## 关联

IOC是思想 DI是实现



## DI的实际使用

### 使用字段注入

也就是直接把注解写在字段上

```java
@Service
public class xxService{
  @Autowired
  private XX xx
}
```



### 构造器赋值

```java
// 加上 final，必须在实例化时赋值
    private final BailianClient client;

    // 用构造方法来接收大管家送来的依赖
    // (在 Spring 4.3 之后，如果只有一个构造方法，@Autowired 甚至可以省略不写！)
    public AgentService(BailianClient client) {
        this.client = client;
    }
```

1. 加上final关键字配合构造方法 保证service对象一旦被创建出来 它的依赖保证非空 
2. 由于是final 保证不能被别人修改 
3. 字段注入是通过反射塞进去的 做不到
4. 方便单元测试 不启动整个springboot环境下测试 则client没有赋值【Spring容器里没东西 因为没启动 给不了依赖。 如果是构造期注入 随便写一个假的client传进去就行，方便解偶

autowired如果不省略 是写在构造方法上 

final的实例变量 必须在对象创建完成之前 也就是构造函数执行之前 被显式的赋值。

spring会先去拿依赖 再通过构造函数赋值。



## DI的注解拓展

### 与@Resouce的区别

@Autowired

- 是spring框架的 离开spring就没用了
- 是按类型查找 如果容器里有两个实现了统一接口的类 那么就不知道给哪一个bean了



@Resouce

- 是java官方标准
- 按名字查找 只有名字找不到 才退化为按类型查找



### @RequiredArgsConstructor

构造期+final关键字太麻烦了 

Lombok提供的 只需要在类前+这个注解

里面只需要写private final XX xx字段

构造函数会自动写好 lombok在编译的时候自动生成构造函数

