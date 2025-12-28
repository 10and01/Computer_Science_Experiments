// 修改指令存储器，支持30位字节地址
module instruction_memory(
    input [29:0] address,        // 改为32位字节地址
    output reg [31:0] instruction
);

reg [7:0] Memory [0:255];  // 仍然只使用前256字节
integer i;

// 初始化指令存储器
initial begin
    // 初始化所有内存为0
    for (i = 0; i < 256; i = i + 1) begin
        Memory[i] = 8'b0;
    end
    
    // 第1条指令: ADD $1, $2, $3 (地址0)
    {Memory[0], Memory[1], Memory[2], Memory[3]} = 32'b000000_00010_00011_00001_00000_100000;
    
    // 第2条指令: SUB $4, $5, $6 (地址4)  
    {Memory[4], Memory[5], Memory[6], Memory[7]} = 32'b000000_00101_00110_00100_00000_100010;
    
    // 第3条指令: BEQ $7, $8, 1 (地址8)
    {Memory[8], Memory[9], Memory[10], Memory[11]} = 32'b000100_00111_01000_0000000000000001;
    
    // 第4条指令: AND $9, $10, $11 (地址12)
    {Memory[12], Memory[13], Memory[14], Memory[15]} = 32'b000000_01010_01011_01001_00000_100100;
    
    // 第5条指令: OR $12, $13, $14 (地址16)
    {Memory[16], Memory[17], Memory[18], Memory[19]} = 32'b000000_01101_01110_01100_00000_100101;
    
    // 第6条指令: SLT $15, $16, $17 (地址20)
    {Memory[20], Memory[21], Memory[22], Memory[23]} = 32'b000000_10000_10001_01111_00000_101010;
    
    // 第7条指令: ADDI $18, $19, 255 (地址24)
    {Memory[24], Memory[25], Memory[26], Memory[27]} = 32'b001000_10011_10010_0000000011111111;
    
    // 第8条指令: LW $20, 8($21) (地址28)
    {Memory[28], Memory[29], Memory[30], Memory[31]} = 32'b100011_10101_10100_0000000000001000;
    
    // 第9条指令: SW $22, 4($23) (地址32)
    {Memory[32], Memory[33], Memory[34], Memory[35]} = 32'b101011_10111_10110_0000000000000100;
	 
	 // 第10指令: ORI $1, $2, 0x00FF (地址44)
    {Memory[36], Memory[37], Memory[38], Memory[39]} = 32'b001101_00010_00001_0000000011111111;
	 
    // 第11条指令: J 256 (地址40)
    {Memory[40], Memory[41], Memory[42], Memory[43]} = 32'b000010_00000000000000000100000000;
end

// 根据地址输出指令 - 只使用低8位地址
always @(*) begin
    // 只使用地址的低8位，高位被忽略（因为我们只有256字节内存）
    instruction = {Memory[address[7:0]], Memory[address[7:0] + 1], Memory[address[7:0] + 2], Memory[address[7:0] + 3]};

end

endmodule