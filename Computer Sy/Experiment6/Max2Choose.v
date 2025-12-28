module Mux2Choose1(
    input [29:0] data0,    // 第1路30位数据输入
    input [29:0] data1,    // 第2路30位数据输入  
    input sel,             // 选择信号
    output reg [29:0] out  // 30位数据输出
);

// 实现2路选择器功能
always @(*) begin
    if (sel == 1'b0) begin
        out = data0;
    end else begin
        out = data1;
    end
end

endmodule