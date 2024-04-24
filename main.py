import collections
import os
import random

import pandas as pd
import streamlit as st
import requests
import streamlit_shadcn_ui as ui
from stqdm import stqdm
from streamlit_image_select import image_select
from streamlit_star_rating import st_star_rating

from data.modules import diy_menu, pages_dict, cachepath, read_txt, read_excel, \
    pie_chart_module, point_chart_module, datapath, word_filter, word_clouds, initialize, init_connection, get_value, \
    get_values, all_cache, checkcache, film_cache, get_keysCache

# 初始化
initialize()

# 默认数据库
DB = 3

# 默认模式
MODE = False

# 设置全局属性
st.set_page_config(
    page_title='豆瓣宇宙',
    page_icon='♾️',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# 页面菜单
diy_menu(_page="主页", _page_dict=pages_dict)

# 只读取键值缓存
keysCache = get_keysCache(_db=DB)

# 获取电影列表
films = [filmkey.split(" : ")[1] for filmkey in keysCache["详情"]]
selected_films = st.multiselect(label="搜索电影", options=films, default=None)
if not selected_films:
    selected_films = films


# 获取封面相关信息
def get_covers(_db: int):
    try:
        with init_connection(db=_db) as _r:
            result = get_values(_r=_r, keys=[f"电影 : {_} : 封面" for _ in selected_films])
    except Exception as e:
        st.error(f"{e}\n数据库连接失败")
    return result


all_data = get_covers(_db=DB)
image_urls = all_data["cover"]
# image_urls = ["https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp",
#               "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2561716440.webp",
#               "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p2372307693.webp"]
avatar_urls = all_data["avatars"]
avatar_names = all_data["names"]

# 侧边栏+所有缓存任务
with st.sidebar:
    st.title("电影信息速览")
    # 模式
    with st.container(border=True):
        st.markdown("#### 缓存操作: ####")
        MODE = st.toggle("强制覆盖", help="强制覆盖耗时更久", value=False)
        if st.button("全部缓存",
                     type="primary",
                     use_container_width=True):
            # 全部缓存
            all_cache(_db=DB, _mode=MODE)


# 发起GET请求获取图片内容
@st.cache_data(show_spinner="正在获取封面...", ttl=300)
def  get_cover(url: str, _film: str, mode: bool):
    if not os.path.exists(f"{cachepath}/{_film}"):
        # 判断目录是否存在，不存在则创建
        os.mkdir(f"{cachepath}/{_film}")
    if not os.path.exists(f"{cachepath}/{_film}/images"):
        os.mkdir(f"{cachepath}/{_film}/images")
    # mode=True 强制覆盖刷新封面缓存
    if not os.path.exists(f"{cachepath}/{_film}/images/cover.jpg") or mode:
        response = requests.get(url)
        with open(f"{cachepath}/{_film}/images/cover.jpg", 'wb') as f:
            f.write(response.content)
    Image_path = f"{os.getcwd()}/cache/{_film}/images/cover.jpg"
    return Image_path


# @st.cache_data(show_spinner="正在获取头像...")
# def get_avatars(urls: list[str], _film: str):
#     Image_paths = []
#     if not os.path.exists(f"{cachepath}/{_film}"):
#         # 判断目录是否存在，不存在则创建
#         os.mkdir(f"{cachepath}/{_film}")
#     if not os.path.exists(f"{cachepath}/{_film}/images"):
#         os.mkdir(f"{cachepath}/{_film}/images")
#     for url in urls:
#         response = requests.get(url)
#         if not os.path.exists(f"{cachepath}/{_film}/images/{urls.index(url)}.jpg"):
#             with open(f"{cachepath}/{_film}/images/{urls.index(url)}.jpg", 'wb') as f:
#                 f.write(response.content)
#         Image_paths.append(f"{os.getcwd()}\\cache\\{_film}\\images\\{urls.index(url)}.jpg")
#     return Image_paths

col_1, col_2 = st.columns(spec=[0.25, 0.75])

cover_paths = []
# 获取所有图片
for film in stqdm(selected_films, desc="进度"):
    url = image_urls[selected_films.index(film)]
    try:
        cover_paths.append(get_cover(url=url, _film=film, mode=False))
    except Exception as e:
        st.write(f"{e}\n{film}")
        break

# 选择电影
film_index = image_select(
    label="选择电影",
    images=cover_paths,
    use_container_width=False,
    captions=selected_films,
    return_value="index",
)
film = selected_films[film_index]

# 缓存信息
with st.sidebar:
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
film_cache(_db=DB, film=film, keysCache=keysCache, mode=MODE)
# mode=True 时以防万一覆盖图片
get_cover(url=image_urls[selected_films.index(film)], _film=film, mode=MODE)

# 图表的基础数据源
usersDf = read_excel(f"{cachepath}/{film}/用户.xlsx")
scommsDf = read_excel(f"{cachepath}/{film}/短评.xlsx")
fcommsDf = read_excel(f"{cachepath}/{film}/长评.xlsx")
# 评论拼接
fcommsDf.rename(columns={"full_comment": "comment"}, inplace=True)  # 拼接列名一致
sandfDf = pd.concat([scommsDf, fcommsDf], axis=0).astype(str)
comString = '|'.join(sandfDf["comment"].to_list())
# 用户ip处理
# 用于判断属地 - 常居地 > IP
LOCATIONS = ["河北", "山西", "辽宁", "吉林", "黑龙江", "江苏",
             "浙江", "安徽", "福建", "江西", "山东", "河南",
             "湖北", "湖南", "广东", "海南", "四川", "贵州",
             "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古",
             "广西", "西藏", "宁夏", "新疆", "北京", "天津",
             "上海", "重庆", "香港", "澳门"]
# IP异常用location填充
usersDf.fillna({"ip": usersDf["location"]}, inplace=True)
# ip置换
for ip in usersDf["ip"].astype(str):
    for pos in LOCATIONS:
        if pos in ip:
            usersDf["ip"].replace(ip, pos, inplace=True)
            break
# 过滤 nan
usersDf.dropna(axis=0, how="any", subset=["ip"], inplace=True)

with col_1:
    with st.container(border=True):
        st.write(cover_paths[film_index], os.path.isfile(cover_paths[film_index]))
        st.image(cover_paths[film_index], use_column_width=True)
with col_2:
    try:
        with init_connection(db=DB) as r:
            value = get_value(_r=r, key=f"电影 : {film} : 详情")
    except Exception as e:
        st.error(f"{e}\n数据库连接失败")
    col_2_1, col_2_2 = st.columns(spec=[0.7, 0.3])
    with col_2_1:
        st.markdown(f"#### 🎞️{selected_films[film_index]}")
        st.markdown(f"**🗳投票数: {value['votes']}**  **🍿类型: {value['filmtype']}**"
                    f"  **📀年份: {value['year']}**  **⌛时长: {value['times']}min**"
                    f"  **📜语言: {value['language']}**")
        tab = ui.tabs(options=["简介", "评论", "分析", "词云"], default_value="简介")
    with col_2_2:
        st_star_rating(label="推荐指数:", maxValue=5, defaultValue=round(float(value["score"]) / 2), read_only=True)
        if tab == "评论":
            comm_sel = st.selectbox(label="**随机评论:**", options=["短评", "长评"])
        if tab == "词云":
            if st.button("重新生成词云图",
                         type="primary",
                         use_container_width=True):
                os.remove(f"{cachepath}/{film}/词云.png")
                # 清除st.cahce_data的图片缓存
                word_clouds.clear()
    if tab == "简介":
        st.markdown("**🎬演职员:**")
        colist = st.columns(spec=12)
        avatar_url = avatar_urls[film_index].split(', ')
        avatar_name = avatar_names[film_index].split(', ')
        for co in range(2 * len(avatar_url)):
            with colist[co]:
                if co % 2 == 0:
                    ui.avatar(src=avatar_url, key=co, fallback=avatar_name[co // 2][0])
                else:
                    st.markdown(avatar_name[co // 2])
        with st.container(border=True, height=150):
            st.write(all_data["summary"][film_index])
    if tab == "评论":
        colist = st.columns(spec=3)
        if comm_sel == "短评":
            comm_list = random.sample([_ for _ in keysCache["短评"] if f"电影 : {film} : 短评" in _], 3)
        else:
            comm_list = random.sample([_ for _ in keysCache["长评"] if f"电影 : {film} : 长评" in _], 3)
        for comm, co in zip(comm_list, colist):
            with co:
                try:
                    with init_connection(db=DB) as r:
                        value = get_value(_r=r, key=comm)
                    comment = value["comment"]
                except KeyError:
                    comment = value["full_comment"]
                except Exception as e:
                    st.error(f"{e}\n数据库连接失败")
                with st.container(border=True, height=270):
                    ui.metric_card(title=f"用户: {comm.split(' : ')[3]}", content=comment,
                                   description=f"{value['date']}留言-⭐{value['star']}", key=str(co))
    if tab == "分析":
        tab_1, tab_2, tab_3 = st.tabs(["用户分布饼状图", "用户信息散点图", "影评推荐指数"])
        with tab_1:
            # 取出对应电影数据 astype-float型转换成str
            ipList = usersDf["ip"].astype(str).to_list()
            # 词频统计
            ip_counts = dict(collections.Counter(ipList))  # 对IP做词频统计
            ipdata = pd.DataFrame({
                "地域": list(ip_counts.keys()),
                "数目": list(ip_counts.values())
            })
            with st.expander(f"<{film}>-饼图", expanded=True):
                fig1 = pie_chart_module(ipdata, "用户评论分布")
                st.plotly_chart(fig1, use_container_width=True)
        with tab_2:
            idList = usersDf["id"].astype(str)
            yearList = usersDf["jointime"].to_list()
            hadseenList = usersDf["hadseen"].fillna(0).to_list()
            usersdata = pd.DataFrame({
                "ID": idList,
                "IP": ipList,
                "加入年份": yearList,
                "豆瓣网龄": [2024 - int(x[0:4]) for x in yearList],
                "看过电影": hadseenList
            })
            with st.expander(f"<{film}>-散点图", expanded=True):
                fig2 = point_chart_module(usersdata)
                st.plotly_chart(fig2, use_container_width=True)
        with tab_3:
            co3, co4 = st.columns(spec=2)
            with co3:
                starList = scommsDf["star"].astype(str).replace("-1.0", "1.0").tolist()
                star_map = {"1.0": "很差", "2.0": "较差", "3.0": "还行", "4.0": "推荐", "5.0": "力荐"}
                starList_mapped = [star_map[star] for star in starList]
                star_counts = dict(collections.Counter(starList_mapped))
                star_data = pd.DataFrame({
                    "星级": list(star_counts.keys()),
                    "数目": list(star_counts.values())
                })
                with st.expander(f"<{film}>-饼图", expanded=True):
                    fig_star = pie_chart_module(star_data, "用户评分分布")
                    st.plotly_chart(fig_star, use_container_width=True)
            with co4:
                reviews = ['短评', '长评']
                with st.expander(f"<{film}>-评论", expanded=True):
                    option = st.selectbox(
                        'Featured reviews',
                        reviews
                    )
                    if (option == '短评'):
                        index1 = scommsDf[scommsDf['star'] == 5.0].index[0]
                        comment = scommsDf.loc[index1, 'comment']
                        user_data = scommsDf.loc[index1, '用户']
                        date_data = scommsDf.loc[index1, 'date']
                        homepage = scommsDf.loc[index1, 'homepage']
                        comment_display = f"""{comment}

            Author    :    {user_data}  
            Date      :    {date_data}
                            """
                        st.text_area('', comment_display, height=250)
                        st.write("If you are interested in this author   ,  here is his homepage:")
                        st.markdown(homepage)
                    else:
                        index1 = fcommsDf[(fcommsDf['star'] == 5.0) & (fcommsDf['comment'].str.len() < 200)].index[0]
                        comment = fcommsDf.loc[index1, 'comment']
                        user_data = fcommsDf.loc[index1, '用户']
                        date_data = fcommsDf.loc[index1, 'date']
                        homepage = fcommsDf.loc[index1, 'homepage']
                        comment_display = f"""{comment}

            Author    :    {user_data}  
            Date      :    {date_data}
                                            """
                        st.text_area('', comment_display, height=300)
                        st.write("If you are interested in this author   ,  here is his homepage:")
                        st.markdown(homepage)
    if tab == "词云":
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
