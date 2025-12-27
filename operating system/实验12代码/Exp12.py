import threading
import time
import random
import sys
from enum import Enum
from collections import OrderedDict, deque
from typing import List, Dict, Tuple, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext

# ==================== 全局常量与参数 ====================
MEMORY_SIZE = 2 ** 14  # 16384 字节（16KB物理内存）
PAGE_SIZE = 256  # 256 字节（页面大小）
PAGE_TABLE_ENTRY_SIZE = 4  # 4 字节（页表项大小）
NUM_JOBS = 12  # 作业数（并发进程数量）
PAGES_PER_JOB = 64  # 每个作业的虚拟页面数（每个进程的虚拟地址空间大小）
PHYSICAL_PAGES_PER_PROCESS = 10  # 每个进程分配的物理页框数 (1页表 + 9数据)
PAGE_TABLE_PAGES = 1  # 页表占用的页框数
DATA_PAGES_PER_PROCESS = PHYSICAL_PAGES_PER_PROCESS - PAGE_TABLE_PAGES  # 9（每个进程的数据页框数）
ACCESS_TIMES_PER_PROCESS = 200  # 每个进程访问内存次数（模拟进程执行长度）
MAX_WAIT_TIME_MS = 100  # 最大休眠时间（毫秒）（控制模拟速度）

TOTAL_PHYSICAL_PAGES = MEMORY_SIZE // PAGE_SIZE  # 64
BITMAP_SIZE = TOTAL_PHYSICAL_PAGES  # 位图大小（位数），等于物理页框总数


# ==================== 枚举与全局变量 ====================
class ReplaceAlgo(Enum):
    """页面替换算法枚举"""
    FIFO = "FIFO"  # 先进先出算法
    LRU = "LRU"  # 最近最少使用算法


class ProcessState(Enum):
    """进程状态枚举"""
    WAITING = "等待内存"  # 等待分配内存
    RUNNING = "运行中"  # 正在执行
    FINISHED = "已完成"  # 执行完成


# 全局锁，保护共享资源（多线程同步）
bitmap_lock = threading.Lock()  # 保护内存位图访问
process_lock = threading.Lock()  # 保护进程状态访问
ui_update_lock = threading.Lock()  # 保护UI更新队列访问

# 全局位图，0表示空闲，1表示已分配（用于物理内存管理）
free_page_bitmap = [0] * BITMAP_SIZE
# 记录每个页框的分配信息 (进程ID, 虚拟页号, 类型)，用于UI显示
page_allocation_info = [None] * BITMAP_SIZE  # 每个元素为 (job_id, vpn, page_type)

# 文件系统模拟（模拟磁盘存储，存储未加载到内存的页面内容）
file_system = {}
# 替换算法全局变量，默认为FIFO
REPLACEMENT_ALGO = ReplaceAlgo.FIFO

# 全局UI更新队列（用于线程间通信）
ui_update_queue = []  # 存储UI更新请求的队列
ui_running = True  # UI更新线程运行标志
simulation_thread = None  # 模拟线程引用
simulation_finished = False  # 模拟完成标志
simulation_paused = False  # 模拟暂停标志
simulation_pause_cond = threading.Condition()  # 暂停条件变量

# 全局统计变量
global_statistics = {
    'total_page_faults': 0,  # 总缺页次数
    'total_memory_accesses': 0,  # 总内存访问次数
    'page_fault_rates': [],  # 每个进程的缺页率
    'algorithm_performance': {},  # 算法性能统计
    'memory_efficiency_history': [],  # 内存使用效率历史记录
    'peak_memory_usage': 0,  # 峰值内存使用量
    'average_memory_usage': 0,  # 平均内存使用量
    'simulation_start_time': 0,  # 模拟开始时间
    'simulation_end_time': 0,  # 模拟结束时间
}


