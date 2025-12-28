module adder(
    input [29:0] A,        // 30位加数A
    input [29:0] B,        // 30位加数B
    output reg [29:0] C    // 30位和
);

// 实现30位加法器
always @(A or B) begin
    C = A + B;
end

endmodule