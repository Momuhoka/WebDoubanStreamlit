import collections
import os.path
import streamlit as st
import pandas as pd
import plotly.express as px
from data.modules import (initialize, cachepath, read_txt, read_excel,
                          keys_cache, all_cache, checkcache,
                          film_cache, pie_chart_module, point_chart_module,
                          datapath, word_filter, word_clouds,
                          diy_menu, pages_dict, init_connection, get_values)
diy_menu(_page="hua的主页", _page_dict=pages_dict)
import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config


# 函数用于加载CSV文件并创建节点和边
def load_relations1(file_path):
    df = pd.read_csv(file_path)
    start_ids = df[':START_ID'].tolist()
    end_ids = df[':END_ID'].tolist()
    relations = df['relation'].tolist()
    type = df['type'].tolist()
    filmname = df['film_name'].tolist()
    nodes = []
    edges = []


    for start_ids, end_ids, relations,filmname,type in zip(start_ids, end_ids, relations,filmname,type):
        # 假设start_id和end_id同时代表了节点的ID和标签
        # 实际应用中可能需要从数据库或其他地方获取更多信息
        nodes.append(Node(id=start_ids, label=filmname, color="green"))
        nodes.append(Node(id=end_ids, label=type, color="yellow"))
        edges.append(Edge(source=start_ids, target=end_ids, label=relations))

    # 去除重复的节点
    nodes = list({node.id: node for node in nodes}.values())
    return nodes,edges

def load_relations2(file_path):
    df = pd.read_csv(file_path)
    start_ids = df[':START_ID'].tolist()
    end_ids = df[':END_ID'].tolist()
    relations = df['relation'].tolist()
    director = df['director'].tolist()
    filmname = df['film_name'].tolist()
    nodes = []
    edges = []
    for start_ids, end_ids, relations,filmname,director in zip(start_ids, end_ids, relations,filmname,director):
        # 假设start_id和end_id同时代表了节点的ID和标签
        # 实际应用中可能需要从数据库或其他地方获取更多信息
        nodes.append(Node(id=start_ids, label=filmname, color="pink"))
        nodes.append(Node(id=end_ids, label=director, color="black"))
        edges.append(Edge(source=start_ids, target=end_ids, label=relations))

    # 去除重复的节点
    nodes = list({node.id: node for node in nodes}.values())
    return nodes,edges
# 主函数，用于运行Streamlit应用
def fuc1():
    st.title("Movie Relations Graph")

    # 加载关系，并创建图形的节点和边
    nodes1, edges1 = [], []
    #for relation in ['belong_to']:
    n, e = load_relations1(f'D:\\3160257581\FileRecv\\tt.csv')
    nodes1.extend(n)
    edges1.extend(e)

    # 设置图形的配置
    config = Config(width=5000, height=5000, directed=True, physics=True,hierarchical=True)

    # 创建图形
    agraph(nodes=nodes1, edges=edges1, config=config)
def fuc2():
# 加载关系，并创建图形的节点和边
    nodes2, edges2 = [], []
    #for relation in ['directed']:
    d, g = load_relations2(f'D:\\3160257581\FileRecv\\mm.csv')
    nodes2.extend(d)
    edges2.extend(g)

    # 设置图形的配置
    config = Config(width=5000, height=5000, directed=True, physics=True,hierarchical=False)

    # 创建图形
    agraph(nodes=nodes2, edges=edges2, config=config)
if __name__ == "__main__":
    tab_1,tab_2=st.tabs(["电影类型球云图","导演与演员关系球云图"])
    with tab_1:
        fuc1()
    with tab_2:
        fuc2()