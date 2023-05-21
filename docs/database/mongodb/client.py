from pymongo import MongoClient
import datetime

def get_database():
    client = MongoClient('mongodb://admin:admin@localhost:27017/')
    # 创建数据库并返回
    return client['learn']

def get_cluster_database():
    client = MongoClient('mongodb://localhost:27017/')
    # 创建数据库并返回
    return client

def insert():
    print(datetime.datetime.now())
    db = get_cluster_database()
    collection = db.learn.test
    data = []
    for i in range(10000000):
        data.append({
            "record_index": i,
            "content":f"content_{i}",
            "created": datetime.datetime.now(),
            "list":[i]
        }
        )
    collection.insert_many(data)
    print(datetime.datetime.now())

def query():

    db = get_database()
    # 默认条件为 ==
    # res = db.test.find_one({"record_index": 1,"content":"content_1"}) # 等价于 record_index==1 and content=="content_1"
    # 运算符 field:{"$operator":value}
    # res = db.test.find_one({"record_index": {"$gt": 1}}) # 等价于 record_index>1
    # res= db.test.find_one({"record_index": {"$in": [1,2,3]}}) # 等价于 record_index in (1,2,3)
    # AND 和 OR
    ## AND 同个字典的多个键值对，都是AND关系    
    # res= db.test.find_one({"record_index": {"$in": [1,2,3]},"content":"content_1"}) # 等价于 record_index in (1,2,3)  and content=="content_1"
    ## OR 用$or关键字,条件为[{field,value}]的形式
    # res= db.test.find_one({"$or":[{"record_index": {"$in": [1,2,3]},"content":"content_1"},{"content":"content_12"}]}) # 等价于 (record_index in (1,2,3)  and content=="content_1") or content=="content_12"
    ## 联合使用 
    # res= db.test.find_one({"$or":[{"record_index": {"$in": [1,2,3]},"content":"content_1"},{"content":"content_12"}],"content":"content_1"}) 
    # 等价于 ((record_index in (1,2,3)  and content=="content_1") or content=="content_12") and content=="content_1"

    # 模糊查找 --> 使用正则表达式
    # res= db.test.find_one({"content": {"$regex": "content_1"}}) # 等价于 content like "%content_1%"   
    # res= db.test.find_one({"content": {"$regex": "^content_1"}}) # 等价于 content like "content_1%"  
    # res= db.test.find_one({"content": {"$regex": "content_1$"}}) # 等价于 content like "%content_1"

    # 只返回某些字段，在condition字典里面对字段设置为1，不返回，设置为0，返回
    # res= db.test.find_one({"content": {"$regex": "content_1$"}},{"content":1}) # 等价于select content from content like "%content_1"


    # 全文搜索.每个collection只能有一个全文索引
    # res= db.test.find({"$text": {"$search": "ss"}}) # 等价于select content from content like "%content_1343"
    # for r in res:
    #     print(r)


def createIndex():
    db = get_database()
    
    ## 创建单字段索引
    # db.test.create_index([("record_index",1)]) # 1表示升序，-1表示降序

    ## 创建复合索引
    # db.test.create_index([("record_index",1),("content",-1)]) # 1表示升序，-1表示降序

    ## 创建文本索引,一个collection只能有一个文本索引
    # db.test.create_index([("content","text")]) # 1表示升序，-1表示降序
    

def setSharedCollection():
    ## 设置分片,设置分片的话mongoDB必须以集群的方式部署
    db = get_cluster_database()
    db.admin.command("enableSharding","learn") # 开启分片
    db.admin.command("shardcollection","learn.test",key={"record_index":1}) # 设置分片字段

def aggregate():
    ...

# createIndex()
# query()
# setSharedCollection()
insert()