module Register32(
    input clk,                // 时钟信号
    input wr,                 // 写使能
    input [4:0] Ra, Rb, Rw,  // 读地址A、读地址B、写地址
    input [31:0] busW,        // 写入数据总线
    output reg [31:0] busA,   // 读数据总线A
    output reg [31:0] busB    // 读数据总线B
);

    // 定义32个32位寄存器
    reg [31:0] register [31:0];
    
    // 读操作 - 组合逻辑
    always @(*) begin
        busA = register[Ra];  // 将Ra指定寄存器的内容赋值给busA
        busB = register[Rb];  // 将Rb指定寄存器的内容赋值给busB
    end
    
    // 初始化寄存器
    integer i;
    initial begin
        for (i = 0; i < 32; i = i + 1) begin
            register[i] = 32'b0;  // 将所有寄存器初始化为0
        end
    end
    
    // 写操作 - 时钟下降沿触发
    always @(negedge clk) begin
        if (wr) begin  // 写使能有效
            if (Rw != 0) begin  // 寄存器0是只读寄存器
                register[Rw] <= busW;  // 将busW内容写入Rw指定的寄存器
            end
        end
    end

endmodule