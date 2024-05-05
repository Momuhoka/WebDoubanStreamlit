import os.path
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib import font_manager

from data.modules import (cachepath, read_txt, keys_cache, initialize,
                          diy_menu, pages_dict, init_connection, get_values)

# 设置全局属性
st.set_page_config(
    page_title='整体分析',
    page_icon='🏷️',
    layout='wide',
    initial_sidebar_state='collapsed'
)


def get_Color(movie_count):
    if movie_count >= 100:
        return [179, 205, 224, 255]  # 浅蓝色
    elif movie_count >= 40:
        return [140, 150, 198, 255]  # 浅紫色
    elif movie_count >= 30:
        return [136, 86, 167, 255]  # 深紫色
    elif movie_count >= 20:
        return [200, 100, 100, 255]  # 红色
    elif movie_count >= 10:
        return [255, 178, 102, 255]  # 橙色
    elif movie_count >= 5:
        return [255, 255, 153, 255]  # 黄色
    elif movie_count >= 3:
        return [153, 255, 153, 255]  # 绿色
    else:
        return [51, 204, 255, 255]  # 蓝色


diy_menu(_page="电影整体分析", _page_dict=pages_dict)
# 初始化
initialize()

# 使用的数据库
DB = 3
# 设置plt画图字体属性
plt_font = font_manager.FontProperties(fname=f"{os.getcwd()}/data/fonts/HanYiChaoCuHeiJian-1.ttf")

st.title('豆瓣TOP250电影')
st.info('电影整体概况')
# 默认渲染到主界面

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
infos = [_ for _ in keysCache["详情"]]

with init_connection(db=DB) as r:
    infos_dicts = get_values(_r=r, keys=infos)
# show
st.dataframe(infos_dicts)
tab_1, tab_2, tab_3, tab_4 = st.tabs(["电影评论", "电影分类", "影评推荐指数", "筛选电影"])
with tab_1:
    col_1, col_2 = st.columns(spec=2, gap='large')
    with col_1:
        with st.expander(f"评分分布图", expanded=True):
            score_counts = infos_dicts['score'].value_counts()

            # 创建DataFrame以便于显示
            score_counts_df = pd.DataFrame({'分数': score_counts.index, '电影数': score_counts.values})

            # 使用Plotly创建柱状图
            fig = px.bar(score_counts_df, x='分数', y='电影数', title='电影评分分布图', text='电影数', color='电影数',
                         color_continuous_scale='YlGnBu')
            fig.update_layout(title_font_size=25)
            st.plotly_chart(fig, use_container_width=True)
    with col_2:
        with st.expander(f"电影搜索", expanded=True):
            st.subheader('不同评分的电影介绍')
            scores = infos_dicts['score'].unique()
            scores.sort()
            # 创建一个下拉菜单让用户选择分数
            score_choice = st.selectbox("选择一个分数来查看对应电影:", scores)

            # 根据选定的分数筛选出对应的电影信息
            filtered_movies = infos_dicts[infos_dicts['score'] == score_choice][
                ['filmtype', 'director', 'name', 'times', 'area', 'year']].reset_index(drop=True)

            # 显示筛选后的DataFrame
            st.write(filtered_movies)
with tab_2:
    col_3, col_4 = st.columns(spec=2, gap='large')
    categories = ['剧情', '喜剧', '动作', '爱情', '科幻', '动画', '悬疑', '惊悚', '恐怖', '纪录片']
    with col_3:
        # 统计每个种类的个数
        category_counts = {category: infos_dicts['filmtype'].str.contains(category).sum() for category in categories}

        # 创建饼图的标签和值
        labels = list(category_counts.keys())
        values = list(category_counts.values())
        pull_value = [0.15, 0.16, 0.1, 0.18, 0.06, 0.14, 0.08, 0.12, 0.04, 0.02]

        # 创建饼图
        with st.expander(f"不同类型电影分布-饼图", expanded=True):
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, pull=pull_value)])
            fig.update_layout(title="不同类型电影占比", title_font_size=25)
            st.plotly_chart(fig, use_container_width=True)
    with col_4:
        with st.expander(f"不同类型电影推荐", expanded=True):
            type_choice = st.selectbox("选择一个电影类型来查找推荐电影:", categories)
            filtered_df = infos_dicts[infos_dicts['filmtype'].str.contains(type_choice)]
            sorted_df = filtered_df.sort_values(by='score', ascending=False).head(10).reset_index(drop=True)
            st.subheader(f"高分{type_choice}电影推荐如下：")
            st.write(sorted_df)
