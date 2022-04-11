## multipart/form-data  和 application/x-www-form-urlencoded 的区别
* x-www-form-urlencoded 和 form-data 都可以用来发送表单数据。

* x-www-form-urlencoded 会把发送的内容中的非*ASCII*字符编码成3个字节的长度(URL编码)，因为二进制中的数据中的非数字字符都会被编码成3个字节,所以长度扩大了3倍，故不适合用来发送大数据和文件。图片等        
```text
//// x-www-form-urlencoded格式发送数据

key1=value1&key2=value21&key2=value22&key3=value3

```
* multipart/form-data: 不会对发送的二进制数据进行编码.同时发送的每个KEY-VALUE会按照分割符分割.都会有自己的header信息(适合发送比较大的数据):
```text

//// multipart/form-data格式发送数据

--[分隔符]
Content-Disposition: form-data; name="" \r\n\r\n
Content-Type: text/plain
[DATA]
--[分隔符]
Content-Disposition: form-data; name=""; filename="" \r\n\r\n
Content-Type:  text/plain
[DATA]
--[分隔符]
Content-Disposition: form-data; name="photo"; filename="photo.jpeg" \r\n\r\n
Content-Type: image/jpeg
[JPEG DATA]
--xyz--(最后一个分隔符,多了"--")

```

* 假设发送的表单数据为: name=John,age=2.按不同的表单格式发送,数据的格式如下:
```text
//// x-www-form-urlencoded格式发送数据
name=John&age=23


//// multipart/form-data格式发送数据 分隔符为 xyz

--xyz   \r\n
Content-Disposition: form-data; name="name" \r\n\r\n
Content-Type: text/plain

John
--xyz \r\n
Content-Disposition: form-data; name="age"  \r\n\r\n
Content-Type: text/plain

23

--xyz--

```

### 抓包验证
1.先发送一个数据格式为body为*form-data*格式的请求,用抓包工具抓取其数据格式:

![form-data](../../recource/images/form-data.png)

可以看到其data的格式如上面所示      


2. 先发送一个数据格式为body为*application/x-www-form-urlencoded*格式的请求,用抓包工具抓取其数据格式:

![form-data-urlencoded](../../recource/images/x-www-form-urlencode.png)         

可以看到数据格式为类似"query_string"



