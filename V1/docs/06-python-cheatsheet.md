# 项目专属 Python 速查表(前端工程师视角)

> 只覆盖**本项目实际用到**的 Python 语法,全部配 JavaScript 对照。
> 目标:让你"能读会改",不求精通。看不懂的代码,先查这里。

---

## 一、最大的认知:Python 用缩进代替 `{}`

```python
# Python:冒号 + 缩进(通常 4 空格)表示代码块
def greet(name):
    if name:
        print(f"hello {name}")
    return name
```

```javascript
// JavaScript:花括号表示代码块
function greet(name) {
  if (name) {
    console.log(`hello ${name}`);
  }
  return name;
}
```

**关键**:Python 没有 `{}`、没有 `;`。缩进错了 = 语法错误。

---

## 二、基础语法对照

| 概念 | JavaScript | Python |
|------|-----------|--------|
| 变量 | `const x = 5` / `let x = 5` | `x = 5` |
| 常量 | `const X = 5` | `X = 5`(约定大写,但不强制) |
| 函数 | `function f(a) {}` | `def f(a):` |
| 箭头函数 | `(a) => a * 2` | `lambda a: a * 2` |
| 字典/对象 | `{ key: val }` | `{ "key": val }`(键要引号) |
| 数组/列表 | `[1, 2, 3]` | `[1, 2, 3]` |
| null | `null` / `undefined` | `None` |
| 布尔 | `true` / `false` | `True` / `False` |
| 与或非 | `&&` / `\|\|` / `!` | `and` / `or` / `not` |
| 模板字符串 | `` `${name}` `` | `f"{name}"` |
| 字符串拼接 | `"a" + "b"` | `"a" + "b"`(一样) |
| 注释 | `// xxx` | `# xxx` |
| 多行注释 | `/* xxx */` | `"""xxx"""` |
| 相等 | `===` | `==` |
| 不等 | `!==` | `!=` |

---

## 三、控制流

### if / else

```python
if x > 10:
    level = "high"
elif x > 5:          # 注意是 elif,不是 else if
    level = "mid"
else:
    level = "low"
```

```javascript
if (x > 10) {
  level = "high";
} else if (x > 5) {
  level = "mid";
} else {
  level = "low";
}
```

### for 循环

```python
for item in my_list:          # 遍历元素(像 for...of)
    print(item)

for i in range(10):           # 0 到 9(像 for i=0; i<10; i++)
    print(i)

for i, item in enumerate(my_list):   # 同时拿下标和元素
    print(i, item)
```

```javascript
for (const item of myList) { console.log(item); }
for (let i = 0; i < 10; i++) { console.log(i); }
myList.forEach((item, i) => console.log(i, item));
```

---

## 四、数组操作(最常用,重点看)

| 操作 | JavaScript | Python |
|------|-----------|--------|
| map | `arr.map(x => x*2)` | `[x*2 for x in arr]` |
| filter | `arr.filter(x => x>0)` | `[x for x in arr if x>0]` |
| 长度 | `arr.length` | `len(arr)` |
| 求和 | `arr.reduce((a,b)=>a+b)` | `sum(arr)` |
| 最大 | `Math.max(...arr)` | `max(arr)` |
| 最小 | `Math.min(...arr)` | `min(arr)` |
| 包含 | `arr.includes(x)` | `x in arr` |
| 添加 | `arr.push(x)` | `arr.append(x)` |
| 切片 | `arr.slice(0, 3)` | `arr[0:3]` 或 `arr[:3]` |
| 倒序最后一个 | `arr[arr.length-1]` | `arr[-1]` |

### "列表推导式"——Python 最常见的写法

```python
# 这行很常见,意思是:对 rows 里每个 r,取出 r.h2,组成新列表
gas_values = [r.h2 for r in rows]

# 带条件:只要异常的
abnormal = [r for r in rows if r.is_abnormal]
```

```javascript
const gasValues = rows.map(r => r.h2);
const abnormal = rows.filter(r => r.isAbnormal);
```

---

## 五、字典(对象)操作

```python
d = {"name": "T1", "h2": 12}

d["name"]               # 取值:"T1"
d.get("co", 0)          # 安全取值,不存在返回 0(像 d.co ?? 0)
d["new"] = 5            # 加键
"name" in d             # 判断键存在
d.keys()                # 所有键
d.values()              # 所有值
d.items()               # 键值对(用于 for k, v in d.items())
```

