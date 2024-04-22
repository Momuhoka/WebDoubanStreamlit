import collections
import os.path
import random
import re
import time

import numpy as np
import streamlit as st
import pandas as pd
import redis
import jieba
import plotly.express as px
from PIL import Image, ImageFont, ImageDraw
from wordcloud import WordCloud

# 图表部分用到本地缓存-缓存路径 ./cache
cachepath = "./cache"
if not os.path.exists(cachepath):
    os.mkdir(cachepath)

# 部分文件存储位置
datapath = "./data"
if not os.path.exists(datapath):
    os.mkdir(datapath)

# 设置全局属性
st.set_page_config(
    page_title='第三小组',
    page_icon='♾️',
    layout='wide'
)


# experimental_allow_widgets=True
# 允许在缓存函数中使用小部件。默认值为False
# 对缓存函数中的小部件的支持目前处于实验阶段
# 将此参数设置为 True 可能会导致内存使用过多，因为 widget 值被视为缓存的附加输入参数

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


@st.cache_data(ttl=600)
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


def film_cache(film: str, keysCache: dict, mode: bool):
    if not mode:
        if not os.path.isfile(f"{cachepath}/{film}/详情.xlsx"):
            infos_cache(db=3, film=film)
        if not os.path.isfile(f"{cachepath}/{film}/用户.xlsx"):
            users_cache(db=3, film=film, users=keysCache["用户"])
        if not os.path.isfile(f"{cachepath}/{film}/短评.xlsx"):
            scomms_cache(db=3, film=film, allshort=keysCache["短评"])
        if not os.path.isfile(f"{cachepath}/{film}/长评.xlsx"):
            fcomms_cache(db=3, film=film, allfull=keysCache["长评"])
    else:
        infos_cache(db=3, film=film)
        users_cache(db=3, film=film, users=keysCache["用户"])
        scomms_cache(db=3, film=film, allshort=keysCache["短评"])
        fcomms_cache(db=3, film=film, allfull=keysCache["长评"])


# 缓存大部分表格
def all_cache(_mode: bool):
    # 获取所有键值
    _keysCache = keys_cache(db=3)
    with st.sidebar:
        holder = st.empty()
        length = len(_keysCache["详情"])
        holder.progress(value=0, text=f"处理进度: 0/{length}")
        for _index, keys in enumerate(_keysCache["详情"]):
            holder.progress(value=(_index + 1) / length, text=f"处理进度: {_index + 1}/{length}")
            _film = keys.split(" : ")[1]  # 电影名
            film_cache(film=_film, keysCache=_keysCache, mode=_mode)
        holder.empty()


# 用于判断属地 - 常居地 > IP
LOCATIONS = ["河北", "山西", "辽宁", "吉林", "黑龙江", "江苏",
             "浙江", "安徽", "福建", "江西", "山东", "河南",
             "湖北", "湖南", "广东", "海南", "四川", "贵州",
             "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古",
             "广西", "西藏", "宁夏", "新疆", "北京", "天津",
             "上海", "重庆", "香港", "澳门"]


