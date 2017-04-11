# zdairi
zdairi is zeppelin CLI tool which wrapper zeppelin REST API for control notebook and interpreter.

Zeppelin REST API. see https://zeppelin.apache.org/docs/0.7.0/rest-api/rest-notebook.html

## Support version

* Zeppelin 0.6
* Zeppelin 0.7

## Prerequisites

* Python 2.7

# Install
python setup.py install
or
pip install zdairi

# Configuration

Using zdari with yaml format config.
```bash
$ zdairi COMMAND                      #Using default path  '~/.zdari.yml'
$ zdairi -f /tmp/zdari.yml COMMAND    #Using specified path
```

Config example:
```
zeppelin_url: http://your_zeppelin_url  # Required
# Options
zeppelin_auth: true  #Default is false
zeppelin_user: user_name
zeppelin_password: user_password

```
We support specified user to login zeppelin.

# Usage

Support commands:

* Notebook
  * list
  * run
  * print
  * create
  * delete
  * save

* Interpreter
  * list
  * restart


## Notebook commands


### LIST command

List notebooks id and name

```
$ zdairi notebook list [--notebook ${notebook_id|notebook_name}]
```

Output example

```
$ zdairi notebook list 

id:[2C3XP3FS1], name:[my notebook1]
id:[2C9327A66], name:[my notebook2]
id:[2CFGUBJX2], name:[my notebook3]

```
```
$ zdairi notebook list --notebook "my notebook3"
id:[20170410-113013_1011211975], status:[FINISHED]
id:[20170410-113020_981608729], status:[FINISHED]
```


### RUN command

Run zeppelin notebook/paragraph by id of name
```
$ zdari notebook run --notebook ${notebook_id|$notebook_name} [--paragraph ${paragraph_id|$paragraph_name}] [--parameters ${json}]
```
Example
```
$ zdairi notebook run --notebook mynotebook --paragraph myparagraph --parameters '{ "params":{"forecastDate":"yoo"}}'
```

### PRINT command

Print zeppelin notebook as JSON
```
$ zdari notebook print --notebook ${notebook_id|$notebook_name}
```

### CREATE command

Create zeppelin notebook by .json/.nb
```
$ zdari notebook create --filepath ${filepath}
```

We support create notebook by zeppelin json format or our DSL format.

The format as below:

```
# ${notebook name}

############################################################   ${paragraph title}   ############################################################
${paragraph context}

############################################################   ${paragraph title}   ############################################################
${paragraph context}

```

```
# Test Notebook

############################################################   test_1   ############################################################
%spark
import org.apache.commons.io.IOUtils
import java.net.URL
import java.nio.charset.Charset
// load bank data
val bankText = sc.parallelize(
    IOUtils.toString(
        new URL("https://s3.amazonaws.com/apache-zeppelin/tutorial/bank/bank.csv"),
        Charset.forName("utf8")).split("\n"))
case class Bank(age: Integer, job: String, marital: String, education: String, balance: Integer)

val bank = bankText.map(s => s.split(";")).filter(s => s(0) != "\"age\"").map(
    s => Bank(s(0).toInt, 
            s(1).replaceAll("\"", ""),
            s(2).replaceAll("\"", ""),
            s(3).replaceAll("\"", ""),
            s(5).replaceAll("\"", "").toInt
        )
).toDF()
bank.registerTempTable("bank2")

############################################################   test_2   ############################################################
%pyspark
import os
print(os.environ['PYTHONPATH'])
count = sc.parallelize(range(1, 10000 + 1)).reduce(lambda x,y: x+y)
print("Pi is roughly %f" % (4.0 * count / 12))
accum = sc.accumulator(0)
sc.parallelize([1, 2, 3, 4]).foreach(lambda x: accum.add(x))
print(accum.value)

```

### DELETE command

Delete zeppelin notebook by notebook_id or notebook_name
```
$ zdari notebook delete --notebook ${notebook_id|$notebook_name}
```

### SAVE command
Save zeppelin notebook as xxx.np
```
$ zdari notebook save --notebook ${notebook_id|$notebook_name} --filepath $filepath
```


## Interpreter commands

### LIST command
List interpreters id and name

```
$ zdairi interpreter list
```

Output example
```
id:[2CBC3HCAX], name:[spark]
id:[2C9CZRM8P], name:[md]
id:[2CBBH2DVN], name:[angular]

```

Restart zeppelin interpreter
```
$ zdari interpreter restart --interpreter ${interpreter_id|$interpreter_name}
```
