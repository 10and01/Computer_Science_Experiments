import threading
import time
import random
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from datetime import datetime
import matplotlib.gridspec as gridspec
import matplotlib
import tkinter as tk
from tkinter import ttk
import threading

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 使用Semaphore模拟信号量
class Semaphore:
    def __init__(self, value=1):
        self._value = value
        self._condition = threading.Condition()
        self._waiting_threads = deque()  # 等待队列

    def wait(self):
        with self._condition:
            if self._value <= 0:
                # 将当前线程加入等待队列
                self._waiting_threads.append(threading.get_ident())
                while self._value <= 0 or self._waiting_threads[0] != threading.get_ident():
                    self._condition.wait()
                # 当前线程被唤醒，从队列中移除
                self._waiting_threads.popleft()
            self._value -= 1

    def signal(self):
        with self._condition:
            self._value += 1
            self._condition.notify_all()

class ProducerConsumer:
    def __init__(self, num_producers=3, num_consumers=2, buffer_size=10, total_products=100):
        # 库存大小
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=self.buffer_size)

        # 信号量
        self.mutex = Semaphore(1)  # 互斥信号量，保护共享资源
        self.empty = Semaphore(self.buffer_size)  # 空缓冲区数量
        self.full = Semaphore(0)  # 满缓冲区数量

        # 共享变量
        self.product_id = 0  # 产品编号
        self.produced_count = 0
        self.consumed_count = 0
        self.total_products = total_products  # 总产品数量
        
        # 线程数量
        self.num_producers = num_producers
        self.num_consumers = num_consumers
        
        # 可视化数据记录
        self.time_points = []  # 时间点
        self.stock_levels = []  # 库存水平
        self.production_rates = []  # 生产速率
        self.consumption_rates = []  # 消费速率
        self.producer_activities = {i+1: [] for i in range(self.num_producers)}  # 生产者活动
        self.consumer_activities = {i+1: [] for i in range(self.num_consumers)}  # 消费者活动
        self.start_time = time.time()
        
        # 线程状态
        self.producer_status = {i+1: "等待" for i in range(self.num_producers)}  # 生产者状态
        self.consumer_status = {i+1: "等待" for i in range(self.num_consumers)}  # 消费者状态
        
        # 可视化控制
        self.visualization_running = True

    def producer(self, producer_id):
        """生产者线程函数"""
        while True:
            # 不获取锁，检查是否达到总产品数量
            with self.mutex._condition:
                if self.produced_count >= self.total_products:
                    break

            # 更新状态为等待生产
            self.producer_status[producer_id] = "等待生产"
            
            # 生产产品
            self.empty.wait()  # 等待空缓冲区
            self.mutex.wait()  # 进入临界区

            # 获取锁，检查是否还需要生产（已生产>=最大容量）
            if self.produced_count >= self.total_products:
                self.mutex.signal()
                self.full.signal()  
                break

            # 更新状态为生产中
            self.producer_status[producer_id] = "生产中"
            
            # 生产产品
            self.product_id += 1
            current_id = self.product_id
            self.buffer.append(current_id)
            self.produced_count += 1

            current_stock = len(self.buffer)
            
            # 记录数据
            current_time = time.time() - self.start_time
            self.time_points.append(current_time)
            self.stock_levels.append(current_stock)
            self.producer_activities[producer_id].append((current_time, current_id))

            print(f"生产者{producer_id}(线程{threading.get_ident()}) "
                  f"生产了产品{current_id}, 当前库存量: {current_stock}")

            self.mutex.signal()  # 离开临界区
            self.full.signal()  # 增加满缓冲区
            time.sleep(0.2)#生产完休眠

            # 更新状态为完成
            self.producer_status[producer_id] = "完成"
            
            
            # 重置状态为等待
            self.producer_status[producer_id] = "等待"

    def consumer(self, consumer_id):
        """消费者线程函数"""
        while True:
            # 不获取锁，快速检查是否所有产品都已消费
            with self.mutex._condition:
                if self.consumed_count >= self.total_products:
                    break

            # 更新状态为等待消费
            self.consumer_status[consumer_id] = "等待消费"
            
            self.full.wait()  # 等待满缓冲区
            self.mutex.wait()  # 进入临界区

            # 获取锁，检查是否所有产品都已消费（已消费）
            if self.consumed_count >= self.total_products:
                self.mutex.signal()
                self.empty.signal()  # 避免生产者死锁
                break

            # 更新状态为消费中
            self.consumer_status[consumer_id] = "消费中"
            
            # 消费产品
            product_id = self.buffer.popleft()
            self.consumed_count += 1
            current_stock = len(self.buffer)
            
            # 记录数据
            current_time = time.time() - self.start_time
            self.time_points.append(current_time)
            self.stock_levels.append(current_stock)
            self.consumer_activities[consumer_id].append((current_time, product_id))

            print(f"消费者{consumer_id}(线程{threading.get_ident()}) "
                  f"消费了产品{product_id}, 当前库存量: {current_stock}")

            self.mutex.signal()  # 离开临界区
            self.empty.signal()  # 增加空缓冲区
            time.sleep(0.3)#消费完休眠

            # 更新状态为完成
            self.consumer_status[consumer_id] = "完成"
                        
            # 重置状态为等待
            self.consumer_status[consumer_id] = "等待"

    def update_visualization(self, frame):
        """更新可视化图表"""
        if not self.visualization_running:
            return
        
        # 清空当前图表
        for ax in self.axes:
            ax.clear()
        
        # 获取当前时间
        current_time = time.time() - self.start_time
        
        # 1. 库存水平图表
        if self.time_points and self.stock_levels:
            self.axes[0].plot(self.time_points, self.stock_levels, 'b-', alpha=0.7)
            self.axes[0].axhline(y=self.buffer_size, color='r', linestyle='--', alpha=0.5, label='最大库存')
            self.axes[0].axhline(y=0, color='g', linestyle='--', alpha=0.5, label='空库存')
            if self.time_points:
                self.axes[0].axvline(x=self.time_points[-1], color='gray', linestyle=':', alpha=0.5)
        self.axes[0].set_title('库存水平变化')
        self.axes[0].set_xlabel('时间 (秒)')
        self.axes[0].set_ylabel('库存量')
        self.axes[0].set_ylim(-0.5, self.buffer_size + 0.5)
        self.axes[0].legend()
        self.axes[0].grid(True, alpha=0.3)
        
        # 2. 生产消费统计
        labels = ['已生产', '已消费', '剩余库存']
        values = [self.produced_count, self.consumed_count, len(self.buffer)]
        colors = ['lightblue', 'lightcoral', 'lightgreen']
        bars = self.axes[1].bar(labels, values, color=colors, alpha=0.7)
        self.axes[1].set_title('生产消费统计')
        self.axes[1].set_ylabel('数量')
        
        # 在柱状图上显示数值
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.axes[1].text(bar.get_x() + bar.get_width()/2., height,
                             f'{value}', ha='center', va='bottom')
        
        # 3. 线程状态
        thread_data = []
        thread_labels = []
        thread_colors = []
        
        # 添加生产者状态
        for pid, status in self.producer_status.items():
            thread_labels.append(f'生产者{pid}')
            thread_data.append(1)
            if status == "生产中":
                thread_colors.append('green')
            elif status == "等待生产":
                thread_colors.append('orange')
            elif status == "完成":
                thread_colors.append('blue')
            else:
                thread_colors.append('gray')
        
        # 添加消费者状态
        for cid, status in self.consumer_status.items():
            thread_labels.append(f'消费者{cid}')
            thread_data.append(1)
            if status == "消费中":
                thread_colors.append('red')
            elif status == "等待消费":
                thread_colors.append('orange')
            elif status == "完成":
                thread_colors.append('blue')
            else:
                thread_colors.append('gray')
        
        if thread_data:
            bars = self.axes[2].bar(thread_labels, thread_data, color=thread_colors, alpha=0.7)
            self.axes[2].set_title('线程状态')
            self.axes[2].set_ylabel('状态')
            self.axes[2].set_yticks([])  # 隐藏Y轴刻度
            
            # 添加状态说明
            for bar, label, status in zip(bars, thread_labels, 
                                         list(self.producer_status.values()) + list(self.consumer_status.values())):
                self.axes[2].text(bar.get_x() + bar.get_width()/2., 0.5,
                                 status, ha='center', va='center', rotation=90, fontsize=8)
        
        # 4. 活动时间线
        max_time = max(self.time_points) if self.time_points else 1
        time_range = max(1, max_time)
        
        # 绘制生产者活动
        y_level = 0
        y_labels = []
        
        for pid, activities in self.producer_activities.items():
            if activities:
                times = [a[0] for a in activities]
                self.axes[3].scatter(times, [y_level] * len(times), 
                                   color='blue', marker='o', label=f'生产者{pid}' if pid == 1 else "")
            y_labels.append(f'生产者{pid}')
            y_level += 1
        
        # 绘制消费者活动
        for cid, activities in self.consumer_activities.items():
            if activities:
                times = [a[0] for a in activities]
                self.axes[3].scatter(times, [y_level] * len(times), 
                                   color='red', marker='s', label=f'消费者{cid}' if cid == 1 and y_level == self.num_producers else "")
            y_labels.append(f'消费者{cid}')
            y_level += 1
        
        self.axes[3].set_title('生产消费活动时间线')
        self.axes[3].set_xlabel('时间 (秒)')
        self.axes[3].set_ylabel('线程')
        self.axes[3].set_yticks(range(y_level))
        self.axes[3].set_yticklabels(y_labels)
        if y_level > 0:  # 只有当有线程时才显示图例
            self.axes[3].legend()
        self.axes[3].grid(True, alpha=0.3)
        
        # 调整布局
        plt.tight_layout()
        
        # 检查是否完成
        if self.produced_count >= self.total_products and self.consumed_count >= self.total_products:
            self.visualization_running = False
            print("可视化已完成")

    def setup_visualization(self):
        """设置可视化图表"""
        self.fig, self.axes = plt.subplots(2, 2, figsize=(15, 10))
        self.axes = self.axes.flatten()
        self.fig.suptitle(f'生产者-消费者模型实时监控 (生产者: {self.num_producers}, 消费者: {self.num_consumers})', 
                         fontsize=16, fontweight='bold')
        
        # 创建动画
        self.ani = FuncAnimation(self.fig, self.update_visualization, interval=500, cache_frame_data=False)

    def run(self):
        """运行生产者和消费者线程"""
        print("开始生产者-消费者模拟...")
        print(f"生产者数量: {self.num_producers}, 消费者数量: {self.num_consumers}")
        print(f"总产品数量: {self.total_products}, 库存大小: {self.buffer_size}")
        print("-" * 60)
        
        # 设置可视化
        self.setup_visualization()
        
        # 创建生产者线程
        producers = []
        for i in range(self.num_producers):
            p = threading.Thread(target=self.producer, args=(i + 1,))
            producers.append(p)
            p.daemon = True  # 设置为守护线程，主线程结束时自动结束
            p.start()

        # 创建消费者线程
        consumers = []
        for i in range(self.num_consumers):
            c = threading.Thread(target=self.consumer, args=(i + 1,))
            consumers.append(c)
            c.daemon = True  # 设置为守护线程
            c.start()

        # 显示图表
        plt.show(block=True)  # 阻塞直到图表窗口关闭

        # 等待所有线程完成（如果图表窗口提前关闭）
        for p in producers:
            p.join(timeout=1)

        for c in consumers:
            c.join(timeout=1)

        print("-" * 60)
        print("模拟结束!")
        print(f"总共生产: {self.produced_count} 个产品")
        print(f"总共消费: {self.consumed_count} 个产品")


