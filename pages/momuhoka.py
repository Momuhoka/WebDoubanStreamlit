import base64
import collections
import os

import pandas as pd
import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import streamlit_shadcn_ui as ui
from streamlit_image_select import image_select
from streamlit_star_rating import st_star_rating

from data.modules import diy_menu, pages_dict, cachepath, read_txt, keys_cache, read_excel, \
    pie_chart_module, point_chart_module, datapath, word_filter, word_clouds, initialize

# 初始化
initialize()

# 默认数据库
DB = 3

# 页面菜单
diy_menu(_page="我的主页", _page_dict=pages_dict)

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
    keysCache = keys_cache(db=DB)

# 获取电影列表
films = [filmkey.split(" : ")[1] for filmkey in keysCache["详情"]]

selected_films = st.multiselect(label="搜索电影", options=films, default=None)
if not selected_films:
    selected_films = films

image_urls = ["https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp",
            "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2561716440.webp",
            "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p2372307693.webp"]

PILimages = []
# 发起GET请求获取图片内容
for url in image_urls:
    response = requests.get(url)
    encoded = base64.b64encode(response.content).decode()
    PILimages.append(Image.open(BytesIO(response.content)))

col_1, col_2 = st.columns(spec=[0.25, 0.75])

# 选择电影
img = image_select(
    label="选择电影",
    images=PILimages,
    use_container_width=False,
    captions=films[:3],
    return_value="index",
)
film = films[img]

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
usersDf["ip"].fillna(usersDf["location"], inplace=True)
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
        st.image(PILimages[img], use_column_width=True)
with col_2:
    col_2_1, col_2_2 = st.columns(spec=[0.7, 0.3])
    with col_2_1:
        st.markdown(f"#### {films[img]}")
        st.markdown(f"**投票数: {len(films)}**")
        tab = ui.tabs(options=["简介", "评论", "分析", "词云"], default_value="简介")
    with col_2_2:
        st_star_rating(label="推荐指数:", maxValue=5, defaultValue=img+3, read_only=True)
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
        st.markdown("**人员:**")
        colist = st.columns(spec=16)
        for co in range(2*(img+2)):
            with colist[co]:
                if co % 2 == 0:
                    ui.avatar(src="", key=co)
                else:
                    st.markdown(f"*Number.{img}*")
        with st.container(border=True, height=150):
            st.markdown("Information.")
    if tab == "评论":
        colist = st.columns(spec=3)
        for co in colist:
            with co:
                if comm_sel == "短评":
                    ui.metric_card(title="id", content="short messages.", description="time-ip", key=str(co))
                else:
                    ui.metric_card(title="id", content="long messages.", description="time-ip", key=str(co))
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
                "估算年份": [int(x[0:4]) + int(x[5:7]) / 12 + int(x[8:10]) / 30 for x in yearList],
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

