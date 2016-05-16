# zdairi
zdairi is zeppelin CLI tool

Zeppelin REST API. see https://zeppelin.incubator.apache.org/docs/0.5.6-incubating/rest-api/rest-notebook.html

# Install
python setup.py install
or
pip install zdairi

# Usage

Support commands:

* create
* delete
* save
* print
* run
* restart_interpreter

Run zeppelin notebook/paragraph by id of name
```
zdairi run --url ${zeppelin_url} --notebook ${notebook_id|notebook_name} [--paragraph ${paragraph_id|paragraph_name}] [--parameters json]
```

Print zeppelin notebook as JSON
```
zdairi print --url ${zeppelin_url} --notebook ${notebook_id|notebook_name}
```

Create zeppelin notebook by .json/.nb
```
zdairi create --url ${zeppelin_url} --notebook ${file_path}
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

Delete zeppelin notebook by notebook_id or notebook_name
```
zdairi delete --url ${zeppelin_url} --notebook ${notebook_id|notebook_name}
```

Save zeppelin notebook as xxx.np
```
zdairi save --url ${zeppelin_url} --notebook ${notebook_id|notebook_name} --savepath ${filepath}
```

Restart zeppelin interpreter
```
zdairi restart_interpreter --url ${zeppelin_url} --interpreter ${interpreter_id|interpreter_name}
```
