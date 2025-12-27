# -*- coding: utf-8 -*-
import threading
import re
import os
import sys
from collections import Counter
import argparse
from datetime import datetime
from typing import Dict, List, Callable, Optional
import queue
# PyQt5相关导入
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLabel,
                             QProgressBar, QFileDialog, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QSplitter, QMessageBox,
                             QListWidget, QListWidgetItem, QCheckBox,QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib

matplotlib.use('Qt5Agg')

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False


class WordCounter:
    def __init__(self):
        self.total_words = 0
        self.lock = threading.Lock()
        self.file_stats = {}
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def count_words_in_file(self, filename: str) -> Dict:
        """统计单个文件的词频 - 符合图片中的原则"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            # 修改正则表达式以符合图片原则：匹配连续的字母或数字字符
            words = re.findall(r'[a-zA-Z0-9]+', content)
            word_count = len(words)

            # 获取词频统计（转换为小写以便合并相同单词）
            word_freq = Counter([word.lower() for word in words])

            # 使用锁保护共享资源
            with self.lock:
                self.total_words += word_count
                self.file_stats[filename] = {
                    'word_count': word_count,
                    'word_frequency': word_freq,
                    'top_words': word_freq.most_common(10)
                }

            # 更新进度
            if self.progress_callback:
                self.progress_callback(filename, word_count)

            return self.file_stats[filename]

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            return {}

    def process_files_multithreaded(self, file_list: List[str]) -> None:
        """使用多线程处理多个文件"""
        threads = []

        for filename in file_list:
            thread = threading.Thread(target=self.count_words_in_file, args=(filename,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

    def get_statistics(self) -> Dict:
        """获取完整的统计信息"""
        return {
            'total_words': self.total_words,
            'files_processed': len(self.file_stats),
            'file_statistics': self.file_stats,
            'combined_word_frequency': self.get_combined_word_frequency(),
            'average_words_per_file': self.total_words / len(self.file_stats) if self.file_stats else 0
        }

    def get_combined_word_frequency(self) -> Counter:
        """获取所有文件的合并词频统计"""
        combined_freq = Counter()
        for stats in self.file_stats.values():
            combined_freq.update(stats['word_frequency'])
        return combined_freq



class WordCounter2:
    def __init__(self):
        self.total_words = 0
        self.file_stats = {}
        self.progress_callback = None
        self.result_queue = queue.Queue()  # 用于收集线程结果

    def set_progress_callback(self, callback: Callable[[str, int], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

    def count_words_in_file(self, filename: str) -> Dict:
        """统计单个文件的词频 - 独立统计，不更新共享变量"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            # 匹配连续的字母或数字字符
            words = re.findall(r'[a-zA-Z0-9]+', content)
            word_count = len(words)
            
            # 获取词频统计（转换为小写以便合并相同单词）
            word_freq = Counter([word.lower() for word in words])
            
            # 创建独立的结果字典
            result = {
                'word_count': word_count,
                'word_frequency': word_freq,
                'top_words': word_freq.most_common(10)
            }
            
            # 将结果放入队列
            self.result_queue.put((filename, result))
            
            # 更新进度
            if self.progress_callback:
                self.progress_callback(filename, word_count)
                
            return result
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            # 即使出错也放入空结果，保持队列完整
            self.result_queue.put((filename, {
                'word_count': 0,
                'word_frequency': Counter(),
                'top_words': []
            }))
            return {}

    def process_files_multithreaded(self, file_list: List[str]) -> None:
        """使用多线程处理多个文件，独立统计，最后合并结果"""
        threads = []
        
        # 重置队列
        self.result_queue = queue.Queue()
        
        for filename in file_list:
            thread = threading.Thread(target=self.count_words_in_file, args=(filename,))
            threads.append(thread)
            thread.start()
            
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
        # 从队列中收集所有结果并合并
        self._merge_results(len(file_list))

    def _merge_results(self, file_count: int):
        """从队列中收集结果并合并到类属性中"""
        self.file_stats = {}
        self.total_words = 0
        
        # 收集所有文件的结果
        for _ in range(file_count):
            filename, result = self.result_queue.get()
            self.file_stats[filename] = result
            self.total_words += result['word_count']

    def get_statistics(self) -> Dict:
        """获取完整的统计信息"""
        return {
            'total_words': self.total_words,
            'files_processed': len(self.file_stats),
            'file_statistics': self.file_stats,
            'combined_word_frequency': self.get_combined_word_frequency(),
            'average_words_per_file': self.total_words / len(self.file_stats) if self.file_stats else 0
        }

    def get_combined_word_frequency(self) -> Counter:
        """获取所有文件的合并词频统计"""
        combined_freq = Counter()
        for stats in self.file_stats.values():
            combined_freq.update(stats['word_frequency'])
        return combined_freq

