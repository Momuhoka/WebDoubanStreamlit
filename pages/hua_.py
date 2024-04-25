import streamlit as st
from data.modules import (initialize, diy_menu, pages_dict, init_connection)
from streamlit_agraph import agraph, Node, Edge, Config

# 设置全局属性
st.set_page_config(
    page_title='球云图',
    page_icon='🔮',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# 初始化
initialize()
# 页面菜单
diy_menu(_page="电影球云图", _page_dict=pages_dict)


# 处理函数
def handle_results(_results: list[str], _colors: list[str], _label):
    nodes, edges = [], []
    for result in _results:
        words = result.split(', ')
        # 存入变量
        filmname = words[0]
        relation = words[1]  # 避免使用type关键字作为变量名
        # 去除重复的节点
        nodes.append(Node(id=filmname, label=filmname, size=15, color=_colors[0]))
        nodes.append(Node(id=relation, label=relation, size=15, color=_colors[1]))
        if not _label:
            edges.append(Edge(source=filmname, target=relation))
        else:
            edges.append(Edge(source=filmname, target=relation, label=_label))
    # 节点列表处理
    nodes = set({node.id: node for node in nodes}.values())
    return nodes, edges


def film_type_relation():
    # 采用管道访问
    with init_connection(db=6) as r:
        keys = r.keys()
        pipe = r.pipeline()
    for key in keys:
        pipe.get(key)
    results = pipe.execute()  # 获取值
    nodes, edges = handle_results(_results=results, _colors=["green", "yellow"], _label=None)

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


def film_actor_relation():
    # 采用管道访问
    with init_connection(db=5) as r:
        keys = r.keys()
        pipe = r.pipeline()
    for key in keys:
        pipe.get(key)
    results = pipe.execute()
    nodes, edges = handle_results(_results=results, _colors=["pink", "black"], _label="directed")

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

tab_1, tab_2 = st.tabs(["电影类型球云图", "导演与电影关系球云图"])
with tab_1:
    film_type_relation()
with tab_2:
    film_actor_relation()