# ==================== UI类 ====================
class MemorySimulatorUI:
    """内存模拟器用户界面类"""

    def __init__(self, root):
        """初始化UI界面"""
        self.root = root
        self.root.title("内存分页与进程调度模拟器")
        self.root.geometry("1200x800")

        # 初始化颜色映射（用于内存可视化）
        self.COLOR_MAP = {
            "free": "#E0E0E0",  # 浅灰 - 空闲页框
            "page_table": "#FFCC99",  # 浅橙 - 页表页框
            "data": "#CCFFCC",  # 浅绿 - 数据页框
            "current": "#FF6666",  # 红色 - 当前访问页框
        }

        # 进程颜色列表（每个进程使用不同颜色）
        self.process_colors = [
            "#99CCFF", "#CC99FF", "#99FF99", "#FFCC99",
            "#FF99CC", "#99FFFF", "#FFFF99", "#CCCCFF",
            "#FFCCCC", "#CCFFCC", "#FFE5CC", "#E5CCFF"
        ]

        # 设置UI组件并启动定时器
        self.setup_ui()
        self.update_timer()

    def setup_ui(self):
        """设置UI界面布局和组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重（使界面可缩放）
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # 算法选择组件
        ttk.Label(control_frame, text="替换算法:").grid(row=0, column=0, padx=(0, 5))
        self.algo_var = tk.StringVar(value="FIFO")
        algo_combo = ttk.Combobox(control_frame, textvariable=self.algo_var,
                                  values=["FIFO", "LRU"], state="readonly", width=10)
        algo_combo.grid(row=0, column=1, padx=(0, 20))

        # 控制按钮
        self.start_btn = ttk.Button(control_frame, text="开始模拟", command=self.start_simulation)
        self.start_btn.grid(row=0, column=2, padx=5)

        self.pause_btn = ttk.Button(control_frame, text="暂停", command=self.pause_simulation, state=tk.DISABLED)
        self.pause_btn.grid(row=0, column=3, padx=5)

        self.resume_btn = ttk.Button(control_frame, text="继续", command=self.resume_simulation, state=tk.DISABLED)
        self.resume_btn.grid(row=0, column=4, padx=5)

        self.reset_btn = ttk.Button(control_frame, text="重置", command=self.reset_simulation, state=tk.DISABLED)
        self.reset_btn.grid(row=0, column=5, padx=5)

        # 速度控制滑块
        ttk.Label(control_frame, text="速度:").grid(row=0, column=6, padx=(20, 5))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(control_frame, from_=0.1, to=5.0, variable=self.speed_var,
                                orient=tk.HORIZONTAL, length=100)
        speed_scale.grid(row=0, column=7, padx=5)

        # 状态标签
        self.status_label = ttk.Label(control_frame, text="状态: 就绪")
        self.status_label.grid(row=0, column=8, padx=(20, 5))

        # 左侧：内存可视化区域
        memory_frame = ttk.LabelFrame(main_frame, text="内存分配状态", padding="10")
        memory_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # 内存位图可视化 - 16列4行布局显示64个物理页框
        self.memory_canvas = tk.Canvas(memory_frame, width=600, height=300, bg="white")
        self.memory_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 内存图例说明
        legend_frame = ttk.Frame(memory_frame)
        legend_frame.grid(row=1, column=0, pady=(10, 0), sticky=tk.W)

        for i, (label, color) in enumerate([
            ("空闲", self.COLOR_MAP["free"]),
            ("页表", self.COLOR_MAP["page_table"]),
            ("数据", self.COLOR_MAP["data"]),
            ("当前访问", self.COLOR_MAP["current"])
        ]):
            frame = ttk.Frame(legend_frame)
            frame.grid(row=0, column=i, padx=5)
            canvas = tk.Canvas(frame, width=20, height=20, bg=color, highlightthickness=1)
            canvas.grid(row=0, column=0, padx=(0, 5))
            ttk.Label(frame, text=label).grid(row=0, column=1)

        # 内存状态统计信息显示区域
        self.memory_stats = tk.Text(memory_frame, width=50, height=12, font=("Courier", 10))
        self.memory_stats.grid(row=2, column=0, pady=(10, 0), sticky=(tk.W, tk.E))

        # 右侧：进程信息区域
        process_frame = ttk.LabelFrame(main_frame, text="进程信息", padding="10")
        process_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 进程信息表格（显示所有进程状态）
        columns = ("进程ID", "状态", "缺页次数", "缺页率", "物理页框")
        self.process_tree = ttk.Treeview(process_frame, columns=columns, show="headings", height=15)

        # 设置表格列属性
        for col in columns:
            self.process_tree.heading(col, text=col)
            if col == "物理页框":
                self.process_tree.column(col, width=150)  # 物理页框列较宽
            else:
                self.process_tree.column(col, width=80)

        self.process_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 添加滚动条
        scrollbar = ttk.Scrollbar(process_frame, orient=tk.VERTICAL, command=self.process_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.process_tree.configure(yscrollcommand=scrollbar.set)

        # 底部：日志输出区域
        log_frame = ttk.LabelFrame(main_frame, text="模拟日志", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=10, font=("Courier", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重（使组件可随窗口缩放）
        memory_frame.rowconfigure(0, weight=1)
        memory_frame.columnconfigure(0, weight=1)
        process_frame.rowconfigure(0, weight=1)
        process_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

    def update_timer(self):
        """定时更新UI（每100毫秒执行一次）"""
        if ui_running:
            self.process_ui_updates()
        # 递归调用，实现定时器功能
        self.root.after(100, self.update_timer)

    def process_ui_updates(self):
        """处理UI更新队列中的更新请求"""
        # 获取待处理的更新请求（线程安全）
        with ui_update_lock:
            updates_to_process = ui_update_queue.copy()
            ui_update_queue.clear()  # 清空队列

        # 处理每种类型的更新请求
        for update_type, data in updates_to_process:
            if update_type == "memory_bitmap":
                self.update_memory_bitmap(data)  # 更新内存位图显示
            elif update_type == "process_info":
                self.update_process_table(data)  # 更新进程信息表格
            elif update_type == "log":
                self.add_log_message(data)  # 添加日志消息
            elif update_type == "stats":
                self.update_memory_stats(data)  # 更新内存统计信息
            elif update_type == "simulation_finished":
                self.on_simulation_finished(data)  # 模拟结束处理
            elif update_type == "status":
                self.update_status(data)  # 更新状态显示
            elif update_type == "performance_stats":
                self.update_performance_stats(data)  # 更新性能统计信息

    def update_memory_bitmap(self, allocation_info):
        """更新内存位图可视化（16列4行布局显示64个物理页框）"""
        # 清空画布
        self.memory_canvas.delete("all")

        # 计算每个页框的显示大小，16列4行布局
        cols = 16  # 16列
        rows = 4  # 4行

        # 画布尺寸
        canvas_width = 600
        canvas_height = 300

        # 调整边距，减少上方边距使位图向上平移
        margin_x = 10
        margin_y = 5  # 减少上方边距，从10改为5

        # 计算每个格子的实际大小
        cell_width = (canvas_width - 2 * margin_x) // cols
        cell_height = (canvas_height - 2 * margin_y) // rows

        # 限制格子大小在合理范围内
        cell_width = max(min(cell_width, 30), 20)  # 宽度限制在20-30之间
        cell_height = max(min(cell_height, 40), 25)  # 高度限制在25-40之间

        # 重新计算总宽度和高度
        total_width = cell_width * cols
        total_height = cell_height * rows

        # 向上平移：减小start_y的值，使位图更靠上
        # 原居中计算：start_y = (canvas_height - total_height) // 2
        # 现在改为从更靠近顶部的位置开始
        start_x = (canvas_width - total_width) // 2
        start_y = margin_y + 10  # 从顶部边距+10开始，而不是居中

        # 绘制每个物理页框
        for i in range(BITMAP_SIZE):
            # 计算当前页框在网格中的位置
            row = i // cols
            col = i % cols

            # 计算矩形坐标
            x1 = start_x + col * cell_width
            y1 = start_y + row * cell_height
            x2 = x1 + cell_width - 2  # 留出边距
            y2 = y1 + cell_height - 2

            # 获取页框分配信息
            info = allocation_info[i]

            if info is None:
                # 空闲页框：显示为灰色
                color = self.COLOR_MAP["free"]
                label = f"{i}\n空闲"
            else:
                # 已分配页框：根据类型显示不同颜色
                job_id, vpn, page_type = info
                if page_type == "page_table":
                    # 页表页框：显示为橙色
                    color = self.COLOR_MAP["page_table"]
                    label = f"{i}\nP{job_id}表"  # 格式：页框号\n进程Px表
                else:
                    # 数据页框：使用进程特定颜色
                    color_idx = job_id % len(self.process_colors)
                    color = self.process_colors[color_idx]
                    label = f"{i}\nP{job_id}:{vpn}"  # 格式：页框号\n进程Px:虚拟页号y

            # 绘制矩形代表页框
            self.memory_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", width=1)

            # 根据格子大小调整字体大小
            font_size = 7
            if cell_width > 25 and cell_height > 30:
                font_size = 8

            # 计算文本位置（居中）
            text_x = x1 + cell_width / 2
            text_y = y1 + cell_height / 2

            # 绘制主要文本
            self.memory_canvas.create_text(text_x, text_y - 5,
                                           text=label, font=("Arial", font_size),
                                           justify=tk.CENTER, width=cell_width - 4)

            # 在格子左下角添加小字体的页框编号（便于识别）
            self.memory_canvas.create_text(x1 + 2, y1 + 2, text=str(i),
                                           font=("Arial", 6), anchor=tk.NW, fill="#666666")

    def update_process_table(self, processes_info):
        """更新进程信息表格"""
        # 清空表格现有数据
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        # 添加新数据
        for proc_info in processes_info:
            job_id, state, page_faults, fault_rate, pages = proc_info

            # 格式化物理页框显示（最多显示5个，超出用省略号表示）
            pages_str = ", ".join(map(str, pages[:5]))
            if len(pages) > 5:
                pages_str += f" ...等{len(pages)}个"

            # 插入新行
            self.process_tree.insert("", tk.END, values=(
                f"P{job_id}",  # 进程ID
                state.value if isinstance(state, ProcessState) else state,  # 状态
                page_faults,  # 缺页次数
                f"{fault_rate:.2%}" if fault_rate >= 0 else "N/A",  # 缺页率（百分比格式）
                pages_str  # 分配的物理页框
            ))

    def update_memory_stats(self, stats):
        """更新内存统计信息显示"""
        # 清空现有文本
        self.memory_stats.delete(1.0, tk.END)

        # 格式化统计信息
        stats_text = f"""内存使用统计:
