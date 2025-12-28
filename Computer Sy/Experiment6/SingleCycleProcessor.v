
// 符号扩展模块
module SignExtend(
    input [15:0] immediate,    // 16位立即数
    input [1:0] ExOP,          // 扩展操作控制
    output reg [31:0] extended  // 32位扩展结果
);

always @(*) begin
    case(ExOP)
        2'b00: extended = {16'b0, immediate};           // 零扩展
        2'b01: extended = {{16{immediate[15]}}, immediate}; // 符号扩展
        2'b10: extended = {immediate, 16'b0};           // 左移16位
        default: extended = {16'b0, immediate};         // 默认零扩展
    endcase
end

endmodule

// 单周期处理器模块
module SingleCycleProcessor(
    input clk,                  // 时钟信号
    input reset,               // 复位信号
    output [29:0] pc,          // 程序计数器
    output [31:0] instru,      // 当前指令
    output [31:0] busA,        // 寄存器A总线
    output [31:0] busB,        // 寄存器B总线
    output [31:0] DataOut,     // 数据存储器输出
    output [31:0] busOut,      // ALU输出总线
    output [31:0] Result,      // 最终结果
    output Zero,               // 零标志
    output Branch,             // 分支信号
    output Jump,               // 跳转信号
    output [2:0] AluCtr        // ALU控制信号
);

// 内部连线定义
wire [5:0] opcode, funct;
wire [4:0] rs, rt, rd, shamt;
wire [15:0] immediate;
wire [25:0] jump_target;

// 控制信号
wire RegWr, ALUSrc, MemWr, MemtoReg, RegDst;
wire [1:0] ExOP;

// ALU相关信号
wire [31:0] ALUResult;
wire ALUZero, ALUOverflow, ALUNegative;

// 其他内部信号
wire [31:0] extended_immediate;
wire [31:0] ALUInputB;
wire [4:0] WriteReg;
wire [31:0] MemToRegData;
wire PCSrc;
wire [29:0] PCPlus4, BranchTarget, NextPC;
wire [27:0] jump_address_shifted;

// 指令解码
assign opcode = instru[31:26];
assign rs = instru[25:21];
assign rt = instru[20:16];
assign rd = instru[15:11];
assign shamt = instru[10:6];
assign funct = instru[5:0];
assign immediate = instru[15:0];
assign jump_target = instru[25:0];

// 取指令模块实例化
assign jump_address_word = {PCPlus4[29:26], jump_target};
instruction_fetch IF(
    .clk(clk),
    .reset(reset),
    .jump_en(Jump),
    .jump_addr(jump_address_word), // 跳转地址（已左移2位）
    .instruction(instru),
    .pc(pc)
);

// 控制器实例化
Controller CTRL(
    .op(opcode),
    .func(funct),
    .RegWr(RegWr),
    .Branch(Branch),
    .Jump(Jump),
    .ExOP(ExOP),
    .ALUSrc(ALUSrc),
    .ALUCtr(AluCtr),
    .MemWr(MemWr),
    .MemtoReg(MemtoReg),
    .RegDst(RegDst)
);

// 寄存器文件实例化
Register32 REG_FILE(
    .clk(clk),
    .wr(RegWr),
    .Ra(rs),
    .Rb(rt),
    .Rw(WriteReg),
    .busW(MemToRegData),
    .busA(busA),
    .busB(busB)
);

// 符号扩展实例化
SignExtend SIGN_EXT(
    .immediate(immediate),
    .ExOP(ExOP),
    .extended(extended_immediate)
);

// ALU输入B的多路选择器
assign ALUInputB = ALUSrc ? extended_immediate : busB;

// ALU实例化（使用文档3中的alu模块）
alu #(32) ALU(
    .a(busA),
    .b(ALUInputB),
    .opcode(AluCtr),
    .cin(1'b0),
    .result(ALUResult),
    .cout(), // 未使用
    .zero(ALUZero),
    .negative(ALUNegative),
    .overflow(ALUOverflow)
);

assign busOut = ALUResult;
assign Zero = ALUZero;

// 数据存储器实例化
DataMemory DATA_MEM(
    .WrEn(MemWr),
    .Clk(clk),
    .DataIn(busB),
    .Adr(ALUResult[6:2]), // 使用ALU结果的低位作为地址
    .DataOut(DataOut)
);

// 写回数据多路选择器
assign MemToRegData = MemtoReg ? DataOut : ALUResult;

// 目标寄存器多路选择器
assign WriteReg = RegDst ? rd : rt;

// 下一条PC计算逻辑
assign PCPlus4 = pc + 1; // 注意：pc是字地址，+1相当于+4字节

// 分支目标地址计算（PC+4 + 符号扩展立即数左移2位）
wire [31:0] extended_immediate_shifted = {extended_immediate[29:0], 2'b00};
assign BranchTarget = PCPlus4 + extended_immediate_shifted[31:2];

// 跳转地址计算（左移2位）
assign jump_address_shifted = {PCPlus4[29:28], jump_target, 2'b00}; 
// 分支条件
assign PCSrc = Branch & Zero;

// 下一条PC选择
assign NextPC = PCSrc ? BranchTarget : 
               Jump ? jump_address_word : 
               PCPlus4;

// 最终结果输出
assign Result = MemToRegData;

endmodule

