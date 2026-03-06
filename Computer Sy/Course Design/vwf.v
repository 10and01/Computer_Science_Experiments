//=============================================================================
// 简化版MIPS流水线处理器 (8个寄存器输出)
// 适合FPGA演示，减少I/O资源使用
//=============================================================================
module mips_pipeline_vwf (
    input         clk, reset,           // 时钟和复位信号
    output [31:0] o_pc_current,         // 当前PC值输出
    output [31:0] o_instruction,        // 当前指令输出
    output [31:0] o_alu_result,         // ALU运算结果输出
    output [31:0] o_reg0, o_reg1, o_reg2, o_reg3,  // 寄存器0-3输出
    output [31:0] o_reg4, o_reg5, o_reg6, o_reg7,  // 寄存器4-7输出
    output [4:0]  o_write_reg,          // 写回寄存器地址输出
    output        o_reg_write,          // 寄存器写使能输出
    output        o_pc_write,           // PC写使能输出（用于冒险控制）
    output        o_if_id_write,        // IF/ID流水线寄存器写使能输出
    output [5:0]  o_debug_bus           // 调试总线[stall, flush, forwardB, forwardA]
);

    //=========================================================================
    // 内部信号声明
    //=========================================================================
    wire [31:0] pc_current, instruction, alu_result;  // 流水线内部信号
    wire [1:0]  forwardA, forwardB;                   // 前递控制信号
    wire        stall, flush;                         // 冒险和冲刷控制信号
    wire [4:0]  mem_wb_write_reg;                     // MEM/WB阶段的写寄存器地址
    wire        mem_wb_reg_write;                     // MEM/WB阶段的寄存器写使能
    wire        pc_write, if_id_write;                // 流水线控制信号
    wire [31:0] reg_vals [0:31];                      // 32个寄存器值数组
    
    // 调试总线定义：将关键控制信号打包输出
    wire [5:0] debug_bus = {stall, flush, forwardB, forwardA};
    
    //=========================================================================
    // 核心模块实例化
    //=========================================================================
    mips_pipeline_core_simple core (
        .clk(clk), .reset(reset),
        .pc_current(pc_current), 
        .instruction(instruction), 
        .alu_result(alu_result),
        .forwardA(forwardA), 
        .forwardB(forwardB), 
        .stall(stall), 
        .flush(flush),
        .pc_write(pc_write), 
        .if_id_write(if_id_write),
        .reg_out0(reg_vals[0]), .reg_out1(reg_vals[1]), 
        .reg_out2(reg_vals[2]), .reg_out3(reg_vals[3]),
        .reg_out4(reg_vals[4]), .reg_out5(reg_vals[5]), 
        .reg_out6(reg_vals[6]), .reg_out7(reg_vals[7]),
        .mem_wb_write_reg(mem_wb_write_reg), 
        .mem_wb_reg_write(mem_wb_reg_write)
    );
    
    //=========================================================================
    // 输出信号连接
    //=========================================================================
    assign o_pc_current = pc_current;
    assign o_instruction = instruction;
    assign o_alu_result = alu_result;
    
    assign o_reg0 = reg_vals[0];
    assign o_reg1 = reg_vals[1];
    assign o_reg2 = reg_vals[2];
    assign o_reg3 = reg_vals[3];
    assign o_reg4 = reg_vals[4];
    assign o_reg5 = reg_vals[5];
    assign o_reg6 = reg_vals[6];
    assign o_reg7 = reg_vals[7];
    
    assign o_write_reg = mem_wb_write_reg;
    assign o_reg_write = mem_wb_reg_write;
    assign o_pc_write = pc_write;
    assign o_if_id_write = if_id_write;
    assign o_debug_bus = debug_bus;

endmodule