========================
总物理页框: {BITMAP_SIZE}
已分配页框: {stats['allocated']}
空闲页框: {stats['free']}
使用率: {stats['usage']:.1%}

页框类型分布:
  空闲页框: {stats['free_pages']}
  页表页框: {stats['page_table_pages']}
  数据页框: {stats['data_pages']}

进程状态:
  运行中: {stats['running_procs']}
  等待中: {stats['waiting_procs']}
  已完成: {stats['finished_procs']}

总缺页次数: {stats['total_page_faults']}
平均缺页率: {stats['avg_fault_rate']:.2%}
"""
        # 插入新文本
        self.memory_stats.insert(1.0, stats_text)

    def add_log_message(self, message):
        """添加日志消息到日志区域"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 自动滚动到底部

    def clear_log(self):
        """清空日志区域"""
        self.log_text.delete(1.0, tk.END)

    def update_status(self, message):
        """更新状态标签"""
        self.status_label.config(text=f"状态: {message}")

    def update_performance_stats(self, stats):
        """更新性能统计信息到日志"""
        self.add_log_message("\n" + "=" * 60)
        self.add_log_message("模拟性能统计:")
        self.add_log_message("=" * 60)

        # 算法性能统计
        algo_name = "FIFO" if REPLACEMENT_ALGO == ReplaceAlgo.FIFO else "LRU"
        self.add_log_message(f"替换算法: {algo_name}")

        # 总体统计
        self.add_log_message(f"模拟总时间: {stats.get('simulation_time', 0):.2f}秒")
        self.add_log_message(f"总内存访问次数: {stats.get('total_accesses', 0)}")
        self.add_log_message(f"总缺页次数: {stats.get('total_faults', 0)}")
        self.add_log_message(f"总体平均缺页率: {stats.get('avg_fault_rate', 0):.2%}")
        self.add_log_message(f"峰值内存使用率: {stats.get('peak_memory_usage', 0):.2%}")
        self.add_log_message(f"平均内存使用率: {stats.get('average_memory_usage', 0):.2%}")

        # 进程级统计
        self.add_log_message(f"\n进程级统计:")
        for i, (pid, faults, rate) in enumerate(stats.get('process_stats', [])):
            self.add_log_message(f"  进程 {pid}: 缺页次数={faults}, 缺页率={rate:.2%}")

        self.add_log_message("=" * 60)

    def on_simulation_finished(self, performance_stats=None):
        """模拟结束时的回调函数"""
        global simulation_finished
        simulation_finished = True

        # 恢复按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)

        self.update_status("模拟完成")
        self.add_log_message("模拟已结束，可以重新开始或重置")

        # 如果有性能统计数据，显示它们
        if performance_stats:
            self.update_performance_stats(performance_stats)

    def start_simulation(self):
        """开始模拟（按钮点击事件处理）"""
        global REPLACEMENT_ALGO, ui_running, simulation_thread, simulation_finished, simulation_paused, global_statistics

        # 重置全局统计
        global_statistics = {
            'total_page_faults': 0,
            'total_memory_accesses': 0,
            'page_fault_rates': [],
            'algorithm_performance': {},
            'memory_efficiency_history': [],
            'peak_memory_usage': 0,
            'average_memory_usage': 0,
            'simulation_start_time': time.time(),
            'simulation_end_time': 0,
        }

        # 重置完成标志
        simulation_finished = False
        simulation_paused = False

        # 设置替换算法（从UI获取选择）
        algo = self.algo_var.get()
        REPLACEMENT_ALGO = ReplaceAlgo.FIFO if algo == "FIFO" else ReplaceAlgo.LRU

        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)

        # 清空日志
        self.clear_log()

        # 启动模拟线程（分离线程，避免阻塞UI）
        ui_running = True
        simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        simulation_thread.start()

        self.update_status("模拟运行中")
        self.add_log_message(f"模拟开始，使用{algo}替换算法")

    def pause_simulation(self):
        """暂停模拟（按钮点击事件处理）"""
        global simulation_paused

        with simulation_pause_cond:
            simulation_paused = True
            self.pause_btn.config(state=tk.DISABLED)
            self.resume_btn.config(state=tk.NORMAL)
            self.update_status("模拟已暂停")
            self.add_log_message("模拟已暂停")
            simulation_pause_cond.notify_all()  # 通知所有等待的线程

    def resume_simulation(self):
        """继续模拟（按钮点击事件处理）"""
        global simulation_paused

        with simulation_pause_cond:
            simulation_paused = False
            self.pause_btn.config(state=tk.NORMAL)
            self.resume_btn.config(state=tk.DISABLED)
            self.update_status("模拟运行中")
            self.add_log_message("模拟继续")
            simulation_pause_cond.notify_all()  # 唤醒模拟线程

    def reset_simulation(self):
        """重置模拟（按钮点击事件处理）"""
        global ui_running, free_page_bitmap, page_allocation_info, simulation_finished, simulation_paused, simulation_thread, global_statistics

        # 停止模拟
        ui_running = False
        simulation_paused = False

        # 等待模拟线程结束
        if simulation_thread and simulation_thread.is_alive():
            with simulation_pause_cond:
                simulation_paused = False
                simulation_pause_cond.notify_all()  # 确保模拟线程能退出
            simulation_thread.join(timeout=2.0)  # 等待最多2秒

        # 重置模拟状态
        simulation_finished = False
        simulation_thread = None

        # 重置全局统计
        global_statistics = {
            'total_page_faults': 0,
            'total_memory_accesses': 0,
            'page_fault_rates': [],
            'algorithm_performance': {},
            'memory_efficiency_history': [],
            'peak_memory_usage': 0,
            'average_memory_usage': 0,
            'simulation_start_time': 0,
            'simulation_end_time': 0,
        }

        # 重置内存状态（线程安全）
        with bitmap_lock:
            free_page_bitmap = [0] * BITMAP_SIZE  # 重置位图（全部空闲）
            page_allocation_info = [None] * BITMAP_SIZE  # 清空分配信息

        # 重置按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(text="暂停", state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)

        # 清空UI显示
        self.memory_canvas.delete("all")  # 清空内存画布
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)  # 清空进程表格
        self.clear_log()  # 清空日志
        self.memory_stats.delete(1.0, tk.END)  # 清空统计信息
        self.update_status("就绪")  # 重置状态显示

        # 显示初始内存状态（全空闲）
        self.update_memory_bitmap(page_allocation_info)

        self.add_log_message("模拟已重置，可以重新开始")


