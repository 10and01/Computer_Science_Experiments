import os
import signal
import time
import sys
import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
from multiprocessing import Process, Pipe, Queue, Value, Array, Lock, Event, Manager
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import rcParams
from collections import deque
import random
from typing import Dict, Callable, Any

# 设置matplotlib中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# 模块级信号处理函数
def custom_signal_handler(signum, frame):
    """全局信号处理函数"""
    signals = {
        10: 'SIGUSR1',
        12: 'SIGUSR2',
        15: 'SIGTERM'
    }
    return f"进程 {os.getpid()} 收到模拟信号: {signals.get(signum, signum)}"


def child_signal_handler(signum, frame):
    """子进程信号处理函数"""
    signals = {
        10: 'SIGUSR1',
        12: 'SIGUSR2'
    }
    return f"子进程 {os.getpid()} 收到信号: {signals.get(signum, signum)}"


def child_signal_process(output_queue, signal_bus, child_ready):
    """独立的子进程函数"""
    try:
        child_sim = WindowsSignalSimulator()
        child_sim.signal_bus = signal_bus
        child_sim.signal(child_sim.SIGUSR1, child_signal_handler)
        child_sim.signal(child_sim.SIGUSR2, child_signal_handler)

        output_queue.put(f"子进程 {os.getpid()} 已启动，等待信号...")
        child_ready.set()

        start_time = time.time()
        signal_count = 0
        max_wait_time = 10

        while time.time() - start_time < max_wait_time:
            if not signal_bus.empty():
                try:
                    signal_data = signal_bus.get_nowait()
                    target_pid = signal_data.get('target_pid')
                    signum = signal_data.get('signum')
                    sender_pid = signal_data.get('sender_pid')

                    if target_pid == os.getpid():
                        if signum in [child_sim.SIGUSR1, child_sim.SIGUSR2]:
                            signal_count += 1
                            result = child_signal_handler(signum, None)
                            output_queue.put(f"{result} (来自进程 {sender_pid})")
                            if signal_count >= 2:
                                break
                        elif signum == child_sim.SIGTERM:
                            output_queue.put(f"子进程 {os.getpid()} 收到终止信号")
                            break
                except Exception as e:
                    output_queue.put(f"子进程信号处理错误: {e}")

            time.sleep(0.1)

        output_queue.put(f"子进程完成，收到 {signal_count} 个信号")

    except Exception as e:
        output_queue.put(f"子进程错误: {e}")


class WindowsSignalSimulator:
    """Windows信号通信模拟器"""

    def __init__(self):
        self.signal_handlers: Dict[int, Callable] = {}
        self.signal_bus = None
        self.SIGUSR1 = 10
        self.SIGUSR2 = 12
        self.SIGTERM = 15

    def signal(self, signum: int, handler: Callable):
        """注册信号处理程序"""
        self.signal_handlers[signum] = handler

    def kill(self, pid: int, signum: int):
        """向指定进程发送信号"""
        if self.signal_bus:
            signal_data = {
                'target_pid': pid,
                'signum': signum,
                'sender_pid': os.getpid(),
                'timestamp': time.time()
            }
            self.signal_bus.put(signal_data)


def windows_signal_communication(output_queue, visual_callback):
    """Windows兼容的信号通信演示"""
    output_queue.put("\n=== Windows信号通信模拟 ===")
    visual_callback('signal', {'type': 'start'})

    with Manager() as manager:
        signal_bus = manager.Queue()
        child_ready = manager.Event()

        parent_sim = WindowsSignalSimulator()
        parent_sim.signal_bus = signal_bus
        parent_sim.signal(parent_sim.SIGUSR1, custom_signal_handler)
        parent_sim.signal(parent_sim.SIGUSR2, custom_signal_handler)
        parent_sim.signal(parent_sim.SIGTERM, custom_signal_handler)

        output_queue.put(f"父进程 {os.getpid()} 已启动")
        visual_callback('signal', {'type': 'handler_started'})

        child_proc = Process(target=child_signal_process,
                             args=(output_queue, signal_bus, child_ready))
        child_proc.start()

        if child_ready.wait(timeout=5):
            child_pid = child_proc.pid
            output_queue.put(f"子进程就绪: PID {child_pid}")

            output_queue.put(f"父进程 {os.getpid()} 向子进程 {child_pid} 发送 SIGUSR1")
            parent_sim.kill(child_pid, parent_sim.SIGUSR1)
            visual_callback('signal', {'type': 'signal_sent', 'signal': 'SIGUSR1'})

            time.sleep(1)

            output_queue.put("父进程等待子进程响应...")
            visual_callback('signal', {'type': 'waiting_response'})

            output_queue.put(f"父进程 {os.getpid()} 向子进程 {child_pid} 发送 SIGUSR2")
            parent_sim.kill(child_pid, parent_sim.SIGUSR2)
            visual_callback('signal', {'type': 'second_signal_sent', 'signal': 'SIGUSR2'})

            child_proc.join(timeout=5)

            if child_proc.is_alive():
                output_queue.put("子进程未正常终止，尝试优雅终止")
                parent_sim.kill(child_pid, parent_sim.SIGTERM)
                time.sleep(1)

                if child_proc.is_alive():
                    output_queue.put("强制终止子进程")
                    child_proc.terminate()
                    child_proc.join(timeout=1)
            else:
                output_queue.put("子进程正常完成")
        else:
            output_queue.put("子进程启动超时")

    visual_callback('signal', {'type': 'completed'})
    output_queue.put("Windows信号通信模拟完成!")


# 其他IPC方法的模块级函数定义
def signal_handler(signum, frame):
    signals = {
        signal.SIGUSR1: 'SIGUSR1',
        signal.SIGUSR2: 'SIGUSR2'
    }
    return f"进程 {os.getpid()} 收到信号: {signals.get(signum, signum)}"


def child_process_pipe(conn, process_id, output_queue):
    """管道通信子进程"""
    message = conn.recv()
    output_queue.put(f"子进程{process_id}收到: {message}")
    response = f"子进程{process_id}响应: {message.upper()}"
    conn.send(response)
    conn.close()


def producer_process(queue, items, producer_id, output_queue):
    """生产者进程"""
    for msg in items:
        full_msg = f"生产者{producer_id}: {msg}"
        output_queue.put(f"发送: {full_msg}")
        queue.put(full_msg)
        time.sleep(0.3)
    queue.put("END")


def consumer_process(queue, consumer_id, output_queue):
    """消费者进程"""
    while True:
        message = queue.get()
        if message == "END":
            output_queue.put(f"消费者{consumer_id}: 完成")
            break
        output_queue.put(f"消费者{consumer_id}收到: {message}")
        time.sleep(0.3)


