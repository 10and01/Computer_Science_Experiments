import matplotlib
import heapq
import matplotlib.patches as patches
from matplotlib import animation
import numpy as np
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.font_manager import FontProperties

# 设置matplotlib使用支持中文的字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


class Process:
    def __init__(self, name, arrival, burst, priority=0):
        self.name = name
        self.arrival = arrival
        self.burst = burst
        self.priority = priority
        self.start_time = -1
        self.finish_time = -1
        self.remaining = burst
        self.last_run = arrival
        self.response_ratio = 0.0
        self.running_intervals = []  # 记录进程运行的时间区间
        self.waiting_intervals = []  # 记录进程等待的时间区间

    def reset(self):
        self.start_time = -1
        self.finish_time = -1
        self.remaining = self.burst
        self.last_run = self.arrival
        self.response_ratio = 0.0
        self.running_intervals = []
        self.waiting_intervals = []


class Event:
    def __init__(self, time, event_type, process):
        self.time = time
        self.type = event_type
        self.process = process

    def __lt__(self, other):
        return self.time < other.time


class SchedulerSimulator:
    PROCESS_ARRIVAL = 0
    PROCESS_START = 1
    PROCESS_COMPLETE = 2
    TIME_SLICE_EXPIRED = 3

    def __init__(self, processes, algorithm, quantum=1):
        self.processes = processes
        self.algorithm = algorithm
        self.quantum = quantum
        self.current_time = 0
        self.current_process = None
        self.ready_queue = deque()
        self.event_queue = []
        self.timeline = []
        self.gantt_data = []

        # 重置所有进程状态
        for p in self.processes:
            p.reset()

        # 添加所有进程的到达事件
        for p in self.processes:
            heapq.heappush(self.event_queue, Event(p.arrival, self.PROCESS_ARRIVAL, p))

    def run(self):
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time

            # 记录事件
            self.timeline.append({
                'time': self.current_time,
                'event': event.type,
                'process': event.process.name if event.process else None,
                'ready_queue': [p.name for p in self.ready_queue]
            })

            if event.type == self.PROCESS_ARRIVAL:
                # 进程到达，加入就绪队列
                self.ready_queue.append(event.process)
                event.process.last_run = self.current_time

                # 开始等待状态
                if not event.process.waiting_intervals or event.process.waiting_intervals[-1][1] is not None:
                    event.process.waiting_intervals.append([self.current_time, None])

            elif event.type == self.PROCESS_START:
                # 进程开始运行
                self.current_process = event.process
                if self.current_process.start_time == -1:
                    self.current_process.start_time = self.current_time

                # 结束等待状态
                if self.current_process.waiting_intervals and self.current_process.waiting_intervals[-1][1] is None:
                    self.current_process.waiting_intervals[-1][1] = self.current_time

                # 记录开始运行时间
                if not self.current_process.running_intervals or self.current_process.running_intervals[-1][
                    1] is not None:
                    self.current_process.running_intervals.append([self.current_time, None])

                # 对于RR算法，添加时间片到期事件
                if self.algorithm == "RR":
                    run_time = min(self.current_process.remaining, self.quantum)
                    heapq.heappush(self.event_queue,
                                   Event(self.current_time + run_time,
                                         self.TIME_SLICE_EXPIRED,
                                         self.current_process))
                else:
                    # 非RR算法，直接添加完成事件
                    heapq.heappush(self.event_queue,
                                   Event(self.current_time + self.current_process.remaining,
                                         self.PROCESS_COMPLETE,
                                         self.current_process))

            elif event.type == self.PROCESS_COMPLETE:
                # 进程完成
                p = event.process
                p.finish_time = self.current_time
                p.remaining = 0

                # 记录运行结束时间
                if p.running_intervals and p.running_intervals[-1][1] is None:
                    p.running_intervals[-1][1] = self.current_time

                # 从就绪队列中移除（如果存在）
                if p in self.ready_queue:
                    self.ready_queue.remove(p)

                if self.current_process == p:
                    self.current_process = None

            elif event.type == self.TIME_SLICE_EXPIRED:
                # RR算法时间片到期
                p = event.process

                # 更新剩余时间
                time_run = self.current_time - p.last_run
                p.remaining -= time_run
                p.last_run = self.current_time

                # 记录运行结束时间
                if p.running_intervals and p.running_intervals[-1][1] is None:
                    p.running_intervals[-1][1] = self.current_time

                if p.remaining <= 0:
                    # 进程完成
                    p.finish_time = self.current_time

                    # 从就绪队列中移除（如果存在）
                    if p in self.ready_queue:
                        self.ready_queue.remove(p)

                    if self.current_process == p:
                        self.current_process = None
                else:
                    # 时间片用完但未完成，重新加入就绪队列
                    self.ready_queue.append(p)

                    # 开始等待状态
                    if not p.waiting_intervals or p.waiting_intervals[-1][1] is not None:
                        p.waiting_intervals.append([self.current_time, None])

                    if self.current_process == p:
                        self.current_process = None

            # 根据算法选择下一个运行的进程
            if self.current_process is None and self.ready_queue:
                next_process = None

                if self.algorithm == "FCFS":
                    # 先来先服务 - 选择最先到达的进程
                    next_process = self.ready_queue[0]

                elif self.algorithm == "SJF":
                    # 最短作业优先 - 选择执行时间最短的进程
                    next_process = min(self.ready_queue, key=lambda p: p.burst)

                elif self.algorithm == "HRRF":
                    # 最高响应比优先 - 选择响应比最高的进程
                    for p in self.ready_queue:
                        waiting_time = self.current_time - p.arrival - (p.burst - p.remaining)
                        p.response_ratio = 1 + waiting_time / p.burst
                    next_process = max(self.ready_queue, key=lambda p: p.response_ratio)

                elif self.algorithm == "RR":
                    # 轮转法 - 选择就绪队列中的第一个进程
                    next_process = self.ready_queue[0]

                elif self.algorithm == "SRTF":
                    # 最短剩余时间优先 - 选择剩余时间最短的进程
                    next_process = min(self.ready_queue, key=lambda p: p.remaining)

                if next_process:
                    # 从就绪队列中移除选中的进程
                    if next_process in self.ready_queue:
                        self.ready_queue.remove(next_process)

                    # 创建开始事件
                    heapq.heappush(self.event_queue,
                                   Event(self.current_time,
                                         self.PROCESS_START,
                                         next_process))

                    # 更新最后运行时间
                    next_process.last_run = self.current_time

        # 收集甘特图数据
        self.gantt_data = []
        for p in self.processes:
            # 运行区间
            for start, end in p.running_intervals:
                if end is None:  # 处理未结束的情况
                    end = self.current_time
                self.gantt_data.append({
                    'process': p.name,
                    'start': start,
                    'end': end,
                    'duration': end - start,
                    'type': 'running'  # 标记为运行状态
                })

            # 等待区间
            for start, end in p.waiting_intervals:
                if end is None:  # 处理未结束的情况
                    end = self.current_time
                self.gantt_data.append({
                    'process': p.name,
                    'start': start,
                    'end': end,
                    'duration': end - start,
                    'type': 'waiting'  # 标记为等待状态
                })

        # 计算结果
        results = []
        total_turnaround = 0
        total_waiting = 0
        valid_count = 0

        for p in self.processes:
            if p.finish_time != -1:
                turnaround = p.finish_time - p.arrival
                waiting = turnaround - p.burst
                total_turnaround += turnaround
                total_waiting += waiting
                valid_count += 1
            #逐个添加结果
                results.append({
                    'name': p.name,
                    'arrival': p.arrival,
                    'burst': p.burst,
                    'start': p.start_time,
                    'finish': p.finish_time,
                    'turnaround': turnaround,
                    'waiting': waiting
                })

        avg_turnaround = total_turnaround / valid_count if valid_count > 0 else 0
        avg_waiting = total_waiting / valid_count if valid_count > 0 else 0
        #返回所有结果
        return {
            'results': results,
            'avg_turnaround': avg_turnaround,
            'avg_waiting': avg_waiting,
            'gantt_data': self.gantt_data,
            'timeline': self.timeline
        }


class SchedulingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("进程调度算法仿真系统")#标题
        self.root.geometry("1200x800")#界面大小
        self.root.configure(bg='#f0f0f0')#背景颜色

        # 设置样式
        self.setup_styles()

        self.processes = []
        self.current_algorithm = "FCFS"#界面开始默认算法
        self.quantum = 2

        # 确保中文字体设置
        self.setup_chinese_font()

        self.create_widgets()

    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'), background='#f0f0f0')
        style.configure('Custom.TLabelframe', background='#f0f0f0')
        style.configure('Custom.TLabelframe.Label', font=('Arial', 10, 'bold'), background='#f0f0f0')

        # 修复样式名称：使用默认的Treeview样式
        style.configure('Treeview', rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 9, 'bold'))

        style.configure('Accent.TButton', font=('Arial', 9))

        # 配置颜色
        self.colors = {
            'primary': '#4a6fa5',
            'secondary': '#6b8cbc',
            'accent': '#ff6b6b',
            'background': '#f0f0f0',
            'surface': '#ffffff',
            'text': '#333333'
        }

    def setup_chinese_font(self):
        """设置中文字体支持"""
        # 尝试多种中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'STSong', 'KaiTi', 'FangSong']

        # 检查系统可用的中文字体
        available_fonts = []
        for font in chinese_fonts:
            try:
                # 尝试创建字体属性来检查字体是否可用
                test_font = matplotlib.font_manager.FontProperties(family=font)
                # 如果能成功获取字体路径，说明字体可用
                path = matplotlib.font_manager.findfont(test_font)
                available_fonts.append(font)
            except:
                continue

        if available_fonts:
            # 使用第一个可用的中文字体
            plt.rcParams['font.sans-serif'] = available_fonts + ['DejaVu Sans', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False
            print(f"已设置中文字体: {available_fonts[0]}")
            return True
        else:
            print("警告：未找到可用的中文字体，中文显示可能不正常")
            # 尝试使用默认字体
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False
            return False

    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建顶部标题
        title_label = ttk.Label(main_frame, text="进程调度算法仿真系统",
                                style='Title.TLabel')
        title_label.pack(pady=(0, 10))

        # 创建左右分栏
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧面板 - 进程输入和算法设置
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)

        # 右侧面板 - 结果显示和可视化
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        # 配置左右面板比例
        paned_window.sashpos(0, 500)

        # 创建左侧内容
        self.create_left_panel(left_frame)

        # 创建右侧内容
        self.create_right_panel(right_frame)

    def create_left_panel(self, parent):
        # 进程信息框架
        process_frame = ttk.LabelFrame(parent, text="进程信息", style='Custom.TLabelframe')
        process_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 进程表格
        columns = ("name", "arrival", "burst", "priority")
        # 使用默认的Treeview样式
        self.tree = ttk.Treeview(process_frame, columns=columns, show="headings", height=8)
        self.tree.heading("name", text="进程名")
        self.tree.heading("arrival", text="到达时间")
        self.tree.heading("burst", text="执行时间")
        self.tree.heading("priority", text="优先级")

        # 设置列宽
        self.tree.column("name", width=80)
        self.tree.column("arrival", width=80)
        self.tree.column("burst", width=80)
        self.tree.column("priority", width=80)

        # 添加滚动条
        tree_scrollbar = ttk.Scrollbar(process_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        # 打包表格和滚动条
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 按钮框架
        btn_frame = ttk.Frame(process_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="添加进程", command=self.add_process,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="编辑进程", command=self.edit_process,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="删除进程", command=self.delete_process,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_processes,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 算法选择框架
        algo_frame = ttk.LabelFrame(parent, text="调度算法设置", style='Custom.TLabelframe')
        algo_frame.pack(fill=tk.X, pady=10)

        self.algo_var = tk.StringVar(value="FCFS")
        algorithms = [
            ("先来先服务 (FCFS)", "FCFS"),
            ("最短作业优先 (SJF)", "SJF"),
            ("最高响应比优先 (HRRF)", "HRRF"),
            ("轮转法 (RR)", "RR"),
            ("最短剩余时间优先 (SRTF)", "SRTF")
        ]

        # 创建算法选择按钮
        for i, (text, algo) in enumerate(algorithms):
            rb = ttk.Radiobutton(algo_frame, text=text, variable=self.algo_var,
                                 value=algo, command=self.select_algorithm)
            rb.grid(row=i // 2, column=i % 2, sticky=tk.W, padx=10, pady=5)

        # 时间片设置（仅RR算法）
        self.quantum_frame = ttk.Frame(algo_frame)
        ttk.Label(self.quantum_frame, text="时间片大小:").pack(side=tk.LEFT)
        self.quantum_entry = ttk.Entry(self.quantum_frame, width=5)
        self.quantum_entry.pack(side=tk.LEFT, padx=5)
        self.quantum_entry.insert(0, "2")

        # 运行按钮框架
        run_frame = ttk.Frame(parent)
        run_frame.pack(fill=tk.X, pady=10)

        ttk.Button(run_frame, text="运行仿真", command=self.run_simulation,
                   style='Accent.TButton').pack(fill=tk.X, pady=5)

    def create_right_panel(self, parent):
        # 创建笔记本控件用于分页显示
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 第一页：结果表格
        result_frame = ttk.Frame(notebook)
        notebook.add(result_frame, text="调度结果")

        # 结果表格
        result_columns = ("name", "arrival", "burst", "start", "finish", "turnaround", "waiting")
        # 使用默认的Treeview样式
        self.result_tree = ttk.Treeview(result_frame, columns=result_columns, show="headings", height=10)

        # 设置列标题
        self.result_tree.heading("name", text="进程名")
        self.result_tree.heading("arrival", text="到达时间")
        self.result_tree.heading("burst", text="执行时间")
        self.result_tree.heading("start", text="开始时间")
        self.result_tree.heading("finish", text="完成时间")
        self.result_tree.heading("turnaround", text="周转时间")
        self.result_tree.heading("waiting", text="等待时间")

        # 设置列宽
        self.result_tree.column("name", width=70)
        self.result_tree.column("arrival", width=70)
        self.result_tree.column("burst", width=70)
        self.result_tree.column("start", width=70)
        self.result_tree.column("finish", width=70)
        self.result_tree.column("turnaround", width=80)
        self.result_tree.column("waiting", width=70)

        # 添加滚动条
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)

        # 打包结果表格
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 平均结果标签
        avg_frame = ttk.Frame(result_frame)
        avg_frame.pack(fill=tk.X, pady=5)

        self.avg_label = ttk.Label(avg_frame, text="平均周转时间: -\n平均等待时间: -",
                                   style='Title.TLabel')
        self.avg_label.pack(anchor=tk.CENTER)

        # 第二页：甘特图
        gantt_frame = ttk.Frame(notebook)
        notebook.add(gantt_frame, text="甘特图")

        # 甘特图显示区域
        self.gantt_canvas_frame = ttk.Frame(gantt_frame)
        self.gantt_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 第三页：时间线动画
        timeline_frame = ttk.Frame(notebook)
        notebook.add(timeline_frame, text="时间线")

        # 时间线显示区域
        self.timeline_canvas_frame = ttk.Frame(timeline_frame)
        self.timeline_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 可视化按钮框架
        viz_btn_frame = ttk.Frame(parent)
        viz_btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(viz_btn_frame, text="刷新甘特图", command=self.show_gantt,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(viz_btn_frame, text="显示时间线动画", command=self.show_timeline_animation,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def select_algorithm(self):
        self.current_algorithm = self.algo_var.get()
        if self.current_algorithm == "RR":
            self.quantum_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        else:
            self.quantum_frame.grid_forget()

    def add_process(self):
        dialog = ProcessDialog(self.root, "添加进程")
        if dialog.result:
            name, arrival, burst, priority = dialog.result
            self.processes.append(Process(name, arrival, burst, priority))
            self.update_process_list()

    def edit_process(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择一个进程进行编辑")
            return

        item = selected[0]
        values = self.tree.item(item, 'values')
        index = self.tree.index(item)

        dialog = ProcessDialog(self.root, "编辑进程", values)
        if dialog.result:
            name, arrival, burst, priority = dialog.result
            self.processes[index] = Process(name, arrival, burst, priority)
            self.update_process_list()

    def delete_process(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要删除的进程")
            return

        item = selected[0]
        index = self.tree.index(item)
        del self.processes[index]
        self.update_process_list()

    def clear_processes(self):
        if messagebox.askyesno("确认", "确定要清空所有进程吗？"):
            self.processes = []
            self.update_process_list()

    def update_process_list(self):
        # 清空树视图
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加新数据
        for p in self.processes:
            self.tree.insert("", "end", values=(p.name, p.arrival, p.burst, p.priority))

    def run_simulation(self):
        if not self.processes:
            messagebox.showwarning("警告", "请添加至少一个进程")
            return

        # 获取时间片大小
        if self.current_algorithm == "RR":
            try:
                self.quantum = int(self.quantum_entry.get())
                if self.quantum <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("错误", "时间片大小必须是正整数")
                return

        # 运行仿真
        simulator = SchedulerSimulator(self.processes, self.current_algorithm, self.quantum)
        results = simulator.run()

        # 显示结果
        self.show_results(results)

        # 保存结果用于可视化
        self.simulation_results = results

        # 自动更新甘特图
        self.show_gantt(embed=True)

    def show_results(self, results):
        # 清空结果树视图
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        # 添加新结果
        for res in results['results']:
            self.result_tree.insert("", "end", values=(
                res['name'],
                res['arrival'],
                res['burst'],
                res['start'],
                res['finish'],
                f"{res['turnaround']:.2f}",  # 保留两位小数
                f"{res['waiting']:.2f}"  # 保留两位小数
            ))

        # 添加平均结果行
        self.result_tree.insert("", "end", values=(
            "平均",
            "",
            "",
            "",
            "",
            f"{results['avg_turnaround']:.2f}",
            f"{results['avg_waiting']:.2f}"
        ), tags=('average',))

        # 配置标签样式
        self.result_tree.tag_configure('average', background='#e0e0e0', font=('Arial', 9, 'bold'))

        # 显示平均结果标签
        self.avg_label.config(
            text=f"平均周转时间: {results['avg_turnaround']:.2f}\n平均等待时间: {results['avg_waiting']:.2f}")

    def show_gantt(self, embed=False):
        if not hasattr(self, 'simulation_results'):
            messagebox.showwarning("警告", "请先运行仿真")
            return

        gantt_data = self.simulation_results['gantt_data']

        if not gantt_data:
            messagebox.showinfo("信息", "没有可显示的甘特图数据")
            return

        # 清除之前的甘特图
        for widget in self.gantt_canvas_frame.winfo_children():
            widget.destroy()

        # 创建甘特图
        fig, ax = plt.subplots(figsize=(10, 6))

        # 获取所有进程名
        process_names = sorted(set([d['process'] for d in gantt_data]))
        y_ticks = np.arange(len(process_names))
        y_tick_labels = process_names

        # 设置y轴
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_tick_labels)
        ax.set_ylabel('进程')
        ax.set_xlabel('时间')
        ax.set_title(f'进程调度甘特图 - {self.current_algorithm}算法')

        # 为每个进程分配固定颜色
        colors = plt.cm.Set3(np.linspace(0, 1, len(process_names)))
        color_map = {name: colors[i] for i, name in enumerate(process_names)}

        # 绘制每个进程的运行区间
        for d in gantt_data:
            y_pos = process_names.index(d['process'])

            if d['type'] == 'running':
                # 运行状态 - 使用彩色
                face_color = color_map[d['process']]
                edge_color = 'black'
                alpha = 0.7
            else:
                # 等待状态 - 使用灰色
                face_color = 'lightgray'
                edge_color = 'gray'
                alpha = 0.5

            rect = patches.Rectangle(
                (d['start'], y_pos - 0.4),
                d['duration'],
                0.8,
                edgecolor=edge_color,
                linewidth=1,
                facecolor=face_color,
                alpha=alpha
            )
            ax.add_patch(rect)

            # 添加时间标签（只在运行状态且时间足够长时显示）
            if d['type'] == 'running' and d['duration'] >= 1:
                ax.text(d['start'] + d['duration'] / 2, y_pos,
                        f"{d['start']}-{d['end']}",
                        ha='center', va='center', color='black', fontsize=8,
                        bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))

        # 设置x轴范围
        max_time = max([d['end'] for d in gantt_data]) if gantt_data else 10
        ax.set_xlim(0, max_time + 1)

        # 添加图例
        running_patch = patches.Patch(color=colors[0], alpha=0.7, label='运行状态')
        waiting_patch = patches.Patch(color='lightgray', alpha=0.5, label='等待状态')
        ax.legend(handles=[running_patch, waiting_patch], loc='upper right')

        # 添加网格
        ax.grid(True, axis='x', alpha=0.3)
        ax.set_axisbelow(True)

        plt.tight_layout()

        if embed:
            # 嵌入到界面中
            canvas = FigureCanvasTkAgg(fig, self.gantt_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # 添加工具栏
            toolbar = NavigationToolbar2Tk(canvas, self.gantt_canvas_frame)
            toolbar.update()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            plt.show()

    def show_timeline_animation(self):
        if not hasattr(self, 'simulation_results'):
            messagebox.showwarning("警告", "请先运行仿真")
            return

        timeline = self.simulation_results['timeline']

        if not timeline:
            messagebox.showinfo("信息", "没有可显示的时间线数据")
            return

        # 清除之前的时间线
        for widget in self.timeline_canvas_frame.winfo_children():
            widget.destroy()

        # 创建动画
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_xlim(0, timeline[-1]['time'] + 5)
        ax.set_ylim(-0.5, 2.5)
        ax.set_xlabel('时间')
        ax.set_title('进程调度时间线动画')

        # 创建状态文本
        time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes, fontsize=12)
        event_text = ax.text(0.02, 0.90, '', transform=ax.transAxes, fontsize=12)
        process_text = ax.text(0.02, 0.85, '', transform=ax.transAxes, fontsize=12)
        queue_text = ax.text(0.02, 0.80, '', transform=ax.transAxes, fontsize=12)

        # 创建运行进程的矩形
        current_rect = None

        # 创建就绪队列文本
        queue_positions = np.linspace(1.5, 0.5, 5)  # 最多显示5个就绪进程

        def init():
            time_text.set_text('')
            event_text.set_text('')
            process_text.set_text('')
            queue_text.set_text('')
            return time_text, event_text, process_text, queue_text

        def animate(i):
            ax.clear()
            ax.set_xlim(0, timeline[-1]['time'] + 5)
            ax.set_ylim(-0.5, 2.5)
            ax.set_xlabel('时间')
            ax.set_title('进程调度时间线动画')

            # 绘制当前时间点
            ax.axvline(x=timeline[i]['time'], color='r', linestyle='--', alpha=0.5)

            # 更新文本
            time_text = ax.text(0.02, 0.95, f'时间: {timeline[i]["time"]}', transform=ax.transAxes, fontsize=12)

            event_type = timeline[i]['event']
            event_name = {
                0: "进程到达",
                1: "进程开始",
                2: "进程完成",
                3: "时间片到期"
            }.get(event_type, "未知事件")
            event_text = ax.text(0.02, 0.90, f'事件: {event_name}', transform=ax.transAxes, fontsize=12)

            process_name = timeline[i]['process'] or "无"
            process_text = ax.text(0.02, 0.85, f'当前进程: {process_name}', transform=ax.transAxes, fontsize=12)

            queue_list = ", ".join(timeline[i]['ready_queue']) or "空"
            queue_text = ax.text(0.02, 0.80, f'就绪队列: {queue_list}', transform=ax.transAxes, fontsize=12)

            # 绘制就绪队列
            for j, proc in enumerate(timeline[i]['ready_queue'][:5]):
                ax.text(timeline[i]['time'] + 1, queue_positions[j], proc,
                        bbox=dict(boxstyle="round", fc="lightblue", ec="blue", alpha=0.7),
                        fontsize=10, ha='center')

            # 绘制当前运行的进程
            if timeline[i]['process']:
                ax.text(timeline[i]['time'], 2, timeline[i]['process'],
                        bbox=dict(boxstyle="round", fc="lightgreen", ec="green", alpha=0.7),
                        fontsize=12, ha='center')

            return time_text, event_text, process_text, queue_text

        anim = animation.FuncAnimation(fig, animate, frames=len(timeline),
                                       init_func=init, blit=False, interval=500, repeat=False)

        # 嵌入到界面中
        canvas = FigureCanvasTkAgg(fig, self.timeline_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 添加工具栏
        toolbar = NavigationToolbar2Tk(canvas, self.timeline_canvas_frame)
        toolbar.update()

        plt.tight_layout()


class ProcessDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_values=None):
        self.result = None
        self.initial_values = initial_values
        super().__init__(parent, title)

    def body(self, frame):
        ttk.Label(frame, text="进程名:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_entry = ttk.Entry(frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="到达时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.arrival_entry = ttk.Entry(frame)
        self.arrival_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="执行时间:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.burst_entry = ttk.Entry(frame)
        self.burst_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(frame, text="优先级:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.priority_entry = ttk.Entry(frame)
        self.priority_entry.grid(row=3, column=1, padx=5, pady=5)

        if self.initial_values:
            self.name_entry.insert(0, self.initial_values[0])
            self.arrival_entry.insert(0, self.initial_values[1])
            self.burst_entry.insert(0, self.initial_values[2])
            self.priority_entry.insert(0, self.initial_values[3])

        return self.name_entry

    def validate(self):
        try:
            name = self.name_entry.get().strip()
            arrival = int(self.arrival_entry.get())
            burst = int(self.burst_entry.get())
            priority = int(self.priority_entry.get())

            if not name:
                messagebox.showerror("错误", "进程名不能为空")
                return False

            if arrival < 0:
                messagebox.showerror("错误", "到达时间不能为负数")
                return False

            if burst <= 0:
                messagebox.showerror("错误", "执行时间必须大于0")
                return False

            self.result = (name, arrival, burst, priority)
            return True
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数")
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulingApp(root)
    root.mainloop()