# ==================== 模拟器核心 ====================
def init_file_system():
    """初始化文件系统（模拟磁盘存储）"""
    global file_system
    file_system.clear()  # 清空现有文件系统

    # 为每个进程的每个虚拟页面创建文件内容
    for job_id in range(NUM_JOBS):
        for vpn in range(PAGES_PER_JOB):
            # 创建页面内容（包含作业ID和页面号信息）
            content = f"<作业{job_id},页面{vpn}>"
            # 填充到页面大小（256字节）
            padded_content = content.ljust(PAGE_SIZE, ' ')
            # 存储到文件系统（键为(进程ID, 虚拟页号)）
            file_system[(job_id, vpn)] = padded_content


def update_ui(update_type, data):
    """向UI更新队列添加更新请求（线程安全）"""
    with ui_update_lock:
        ui_update_queue.append((update_type, data))


def get_memory_stats():
    """获取内存统计信息（线程安全）"""
    with bitmap_lock:
        # 计算已分配和空闲页框数量
        allocated = sum(free_page_bitmap)
        free = BITMAP_SIZE - allocated

        # 统计不同类型页框的数量
        page_table_pages = 0  # 页表页框计数
        data_pages = 0  # 数据页框计数

        for info in page_allocation_info:
            if info:  # 页框已分配
                job_id, vpn, page_type = info
                if page_type == "page_table":
                    page_table_pages += 1
                else:
                    data_pages += 1

        # 记录当前内存使用效率
        current_memory_efficiency = allocated / BITMAP_SIZE if BITMAP_SIZE > 0 else 0
        global_statistics['memory_efficiency_history'].append(current_memory_efficiency)

        # 更新峰值内存使用
        if current_memory_efficiency > global_statistics['peak_memory_usage']:
            global_statistics['peak_memory_usage'] = current_memory_efficiency

        # 返回统计信息字典
        return {
            'allocated': allocated,  # 已分配页框总数
            'free': free,  # 空闲页框总数
            'usage': current_memory_efficiency,  # 当前内存使用率
            'free_pages': free,  # 空闲页框数（与free相同）
            'page_table_pages': page_table_pages,  # 页表页框数
            'data_pages': data_pages  # 数据页框数
        }