@st.cache_data(show_spinner="散点图生成中...")
def point_chart_module(data: pd.DataFrame):
    fig = px.scatter(
        data,
        x="估算年份",
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
def pie_chart_module(data: pd.DataFrame):
    # 使用altair创建饼图
    fig = px.pie(
        data,
        values="数目",
        names="地域",
        hover_name="地域",
        hole=0.4,
        title="用户评论分布")
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


# 默认渲染到主界面
st.title('豆瓣TOP250电影')
st.info('电影详情一览')
st.markdown('> st.cahce 缓存返回数据的函数-检查到更新才会刷新-请检查使用正误')

# 网页界面

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
    keysCache = keys_cache(db=3)

# 获取电影列表
films = [filmkey.split(" : ")[1] for filmkey in keysCache["详情"]]

film = st.selectbox(
    "电影列表", films, help="输入以搜索"
)

# 侧边栏+所有缓存任务
with st.sidebar:
    st.title("电影信息速览")
    # 模式
    with st.form("缓存操作:"):
        mode = st.toggle("强制覆盖", help="强制覆盖耗时更久", value=False)
        if st.form_submit_button("全部缓存",
                                 type="primary",
                                 use_container_width=True):
            # 全部缓存
            all_cache(_mode=mode)
    # 手动展开
    check = st.checkbox("查看缓存状态", value=False)
    cache_status = checkcache(film=film)
    # 展示缓存
    if check:
        # 显示缓存状态
        status = pd.DataFrame(cache_status).T \
            .rename_axis(index=film) \
            .rename(columns={0: "是否缓存", 1: "缓存时间"})
        st.dataframe(status, use_container_width=True)

# 得到电影后就可以开始缓存-放在all_cache之后
if not mode:
    film_cache(film=film, keysCache=keysCache, mode=False)

choice = st.selectbox(
    "选择", ["详情", "用户", "短评", "长评"]
)
chosen_str = f"电影 : {film} : {choice}"
chosen_keys = [key for key in keysCache[choice] if chosen_str in key]
desc = {
    "详情": f"{choice}-<{film}>",
    "用户": f"已收集{choice}信息: {len(chosen_keys)}",
    "短评": f"已收集{choice}信息: {len(chosen_keys)}",
    "长评": f"已收集{choice}信息: {len(chosen_keys)}"
}

# 显示选择的电影信息
# 这里一定要有缓存
values = read_excel(f"{cachepath}/{film}/{choice}.xlsx")
expander = st.expander(desc[choice])
expander.dataframe(values, use_container_width=True, hide_index=True)

# 图表的基础数据源
usersDf = read_excel(f"{cachepath}/{film}/用户.xlsx")
scommsDf = read_excel(f"{cachepath}/{film}/短评.xlsx")
fcommsDf = read_excel(f"{cachepath}/{film}/长评.xlsx")
# 评论拼接
fcommsDf.rename(columns={"full_comment": "comment"}, inplace=True)  # 拼接列名一致
sandfDf = pd.concat([scommsDf, fcommsDf], axis=0).astype(str)
comString = '|'.join(sandfDf["comment"].to_list())
# 用户ip处理
# IP异常用location填充
usersDf["ip"].fillna(usersDf["location"], inplace=True)
# ip置换
for ip in usersDf["ip"].astype(str):
    for pos in LOCATIONS:
        if pos in ip:
            usersDf["ip"].replace(ip, pos, inplace=True)
            break
# 过滤 nan
usersDf.dropna(axis=0, how="any", subset=["ip"], inplace=True)

tab_1, tab_2 = st.tabs(["电影评论", "电影云图"])
# 图表部分
with tab_1:
    col_1, col_2 = st.columns(spec=2)
    with col_1:
        # 取出对应电影数据 astype-float型转换成str
        ipList = usersDf["ip"].astype(str).to_list()
        # 词频统计
        ip_counts = dict(collections.Counter(ipList))  # 对IP做词频统计
        ipdata = pd.DataFrame({
            "地域": list(ip_counts.keys()),
            "数目": list(ip_counts.values())
        })
        with st.expander(f"<{film}>-饼图", expanded=True):
            fig1 = pie_chart_module(ipdata)
            st.plotly_chart(fig1, use_container_width=True)
    with col_2:
        idList = usersDf["id"].astype(str)
        yearList = usersDf["jointime"].to_list()
        hadseenList = usersDf["hadseen"].fillna(0).to_list()
        usersdata = pd.DataFrame({
            "ID": idList,
            "IP": ipList,
            "加入年份": yearList,
            "估算年份": [int(x[0:4]) + int(x[5:7]) / 12 + int(x[8:10]) / 30 for x in yearList],
            "看过电影": hadseenList
        })
        with st.expander(f"<{film}>-散点图", expanded=True):
            fig2 = point_chart_module(usersdata)
            st.plotly_chart(fig2, use_container_width=True)
# 词云部分
with tab_2:
    if not os.path.isfile(f"{datapath}/new_stopwords.txt"):
        st.markdown(f"# 在{datapath}没有找到new_stopwords.txt文件")
    else:
        co1, co2 = st.columns(spec=[0.6, 0.4])
        stopwords = read_txt(f"{datapath}/new_stopwords.txt")
        words = word_filter(comstring=comString, name=film, stopwords=stopwords)
        # 词频统计
        word_counts = collections.Counter(words)  # 对分词做词频统计
        word_counts_top = word_counts.most_common(20)  # 获取最高频的词
        with co2:
            if st.button("重新生成词云图",
                         type="primary",
                         use_container_width=True):
                os.remove(f"{cachepath}/{film}/词云.png")
                # 清除st.cahce_data的图片缓存
                word_clouds.clear()
            # 高频词展示
            wordTop = pd.DataFrame(word_counts_top).rename(
                columns={0: "分词", 1: "频次"})
            st.dataframe(wordTop, use_container_width=True, hide_index=True)
            st.info("词云图背景以第一个高频中文词决定", icon="ℹ️")
        with co1:
            with st.expander(f"<{film}>-词云图", expanded=True):
                if not os.path.isfile(f"{cachepath}/{film}/词云.png"):
                    # 调用函数+缓存
                    fig = word_clouds(words=words, hotwords=word_counts_top)
                    st.image(fig)
                    if not os.path.exists(f"{cachepath}/{film}"):
                        os.mkdir(f"{cachepath}/{film}")
                    fig.save(f"{cachepath}/{film}/词云.png")
                else:  # 存在词云文件
                    # 读取词云图
                    st.image(f"{cachepath}/{film}/词云.png")
