//二选一
module mux2to1 #(parameter WIDTH = 8) (
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input sel,
    output reg [WIDTH-1:0] y
);
    always @(*) begin
        case(sel)
            1'b0: y = a;
            1'b1: y = b;
            default: y = a;
        endcase
    end
endmodule

//三选一
module mux3to1 #(parameter WIDTH = 8) (
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input [WIDTH-1:0] c,
    input [1:0] sel,
    output reg [WIDTH-1:0] y
);
    always @(*) begin
        case(sel)
            2'b00: y = a;
            2'b01: y = b;
            2'b10: y = c;
            default: y = a;
        endcase
    end
endmodule

//加法器
module adder #(parameter WIDTH = 8) (
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input cin,
    output [WIDTH-1:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule

//算术逻辑单元核心
module alu #(parameter WIDTH = 8) (
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input [2:0] opcode,
    input cin,
    output reg [WIDTH-1:0] result,
    output reg cout,
    output reg zero,
    output reg negative,
    output reg overflow
);
    
    wire [WIDTH-1:0] sum;
    wire add_cout;
    
    // 实例化加法器
    adder #(WIDTH) add_inst (.a(a), .b(b), .cin(cin), .sum(sum), .cout(add_cout));
    always @(*) begin
        cout = 1'b0;
        overflow = 1'b0;
        
        case(opcode)
            // 加法运算
            3'b000: begin
                result = sum;
                cout = add_cout;
                // 溢出检测：两个同号数相加结果符号改变
                overflow = (~a[WIDTH-1] & ~b[WIDTH-1] & result[WIDTH-1]) | 
                          (a[WIDTH-1] & b[WIDTH-1] & ~result[WIDTH-1]);
            end
            
            // 减法运算 (a - b)
            3'b001: begin
                result = a - b;
                cout = (a >= b) ? 1'b1 : 1'b0;
                overflow = (~a[WIDTH-1] & b[WIDTH-1] & result[WIDTH-1]) | 
                          (a[WIDTH-1] & ~b[WIDTH-1] & ~result[WIDTH-1]);
            end
            
            // 与运算
            3'b010: result = a & b;
            // 或运算
            3'b011: result = a | b;
            // 异或运算
            3'b100: result = a ^ b;
            // 非运算
            3'b101: result = ~a;
            // SLT运算
            3'b110: begin
                // 有符号比较：如果a < b，则结果为1，否则为0
                result = ($signed(a) < $signed(b)) ? 1 : 0;
                // 对于SLT，通常不需要设置cout、overflow等标志位，但可以保持默认
                cout = 1'b0;
                overflow = 1'b0;
            end
            // 右移
            3'b111: result = a >> 1;

            
            default: result = 8'b0;
        endcase
        
        // 标志位设置
        zero = (result == 0);
        negative = result[WIDTH-1];
    end
    
endmodule

module ALU #(parameter WIDTH = 8) (
    input clk,
    input rst_n,
    input [WIDTH-1:0] data_in,
    input [1:0] reg_sel,
    input [2:0] alu_op,
    input write_en,
    input alu_en,
    input cin,
    output [WIDTH-1:0] data_out,
    output zero_flag,
    output neg_flag,
    output ovf_flag
);
    
    // 内部寄存器
    reg [WIDTH-1:0] reg_a, reg_b, reg_c;
    
    // ALU输入多路选择
    wire [WIDTH-1:0] alu_a, alu_b;
    wire [WIDTH-1:0] alu_result;
    wire alu_cout, alu_zero, alu_neg, alu_ovf;
    
    // 三选一多路选择器选择寄存器输出
    mux3to1 #(WIDTH) mux_reg_out (
        .a(reg_a),
        .b(reg_b),
        .c(reg_c),
        .sel(reg_sel),
        .y(data_out)
    );
    
    // 二选一多路选择器选择ALU输入A
    mux2to1 #(WIDTH) mux_alu_a (
        .a(reg_a),
        .b(data_in),
        .sel(alu_en),
        .y(alu_a)
    );
    
    // 二选一多路选择器选择ALU输入B
    mux2to1 #(WIDTH) mux_alu_b (
        .a(reg_b),
        .b(reg_c),
        .sel(alu_en),
        .y(alu_b)
    );
    
    // ALU实例
    alu #(WIDTH) alu_inst (
        .a(alu_a),
        .b(alu_b),
        .opcode(alu_op),
        .cin(cin),
        .result(alu_result),
        .cout(alu_cout),
        .zero(alu_zero),
        .negative(alu_neg),
        .overflow(alu_ovf)
    );
    
    // 寄存器写入逻辑
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_a <= 0;
            reg_b <= 0;
            reg_c <= 0;
        end else if (write_en) begin
            case(reg_sel)
                2'b00: reg_a <= alu_en ? alu_result : data_in;
                2'b01: reg_b <= alu_en ? alu_result : data_in;
                2'b10: reg_c <= alu_en ? alu_result : data_in;
                default: ; // 保持原值
            endcase
        end
    end
    
    // 输出标志位
    assign zero_flag = alu_zero;
    assign neg_flag = alu_neg;
    assign ovf_flag = alu_ovf;
    
endmodule