def calculate_final_statistics(processes):
    """计算最终统计信息"""
    global global_statistics

    # 计算总访问次数和总缺页次数
    total_accesses = 0
    total_faults = 0
    process_stats = []

    for proc in processes:
        total_accesses += proc.access_count
        total_faults += proc.page_fault_count
        fault_rate = proc.page_fault_count / max(proc.access_count, 1)
        process_stats.append((proc.job_id, proc.page_fault_count, fault_rate))

    # 计算平均缺页率
    avg_fault_rate = total_faults / max(total_accesses, 1)

    # 计算平均内存使用率（基于历史记录）
    average_memory_usage = 0
    if global_statistics['memory_efficiency_history']:
        average_memory_usage = sum(global_statistics['memory_efficiency_history']) / len(
            global_statistics['memory_efficiency_history'])

    # 更新全局统计
    global_statistics['total_page_faults'] = total_faults
    global_statistics['total_memory_accesses'] = total_accesses
    global_statistics['page_fault_rates'] = [rate for _, _, rate in process_stats]
    global_statistics['algorithm_performance'] = {
        'total_faults': total_faults,
        'avg_fault_rate': avg_fault_rate,
        'peak_memory_usage': global_statistics['peak_memory_usage'],
        'average_memory_usage': average_memory_usage
    }
    global_statistics['average_memory_usage'] = average_memory_usage
    global_statistics['simulation_end_time'] = time.time()

    # 返回详细的统计信息
    return {
        'total_accesses': total_accesses,
        'total_faults': total_faults,
        'avg_fault_rate': avg_fault_rate,
        'peak_memory_usage': global_statistics['peak_memory_usage'],
        'average_memory_usage': average_memory_usage,
        'simulation_time': global_statistics['simulation_end_time'] - global_statistics['simulation_start_time'],
        'process_stats': process_stats
    }


