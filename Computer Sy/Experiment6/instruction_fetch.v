module instruction_fetch(
    input clk,             // 时钟信号
    input reset,           // 复位信号
    input jump_en,         // 跳转使能信号
    input [29:0] jump_addr, // 跳转地址
    output [31:0] instruction, // 当前指令
	 output reg [29:0] pc
);

// 内部信号定义
wire [29:0] pc_plus_4;     // PC+4
wire [29:0] next_pc;       // 下一个PC值

// 实例化加法器模块，计算PC+4
adder #(30) pc_adder(
    .a(pc),
    .b(30'd4),
    .cin(1'b0),
    .sum(pc_plus_4),
//    .cout(cout)
);


// 实例化多路选择器，选择下一条指令地址
Mux2Choose1 pc_mux(
    .data0(pc_plus_4),     // 顺序执行
    .data1(jump_addr),     // 跳转地址
    .sel(jump_en),         // 跳转使能选择
    .out(next_pc)
);

// 实例化指令存储器
instruction_memory imem(
    .address(pc), 
    .instruction(instruction)
);

// PC寄存器，在时钟下降沿更新
always @(negedge clk or posedge reset) begin
    if (reset) begin
        pc <= 30'b0;       // 复位时PC清零
    end else begin
        pc <= next_pc;     // 更新PC值
    end
end

endmodule