def writer_process_shared(shared_value, shared_array, lock, process_id, output_queue):
    """共享内存写入进程"""
    for i in range(3):
        with lock:
            shared_value.value += process_id
            output_queue.put(f"写入进程{process_id}设置值: {shared_value.value}")
            for j in range(len(shared_array)):
                shared_array[j] = process_id * 10 + j + i
            output_queue.put(f"写入进程{process_id}设置数组: {list(shared_array)}")
        time.sleep(0.4)


def reader_process_shared(shared_value, shared_array, lock, process_id, output_queue):
    """共享内存读取进程"""
    for i in range(3):
        with lock:
            current_value = shared_value.value
            output_queue.put(f"读取进程{process_id}读取值: {current_value}")
            array_data = list(shared_array)
            output_queue.put(f"读取进程{process_id}读取数组: {array_data}")
        time.sleep(0.5)


def socket_server_process(output_queue, visual_queue):
    """套接字服务器进程"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 9999))
    server_socket.listen(1)
    output_queue.put("服务器启动，等待连接...")
    visual_queue.put({'type': 'server_start', 'status': '等待连接'})

    client_socket, addr = server_socket.accept()
    output_queue.put(f"客户端 {addr} 已连接")
    visual_queue.put({'type': 'client_connected', 'addr': str(addr)})

    for i in range(3):
        data = client_socket.recv(1024).decode()
        output_queue.put(f"服务器收到: {data}")
        visual_queue.put({'type': 'message_received', 'from': 'client', 'content': data, 'seq': i + 1})

        response = f"服务器响应消息 {i + 1}"
        client_socket.send(response.encode())
        output_queue.put(f"服务器发送: {response}")
        visual_queue.put({'type': 'message_sent', 'from': 'server', 'content': response, 'seq': i + 1})
        time.sleep(0.3)

    client_socket.close()
    server_socket.close()
    visual_queue.put({'type': 'connection_closed'})


def socket_client_process(output_queue, visual_queue):
    """套接字客户端进程"""
    time.sleep(1)  # 等待服务器启动
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(('localhost', 9999))
        visual_queue.put({'type': 'connected', 'status': '已连接'})
    except Exception as e:
        output_queue.put(f"连接失败: {e}")
        return

    for i in range(3):
        message = f"客户端消息 {i + 1}"
        client_socket.send(message.encode())
        output_queue.put(f"客户端发送: {message}")
        visual_queue.put({'type': 'message_sent', 'from': 'client', 'content': message, 'seq': i + 1})

        response = client_socket.recv(1024).decode()
        output_queue.put(f"客户端收到: {response}")
        visual_queue.put({'type': 'message_received', 'from': 'server', 'content': response, 'seq': i + 1})
        time.sleep(0.5)

    client_socket.close()
    visual_queue.put({'type': 'connection_closed'})


def semaphore_producer_process(semaphore, buffer, buffer_lock, producer_id, output_queue, max_items=5):
    """信号量生产者进程"""
    try:
        for i in range(max_items):
            item = f"产品_{producer_id}_{i + 1}"
            time.sleep(0.5)  # 模拟生产时间

            # 获取信号量（等待空位）
            semaphore.acquire()

            with buffer_lock:
                buffer.append(item)
                current_size = len(buffer)

            output_queue.put(f"生产者{producer_id} 生产: {item} (缓冲区大小: {current_size})")

        output_queue.put(f"生产者{producer_id} 完成生产")

    except Exception as e:
        output_queue.put(f"生产者{producer_id} 错误: {e}")


def semaphore_consumer_process(semaphore, buffer, buffer_lock, consumer_id, output_queue, max_items=3):
    """信号量消费者进程"""
    try:
        items_consumed = 0
        while items_consumed < max_items:
            time.sleep(0.7)  # 模拟消费时间

            item = None
            with buffer_lock:
                if buffer:
                    item = buffer.pop(0)
                    items_consumed += 1
                    # 释放信号量（通知有空位）
                    semaphore.release()

            if item:
                with buffer_lock:
                    current_size = len(buffer)
                output_queue.put(f"消费者{consumer_id} 消费: {item} (缓冲区大小: {current_size})")
            else:
                # 如果缓冲区为空，等待一会儿再检查
                time.sleep(0.1)

        output_queue.put(f"消费者{consumer_id} 完成消费")

    except Exception as e:
        output_queue.put(f"消费者{consumer_id} 错误: {e}")

class Visualizer:
    """数据可视化组件"""

    def __init__(self, parent):
        self.parent = parent
        self.figures = {}
        self.canvases = {}
        self.data_queues = {}
        self.current_data = {}  # 存储当前演示的数据

    def create_signal_visualization(self, frame):
        """创建信号通信可视化 - 优化版本"""
        fig = plt.Figure(figsize=(8, 4), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('信号通信时序图', size=14, fontweight='bold')
        ax.set_xlabel('时间轴 (秒)', size=12)
        ax.set_ylabel('进程/信号', size=12)
        ax.set_ylim(0, 4)
        ax.set_xlim(0, 10)
        ax.grid(True, alpha=0.3)
        ax.set_yticks([1, 2, 3])
        ax.set_yticklabels(['父进程', '信号传输', '子进程'], size=10)

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['signal'] = fig
        self.canvases['signal'] = canvas
        self.data_queues['signal'] = deque(maxlen=50)
        self.current_data['signal'] = {
            'events': [],
            'start_time': time.time(),
            'parent_events': [],
            'child_events': []
        }

        return fig, canvas

    def create_pipe_visualization(self, frame):
        """创建管道可视化"""
        fig = plt.Figure(figsize=(6, 3), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('管道通信数据流', size=12)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 3)
        ax.set_xlabel('时间轴')
        ax.set_ylabel('进程')

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['pipe'] = fig
        self.canvases['pipe'] = canvas
        self.data_queues['pipe'] = deque(maxlen=20)
        self.current_data['pipe'] = {'messages': []}

        return fig, canvas

    def create_queue_visualization(self, frame):
        """创建队列可视化"""
        fig = plt.Figure(figsize=(6, 3), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('消息队列状态', size=12)
        ax.set_xlabel('时间')
        ax.set_ylabel('队列长度')

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['queue'] = fig
        self.canvases['queue'] = canvas
        self.data_queues['queue'] = deque(maxlen=20)
        self.current_data['queue'] = {'queue_lengths': []}

        return fig, canvas

    def create_shared_memory_visualization(self, frame):
        """创建共享内存可视化"""
        fig = plt.Figure(figsize=(6, 3), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('共享内存状态', size=12)
        ax.set_xlabel('数组索引')
        ax.set_ylabel('数值')

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['shared_memory'] = fig
        self.canvases['shared_memory'] = canvas
        self.data_queues['shared_memory'] = deque(maxlen=20)
        self.current_data['shared_memory'] = {'values': [0] * 5}

        return fig, canvas

    def create_socket_visualization(self, frame):
        """创建套接字通信可视化 - 优化版本"""
        fig = plt.Figure(figsize=(8, 5), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('套接字通信时序图', size=14, fontweight='bold')
        ax.set_xlabel('时间轴 (秒)', size=12)
        ax.set_ylabel('通信节点', size=12)
        ax.set_ylim(0, 5)
        ax.set_xlim(0, 10)
        ax.grid(True, alpha=0.3)
        ax.set_yticks([1, 2, 3, 4])
        ax.set_yticklabels(['客户端', '连接建立', '数据传输', '服务器'], size=10)

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['socket'] = fig
        self.canvases['socket'] = canvas
        self.data_queues['socket'] = deque(maxlen=50)
        self.current_data['socket'] = {
            'events': [],
            'start_time': time.time(),
            'connections': [],
            'messages': []
        }

        return fig, canvas

    def create_semaphore_visualization(self, frame):
        """创建信号量通信可视化"""
        fig = plt.Figure(figsize=(8, 5), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('信号量通信演示 - 生产者消费者模型', size=14, fontweight='bold')
        ax.set_xlabel('时间轴', size=12)
        ax.set_ylabel('进程状态', size=12)
        ax.set_ylim(0, 6)
        ax.set_xlim(0, 10)
        ax.grid(True, alpha=0.3)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(['生产者1', '生产者2', '缓冲区', '消费者1', '消费者2'], size=10)

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.figures['semaphore'] = fig
        self.canvases['semaphore'] = canvas
        self.data_queues['semaphore'] = deque(maxlen=50)
        self.current_data['semaphore'] = {
            'events': [],
            'start_time': time.time(),
            'producer1_events': [],
            'producer2_events': [],
            'consumer1_events': [],
            'consumer2_events': [],
            'buffer_size': 0,
            'semaphore_value': 3
        }

        return fig, canvas

    def clear_visualization(self, method):
        """清空指定方法的可视化数据"""
        if method in self.data_queues:
            self.data_queues[method].clear()
        if method in self.current_data:
            # 重置当前数据
            if method == 'signal':
                self.current_data[method] = {
                    'events': [],
                    'start_time': time.time(),
                    'parent_events': [],
                    'child_events': []
                }
            elif method == 'pipe':
                self.current_data[method] = {'messages': []}
            elif method == 'queue':
                self.current_data[method] = {'queue_lengths': []}
            elif method == 'shared_memory':
                self.current_data[method] = {'values': [0] * 5}
            elif method == 'socket':
                self.current_data[method] = {
                    'events': [],
                    'start_time': time.time(),
                    'connections': [],
                    'messages': []
                }
            elif method == 'semaphore':
                self.current_data[method] = {
                    'events': [],
                    'start_time': time.time(),
                    'producer1_events': [],
                    'producer2_events': [],
                    'consumer1_events': [],
                    'consumer2_events': [],
                    'buffer_size': 0,
                    'semaphore_value': 3
                }

        # 重绘空图表
        self.redraw(method)

    def update_visualization(self, method, data):
        """更新可视化数据"""
        if method in self.data_queues:
            self.data_queues[method].append(data)
            self.redraw(method)

    def redraw(self, method):
        """重绘图表 - 修复字体重叠问题"""
        if method not in self.figures:
            return

        fig = self.figures[method]
        ax = fig.axes[0]
        ax.clear()

        if method == 'signal':
            # 优化信号通信可视化
            ax.set_title('信号通信时序图', size=14, fontweight='bold')
            ax.set_xlabel('时间轴 (秒)', size=12)
            ax.set_ylabel('进程/信号', size=12)
            ax.set_ylim(0, 4)
            ax.set_xlim(0, 10)
            ax.grid(True, alpha=0.3)
            ax.set_yticks([1, 2, 3])
            ax.set_yticklabels(['父进程', '信号传输', '子进程'], size=10)

            # 绘制进程线
            ax.axhline(y=1, color='blue', linestyle='-', alpha=0.5, label='父进程')
            ax.axhline(y=3, color='green', linestyle='-', alpha=0.5, label='子进程')

            # 处理事件数据
            events = self.current_data['signal']['events']
            current_time = time.time() - self.current_data['signal']['start_time']

            # 绘制事件点
            for event in events:
                event_time = event['time']
                event_type = event['type']
                signal_name = event.get('signal', '')

                if event_type == 'signal_sent':
                    # 父进程发送信号
                    ax.scatter(event_time, 1, color='red', s=100, zorder=5)
                    # 修复文本重叠：调整文本位置
                    ax.annotate(f'发送{signal_name}', (event_time, 1.1),
                                xytext=(event_time, 1.3), ha='center', fontsize=8,
                                arrowprops=dict(arrowstyle='->', color='red', lw=1))
                    # 绘制信号传输线
                    ax.plot([event_time, event_time], [1, 3], 'r--', alpha=0.7)

                elif event_type == 'signal_received':
                    # 子进程接收信号
                    ax.scatter(event_time, 3, color='green', s=100, zorder=5)
                    # 修复文本重叠：调整文本位置
                    ax.annotate(f'接收{signal_name}', (event_time, 3),
                                xytext=(event_time, 2.7), ha='center', fontsize=8,
                                arrowprops=dict(arrowstyle='->', color='green', lw=1))

            # 添加图例
            ax.legend(loc='upper right', fontsize=9)

            # 添加时间线
            ax.axvline(x=current_time, color='orange', linestyle=':', alpha=0.7)
            ax.text(current_time, 3.5, f'当前时间: {current_time:.1f}s',
                    ha='center', fontsize=9, bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

        elif method == 'pipe':
            ax.set_title('管道通信数据流', size=12)
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 3)
            ax.set_xlabel('时间轴')
            ax.set_ylabel('进程')
            if self.data_queues[method]:
                x = range(len(self.data_queues[method]))
                y = [random.uniform(0.5, 2.5) for _ in x]
                ax.plot(x, y, 'bo-', alpha=0.7)
                ax.scatter(x, y, c='red', s=50, alpha=0.8)

        elif method == 'queue':
            ax.set_title('消息队列状态', size=12)
            ax.set_xlabel('时间')
            ax.set_ylabel('队列长度')
            if self.data_queues[method]:
                x = range(len(self.data_queues[method]))
                y = [random.randint(1, 10) for _ in x]
                bars = ax.bar(x, y, alpha=0.7, color='skyblue')
                for i, v in enumerate(y):
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(i, v + 0.1, str(v), ha='center', fontsize=8)

        elif method == 'shared_memory':
            ax.set_title('共享内存状态', size=12)
            ax.set_xlabel('数组索引')
            ax.set_ylabel('数值')
            indices = list(range(5))
            values = [random.randint(1, 100) for _ in indices]
            bars = ax.bar(indices, values, alpha=0.7, color='lightgreen')
            for i, v in enumerate(values):
                # 修复文本重叠：调整文本位置和字体大小
                ax.text(i, v + 1, str(v), ha='center', fontsize=8)

        elif method == 'socket':
            # 套接字通信可视化 - 优化版本，修复字体重叠
            ax.set_title('套接字通信时序图', size=14, fontweight='bold')
            ax.set_xlabel('时间轴 (秒)', size=12)
            ax.set_ylabel('通信节点', size=12)
            ax.set_ylim(0, 5)
            ax.set_xlim(0, 10)
            ax.grid(True, alpha=0.3)
            ax.set_yticks([1, 2, 3, 4])
            ax.set_yticklabels(['客户端', '连接建立', '数据传输', '服务器'], size=10)

            # 绘制节点线
            ax.axhline(y=1, color='blue', linestyle='-', alpha=0.5, label='客户端')
            ax.axhline(y=4, color='green', linestyle='-', alpha=0.5, label='服务器')
            ax.axhline(y=2.5, color='red', linestyle='--', alpha=0.3, label='连接')

            # 处理事件数据
            events = self.current_data['socket']['events']
            current_time = time.time() - self.current_data['socket']['start_time']

            # 绘制事件
            for event in events:
                event_time = event['time']
                event_type = event['type']

                if event_type == 'server_start':
                    ax.scatter(event_time, 4, color='green', s=100, zorder=5)
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(event_time, 4.2, '服务器启动', ha='center', fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

                elif event_type == 'client_connected':
                    ax.scatter(event_time, 1, color='blue', s=100, zorder=5)
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(event_time, 0.8, '客户端连接', ha='center', fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
                    # 绘制连接线
                    ax.plot([event_time, event_time], [1, 4], 'r-', alpha=0.7)
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(event_time, 2.5, '连接建立', ha='center', fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))

                elif event_type == 'message_sent':
                    from_node = event['from']
                    seq = event.get('seq', 1)
                    y_start = 1 if from_node == 'client' else 4
                    y_end = 4 if from_node == 'client' else 1
                    color = 'orange' if from_node == 'client' else 'purple'

                    # 绘制消息箭头
                    ax.annotate('', xy=(event_time, y_end), xytext=(event_time, y_start),
                                arrowprops=dict(arrowstyle='->', color=color, lw=2))

                    # 添加消息标签 - 修复文本重叠：调整文本位置和字体大小
                    label_y = (y_start + y_end) / 2
                    direction = '→' if from_node == 'client' else '←'
                    ax.text(event_time, label_y, f'消息{seq}{direction}',
                            ha='center', va='center', fontsize=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

                elif event_type == 'message_received':
                    from_node = event['from']
                    seq = event.get('seq', 1)
                    y_pos = 1 if from_node == 'server' else 4
                    color = 'lightgreen' if from_node == 'server' else 'lightblue'

                    ax.scatter(event_time, y_pos, color=color, s=80, zorder=5, marker='s')
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(event_time, y_pos - 0.3, f'接收{seq}',
                            ha='center', fontsize=7, color=color,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

                elif event_type == 'connection_closed':
                    ax.scatter(event_time, 2.5, color='red', s=100, zorder=5, marker='x')
                    # 修复文本重叠：调整文本位置和字体大小
                    ax.text(event_time, 2.2, '连接关闭', ha='center', fontsize=8, color='red',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

            # 添加图例 - 修复文本重叠：调整图例位置和字体大小
            ax.legend(loc='upper right', fontsize=9)

            # 添加时间线
            ax.axvline(x=current_time, color='orange', linestyle=':', alpha=0.7)
            ax.text(current_time, 4.5, f'当前时间: {current_time:.1f}s',
                    ha='center', fontsize=9, bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        elif method == 'semaphore':
            # 信号量通信可视化
            ax.set_title('信号量通信演示 - 生产者消费者模型', size=14, fontweight='bold')
            ax.set_xlabel('时间轴', size=12)
            ax.set_ylabel('进程状态', size=12)
            ax.set_ylim(0, 6)
            ax.set_xlim(0, 10)
            ax.grid(True, alpha=0.3)
            ax.set_yticks([1, 2, 3, 4, 5])
            ax.set_yticklabels(['生产者1', '生产者2', '缓冲区', '消费者1', '消费者2'], size=10)

            # 绘制进程线
            ax.axhline(y=1, color='blue', linestyle='-', alpha=0.5, label='生产者1')
            ax.axhline(y=2, color='lightblue', linestyle='-', alpha=0.5, label='生产者2')
            ax.axhline(y=3, color='green', linestyle='-', alpha=0.5, label='缓冲区')
            ax.axhline(y=4, color='orange', linestyle='-', alpha=0.5, label='消费者1')
            ax.axhline(y=5, color='red', linestyle='-', alpha=0.5, label='消费者2')

            # 处理事件数据
            events = self.current_data['semaphore']['events']
            current_time = time.time() - self.current_data['semaphore']['start_time']
            buffer_size = self.current_data['semaphore'].get('buffer_size', 0)

            # 绘制缓冲区状态
            ax.barh(3, buffer_size / 3, height=0.3, color='lightgreen', alpha=0.7)
            ax.text(5, 3, f'缓冲区: {buffer_size}/3', ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

            # 处理事件数据
            events = self.current_data['semaphore']['events']
            current_time = time.time() - self.current_data['semaphore']['start_time']
            buffer_size = self.current_data['semaphore'].get('buffer_size', 0)

            # 绘制缓冲区状态
            if buffer_size > 0:
                ax.barh(3, min(buffer_size / 3, 1.0), height=0.3, color='lightgreen', alpha=0.7)
            ax.text(5, 3, f'缓冲区: {buffer_size}/3', ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

            # 绘制事件
            for event in events:
                event_time = event.get('time', 0)
                event_type = event.get('type', '')
                process_id = event.get('process_id', 0)

                if event_type == 'item_produced':
                    y_pos = 1 if process_id == 1 else 2
                    color = 'blue' if process_id == 1 else 'lightblue'
                    if event_time <= 10:  # 只绘制在时间轴范围内的点
                        ax.scatter(event_time, y_pos, color=color, s=100, zorder=5)
                        ax.annotate('生产', (event_time, y_pos), xytext=(event_time, y_pos + 0.2),
                                    ha='center', fontsize=8, arrowprops=dict(arrowstyle='->', color=color))

                elif event_type == 'item_consumed':
                    y_pos = 4 if process_id == 1 else 5
                    color = 'orange' if process_id == 1 else 'red'
                    if event_time <= 10:  # 只绘制在时间轴范围内的点
                        ax.scatter(event_time, y_pos, color=color, s=100, zorder=5)
                        ax.annotate('消费', (event_time, y_pos), xytext=(event_time, y_pos - 0.2),
                                    ha='center', fontsize=8, arrowprops=dict(arrowstyle='->', color=color))

            # 添加图例
            ax.legend(loc='upper right', fontsize=9)

            # 添加时间线
            ax.axvline(x=current_time, color='purple', linestyle=':', alpha=0.7)
            ax.text(current_time, 5.5, f'当前时间: {current_time:.1f}s', ha='center', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

        try:
            self.canvases[method].draw()
        except Exception as e:
            print(f"绘图错误: {e}")



    def add_signal_event(self, event_type, signal_name=''):
        """添加信号事件到时序图"""
        if 'signal' in self.current_data:
            event_time = time.time() - self.current_data['signal']['start_time']
            event = {
                'time': event_time,
                'type': event_type,
                'signal': signal_name
            }
            self.current_data['signal']['events'].append(event)
            self.redraw('signal')

    def add_socket_event(self, event_data):
        """添加套接字事件到时序图"""
        if 'socket' in self.current_data:
            event_time = time.time() - self.current_data['socket']['start_time']
            event_data['time'] = event_time
            self.current_data['socket']['events'].append(event_data)
            self.redraw('socket')


class IPCManager:
    """进程间通信管理器"""

    def __init__(self, output_callback=None, visual_callback=None):
        self.methods = {
            'signal': '信号通信',
            'pipe': '管道通信',
            'queue': '消息队列',
            'shared_memory': '共享内存',
            'socket': '套接字通信',
            'semaphore': '信号量通信'
        }
        self.output_callback = output_callback
        self.visual_callback = visual_callback
        self.is_running = False
        self.current_method = None
        # 新增：跟踪每个方法的状态
        self.method_status = {
            'signal': 'waiting',
            'pipe': 'waiting',
            'queue': 'waiting',
            'shared_memory': 'waiting',
            'socket': 'waiting',
            'semaphore': 'waiting'
        }
        self.visualizer = None  # 确保这个属性存在

    def set_visualizer(self, visualizer):
        """设置可视化器"""
        self.visualizer = visualizer

    def log(self, message):
        if self.output_callback:
            self.output_callback(message)

    def visual_update(self, method, data):
        if self.visual_callback:
            self.visual_callback(method, data)

        # 添加信号事件到时序图
        if method == 'signal' and self.visualizer:
            event_type = data.get('type')
            if event_type == 'signal_sent':
                signal_name = data.get('signal', '')
                self.visualizer.add_signal_event('signal_sent', signal_name)
            elif event_type == 'signal_received':
                signal_name = data.get('signal', '')
                self.visualizer.add_signal_event('signal_received', signal_name)

        # 添加套接字事件到时序图
        elif method == 'socket' and self.visualizer and hasattr(self.visualizer, 'add_socket_event'):
            self.visualizer.add_socket_event(data)

        # 修复信号量通信部分 - 通过 visualizer 访问 current_data
        elif method == 'semaphore' and self.visualizer:
            if 'type' in data:
                event_type = data['type']
                # 通过 visualizer 访问 current_data
                if method in self.visualizer.current_data:
                    current_time = time.time() - self.visualizer.current_data[method]['start_time']

                    if event_type == 'item_produced':
                        self.visualizer.current_data[method]['events'].append({
                            'time': current_time,
                            'type': 'item_produced',
                            'process_id': data.get('process_id', 0)
                        })
                    elif event_type == 'item_consumed':
                        self.visualizer.current_data[method]['events'].append({
                            'time': current_time,
                            'type': 'item_consumed',
                            'process_id': data.get('process_id', 0)
                        })
                    elif event_type == 'buffer_update':
                        self.visualizer.current_data[method]['buffer_size'] = data.get('size', 0)

                    # 重绘图表
                    self.visualizer.redraw(method)

    def signal_communication(self):
        """信号通信演示"""
        self.current_method = 'signal'
        self.method_status['signal'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('signal')

        self.log("\n=== 信号通信示例 ===")
        self.visual_update('signal', {'type': 'start'})

        if os.name == 'nt':
            output_queue = Queue()

            def queue_reader():
                start_time = time.time()
                max_read_time = 20
                messages_received = 0
                signal_completed = False

                while time.time() - start_time < max_read_time and not signal_completed:
                    try:
                        if not output_queue.empty():
                            message = output_queue.get_nowait()
                            self.log(message)
                            messages_received += 1

                            if "收到信号" in message:
                                self.visual_update('signal', {'type': 'signal_received', 'content': message})
                            elif "发送" in message:
                                self.visual_update('signal', {'type': 'signal_sent', 'content': message})
                            elif "完成" in message or "Windows信号通信模拟完成" in message:
                                signal_completed = True
                                self.method_status['signal'] = 'completed'
                                self.visual_update('signal', {'type': 'completed'})

                            if messages_received > 10:
                                break
                    except:
                        pass
                    time.sleep(0.1)

                # 确保最终状态更新
                if not signal_completed:
                    self.method_status['signal'] = 'completed'
                    self.visual_update('signal', {'type': 'completed'})

            reader_thread = threading.Thread(target=queue_reader)
            reader_thread.daemon = True
            reader_thread.start()

            def run_windows_signal():
                try:
                    windows_signal_communication(output_queue, self.visual_update)
                except Exception as e:
                    self.log(f"Windows信号通信错误: {e}")
                finally:
                    # 确保发送完成状态
                    self.method_status['signal'] = 'completed'
                    self.visual_update('signal', {'type': 'completed'})

            signal_thread = threading.Thread(target=run_windows_signal)
            signal_thread.daemon = True
            signal_thread.start()
            signal_thread.join(timeout=15)

            # 确保状态正确更新
            if self.method_status['signal'] != 'completed':
                self.method_status['signal'] = 'completed'
                self.visual_update('signal', {'type': 'completed'})
        else:
            # Unix系统实现
            pass

        # 最终确认状态更新
        self.method_status['signal'] = 'completed'
        self.visual_update('signal', {'type': 'completed'})

    def pipe_communication(self):
        """管道通信演示"""
        self.current_method = 'pipe'
        self.method_status['pipe'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('pipe')

        self.log("\n=== 管道通信示例 ===")
        self.visual_update('pipe', {'type': 'start'})

        try:
            output_queue = Queue()
            processes = []

            for i in range(2):
                parent_conn, child_conn = Pipe()
                p = Process(target=child_process_pipe, args=(child_conn, i + 1, output_queue))
                processes.append((p, parent_conn))
                p.start()
                self.visual_update('pipe', {'type': 'process_started', 'id': i + 1})

            for i, (p, conn) in enumerate(processes):
                message = f"向子进程 {i + 1} 问好"
                conn.send(message)
                self.log(f"父进程发送: {message}")
                self.visual_update('pipe', {'type': 'message_sent', 'content': message})

                response = conn.recv()
                self.log(f"父进程收到: {response}")
                self.visual_update('pipe', {'type': 'message_received', 'content': response})

                p.join(timeout=5)
                conn.close()

            self.method_status['pipe'] = 'completed'
            self.visual_update('pipe', {'type': 'completed'})
            self.log("管道通信完成!")
        except Exception as e:
            self.log(f"管道通信错误: {e}")
            self.method_status['pipe'] = 'error'
            self.visual_update('pipe', {'type': 'error'})

    def queue_communication(self):
        """消息队列通信演示"""
        self.current_method = 'queue'
        self.method_status['queue'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('queue')

        self.log("\n=== 消息队列通信示例 ===")
        self.visual_update('queue', {'type': 'start'})

        try:
            message_queue = Queue()
            output_queue = Queue()

            messages = [f"消息 {i + 1}" for i in range(3)]

            producer_proc = Process(target=producer_process,
                                    args=(message_queue, messages, 1, output_queue))
            consumer_proc = Process(target=consumer_process,
                                    args=(message_queue, 1, output_queue))

            producer_proc.start()
            consumer_proc.start()
            self.visual_update('queue', {'type': 'processes_started'})

            start_time = time.time()
            while time.time() - start_time < 10:
                while not output_queue.empty():
                    msg = output_queue.get_nowait()
                    self.log(msg)
                    self.visual_update('queue', {'type': 'message_flow'})
                time.sleep(0.1)

            producer_proc.join(timeout=2)
            consumer_proc.join(timeout=2)

            self.method_status['queue'] = 'completed'
            self.visual_update('queue', {'type': 'completed'})
            self.log("消息队列通信完成!")
        except Exception as e:
            self.log(f"消息队列通信错误: {e}")
            self.method_status['queue'] = 'error'
            self.visual_update('queue', {'type': 'error'})

    def shared_memory_communication(self):
        """共享内存通信演示"""
        self.current_method = 'shared_memory'
        self.method_status['shared_memory'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('shared_memory')

        self.log("\n=== 共享内存通信示例 ===")
        self.visual_update('shared_memory', {'type': 'start'})

        try:
            shared_value = Value('i', 0)
            shared_array = Array('i', 5)
            lock = Lock()
            output_queue = Queue()

            writer1 = Process(target=writer_process_shared,
                              args=(shared_value, shared_array, lock, 1, output_queue))
            writer2 = Process(target=writer_process_shared,
                              args=(shared_value, shared_array, lock, 2, output_queue))
            reader = Process(target=reader_process_shared,
                             args=(shared_value, shared_array, lock, 1, output_queue))

            writer1.start()
            writer2.start()
            reader.start()

            self.visual_update('shared_memory', {'type': 'processes_started'})

            start_time = time.time()
            while time.time() - start_time < 10:
                while not output_queue.empty():
                    msg = output_queue.get_nowait()
                    self.log(msg)
                    self.visual_update('shared_memory', {'type': 'memory_update'})
                time.sleep(0.1)

            writer1.join(timeout=2)
            writer2.join(timeout=2)
            reader.join(timeout=2)

            self.method_status['shared_memory'] = 'completed'
            self.visual_update('shared_memory', {'type': 'completed'})
            self.log("共享内存通信完成!")
        except Exception as e:
            self.log(f"共享内存通信错误: {e}")
            self.method_status['shared_memory'] = 'error'
            self.visual_update('shared_memory', {'type': 'error'})

    def socket_communication(self):
        """套接字通信演示"""
        self.current_method = 'socket'
        self.method_status['socket'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('socket')

        self.log("\n=== 套接字通信示例 ===")
        self.visual_update('socket', {'type': 'start'})

        try:
            output_queue = Queue()
            visual_queue = Queue()  # 专门用于可视化数据的队列

            server_process = Process(target=socket_server_process, args=(output_queue, visual_queue))
            client_process = Process(target=socket_client_process, args=(output_queue, visual_queue))

            server_process.start()
            client_process.start()
            self.visual_update('socket', {'type': 'processes_started'})

            start_time = time.time()
            while time.time() - start_time < 10:
                # 处理输出消息
                while not output_queue.empty():
                    msg = output_queue.get_nowait()
                    self.log(msg)
                    self.visual_update('socket', {'type': 'message_exchange'})

                # 处理可视化事件
                while not visual_queue.empty():
                    visual_data = visual_queue.get_nowait()
                    self.visual_update('socket', visual_data)

                time.sleep(0.1)

            server_process.join(timeout=2)
            client_process.join(timeout=2)

            self.method_status['socket'] = 'completed'
            self.visual_update('socket', {'type': 'completed'})
            self.log("套接字通信完成!")
        except Exception as e:
            self.log(f"套接字通信错误: {e}")
            self.method_status['socket'] = 'error'
            self.visual_update('socket', {'type': 'error'})

    def semaphore_communication(self):
        """信号量通信演示"""
        self.current_method = 'semaphore'
        self.method_status['semaphore'] = 'running'

        # 清空之前的图表
        if self.visualizer:
            self.visualizer.clear_visualization('semaphore')

        self.log("\n=== 信号量通信示例 ===")
        self.visual_update('semaphore', {'type': 'start'})

        try:
            from multiprocessing import Semaphore, Manager

            # 使用Manager创建共享列表和锁
            with Manager() as manager:
                # 创建大小为3的缓冲区
                buffer = manager.list()
                buffer_lock = manager.Lock()
                # 创建信号量，初始值为缓冲区大小
                semaphore = Semaphore(3)

                output_queue = Queue()

                # 创建生产者和消费者进程
                producers = []
                consumers = []

                # 启动2个生产者，每个生产3个产品
                for i in range(2):
                    p = Process(target=semaphore_producer_process,
                                args=(semaphore, buffer, buffer_lock, i + 1, output_queue, 3))
                    producers.append(p)
                    p.start()
                    self.visual_update('semaphore', {'type': 'producer_started', 'id': i + 1})

                # 启动2个消费者，每个消费3个产品
                for i in range(2):
                    p = Process(target=semaphore_consumer_process,
                                args=(semaphore, buffer, buffer_lock, i + 1, output_queue, 3))
                    consumers.append(p)
                    p.start()
                    self.visual_update('semaphore', {'type': 'consumer_started', 'id': i + 1})

                self.visual_update('semaphore', {'type': 'processes_started'})

                # 监控进程输出
                start_time = time.time()
                completed_processes = 0
                total_processes = len(producers) + len(consumers)

                while time.time() - start_time < 20 and completed_processes < total_processes:
                    try:
                        while not output_queue.empty():
                            msg = output_queue.get_nowait()
                            self.log(msg)

                            # 解析进程ID
                            process_id = 0
                            if "生产者1" in msg:
                                process_id = 1
                            elif "生产者2" in msg:
                                process_id = 2
                            elif "消费者1" in msg:
                                process_id = 1
                            elif "消费者2" in msg:
                                process_id = 2

                            # 更新可视化
                            if "生产" in msg:
                                self.visual_update('semaphore', {
                                    'type': 'item_produced',
                                    'content': msg,
                                    'process_id': process_id
                                })
                            elif "消费" in msg:
                                self.visual_update('semaphore', {
                                    'type': 'item_consumed',
                                    'content': msg,
                                    'process_id': process_id
                                })
                            elif "完成" in msg:
                                completed_processes += 1
                                self.visual_update('semaphore', {
                                    'type': 'process_completed',
                                    'process_id': process_id
                                })

                        # 更新缓冲区状态
                        with buffer_lock:
                            buffer_size = len(buffer)
                        self.visual_update('semaphore', {'type': 'buffer_update', 'size': buffer_size})

                        time.sleep(0.1)

                    except Exception as e:
                        self.log(f"监控错误: {e}")
                        break

                # 强制终止任何仍在运行的进程
                for p in producers:
                    if p.is_alive():
                        p.terminate()
                for p in consumers:
                    if p.is_alive():
                        p.terminate()

                # 等待进程结束
                for p in producers:
                    p.join(timeout=1)
                for p in consumers:
                    p.join(timeout=1)

                self.method_status['semaphore'] = 'completed'
                self.visual_update('semaphore', {'type': 'completed'})
                self.log("信号量通信完成!")

        except Exception as e:
            self.log(f"信号量通信错误: {e}")
            self.method_status['semaphore'] = 'error'
            self.visual_update('semaphore', {'type': 'error'})

    def run_all_demos(self):
        """运行所有演示"""
        if self.is_running:
            self.log("演示已在运行中，请等待完成...")
            return

        self.is_running = True
        # 重置所有方法状态
        for method in self.method_status:
            self.method_status[method] = 'waiting'

        self.log("开始运行所有进程间通信方法演示...")
        self.log("=" * 50)

        try:
            methods = ['signal', 'pipe', 'queue', 'shared_memory', 'socket', 'semaphore']
            for method in methods:
                self.current_method = method
                if method == 'signal':
                    self.signal_communication()
                elif method == 'pipe':
                    self.pipe_communication()
                elif method == 'queue':
                    self.queue_communication()
                elif method == 'shared_memory':
                    self.shared_memory_communication()
                elif method == 'socket':
                    self.socket_communication()

                time.sleep(1)

            self.log("\n" + "=" * 50)
            self.log("所有IPC方法演示完成!")
        except Exception as e:
            self.log(f"演示过程中出错: {e}")
        finally:
            self.is_running = False
            self.current_method = None

    def run_selected_demo(self, method):
        """运行选定的演示"""
        if self.is_running:
            self.log("演示已在运行中，请等待完成...")
            return

        self.is_running = True
        # 重置方法状态
        for m in self.method_status:
            self.method_status[m] = 'waiting'

        self.log(f"开始 {self.methods[method]} 演示...")
        self.log("=" * 50)

        try:
            self.current_method = method
            if method == 'signal':
                self.signal_communication()
            elif method == 'pipe':
                self.pipe_communication()
            elif method == 'queue':
                self.queue_communication()
            elif method == 'shared_memory':
                self.shared_memory_communication()
            elif method == 'socket':
                self.socket_communication()
            elif method == 'semaphore':
                self.semaphore_communication()

            self.log(f"{self.methods[method]} 演示完成!")
        except Exception as e:
            self.log(f"演示过程中出错: {e}")
        finally:
            self.is_running = False
            self.current_method = None


class IPCApp:
    """IPC演示应用程序"""

    def __init__(self, root):
        self.root = root
        self.root.title("进程间通信(IPC)方法演示 - 图形化界面")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        self.visualizer = Visualizer(self.root)
        self.ipc_manager = IPCManager(self.add_log, self.update_visualization)
        self.ipc_manager.set_visualizer(self.visualizer)  # 设置可视化器

        self.create_widgets()
        self.setup_styles()

    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.configure('.', font=('Microsoft YaHei', 9))
        style.configure('Title.TLabel', font=('Microsoft YaHei', 18, 'bold'), background='#f0f0f0')
        style.configure('Method.TRadiobutton', font=('Microsoft YaHei', 10), background='#f0f0f0')
        style.configure('Action.TButton', font=('Microsoft YaHei', 10, 'bold'))
        style.configure('Status.TFrame', background='#e0e0e0')

    def create_widgets(self):
        """创建界面控件"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky=(tk.W, tk.E))

        title_label = ttk.Label(title_frame, text="进程间通信(IPC)方法图形化演示",
                                style='Title.TLabel')
        title_label.pack()

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.create_control_panel(left_frame)
        self.create_visualization_panel(right_frame)

        log_frame = ttk.LabelFrame(main_frame, text="实时日志", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=12,
                                                  font=('Microsoft YaHei', 9), bg='#fafafa')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        status_frame = ttk.Frame(main_frame, style='Status.TFrame', height=25)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        status_frame.grid_propagate(False)

        self.status_label = ttk.Label(status_frame, text="就绪", background='#e0e0e0', font=('Microsoft YaHei', 9))
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding="15")
        control_frame.pack(fill=tk.BOTH, expand=True)

        # 方法选择 - 改为两列布局
        method_frame = ttk.LabelFrame(control_frame, text="选择IPC方法", padding="10")
        method_frame.pack(fill=tk.X, pady=(0, 10))

        self.method_var = tk.StringVar(value="all")
        methods = [("全部方法", "all"),
                   ("信号通信", "signal"),
                   ("管道通信", "pipe"),
                   ("消息队列", "queue"),
                   ("共享内存", "shared_memory"),
                   ("套接字通信", "socket"),
                   ("信号量通信", "semaphore")]

        # 创建两列框架
        method_columns_frame = ttk.Frame(method_frame)
        method_columns_frame.pack(fill=tk.BOTH, expand=True)

        left_method_frame = ttk.Frame(method_columns_frame)
        left_method_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_method_frame = ttk.Frame(method_columns_frame)
        right_method_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 将方法平均分配到两列
        mid_point = (len(methods) + 1) // 2  # 计算中点
        for i, (text, value) in enumerate(methods):
            if i < mid_point:
                parent_frame = left_method_frame
            else:
                parent_frame = right_method_frame

            rb = ttk.Radiobutton(parent_frame, text=text, variable=self.method_var,
                                 value=value, style='Method.TRadiobutton')
            rb.pack(anchor=tk.W, pady=2)

        # 控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.start_button = ttk.Button(button_frame, text="开始演示",
                                       command=self.start_demo, style='Action.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)

        self.clear_button = ttk.Button(button_frame, text="清空日志",
                                       command=self.clear_log)
        self.clear_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 状态指示器 - 改为两列布局
        status_frame = ttk.LabelFrame(control_frame, text="演示状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 创建两列框架
        status_columns_frame = ttk.Frame(status_frame)
        status_columns_frame.pack(fill=tk.BOTH, expand=True)

        left_status_frame = ttk.Frame(status_columns_frame)
        left_status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_status_frame = ttk.Frame(status_columns_frame)
        right_status_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.status_labels = {}
        method_items = list(self.ipc_manager.methods.items())

        # 将状态项平均分配到两列
        mid_point = (len(method_items) + 1) // 2  # 计算中点

        for i, (method, name) in enumerate(method_items):
            if i < mid_point:
                parent_frame = left_status_frame
            else:
                parent_frame = right_status_frame

            frame = ttk.Frame(parent_frame)
            frame.pack(fill=tk.X, pady=2)

            label = ttk.Label(frame, text=name, width=10, anchor=tk.W, font=('Microsoft YaHei', 9))
            label.pack(side=tk.LEFT)

            status = ttk.Label(frame, text="等待", foreground="gray", width=8, font=('Microsoft YaHei', 9))
            status.pack(side=tk.RIGHT)

            self.status_labels[method] = status

    def create_visualization_panel(self, parent):
        """创建可视化面板"""
        viz_frame = ttk.LabelFrame(parent, text="实时可视化", padding="10")
        viz_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(viz_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        signal_frame = ttk.Frame(notebook, padding="5")
        notebook.add(signal_frame, text="信号通信")
        self.visualizer.create_signal_visualization(signal_frame)

        pipe_frame = ttk.Frame(notebook, padding="5")
        notebook.add(pipe_frame, text="管道通信")
        self.visualizer.create_pipe_visualization(pipe_frame)

        queue_frame = ttk.Frame(notebook, padding="5")
        notebook.add(queue_frame, text="消息队列")
        self.visualizer.create_queue_visualization(queue_frame)

        shared_frame = ttk.Frame(notebook, padding="5")
        notebook.add(shared_frame, text="共享内存")
        self.visualizer.create_shared_memory_visualization(shared_frame)

        socket_frame = ttk.Frame(notebook, padding="5")
        notebook.add(socket_frame, text="套接字通信")
        self.visualizer.create_socket_visualization(socket_frame)

        semaphore_frame = ttk.Frame(notebook, padding="5")
        notebook.add(semaphore_frame, text="信号量通信")
        self.visualizer.create_semaphore_visualization(semaphore_frame)

        overview_frame = ttk.Frame(notebook, padding="5")
        notebook.add(overview_frame, text="概览")
        self.create_overview_tab(overview_frame)

    def create_overview_tab(self, parent):
        """创建概览标签页"""
        fig = plt.Figure(figsize=(8, 4), dpi=80)
        ax = fig.add_subplot(111)
        ax.set_title('IPC方法性能比较', size=12)
        ax.set_xlabel('IPC方法')
        ax.set_ylabel('相对性能')

        methods = list(self.ipc_manager.methods.values())
        # 为6个方法提供6个性能值
        performance = [0.1, 0.3, 0.5, 0.7, 0.9, 0.6]  # 添加第6个值

        # 为6个方法提供6个颜色
        colors = ['skyblue', 'lightgreen', 'gold', 'lightcoral', 'plum', 'orange']  # 添加第6个颜色

        bars = ax.bar(methods, performance, color=colors)
        for bar, perf in zip(bars, performance):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f'{perf:.1f}', ha='center', va='bottom')

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    def add_log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_visualization(self, method, data):
        """更新可视化"""
        if hasattr(self, 'visualizer'):
            self.visualizer.update_visualization(method, data)

        # 改进的状态更新逻辑 - 确保所有状态都能正确更新
        if method in self.status_labels:
            status_label = self.status_labels[method]
            event_type = data.get('type')

            if event_type == 'start':
                status_label.config(text="运行中", foreground="blue")
            elif event_type == 'completed':
                status_label.config(text="已完成", foreground="green")
            elif event_type == 'signal_sent':
                status_label.config(text="发送信号", foreground="orange")
            elif event_type == 'signal_received':
                status_label.config(text="收到信号", foreground="purple")
            elif event_type == 'error':
                status_label.config(text="错误", foreground="red")
            elif event_type == 'server_start':
                status_label.config(text="服务器启动", foreground="blue")
            elif event_type == 'client_connected':
                status_label.config(text="客户端连接", foreground="orange")
            elif event_type == 'message_sent':
                status_label.config(text="发送消息", foreground="purple")
            elif event_type == 'message_received':
                status_label.config(text="接收消息", foreground="green")
            elif event_type == 'connection_closed':
                status_label.config(text="连接关闭", foreground="red")

            # 强制更新界面
            self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def start_demo(self):
        """开始演示"""
        if self.ipc_manager.is_running:
            messagebox.showwarning("警告", "演示已在运行中，请等待完成")
            return

        # 重置所有状态标签
        for status_label in self.status_labels.values():
            status_label.config(text="等待", foreground="gray")

        self.start_button.config(state='disabled')
        self.status_label.config(text="演示运行中...")
        self.progress.start()

        def run_demo():
            selected_method = self.method_var.get()
            if selected_method == 'all':
                self.ipc_manager.run_all_demos()
            else:
                self.ipc_manager.run_selected_demo(selected_method)

            self.root.after(0, self.demo_finished)

        demo_thread = threading.Thread(target=run_demo)
        demo_thread.daemon = True
        demo_thread.start()

    def demo_finished(self):
        """演示完成后的回调"""
        self.progress.stop()
        self.start_button.config(state='normal')
        self.status_label.config(text="演示完成")

        # 最终状态检查，确保所有方法都标记为完成
        for method in self.status_labels:
            current_text = self.status_labels[method].cget('text')
            if current_text in ["运行中", "发送信号", "收到信号", "服务器启动", "客户端连接", "发送消息", "接收消息",
                                "连接关闭"]:
                self.status_labels[method].config(text="已完成", foreground="green")

        # 强制更新界面
        self.root.update_idletasks()
        messagebox.showinfo("完成", "IPC演示已完成!")


def main():
    """主函数"""
    import matplotlib
    matplotlib.use('TkAgg')

    root = tk.Tk()
    app = IPCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()