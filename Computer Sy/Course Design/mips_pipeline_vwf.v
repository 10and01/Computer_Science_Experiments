//=============================================================================
// 简化版MIPS流水线处理器 (8个寄存器输出)
// 适合FPGA演示，减少I/O资源使用
//=============================================================================
module mips_pipeline_vwf (
    input         clk, reset,
    output [31:0] o_pc_current,
    output [31:0] o_instruction,
    output [31:0] o_alu_result,
    output [31:0] o_reg0, o_reg1, o_reg2, o_reg3,
    output [31:0] o_reg4, o_reg5, o_reg6, o_reg7,
    output [4:0]  o_write_reg,
    output        o_reg_write,
    output        o_pc_write,
    output        o_if_id_write,
    output [5:0]  o_debug_bus
);

    //=========================================================================
    // 内部信号声明
    //=========================================================================
    wire [31:0] pc_current, instruction, alu_result;
    wire [1:0]  forwardA, forwardB;
    wire        stall, flush;
    wire [4:0]  mem_wb_write_reg;
    wire        mem_wb_reg_write;
    wire        pc_write, if_id_write;
    wire [31:0] reg_vals [0:31];
    
    // 调试总线定义
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
    // 输出信号连接（只输出前8个寄存器）
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
// 简化版核心流水线模块
// 只输出前8个寄存器，减少资源使用
//=============================================================================
module mips_pipeline_core_simple (
    input         clk, reset,
    output [31:0] pc_current, instruction, alu_result,
    output [1:0]  forwardA, forwardB,
    output        stall, flush,
    output        pc_write, if_id_write,
    // 只输出前8个寄存器
    output [31:0] reg_out0, reg_out1, reg_out2, reg_out3,
    output [31:0] reg_out4, reg_out5, reg_out6, reg_out7,
    output [4:0]  mem_wb_write_reg,
    output        mem_wb_reg_write
);

    //=========================================================================
    // 流水线寄存器声明
    //=========================================================================
    
    // IF/ID流水线寄存器
    reg [31:0] IF_ID_PC, IF_ID_Instr;
    reg        IF_ID_valid;
    
    // ID/EX流水线寄存器
    reg [31:0] ID_EX_PC, ID_EX_R1, ID_EX_R2, ID_EX_Imm;
    reg [4:0]  ID_EX_Rs, ID_EX_Rt, ID_EX_Rd;
    reg        ID_EX_valid;
    reg        ID_EX_RegDst, ID_EX_ALUSrc, ID_EX_MemRead, ID_EX_MemWrite;
    reg        ID_EX_RegWrite, ID_EX_MemtoReg, ID_EX_Branch, ID_EX_Jump, ID_EX_Jal;
    reg [3:0]  ID_EX_ALUOp;
    
    // EX/MEM流水线寄存器
    reg [31:0] EX_MEM_ALU, EX_MEM_WData;
    reg [4:0]  EX_MEM_WReg;
    reg        EX_MEM_Zero, EX_MEM_MemRead, EX_MEM_MemWrite, EX_MEM_RegWrite;
    reg        EX_MEM_MemtoReg, EX_MEM_Branch, EX_MEM_Jump, EX_MEM_Jal;
    reg [31:0] EX_MEM_BranchTarget, EX_MEM_JumpTarget, EX_MEM_PC_plus_4;
    
    // MEM/WB流水线寄存器
    reg [31:0] MEM_WB_Data;
    reg [4:0]  MEM_WB_Reg;
    reg        MEM_WB_RegWrite, MEM_WB_MemtoReg, MEM_WB_Jal;
    
    // 输出连接
    assign mem_wb_write_reg = MEM_WB_Reg;
    assign mem_wb_reg_write = MEM_WB_RegWrite;

    //=========================================================================
    // 存储器定义
    //=========================================================================
    reg [31:0] instr_mem [0:31];  // 32条指令
    reg [31:0] data_mem  [0:31];  // 32个字数据内存
    reg [31:0] registers [0:31];  // 32个寄存器
    
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
        

			// 指令0: 初始化寄存器
        instr_mem[0] = 32'h20010001;  // addi $1, $0, 1     ($1=1)
        
        // 指令1: BEQ测试 - 相等时跳转
        instr_mem[1] = 32'h20020001;  // addi $2, $0, 1     ($2=1)
        // 此时 $1==$2==1
        
        // 指令2: BEQ指令 - 如果相等则跳过下一条指令
        instr_mem[2] = 32'h10220001;  // beq  $1, $2, 1     (如果$1==$2，跳转到地址3+1=4)
        // 这里应该跳转，跳过指令3
    
    // 程序执行预期结果：
    // 执行完8条指令后，各寄存器值应为：
    // $1 = 2   (证明BEQ跳转成功，执行了指令4的addi)
    // $2 = 1
    // $3 = 0   (因为J指令跳转，指令6被跳过)
    // $4 = 255 (程序结束)
	 
	 end

    //=========================================================================
    // IF阶段 (Instruction Fetch)
    //=========================================================================
    reg [31:0] PC;
    wire [31:0] PC_plus_4 = PC + 4;
    
    // 下一条PC选择逻辑
    wire [31:0] next_PC;
    wire branch_taken = EX_MEM_Branch && EX_MEM_Zero;
    wire jump_taken = EX_MEM_Jump || EX_MEM_Jal;
    
    wire [31:0] branch_next_PC = branch_taken ? EX_MEM_BranchTarget : PC_plus_4;
    wire [31:0] jump_next_PC = jump_taken ? EX_MEM_JumpTarget : branch_next_PC;
    
    // PC更新
    always @(posedge clk or posedge reset) begin
        if (reset) 
            PC <= 0;
        else if (pc_write)  // 冒险控制
            PC <= jump_next_PC;
    end
    
    // 冒险控制信号
    assign pc_write = ~stall;  // 暂停时停止PC更新
    assign if_id_write = ~stall;  // 暂停时停止IF/ID更新
    
    // IF/ID流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            IF_ID_PC <= 0;
            IF_ID_Instr <= 0;
            IF_ID_valid <= 0;
        end
        else if (flush) begin
            // 冲刷流水线（分支/跳转时）
            IF_ID_PC <= 0;
            IF_ID_Instr <= 0;
            IF_ID_valid <= 0;
        end
        else if (if_id_write) begin
            IF_ID_PC <= PC;
            IF_ID_Instr <= instr_mem[PC[6:2]];  // 地址以字为单位
            IF_ID_valid <= 1;
        end
    end
    
    // 冲刷条件：分支或跳转成功
    assign flush = branch_taken || jump_taken;

    //=========================================================================
    // ID阶段 (Instruction Decode)
    //=========================================================================
    
    // 指令字段分解
    wire [5:0] opcode = IF_ID_Instr[31:26];
    wire [4:0] rs = IF_ID_Instr[25:21];
    wire [4:0] rt = IF_ID_Instr[20:16];
    wire [4:0] rd = IF_ID_Instr[15:11];
    wire [5:0] funct = IF_ID_Instr[5:0];
    wire [15:0] immediate = IF_ID_Instr[15:0];
    
    // 控制单元
    reg ctrl_RegDst, ctrl_ALUSrc, ctrl_MemRead, ctrl_MemWrite;
    reg ctrl_RegWrite, ctrl_MemtoReg, ctrl_Branch, ctrl_Jump, ctrl_Jal;
    reg [3:0] ctrl_ALUOp;
    
    always @(*) begin
        // 默认值
        ctrl_RegDst=0; ctrl_ALUSrc=0; ctrl_ALUOp=0;
        ctrl_MemRead=0; ctrl_MemWrite=0; ctrl_RegWrite=0;
        ctrl_MemtoReg=0; ctrl_Branch=0; ctrl_Jump=0; ctrl_Jal=0;
        
        case (opcode)
            6'b000000: begin  // R型指令
                ctrl_RegDst=1; ctrl_RegWrite=1;
                case (funct)
                    6'b100000: ctrl_ALUOp = 4'b0010; // add
                    6'b100010: ctrl_ALUOp = 4'b0110; // sub
                    6'b100100: ctrl_ALUOp = 4'b0000; // and
                    6'b100101: ctrl_ALUOp = 4'b0001; // or
                    6'b101010: ctrl_ALUOp = 4'b0111; // slt
                    6'b001000: ctrl_Jump=1; // jr (特殊处理)
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
                ctrl_Branch=1; ctrl_ALUOp=4'b0110;
            end
            6'b000010: begin  // j
                ctrl_Jump=1;
            end
            6'b000011: begin  // jal
                ctrl_Jump=1; ctrl_Jal=1; ctrl_RegWrite=1;
            end
            default: begin end
        endcase
    end
    
    // 寄存器文件读取（带WB前递）
    wire [31:0] reg_r1_raw = registers[rs];
    wire [31:0] reg_r2_raw = registers[rt];
    
    // WB前递检测
    wire wb_fwd_rs = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == rs);
    wire wb_fwd_rt = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == rt);
    
    wire [31:0] rdata1 = wb_fwd_rs ? MEM_WB_Data : reg_r1_raw;
    wire [31:0] rdata2 = wb_fwd_rt ? MEM_WB_Data : reg_r2_raw;
    
    // 立即数处理
    wire [31:0] imm_ext = {{16{immediate[15]}}, immediate};
    wire [31:0] imm_ext_shifted = imm_ext << 2;
    
    // 跳转地址计算
    wire [31:0] jump_target = {IF_ID_PC[31:28], IF_ID_Instr[25:0], 2'b00};
    
    // 分支地址计算
    wire [31:0] branch_target = IF_ID_PC + 4 + imm_ext_shifted;
    
    // 冒险检测
    wire load_use_stall = ID_EX_MemRead && ((ID_EX_Rt == rs) || (ID_EX_Rt == rt));
    wire control_hazard = ctrl_Jump || ctrl_Jal || ctrl_Branch;
    assign stall = load_use_stall || (control_hazard && (branch_taken || jump_taken));
    
    // ID/EX流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            {ID_EX_PC, ID_EX_R1, ID_EX_R2, ID_EX_Imm, ID_EX_Rs, ID_EX_Rt, ID_EX_Rd} <= 0;
            {ID_EX_valid, ID_EX_RegDst, ID_EX_ALUSrc, ID_EX_ALUOp, 
             ID_EX_MemRead, ID_EX_MemWrite, ID_EX_RegWrite, ID_EX_MemtoReg,
             ID_EX_Branch, ID_EX_Jump, ID_EX_Jal} <= 0;
        end else if (stall) begin
            // 插入气泡
            ID_EX_valid <= 0;
            ID_EX_MemRead <= 0; ID_EX_MemWrite <= 0; ID_EX_RegWrite <= 0;
            ID_EX_Branch <= 0; ID_EX_Jump <= 0; ID_EX_Jal <= 0;
        end else begin
            ID_EX_PC <= IF_ID_PC;
            ID_EX_R1 <= rdata1;
            ID_EX_R2 <= rdata2;
            ID_EX_Imm <= imm_ext;
            ID_EX_Rs <= rs;
            ID_EX_Rt <= rt;
            ID_EX_Rd <= rd;
            ID_EX_valid <= IF_ID_valid;
            
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
    // EX阶段 (Execute)
    //=========================================================================
    
    // 转发单元
    wire ex_fwd_a = EX_MEM_RegWrite && (EX_MEM_WReg != 0) && (EX_MEM_WReg == ID_EX_Rs);
    wire ex_fwd_b = EX_MEM_RegWrite && (EX_MEM_WReg != 0) && (EX_MEM_WReg == ID_EX_Rt);
    
    wire mem_fwd_a = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == ID_EX_Rs) && !ex_fwd_a;
    wire mem_fwd_b = MEM_WB_RegWrite && (MEM_WB_Reg != 0) && (MEM_WB_Reg == ID_EX_Rt) && !ex_fwd_b;
    
    assign forwardA = ex_fwd_a ? 2'b10 : (mem_fwd_a ? 2'b01 : 2'b00);
    assign forwardB = ex_fwd_b ? 2'b10 : (mem_fwd_b ? 2'b01 : 2'b00);
    
    // ALU输入选择（带转发）
    wire [31:0] alu_A_forwarded = ex_fwd_a ? EX_MEM_ALU :
                                  (mem_fwd_a ? MEM_WB_Data : ID_EX_R1);
    
    wire [31:0] alu_B_raw_forwarded = ex_fwd_b ? EX_MEM_ALU :
                                      (mem_fwd_b ? MEM_WB_Data : ID_EX_R2);
    
    wire [31:0] alu_B = ID_EX_ALUSrc ? ID_EX_Imm : alu_B_raw_forwarded;
    
    // ALU运算
    reg [31:0] alu_out;
    reg alu_zero;
    
    always @(*) begin
        case (ID_EX_ALUOp)
            4'b0010: alu_out = alu_A_forwarded + alu_B;  // add/addi
            4'b0110: alu_out = alu_A_forwarded - alu_B;  // sub/beq
            4'b0000: alu_out = alu_A_forwarded & alu_B;  // and
            4'b0001: alu_out = alu_A_forwarded | alu_B;  // or
            4'b0111: alu_out = ($signed(alu_A_forwarded) < $signed(alu_B)) ? 32'b1 : 32'b0; // slt
            default: alu_out = 32'b0;
        endcase
        alu_zero = (alu_A_forwarded == alu_B_raw_forwarded);
    end
    
    // 分支条件判断
    wire branch_condition = alu_zero;
    
    // 目标寄存器选择
    wire [4:0] ex_wreg = ID_EX_RegDst ? ID_EX_Rd : 
                        (ID_EX_Jal ? 5'd31 : ID_EX_Rt);
    
    // 分支地址计算
    wire [31:0] branch_target_ex = ID_EX_PC + 4 + (ID_EX_Imm << 2);
    
    // 跳转地址计算
    wire [31:0] jump_target_ex = {ID_EX_PC[31:28], {ID_EX_Imm[25:0], 2'b00}};
    
    // PC+4保存（用于jal指令）
    wire [31:0] pc_plus_4_ex = ID_EX_PC + 4;
    
    // EX/MEM流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin
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
        end else begin
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
    // MEM阶段 (Memory)
    //=========================================================================
    
    // 内存访问
    wire [31:0] mem_rdata = EX_MEM_MemRead ? data_mem[EX_MEM_ALU[4:2]] : 0;
    
    // 写回数据选择
    wire [31:0] wb_data_pre = EX_MEM_MemtoReg ? mem_rdata : 
                             (EX_MEM_Jal ? EX_MEM_PC_plus_4 : EX_MEM_ALU);
    
    // 内存写入
    always @(posedge clk) begin
        if (EX_MEM_MemWrite)
            data_mem[EX_MEM_ALU[4:2]] <= EX_MEM_WData;
    end
    
    // MEM/WB流水线寄存器更新
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            MEM_WB_Data <= 0;
            MEM_WB_Reg <= 0;
            MEM_WB_RegWrite <= 0;
            MEM_WB_MemtoReg <= 0;
            MEM_WB_Jal <= 0;
        end else begin
            MEM_WB_Data <= wb_data_pre;
            MEM_WB_Reg <= EX_MEM_WReg;
            MEM_WB_RegWrite <= EX_MEM_RegWrite;
            MEM_WB_MemtoReg <= EX_MEM_MemtoReg;
            MEM_WB_Jal <= EX_MEM_Jal;
        end
    end

    //=========================================================================
    // WB阶段 (Write Back)
    //=========================================================================
    always @(posedge clk) begin
        if (MEM_WB_RegWrite && MEM_WB_Reg != 0)
            registers[MEM_WB_Reg] <= MEM_WB_Data;
        registers[0] <= 0;  // $0寄存器始终为0
    end

    //=========================================================================
    // 模块输出
    //=========================================================================
    assign pc_current = PC;
    assign instruction = IF_ID_Instr;
    assign alu_result = EX_MEM_ALU;

endmodule