class ConfigWindow:
    """配置窗口类"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("生产者-消费者模型配置")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 设置默认值
        self.num_producers = tk.IntVar(value=3)
        self.num_consumers = tk.IntVar(value=2)
        self.buffer_size = tk.IntVar(value=10)
        self.total_products = tk.IntVar(value=100)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="生产者-消费者模型配置", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 配置框架
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 生产者数量配置
        ttk.Label(config_frame, text="生产者数量:").grid(row=0, column=0, sticky=tk.W, pady=5)
        producer_spinbox = ttk.Spinbox(config_frame, from_=1, to=10, textvariable=self.num_producers, width=10)
        producer_spinbox.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 消费者数量配置
        ttk.Label(config_frame, text="消费者数量:").grid(row=1, column=0, sticky=tk.W, pady=5)
        consumer_spinbox = ttk.Spinbox(config_frame, from_=1, to=10, textvariable=self.num_consumers, width=10)
        consumer_spinbox.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 缓冲区大小配置
        ttk.Label(config_frame, text="缓冲区大小:").grid(row=2, column=0, sticky=tk.W, pady=5)
        buffer_spinbox = ttk.Spinbox(config_frame, from_=1, to=50, textvariable=self.buffer_size, width=10)
        buffer_spinbox.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 总产品数量配置
        ttk.Label(config_frame, text="总产品数量:").grid(row=3, column=0, sticky=tk.W, pady=5)
        total_spinbox = ttk.Spinbox(config_frame, from_=10, to=1000, textvariable=self.total_products, width=10)
        total_spinbox.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 开始按钮
        start_button = ttk.Button(button_frame, text="开始模拟", command=self.start_simulation)
        start_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 退出按钮
        quit_button = ttk.Button(button_frame, text="退出", command=self.root.quit)
        quit_button.pack(side=tk.RIGHT)
        
        # 默认值说明
        default_label = ttk.Label(main_frame, text="默认值: 3个生产者, 2个消费者, 缓冲区大小10, 总产品100", 
                                 font=("Arial", 9), foreground="gray")
        default_label.pack(side=tk.BOTTOM, pady=(10, 0))
    
    def start_simulation(self):
        """开始模拟"""
        # 获取配置值
        num_producers = self.num_producers.get()
        num_consumers = self.num_consumers.get()
        buffer_size = self.buffer_size.get()
        total_products = self.total_products.get()
        
        # 验证输入
        if num_producers < 1 or num_consumers < 1 or buffer_size < 1 or total_products < 10:
            tk.messagebox.showerror("错误", "请输入有效的参数值！")
            return
        
        # 关闭配置窗口
        self.root.destroy()
        
        # 创建并运行生产者-消费者模型
        pc = ProducerConsumer(num_producers, num_consumers, buffer_size, total_products)
        pc.run()
    
    def run(self):
        """运行配置窗口"""
        self.root.mainloop()


def main():
    # 显示配置窗口
    config_window = ConfigWindow()
    config_window.run()


if __name__ == "__main__":
    import tkinter.messagebox
    main()