class Process:
    """进程类，模拟一个执行中的进程"""

    def __init__(self, job_id):
        """初始化进程"""
        self.job_id = job_id  # 进程ID
        self.state = ProcessState.WAITING  # 初始状态为等待内存
        self.page_fault_count = 0  # 缺页中断次数统计
        self.access_count = 0  # 内存访问次数统计
        self.access_history = deque()  # FIFO算法的访问历史队列
        self.lru_dict = OrderedDict()  # LRU算法的访问时间字典
        self.allocated_pages = []  # 分配的物理页框列表
        self.page_table_base = -1  # 页表基地址（物理页框号）
        # 页表：长度为虚拟页面数，值-1表示未加载，其他值表示物理页框号
        self.page_table = [-1] * PAGES_PER_JOB

        # 新增：性能统计
        self.hit_count = 0  # 命中次数
        self.fault_rate_history = []  # 缺页率历史记录

    def allocate_memory(self):
        """为进程分配内存（线程安全）"""
        with bitmap_lock:
            # 查找连续的空闲页框（需要连续的PHYSICAL_PAGES_PER_PROCESS个页框）
            free_pages = []  # 连续空闲页框列表
            for i, allocated in enumerate(free_page_bitmap):
                if not allocated:  # 页框空闲
                    free_pages.append(i)
                    # 找到足够数量的连续空闲页框
                    if len(free_pages) == PHYSICAL_PAGES_PER_PROCESS:
                        break
                else:
                    # 如果遇到已分配的页框，重新开始查找
                    free_pages = []

            # 检查是否找到足够的连续空闲页框
            if len(free_pages) < PHYSICAL_PAGES_PER_PROCESS:
                return False  # 分配失败

            # 分配页框并设置相关信息
            for i, page in enumerate(free_pages):
                free_page_bitmap[page] = 1  # 标记为已分配

                if i == 0:  # 第一个页框用作页表
                    page_allocation_info[page] = (self.job_id, 0, "page_table")
                    self.page_table_base = page  # 记录页表基地址
                else:  # 数据页框
                    vpn = i - 1  # 虚拟页号（从0开始）
                    page_allocation_info[page] = (self.job_id, vpn, "data")
                    self.allocated_pages.append(page)  # 添加到分配页框列表
                    if vpn < PAGES_PER_JOB:
                        self.page_table[vpn] = page  # 建立页表映射

            return True  # 分配成功

    def release_memory(self):
        """释放进程占用的内存（线程安全）"""
        with bitmap_lock:
            # 释放页表页框
            if self.page_table_base >= 0:
                free_page_bitmap[self.page_table_base] = 0  # 标记为空闲
                page_allocation_info[self.page_table_base] = None  # 清除分配信息

            # 释放数据页框
            for page in self.allocated_pages:
                if 0 <= page < BITMAP_SIZE:
                    free_page_bitmap[page] = 0
                    page_allocation_info[page] = None

            # 清空分配页框列表
            self.allocated_pages.clear()

    def generate_virtual_address(self):
        """生成虚拟地址（模拟程序的内存访问模式）"""
        # 使用加权随机，模拟程序的局部性原理（前几个页面访问概率更高）
        weights = [1.0 / ((i + 1) ** 0.5) for i in range(PAGES_PER_JOB)]
        # 随机选择虚拟页号（加权随机）
        vpn = random.choices(range(PAGES_PER_JOB), weights=weights)[0]
        # 随机生成页内偏移（0到255）
        offset = random.randint(0, PAGE_SIZE - 1)
        # 计算虚拟地址 = 虚拟页号 × 页大小 + 偏移量
        virtual_addr = vpn * PAGE_SIZE + offset
        return virtual_addr, vpn, offset

    def translate_address(self, virtual_addr, vpn, offset):
        """地址转换：将虚拟地址转换为物理地址"""
        if self.page_table[vpn] != -1:
            # 页面在内存中（页表项有效）
            ppn = self.page_table[vpn]  # 获取物理页框号
            physical_addr = ppn * PAGE_SIZE + offset  # 计算物理地址
            return False, physical_addr, ppn  # 返回：非缺页，物理地址，物理页框号
        else:
            # 缺页：页面不在内存中
            return True, -1, -1  # 返回：缺页，无效地址，无效页框号

    def handle_page_fault(self, vpn):
        """处理缺页中断：将请求的页面加载到内存"""
        # 首先尝试查找空闲的数据页框
        allocated_ppn = -1  # 分配的物理页框号，初始为无效值

        # 遍历已分配的页框，查找空闲页框（不在当前页表映射中的页框）
        for ppn in self.allocated_pages:
            if ppn not in self.page_table:  # 页框空闲（未被映射）
                allocated_ppn = ppn
                break

        if allocated_ppn == -1:
            # 没有空闲页框，需要页面替换
            if REPLACEMENT_ALGO == ReplaceAlgo.FIFO:
                # FIFO算法：替换最早进入的页面
                if self.access_history:
                    replaced_vpn = self.access_history.popleft()  # 从队列头部取出
                else:
                    # 如果历史记录为空，随机选择一个已加载的页面替换
                    in_memory_vpns = [v for v, p in enumerate(self.page_table) if p != -1]
                    replaced_vpn = random.choice(in_memory_vpns) if in_memory_vpns else 0
            else:  # LRU算法
                # LRU算法：替换最近最少使用的页面
                if self.lru_dict:
                    replaced_vpn, _ = self.lru_dict.popitem(last=False)  # 从有序字典头部取出
                else:
                    # 如果LRU记录为空，随机选择一个已加载的页面替换
                    in_memory_vpns = [v for v, p in enumerate(self.page_table) if p != -1]
                    replaced_vpn = random.choice(in_memory_vpns) if in_memory_vpns else 0

            # 获取被替换页面的物理页框号
            allocated_ppn = self.page_table[replaced_vpn]
            # 清除被替换页面的页表项
            self.page_table[replaced_vpn] = -1

        # 建立新页面的映射关系
        self.page_table[vpn] = allocated_ppn

        # 更新页框分配信息（线程安全）
        with bitmap_lock:
            page_allocation_info[allocated_ppn] = (self.job_id, vpn, "data")

        return allocated_ppn  # 返回分配的物理页框号

    def get_performance_stats(self):
        """获取进程性能统计"""
        fault_rate = self.page_fault_count / max(self.access_count, 1) if self.access_count > 0 else 0
        hit_rate = 1 - fault_rate
        return {
            'job_id': self.job_id,
            'page_faults': self.page_fault_count,
            'access_count': self.access_count,
            'fault_rate': fault_rate,
            'hit_rate': hit_rate
        }