class MplCanvas(FigureCanvas):
    """Matplotlib画布 - 修复图表状态残留问题"""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def clear_plot(self):
        """彻底清除图表状态 - 修复图表残留问题"""
        # 完全清除图形
        self.fig.clf()
        # 重新创建子图
        self.axes = self.fig.add_subplot(111)
        # 清除所有文本和图形元素
        self.axes.clear()
        # 重置坐标轴
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.set_frame_on(False)
        # 强制重绘
        self.draw_idle()

class AnalysisThread(QThread):
    """分析线程"""
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, file_list,counter_type):
        super().__init__()
        self.file_list = file_list
        self.counter = WordCounter()
        self.counter_type = counter_type
        # 根据类型创建计数器
        if counter_type == "shared":
                self.counter = WordCounter()
        else:
                self.counter = WordCounter2()

    def run(self):
        try:
            # 设置进度回调
            self.counter.set_progress_callback(self.update_progress)
            self.counter.process_files_multithreaded(self.file_list)
            self.finished_signal.emit(self.counter)
        except Exception as e:
            self.error_signal.emit(str(e))

    def update_progress(self, filename, word_count):
        self.progress_signal.emit(filename, word_count)


class WordCounterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.counter = WordCounter()
        self.selected_files = []
        self.analysis_history = []
        self.analysis_completed = False
        self.current_chart_type = None
        self.init_ui()
        self.setWindowTitle("词频统计可视化工具 - 多文件分析")
        self.setGeometry(100, 100, 1400, 900)

        # 在WordCounterGUI类的init_ui方法中添加计数器选择控件
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_splitter = QSplitter(Qt.Horizontal)
        layout = QVBoxLayout(central_widget)
        layout.addWidget(main_splitter)

        # 左侧文件管理面板
        self.setup_file_panel(main_splitter)

        # 右侧主内容区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        main_splitter.addWidget(right_widget)

        # 添加计数器类型选择控件
        counter_layout = QHBoxLayout()
        counter_layout.addWidget(QLabel("计数器类型:"))
        
        self.counter_type_combo = QComboBox()
        self.counter_type_combo.addItem("WordCounter (共享计数)", "shared")
        self.counter_type_combo.addItem("WordCounter2 (独立计数)", "independent")
        self.counter_type_combo.setCurrentIndex(0)
        self.counter_type_combo.currentIndexChanged.connect(self.on_counter_type_changed)
        
        counter_layout.addWidget(self.counter_type_combo)
        counter_layout.addStretch()
        
        right_layout.addLayout(counter_layout)

        self.tabs = QTabWidget()
        # 关键修复：连接标签页切换信号
        self.tabs.currentChanged.connect(self.on_tab_changed)
        right_layout.addWidget(self.tabs)

        self.setup_control_tab()
        self.setup_visualization_tab()
        self.setup_data_tab()

        main_splitter.setSizes([300, 1100])

    def on_counter_type_changed(self, index):
        """计数器类型改变时的处理"""
        counter_type = self.counter_type_combo.currentData()
        self.log_message(f"计数器类型已更改为: {self.counter_type_combo.currentText()}")
        
        # 重置分析状态
        self.analysis_completed = False
        self.current_chart_type = None
        self.show_welcome_message()
        
        # 根据选择的类型创建新的计数器实例
        if counter_type == "shared":
            self.counter = WordCounter()
        else:
            self.counter = WordCounter2()
        
        # 清空数据表格
        self.data_table.setRowCount(0)
        self.summary_label.setText("暂无统计数据")
        
        # 禁用图表按钮
        self.set_chart_buttons_enabled(False)

    

    # 在WordCounterGUI类的start_analysis方法中修改线程创建
    def start_analysis(self):
        """开始分析过程"""
        if not self.selected_files:
            QMessageBox.warning(self, "警告", "请先添加要分析的文件")
            return

        # 确定要分析的文件列表
        if self.only_selected_cb.isChecked():
            selected_items = self.file_list_widget.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选择要分析的文件")
                return
            files_to_analyze = [self.selected_files[self.file_list_widget.row(item)]
                                for item in selected_items]
        else:
            files_to_analyze = self.selected_files

        # 获取当前选择的计数器类型
        counter_type = self.counter_type_combo.currentData()
        
        # 检查是否追加分析
        if not self.append_analysis_cb.isChecked():
            # 不追加分析，重置计数器
            if counter_type == "shared":
                self.counter = WordCounter()
            else:
                self.counter = WordCounter2()
                
            self.data_table.setRowCount(0)
            self.analysis_completed = False
            self.current_chart_type = None
            self.log_message("开始新的分析会话...")

            # 重置图表显示
            self.show_welcome_message()

        # 重置界面状态
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files_to_analyze))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.delete_selected_btn.setEnabled(False)
        self.clear_list_btn.setEnabled(False)
        self.status_label.setText("分析中...")

        # 禁用图表按钮直到分析完成
        self.set_chart_buttons_enabled(False)

        # 显示分析中状态
        self.canvas.clear_plot()
        self.canvas.axes.text(0.5, 0.5, '分析中...\n请稍候',
                            ha='center', va='center', fontsize=14,
                            transform=self.canvas.axes.transAxes)
        self.canvas.draw()

        # 启动分析线程
        self.analysis_thread = AnalysisThread(files_to_analyze, counter_type)
        self.analysis_thread.progress_signal.connect(self.update_progress)
        self.analysis_thread.finished_signal.connect(self.analysis_finished)
        self.analysis_thread.error_signal.connect(self.analysis_error)
        self.analysis_thread.start()

        self.log_message(f"开始分析 {len(files_to_analyze)} 个文件...")
        self.log_message(f"使用计数器: {self.counter_type_combo.currentText()}")

    # 在analysis_finished方法中添加计数器类型信息
    def analysis_finished(self, counter):
        """分析完成处理"""
        # 关键修复：更新主counter对象
        if not self.append_analysis_cb.isChecked():
            # 新建分析：直接替换counter
            self.counter = counter
        else:
            # 追加分析：合并数据
            self.counter.total_words += counter.total_words
            self.counter.file_stats.update(counter.file_stats)

        self.start_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.delete_selected_btn.setEnabled(True)
        self.clear_list_btn.setEnabled(True)
        self.status_label.setText("分析完成")
        self.analysis_completed = True

        # 启用图表按钮
        self.set_chart_buttons_enabled(True)

        # 更新统计摘要
        results = self.counter.get_statistics()
        self.update_summary(results)
        self.log_message(f"所有文件处理完成！总词数: {results['total_words']}")
        self.log_message(f"使用的计数器: {self.counter_type_combo.currentText()}")

        # 自动显示图表
        QTimer.singleShot(100, self.plot_file_statistics)

    def on_tab_changed(self, index):
        """标签页切换时的处理 - 关键修复：解决图表显示异常"""
        tab_name = self.tabs.tabText(index)
        if tab_name == "数据可视化" and self.analysis_completed:
            # 使用较长的延迟确保画布完全显示
            QTimer.singleShot(300, self.redraw_current_chart)

    def redraw_current_chart(self):
        """重新绘制当前图表 - 解决切换标签页后图表显示异常问题"""
        if not self.analysis_completed:
            return

        # 如果当前没有图表类型，默认显示文件统计图
        if self.current_chart_type is None:
            self.current_chart_type = "file_statistics"

        if self.current_chart_type == "word_frequency":
            self.plot_word_frequency()
        elif self.current_chart_type == "file_statistics":
            self.plot_file_statistics()
        elif self.current_chart_type == "top_words":
            self.plot_top_words()
        else:
            # 默认显示文件统计图
            self.plot_file_statistics()

    def setup_file_panel(self, parent_splitter):
        """设置文件管理面板"""
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)

        # 第一行按钮：添加文件相关
        btn_layout1 = QHBoxLayout()
        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)

        btn_layout1.addWidget(self.add_files_btn)
        btn_layout1.addWidget(self.add_folder_btn)
        btn_layout1.addStretch()

        # 第二行按钮：删除相关
        btn_layout2 = QHBoxLayout()
        self.delete_selected_btn = QPushButton("删除选中")
        self.delete_selected_btn.clicked.connect(self.delete_selected_files)
        self.clear_list_btn = QPushButton("清空列表")
        self.clear_list_btn.clicked.connect(self.clear_files)

        btn_layout2.addWidget(self.delete_selected_btn)
        btn_layout2.addWidget(self.clear_list_btn)
        btn_layout2.addStretch()

        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.file_stats_label = QLabel("已选择 0 个文件")

        options_layout = QVBoxLayout()
        self.append_analysis_cb = QCheckBox("追加分析（保留历史数据）")
        self.append_analysis_cb.setChecked(True)
        self.only_selected_cb = QCheckBox("仅分析选中的文件")

        options_layout.addWidget(self.append_analysis_cb)
        options_layout.addWidget(self.only_selected_cb)

        file_layout.addLayout(btn_layout1)
        file_layout.addLayout(btn_layout2)
        file_layout.addWidget(QLabel("文件列表:"))
        file_layout.addWidget(self.file_list_widget)
        file_layout.addWidget(self.file_stats_label)
        file_layout.addLayout(options_layout)

        parent_splitter.addWidget(file_widget)

    def setup_control_tab(self):
        """设置控制选项卡"""
        control_tab = QWidget()
        layout = QVBoxLayout(control_tab)

        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始分析")
        self.start_btn.clicked.connect(self.start_analysis)
        self.start_btn.setEnabled(False)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_analysis)
        self.pause_btn.setEnabled(False)

        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.clear_log_btn)
        control_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("准备就绪")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        font = QFont("Microsoft YaHei", 9)
        self.log_text.setFont(font)

        layout.addLayout(control_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("处理日志:"))
        layout.addWidget(self.log_text)

        self.tabs.addTab(control_tab, "控制面板")

    def setup_visualization_tab(self):
        """设置可视化选项卡"""
        viz_tab = QWidget()
        layout = QVBoxLayout(viz_tab)

        btn_layout = QHBoxLayout()
        self.word_freq_btn = QPushButton("显示词频分布")
        self.word_freq_btn.clicked.connect(self.plot_word_frequency)
        self.file_stats_btn = QPushButton("显示文件统计")
        self.file_stats_btn.clicked.connect(self.plot_file_statistics)
        self.top_words_btn = QPushButton("显示高频词汇")
        self.top_words_btn.clicked.connect(self.plot_top_words)
        self.export_chart_btn = QPushButton("导出图表")
        self.export_chart_btn.clicked.connect(self.export_chart)

        # 初始禁用图表按钮
        self.word_freq_btn.setEnabled(False)
        self.file_stats_btn.setEnabled(False)
        self.top_words_btn.setEnabled(False)
        self.export_chart_btn.setEnabled(False)

        btn_layout.addWidget(self.word_freq_btn)
        btn_layout.addWidget(self.file_stats_btn)
        btn_layout.addWidget(self.top_words_btn)
        btn_layout.addWidget(self.export_chart_btn)
        btn_layout.addStretch()

        self.canvas = MplCanvas(self, width=10, height=8)
        self.show_welcome_message()

        layout.addLayout(btn_layout)
        layout.addWidget(self.canvas)

        self.tabs.addTab(viz_tab, "数据可视化")

    def show_welcome_message(self):
        """显示欢迎消息"""
        self.canvas.clear_plot()
        self.canvas.axes.text(0.5, 0.5,
                              '欢迎使用词频统计可视化工具\n\n请先添加文件并完成分析\n然后点击上方按钮查看图表',
                              ha='center', va='center', fontsize=14,
                              transform=self.canvas.axes.transAxes)
        self.canvas.draw()

    def setup_data_tab(self):
        """设置详细数据选项卡"""
        data_tab = QWidget()
        layout = QVBoxLayout(data_tab)

        self.summary_label = QLabel("暂无统计数据")
        self.summary_label.setWordWrap(True)
        self.summary_label.setFont(QFont("Microsoft YaHei", 10))

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["文件名", "词数", "处理时间", "状态"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        font = QFont("Microsoft YaHei", 9)
        self.data_table.setFont(font)

        layout.addWidget(QLabel("统计摘要:"))
        layout.addWidget(self.summary_label)
        layout.addWidget(QLabel("详细数据:"))
        layout.addWidget(self.data_table)

        self.tabs.addTab(data_tab, "详细数据")

    def add_files(self):
        """添加文件到列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文本文件", "", "Text Files (*.txt);;All Files (*)"
        )
        if files:
            self.add_files_to_list(files)

    def add_folder(self):
        """添加文件夹中的所有文本文件"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            txt_files = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.txt'):
                        txt_files.append(os.path.join(root, file))

            if txt_files:
                self.add_files_to_list(txt_files)
            else:
                QMessageBox.information(self, "提示", "该文件夹中没有找到文本文件")

    def add_files_to_list(self, files):
        """将文件添加到列表（去重）"""
        new_files = []
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                new_files.append(file)

                item = QListWidgetItem(os.path.basename(file))
                item.setToolTip(file)
                self.file_list_widget.addItem(item)

        if new_files:
            self.update_file_stats()
            self.start_btn.setEnabled(True)
            self.log_message(f"添加了 {len(new_files)} 个新文件")
        else:
            self.log_message("没有添加新文件（所有文件已存在）")

    def delete_selected_files(self):
        """删除选中的文件"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的文件")
            return

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除选中的 {len(selected_items)} 个文件吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 从后往前删除，避免索引变化问题
            for item in reversed(selected_items):
                row = self.file_list_widget.row(item)
                removed_file = self.selected_files.pop(row)
                self.file_list_widget.takeItem(row)
                self.log_message(f"已删除文件: {os.path.basename(removed_file)}")

            self.update_file_stats()

            # 如果没有文件了，禁用开始分析按钮
            if not self.selected_files:
                self.start_btn.setEnabled(False)
                self.log_message("文件列表已为空")

    def clear_files(self):
        """清空文件列表"""
        if not self.selected_files:
            QMessageBox.information(self, "提示", "文件列表已经是空的")
            return

        reply = QMessageBox.question(self, "确认清空",
                                     "确定要清空整个文件列表吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.selected_files.clear()
            self.file_list_widget.clear()
            self.update_file_stats()
            self.start_btn.setEnabled(False)
            self.log_message("已清空文件列表")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_message("日志已清空")

    def update_file_stats(self):
        """更新文件统计信息"""
        count = len(self.selected_files)
        total_size = sum(os.path.getsize(f) for f in self.selected_files if os.path.exists(f))
        self.file_stats_label.setText(f"已选择 {count} 个文件，总大小: {total_size / 1024:.1f} KB")

    

    def pause_analysis(self):
        """暂停分析"""
        QMessageBox.information(self, "提示", "暂停功能正在开发中")

    def update_progress(self, filename, word_count):
        """更新进度显示"""
        current_value = self.progress_bar.value()
        self.progress_bar.setValue(current_value + 1)

        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        self.data_table.setItem(row, 0, QTableWidgetItem(os.path.basename(filename)))
        self.data_table.setItem(row, 1, QTableWidgetItem(str(word_count)))
        self.data_table.setItem(row, 2, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.data_table.setItem(row, 3, QTableWidgetItem("完成"))

        self.log_message(f"处理完成: {os.path.basename(filename)} - {word_count} 个词")

    

    def set_chart_buttons_enabled(self, enabled):
        """设置图表按钮的启用状态"""
        self.word_freq_btn.setEnabled(enabled)
        self.file_stats_btn.setEnabled(enabled)
        self.top_words_btn.setEnabled(enabled)
        self.export_chart_btn.setEnabled(enabled)

    def analysis_error(self, error_msg):
        """分析错误处理"""
        self.start_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.delete_selected_btn.setEnabled(True)
        self.clear_list_btn.setEnabled(True)
        self.status_label.setText("分析出错")
        self.analysis_completed = False
        self.set_chart_buttons_enabled(False)
        self.log_message(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"分析过程中出现错误:\n{error_msg}")

    def update_summary(self, results):
        """更新统计摘要"""
        summary_text = f"""
        <b>统计分析结果摘要:</b><br>
        - 总词数: {results['total_words']:,}<br>
        - 处理文件数: {results['files_processed']}<br>
        - 平均每文件词数: {results['average_words_per_file']:,.1f}<br>
        - 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        """
        self.summary_label.setText(summary_text)

        self.analysis_history.append({
            'timestamp': datetime.now(),
            'results': results
        })

    def plot_word_frequency(self):
        """绘制词频分布图 - 修复图表状态残留问题"""
        if not self.analysis_completed or not self.counter.file_stats:
            QMessageBox.information(self, "提示", "请先完成文件分析")
            return

        try:
            # 关键修复：彻底清除画布状态
            self.canvas.clear_plot()

            combined_freq = self.counter.get_combined_word_frequency()

            if len(combined_freq) == 0:
                self.canvas.axes.text(0.5, 0.5, '无数据', ha='center', va='center')
                self.canvas.draw()
                return

            # 取前20个高频词
            top_words = combined_freq.most_common(20)
            words, counts = zip(*top_words)

            y_pos = range(len(words))
            bars = self.canvas.axes.barh(y_pos, counts, color='skyblue')
            self.canvas.axes.set_yticks(y_pos)
            self.canvas.axes.set_yticklabels(words)
            self.canvas.axes.set_xlabel('出现次数')
            self.canvas.axes.set_title('Top 20 高频词汇分布')

            # 在条形上显示数值
            for i, count in enumerate(counts):
                self.canvas.axes.text(count, i, f' {count}', va='center')

            self.canvas.fig.tight_layout()
            self.canvas.draw()
            self.current_chart_type = "word_frequency"
            self.log_message("词频分布图已更新")

        except Exception as e:
            self.log_message(f"绘制词频分布图时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"绘制图表时出错:\n{str(e)}")

    def plot_file_statistics(self):
        """绘制文件统计图 - 修复图表状态残留问题"""
        if not self.analysis_completed or not self.counter.file_stats:
            QMessageBox.information(self, "提示", "请先完成文件分析")
            return

        try:
            # 关键修复：彻底清除画布状态
            self.canvas.clear_plot()

            filenames = [os.path.basename(f) for f in self.counter.file_stats.keys()]
            word_counts = [stats['word_count'] for stats in self.counter.file_stats.values()]

            if len(filenames) == 0 or len(word_counts) == 0:
                self.canvas.axes.text(0.5, 0.5, '无数据', ha='center', va='center')
                self.canvas.draw()
                return

            y_pos = range(len(filenames))
            bars = self.canvas.axes.barh(y_pos, word_counts, color='lightgreen')
            self.canvas.axes.set_yticks(y_pos)
            self.canvas.axes.set_yticklabels(filenames)
            self.canvas.axes.set_xlabel('词数')
            self.canvas.axes.set_title('各文件词数统计')

            # 在条形上显示数值
            for bar, count in zip(bars, word_counts):
                width = bar.get_width()
                self.canvas.axes.text(width, bar.get_y() + bar.get_height() / 2,
                                      f' {count}', va='center')

            self.canvas.fig.tight_layout()
            self.canvas.draw()
            self.current_chart_type = "file_statistics"
            self.log_message(f"文件统计图已更新 - 显示 {len(filenames)} 个文件")

        except Exception as e:
            self.log_message(f"绘制文件统计图时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"绘制图表时出错:\n{str(e)}")

    def plot_top_words(self):
        """绘制高频词饼图 - 修复图表状态残留问题"""
        if not self.analysis_completed or not self.counter.file_stats:
            QMessageBox.information(self, "提示", "请先完成文件分析")
            return

        try:
            # 关键修复：彻底清除画布状态
            self.canvas.clear_plot()

            combined_freq = self.counter.get_combined_word_frequency()

            if len(combined_freq) == 0:
                self.canvas.axes.text(0.5, 0.5, '无数据', ha='center', va='center')
                self.canvas.draw()
                return

            # 取前10个高频词
            top_words = combined_freq.most_common(10)
            words, counts = zip(*top_words)

            # 绘制饼图
            wedges, texts, autotexts = self.canvas.axes.pie(
                counts, labels=words, autopct='%1.1f%%', startangle=90
            )
            self.canvas.axes.set_title('Top 10 高频词汇占比')

            self.canvas.fig.tight_layout()
            self.canvas.draw()
            self.current_chart_type = "top_words"
            self.log_message("高频词饼图已更新")

        except Exception as e:
            self.log_message(f"绘制高频词饼图时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"绘制图表时出错:\n{str(e)}")

    def export_chart(self):
        """导出图表为图片"""
        if not self.analysis_completed:
            QMessageBox.information(self, "提示", "请先完成文件分析并生成图表")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图表", f"word_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)"
        )

        if file_path:
            try:
                self.canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                self.log_message(f"图表已导出到: {file_path}")
            except Exception as e:
                self.log_message(f"导出图表失败: {str(e)}")

    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        parser = argparse.ArgumentParser(description='多线程词频统计工具')
        parser.add_argument('files', nargs='+', help='要处理的文件列表')
        parser.add_argument('--output', '-o', help='输出文件')
        parser.add_argument('--format', '-f', choices=['text', 'json'], default='text',
                            help='输出格式')

        args = parser.parse_args()

        valid_files = []
        for file in args.files:
            if os.path.exists(file):
                valid_files.append(file)
            else:
                print(f"警告: 文件 {file} 不存在，已跳过")

        if not valid_files:
            print("错误: 没有有效的文件可处理")
            return

        counter = WordCounter()
        counter.process_files_multithreaded(valid_files)

        if args.format == 'json':
            import json
            result = counter.get_statistics()
            result['combined_word_frequency'] = dict(result['combined_word_frequency'])
            for file_stat in result['file_statistics'].values():
                file_stat['word_frequency'] = dict(file_stat['word_frequency'])

            output = json.dumps(result, indent=2)
        else:
            output = f"总词数: {counter.total_words}\n"
            for filename, stats in counter.file_stats.items():
                output += f"{filename}: {stats['word_count']} 个词\n"

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"结果已保存到 {args.output}")
        else:
            print(output)
    else:
        # GUI模式
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        # 设置应用程序字体
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)

        window = WordCounterGUI()
        window.show()

        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
