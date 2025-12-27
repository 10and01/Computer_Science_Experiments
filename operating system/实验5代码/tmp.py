import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.patches import Patch
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton, QLabel,
                             QHeaderView, QMessageBox, QGroupBox, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIntValidator

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class Job:
    """作业类"""

    def __init__(self, name: str, arrival_time: int, service_time: int):
        self.name = name
        self.arrival_time = arrival_time
        self.service_time = service_time
        self.remaining_time = service_time
        self.start_time = -1
        self.end_time = -1
        self.current_queue = 0  # 当前所在的队列(0,1,2)
        self.execution_history = []  # 记录执行历史，用于可视化
        self.queue_entry_time = {}  # 记录进入每个队列的时间
        self.last_queue_change_time = 0  # 最后一次队列变化的时间


class MLFQScheduler:
    """多级反馈队列调度器类"""

    def __init__(self, enable_priority_boost=False, boost_threshold=5):
        self.jobs = []  # 所有作业
        self.ready_queues = [[] for _ in range(3)]  # 3个就绪队列
        self.current_job = None  # 当前正在运行的作业
        self.current_time = 0  # 当前系统时间
        self.next_job_index = 0  # 下一个要处理的作业索引
        self.time_slices = [1, 2, 4]  # 时间片大小配置
        self.scheduling_log = []  # 调度日志，用于可视化
        self.enable_priority_boost = enable_priority_boost  # 是否启用优先级提升
        self.boost_threshold = boost_threshold  # 优先级提升阈值

    def add_job(self, job: Job) -> None:
        """添加作业"""
        self.jobs.append(job)

    def run(self) -> None:
        """运行调度器"""
        # 按到达时间排序
        self.jobs.sort(key=lambda x: x.arrival_time)

        print("多级反馈队列调度过程:")
        print(f"算法: {'变种算法' if self.enable_priority_boost else '原版算法'}")
        if self.enable_priority_boost:
            print(f"优先级提升阈值: {self.boost_threshold}时间单位")
        print("时间\t事件")
        print("----------------")

        # 记录初始状态
        self._log_state("开始调度")

        # 主循环
        while True:
            # 添加所有已到达但未处理的作业到就绪队列0
            while (self.next_job_index < len(self.jobs) and
                   self.jobs[self.next_job_index].arrival_time <= self.current_time):

                job = self.jobs[self.next_job_index]
                print(f"{self.current_time}\t{job.name} 到达，进入队列0")
                self._log_state(f"{job.name}到达")

                if job.start_time == -1:
                    job.start_time = self.current_time

                # 记录进入队列0的时间
                job.queue_entry_time[0] = self.current_time
                job.last_queue_change_time = self.current_time

                self.ready_queues[0].append(job)
                self.next_job_index += 1

                # 检查是否需要抢占当前作业
                if (self.current_job is not None and
                        self.current_job.current_queue > 0):
                    print(f"{self.current_time}\t抢占 {self.current_job.name}，新作业{job.name}有更高优先级")
                    self.ready_queues[self.current_job.current_queue].append(self.current_job)
                    self._log_state(f"抢占{self.current_job.name}")
                    self.current_job = None

            # 检查并处理优先级提升（变种算法）
            if self.enable_priority_boost:
                self._check_priority_boost()

            # 如果CPU空闲，从就绪队列中选择作业
            if self.current_job is None:
                # 找到最高优先级的非空队列
                queue_idx = -1
                for i in range(3):
                    if self.ready_queues[i]:
                        queue_idx = i
                        break

                if queue_idx == -1:
                    # 如果没有作业在等待，但有作业未到达，跳到下一个作业的到达时间
                    if self.next_job_index < len(self.jobs):
                        self.current_time = self.jobs[self.next_job_index].arrival_time
                        continue
                    else:
                        # 所有作业都处理完毕
                        break

                # 从队列中取出作业
                self.current_job = self.ready_queues[queue_idx].pop(0)
                self.current_job.current_queue = queue_idx

                # 计算本次运行时间
                allocated_time = min(self.time_slices[queue_idx], self.current_job.remaining_time)
                print(
                    f"{self.current_time}\t{self.current_job.name} 从队列{queue_idx}开始运行 ({allocated_time}时间单位)")
                self._log_state(f"{self.current_job.name}开始运行")

                # 记录执行开始
                execution_start = self.current_time

                # 检查是否有新作业会在此期间到达
                actual_run_time = allocated_time
                if self.next_job_index < len(self.jobs):
                    next_arrival = self.jobs[self.next_job_index].arrival_time
                    if self.current_time + actual_run_time > next_arrival:
                        actual_run_time = next_arrival - self.current_time
                        print(f"{self.current_time}\t注意: {self.current_job.name} 的运行将被新作业到达中断")

                # 推进时间
                self.current_time += actual_run_time
                self.current_job.remaining_time -= actual_run_time

                # 记录执行历史
                self.current_job.execution_history.append(
                    (execution_start, self.current_time, self.current_job.current_queue)
                )

                # 检查作业是否完成
                if self.current_job.remaining_time == 0:
                    print(f"{self.current_time}\t{self.current_job.name} 完成")
                    self.current_job.end_time = self.current_time
                    self._log_state(f"{self.current_job.name}完成")
                    self.current_job = None
                elif actual_run_time < allocated_time:
                    # 作业被新作业到达中断
                    print(
                        f"{self.current_time}\t{self.current_job.name} 被新作业中断，剩余时间: {self.current_job.remaining_time}")

                    # 记录进入队列的时间
                    self.current_job.queue_entry_time[self.current_job.current_queue] = self.current_time
                    self.current_job.last_queue_change_time = self.current_time

                    self.ready_queues[self.current_job.current_queue].append(self.current_job)
                    self._log_state(f"{self.current_job.name}被中断")
                    self.current_job = None
                else:
                    # 时间片用完，但作业未完成
                    print(
                        f"{self.current_time}\t{self.current_job.name} 在队列{self.current_job.current_queue}时间片用完，剩余时间: {self.current_job.remaining_time}")

                    # 降级到下一队列
                    next_queue = min(self.current_job.current_queue + 1, 2)
                    print(f"{self.current_time}\t{self.current_job.name} 降级到队列{next_queue}")

                    self.current_job.current_queue = next_queue

                    # 记录进入新队列的时间
                    self.current_job.queue_entry_time[next_queue] = self.current_time
                    self.current_job.last_queue_change_time = self.current_time

                    self.ready_queues[next_queue].append(self.current_job)
                    self._log_state(f"{self.current_job.name}降级到队列{next_queue}")
                    self.current_job = None
            else:
                # 这不应该发生，因为我们在上面已经处理了所有情况
                break

        # 输出结果
        self.print_results()

        # 生成可视化
        self.visualize_scheduling()

    def _check_priority_boost(self):
        """检查并处理优先级提升（变种算法）"""
        # 只检查队列1和队列2（低优先级队列）
        for queue_idx in [1, 2]:
            jobs_to_boost = []

            # 遍历队列中的每个作业
            for job in self.ready_queues[queue_idx]:
                # 计算在当前队列的等待时间
                if queue_idx in job.queue_entry_time:
                    wait_time = self.current_time - job.queue_entry_time[queue_idx]

                    # 如果等待时间超过阈值，则提升优先级
                    if wait_time >= self.boost_threshold:
                        jobs_to_boost.append(job)

            # 提升符合条件的作业优先级
            for job in jobs_to_boost:
                # 从当前队列移除
                self.ready_queues[queue_idx].remove(job)

                # 提升到上一级队列（但不能超过队列0）
                new_queue = max(0, queue_idx - 1)
                job.current_queue = new_queue

                # 记录进入新队列的时间
                job.queue_entry_time[new_queue] = self.current_time
                job.last_queue_change_time = self.current_time

                # 添加到新队列
                self.ready_queues[new_queue].append(job)

                print(f"{self.current_time}\t{job.name} 在队列{queue_idx}等待时间超过阈值，提升到队列{new_queue}")
                self._log_state(f"{job.name}优先级提升")

    def _log_state(self, event: str) -> None:
        """记录调度状态"""
        queue_states = []
        for i, queue in enumerate(self.ready_queues):
            queue_states.append([job.name for job in queue])

        current_job_name = self.current_job.name if self.current_job else "None"

        self.scheduling_log.append({
            'time': self.current_time,
            'event': event,
            'current_job': current_job_name,
            'queue0': queue_states[0].copy(),
            'queue1': queue_states[1].copy(),
            'queue2': queue_states[2].copy()
        })

    def print_results(self) -> None:
        """输出调度结果"""
        print("\n调度结果:")
        print("作业\t到达时间\t开始时间\t完成时间\t周转时间")
        print("----------------------------------------")

        total_turnaround = 0
        for job in self.jobs:
            turnaround = job.end_time - job.arrival_time
            total_turnaround += turnaround

            print(f"{job.name}\t{job.arrival_time}\t\t{job.start_time}\t\t{job.end_time}\t\t{turnaround}")

        print(f"\n平均周转时间: {total_turnaround / len(self.jobs):.2f}")
        print(f"总周转时间: {total_turnaround}")

    def visualize_scheduling(self) -> None:
        """生成调度过程可视化"""
        if not self.jobs:
            return

        # 创建图形
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
        fig.suptitle('多级反馈队列调度算法可视化', fontsize=16, fontweight='bold')

        # 1. 甘特图
        self._create_gantt_chart(ax1)

        # 2. 队列状态随时间变化图
        self._create_queue_status_chart(ax2)

        # 3. 统计信息图
        self._create_statistics_chart(ax3)

        plt.tight_layout()
        plt.show()

        # 打印详细调度日志
        self._print_detailed_log()

    def _create_gantt_chart(self, ax) -> None:
        """创建甘特图"""
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9AA2', '#FFB7B2', '#FFDAC1', '#E2F0CB',
                  '#B5EAD7']  # 不同作业的颜色

        for i, job in enumerate(self.jobs):
            for start, end, queue in job.execution_history:
                # 使用作业颜色，但根据队列调整亮度
                color = colors[i % len(colors)]
                # 根据队列深度调整颜色亮度
                brightness = 0.7 + queue * 0.1
                color = self._adjust_color_brightness(color, brightness)

                # 绘制执行条
                bar = ax.barh(job.name, end - start, left=start, height=0.6,
                              color=color, edgecolor='black', alpha=0.8)

                # 在条形中间添加队列信息
                ax.text((start + end) / 2, i, f'Q{queue}',
                        ha='center', va='center', fontweight='bold')

                # 在条形上方添加时间范围
                time_range = f"{start}-{end}"
                ax.text((start + end) / 2, i + 0.25, time_range,
                        ha='center', va='center', fontsize=8)

        ax.set_xlabel('时间')
        ax.set_ylabel('作业')
        ax.set_title('作业执行甘特图')
        ax.grid(True, alpha=0.3)

        # 创建图例
        legend_elements = [
            Patch(facecolor=colors[i], label=f'作业 {job.name}')
            for i, job in enumerate(self.jobs)
        ]
        ax.legend(handles=legend_elements, loc='upper right')

    def _create_queue_status_chart(self, ax) -> None:
        """创建队列状态图"""
        times = [log['time'] for log in self.scheduling_log]
        queue0_lengths = [len(log['queue0']) for log in self.scheduling_log]
        queue1_lengths = [len(log['queue1']) for log in self.scheduling_log]
        queue2_lengths = [len(log['queue2']) for log in self.scheduling_log]

        ax.plot(times, queue0_lengths, label='队列0', color='red', linewidth=2, marker='o')
        ax.plot(times, queue1_lengths, label='队列1', color='blue', linewidth=2, marker='s')
        ax.plot(times, queue2_lengths, label='队列2', color='green', linewidth=2, marker='^')

        ax.set_xlabel('时间')
        ax.set_ylabel('队列长度')
        ax.set_title('队列状态随时间变化')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _create_statistics_chart(self, ax) -> None:
        """创建统计信息图"""
        # 计算统计信息
        job_names = [job.name for job in self.jobs]
        turnaround_times = [job.end_time - job.arrival_time for job in self.jobs]
        wait_times = [turnaround - job.service_time for job, turnaround in zip(self.jobs, turnaround_times)]

        x = np.arange(len(job_names))
        width = 0.35

        bars1 = ax.bar(x - width / 2, turnaround_times, width, label='周转时间', color='lightblue', alpha=0.7)
        bars2 = ax.bar(x + width / 2, wait_times, width, label='等待时间', color='lightcoral', alpha=0.7)

        ax.set_xlabel('作业')
        ax.set_ylabel('时间')
        ax.set_title('作业调度统计信息')
        ax.set_xticks(x)
        ax.set_xticklabels(job_names)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 在柱子上添加数值
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.0f}', ha='center', va='bottom')

        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.0f}', ha='center', va='bottom')

    def _adjust_color_brightness(self, color, factor):
        """调整颜色亮度"""
        import matplotlib.colors as mc
        import colorsys
        try:
            c = mc.cnames[color]
        except:
            c = color
        c = colorsys.rgb_to_hls(*mc.to_rgb(c))
        return colorsys.hls_to_rgb(c[0], max(0, min(1, factor * c[1])), c[2])

    def _print_detailed_log(self) -> None:
        """打印详细调度日志"""
        print("\n" + "=" * 60)
        print("详细调度日志")
        print("=" * 60)

        df_log = pd.DataFrame(self.scheduling_log)
        print(df_log.to_string(index=False))


