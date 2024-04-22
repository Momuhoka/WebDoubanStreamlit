import os
import random

import streamlit as st
from streamlit_elements import elements, mui, html

from data.modules import diy_menu, pages_dict, cachepath, read_txt, keys_cache

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

# 动态元素
with elements("dashboard"):

    from streamlit_elements import dashboard, html

    if 'chosen_film' not in st.session_state:
        st.session_state.chosen_film = 'None'

    # 格子规模
    width = 2
    height = 3
    # 乱序
    random.shuffle(selected_films)
    if not st.session_state.chosen_film or st.session_state.chosen_film not in selected_films:
        st.session_state.chosen_film = selected_films[0]
    # 选中的电影和信息栏
    layout = [dashboard.Item(st.session_state.chosen_film, 0, 0, width + 1, height + 1, isResizable=False),
              dashboard.Item("infos", width + 1, 0, 11 - width, height + 1, static=True)]
    # 过滤选中的电影，并展示其他的电影
    for index, film in enumerate([_ for _ in selected_films if st.session_state.chosen_film != _]):
        layout.append(dashboard.Item(film, (index * width) % (width * 6), height + 1 + index // 6, width, height,
                                     isResizable=False))


    # callback函数，用来固定需要展示的信息
    def handle_drag_stop(updated_layout):
        # 找最小值先设置很大的值
        minxplusy = 1e2
        for old_layout in updated_layout:
            if old_layout['x'] + old_layout['y'] < minxplusy:
                minxplusy = old_layout['x'] + old_layout['y']
                st.session_state.chosen_film = old_layout['i']


    with dashboard.Grid(layout, compactType="vertical", onDragStop=handle_drag_stop):
        for film in selected_films:
            with mui.Paper(key=film, elevation=3, variant="elevation", square=False):
                html.img(
                    # src="data/temp.jpg",
                    alt=film
                )
        with mui.Paper(key="infos", elevation=2, variant="elevation", square=False):
            mui.icon.DoubleArrow()
            mui.Typography("Infomations.")

