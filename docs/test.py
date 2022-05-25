import sqlite3
#创建连接
con = sqlite3.connect(":memory:")

# 允许加载扩展
con.enable_load_extension(True)

# 加载csv扩展
con.execute("select load_extension('csv.so');")
#禁止加载扩展
con.enable_load_extension(False)

sql="""
drop table if exists diamonds;
CREATE VIRTUAL TABLE temp.diamonds USING csv(filename='/Users/steven/data/diamonds.txt',header=1);
"""
#执行SQL脚本（多条语句）
con.executescript(sql)

#查看diamonds表结构
for row in con.execute("PRAGMA table_info(diamonds);"):
    print(row)
#把钻石售价按5000美金一档汇总数量（仅是测试）
for row in con.execute("select price/5000,count(*) from diamonds group by 1"):
    print(row)
con.close()