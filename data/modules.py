import os
import random
import re
import time
import jieba
import numpy as np
import redis

import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image, ImageFont, ImageDraw
from streamlit_option_menu import option_menu
from wordcloud import WordCloud

# 页面字典
pages_dict = {"主页": "main.py", "模型": "pages/model.py",
              "电影信息一览": "pages/analysis.py", "电影整体分析": "pages/jared_.py",
              "电影球云图": "pages/hua_.py", "工具": "pages/settings.py"}


# 初始化
def initialize():
    if not os.path.exists(cachepath):
        os.mkdir(cachepath)
    if not os.path.exists(datapath):
        os.mkdir(datapath)


# 图表部分用到本地缓存-缓存路径 ./cache
cachepath = "./cache"
# 部分文件存储位置
datapath = "./data"


# 读取本地缓存文件
def read_excel(filepath: str):
    data = pd.read_excel(filepath)
    return data


def read_txt(filepath: str):
    with open(filepath, mode="r", encoding="utf-8") as file:
        # 要注意回车符号-strip会删除左右的特殊字符-不能为空!
        data = [line.strip('\n') for line in file.readlines()]
    return data


# 返回数据库值
@st.cache_data(ttl=300)
def get_value(_r: redis.Redis, key: str):
    keys = _r.hkeys(key)
    vals = _r.hvals(key)
    result = pd.Series(data=list(vals), index=list(keys))
    return result


# 返回大量值
@st.cache_data(ttl=300)
def get_values(_r: redis.Redis, keys: list):
    pipe = _r.pipeline()
    for key in keys:
        pipe.hkeys(key)
        pipe.hvals(key)
    result = pipe.execute()
    allkeys = result[0::2]
    allvals = result[1::2]
    data = [dict(zip(keys, vals))
            for keys, vals in zip(allkeys, allvals)]
    data = pd.DataFrame(data)
    return data


# 返回数据库连接，是不可迭代的，需要cahce_resource
@st.cache_resource
def init_connection(db: int):
    # 连接指定数据库，记得关闭
    redis_pool = redis.ConnectionPool(
        host='175.178.4.58',
        port=6379,
        password="momuhoka",
        decode_responses=True,
        db=db)
    return redis.Redis(connection_pool=redis_pool)


# 键值缓存
@st.cache_data(ttl=600,
               show_spinner="获取键值中...")
def keys_table(_r: redis.Redis, allkeys: list):
    films, users, allshort, allfull = [], [], [], []
    # key 分类
    for allkey in allkeys:
        if "详情" in allkey:
            films.append(allkey)  # 电影详情key
        elif "用户" in allkey:
            users.append(allkey)  # 用户信息key
        elif "短评" in allkey:
            allshort.append(allkey)  # 电影短评key
        elif "长评" in allkey:
            allfull.append(allkey)  # 电影长评key
    return films, users, allshort, allfull


@st.cache_data(ttl=300)
def users_df(_r: redis.Redis, userskeys: list):
    users_dataframe = get_values(_r=_r, keys=userskeys)
    users_dataframe = users_dataframe.set_index("id")
    return users_dataframe


@st.cache_data(ttl=300)
def scomms_df(_r: redis.Redis, scommkeys: list):
    scomms_dataframe = get_values(_r=_r, keys=scommkeys)
    _cid = [_id.split(" : ")[3] for _id in scommkeys]
    scomms_dataframe = scomms_dataframe.set_index(pd.Index(_cid).astype(str)).rename_axis("用户")
    return scomms_dataframe


@st.cache_data(ttl=300)
def fcomms_df(_r: redis.Redis, fcommkeys: list):
    fcomms_dataframe = get_values(_r=_r, keys=fcommkeys)
    _cid = [_id.split(" : ")[3] for _id in fcommkeys]
    fcomms_dataframe = fcomms_dataframe.set_index(pd.Index(_cid).astype(str)).rename_axis("用户")
    return fcomms_dataframe


@st.cache_data(ttl=600, show_spinner="下载键值中...")
def keys_cache(db: int):
    with init_connection(db=db) as r:
        allkeys: list[str] = r.keys()
        films, users, allshort, allfull = keys_table(_r=r, allkeys=allkeys)
        # 合并处理
        keysCache = ['|'.join(films), '|'.join(users), '|'.join(allshort), '|'.join(allfull)]
        # 缓存文件
        with open(f"{cachepath}/键值.txt", mode='w', encoding="utf-8") as keysfile:
            keysfile.write('\n'.join(keysCache))
    return {"详情": films, "用户": users, "短评": allshort, "长评": allfull}


