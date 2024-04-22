import os
import pickle
import time
import streamlit as st
import numpy as np
import pandas as pd
import thulac
from stqdm import stqdm

from data.modules import diy_menu, pages_dict

# 设置全局属性
st.set_page_config(
    page_title='模型训练',
    page_icon='🧊',
    layout='wide',
    initial_sidebar_state='collapsed'
)
st.spinner("载入jieba分词缓存...")
import jieba

st.spinner("载入tensorflow模型库...")
import tensorflow as tf

# 页面菜单
diy_menu(_page="模型", _page_dict=pages_dict)

EAGER_MODE = ":green[TRUE]" if tf.executing_eagerly() else ":red[FALSE]"
GPU_AVAILABLE = ":green[AVAILABLE]" if tf.config.list_physical_devices('GPU') else ":red[NOT AVAILABLE]"
tc1, tc2 = st.columns(spec=[0.6, 0.4])
with tc1:
    st.markdown(f'''## **TensorFlow版本:** {tf.__version__}   
> **Eager模式:** {EAGER_MODE}   
> **GPU支持:** {GPU_AVAILABLE}''')
with tc2:
    t1, t2 = st.columns(spec=2)
    # 全局选择
    with st.container():
        with t1:
            st.markdown("**页面设置**")
            train_module = st.toggle("模型训练", value=True)
            use_module = st.toggle("模型使用", value=False)
            show_module = st.toggle("数据展示", value=False)
        with t2:
            threadings = st.number_input("> **TensorFlow线程数**",
                                         help='''最大线程数可能会受到其他因素的限制,
                                                         如内存大小、缓存大小、并行硬件资源等.
                                                         需要综合考虑多个因素,并进行实验和测试来找到最佳的设置''',
                                         value=6,
                                         min_value=1)
            st.info(f"**当前线程数**(6): :green[{threadings}]")

# 主页部分
# 设置 TensorFlow 的线程数
os.environ["TF_NUM_INTEROP_THREADS"] = str(threadings)
os.environ["TF_NUM_INTRAOP_THREADS"] = str(threadings)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 禁用除了错误信息之外的所有日志输出, 包括警告信息
tf.config.threading.set_inter_op_parallelism_threads(threadings)
tf.config.threading.set_intra_op_parallelism_threads(threadings)
# Tensorflow相关库导入
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
# 自定义回调函数
from data.keras.streamlit_callback import StreamlitLambdaCallback

# 缓存路径 ./cache
cachepath = "./cache"
if not os.path.exists(cachepath):
    os.mkdir(cachepath)

# 部分文件存储位置
datapath = "./data"
if not os.path.exists(f"{datapath}/keras/saves"):
    os.makedirs(f"{datapath}/keras/saves")

# 要读取的缓存文件
cachefile_name = "cache.csv"

# 重新训练按钮缓存
if "retrain" not in st.session_state:
    st.session_state.retrain = False


@st.cache_data(ttl=300,  # Cache data for 5 min (=300 seconds)
               show_spinner="检查数据文件状态...")
def checkdatafile(path: str):
    walkers = os.listdir(path)
    filespath = [f"{path}/{walker}" for walker in walkers if not os.path.isfile(f"{path}/{walker}")]
    for _filepath in filespath:
        if not os.path.isfile(f"{_filepath}/短评.xlsx"):
            return f"{_filepath}/短评.xlsx", False
        if not os.path.isfile(f"{_filepath}/长评.xlsx"):
            return f"{_filepath}/长评.xlsx", False
    return filespath, True


# 数据预处理检查
def pre_data_check():
    _tokenized_data_check = os.path.isfile(f"{datapath}/keras/tokenized_data.csv")
    _tokenizer_check = os.path.isfile(f"{datapath}/keras/tokenizer.pkl")
    _sequences_check = os.path.isfile(f"{datapath}/keras/sequences.pkl")
    _padded_check = os.path.isfile(f"{datapath}/keras/padded.pkl")
    return _tokenized_data_check, _tokenizer_check, _sequences_check, _padded_check


def check_mdoel_had(path: str):
    walkers = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    models = {}
    for walker in walkers:
        if os.path.isfile(f"{path}/{walker}/{walker}.keras"):
            modification_time = os.path.getmtime(f"{path}/{walker}/{walker}.keras")
            hadtokenizer_check = os.path.isfile(f"{path}/{walker}/{walker}.pkl")
            models[f"{walker}"] = [time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(modification_time)), hadtokenizer_check]
    return models


