import os
import pickle
import re

import numpy as np
import pandas as pd
import streamlit as st

# 缓存路径 ./cache
cachepath = "./cache"

# 部分文件存储位置
datapath = "./data"


@st.cache_data(ttl=300,  # Cache data for 5 min (=300 seconds)
               show_spinner="检查数据文件状态...")
def checkdatafile(path: str):
    walkers = os.listdir(path)
    filespath = [f"{path}/{walker}" for walker in walkers if not os.path.isfile(f"{path}/{walker}")]
    for _filepath in filespath:
        if not os.path.isfile(f"{_filepath}/短评.xlsx"):
            return f"{_filepath}/短评.xlsx", False
        if not os.path.isfile(f"{_filepath}/长评.xlsx"):
            return f"{_filepath}/长评.xlsx", False
    return filespath, True


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


def create_data(_filespath: list):
    _data = pd.DataFrame()
    # 加载数据集
    holder = st.empty()
    _length = len(_filespath)
    holder.progress(value=0, text=f"数据合成中: 0/{_length}")
    for index, _filepath in enumerate(_filespath):
        holder.progress(value=(index + 1) / _length, text=f"数据合成中: {index + 1}/{_length}")
        scommsDf = pd.read_excel(f"{_filepath}/短评.xlsx")
        # fcommsDf = pd.read_excel(f"{_filepath}/长评.xlsx")
        # 评论拼接
        # fcommsDf.rename(columns={"full_comment": "comment"}, inplace=True)  # 拼接列名一致
        # sandfDf = pd.concat([scommsDf, fcommsDf], axis=0).astype(str)
        sandfDf = scommsDf.astype(np.str_)
        # 评论处理
        pattern = re.compile(r"[^\u4e00-\u9fa5^a-zA-Z]")  # 需要的字符
        sandfDf["comment"] = sandfDf["comment"].apply(lambda x: pattern.sub(' ', x))
        # 过滤无效分数
        sandfDf.dropna(subset=['star'], axis=0, inplace=True)
        sandfDf.drop(sandfDf[sandfDf['star'].astype(float) < 0.0].index, inplace=True)
        # dataframe拼接
        _data = pd.concat([_data, sandfDf], axis=0)
    holder.empty()
    _data.to_csv(f"{datapath}/cache.csv")
    return _data


def sample_data():
    _data = read_data(_type="csv", path=f"{datapath}/cache.csv")
    with st.status("分类中...") as running:
        neg_data = _data[_data["star"] < 3]
        st.write(f"NEG长度: *:orange[{len(neg_data)}]*")
        neu_data = _data[_data["star"] == 3]
        st.write(f"NEU长度: *:orange[{len(neu_data)}]*")
        pos_data = _data[_data["star"] > 3]
        st.write(f"POS长度: *:orange[{len(pos_data)}]*")
        running.update(label="分类完毕", state="complete")
    _min_len = min(min(len(neg_data), len(neu_data)), len(pos_data))
    return neg_data.sample(_min_len), neu_data.sample(_min_len), pos_data.sample(_min_len)


if st.button("合成数据", use_container_width=True):
    walkers = os.listdir(cachepath)
    filespath = [f"{cachepath}/{walker}" for walker in walkers if not os.path.isfile(f"{cachepath}/{walker}")]
    data = create_data(filespath)
    st.success(f"**已保存至:** :blue[{datapath}/cache.csv] **长度:** :orange[{len(data)}]")
    show_data = data.reset_index(drop=True).rename_axis("序列")
    show_data.index = show_data.index + 1
    st.dataframe(show_data, use_container_width=True)

with st.container(border=True):
    frac = st.select_slider("**训练数据占比**", value=0.2, options=[0.1, 0.2, 0.3, 0.4, 0.5])
    neg_data, neu_data, pos_data = sample_data()
    min_len = min(min(len(neg_data), len(neu_data)), len(pos_data))
    data = pd.concat([neg_data, neu_data, pos_data], axis=0)
    if st.button("保存/覆盖至new_cache.csv", use_container_width=True):
        data.to_csv(f"{datapath}/new_cache.csv")
        st.success(f"**已保存至:** :blue[{datapath}/new_cache.csv] **长度:** :orange[{len(data)}]")
