import redis

from data.modules import (diy_menu, pages_dict)

diy_menu(_page="电影球云图", _page_dict=pages_dict)
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config


def main1():
    nodes, edges = [], []
    redis_pool = redis.ConnectionPool(host='175.178.4.58', port=6379, password="momuhoka", decode_responses=True, db=5)
    r = redis.Redis(connection_pool=redis_pool)
    for i in range(694):
        m = r.get(str(i))  # 将'i'转换为字符串，并使用r.get()获取对应键的值
        words = m.split()
        # 存入变量
        start_ids = int(words[0])
        end_ids = int(words[1])
        filmname = words[2]
        filmtype = words[3]  # 避免使用type关键字作为变量名
        # 去除重复的节点
        nodes.append(Node(id=start_ids, label=filmname, size=15, color="green"))
        nodes.append(Node(id=end_ids, label=filmtype, size=15, color="yellow"))
        edges.append(Edge(source=start_ids, target=end_ids))

    nodes = set({node.id: node for node in nodes}.values())

    # 设置图形的配置
    config = Config(width=2000, height=2000, directed=True, physics=True, hierarchical=True, edgeMinimization=False,
                    nodeSpacing=10, levelSeparation=10)
    st.title("电影类型关系图")
    st.markdown('''
    :red[ps:] :orange[球云图] :green[中心] :blue[可移动] :violet[,]
    :gray[大小] :rainbow[可缩放].''')
    st.markdown('''
    :red[ps:] :orange[球云图可以反映] :green[电影与类型] :blue[之间的关系,] :violet[其中黄色小球代表]
    :gray[不同的类型,] :rainbow[绿色小球代表电影名].''')
    agraph(nodes=nodes, edges=edges, config=config)


def main2():
    nodes, edges = [], []
    redis_pool = redis.ConnectionPool(host='175.178.4.58', port=6379, password="momuhoka", decode_responses=True, db=6)
    r = redis.Redis(connection_pool=redis_pool)
    for i in range(217):
        m = r.get(str(i))  # 将'i'转换为字符串，并使用r.get()获取对应键的值
        words = m.split()
        # 存入变量
        start_ids = int(words[0])
        end_ids = int(words[1])
        filmname = words[2]
        director = words[3]  # 避免使用type关键字作为变量名
        # 去除重复的节点
        nodes.append(Node(id=start_ids, label=filmname, size=15, color="pink"))
        nodes.append(Node(id=end_ids, label=director, size=15, color="black"))
        edges.append(Edge(source=start_ids, target=end_ids, label='directed'))

    nodes = set({node.id: node for node in nodes}.values())

    # 设置图形的配置
    config = Config(width=2000, height=2000, directed=True, physics=True, hierarchical=False)
    st.title("导演与电影关系图")
    st.markdown('''
    :red[ps:] :orange[球云图] :green[中心] :blue[可移动] :violet[ , ]
    :gray[大小] :rainbow[可缩放].''')
    st.markdown('''
    :red[ps:] :orange[球云图可以反映] :green[电影与导演] :blue[之间的关系 , ] :violet[ 其中粉色小球代表]
    :gray[不同的电影 , ] :rainbow[ 黑色小球代表导演].''')
    agraph(nodes=nodes, edges=edges, config=config)


# 函数用于加载CSV文件并创建节点和边

if __name__ == "__main__":
    tab_1, tab_2 = st.tabs(["电影类型球云图", "导演与电影关系球云图"])
    with tab_1:
        main1()
    with tab_2:
        main2()