def read_data(_type: str, path: str):
    if _type == "csv":
        _data = pd.read_csv(path, index_col=0)
    elif _type == "pkl":
        with open(path, "rb") as _file:
            _data = pickle.load(_file)
    else:
        with open(path, mode="r", encoding="utf-8") as _file:
            # 要注意回车符号-strip会删除左右的特殊字符-不能为空!
            _data = [line.strip('\n') for line in _file.readlines()]
    return _data


@st.cache_data(show_spinner="读取数据中...")
def read_cache(path: str):
    _tokenized_data = read_data(_type="csv", path=path)
    return _tokenized_data


@st.cache_data(show_spinner="读取数据中...")
def read_tokenizer(path: str):
    _tokenizer = read_data(_type="pkl", path=path)
    return _tokenizer


@st.cache_data(show_spinner="读取数据中...")
def read_sequences(path: str):
    _sequences = read_data(_type="pkl", path=path)
    return _sequences


@st.cache_data(show_spinner="读取数据中...")
def read_padded(path: str):
    _padded = read_data(_type="pkl", path=path)
    return _padded


@st.cache_resource(show_spinner="读取模型中...")
def read_model(path: str):
    _model = tf.keras.models.load_model(path)
    return _model


if train_module:
    # 侧边栏部分
    if os.path.isfile(f"{datapath}/{cachefile_name}"):
        data = read_data(_type="csv", path=f"{datapath}/{cachefile_name}")
        data = data.rename(columns={"Star": "star", "Comment": "comment"})
        data = data.sample(frac=1).reset_index()  # 打乱
        show_all_data = data.reset_index(drop=True).rename_axis("序列ID")
        show_all_data.index = show_all_data.index + 1  # 从 1 起始
        next_check = True
    else:
        data, show_all_data = None, None
        st.error(f"**缺少必要文件{datapath}/{cachefile_name}**")
        next_check = False
    if os.path.isfile(f"{datapath}/keras/model_filterwords.txt"):
        filter_words = read_data(_type="txt", path=f"{datapath}/model_filterwords.txt")
    else:
        filter_words = None

    with st.sidebar:
        with st.form("模型配置"):
            t1, t2, t3 = st.tabs(["字典生成配置", "模型参数配置", "过滤词预览"])
            with t1:
                vocab_size = st.number_input("词汇表大小-(vocab_size)",
                                             help='''在文本处理任务中,
                                             我们通常将文本数据转换为数字表示,
                                             其中每个单词都被映射到一个唯一的整数值.
                                             这个整数值的范围就是词汇表的大小,
                                             也就是vocab_size''',
                                             value=10000,
                                             min_value=1)
                embedding_dim = st.number_input("词嵌入维度-(embedding_dim)",
                                                help='''在NLP任务中,通常会使用预训练的词嵌入模型
                                                (如Word2Vec、GloVe或BERT)来将单词转换为向量表示.
                                                这些词嵌入模型会为每个单词分配一个固定长度的向量,
                                                这个向量的维度就是embedding_dim.
                                                较小的维度可能会导致信息丢失,而较大的维度可能会增加计算成本.
                                                一般来说，embedding_dim的值通常在50到300之间.''',
                                                value=50,
                                                min_value=1,
                                                max_value=300)
                max_length = st.number_input("序列最大长度-(max_length)",
                                             help='''由于文本序列的长度可能不一致,为了方便模型处理,
                                             我们需要将所有序列调整为相同的长度.max_length指定了文本序列的最大长度,
                                             超过这个长度的序列将被截断,不足这个长度的序列将被填充.''',
                                             value=100,
                                             min_value=10)
                oov_tok = st.text_input("特殊标记-(token)",
                                        help='''oov_tok 是在自然语言处理(NLP)中常用的一个特殊标记(token),
                                         用于表示'未知单词'(Out-Of-Vocabulary word), 一般不需要修改.''',
                                        value="<OOV>")
                with st.expander(":orange[当前字典参数:]", expanded=True):
                    st.markdown(f'''
                    **词汇表大小**(10000): :green[{vocab_size}]  
                    **词嵌入维度**(16): :green[{embedding_dim}]  
                    **序列最大长度**(100): :green[{max_length}]    
                    **未知单词特殊标记**(<OOV>): :blue[{oov_tok}]
                    ''')
            with t2:
                batch_size = st.number_input("每批次样本数量-(batch_size)",
                                             help='''batch_size指定每个训练批次中的样本数量,
                                             使用批处理,可以提高训练的效率和速度.常见的batch_size值通常在8到256之间,
                                             具体取决于问题的复杂性和可用资源''',
                                             value=64,
                                             min_value=8,
                                             max_value=256)
                epochs = st.number_input("迭代次数-(epochs)",
                                         help='''一个epoch表示将整个训练数据集完整地过一遍的次数.
                                         根据数据集的大小和模型的复杂性来选择合适的迭代次数''',
                                         value=20,
                                         min_value=1)
                patience = st.number_input("监测指标-(patience)",
                                           help='''EarlyStopping(TensorFlow中的一个回调函数,
                                           用于在训练过程中实现早停(early stopping)机制)的参数之一.
                                           如果在连续的patience轮训练中,监测指标没有改善,训练将会提前停止.
                                           (0表示没有容忍度)''',
                                           value=min(epochs, 5),
                                           min_value=0,
                                           max_value=epochs)
                validation_split = st.select_slider("数据划分-(validation_split)",
                                                    help='''介于0和1之间的浮点数,表示要保留作为验证集的训练数据的比例.
                                                    例如0.2将会从训练数据中随机选择20%的样本作为验证集,而剩下的 80% 样本将用于训练.
                                                    只提供0.1~0.5可选''',
                                                    options=[0.1, 0.2, 0.3, 0.4, 0.5],
                                                    value=0.2)
                with st.expander(":orange[当前模型参数:]", expanded=True):
                    st.markdown(f'''
                    **每批次样本数量**(32): :green[{batch_size}]  
                    **迭代次数**(100): :green[{epochs}]  
                    **监测指标**(50): :green[{patience}]  
                    **数据划分(训练/验证)**(0.2): 
                    :green[{(1 - validation_split) * 100}]% **/** 
                    :blue[{validation_split * 100}]%
                    ''')
            with t3:
                if filter_words:
                    show_filter_words = pd.DataFrame(filter_words).rename(columns={0: "自定义过滤"})
                    st.dataframe(show_filter_words, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"{datapath}下没有找到model_filterwords.txt过滤词文件", icon='🗂️')
            st.form_submit_button("应用修改", use_container_width=True)

    # 展示数据
    with st.expander("**已收集数据:** {}".format(":red[None]" if data is None else f":green[{len(data)}]")):
        st.dataframe(show_all_data, use_container_width=True)

    # # 临时用0.1不然训练集太大
    # data = data[:10000].reset_index(drop=True)

    tokenized_data_check, tokenizer_check, sequences_check, padded_check = pre_data_check()
    pre_check = tokenized_data_check & tokenizer_check & sequences_check & padded_check
    with st.status("**数据预处理**", expanded=not pre_check):
        st.markdown("###### ℹ️模型页面反应和加载比较缓慢, 请耐心等待")
        co1, co2 = st.columns(spec=2)
        with co1:
            cut_toggle = st.toggle("*使用 :orange[thulac] 分词(默认 :orange[jieba] )*", value=False)
            retokenizer_button = st.button("**一键处理**", type="primary", use_container_width=True)
            with st.container(border=True):
                infoholder = st.empty()
                infoholder_button = st.empty()
                cut_button = infoholder_button.button("数据处理", use_container_width=True, disabled=not next_check)
                if cut_button or retokenizer_button:
                    # 清除对应函数缓存
                    read_cache.clear()
                    # 分词
                    s = time.time()
                    tokenized_data = pd.DataFrame()
                    stqdm(st_container=infoholder_button).pandas(desc="数据处理进度")
                    # 三分类
                    tokenized_data['sentiment'] = data['star'].astype(np.int16).apply(
                        lambda x: 0 if x in [1, 2] else (1 if x == 3 else 2))
                    if not cut_toggle:
                        tokenized_data["tokenized_comment"] = data["comment"].astype(np.str_).progress_apply(
                            lambda x: ' '.join(jieba.cut(x)))
                    else:
                        thu = thulac.thulac(seg_only=True, filt=True)
                        tokenized_data["tokenized_comment"] = data["comment"].astype(np.str_).progress_apply(
                            lambda x: thu.cut(x, text=True))
                    e = time.time()
                    infoholder.info("**成功生成数据表:** {:.2f}s".format(e - s))
                    tokenized_data.to_csv(f"{datapath}/keras/tokenized_data.csv")
                    tokenized_data_check = True
                else:
                    if tokenized_data_check:
                        tokenized_data = read_cache(path=f"{datapath}/keras/tokenized_data.csv")
                        infoholder.info(f":green[**检测到数据处理缓存**]: {len(tokenized_data)}")
                    else:
                        show_data = None
                        infoholder.info(f":red[**没有检测到数据处理缓存(请点击数据处理)**]", icon='🚨')
            with st.container(border=True):
                dictholder = st.empty()
                dictholder_button = st.empty()
                fit_button = dictholder_button.button("映射表生成", use_container_width=True,
                                                      disabled=not tokenized_data_check)
                if fit_button or retokenizer_button:
                    # 清除对应函数缓存
                    read_tokenizer.clear()
                    dictholder_button.empty()
                    # 字典映射生成-依据训练集-必须唯一
                    s = time.time()
                    # num_words:None或整数,处理的最大单词数量。少于此数的单词丢掉
                    with st.spinner("词汇映射表生成中..."):
                        tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_tok)
                        # fit_on_texts后: word_counts: 词频统计结果, word_index: 词和index的对应关系
                        tokenizer.fit_on_texts(tokenized_data["tokenized_comment"].astype(np.str_))
                    e = time.time()
                    dictholder.info("**成功生成词汇映射表:** {:.2f}s".format(e - s))
                    # 保存 Tokenizer 对象到文件
                    with open(f"{datapath}/keras/tokenizer.pkl", "wb") as file:
                        pickle.dump(tokenizer, file)
                    tokenizer_check = True
                else:
                    if tokenizer_check:
                        # 从文件中加载 Tokenizer 对象
                        tokenizer = read_tokenizer(path=f"{datapath}/keras/tokenizer.pkl")
                        dictholder.info(f":green[**检测到词汇映射表缓存**]: {len(tokenizer.index_word)}")
                    else:
                        tokenizer = None
                        dictholder.info(f":red[**没有检测到词汇映射表缓存(请点击映射表生成)**]", icon='🚨')
            with st.container(border=True):
                co1_1, co1_2 = st.columns(spec=2)
                with co1_1:
                    seqholder = st.empty()
                    seqholder_button = st.empty()
                    seq_button = seqholder_button.button("转换表生成", use_container_width=True,
                                                         disabled=not tokenized_data_check)
                    if seq_button or retokenizer_button:
                        # 清除对应函数缓存
                        read_sequences.clear()
                        seqholder_button.empty()
                        s = time.time()
                        with st.spinner("评论转换表生成中..."):
                            sequences = tokenizer.texts_to_sequences(
                                tokenized_data["tokenized_comment"].astype(np.str_))
                        e = time.time()
                        seqholder.info("**成功生成评论转换表:** {:.2f}s".format(e - s))
                        with open(f"{datapath}/keras/sequences.pkl", "wb") as file:
                            pickle.dump(sequences, file)
                        sequences_check = True
                    else:
                        if sequences_check:
                            # 从文件中加载 sequences 对象
                            sequences = read_sequences(path=f"{datapath}/keras/sequences.pkl")
                            seqholder.info(f":green[**检测到评论转换表缓存**]: {len(sequences)}")
                        else:
                            sequences = None
                            seqholder.info(f":red[**没有检测到评论转换表缓存(请点击转换表生成)**]", icon='🚨')
                with co1_2:
                    padholder = st.empty()
                    padholder_button = st.empty()
                    pad_button = padholder_button.button("补全表生成", use_container_width=True,
                                                         disabled=not sequences_check)
                    if pad_button or retokenizer_button:
                        # 清除对应函数缓存
                        read_padded.clear()
                        padholder_button.empty()
                        s = time.time()
                        with st.spinner("转换补全表生成中..."):
                            # pad_sequences, 对上面生成的不定长序列进行补全
                            padded = pad_sequences(sequences, maxlen=max_length, padding="post", truncating="post")
                        e = time.time()
                        padholder.info("**成功生成转换补全表:** {:.2f}s".format(e - s))
                        with open(f"{datapath}/keras/padded.pkl", "wb") as file:
                            pickle.dump(padded, file)
                        padded_check = True
                    else:
                        if padded_check:
                            # 从文件中加载 padded 对象
                            padded = read_padded(path=f"{datapath}/keras/padded.pkl")
                            padholder.info(f":green[**检测到转换补全表缓存**]: {len(padded)}")
                        else:
                            padded = None
                            padholder.info(f":red[**没有检测到转换补全表缓存(请点击补全表生成)**]", icon='🚨')
        with co2:
            if show_module:
                t1, t2, t3, t4, t5 = st.tabs(
                    ["数据处理预览", "词汇映射预览", "评论转换预览", "转换补全预览", "补全表信息"])
                with t1:
                    # 处理数据展示
                    if tokenized_data is not None:
                        show_data = tokenized_data.rename(
                            columns={"sentiment": "情感", "tokenized_comment": "分词"}).rename_axis("序列ID")
                        show_data.index = show_data.index + 1  # 从1开始
                    else:
                        show_data = None
                    st.dataframe(show_data, use_container_width=True)
                with t2:
                    # 词汇表展示
                    if tokenizer is not None:
                        show_tokenizer = pd.Series(tokenizer.index_word)  # 字典映射变dataframe
                        show_tokenizer = show_tokenizer.rename(index="映射词汇").rename_axis("索引")
                    else:
                        show_tokenizer = None
                    st.dataframe(show_tokenizer, use_container_width=True)
                with t3:
                    # 转换表展示, 由于太大用字典拆分表示
                    show_seq = sequences
                    if show_seq is not None:
                        length = len(sequences)
                        seq_index = st.number_input(f"**序列ID:** :green[1~{length}] ",
                                                    value=1,
                                                    min_value=1,
                                                    max_value=length)
                        show_seq = pd.DataFrame(sequences[seq_index - 1])
                        show_seq.index = show_seq.index + 1  # 从1开始
                        show_seq = show_seq.rename(columns={0: "特征值"}).rename_axis("时间步")
                    st.dataframe(show_seq, use_container_width=True)
                with t4:
                    # 补全表展示
                    show_padded = None
                    if padded is not None:
                        show_padded = pd.DataFrame(padded).rename_axis("序列ID")
                        show_padded.index = show_padded.index + 1
                    st.dataframe(show_padded, use_container_width=True)
                with t5:
                    # 补全表状态展示
                    cp1, cp2 = st.columns(spec=2)
                    # 计算每行的长度
                    with cp1:
                        lengths = np.array([len(np.trim_zeros(row, 'b')) for row in padded])
                        show_lengths = pd.Series(lengths).rename_axis("序列").rename(index="长度")
                        show_lengths.index = show_lengths.index + 1
                        st.dataframe(show_lengths, use_container_width=True)
                    # 生成统计表
                    with cp2:
                        unique_lengths, counts = np.unique(lengths, return_counts=True)
                        stat_table = np.column_stack((unique_lengths, counts))
                        show_table = pd.DataFrame(stat_table) \
                            .set_index(0).rename_axis("长度").rename(columns={1: "占比数"})
                        show_table["占比"] = show_table["占比数"].apply(
                            lambda x: "{:.2f}%".format(x / len(padded) * 100))
                        st.dataframe(show_table, use_container_width=True)
            else:
                st.info("没有启用 **:orange[数据展示]** ", icon='⚠️')

    next_check = tokenized_data_check & tokenizer_check & sequences_check & padded_check
    with st.container(border=True):
        model_name = st.text_input("**模型名称:**",
                                   placeholder="存在则读取模型/不存在则新建模型",
                                   disabled=not next_check)
        if next_check and model_name:
            if not os.path.exists(f"{datapath}/keras/saves/{model_name}"):
                os.mkdir(f"{datapath}/keras/saves/{model_name}")
            if not os.path.isfile(f"{datapath}/keras/saves/{model_name}/{model_name}.keras"):
                # 构建CNN模型
                with st.spinner("构建CNN模型..."):
                    s = time.time()
                    model = Sequential([
                        Embedding(vocab_size, embedding_dim, input_length=max_length),
                        Conv1D(128, 5, activation='relu'),
                        Dropout(0.5),
                        GlobalMaxPooling1D(),
                        Dense(3, activation='softmax')
                    ])
                    model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
                    e = time.time()
                st.info("**CNN模型:red[构建]成功:** {:.2f}s".format(e - s))
                model.save(f"{datapath}/keras/saves/{model_name}/{model_name}.keras")
            else:
                model = read_model(f"{datapath}/keras/saves/{model_name}/{model_name}.keras")
                st.info(f"**CNN模型:green[读取]成功:** {model_name}")

            tc1, tc2 = st.columns(spec=2)
            with st.container(border=True):
                with tc1:
                    # 获取模型字典的参数
                    model_vocab_size = model.get_layer('embedding').input_dim
                    model_embedding_dim = model.get_layer('embedding').output_dim
                    model_max_length = model.get_layer('embedding').input_length
                    # 检查
                    vocab_size_check = vocab_size == model_vocab_size
                    embedding_dim_check = embedding_dim == model_embedding_dim
                    max_length_check = max_length == model_max_length
                    model_check = vocab_size_check & embedding_dim_check & max_length_check
                    padded_check = padded.shape[1] == model_max_length  # 实际深度
                    st.markdown(f'''**字典参数(:orange[当前]/:blue[{model_name}]):**    
> **词汇表大小**(10000): :orange[{vocab_size}]/:blue[{model_vocab_size}] {":green[✅匹配]" if vocab_size_check else ":red[❎不匹配]"}  
> **词嵌入维度**(16): :orange[{embedding_dim}]/:blue[{model_embedding_dim} {":green[✅匹配]" if embedding_dim_check else ":red[❎不匹配]"}]  
> **序列最大长度**(100): :orange[{max_length}]/:blue[{model_max_length}] {":green[✅匹配]" if max_length_check else ":red[❎不匹配]"}  
> **{":red[❎请重构模型]" if not model_check else (":red[⚠️参数更新但缓存过旧, 请刷新缓存]" if not padded_check else ":green[✅模型可以运行]")}**''')
                with tc2:
                    st.markdown(f'''**模型运行参数(:orange[当前]):**  
> **每批次样本数量**: :orange[{batch_size}]  
> **迭代次数**: :orange[{epochs}]  
> **监测指标**: :orange[{patience}]  
> **数据划分(训练/验证)**: 
:orange[{int((1 - validation_split) * len(tokenized_data))}] **/** 
:blue[{int(validation_split * len(tokenized_data))}]''')

            with st.form("train"):
                rebuild_toggle = st.toggle("覆盖", value=False, help="训练完毕后覆盖原模型")
                train_button = st.form_submit_button("开始训练", type="primary", use_container_width=True,
                                                     disabled=not (model_check & padded_check))
            if train_button or st.session_state.retrain:
                st.spinner("模型训练中...")
                # 迭代次数 epochs - yes
                # 每次处理的批次大小 batch_size - yes
                # 优化器 optimizer - no
                # 激活函数 Activation - no
                # 损失函数 Loss_function
                # 如果在连续的 patience 轮训练中,监测指标没有改善,训练将会提前停止.默认值为0,表示没有容忍度,只要监测指标没有改善就会立即停止训练
                early_stopping = EarlyStopping(monitor='val_loss', patience=patience)
                # 降低学习率防止过拟合
                reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=2, min_lr=0.0001)
                # 自定义的回调函数, 包含容器显示和自动保存(覆盖/时间戳命名)
                streamlit_callback = StreamlitLambdaCallback(tokenizer_map=tokenizer,
                                                             model_name=model_name if rebuild_toggle else None)
                model.fit(padded, tokenized_data["sentiment"], epochs=epochs, batch_size=batch_size,
                          validation_split=validation_split,
                          callbacks=[streamlit_callback, reduce_lr, early_stopping])

