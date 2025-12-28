module Controller(
    input [5:0] op,     // 操作码
    input [5:0] func,   // 功能码
    output reg RegWr,    // 寄存器写使能
    output reg Branch,   // 分支指令
    output reg Jump,     // 跳转指令
    output reg [1:0] ExOP,  // 扩展操作
    output reg ALUSrc,   // ALU源选择
    output reg [2:0] ALUCtr, // ALU控制
    output reg MemWr,    // 内存写使能
    output reg MemtoReg, // 写回源选择
    output reg RegDst    // 目标寄存器选择
);

    // 操作码定义
    localparam OP_RTYPE = 6'b000000;  // R型指令
    localparam OP_ADDI  = 6'b001000;  // 加立即数
    localparam OP_LW    = 6'b100011;  // 加载字
    localparam OP_SW    = 6'b101011;  // 存储字
    localparam OP_BEQ   = 6'b000100;  // 相等分支
    localparam OP_J     = 6'b000010;  // 跳转
    localparam OP_ORI   = 6'b001101;  // 或立即数指令
    // 功能码定义
    localparam FUNC_ADD = 6'b100000;
    localparam FUNC_SUB = 6'b100010;
    localparam FUNC_AND = 6'b100100;
    localparam FUNC_OR  = 6'b100101;
    localparam FUNC_SLT = 6'b101010;

    // ALU控制编码
    localparam ALU_ADD  = 3'b000;
    localparam ALU_SUB  = 3'b001;
    localparam ALU_AND  = 3'b010;
    localparam ALU_OR   = 3'b011;  // 或操作
    localparam ALU_SLT  = 3'b110;

    // 扩展操作编码 
    localparam EX_NONE  = 2'b11;  // 不扩展
    localparam EX_SIGN  = 2'b01;  // 符号扩展
    localparam EX_ZERO  = 2'b00;  // 零扩展 

    always @(*) begin
        // 默认值
        RegWr    = 1'b0;
        Branch   = 1'b0;
        Jump     = 1'b0;
        ExOP     = EX_NONE;
        ALUSrc   = 1'b0;
        ALUCtr   = ALU_ADD;
        MemWr    = 1'b0;
        MemtoReg = 1'b0;
        RegDst   = 1'b0;
        
        case (op)
            OP_RTYPE: begin
                // R型指令
                RegWr = 1'b1;
                RegDst = 1'b1;
                
                case (func)
                    FUNC_ADD:  ALUCtr = ALU_ADD;
                    FUNC_SUB:  ALUCtr = ALU_SUB;
                    FUNC_AND:  ALUCtr = ALU_AND;
                    FUNC_OR:   ALUCtr = ALU_OR;
                    FUNC_SLT:  ALUCtr = ALU_SLT;
                    default:   ALUCtr = ALU_ADD;
                endcase
            end
            
            OP_ADDI: begin
                RegWr = 1'b1;
                ALUSrc = 1'b1;
                ExOP = EX_SIGN;
                ALUCtr = ALU_ADD;
            end
            
            // 新增ORI指令处理
            OP_ORI: begin
                RegWr = 1'b1;
                ALUSrc = 1'b1;
                ExOP = EX_ZERO;  // 零扩展
                ALUCtr = ALU_OR;  // 或操作
            end
            
            OP_LW: begin
                RegWr = 1'b1;
                ALUSrc = 1'b1;
                MemtoReg = 1'b1;
                ExOP = EX_SIGN;
                ALUCtr = ALU_ADD;
            end
            
            OP_SW: begin
                MemWr = 1'b1;
                ALUSrc = 1'b1;
                ExOP = EX_SIGN;
                ALUCtr = ALU_ADD;
            end
            
            OP_BEQ: begin
                Branch = 1'b1;
                ExOP = EX_SIGN;
                ALUCtr = ALU_SUB;
            end
            
            OP_J: begin
                Jump = 1'b1;
            end
            
            default: begin
                // 未定义指令
                RegWr    = 1'b0;
                Branch   = 1'b0;
                Jump     = 1'b0;
                ExOP     = EX_NONE;
                ALUSrc   = 1'b0;
                ALUCtr   = ALU_ADD;
                MemWr    = 1'b0;
                MemtoReg = 1'b0;
                RegDst   = 1'b0;
            end
        endcase
    end
endmodule