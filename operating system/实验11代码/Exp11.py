import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import math

class PagingMemoryManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("分页存储管理系统")
        self.root.geometry("900x700")
        
        # 初始化内存管理器
        self.total_memory = 100000 #总内存
        self.page_size = 1000 #页框大小
        self.total_frames = self.total_memory // self.page_size #页面数量
        self.memory = [None] * self.total_frames #已占用内存数组
        self.page_tables = {}
        self.job_sizes = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重，使界面可调整大小
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="分页存储管理系统", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 系统信息
        info_text = f"内存大小: {self.total_memory}字节, 页框大小: {self.page_size}字节, 总页框数: {self.total_frames}个(0-{self.total_frames-1})"
        info_label = ttk.Label(main_frame, text=info_text)
        info_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # 功能区域
        func_frame = ttk.LabelFrame(main_frame, text="功能操作", padding="10")
        func_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        func_frame.columnconfigure(1, weight=1)
        
        # 作业名输入
        ttk.Label(func_frame, text="作业名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.job_name_var = tk.StringVar()
        job_name_entry = ttk.Entry(func_frame, textvariable=self.job_name_var, width=15)
        job_name_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        # 内存大小输入
        ttk.Label(func_frame, text="内存大小(字节):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.memory_size_var = tk.StringVar()
        memory_size_entry = ttk.Entry(func_frame, textvariable=self.memory_size_var, width=15)
        memory_size_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # 逻辑地址输入
        ttk.Label(func_frame, text="逻辑地址:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.logical_addr_var = tk.StringVar()
        logical_addr_entry = ttk.Entry(func_frame, textvariable=self.logical_addr_var, width=15)
        logical_addr_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 10))
        
        # 按钮区域
        button_frame = ttk.Frame(func_frame)
        button_frame.grid(row=0, column=4, rowspan=2, padx=(20, 0))
        
        ttk.Button(button_frame, text="分配内存", 
                  command=self.allocate_memory).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
        ttk.Button(button_frame, text="回收内存", 
                  command=self.deallocate_memory).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W+tk.E)
        ttk.Button(button_frame, text="显示内存", 
                  command=self.show_memory).grid(row=1, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
        ttk.Button(button_frame, text="访问内存", 
                  command=self.access_memory).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W+tk.E)
        ttk.Button(button_frame, text="运行测试", 
                  command=self.run_test).grid(row=2, column=0, columnspan=2, padx=5, pady=(10, 2), sticky=tk.W+tk.E)
        
        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text="输出信息", padding="5")
        output_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, width=80, height=20, state=tk.DISABLED)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 内存可视化区域
        mem_viz_frame = ttk.LabelFrame(main_frame, text="内存可视化", padding="5")
        mem_viz_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建画布用于内存可视化
        self.canvas = tk.Canvas(mem_viz_frame, width=860, height=100, bg='white')
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
    def log_message(self, message):
        """在输出区域添加消息"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        
    def clear_output(self):
        """清空输出区域"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
    def allocate_memory(self):
        """为作业分配内存"""
        job_name = self.job_name_var.get().strip()
        if not job_name: #未输入作业名
            messagebox.showerror("错误", "请输入作业名！")
            return
            
        try:
            size = int(self.memory_size_var.get())
            if size <= 0: #作业大小非法
                messagebox.showerror("错误", "作业大小必须为正整数！")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")
            return
            
        if job_name in self.page_tables: #作业已存在
            messagebox.showerror("错误", f"作业 '{job_name}' 已存在！")
            return
            
        # 计算所需页面数
        pages_needed = (size + self.page_size - 1) // self.page_size
        
        if pages_needed > self.total_frames:
            messagebox.showerror("错误", f"作业 '{job_name}' 所需内存超过系统总内存！")
            return
            
        # 查找空闲页框
        free_frames = []
        for i in range(self.total_frames):
            if self.memory[i] is None:
                free_frames.append(i)
            if len(free_frames) == pages_needed:
                break
                
        if len(free_frames) < pages_needed:#未找到足够页面数量
            self.log_message(f"错误：内存不足，无法为作业 '{job_name}' 分配 {size} 字节内存！")
            self.status_var.set(f"内存不足，无法为作业 '{job_name}' 分配内存")
            return
            
        # 分配内存
        for frame in free_frames:
            self.memory[frame] = job_name
            
        self.page_tables[job_name] = free_frames
        self.job_sizes[job_name] = size
        
        self.log_message(f"成功为作业 '{job_name}' 分配 {size} 字节内存，占用 {pages_needed} 个页框")
        self.status_var.set(f"已为作业 '{job_name}' 分配内存")
        
        # 更新内存可视化
        self.update_memory_visualization()
        
    def deallocate_memory(self):
        """回收作业内存"""
        job_name = self.job_name_var.get().strip()
        if not job_name:
            messagebox.showerror("错误", "请输入作业名！")
            return
            
        if job_name not in self.page_tables:
            messagebox.showerror("错误", f"作业 '{job_name}' 不存在！")
            return
            
        # 回收内存
        for frame in self.page_tables[job_name]:
            self.memory[frame] = None
            
        del self.page_tables[job_name]
        del self.job_sizes[job_name]
        
        self.log_message(f"成功回收作业 '{job_name}' 的内存")
        self.status_var.set(f"已回收作业 '{job_name}' 的内存")
        
        # 更新内存可视化
        self.update_memory_visualization()
        
    def show_memory(self):
        """显示内存分配情况"""
        self.clear_output()
        self.log_message("=" * 60)
        self.log_message("内存分配情况")
        self.log_message("=" * 60)
        
        # 按进程显示内存分配情况
        self.log_message("\n1. 按进程显示内存分配情况：")
        self.log_message("-" * 40)
        
        if not self.page_tables:
            self.log_message("暂无作业运行")
        else:
            self.log_message(f"{'作业名':<10} {'占用页面数':<12} {'占用页框号':<20}")
            self.log_message("-" * 40)
            
            for job_name, frames in self.page_tables.items():
                pages = len(frames)
                # 将连续的页框号合并显示
                frame_ranges = []
                if frames:
                    start = frames[0]
                    end = frames[0]
                    
                    for i in range(1, len(frames)):
                        if frames[i] == end + 1:
                            end = frames[i]
                        else:
                            if start == end:
                                frame_ranges.append(str(start))
                            else:
                                frame_ranges.append(f"{start}-{end}")
                            start = end = frames[i]
                    
                    if start == end:
                        frame_ranges.append(str(start))
                    else:
                        frame_ranges.append(f"{start}-{end}")
                
                frame_str = ", ".join(frame_ranges)
                self.log_message(f"{job_name:<10} {pages:<12} {frame_str:<20}")
        
        # 显示空闲区情况
        self.log_message(f"\n2. 空闲区情况：")
        self.log_message("-" * 40)
        
        free_blocks = []
        start = None
        length = 0
        
        for i in range(self.total_frames):
            if self.memory[i] is None:
                if start is None:
                    start = i
                length += 1
            else:
                if start is not None:
                    free_blocks.append((start * self.page_size, length * self.page_size))
                    start = None
                    length = 0
                    
        if start is not None:
            free_blocks.append((start * self.page_size, length * self.page_size))
            
        if free_blocks:
            self.log_message(f"{'起始地址':<12} {'长度':<12}")
            self.log_message("-" * 24)
            for start_addr, length in free_blocks:
                self.log_message(f"{start_addr:<12} {length:<12}")
        else:
            self.log_message("无空闲内存")
            
        self.log_message("=" * 60)
        self.status_var.set("已显示内存分配情况")
        
    def access_memory(self):
        """访问内存，计算物理地址"""
        job_name = self.job_name_var.get().strip()
        if not job_name:
            messagebox.showerror("错误", "请输入作业名！")
            return
            
        try:
            logical_address = int(self.logical_addr_var.get())
            if logical_address < 0:
                messagebox.showerror("错误", "地址不能为负数！")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")
            return
            
        if job_name not in self.page_tables:
            messagebox.showerror("错误", f"作业 '{job_name}' 不存在！")
            return
            
        frames = self.page_tables[job_name]
        page_size = self.page_size
        total_size = self.job_sizes[job_name]
        
        # 计算页号和页内偏移
        page_number = logical_address // page_size
        offset = logical_address % page_size
        
        if logical_address >= total_size:
            self.log_message(f"错误：逻辑地址 {logical_address} 越界！作业 '{job_name}' 大小为 {total_size} 字节")
            self.status_var.set(f"作业 '{job_name}' 访问越界")
            return
            
        if page_number >= len(frames):
            self.log_message(f"错误：页号 {page_number} 越界！作业 '{job_name}' 只有 {len(frames)} 个页面")
            self.status_var.set(f"作业 '{job_name}' 访问越界")
            return
            
        frame_number = frames[page_number]
        physical_address = frame_number * page_size + offset
        
        self.log_message(f"作业 '{job_name}' 逻辑地址 {logical_address} 对应的物理地址信息：")
        self.log_message(f"  页号: {page_number}, 页内偏移: {offset}")
        self.log_message(f"  物理页框号: {frame_number}")
        self.log_message(f"  物理地址: {physical_address} (即 {frame_number}号页框 {offset}偏移)")
        self.status_var.set(f"作业 '{job_name}' 地址转换完成")
        
    def update_memory_visualization(self):
        """更新内存可视化"""
        self.canvas.delete("all")
        
        # 计算每个页框的显示宽度
        frame_width = 860 / self.total_frames
        
        # 为每个作业分配颜色
        jobs = list(set([job for job in self.memory if job is not None]))
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", 
                 "#FF9FF3", "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43"]
        job_colors = {}
        for i, job in enumerate(jobs):
            job_colors[job] = colors[i % len(colors)]
        
        # 绘制每个页框
        for i in range(self.total_frames):
            x1 = i * frame_width
            x2 = (i + 1) * frame_width
            job = self.memory[i]
            
            if job is None:
                # 空闲页框 - 白色
                color = "white"
                outline = "black"
            else:
                # 已分配页框 - 使用作业对应颜色
                color = job_colors.get(job, "gray")
                outline = "black"
            
            # 绘制矩形
            self.canvas.create_rectangle(x1, 10, x2, 60, fill=color, outline=outline)
            
            # 显示页框号
            if frame_width > 15:  # 只有宽度足够时才显示页框号
                self.canvas.create_text((x1 + x2) / 2, 20, text=str(i), font=("Arial", 8))
            
            # 显示作业名（如果页框足够宽）
            if frame_width > 30 and job is not None:
                self.canvas.create_text((x1 + x2) / 2, 40, text=job, font=("Arial", 8))
        
        # 添加图例
        legend_x = 10
        legend_y = 70
        for job, color in job_colors.items():
            self.canvas.create_rectangle(legend_x, legend_y, legend_x + 15, legend_y + 15, 
                                       fill=color, outline="black")
            self.canvas.create_text(legend_x + 20, legend_y + 7, text=job, anchor=tk.W, font=("Arial", 8))
            legend_x += 60
            
        # 空闲页框图例
        self.canvas.create_rectangle(legend_x, legend_y, legend_x + 15, legend_y + 15, 
                                   fill="white", outline="black")
        self.canvas.create_text(legend_x + 20, legend_y + 7, text="空闲", anchor=tk.W, font=("Arial", 8))
        
    def run_test(self):
        """运行测试案例"""
        self.clear_output()
        self.log_message("开始执行测试案例...")
        
        # 重置内存
        self.memory = [None] * self.total_frames
        self.page_tables = {}
        self.job_sizes = {}
        
        # 测试步骤
        test_steps = [
            ('分配', 'a', 5000),
            ('分配', 'b', 38400),
            ('分配', 'c', 49700),
            ('分配', 'd', 11000),  # 应该提示内存不够
            ('回收', 'b', None),
            ('分配', 'd', 25000),
            ('分配', 'e', 16000),
            ('回收', 'a', None),
            ('分配', 'f', 10000),  # 应该提示内存不够
            ('访问', 'e', 15437),  # 显示95号页框 437偏移
            ('访问', 'c', 50000),  # 提示访问越界
            ('显示', None, None)
        ]
        
        for i, step in enumerate(test_steps):
            self.log_message(f"\n步骤 {i+1}: {step[0]} {step[1]} {step[2] if step[2] else ''}")
            
            if step[0] == '分配':
                # 模拟分配内存
                job_name = step[1]
                size = step[2]
                
                if job_name in self.page_tables:
                    self.log_message(f"错误：作业 '{job_name}' 已存在！")
                    continue
                    
                pages_needed = (size + self.page_size - 1) // self.page_size
                
                if pages_needed > self.total_frames:
                    self.log_message(f"错误：作业 '{job_name}' 所需内存超过系统总内存！")
                    continue
                    
                # 查找空闲页框
                free_frames = []
                for j in range(self.total_frames):
                    if self.memory[j] is None:
                        free_frames.append(j)
                    if len(free_frames) == pages_needed:
                        break
                        
                if len(free_frames) < pages_needed:
                    self.log_message(f"错误：内存不足，无法为作业 '{job_name}' 分配 {size} 字节内存！")
                    continue
                    
                # 分配内存
                for frame in free_frames:
                    self.memory[frame] = job_name
                    
                self.page_tables[job_name] = free_frames
                self.job_sizes[job_name] = size
                self.log_message(f"成功为作业 '{job_name}' 分配 {size} 字节内存，占用 {pages_needed} 个页框")
                
            elif step[0] == '回收':
                job_name = step[1]
                if job_name not in self.page_tables:
                    self.log_message(f"错误：作业 '{job_name}' 不存在！")
                    continue
                    
                # 回收内存
                for frame in self.page_tables[job_name]:
                    self.memory[frame] = None
                    
                del self.page_tables[job_name]
                del self.job_sizes[job_name]
                self.log_message(f"成功回收作业 '{job_name}' 的内存")
                
            elif step[0] == '访问':
                job_name = step[1]
                logical_address = step[2]
                
                if job_name not in self.page_tables:
                    self.log_message(f"错误：作业 '{job_name}' 不存在！")
                    continue
                    
                frames = self.page_tables[job_name]
                page_size = self.page_size
                total_size = self.job_sizes[job_name]
                
                page_number = logical_address // page_size
                offset = logical_address % page_size
                
                if logical_address >= total_size:
                    self.log_message(f"错误：逻辑地址 {logical_address} 越界！作业 '{job_name}' 大小为 {total_size} 字节")
                    continue
                    
                if page_number >= len(frames):
                    self.log_message(f"错误：页号 {page_number} 越界！作业 '{job_name}' 只有 {len(frames)} 个页面")
                    continue
                    
                frame_number = frames[page_number]
                physical_address = frame_number * page_size + offset
                
                self.log_message(f"逻辑地址 {logical_address} 对应的物理地址信息：")
                self.log_message(f"  页号: {page_number}, 页内偏移: {offset}")
                self.log_message(f"  物理页框号: {frame_number}")
                self.log_message(f"  物理地址: {physical_address} (即 {frame_number}号页框 {offset}偏移)")
                
            elif step[0] == '显示':
                self.show_memory()
        
        self.log_message("\n测试案例执行完成！")
        self.status_var.set("测试案例执行完成")
        
        # 更新内存可视化
        self.update_memory_visualization()

def main():
    root = tk.Tk()
    app = PagingMemoryManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()