//=============================================================================
// 核心流水线模块
// 只输出前8个寄存器，减少资源使用
//=============================================================================
module mips_pipeline_core_simple (
    input         clk, reset,
    output [31:0] pc_current, instruction, alu_result,  // 流水线输出
    output [1:0]  forwardA, forwardB,                   // 前递控制输出
    output        stall, flush,                         // 冒险控制输出
    output        pc_write, if_id_write,                // 流水线控制输出
    // 只输出前8个寄存器
    output [31:0] reg_out0, reg_out1, reg_out2, reg_out3,
    output [31:0] reg_out4, reg_out5, reg_out6, reg_out7,
    output [4:0]  mem_wb_write_reg,      // MEM/WB阶段写寄存器地址
    output        mem_wb_reg_write       // MEM/WB阶段寄存器写使能
);

    //=========================================================================
    // 流水线寄存器声明
    //=========================================================================
    
    // IF/ID流水线寄存器
    reg [31:0] IF_ID_PC, IF_ID_Instr;    // 保存IF阶段的PC和指令
    reg        IF_ID_valid;              // IF/ID流水线寄存器有效标志
    
    // ID/EX流水线寄存器
    reg [31:0] ID_EX_PC, ID_EX_R1, ID_EX_R2, ID_EX_Imm;  // PC、源寄存器值、立即数
    reg [4:0]  ID_EX_Rs, ID_EX_Rt, ID_EX_Rd;             // 寄存器地址
    reg        ID_EX_valid;                              // 有效标志
    reg        ID_EX_RegDst, ID_EX_ALUSrc, ID_EX_MemRead, ID_EX_MemWrite;  // 控制信号
    reg        ID_EX_RegWrite, ID_EX_MemtoReg, ID_EX_Branch, ID_EX_Jump, ID_EX_Jal;
    reg [3:0]  ID_EX_ALUOp;               // ALU操作码
    
    // EX/MEM流水线寄存器
    reg [31:0] EX_MEM_ALU, EX_MEM_WData;  // ALU结果和要写入内存的数据
    reg [4:0]  EX_MEM_WReg;               // 写寄存器地址
    reg        EX_MEM_Zero;               // ALU零标志（用于分支判断）
    reg        EX_MEM_MemRead, EX_MEM_MemWrite, EX_MEM_RegWrite;  // 控制信号
    reg        EX_MEM_MemtoReg, EX_MEM_Branch, EX_MEM_Jump, EX_MEM_Jal;
    reg [31:0] EX_MEM_BranchTarget, EX_MEM_JumpTarget, EX_MEM_PC_plus_4;  // 目标地址
    
    // MEM/WB流水线寄存器
    reg [31:0] MEM_WB_Data;               // 写回数据
    reg [4:0]  MEM_WB_Reg;                // 写寄存器地址
    reg        MEM_WB_RegWrite, MEM_WB_MemtoReg, MEM_WB_Jal;  // 控制信号
    
    // 输出连接
    assign mem_wb_write_reg = MEM_WB_Reg;
    assign mem_wb_reg_write = MEM_WB_RegWrite;

    //=========================================================================
    // 存储器定义
    //=========================================================================
    reg [31:0] instr_mem [0:31];  // 32条指令的指令存储器
    reg [31:0] data_mem  [0:31];  // 32个字的数据存储器
    reg [31:0] registers [0:31];  // 32个寄存器文件
    
    // 只输出前8个寄存器
    assign reg_out0 = registers[0];
    assign reg_out1 = registers[1];
    assign reg_out2 = registers[2];
    assign reg_out3 = registers[3];
    assign reg_out4 = registers[4];
    assign reg_out5 = registers[5];
    assign reg_out6 = registers[6];
    assign reg_out7 = registers[7];
    
    //=========================================================================
    // 存储器初始化
    //=========================================================================
    integer i;
    initial begin
        // 初始化所有寄存器、数据存储器为0
        for (i=0; i<8; i=i+1) begin 
            registers[i]=0; 
            data_mem[i]=0; 
        end
        
        // 数据存储器预初始化
        data_mem[0] = 32'd13;  // 内存地址0存储值13
        
        // 指令存储器预初始化 - 测试程序
        // 程序功能：计算一系列算术运算，验证流水线功能
        instr_mem[0] = 32'h20010005;  // addi $1, $0, 5    ($1=5)
        instr_mem[1] = 32'h20220003;  // addi $2, $1, 3    ($2=5+3=8)
        instr_mem[2] = 32'h00221820;  // add  $3, $1, $2   ($3=5+8=13)
        instr_mem[3] = 32'hac030000;  // sw   $3, 0($0)    (Mem[0]=13)
        instr_mem[4] = 32'h8c040000;  // lw   $4, 0($0)    ($4=13)
        instr_mem[5] = 32'h00812820;  // add  $5, $4, $1   ($5=13+5=18)
        instr_mem[6] = 32'h2086000A;  // addi $6, $4, 10   ($6=13+10=23)
        instr_mem[7] = 32'h00c23822;  // sub  $7, $6, $2   ($7=23-8=15)
    end

    //=========================================================================
    // IF阶段 (Instruction Fetch) - 取指令
    //=========================================================================
    reg [31:0] PC;                        // 程序计数器
    wire [31:0] PC_plus_4 = PC + 4;       // PC+4计算（顺序下一条指令）
    
    // 下一条PC选择逻辑
    wire [31:0] next_PC;
    wire branch_taken = EX_MEM_Branch && EX_MEM_Zero;  // 分支条件满足
    wire jump_taken = EX_MEM_Jump || EX_MEM_Jal;       // 跳转条件满足
    
    // 多路选择器：分支->跳转->PC+4
    wire [31:0] branch_next_PC = branch_taken ? EX_MEM_BranchTarget : PC_plus_4;
    wire [31:0] jump_next_PC = jump_taken ? EX_MEM_JumpTarget : branch_next_PC;
    
    // PC更新逻辑
    always @(posedge clk or posedge reset) begin
        if (reset) 
            PC <= 0;                      // 复位时PC归零
        else if (pc_write)                // 冒险控制：暂停时停止PC更新
            PC <= jump_next_PC;           // 更新PC
    end
    
    // 冒险控制信号
    assign pc_write = ~stall;             // 暂停时停止PC更新
    assign if_id_write = ~stall;          // 暂停时停止IF/ID流水线寄存器更新
    
    // IF/ID流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin                  // 复位初始化
            IF_ID_PC <= 0;
            IF_ID_Instr <= 0;
            IF_ID_valid <= 0;
        end
        else if (flush) begin             // 冲刷流水线（分支/跳转时）
            IF_ID_PC <= 0;
            IF_ID_Instr <= 0;
            IF_ID_valid <= 0;
        end
        else if (if_id_write) begin       // 正常流水线推进
            IF_ID_PC <= PC;
            IF_ID_Instr <= instr_mem[PC[6:2]];  // 指令存储器读取（地址以字为单位）
            IF_ID_valid <= 1;
        end
    end
    
    // 冲刷条件：分支或跳转成功时需要冲刷IF/ID流水线寄存器
    assign flush = branch_taken || jump_taken;

    //=========================================================================
    // ID阶段 (Instruction Decode) - 指令译码
    //=========================================================================
    
    // 指令字段分解
    wire [5:0] opcode = IF_ID_Instr[31:26];    // 操作码
    wire [4:0] rs = IF_ID_Instr[25:21];        // 源寄存器1地址
    wire [4:0] rt = IF_ID_Instr[20:16];        // 源寄存器2地址/目标寄存器地址
    wire [4:0] rd = IF_ID_Instr[15:11];        // 目标寄存器地址
    wire [5:0] funct = IF_ID_Instr[5:0];       // 功能码（R型指令）
    wire [15:0] immediate = IF_ID_Instr[15:0]; // 立即数字段
    
    // 控制单元 - 生成流水线控制信号
    reg ctrl_RegDst, ctrl_ALUSrc, ctrl_MemRead, ctrl_MemWrite;
    reg ctrl_RegWrite, ctrl_MemtoReg, ctrl_Branch, ctrl_Jump, ctrl_Jal;
    reg [3:0] ctrl_ALUOp;
    
    always @(*) begin
        // 默认值（防止锁存器）
        ctrl_RegDst=0; ctrl_ALUSrc=0; ctrl_ALUOp=0;
        ctrl_MemRead=0; ctrl_MemWrite=0; ctrl_RegWrite=0;
        ctrl_MemtoReg=0; ctrl_Branch=0; ctrl_Jump=0; ctrl_Jal=0;
        
        case (opcode)
            6'b000000: begin  // R型指令
                ctrl_RegDst=1; ctrl_RegWrite=1;
                case (funct)   // 根据功能码确定ALU操作
                    6'b100000: ctrl_ALUOp = 4'b0010; // add
                    6'b100010: ctrl_ALUOp = 4'b0110; // sub
                    6'b100100: ctrl_ALUOp = 4'b0000; // and
                    6'b100101: ctrl_ALUOp = 4'b0001; // or
                    6'b101010: ctrl_ALUOp = 4'b0111; // slt
                    6'b001000: ctrl_Jump=1; // jr (特殊处理，实际未实现完整)
                    default:   ctrl_ALUOp = 4'b0010;
                endcase
            end
            6'b001000: begin  // addi
                ctrl_ALUSrc=1; ctrl_RegWrite=1; ctrl_ALUOp=4'b0010;
            end
            6'b100011: begin  // lw
                ctrl_ALUSrc=1; ctrl_MemRead=1; ctrl_RegWrite=1; 
                ctrl_MemtoReg=1; ctrl_ALUOp=4'b0010;
            end
            6'b101011: begin  // sw
                ctrl_ALUSrc=1; ctrl_MemWrite=1; ctrl_ALUOp=4'b0010;
            end
            6'b000100: begin  // beq
                ctrl_Branch=1; ctrl_ALUOp=4'b0110;  // 减法比较
            end
            6'b000010: begin  // j
                ctrl_Jump=1;
            end
            6'b000011: begin  // jal
                ctrl_Jump=1; ctrl_Jal=1; ctrl_RegWrite=1;  // 跳转并链接
            end
            default: begin end  // 其他指令（空操作）
        endcase
    end
    
    // 寄存器文件读取（带WB前递）
    wire [31:0] reg_r1_raw = registers[rs];  // 直接从寄存器文件读取
    wire [31:0] reg_r2_raw = registers[rt];
    
    // WB前递检测：检查MEM/WB阶段是否有对当前指令源寄存器的写回
    wire wb_fwd_rs = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == rs);
    wire wb_fwd_rt = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == rt);
    
    // 寄存器读取数据（考虑WB前递）
    wire [31:0] rdata1 = wb_fwd_rs ? MEM_WB_Data : reg_r1_raw;
    wire [31:0] rdata2 = wb_fwd_rt ? MEM_WB_Data : reg_r2_raw;
    
    // 立即数处理
    wire [31:0] imm_ext = {{16{immediate[15]}}, immediate};  // 符号扩展
    wire [31:0] imm_ext_shifted = imm_ext << 2;              // 左移2位（用于地址计算）
    
    // 跳转地址计算
    wire [31:0] jump_target = {IF_ID_PC[31:28], IF_ID_Instr[25:0], 2'b00};
    
    // 分支地址计算
    wire [31:0] branch_target = IF_ID_PC + 4 + imm_ext_shifted;
    
    // 冒险检测
    wire load_use_stall = ID_EX_MemRead && ((ID_EX_Rt == rs) || (ID_EX_Rt == rt));  // 加载-使用冒险
    wire control_hazard = ctrl_Jump || ctrl_Jal || ctrl_Branch;  // 控制冒险
    assign stall = load_use_stall || (control_hazard && (branch_taken || jump_taken));  // 冒险暂停条件
    
    // ID/EX流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin  // 复位初始化
            {ID_EX_PC, ID_EX_R1, ID_EX_R2, ID_EX_Imm, ID_EX_Rs, ID_EX_Rt, ID_EX_Rd} <= 0;
            {ID_EX_valid, ID_EX_RegDst, ID_EX_ALUSrc, ID_EX_ALUOp, 
             ID_EX_MemRead, ID_EX_MemWrite, ID_EX_RegWrite, ID_EX_MemtoReg,
             ID_EX_Branch, ID_EX_Jump, ID_EX_Jal} <= 0;
        end else if (stall) begin  // 冒险暂停：插入气泡
            ID_EX_valid <= 0;
            // 关键控制信号置零，避免执行无效操作
            ID_EX_MemRead <= 0; ID_EX_MemWrite <= 0; ID_EX_RegWrite <= 0;
            ID_EX_Branch <= 0; ID_EX_Jump <= 0; ID_EX_Jal <= 0;
        end else begin  // 正常流水线推进
            // 传递数据和控制信号
            ID_EX_PC <= IF_ID_PC;
            ID_EX_R1 <= rdata1;
            ID_EX_R2 <= rdata2;
            ID_EX_Imm <= imm_ext;
            ID_EX_Rs <= rs;
            ID_EX_Rt <= rt;
            ID_EX_Rd <= rd;
            ID_EX_valid <= IF_ID_valid;
            
            // 传递控制信号
            ID_EX_RegDst <= ctrl_RegDst;
            ID_EX_ALUSrc <= ctrl_ALUSrc;
            ID_EX_ALUOp <= ctrl_ALUOp;
            ID_EX_MemRead <= ctrl_MemRead;
            ID_EX_MemWrite <= ctrl_MemWrite;
            ID_EX_RegWrite <= ctrl_RegWrite;
            ID_EX_MemtoReg <= ctrl_MemtoReg;
            ID_EX_Branch <= ctrl_Branch;
            ID_EX_Jump <= ctrl_Jump;
            ID_EX_Jal <= ctrl_Jal;
        end
    end

    //=========================================================================
    // EX阶段 (Execute) - 执行
    //=========================================================================
    
    // 转发单元（前递逻辑）
    wire ex_fwd_a = EX_MEM_RegWrite && (EX_MEM_WReg != 0) && (EX_MEM_WReg == ID_EX_Rs);  // EX/MEM前递
    wire ex_fwd_b = EX_MEM_RegWrite && (EX_MEM_WReg != 0) && (EX_MEM_WReg == ID_EX_Rt);
    
    wire mem_fwd_a = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == ID_EX_Rs) && !ex_fwd_a;  // MEM/WB前递
    wire mem_fwd_b = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == ID_EX_Rt) && !ex_fwd_b;
    
    // 前递控制信号输出（用于调试）
    assign forwardA = ex_fwd_a ? 2'b10 : (mem_fwd_a ? 2'b01 : 2'b00);  // 00=无前递,01=MEM/WB前递,10=EX/MEM前递
    assign forwardB = ex_fwd_b ? 2'b10 : (mem_fwd_b ? 2'b01 : 2'b00);
    
    // ALU输入选择（带前递）
    wire [31:0] alu_A_forwarded = ex_fwd_a ? EX_MEM_ALU :           // EX/MEM阶段前递
                                  (mem_fwd_a ? MEM_WB_Data : ID_EX_R1);  // MEM/WB阶段前递
    
    wire [31:0] alu_B_raw_forwarded = ex_fwd_b ? EX_MEM_ALU :
                                      (mem_fwd_b ? MEM_WB_Data : ID_EX_R2);
    
    wire [31:0] alu_B = ID_EX_ALUSrc ? ID_EX_Imm : alu_B_raw_forwarded;  // ALU第二个操作数选择：立即数或寄存器
    
    // ALU运算单元
    reg [31:0] alu_out;
    reg alu_zero;
    
    always @(*) begin
        case (ID_EX_ALUOp)  // 根据ALU操作码执行运算
            4'b0010: alu_out = alu_A_forwarded + alu_B;  // add/addi
            4'b0110: alu_out = alu_A_forwarded - alu_B;  // sub/beq
            4'b0000: alu_out = alu_A_forwarded & alu_B;  // and
            4'b0001: alu_out = alu_A_forwarded | alu_B;  // or
            4'b0111: alu_out = ($signed(alu_A_forwarded) < $signed(alu_B)) ? 32'b1 : 32'b0; // slt
            default: alu_out = 32'b0;  // 默认值
        endcase
        alu_zero = (alu_A_forwarded == alu_B_raw_forwarded);  // 用于beq判断
    end
    
    // 分支条件判断（beq指令使用）
    wire branch_condition = alu_zero;
    
    // 目标寄存器选择
    wire [4:0] ex_wreg = ID_EX_RegDst ? ID_EX_Rd :         // R型指令使用rd
                        (ID_EX_Jal ? 5'd31 : ID_EX_Rt);   // jal使用$31，否则使用rt
    
    // 分支地址计算
    wire [31:0] branch_target_ex = ID_EX_PC + 4 + (ID_EX_Imm << 2);
    
    // 跳转地址计算
    wire [31:0] jump_target_ex = {ID_EX_PC[31:28], {ID_EX_Imm[25:0], 2'b00}};
    
    // PC+4保存（用于jal指令的返回地址）
    wire [31:0] pc_plus_4_ex = ID_EX_PC + 4;
    
    // EX/MEM流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin  // 复位初始化
            EX_MEM_ALU <= 0;
            EX_MEM_WData <= 0;
            EX_MEM_WReg <= 0;
            EX_MEM_Zero <= 0;
            EX_MEM_MemRead <= 0;
            EX_MEM_MemWrite <= 0;
            EX_MEM_RegWrite <= 0;
            EX_MEM_MemtoReg <= 0;
            EX_MEM_Branch <= 0;
            EX_MEM_Jump <= 0;
            EX_MEM_Jal <= 0;
            EX_MEM_BranchTarget <= 0;
            EX_MEM_JumpTarget <= 0;
            EX_MEM_PC_plus_4 <= 0;
        end else begin  // 正常流水线推进
            EX_MEM_ALU <= alu_out;
            EX_MEM_WData <= alu_B_raw_forwarded;
            EX_MEM_WReg <= ex_wreg;
            EX_MEM_Zero <= branch_condition;
            EX_MEM_MemRead <= ID_EX_MemRead;
            EX_MEM_MemWrite <= ID_EX_MemWrite;
            EX_MEM_RegWrite <= ID_EX_RegWrite;
            EX_MEM_MemtoReg <= ID_EX_MemtoReg;
            EX_MEM_Branch <= ID_EX_Branch;
            EX_MEM_Jump <= ID_EX_Jump;
            EX_MEM_Jal <= ID_EX_Jal;
            EX_MEM_BranchTarget <= branch_target_ex;
            EX_MEM_JumpTarget <= jump_target_ex;
            EX_MEM_PC_plus_4 <= pc_plus_4_ex;
        end
    end

    //=========================================================================
    // MEM阶段 (Memory) - 内存访问
    //=========================================================================
    
    // 内存读取（load指令）
    wire [31:0] mem_rdata = EX_MEM_MemRead ? data_mem[EX_MEM_ALU[4:2]] : 0;  // 字对齐访问
    
    // 写回数据选择
    wire [31:0] wb_data_pre = EX_MEM_MemtoReg ? mem_rdata :      // lw指令：从内存读取
                             (EX_MEM_Jal ? EX_MEM_PC_plus_4 : EX_MEM_ALU);  // jal：返回地址，其他：ALU结果
    
    // 内存写入（store指令）
    always @(posedge clk) begin
        if (EX_MEM_MemWrite)
            data_mem[EX_MEM_ALU[4:2]] <= EX_MEM_WData;
    end
    
    // MEM/WB流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin  // 复位初始化
            MEM_WB_Data <= 0;
            MEM_WB_Reg <= 0;
            MEM_WB_RegWrite <= 0;
            MEM_WB_MemtoReg <= 0;
            MEM_WB_Jal <= 0;
        end else begin  // 正常流水线推进
            MEM_WB_Data <= wb_data_pre;
            MEM_WB_Reg <= EX_MEM_WReg;
            MEM_WB_RegWrite <= EX_MEM_RegWrite;
            MEM_WB_MemtoReg <= EX_MEM_MemtoReg;
            MEM_WB_Jal <= EX_MEM_Jal;
        end
    end

    //=========================================================================
    // WB阶段 (Write Back) - 写回
    //=========================================================================
    always @(posedge clk) begin
        if (MEM_WB_RegWrite && MEM_WB_Reg != 0)  // 寄存器写使能且目标不是$0
            registers[MEM_WB_Reg] <= MEM_WB_Data;
        registers[0] <= 0;  // $0寄存器始终为0（硬件约束）
    end

    //=========================================================================
    // 模块输出
    //=========================================================================
    assign pc_current = PC;              // 当前PC值
    assign instruction = IF_ID_Instr;    // 当前指令
    assign alu_result = EX_MEM_ALU;      // ALU结果

endmodule