```javascript
const d = { name: "T1", h2: 12 };
d.name;
d.co ?? 0;
d.new = 5;
"name" in d;
Object.keys(d);
Object.values(d);
Object.entries(d);
```

---

## 六、本项目特有的东西

### 1. FastAPI 路由(≈ Express 路由)

```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/api/data")

@router.get("/overview")              # ≈ app.get("/api/data/overview")
def get_overview(db = Depends(get_db)):
    return {"status": "ok"}            # 自动转成 JSON 返回
```

- `@router.get(...)` 这种 `@` 开头的叫**装饰器**,理解为"给下面这个函数贴个标签"
- `Depends(get_db)` 是 FastAPI 的**依赖注入**:每次请求自动给你一个数据库连接
- 返回 `dict` 会**自动变成 JSON**,不用手动 `JSON.stringify`

### 2. SQLAlchemy 查询(≈ ORM,像 Prisma/TypeORM)

```python
from sqlalchemy import select, func

# 查总数:SELECT COUNT(*) FROM monitoring
total = db.execute(select(func.count()).select_from(Monitoring)).scalar()

# 查列表:SELECT * FROM monitoring WHERE transformer_id=1
rows = db.execute(
    select(Monitoring).where(Monitoring.transformer_id == 1)
).scalars().all()
```

对照(伪 SQL 思路即可):
```javascript
const total = await db.monitoring.count();
const rows = await db.monitoring.findMany({ where: { transformerId: 1 } });
```

- `.scalar()` = 取单个值(如 count 结果)
- `.scalars().all()` = 取一组对象
- `Monitoring.transformer_id == 1` 是查询条件,不是真的比较

### 3. 类型注解(可选,看到别怕)

```python
def f(name: str, age: int) -> dict:    # 冒号后是类型,-> 后是返回类型
    return {"name": name}
```

```typescript
function f(name: string, age: number): object {
  return { name };
}
```

**和 TypeScript 一个意思**,只是写法不同。Python 的类型注解**不强制**(写错了也能跑),纯粹帮助阅读。

### 4. f-string(模板字符串)

```python
name = "T1"
msg = f"变压器 {name} 的 H2 是 {h2:.2f} ppm"   # :.2f 表示保留 2 位小数
```

```javascript
const msg = `变压器 ${name} 的 H2 是 ${h2.toFixed(2)} ppm`;
```

---

## 七、怎么运行 Python(本项目)

```bash
cd BE
source .venv/bin/activate        # 激活虚拟环境(每次开新终端都要)

# 运行某个脚本(-m 是"以模块方式运行")
python -m scripts.eda
python -m scripts.synthesize_data

# 启动后端
uvicorn app.main:app --reload
```

- `.venv` 是**虚拟环境**,理解为这个项目专属的 `node_modules`
- `source .venv/bin/activate` ≈ 进入这个项目的依赖环境
- 装包:`pip install xxx`(≈ `npm install xxx`)
- `requirements.txt` ≈ `package.json` 的 dependencies

---

## 八、看到这些"陷阱"别慌

| 现象 | 解释 |
|------|------|
| `self` 到处出现 | 类的方法第一个参数,理解为 JS 的 `this`,固定写法 |
| `__init__` | 类的构造函数,≈ JS 的 `constructor` |
| `if __name__ == "__main__":` | "这个文件被直接运行时才执行",固定套路 |
| `from __future__ import ...` | Python 版本兼容,固定写在文件头,不用管 |
| `@dataclass` | 自动生成构造函数的类,≈ 简化版 class |
| `*args` / `**kwargs` | 不定参数,≈ JS 的 `...args` |
| `None` 报错 `NoneType` | 相当于 JS 的 `Cannot read property of undefined` |

---

## 九、遇到报错怎么办

1. **看最后一行**:Python 报错最关键的信息在**最后一行**(和 JS 相反)
2. **看 `File "xxx", line N`**:告诉你哪个文件第几行
3. **常见错误**:
   - `ModuleNotFoundError` → 包没装,`pip install`
   - `IndentationError` → 缩进错了
   - `KeyError` → 字典里没这个键
   - `AttributeError: NoneType` → 某个值是 None,却当对象用了
4. **直接把报错贴给我**,我帮你定位

---

## 十、心态

- 你**不需要**默写 Python,只需要**读懂 + 微调**
- 硬核算法(LSTM/Agent)我写,你理解流程
- 90% 的时候你改的是:**返回字段、参数数字、规则配置**
- 这些和改 JS 配置没区别

**Python 在本项目里是工具,不是考试科目。**