# engine='xlsxwriter' 去除非法字符防止read报错
@st.cache_data(ttl=300)
def infos_cache(db: int, film: str):
    with init_connection(db=db) as r:
        # 缓存文件夹
        if not os.path.exists(f"{cachepath}/{film}"):
            os.mkdir(f"{cachepath}/{film}")
        infosDf = get_value(_r=r, key=f"电影 : {film} : 详情")
        infosDf = infosDf.rename_axis("类别").rename(index="信息")
        # 缓存文件
        # 换用xlsxwriter去除非法字符
        infosDf.to_excel(f"{cachepath}/{film}/详情.xlsx", engine='xlsxwriter')
    return infosDf


@st.cache_data(ttl=300)
def users_cache(db: int, film: str, users: list):
    with init_connection(db=db) as r:
        # 缓存文件夹
        if not os.path.exists(f"{cachepath}/{film}"):
            os.mkdir(f"{cachepath}/{film}")
        ukeys = [ukey for ukey in users if film in ukey]
        usersDf = users_df(_r=r, userskeys=ukeys)
        # 缓存文件
        usersDf.to_excel(f"{cachepath}/{film}/用户.xlsx", engine='xlsxwriter')
    return usersDf


@st.cache_data(ttl=300)
def scomms_cache(db: int, film: str, allshort: list):
    with init_connection(db=db) as r:
        # 缓存文件夹
        if not os.path.exists(f"{cachepath}/{film}"):
            os.mkdir(f"{cachepath}/{film}")
        sckeys = [sckey for sckey in allshort if film in sckey]
        scommsDf = scomms_df(_r=r, scommkeys=sckeys)
        # 缓存文件
        scommsDf.to_excel(f"{cachepath}/{film}/短评.xlsx", engine='xlsxwriter')
    return scommsDf


@st.cache_data(ttl=300)
def fcomms_cache(db: int, film: str, allfull: list):
    with init_connection(db=db) as r:
        # 缓存文件夹
        if not os.path.exists(f"{cachepath}/{film}"):
            os.mkdir(f"{cachepath}/{film}")
        fckeys = [fckey for fckey in allfull if film in fckey]
        fcommsDf = fcomms_df(_r=r, fcommkeys=fckeys)
        # 缓存文件
        fcommsDf.to_excel(f"{cachepath}/{film}/长评.xlsx", engine='xlsxwriter')
    return fcommsDf


# 检查缓存状态-实时更新: 不能st.cache_data
def checkcache(film: str):
    def file_with_time(path: str):
        if os.path.isfile(path=path):
            return [True, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(path)))]
        else:
            return [False, None]

    films_status = file_with_time(f"{cachepath}/{film}/详情.xlsx")
    users_status = file_with_time(f"{cachepath}/{film}/用户.xlsx")
    allshort_status = file_with_time(f"{cachepath}/{film}/短评.xlsx")
    allfull_status = file_with_time(f"{cachepath}/{film}/长评.xlsx")
    cache_bool_table = {
        "详情": films_status,
        "用户": users_status,
        "短评": allshort_status,
        "长评": allfull_status
    }
    return cache_bool_table


def film_cache(_db: int, film: str, keysCache: dict, mode: bool):
    if not mode:
        if not os.path.isfile(f"{cachepath}/{film}/详情.xlsx"):
            infos_cache(db=_db, film=film)
        if not os.path.isfile(f"{cachepath}/{film}/用户.xlsx"):
            users_cache(db=_db, film=film, users=keysCache["用户"])
        if not os.path.isfile(f"{cachepath}/{film}/短评.xlsx"):
            scomms_cache(db=_db, film=film, allshort=keysCache["短评"])
        if not os.path.isfile(f"{cachepath}/{film}/长评.xlsx"):
            fcomms_cache(db=_db, film=film, allfull=keysCache["长评"])
    else:
        infos_cache(db=_db, film=film)
        users_cache(db=_db, film=film, users=keysCache["用户"])
        scomms_cache(db=_db, film=film, allshort=keysCache["短评"])
        fcomms_cache(db=_db, film=film, allfull=keysCache["长评"])


