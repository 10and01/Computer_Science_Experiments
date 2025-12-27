import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import time

class ProgramA:
    def __init__(self):
        # 初始化界面
        self.root = tk.Tk()
        self.root.title("程序A - 双向通信")
        self.root.geometry("600x500")
        
        # 创建界面组件
        self.create_widgets()
        
        # 网络设置
        self.host = 'localhost'
        self.port_a = 8888  # A的监听端口
        self.port_b = 8889  # B的监听端口
        
        # 通信状态
        self.connected = False
        self.socket_to_b = None
        
        # 启动A的服务器线程
        self.start_server()
        
        # 尝试连接到B
        self.connect_to_b()
        
    def create_widgets(self):
        # 消息显示区域
        self.text_area = scrolledtext.ScrolledText(self.root, width=70, height=20)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.config(state=tk.DISABLED)
        
        # 输入区域
        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.entry = tk.Entry(input_frame, width=50)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind("<Return>", self.send_message)
        
        self.send_btn = tk.Button(input_frame, text="发送", command=self.send_message)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态显示
        self.status_label = tk.Label(self.root, text="状态: 未连接", fg="red")
        self.status_label.pack(pady=5)
        
        # 控制按钮区域
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)
        
        self.clear_btn = tk.Button(control_frame, text="清空消息", command=self.clear_messages)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.exit_btn = tk.Button(control_frame, text="退出", command=self.exit_program)
        self.exit_btn.pack(side=tk.LEFT, padx=5)
    
    def start_server(self):
        """启动A的服务器线程，监听来自B的连接"""
        def server_thread():
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                server_socket.bind((self.host, self.port_a))
                server_socket.listen(1)
                self.add_message("系统", f"A正在端口{self.port_a}上监听...")
                
                while True:
                    client_socket, addr = server_socket.accept()
                    self.add_message("系统", f"收到来自{addr}的连接")
                    
                    # 启动接收消息线程
                    receive_thread = threading.Thread(
                        target=self.receive_messages, 
                        args=(client_socket,)
                    )
                    receive_thread.daemon = True
                    receive_thread.start()
                    
            except Exception as e:
                self.add_message("系统错误", f"服务器错误: {str(e)}")
        
        thread = threading.Thread(target=server_thread)
        thread.daemon = True
        thread.start()
    
    def connect_to_b(self):
        """连接到B程序"""
        def connect_thread():
            try:
                self.socket_to_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_to_b.connect((self.host, self.port_b))
                self.connected = True
                self.update_status("已连接到B", "green")
                self.add_message("系统", "成功连接到程序B")
                
                # 启动接收来自B的消息的线程
                receive_thread = threading.Thread(target=self.receive_from_b)
                receive_thread.daemon = True
                receive_thread.start()
                
            except Exception as e:
                self.add_message("系统", f"无法连接到B: {str(e)}，5秒后重试...")
                self.root.after(5000, self.connect_to_b)  # 5秒后重试
        
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def receive_from_b(self):
        """从B接收消息"""
        try:
            while self.connected:
                data = self.socket_to_b.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                try:
                    message_data = json.loads(data)
                    self.add_message("B", message_data['message'])
                except:
                    self.add_message("B", data)
                    
        except Exception as e:
            self.add_message("系统错误", f"接收消息错误: {str(e)}")
            self.connected = False
            self.update_status("连接断开", "red")
            self.root.after(5000, self.connect_to_b)  # 5秒后重试连接
    
    def receive_messages(self, client_socket):
        """从连接的客户端接收消息"""
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                try:
                    message_data = json.loads(data)
                    self.add_message("B", message_data['message'])
                except:
                    self.add_message("B", data)
                    
        except Exception as e:
            self.add_message("系统错误", f"接收消息错误: {str(e)}")
        finally:
            client_socket.close()
    
    def send_message(self, event=None):
        """发送消息到B"""
        message = self.entry.get().strip()
        if not message:
            return
            
        if not self.connected:
            messagebox.showwarning("警告", "未连接到程序B，无法发送消息")
            return
            
        try:
            # 创建消息数据包
            message_data = {
                'timestamp': time.time(),
                'message': message,
                'sender': 'A'
            }
            
            # 发送消息
            self.socket_to_b.send(json.dumps(message_data).encode('utf-8'))
            
            # 在界面显示
            self.add_message("A", message)
            
            # 清空输入框
            self.entry.delete(0, tk.END)
            
        except Exception as e:
            self.add_message("系统错误", f"发送消息失败: {str(e)}")
            self.connected = False
            self.update_status("连接断开", "red")
    
    def add_message(self, sender, message):
        """在消息区域添加消息"""
        self.text_area.config(state=tk.NORMAL)
        
        # 添加时间戳
        timestamp = time.strftime("%H:%M:%S")
        
        # 不同发送者使用不同颜色
        if sender == "A":
            self.text_area.insert(tk.END, f"[{timestamp}] A: {message}\n", "a_message")
        elif sender == "B":
            self.text_area.insert(tk.END, f"[{timestamp}] B: {message}\n", "b_message")
        else:  # 系统消息
            self.text_area.insert(tk.END, f"[{timestamp}] 系统: {message}\n", "system")
        
        self.text_area.config(state=tk.DISABLED)
        self.text_area.see(tk.END)  # 滚动到底部
    
    def update_status(self, status, color):
        """更新状态标签"""
        self.status_label.config(text=f"状态: {status}", fg=color)
    
    def clear_messages(self):
        """清空消息区域"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)
    
    def exit_program(self):
        """退出程序"""
        if self.connected and self.socket_to_b:
            self.socket_to_b.close()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        # 配置文本标签样式
        self.text_area.tag_config("a_message", foreground="blue")
        self.text_area.tag_config("b_message", foreground="green")
        self.text_area.tag_config("system", foreground="gray")
        
        # 启动主循环
        self.root.mainloop()

if __name__ == "__main__":
    app = ProgramA()
    app.run()