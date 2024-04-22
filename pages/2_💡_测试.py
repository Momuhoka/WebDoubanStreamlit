import os
import pickle
import time

import pandas as pd
import streamlit as st
# 自定义sensiment函数
from data.snownlp import streamlit_snownlp as streamsensiment
from stqdm import stqdm

# 设置全局属性
st.set_page_config(
    page_title='DEBUG测试',
    page_icon='💡',
    layout='wide'
)

# 缓存路径 ./cache
cachepath = "./cache"
if not os.path.exists(cachepath):
    os.mkdir(cachepath)

# 部分文件存储位置
datapath = "./data"
if not os.path.exists(f"{datapath}/snownlp"):
    os.mkdir(f"{datapath}/snownlp")


# n/名词 np/人名 ns/地名 ni/机构名 nz/其它专名
# m/数词 q/量词 mq/数量词 t/时间词 f/方位词 s/处所词
# v/动词 a/形容词 d/副词 h/前接成分 k/后接成分 i/习语
# j/简称 r/代词 c/连词 p/介词 u/助词 y/语气助词
# e/叹词 o/拟声词 g/语素 w/标点 x/其它

def read_data(_type: str, path: str):
    if _type == "csv":
        _data = pd.read_csv(path, index_col=0)
    elif _type == "pkl":
        with open(path, "rb") as _file:
            _data = pickle.load(_file)
    else:
        with open(path, mode="r", encoding="utf-8") as _file:
            _data = [line.strip('\n') for line in _file.readlines()]
    return _data


def save_file(star: int, _text: str):
    if star > 3:
        with open(f"{datapath}/snownlp/pos.txt", mode="a", encoding="utf-8") as _file:
            _file.write(f"{_text}\n")
    else:
        with open(f"{datapath}/snownlp/neg.txt", mode="a", encoding="utf-8") as _file:
            _file.write(f"{_text}\n")


with st.container(border=True):
    if st.button("生成好评/差评txt文件", use_container_width=True):
        s = time.time()

        data = read_data(_type="csv", path=f"{datapath}/cache.csv")
        data.index = data.index + 1
        data.rename_axis("序列", inplace=True)
        data = data.sample(frac=0.01)
        st.dataframe(data)
        holder = st.empty()
        stqdm(st_container=holder).pandas(desc="数据处理进度")
        data.progress_apply(lambda x: save_file(x["star"], x["comment"]), axis=1)
        e = time.time()
        holder.success("**成功生成数txt:** {:.2f}s".format(e - s), icon='✅')

# snownlp分析很慢
with st.container(border=True):
    if st.button("开始训练", use_container_width=True):
        pos_text = read_data(_type="txt", path=f"{datapath}/snownlp/pos.txt")
        neg_text = read_data(_type="txt", path=f"{datapath}/snownlp/neg.txt")
        with st.spinner("运行中..."):
            streamsensiment.train(f"{datapath}/snownlp/neg.txt", f"{datapath}/snownlp/pos.txt")
            streamsensiment.save(f"{datapath}/snownlp/sentiment.marshal")
        st.success("训练完毕")

if os.path.isfile(f"{datapath}/snownlp/sentiment.marshal"):
    text = st.chat_input("测试")
    with st.container(border=True):
        snownlp_model = streamsensiment.load(f"{datapath}/snownlp/sentiment.marshal")
        result = snownlp_model.sentiment(text)
        st.markdown(f'''> **输入:** {text}
> **结果:** {result}''')
