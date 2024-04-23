from time import sleep

import redis
import streamlit as st
import pandas as pd

data = pd.read_csv("data/douban_top250.txt", delimiter='\t', header=None)
st.dataframe(data, use_container_width=True)

redis_pool = redis.ConnectionPool(host='175.178.4.58', port=6379, password="momuhoka", decode_responses=True, db=3)


def insert2redis(value, dictinfo):
    retry_count = 3  # 尝试次数，使用多线程后可能导致同一时间存储大量数据
    # 一般数据库用的db0但是由于IP池使用了redis的db0，改为db1
    r = redis.Redis(connection_pool=redis_pool)
    while retry_count > 0:
        try:
            # redis默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令
            pipe = r.pipeline()
            for pair in dictinfo.items():  # 直接传递字典可能超过最大参数限制，通过看hset源码拆分传输
                pipe.hset(value, items=pair)  # 存储对应key值
            pipe.execute()  # pipe相当于缓存指令然后一口气发送，一定要加执行
            return True
        except Exception as e:
            retry_count -= 1
            print(f"\n数据库存储异常...\n相关信息: {value}-{dictinfo}\n{e}")
    print("redis连接异常，存储失败")
    return False


films = data[0].to_list()
film_pages = data[1].to_list()
film_summaries = data[2].to_list()
film_actors = data[3].to_list()
film_actor_names = data[4].to_list()
# st.table(films)
dict_lists = []
for index, film in enumerate(films):
    dict_lists.append({"cover": film_pages[index],
                       "summary": film_summaries[index],
                       "avatars": film_actors[index],
                       "names": film_actor_names[index]})

new_empty = st.empty()
if new_empty.button("开始存储", disabled=False):
    for film, dict_list in zip(films, dict_lists):
        new_empty.dataframe(dict_list)
        insert2redis(f"电影 : {film} : 封面", dict_list)
