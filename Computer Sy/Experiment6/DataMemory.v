module DataMemory(
    input WrEn,               // 写使能
    input Clk,                // 时钟信号
    input [31:0] DataIn,      // 输入数据
    input [4:0] Adr,          // 地址
    output [31:0] DataOut     // 输出数据
);

    // 定义64个32位存储器单元
    reg [31:0] MemReg [63:0];
    integer i;
    initial begin
        for (i = 0; i < 64; i = i + 1) begin
            MemReg[i] = i;  
        end
    end
    // 写操作 - 时钟下降沿触发
    always @(negedge Clk) begin
        if (WrEn) begin  // 写使能有效
            MemReg[Adr] <= DataIn;  // 将DataIn内容写入MemReg[Adr]
        end
    end
    
    // 读操作 - 组合逻辑
    assign DataOut = MemReg[Adr];  // 将MemReg[Adr]中内容赋值给DataOut

endmodule
