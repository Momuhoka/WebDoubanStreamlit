import collections
import os.path
import streamlit as st
import pandas as pd

from data.modules import (initialize, cachepath, read_txt, read_excel,
                          keys_cache, all_cache, checkcache,
                          film_cache, pie_chart_module, point_chart_module,
                          datapath, word_filter, word_clouds,
                          diy_menu, pages_dict)
# 初始化
initialize()

# 使用的数据库
DB = 3

# 设置全局属性
st.set_page_config(
    page_title='第三小组',
    page_icon='♾️',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# experimental_allow_widgets=True
# 允许在缓存函数中使用小部件。默认值为False
# 对缓存函数中的小部件的支持目前处于实验阶段
# 将此参数设置为 True 可能会导致内存使用过多，因为 widget 值被视为缓存的附加输入参数

# 页面菜单
diy_menu(_page="主页", _page_dict=pages_dict)

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
    keysCache = keys_cache(db=DB)

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
            all_cache(_db=DB, _mode=mode)
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
    film_cache(_db=DB, film=film, keysCache=keysCache, mode=False)

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

tab_1, tab_2 ,tab_3= st.tabs(["电影评论", "电影云图","影评推荐指数"])
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
            fig1 = pie_chart_module(ipdata,"用户评论分布")
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
    with  co4:
        reviews=['短评','长评']
        with st.expander(f"<{film}>-评论", expanded=True):
            st.subheader('精选评论')
            option = st.selectbox(
                '',
                reviews
            )
            if(option=='短评'):
                index1=scommsDf[scommsDf['star']==5.0].index[0]
                comment = scommsDf.loc[index1,'comment']
                user_data = scommsDf.loc[index1,'用户']
                date_data = scommsDf.loc[index1,'date']
                homepage = scommsDf.loc[index1,'homepage']
                comment_display = f"""{comment}

Author    :    {user_data}  
Date      :    {date_data}
                """
                st.text_area('', comment_display, height=250)
                st.write("如果你对这位用户感兴趣   ,  这是他的主页:")
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
                st.write("如果你对这位用户感兴趣   ,  这是他的主页:")
                st.markdown(homepage)

