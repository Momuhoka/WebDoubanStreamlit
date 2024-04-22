import time

import streamlit as st
import codecs
from snownlp.classification.bayes import Bayes
from snownlp.sentiment import Sentiment
from snownlp.utils.frequency import AddOneProb


class StreamlitBayes(Bayes):
    def __init__(self):
        super().__init__()
        self.holder = None

    def train(self, data):
        self.holder = st.empty()
        length = len(data)
        s = time.time()
        self.holder.progress(value=0, text=f"训练进度: 0/{length}")
        for index, d in enumerate(data):
            self.holder.progress(value=(index + 1) / length, text=f"训练进度: {index + 1}/{length}")
            c = d[1]
            if c not in self.d:
                self.d[c] = AddOneProb()
            for word in d[0]:
                self.d[c].add(word, 1)
        e = time.time()
        self.holder.info(f"**训练完毕:** :orange[{e - s:.2f}]s")
        self.total = sum(map(lambda x: self.d[x].getsum(), self.d.keys()))


class StreamlitSentiment(Sentiment):
    def __init__(self):
        self.classifier = StreamlitBayes()
        super().__init__()
        self.holder = None

    def train(self, neg_docs, pos_docs):
        data = []
        self.holder = st.empty()
        neg_length = len(neg_docs)
        pos_length = len(pos_docs)
        s = time.time()
        self.holder.progress(value=0, text=f"NEG处理进度: 0/{neg_length}")
        for index, sent in enumerate(neg_docs):
            self.holder.progress(value=(index + 1) / neg_length, text=f"NEG处理进度: {index + 1}/{neg_length}")
            data.append([self.handle(sent), 'neg'])
        e = time.time()
        self.holder.info(f"**NEG处理完毕:** :orange[{e-s:.2f}]s")
        s = time.time()
        self.holder.progress(value=0, text=f"POS处理进度: 0/{pos_length}")
        for index, sent in enumerate(pos_docs):
            self.holder.progress(value=(index + 1) / pos_length, text=f"POS处理进度: {index + 1}/{pos_length}")
            data.append([self.handle(sent), 'pos'])
        e = time.time()
        self.holder.info(f"**POS处理完毕:** :orange[{e-s:.2f}]s")
        self.classifier.train(data)


classifier = StreamlitSentiment()
classifier.load()


def train(neg_file, pos_file):
    st.spinner("读取文件中...")
    s1 = time.time()
    neg_docs = codecs.open(neg_file, 'r', 'utf-8').readlines()
    s2 = time.time()
    pos_docs = codecs.open(pos_file, 'r', 'utf-8').readlines()
    s3 = time.time()
    st.info(f"**读取完毕:** :red[NEG]: :orange[{s2-s1:.2f}]s / :green[POS]: :orange[{s3-s2:.2f}]s")
    t1, t2 = st.tabs(["NEG", "POS"])
    with t1:
        st.dataframe(neg_docs, use_container_width=True)
    with t2:
        st.dataframe(pos_docs, use_container_width=True)
    global classifier
    classifier = StreamlitSentiment()
    classifier.train(neg_docs, pos_docs)


def save(fname, iszip=True):
    classifier.save(fname, iszip)


def load(fname, iszip=True):
    classifier.load(fname, iszip)


def classify(sent):
    return classifier.classify(sent)