# 缓存大部分表格
def all_cache(_db: int, _mode: bool):
    # 获取所有键值
    _keysCache = keys_cache(db=_db)
    with st.sidebar:
        holder = st.empty()
        length = len(_keysCache["详情"])
        holder.progress(value=0, text=f"处理进度: 0/{length}")
        for _index, keys in enumerate(_keysCache["详情"]):
            holder.progress(value=(_index + 1) / length, text=f"处理进度: {_index + 1}/{length}")
            _film = keys.split(" : ")[1]  # 电影名
            film_cache(_db=_db, film=_film, keysCache=_keysCache, mode=_mode)
        holder.empty()


@st.cache_data(show_spinner="散点图生成中...")
def point_chart_module(data: pd.DataFrame):
    fig = px.scatter(
        data,
        x="加入年份",
        y="IP",
        size="看过电影",
        color="看过电影",  # 区分颜色
        color_continuous_scale=px.colors.sequential.OrRd,
        hover_name="ID",
        hover_data="加入年份",
        log_x=True,
        size_max=50,
    )
    return fig


@st.cache_data(show_spinner="饼图生成中...")
def pie_chart_module(data: pd.DataFrame,titles:str):
    # 使用altair创建饼图
    column_name = data.columns[0]
    fig = px.pie(
        data,
        values="数目",
        names=column_name,
        hover_name=column_name,
        hole=0.4,
        title=titles)
    fig.update_traces(
        textposition='inside',  # 显示在里面
        textinfo='label+percent'  # 标签名+百分比
    )
    return fig

@st.cache_data(show_spinner="字符过滤中...")
def word_filter(comstring: str, name: str, stopwords: list):
    # 评论处理
    pattern = re.compile(r"[^\u4e00-\u9fa5^a-zA-Z]")  # 滤除非中英文字符
    word_string = pattern.sub('', comstring)
    # jieba分词
    words_list = jieba.lcut(word_string)
    # 筛选掉停用词 电影本名也加入停用
    stopwords.append(name)
    stopwords.extend(jieba.lcut(name))
    _words = [word for word in words_list
              if word not in stopwords]
    return _words


# 词云处理
@st.cache_data(show_spinner="词云图生成中...")
def word_clouds(words: list, hotwords: list):
    keywords = ' '.join(words)
    # 生成整个电影数据集的词云图
    font_path = f"{datapath}/fonts/LXGWWenKai-Regular.ttf"
    # 取第一个高频的中文词
    text = hotwords[0][0]
    pattern = re.compile(r"[\u4e00-\u9fa5]")
    for hotword in hotwords:
        if re.match(pattern, hotword[0]):
            text = hotword[0]
            break
    # 字体大小
    size = 1000
    # 背景图画布颜色
    background = Image.new("RGB", (int(size * 1.1), size), (255, 255, 255))
    dr = ImageDraw.Draw(background)
    # 字体样式
    font = ImageFont.truetype(
        f"{datapath}/fonts/HanYiChaoCuHeiJian-1.ttf",
        int(size / len(text)))
    # 文字颜色
    dr.text((size * 0.1 / 2, (size - size / len(text)) / 2), text, font=font, fill="#000000")
    # 加载背景图
    graph = np.array(background)
    # 生成词云
    wordcloud = WordCloud(
        width=int(size * 1.1),
        height=size,
        font_path=font_path,
        background_color="white",
        mask=graph,
        colormap=random.choice(["copper", "autumn", "summer", "winter", "cividis", None])
    ).generate(keywords)  # 使用筛选后的关键词生成词云
    # 转化为图片数据
    wcImage = wordcloud.to_image()
    return wcImage


# 自定义的page菜单
def diy_menu(_page: str, _page_dict: dict) -> None:
    pages = list(_page_dict.keys())
    page = option_menu(None, pages,
                       icons=['house', 'cloud-upload', "list-task", 'activity', 'back', 'gear'],
                       menu_icon="cast", default_index=pages.index(_page), orientation="horizontal")
    if page != _page:
        st.switch_page(_page_dict[page])

def get_keysCache(_db: int):
    # 只读取键值缓存
    if os.path.isfile(f"{cachepath}/键值.txt"):
        # 文件信息需要拆分
        keysString = read_txt(f"{cachepath}/键值.txt")
        keysCache = {}
        # 列表的字典 {x: [a,b,c...], y: [d,e,f...]...}
        for index, keyString in zip(["详情", "用户", "短评", "长评"], keysString):
            keysList = keyString.split('|')
            keysCache[index] = keysList
    else:
        # 列表的字典 {x: [a,b,c...], y: [d,e,f...]...}
        keysCache = keys_cache(db=_db)
    return keysCache

