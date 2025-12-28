// 11条指令的单周期处理器数据通路
// 支持的指令：
// 1. ADD: 加法
// 2. SUB: 减法
// 3. AND: 与运算
// 4. OR:  或运算
// 5. SLT: 小于则置位
// 6. ADDI: 加立即数
// 7. LW:   加载字
// 8. SW:   存储字
// 9. BEQ:  相等分支
// 10. BNE: 不等分支
// 11. J:   无条件跳转
module datapath(
    input clk,
    input reset,
    input [31:0] instruction,
    output [31:0] pc,
    output [31:0] alu_result,
    output [31:0] mem_write_data,
    output mem_write_enable,
    output mem_read_enable
);

    // 指令字段解码
    wire [5:0] opcode = instruction[31:26];
    wire [4:0] rs = instruction[25:21];
    wire [4:0] rt = instruction[20:16];
    wire [4:0] rd = instruction[15:11];
    wire [4:0] shamt = instruction[10:6];
    wire [5:0] funct = instruction[5:0];
    wire [15:0] immediate = instruction[15:0];
    wire [25:0] target = instruction[25:0];

    // 控制信号
    wire reg_dst;        // 选择写入寄存器
    wire branch;         // 分支指令
    wire mem_read;       // 内存读
    wire mem_to_reg;     // 内存到寄存器
    wire [2:0] alu_op;   // ALU操作码
    wire mem_write;      // 内存写
    wire alu_src;        // ALU源选择
    wire reg_write;      // 寄存器写使能
    wire jump;           // 跳转指令
    wire bne;            // 不相等分支

    // 数据通路内部信号
    wire [31:0] pc_plus_4;
    wire [31:0] pc_next;
    wire [31:0] pc_branch;
    wire [31:0] pc_jump;
    wire [31:0] sign_ext_imm;
    wire [31:0] alu_src_b;
    wire [31:0] reg_write_data;
    wire [31:0] reg_data1;
    wire [31:0] reg_data2;
    wire [4:0] write_reg;
    wire alu_zero;
    wire pc_src;
    wire [31:0] alu_result_internal;
    wire [31:0] mem_read_data_internal;  // 内存读取数据内部信号

    // 控制单元
    ControlUnit ctrl_unit(
        .opcode(opcode),
        .reg_dst(reg_dst),
        .branch(branch),
        .mem_read(mem_read),
        .mem_to_reg(mem_to_reg),
        .alu_op(alu_op),
        .mem_write(mem_write),
        .alu_src(alu_src),
        .reg_write(reg_write),
        .jump(jump),
        .bne(bne)
    );

    // 程序计数器
    PC_Register pc_reg(
        .clk(clk),
        .reset(reset),
        .pc_next(pc_next),
        .pc(pc)
    );

    // PC+4计算
    assign pc_plus_4 = pc + 4;

    // 分支目标地址计算
    assign pc_branch = pc_plus_4 + (sign_ext_imm << 2);

    // 跳转目标地址计算
    assign pc_jump = {pc_plus_4[31:28], target, 2'b00};

    // 下一条PC选择
    assign pc_src = (branch & alu_zero) | (bne & ~alu_zero);
    assign pc_next = jump ? pc_jump : (pc_src ? pc_branch : pc_plus_4);

    // 符号扩展
    assign sign_ext_imm = {{16{immediate[15]}}, immediate};

    // 寄存器文件
    RegisterFile reg_file(
        .clk(clk),
        .reg_write(reg_write),
        .read_reg1(rs),
        .read_reg2(rt),
        .write_reg(write_reg),
        .write_data(reg_write_data),
        .read_data1(reg_data1),
        .read_data2(reg_data2)
    );

    // 写入寄存器选择
    assign write_reg = reg_dst ? rd : rt;

    // ALU第二个操作数选择
    assign alu_src_b = alu_src ? sign_ext_imm : reg_data2;

    // ALU
    ALU alu(
        .a(reg_data1),
        .b(alu_src_b),
        .alu_op(alu_op),
        .funct(funct),
        .result(alu_result_internal),
        .zero(alu_zero)
    );

    // 数据存储器
    DataMemory data_memory(
        .clk(clk),
        .mem_write(mem_write),
        .mem_read(mem_read),
        .address(alu_result_internal),  // 使用ALU结果作为内存地址
        .write_data(reg_data2),         // 寄存器数据2作为写入数据
        .read_data(mem_read_data_internal)  // 内部读取数据
    );

    // 写入寄存器数据选择
    assign reg_write_data = mem_to_reg ? mem_read_data_internal : alu_result_internal;

    // 输出连接
    assign alu_result = alu_result_internal;
    assign mem_write_data = reg_data2;
    assign mem_write_enable = mem_write;
    assign mem_read_enable = mem_read;

endmodule

// 控制单元
module ControlUnit(
    input [5:0] opcode,
    output reg reg_dst,
    output reg branch,
    output reg mem_read,
    output reg mem_to_reg,
    output reg [2:0] alu_op,
    output reg mem_write,
    output reg alu_src,
    output reg reg_write,
    output reg jump,
    output reg bne
);

    // 操作码定义
    localparam R_TYPE = 6'b000000;
    localparam LW     = 6'b100011;
    localparam SW     = 6'b101011;
    localparam ADDI   = 6'b001000;
    localparam BEQ    = 6'b000100;
    localparam BNE    = 6'b000101;
    localparam J      = 6'b000010;

    // ALU操作码
    localparam ALU_ADD  = 3'b010;
    localparam ALU_SUB  = 3'b110;
    localparam ALU_AND  = 3'b000;
    localparam ALU_OR   = 3'b001;
    localparam ALU_SLT  = 3'b111;
    localparam ALU_RTYPE = 3'b100;  // R-type指令

    always @(*) begin
        // 默认值
        reg_dst = 1'b0;
        branch = 1'b0;
        mem_read = 1'b0;
        mem_to_reg = 1'b0;
        alu_op = ALU_ADD;
        mem_write = 1'b0;
        alu_src = 1'b0;
        reg_write = 1'b0;
        jump = 1'b0;
        bne = 1'b0;

        case (opcode)
            R_TYPE: begin
                reg_dst = 1'b1;
                reg_write = 1'b1;
                alu_op = ALU_RTYPE;
            end
            LW: begin
                alu_src = 1'b1;
                mem_to_reg = 1'b1;
                reg_write = 1'b1;
                mem_read = 1'b1;
                alu_op = ALU_ADD;
            end
            SW: begin
                alu_src = 1'b1;
                mem_write = 1'b1;
                alu_op = ALU_ADD;
            end
            ADDI: begin
                alu_src = 1'b1;
                reg_write = 1'b1;
                alu_op = ALU_ADD;
            end
            BEQ: begin
                branch = 1'b1;
                alu_op = ALU_SUB;
            end
            BNE: begin
                bne = 1'b1;
                alu_op = ALU_SUB;
            end
            J: begin
                jump = 1'b1;
            end
            default: begin
                // 保持默认值
            end
        endcase
    end
endmodule

// ALU控制单元
module ALUControl(
    input [2:0] alu_op,
    input [5:0] funct,
    output reg [3:0] alu_control
);

    // ALU控制信号
    localparam ALU_AND  = 4'b0000;
    localparam ALU_OR   = 4'b0001;
    localparam ALU_ADD  = 4'b0010;
    localparam ALU_SUB  = 4'b0110;
    localparam ALU_SLT  = 4'b0111;
    localparam ALU_NOR  = 4'b1100;

    // 功能码定义
    localparam FUNCT_ADD = 6'b100000;
    localparam FUNCT_SUB = 6'b100010;
    localparam FUNCT_AND = 6'b100100;
    localparam FUNCT_OR  = 6'b100101;
    localparam FUNCT_SLT = 6'b101010;

    always @(*) begin
        case (alu_op)
            3'b010: alu_control = ALU_ADD;  // lw, sw, addi
            3'b110: alu_control = ALU_SUB;  // beq, bne
            3'b100: begin  // R-type指令
                case (funct)
                    FUNCT_ADD: alu_control = ALU_ADD;
                    FUNCT_SUB: alu_control = ALU_SUB;
                    FUNCT_AND: alu_control = ALU_AND;
                    FUNCT_OR:  alu_control = ALU_OR;
                    FUNCT_SLT: alu_control = ALU_SLT;
                    default:   alu_control = ALU_ADD;
                endcase
            end
            default: alu_control = ALU_ADD;
        endcase
    end
endmodule

// ALU
module ALU(
    input [31:0] a,
    input [31:0] b,
    input [2:0] alu_op,
    input [5:0] funct,
    output reg [31:0] result,
    output reg zero
);

    wire [3:0] alu_ctrl;
    
    ALUControl alu_ctrl_unit(
        .alu_op(alu_op),
        .funct(funct),
        .alu_control(alu_ctrl)
    );

    always @(*) begin
        case (alu_ctrl)
            4'b0000: result = a & b;      // AND
            4'b0001: result = a | b;      // OR
            4'b0010: result = a + b;      // ADD
            4'b0110: result = a - b;      // SUB
            4'b0111: result = (a < b) ? 1 : 0;  // SLT
            4'b1100: result = ~(a | b);   // NOR
            default: result = a + b;      // 默认加法
        endcase
        
        zero = (result == 0) ? 1'b1 : 1'b0;
    end
endmodule

// 寄存器文件 - 同步读取
module RegisterFile(
    input clk,
    input reg_write,
    input [4:0] read_reg1,
    input [4:0] read_reg2,
    input [4:0] write_reg,
    input [31:0] write_data,
    output reg [31:0] read_data1,
    output reg [31:0] read_data2
);

    // 使用FPGA的RAM块
    (* ramstyle = "logic" *) reg [31:0] registers [31:0];
    
    // 初始化寄存器
    integer i;
    initial begin
        for (i = 0; i < 32; i = i + 1)
            registers[i] = 0;
        // 设置一些初始值用于测试
        registers[0] = 0;   // $zero
        registers[1] = 1;   // $at
        registers[2] = 2;   // $v0
        registers[3] = 3;   // $v1
        registers[4] = 4;   // $a0
        registers[5] = 5;   // $a1
    end
    
    // 同步读
    always @(posedge clk) begin
        if (read_reg1 == 0)
            read_data1 <= 32'b0;
        else
            read_data1 <= registers[read_reg1];
            
        if (read_reg2 == 0)
            read_data2 <= 32'b0;
        else
            read_data2 <= registers[read_reg2];
    end
    
    // 同步写
    always @(posedge clk) begin
        if (reg_write && write_reg != 0) begin
            registers[write_reg] <= write_data;
        end
    end
endmodule

// 程序计数器
module PC_Register(
    input clk,
    input reset,
    input [31:0] pc_next,
    output reg [31:0] pc
);

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            pc <= 32'b0;
        end else begin
            pc <= pc_next;
        end
    end
endmodule

// 数据存储器
module DataMemory(
    input clk,
    input mem_write,
    input mem_read,
    input [31:0] address,
    input [31:0] write_data,
    output reg [31:0] read_data
);

    (* ramstyle = "M9K, no_rw_check" *) reg [31:0] memory [0:255];
    
    // 初始化内存
    integer i;
    initial begin
        for (i = 0; i < 256; i = i + 1)
            memory[i] = i;
    end
    
    // 同步读
    always @(posedge clk) begin
        if (mem_read && address < 1024) begin
            read_data <= memory[address >> 2];
        end
    end
    
    // 同步写
    always @(posedge clk) begin
        if (mem_write && address < 1024) begin
            memory[address >> 2] <= write_data;
        end
    end
endmodule

// 指令存储器
module InstructionMemory(
    input clk,
    input [31:0] address,
    output reg [31:0] instruction
);

    (* ramstyle = "M9K, no_rw_check" *) reg [31:0] memory [0:255];
    
    // 同步读
    always @(posedge clk) begin
        if (address < 1024) begin
            instruction <= memory[address >> 2];
        end
    end
endmodule