class JobInputWindow(QMainWindow):
    """作业输入界面"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("多级反馈队列调度算法")
        self.setGeometry(300, 300, 800, 600)

        # 创建主部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 标题
        title_label = QLabel("多级反馈队列调度算法")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)

        # 算法选择区域
        algorithm_group = QGroupBox("算法设置")
        algorithm_layout = QHBoxLayout(algorithm_group)

        # 算法选择标签
        algorithm_label = QLabel("选择算法:")
        algorithm_layout.addWidget(algorithm_label)

        # 算法选择下拉框
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItem("原版算法")
        self.algorithm_combo.addItem("变种算法（优先级提升）")
        algorithm_layout.addWidget(self.algorithm_combo)

        # 优先级提升阈值设置
        self.threshold_label = QLabel("优先级提升阈值:")
        algorithm_layout.addWidget(self.threshold_label)

        self.threshold_input = QLineEdit("5")
        self.threshold_input.setValidator(QIntValidator(1, 100))
        self.threshold_input.setFixedWidth(50)
        algorithm_layout.addWidget(self.threshold_input)

        algorithm_layout.addStretch()
        self.main_layout.addWidget(algorithm_group)

        # 说明标签
        instruction_label = QLabel("请在下方表格中输入作业信息（作业名、到达时间、服务时间）")
        instruction_label.setFont(QFont("Arial", 10))
        self.main_layout.addWidget(instruction_label)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["作业名", "到达时间", "服务时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setRowCount(5)  # 初始5行

        # 设置表格行高
        self.table.verticalHeader().setDefaultSectionSize(30)

        # 填充默认值
        default_jobs = [
            ("A", 0, 3),
            ("B", 2, 6),
            ("C", 4, 4),
            ("D", 6, 5),
            ("E", 8, 2)
        ]

        for row, (name, arrival, service) in enumerate(default_jobs):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(arrival)))
            self.table.setItem(row, 2, QTableWidgetItem(str(service)))

        self.main_layout.addWidget(self.table)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 添加行按钮
        add_row_btn = QPushButton("添加行")
        add_row_btn.clicked.connect(self.add_row)
        button_layout.addWidget(add_row_btn)

        # 删除行按钮
        remove_row_btn = QPushButton("删除行")
        remove_row_btn.clicked.connect(self.remove_row)
        button_layout.addWidget(remove_row_btn)

        # 清空按钮
        clear_btn = QPushButton("清空表格")
        clear_btn.clicked.connect(self.clear_table)
        button_layout.addWidget(clear_btn)

        # 默认数据按钮
        default_btn = QPushButton("加载默认数据")
        default_btn.clicked.connect(self.load_default_data)
        button_layout.addWidget(default_btn)

        self.main_layout.addLayout(button_layout)

        # 运行按钮
        run_btn = QPushButton("运行调度算法")
        run_btn.setFont(QFont("Arial", 12, QFont.Bold))
        run_btn.clicked.connect(self.run_scheduler)
        self.main_layout.addWidget(run_btn)

        # 设置表格单元格验证器
        for row in range(self.table.rowCount()):
            self.set_validators(row)

    def add_row(self):
        """添加新行"""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        self.set_validators(row_count)

    def remove_row(self):
        """删除选中行"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def clear_table(self):
        """清空表格"""
        self.table.setRowCount(0)

    def load_default_data(self):
        """加载默认数据"""
        self.clear_table()

        # 根据选择的算法加载不同的默认数据
        algorithm_type = self.algorithm_combo.currentText()

        if algorithm_type == "原版算法":
            # 原版算法默认数据
            default_jobs = [
                ("A", 0, 3),
                ("B", 2, 6),
                ("C", 4, 4),
                ("D", 6, 5),
                ("E", 8, 2)
            ]
            self.threshold_input.setText("5")  # 重置阈值
        else:  # 变种算法
            # 特别设计的默认数据，用于展示优先级提升效果
            # 长作业 + 多个短作业 + 间隙期
            default_jobs = [
                ("LongJob", 0, 15),  # 长作业，会降级到低优先级队列
                ("ShortJob1", 2, 1),  # 短作业，会抢占长作业
                ("ShortJob2", 4, 1),  # 短作业，会抢占长作业
                ("ShortJob3", 6, 1),  # 短作业，会抢占长作业
                ("ShortJob4", 8, 1),  # 短作业，会抢占长作业
                ("GapPeriod", 10, 0),  # 间隙期，无新作业到达
                ("ShortJob5", 12, 1),  # 短作业，会抢占长作业
                ("ShortJob6", 14, 1),  # 短作业，会抢占长作业
                ("ShortJob7", 16, 1),  # 短作业，会抢占长作业
                ("ShortJob8", 18, 1)  # 短作业，会抢占长作业
            ]
            self.threshold_input.setText("6")  # 设置合理的阈值

        self.table.setRowCount(len(default_jobs))
        for row, (name, arrival, service) in enumerate(default_jobs):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(arrival)))
            self.table.setItem(row, 2, QTableWidgetItem(str(service)))
            self.set_validators(row)

    def set_validators(self, row):
        """为指定行设置验证器"""
        # 到达时间验证器
        arrival_item = self.table.item(row, 1)
        if not arrival_item:
            arrival_item = QTableWidgetItem("0")
            self.table.setItem(row, 1, arrival_item)
        arrival_item.setTextAlignment(Qt.AlignCenter)

        # 服务时间验证器
        service_item = self.table.item(row, 2)
        if not service_item:
            service_item = QTableWidgetItem("1")
            self.table.setItem(row, 2, service_item)
        service_item.setTextAlignment(Qt.AlignCenter)

    def run_scheduler(self):
        """运行调度算法"""
        # 收集作业数据
        jobs = []
        valid = True

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            arrival_item = self.table.item(row, 1)
            service_item = self.table.item(row, 2)

            # 检查数据是否完整
            if not name_item or not name_item.text().strip():
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 作业名不能为空")
                valid = False
                break

            if not arrival_item or not arrival_item.text().strip():
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 到达时间不能为空")
                valid = False
                break

            if not service_item or not service_item.text().strip():
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 服务时间不能为空")
                valid = False
                break

            try:
                name = name_item.text().strip()
                arrival = int(arrival_item.text())
                service = int(service_item.text())

                if arrival < 0:
                    QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 到达时间不能为负数")
                    valid = False
                    break

                if service < 0:
                    QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 服务时间不能为负数")
                    valid = False
                    break

                jobs.append((name, arrival, service))
            except ValueError:
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 到达时间和服务时间必须是整数")
                valid = False
                break

        if not valid or not jobs:
            return

        # 获取算法设置
        algorithm_type = self.algorithm_combo.currentText()
        enable_priority_boost = algorithm_type == "变种算法（优先级提升）"

        # 获取阈值
        try:
            threshold = int(self.threshold_input.text())
            if threshold <= 0:
                QMessageBox.warning(self, "输入错误", "优先级提升阈值必须大于0")
                return
        except ValueError:
            QMessageBox.warning(self, "输入错误", "优先级提升阈值必须是整数")
            return

        # 创建调度器并添加作业
        scheduler = MLFQScheduler(enable_priority_boost=enable_priority_boost, boost_threshold=threshold)
        for name, arrival, service in jobs:
            scheduler.add_job(Job(name, arrival, service))

        # 运行调度器.
        scheduler.run()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = JobInputWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