with tab_3:
    col_5, col_6 = st.columns(spec=2, gap='large')
    with col_5:
        with st.expander(f"电影地域分布", expanded=True):
            country_counts = infos_dicts['area'].value_counts().reset_index()
            country_counts.columns = ['Country', 'Number of Movies']
            # 提取数据
            countries = country_counts['Country']
            movie_counts = country_counts['Number of Movies']
            # 创建画布
            fig = px.bar(country_counts, y='Country', x='Number of Movies',
                         orientation='h', text='Number of Movies',
                         color='Number of Movies',  # 根据电影数量给柱状图上色
                         color_continuous_scale='Viridis',  # 使用 Viridis 渐变色
                         labels={'Country': '国家', 'Number of Movies': '电影数量'})

            # 更新布局设置
            fig.update_layout(
                title='不同国家的电影数量',
                xaxis_title='电影数量',
                yaxis_title='国家',
                title_font=dict(size=24),
                font=dict(family="Microsoft YaHei", size=10.5, color='black'),  # 设置全局字体为微软雅黑，字号为12
                xaxis=dict(tickfont=dict(family="Microsoft YaHei", size=13, color='black')),
                yaxis=dict(tickfont=dict(family="Microsoft YaHei", size=12.5, color='black')),
                xaxis_title_font=dict(family="Microsoft YaHei", size=16, color='black'),
                yaxis_title_font=dict(family="Microsoft YaHei", size=16, color='black'),
                yaxis_categoryorder='total ascending',  # 使柱状图按数值大小逆序排列
                height=525  # 设置图表高度为600像素
            )

            # 更新柱状图的文本标签位置
            fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            # 在 Streamlit 中显示图表
            st.plotly_chart(fig, use_container_width=True)
    with col_6:
        with st.expander(f"不同国家电影推荐", expanded=True):
            country_choice = st.selectbox("选择一个电影类型来查找推荐电影:", countries)
            filtered_df_1 = infos_dicts[infos_dicts['area'].str.contains(country_choice)]
            sorted_df_1 = filtered_df_1.sort_values(by='score', ascending=False).reset_index(drop=True)
            st.subheader(f"{country_choice}电影推荐如下：")
            st.write(sorted_df_1)
with tab_4:
    col_7, col_8 = st.columns(spec=2, gap='large')
    with col_7:
        with st.expander(f"电影导演查询", expanded=True):
            # 提取导演列表
            directors = sorted(infos_dicts['director'].unique())
            st.subheader('选择导演')
            # 创建搜索框
            selected_director = st.selectbox('', directors)

            # 根据所选导演过滤数据
            filtered_df_2 = infos_dicts.query("director == @selected_director")

            # 显示 DataFrame
            st.write(filtered_df_2)
    with col_8:
        with st.expander(f"电影演员查询", expanded=True):
            st.subheader('选择演员')
            all_actors = set()
            for actors in infos_dicts['actor'].str.split(' / '):
                all_actors.update(actors)
            all_actors = sorted(all_actors)

            # 创建下拉选项框供用户选择演员
            selected_actor = st.selectbox('', all_actors)

            # 根据所选演员过滤数据
            filtered_rows = []
            for index, row in infos_dicts.iterrows():
                if selected_actor in row['actor']:
                    filtered_rows.append(row)

            filtered_df = pd.DataFrame(filtered_rows)

            # 显示 DataFrame
            st.write(filtered_df)
