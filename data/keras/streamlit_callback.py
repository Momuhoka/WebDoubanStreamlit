import os
import pickle
import time

import tensorflow as tf
import streamlit as st
import plotly.graph_objects as go

# 部分文件存储位置
datapath = "./data"


class StreamlitLambdaCallback(tf.keras.callbacks.LambdaCallback):
    def __init__(self, tokenizer_map, model_name=None, **kwargs):
        super().__init__()
        self.tokenizer_map = tokenizer_map
        self.model_name = model_name
        self.__dict__.update(kwargs)
        self.progress_empty = None
        self._progress_empty = None
        self.loss_empty = None
        self.delta_loss_empty = None
        self.delta_accuracy_empty = None
        self.accuracy_empty = None
        self.fig_1 = None
        self.fig_2 = None
        self.fig_1_empty = None
        self.fig_2_empty = None
        self.end_empty = None
        self.train_loss = []
        self.train_accuracy = []
        self.previous_val_loss = 0.0
        self.previous_val_accuracy = 0.0

    def on_train_begin(self, logs=None):
        with st.container(border=True):
            # 进度条
            self.progress_empty = st.empty()
            self.progress_empty.progress(value=0, text=f"Epochs: 0/{self.params['epochs']}")
            c1, c2 = st.columns(spec=2)
            with c1:
                # 小进度条
                self._progress_empty = st.empty()
                self._progress_empty.progress(value=0, text=f"Steps: 0/{self.params['steps']}")
                c1_1, c2_2 = st.columns(spec=2)
                with c1_1:
                    with st.container(border=True):
                        self.loss_empty = st.empty()
                        st.info(
                            "损失函数-衡量模型预测结果与实际标签之间的差异程度, 损失函数值越小表示模型的预测结果与实际越接近",
                            icon="ℹ️")
                        self.delta_loss_empty = st.empty()
                with c2_2:
                    with st.container(border=True):
                        self.accuracy_empty = st.empty()
                        st.info(
                            "准确率-是一个表示分类模型性能的指标, 它代表模型正确分类样本的比例, 准确率的取值范围在0到1之间",
                            icon="ℹ️")
                        self.delta_accuracy_empty = st.empty()
                self.end_empty = st.empty()
            with c2:
                with st.container(border=True):
                    c3, c4 = st.columns(spec=2)
                    with c3:
                        self.fig_1_empty = st.empty()
                    with c4:
                        self.fig_2_empty = st.empty()
        # 初始化
        self.loss_empty.markdown(f"> **训练损失:** :red[等待...]")
        self.accuracy_empty.markdown(f"> **训练准确率:** :green[等待...]")
        self.delta_loss_empty.metric("Val_loss", value=0, delta=0, help="使用验证数据集进行评估时的损失值")
        self.delta_accuracy_empty.metric("Val_accuracy", value="0.00%", delta="0.00%", help="使用验证数据集进行评估时的准确率")
        self.fig_1 = go.Figure(layout=go.Layout(title="训练损失", xaxis={"title": "轮数"}, yaxis={"title": "损失"}))
        self.fig_2 = go.Figure(layout=go.Layout(title="训练准确率", xaxis={"title": "轮数"}, yaxis={"title": "准确度"}))
        self.fig_1_empty.plotly_chart(self.fig_1, use_container_width=True)
        self.fig_2_empty.plotly_chart(self.fig_2, use_container_width=True)

    def on_batch_end(self, batch, logs=None):
        # 小进度条更新
        self._progress_empty.progress(value=(batch + 1) / self.params['steps'],
                                      text=f"Steps: {batch + 1}/{self.params['steps']}")
        # 数据更新
        self.loss_empty.markdown(f"> **训练损失:** :red[{logs['loss']:.4f}]")
        self.accuracy_empty.markdown(f"> **训练准确率:** :green[{logs['accuracy'] * 100:.2f}%]")

    def on_epoch_end(self, epoch, logs=None):
        # 进度条更新
        self.progress_empty.progress(value=(epoch + 1) / self.params['epochs'],
                                     text=f"Epochs: {epoch + 1}/{self.params['epochs']}")
        # 获取当前训练进度
        self.train_loss.append(logs["val_loss"])
        self.train_accuracy.append(logs["val_accuracy"])
        # 计算变化值
        current_val_loss = logs["val_loss"]
        loss_delta = current_val_loss - self.previous_val_loss
        self.delta_loss_empty.metric("Val_loss",
                                     value=f"{current_val_loss:.2f}",
                                     delta=f"{loss_delta:.2f}",
                                     delta_color="inverse",  # 损失值越小越好, 颜色翻转
                                     help="使用验证数据集进行评估时的损失值")
        self.previous_val_loss = current_val_loss
        current_val_accuracy = logs["val_accuracy"]
        accuracy_delta = current_val_accuracy - self.previous_val_accuracy
        self.delta_accuracy_empty.metric("Val_accuracy",
                                         value=f"{current_val_accuracy * 100:.2f}%",
                                         delta=f"{accuracy_delta * 100:.2f}%",
                                         help="使用验证数据集进行评估时的准确率")
        self.previous_val_accuracy = current_val_accuracy
        # 添加训练损失图
        self.fig_1.add_trace(go.Scatter(x=list(range(1, epoch + 2)), y=self.train_loss, showlegend=False))
        # 添加训练准确率图
        self.fig_2.add_trace(go.Scatter(x=list(range(1, epoch + 2)), y=self.train_accuracy, showlegend=False))
        # 刷新图表展示
        self.fig_1_empty.plotly_chart(self.fig_1, use_container_width=True)
        self.fig_2_empty.plotly_chart(self.fig_2, use_container_width=True)

    def on_train_end(self, logs=None):
        if self.model_name is None:
            self.model_name = time.strftime("%Y_%m_%d %H_%M_%S", time.localtime(time.time()))
        # 清空进度条
        self.progress_empty.empty()
        self._progress_empty.empty()
        s = time.time()
        if not os.path.exists(f"{datapath}/keras/saves/{self.model_name}"):
            os.makedirs(f"{datapath}/keras/saves/{self.model_name}")  # 递归创建文件夹
        self.model.save(f"{datapath}/keras/saves/{self.model_name}/{self.model_name}.keras")
        with open(f"{datapath}/keras/saves/{self.model_name}/{self.model_name}.pkl", "wb") as file:
            pickle.dump(self.tokenizer_map, file)
        e = time.time()
        self.end_empty.success(f"成功保存:orange[{self.model_name}]模型与映射文件: {(e-s):.2f}s", icon='♾️')