if use_module:
    # 查询可用模型
    models_list = check_mdoel_had(f"{datapath}/keras/saves")
    hadmodel_check = True if models_list else False
    with st.sidebar:
        with st.expander("**模型预览**", expanded=not hadmodel_check):
            show_models = models_list
            if hadmodel_check:
                show_models = pd.DataFrame(show_models).T.rename(columns={0: "修改日期", 1: "映射表文件"}).rename_axis(
                    "可用模型")
            st.dataframe(show_models, use_container_width=True)
        # 选择模型
        chosen_model = st.selectbox("**选择模型**", models_list.keys(), disabled=not hadmodel_check)
        if hadmodel_check:
            next_check, map_saves = True, True
            if not models_list[chosen_model][1]:
                if os.path.isfile(f"{datapath}/keras/tokenizer.pkl"):
                    st.warning("没有检测到对应的映射文件, 使用全局映射可能出现未知的错误", icon='⚠️')
                    map_saves = False
                else:
                    st.error("没有找到任何映射文件, 请先按照顺序生成", icon='🚫')
                    next_check = False
        else:
            next_check, map_saves = False, False
        # 读取模型
        if hadmodel_check:
            s = time.time()
            predict_model = tf.keras.models.load_model(f"{datapath}/keras/saves/{chosen_model}/{chosen_model}.keras")
            e = time.time()
            st.success(f"**:orange[{chosen_model}]模型**读取成功: {(e - s):.2f}s", icon='✅')
        else:
            predict_model = None
        # 读取映射表
        if next_check:
            if map_saves:
                # 对应文件加载 Tokenizer 对象
                with st.spinner("加载对应映射表..."):
                    s = time.time()
                    predict_tokenizer = read_data(_type="pkl",
                                                  path=f"{datapath}/keras/saves/{chosen_model}/{chosen_model}.pkl")
                    e = time.time()
                st.success(f"**:orange[{chosen_model}]映射表**加载成功: {(e - s):.2f}s", icon='✅')
            else:
                # 对应文件加载 Tokenizer 对象
                with st.spinner("加载全局映射表..."):
                    s = time.time()
                    predict_tokenizer = read_data(_type="pkl", path=f"{datapath}/keras/tokenizer.pkl")
                    e = time.time()
                st.success(f"**全局映射表加载成功:** {(e - s):.2f}s", icon='✅')
        # 清空历史
        if st.button("清空历史记录", use_container_width=True, type="primary",
                     disabled=chosen_model not in st.session_state):
            del st.session_state[chosen_model][:]

    # 模型预测输入
    inputwords = st.chat_input("现在想说点什么?", disabled=not next_check)
    if inputwords:
        # 分词
        cutwords = jieba.lcut(inputwords)
        # 映射
        predict_sequences = predict_tokenizer.texts_to_sequences([' '.join(cutwords)])
        # 补全
        predict_model_max_length = predict_model.get_layer('embedding').input_length  # 获取模型字典的参数
        predict_padded = pad_sequences(predict_sequences, maxlen=predict_model_max_length, padding="post",
                                       truncating="post")
        # 输入然后进行预测
        predict_result = predict_model.predict(predict_padded)
        # 定义类别标签
        labels = {0: "消极", 1: "中性", 2: "积极"}
        color_labels = {0: ":red[消极]", 1: ":grey[中性]", 2: ":green[积极]"}
        show_result = pd.DataFrame(predict_result).rename(columns=labels)
        # 找到最大概率值的索引
        predict_classes = np.argmax(predict_result, axis=1)
        predict_class = predict_classes[0]
        # 存储历史
        st.session_state[chosen_model].append({"图表": show_result,
                                               "输入": inputwords,
                                               "分词": '//'.join(cutwords),
                                               "结论": color_labels[predict_class],
                                               "日期": time.strftime("%Y-%m-%d %H:%M:%S",
                                                                     time.localtime(time.time()))})
    # 打印情感类别
    if next_check:
        # 存储对应模型的记录
        st.session_state.setdefault(chosen_model, [])
        for output in st.session_state[chosen_model]:
            with st.chat_message("🧊"):
                with st.container(border=True):
                    st.dataframe(output["图表"], use_container_width=True, hide_index=True)
                    st.success("**情感判别结果**", icon='🧊')
                    st.info(f'''
> **输入:**  ***:blue[{output["输入"]}]***  
> **分词:** {output["分词"]}  
> **结论:** ***{output["结论"]}***''')
                    st.markdown(f"📌: *:grey[{output['日期']}]* - 🧊: *:orange[{chosen_model}]*")
