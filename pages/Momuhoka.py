import streamlit as st
import redis
import os

# 设置全局属性
st.set_page_config(
    page_title="M's测试界面",
    page_icon='📀',
    layout='wide'
)

# 数据库
DB = 3

# 模块化使用范例
st.markdown("#### 获取所有键值表: $\color{orange} {keysCache生成} $ ####")
st.code("""
'''
    1.从 主页.py 获取想要的代码
    2.根据报错从modules中导入需要的模块
'''
from data.modules import cachepath, read_txt, keys_cache
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
# 展示部分数据, 全部展示会过量卡死
st.dataframe(keysCache, use_container_width=True)
""")
st.markdown("**[详情]数据展示:**")
from data.modules import cachepath, read_txt, keys_cache

if os.path.isfile(f"{cachepath}/键值.txt"):
    keysString = read_txt(f"{cachepath}/键值.txt")
    keysCache = {}
    for index, keyString in zip(["详情", "用户", "短评", "长评"], keysString):
        keysList = keyString.split('|')
        keysCache[index] = keysList
else:
    keysCache = keys_cache(db=3)
st.dataframe(keysCache['详情'], use_container_width=True)

st.markdown("#### 获取需要的键值对: $\color{orange} {get_value模块} $ ####")
# st.code()
from data.modules import get_value, init_connection

# 获取电影列表
allfilms = [filmkey.split(" : ")[1] for filmkey in keysCache["详情"]]
col_1, col_2 = st.columns(spec=2)
with st.container(border=True):
    with col_1:
        with st.form(key="单选", clear_on_submit=True):
            film = st.selectbox(label="单选", options=allfilms)
            st.form_submit_button(label="确认", use_container_width=True)
    with col_2:
        with init_connection(db=DB) as r:
            film_df = get_value(_r=r, key=f"电影 : {film} : 详情")
            st.dataframe(film_df, use_container_width=True)
    with st.form(key="多选", clear_on_submit=True):
        st.multiselect(label="多选", options=allfilms)
        st.form_submit_button(label="确认", use_container_width=True)
