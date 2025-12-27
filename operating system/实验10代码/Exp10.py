import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
from matplotlib import rcParams

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


# 定义链表节点类
class MemoryBlock:
    def __init__(self, start_address, size):
        self.start_address = start_address
        self.size = size
        self.next = None


class AllocatedBlock(MemoryBlock):
    def __init__(self, job_name, start_address, size):
        super().__init__(start_address, size)
        self.job_name = job_name


class FreeBlock(MemoryBlock):
    def __init__(self, start_address, size):
        super().__init__(start_address, size)


class MemoryManager:
    def __init__(self, total_memory=100000):
        self.total_memory = total_memory
        # 初始化空闲区链表：只有一个大块
        self.free_list = FreeBlock(0, total_memory)
        self.free_list.next = None
        # 初始化已分配区链表：为空
        self.allocated_list = None
        self.operation_history = []
        # 为下次适应算法记录上一次查询的位置
        self.next_fit_pointer = self.free_list

    def _merge_free_blocks(self):
        """合并相邻的空闲块"""
        if self.free_list is None:
            return

        # 按起始地址排序空闲链表
        blocks = []
        current = self.free_list
        while current:
            blocks.append((current.start_address, current.size))
            current = current.next

        blocks.sort(key=lambda x: x[0])

        # 重建空闲链表并合并相邻块
        if not blocks:
            self.free_list = None
            return

        merged_blocks = []
        current_start, current_size = blocks[0]

        for i in range(1, len(blocks)):
            start, size = blocks[i]
            if current_start + current_size == start:
                # 相邻块，合并
                current_size += size
            else:
                merged_blocks.append((current_start, current_size))
                current_start, current_size = start, size

        merged_blocks.append((current_start, current_size))

        # 重建链表
        if merged_blocks:
            self.free_list = FreeBlock(merged_blocks[0][0], merged_blocks[0][1])
            current = self.free_list
            for i in range(1, len(merged_blocks)):
                new_block = FreeBlock(merged_blocks[i][0], merged_blocks[i][1])
                current.next = new_block
                current = new_block
            current.next = None
        else:
            self.free_list = None

    def first_fit_allocate(self, job_name, size):
        """最先适应分配算法"""
        # 检查作业名是否已存在
        current = self.allocated_list
        while current:
            if current.job_name == job_name:
                return False, f"作业 '{job_name}' 已存在！"
            current = current.next

        if size <= 0:
            return False, "分配大小必须为正整数！"

        # 遍历空闲链表，找到第一个足够大的空闲块
        prev = None
        current = self.free_list
        while current:
            if current.size >= size:
                # 分配这个块
                start_address = current.start_address

                # 创建新的已分配节点
                new_allocated = AllocatedBlock(job_name, start_address, size)
                new_allocated.next = self.allocated_list
                self.allocated_list = new_allocated

                # 更新空闲链表
                if current.size == size:
                    # 整个空闲块被分配，从空闲链表中移除
                    if prev:
                        prev.next = current.next
                    else:
                        self.free_list = current.next
                else:
                    # 切割空闲块
                    current.start_address += size
                    current.size -= size

                self.operation_history.append(
                    f"最先适应算法 - 分配作业 '{job_name}'，大小 {size}字节，起始地址 {start_address}")
                return True, start_address

            prev = current
            current = current.next

        return False, "内存不足，分配失败！"

    def best_fit_allocate(self, job_name, size):
        """最佳适应分配算法"""
        # 检查作业名是否已存在
        current = self.allocated_list
        while current:
            if current.job_name == job_name:
                return False, f"作业 '{job_name}' 已存在！"
            current = current.next

        if size <= 0:
            return False, "分配大小必须为正整数！"

        # 寻找最佳适应块（最小且足够大的空闲块）
        best_prev = None
        best_current = None
        min_remaining = float('inf')  # 初始化为无穷大

        prev = None
        current = self.free_list
        while current:
            if current.size >= size:
                remaining = current.size - size
                if remaining < min_remaining:
                    min_remaining = remaining
                    best_prev = prev
                    best_current = current
            prev = current
            current = current.next

        if best_current is None:
            return False, "内存不足，分配失败！"

        # 分配内存
        start_address = best_current.start_address

        # 创建新的已分配节点
        new_allocated = AllocatedBlock(job_name, start_address, size)
        new_allocated.next = self.allocated_list
        self.allocated_list = new_allocated

        # 更新空闲链表
        if best_current.size == size:
            # 整个空闲块被分配，从空闲链表中移除
            if best_prev:
                best_prev.next = best_current.next
            else:
                self.free_list = best_current.next
        else:
            # 切割空闲块
            best_current.start_address += size
            best_current.size -= size

        self.operation_history.append(f"最佳适应算法 - 分配作业 '{job_name}'，大小 {size}字节，起始地址 {start_address}")
        return True, start_address

    def worst_fit_allocate(self, job_name, size):
        """最坏适应分配算法"""
        # 检查作业名是否已存在
        current = self.allocated_list
        while current:
            if current.job_name == job_name:
                return False, f"作业 '{job_name}' 已存在！"
            current = current.next

        if size <= 0:
            return False, "分配大小必须为正整数！"

        # 寻找最坏适应块（最大且足够大的空闲块）
        worst_prev = None
        worst_current = None
        max_size = -1  # 初始化为-1

        prev = None
        current = self.free_list
        while current:
            if current.size >= size and current.size > max_size:
                max_size = current.size
                worst_prev = prev
                worst_current = current
            prev = current
            current = current.next

        if worst_current is None:
            return False, "内存不足，分配失败！"

        # 分配内存
        start_address = worst_current.start_address

        # 创建新的已分配节点
        new_allocated = AllocatedBlock(job_name, start_address, size)
        new_allocated.next = self.allocated_list
        self.allocated_list = new_allocated

        # 更新空闲链表
        if worst_current.size == size:
            # 整个空闲块被分配，从空闲链表中移除
            if worst_prev:
                worst_prev.next = worst_current.next
            else:
                self.free_list = worst_current.next
        else:
            # 切割空闲块
            worst_current.start_address += size
            worst_current.size -= size

        self.operation_history.append(f"最坏适应算法 - 分配作业 '{job_name}'，大小 {size}字节，起始地址 {start_address}")
        return True, start_address

    def next_fit_allocate(self, job_name, size):
        """下次适应分配算法"""
        # 检查作业名是否已存在
        current = self.allocated_list
        while current:
            if current.job_name == job_name:
                return False, f"作业 '{job_name}' 已存在！"
            current = current.next

        if size <= 0:
            return False, "分配大小必须为正整数！"

        # 如果没有设置指针或指针指向的空闲块已被分配，则从头开始
        if self.next_fit_pointer is None:
            self.next_fit_pointer = self.free_list

        if self.next_fit_pointer is None:  # 空闲链表为空
            return False, "内存不足，分配失败！"

        # 从指针位置开始查找
        start_search = self.next_fit_pointer
        first_iteration = True
        current = start_search
        prev = None

        # 找到current的前一个节点
        temp_prev = None
        temp = self.free_list
        while temp and temp != current:
            temp_prev = temp
            temp = temp.next

        # 循环查找
        while first_iteration or current != start_search:
            if current is None:
                # 到达链表末尾，从头开始
                current = self.free_list
                prev = None
                if current == start_search:
                    break  # 已经找了一圈
                first_iteration = False
                continue

            if current.size >= size:
                # 找到合适的块
                start_address = current.start_address

                # 创建新的已分配节点
                new_allocated = AllocatedBlock(job_name, start_address, size)
                new_allocated.next = self.allocated_list
                self.allocated_list = new_allocated

                # 更新空闲链表和指针
                if current.size == size:
                    # 整个空闲块被分配
                    if prev:
                        prev.next = current.next
                    else:
                        self.free_list = current.next
                    self.next_fit_pointer = current.next  # 指针指向下一个块
                else:
                    # 切割空闲块
                    current.start_address += size
                    current.size -= size
                    self.next_fit_pointer = current  # 指针指向剩余部分

                self.operation_history.append(
                    f"下次适应算法 - 分配作业 '{job_name}'，大小 {size}字节，起始地址 {start_address}")
                return True, start_address

            prev = current
            current = current.next
            first_iteration = False

        return False, "内存不足，分配失败！"

    def allocate_memory(self, job_name, size, algorithm):
        """根据选择的算法分配内存"""
        if algorithm == "最先适应":
            return self.first_fit_allocate(job_name, size)
        elif algorithm == "最佳适应":
            return self.best_fit_allocate(job_name, size)
        elif algorithm == "最坏适应":
            return self.worst_fit_allocate(job_name, size)
        elif algorithm == "下次适应":
            return self.next_fit_allocate(job_name, size)
        else:
            return False, "未知的算法！"

    def free_memory(self, job_name):
        """回收内存"""
        # 在已分配链表中查找作业
        prev = None
        current = self.allocated_list

        while current:
            if current.job_name == job_name:
                # 找到要回收的作业
                start_address = current.start_address
                size = current.size

                # 从已分配链表中移除
                if prev:
                    prev.next = current.next
                else:
                    self.allocated_list = current.next

                # 将回收的内存加入空闲链表
                new_free = FreeBlock(start_address, size)
                if self.free_list is None:
                    self.free_list = new_free
                else:
                    # 插入到合适位置以保持地址有序
                    if start_address < self.free_list.start_address:
                        new_free.next = self.free_list
                        self.free_list = new_free
                    else:
                        temp_prev = None
                        temp = self.free_list
                        while temp and temp.start_address < start_address:
                            temp_prev = temp
                            temp = temp.next
                        if temp_prev:
                            temp_prev.next = new_free
                        new_free.next = temp

                # 合并相邻空闲块
                self._merge_free_blocks()

                self.operation_history.append(f"回收作业 '{job_name}'，释放空间 {size}字节 (起始地址: {start_address})")
                return True, f"成功回收作业 '{job_name}' 占用的内存。"

            prev = current
            current = current.next

        return False, f"作业 '{job_name}' 不存在！"

    def get_memory_status(self):
        """获取内存状态信息"""
        status = "=== 已分配分区情况 ===\n"
        status += "作业名\t起始地址\t长度\n"

        # 收集所有已分配块并按起始地址排序
        allocated_blocks = []
        current = self.allocated_list
        while current:
            allocated_blocks.append((current.job_name, current.start_address, current.size))
            current = current.next

        # 按起始地址排序
        allocated_blocks.sort(key=lambda x: x[1])

        for job_name, start, size in allocated_blocks:
            status += f"{job_name}\t{start}\t\t{size}\n"

        status += "\n=== 空闲分区表 ===\n"
        status += "起始地址\t长度\n"

        current = self.free_list
        while current:
            status += f"{current.start_address}\t\t{current.size}\n"
            current = current.next

        return status

    def visualize_memory(self, ax, algorithm):
        """可视化内存状态"""
        ax.clear()

        # 设置颜色
        allocated_color = 'lightcoral'
        free_color = 'lightgreen'

        # 绘制已分配的内存块
        current = self.allocated_list
        while current:
            # 只有当内存块足够大时才显示标签
            if current.size >= self.total_memory * 0.01:  # 至少占1%才显示标签
                rect = patches.Rectangle(
                    (current.start_address, 0),
                    current.size, 1,
                    linewidth=1,
                    edgecolor='black',
                    facecolor=allocated_color
                )
                ax.add_patch(rect)
                # 添加作业名标签 - 增大字体
                ax.text(
                    current.start_address + current.size / 2, 0.5,
                    f'{current.job_name}\n{current.size}字节',
                    ha='center', va='center', fontsize=10, fontweight='bold'
                )
            current = current.next

        # 绘制空闲内存块
        current = self.free_list
        while current:
            # 只有当内存块足够大时才显示标签
            if current.size >= self.total_memory * 0.01:  # 至少占1%才显示标签
                rect = patches.Rectangle(
                    (current.start_address, 0),
                    current.size, 1,
                    linewidth=1,
                    edgecolor='black',
                    facecolor=free_color
                )
                ax.add_patch(rect)
                # 添加"空闲"标签 - 增大字体
                ax.text(
                    current.start_address + current.size / 2, 0.5,
                    f'空闲\n{current.size}字节',
                    ha='center', va='center', fontsize=10, color='darkgreen'
                )
            current = current.next

        # 设置图形属性
        ax.set_xlim(0, self.total_memory)
        ax.set_ylim(0, 1)
        ax.set_xlabel('内存地址 (字节)', fontsize=12)  # 增大坐标轴标签字体
        ax.set_title(f'内存分配状态 - {algorithm}算法', fontsize=14, fontweight='bold')  # 增大标题字体
        ax.set_yticks([])  # 隐藏Y轴刻度

        # 增大坐标轴刻度字体
        ax.tick_params(axis='x', labelsize=10)


class MemoryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("内存分配管理器 - 支持四种算法")
        self.memory_manager = MemoryManager()

        # 当前选择的算法
        self.current_algorithm = tk.StringVar(value="最先适应")

        # 设置窗口图标和主题
        self.root.geometry("1000x900")  # 增大窗口尺寸

        # 创建UI
        self.setup_ui()

        # 初始显示
        self.update_display()

    def setup_ui(self):
        # 设置默认字体
        default_font = ("Microsoft YaHei", 10)  # 使用微软雅黑字体
        self.root.option_add("*Font", default_font)

        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题和说明
        title_label = ttk.Label(main_frame, text="内存分配管理器 (支持四种算法)",
                                font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # 算法选择区域
        algo_frame = ttk.LabelFrame(main_frame, text="算法选择", padding="5")
        algo_frame.pack(fill=tk.X, pady=(0, 10))

        algorithms = ["最先适应", "最佳适应", "最坏适应", "下次适应"]
        algo_combo = ttk.Combobox(algo_frame, textvariable=self.current_algorithm,
                                  values=algorithms, state="readonly", width=15, font=("Microsoft YaHei", 10))
        algo_combo.pack(side=tk.LEFT, padx=5)
        algo_combo.bind('<<ComboboxSelected>>', self.on_algorithm_change)

        ttk.Label(algo_frame, text="当前算法:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        self.algo_label = ttk.Label(algo_frame, text=self.current_algorithm.get(),
                                    font=("Microsoft YaHei", 12, "bold"), foreground="blue")
        self.algo_label.pack(side=tk.LEFT, padx=5)

        # 功能键说明
        func_frame = ttk.LabelFrame(main_frame, text="功能键说明", padding="5")
        func_frame.pack(fill=tk.X, pady=(0, 10))

        func_text = tk.Text(func_frame, width=80, height=4, font=("Consolas", 11))  # 增大字体
        func_text.insert(tk.END,
                         "0 - 退出程序\n1 - 为作业分配内存 (输入格式: 作业名 内存大小)\n2 - 回收内存 (输入格式: 作业名)\n3 - 显示内存分配情况")
        func_text.config(state=tk.DISABLED)
        func_text.pack(fill=tk.X)

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入", padding="5")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建更人性化的输入方式
        input_method_frame = ttk.Frame(input_frame)
        input_method_frame.pack(fill=tk.X)

        # 方法1：传统功能键+参数方式
        traditional_frame = ttk.LabelFrame(input_method_frame, text="方法1: 功能键+参数")
        traditional_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(traditional_frame, text="功能键:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, padx=(0, 5))
        self.func_entry = ttk.Entry(traditional_frame, width=5, font=("Microsoft YaHei", 10))
        self.func_entry.grid(row=0, column=1, padx=(0, 15))
        self.func_entry.bind('<Return>', lambda e: self.param_entry.focus())

        ttk.Label(traditional_frame, text="参数:", font=("Microsoft YaHei", 10)).grid(row=0, column=2, padx=(0, 5))
        self.param_entry = ttk.Entry(traditional_frame, width=20, font=("Microsoft YaHei", 10))
        self.param_entry.grid(row=0, column=3, padx=(0, 15))
        self.param_entry.bind('<Return>', self.process_input)

        ttk.Button(traditional_frame, text="执行", command=self.process_input).grid(row=0, column=4)

        # 方法2：直接命令方式
        command_frame = ttk.LabelFrame(input_method_frame, text="方法2: 直接命令")
        command_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(command_frame, text="命令:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, padx=(0, 5))
        self.command_entry = ttk.Entry(command_frame, width=25, font=("Microsoft YaHei", 10))
        self.command_entry.grid(row=0, column=1, padx=(0, 15))
        self.command_entry.bind('<Return>', self.process_command)
        self.command_entry.insert(0, "例如: 分配 A 3000 或 回收 B")

        ttk.Button(command_frame, text="执行", command=self.process_command).grid(row=0, column=2)

        # 快速操作按钮
        quick_frame = ttk.LabelFrame(input_frame, text="快速操作")
        quick_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(quick_frame, text="分配 A(3000)",
                   command=lambda: self.quick_allocate("A", 3000)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="分配 B(2000)",
                   command=lambda: self.quick_allocate("B", 2000)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="分配 C(4000)",
                   command=lambda: self.quick_allocate("C", 4000)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="回收 B",
                   command=lambda: self.quick_free("B")).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="分配 D(2500)",
                   command=lambda: self.quick_allocate("D", 2500)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="回收 A",
                   command=lambda: self.quick_free("A")).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="分配 E(1500)",
                   command=lambda: self.quick_allocate("E", 1500)).pack(side=tk.LEFT, padx=5)

        # 内存状态显示
        status_frame = ttk.LabelFrame(main_frame, text="内存状态", padding="5")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.status_text = scrolledtext.ScrolledText(status_frame, width=80, height=12, font=("Consolas", 11))  # 增大字体
        self.status_text.pack(fill=tk.BOTH, expand=True)

        # 内存可视化区域
        viz_frame = ttk.LabelFrame(main_frame, text="内存可视化", padding="5")
        viz_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建图形和轴 - 增大图形尺寸
        self.fig, self.ax = plt.subplots(figsize=(12, 3))  # 增大图形高度
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 操作历史
        history_frame = ttk.LabelFrame(main_frame, text="操作历史", padding="5")
        history_frame.pack(fill=tk.X, pady=(0, 10))

        self.history_text = scrolledtext.ScrolledText(history_frame, width=80, height=4, font=("Consolas", 10))  # 增大字体
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="运行测试案例", command=self.run_test_cases).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置内存", command=self.reset_memory).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出程序", command=self.root.quit).pack(side=tk.LEFT, padx=5)

    def on_algorithm_change(self, event=None):
        """当算法改变时更新显示"""
        self.algo_label.config(text=self.current_algorithm.get())
        self.update_display()
        self.add_to_history(f"切换算法为: {self.current_algorithm.get()}")

    def add_to_history(self, message):
        """添加操作历史"""
        self.memory_manager.operation_history.append(message)
        self.update_display()

    def process_input(self, event=None):
        """处理传统功能键+参数输入"""
        func_key = self.func_entry.get().strip()
        params = self.param_entry.get().strip()

        if not func_key:
            messagebox.showerror("错误", "请输入功能键！")
            return

        # 处理不同的功能键
        if func_key == '0':
            # 退出程序
            self.root.quit()
        elif func_key == '1':
            # 分配内存
            self.allocate_memory(params)
        elif func_key == '2':
            # 回收内存
            self.free_memory(params)
        elif func_key == '3':
            # 显示内存状态
            self.update_display()
            messagebox.showinfo("内存状态", "已更新内存状态显示")
        else:
            messagebox.showerror("错误", "无效的功能键！")

        # 清空输入框
        self.func_entry.delete(0, tk.END)
        self.param_entry.delete(0, tk.END)

    def process_command(self, event=None):
        """处理直接命令输入"""
        command = self.command_entry.get().strip()

        if not command:
            messagebox.showerror("错误", "请输入命令！")
            return

        parts = command.split()
        if len(parts) < 1:
            messagebox.showerror("错误", "命令格式不正确！")
            return

        action = parts[0].lower()

        if action in ["分配", "allocate", "1"]:
            if len(parts) != 3:
                messagebox.showerror("错误", "分配命令格式：分配 作业名 大小")
                return
            job_name, size_str = parts[1], parts[2]
            try:
                size = int(size_str)
            except ValueError:
                messagebox.showerror("错误", "内存大小必须为整数！")
                return
            self.quick_allocate(job_name, size)

        elif action in ["回收", "free", "2"]:
            if len(parts) != 2:
                messagebox.showerror("错误", "回收命令格式：回收 作业名")
                return
            job_name = parts[1]
            self.quick_free(job_name)

        elif action in ["显示", "show", "3"]:
            self.update_display()
            messagebox.showinfo("内存状态", "已更新内存状态显示")

        elif action in ["退出", "exit", "0"]:
            self.root.quit()

        else:
            messagebox.showerror("错误", "未知命令！可用命令：分配/回收/显示/退出")

        # 清空命令输入框
        self.command_entry.delete(0, tk.END)

    def quick_allocate(self, job_name, size):
        """快速分配内存"""
        algorithm = self.current_algorithm.get()
        success, result = self.memory_manager.allocate_memory(job_name, size, algorithm)

        if success:
            messagebox.showinfo("成功", f"分配成功！起始地址: {result}")
        else:
            messagebox.showerror("分配失败", result)

        self.update_display()

    def quick_free(self, job_name):
        """快速回收内存"""
        success, result = self.memory_manager.free_memory(job_name)

        if success:
            messagebox.showinfo("成功", result)
        else:
            messagebox.showerror("回收失败", result)

        self.update_display()

    def allocate_memory(self, params):
        """分配内存"""
        parts = params.split()
        if len(parts) != 2:
            messagebox.showerror("错误", "输入格式错误！正确格式：作业名 内存大小")
            return

        job_name, size_str = parts
        try:
            size = int(size_str)
        except ValueError:
            messagebox.showerror("错误", "内存大小必须为整数！")
            return

        self.quick_allocate(job_name, size)

    def free_memory(self, params):
        """回收内存"""
        job_name = params.strip()
        if not job_name:
            messagebox.showerror("错误", "请输入要回收的作业名！")
            return

        self.quick_free(job_name)

    def update_display(self):
        """更新所有显示区域"""
        # 更新内存状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(1.0, self.memory_manager.get_memory_status())
        self.status_text.config(state=tk.DISABLED)

        # 更新操作历史
        self.history_text.delete(1.0, tk.END)
        for record in self.memory_manager.operation_history[-10:]:  # 显示最近10条记录
            self.history_text.insert(tk.END, record + '\n')

        # 更新内存可视化图
        self.memory_manager.visualize_memory(self.ax, self.current_algorithm.get())
        self.canvas.draw()

    def reset_memory(self):
        """重置内存"""
        self.memory_manager = MemoryManager()
        messagebox.showinfo("成功", "内存已重置！")
        self.update_display()

    def run_test_cases(self):
        """运行测试案例"""
        test_cases = [
            ("分配 A 3000"),
            ("分配 B 2000"),
            ("分配 C 4000"),
            ("回收 B"),
            ("分配 D 2500"),
            ("回收 A"),
            ("分配 E 1500")
        ]

        for command in test_cases:
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, command)
            self.process_command()
            self.root.update()  # 更新界面以显示变化
            self.root.after(500)  # 添加短暂延迟以便观察每一步

        messagebox.showinfo("测试完成", "测试案例执行完毕！")


if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryManagerApp(root)
    root.mainloop()