def run_simulation():
    """运行模拟（在单独线程中执行）"""
    global ui_running, simulation_finished, simulation_paused, global_statistics

    # 初始化文件系统（模拟磁盘）
    init_file_system()

    # 创建进程列表（NUM_JOBS个进程）
    processes = [Process(job_id) for job_id in range(NUM_JOBS)]
    # 就绪队列（等待分配内存的进程ID列表）
    ready_queue = list(range(NUM_JOBS))

    # 模拟循环控制变量
    finished_processes = 0  # 已完成进程计数
    total_page_faults = 0  # 总缺页次数统计

    # 主模拟循环：直到所有进程完成或用户停止
    while finished_processes < NUM_JOBS and ui_running:
        # 检查是否暂停
        with simulation_pause_cond:
            while simulation_paused and ui_running:
                update_ui("status", "模拟已暂停")
                simulation_pause_cond.wait(timeout=0.5)  # 等待暂停状态结束

            if not ui_running:
                break  # 如果ui_running为False，退出循环

        # 更新内存位图显示
        update_ui("memory_bitmap", page_allocation_info)

        # 更新进程信息表格
        processes_info = []
        for proc in processes:
            # 计算缺页率 = 缺页次数 / 总访问次数
            fault_rate = proc.page_fault_count / max(proc.access_count, 1)
            processes_info.append((
                proc.job_id,  # 进程ID
                proc.state,  # 进程状态
                proc.page_fault_count,  # 缺页次数
                fault_rate,  # 缺页率
                proc.allocated_pages.copy()  # 分配的物理页框（副本）
            ))
        update_ui("process_info", processes_info)

        # 更新内存统计信息
        stats = get_memory_stats()

        # 统计各种状态的进程数量
        running_procs = sum(1 for p in processes if p.state == ProcessState.RUNNING)
        waiting_procs = sum(1 for p in processes if p.state == ProcessState.WAITING)
        finished_procs = sum(1 for p in processes if p.state == ProcessState.FINISHED)

        # 计算总访问次数和平均缺页率
        total_accesses = sum(p.access_count for p in processes)
        avg_fault_rate = sum(p.page_fault_count for p in processes) / max(total_accesses,
                                                                          1) if total_accesses > 0 else 0

        # 更新全局统计
        global_statistics['total_page_faults'] = sum(p.page_fault_count for p in processes)
        global_statistics['total_memory_accesses'] = total_accesses

        # 更新统计信息字典
        stats.update({
            'running_procs': running_procs,  # 运行中进程数
            'waiting_procs': waiting_procs,  # 等待中进程数
            'finished_procs': finished_procs,  # 已完成进程数
            'total_page_faults': global_statistics['total_page_faults'],  # 总缺页次数
            'avg_fault_rate': avg_fault_rate  # 平均缺页率
        })
        update_ui("stats", stats)
        update_ui("status", f"运行中 ({finished_processes}/{NUM_JOBS} 完成)")

        # 进程调度：为等待的进程分配内存
        with bitmap_lock:
            free_pages = BITMAP_SIZE - sum(free_page_bitmap)  # 计算空闲页框数

        # 遍历就绪队列，尝试为进程分配内存
        for job_id in ready_queue[:]:  # 使用副本遍历，避免修改遍历中的列表
            if free_pages >= PHYSICAL_PAGES_PER_PROCESS:  # 有足够空闲页框
                proc = processes[job_id]
                if proc.allocate_memory():  # 分配成功
                    proc.state = ProcessState.RUNNING  # 更新进程状态
                    ready_queue.remove(job_id)  # 从就绪队列移除
                    update_ui("log", f"进程 {job_id} 获得内存，页表基地址: {proc.page_table_base}")

        # 进程执行：每个运行中的进程执行一次内存访问
        for proc in processes:
            # 检查进程是否正在运行且未完成
            if proc.state == ProcessState.RUNNING and proc.access_count < ACCESS_TIMES_PER_PROCESS:
                # 生成虚拟地址（模拟程序执行）
                virtual_addr, vpn, offset = proc.generate_virtual_address()

                # 模拟进程访问内存前的随机休眠（0-100毫秒）
                sleep_time_ms = random.uniform(0, MAX_WAIT_TIME_MS)  # 生成0-100毫秒的随机数
                sleep_time_sec = sleep_time_ms / 1000.0  # 转换为秒
                time.sleep(sleep_time_sec)  # 线程休眠

                # 地址转换：虚拟地址->物理地址
                is_page_fault, physical_addr, ppn = proc.translate_address(virtual_addr, vpn, offset)

                if is_page_fault:
                    # 缺页处理
                    proc.page_fault_count += 1  # 进程缺页计数增加
                    total_page_faults += 1  # 总缺页计数增加
                    ppn = proc.handle_page_fault(vpn)  # 处理缺页中断
                    physical_addr = ppn * PAGE_SIZE + offset  # 重新计算物理地址

                    update_ui("log",
                              f"进程 {proc.job_id}: 虚拟地址 {virtual_addr} (页{vpn}) -> 缺页! -> 物理地址 {physical_addr} (休眠:{sleep_time_ms:.1f}ms)")
                else:
                    # 地址转换成功（页面命中）
                    update_ui("log",
                              f"进程 {proc.job_id}: 虚拟地址 {virtual_addr} (页{vpn}) -> 命中 -> 物理地址 {physical_addr} (休眠:{sleep_time_ms:.1f}ms)")

                # 更新访问历史（用于页面替换算法）
                if REPLACEMENT_ALGO == ReplaceAlgo.FIFO:
                    # FIFO算法：如果页面不在历史记录中，添加到队列尾部
                    if vpn not in proc.access_history:
                        proc.access_history.append(vpn)
                else:  # LRU算法
                    # 更新页面的访问时间（移动到字典尾部）
                    proc.lru_dict.pop(vpn, None)  # 移除旧记录（如果存在）
                    proc.lru_dict[vpn] = time.time()  # 添加新记录（当前时间）

                # 增加访问计数
                proc.access_count += 1

                # 检查进程是否完成（达到预定访问次数）
                if proc.access_count >= ACCESS_TIMES_PER_PROCESS:
                    proc.state = ProcessState.FINISHED  # 更新状态为已完成
                    # 计算缺页率
                    fault_rate = proc.page_fault_count / ACCESS_TIMES_PER_PROCESS

                    # 记录进程完成信息
                    update_ui("log", f"\n{'=' * 60}")
                    update_ui("log", f"进程 {proc.job_id} 运行结束")
                    update_ui("log", f"缺页中断次数: {proc.page_fault_count}")
                    update_ui("log", f"缺页率: {fault_rate:.2%}")
                    update_ui("log", f"总访问次数: {proc.access_count}")
                    update_ui("log", f"{'=' * 60}\n")

                    # 释放进程占用的内存
                    proc.release_memory()
                    finished_processes += 1  # 增加完成进程计数

                    # 记录内存释放信息
                    update_ui("log", f"进程 {proc.job_id} 结束，释放内存")

        # 控制模拟速度（避免运行过快）
        time.sleep(0.1)

    # 模拟结束处理
    if finished_processes >= NUM_JOBS:
        update_ui("log", "\n所有进程执行完毕，模拟结束")

        # 计算最终统计信息
        final_stats = calculate_final_statistics(processes)

        # 输出详细统计信息
        update_ui("performance_stats", final_stats)
        update_ui("simulation_finished", final_stats)

    # 更新最终状态显示
    update_ui("memory_bitmap", page_allocation_info)

    # 生成最终的进程信息
    processes_info = []
    for proc in processes:
        fault_rate = proc.page_fault_count / max(proc.access_count, 1)
        processes_info.append((
            proc.job_id,
            proc.state,
            proc.page_fault_count,
            fault_rate,
            proc.allocated_pages.copy()
        ))
    update_ui("process_info", processes_info)


# ==================== 主函数 ====================
def main():
    """主函数：创建GUI并启动应用程序"""
    root = tk.Tk()  # 创建主窗口
    app = MemorySimulatorUI(root)  # 创建UI实例
    root.mainloop()  # 启动GUI事件循环


if __name__ == "__main__":
    main()
