module instruction_memory(
    input [7:0] address,
    output reg [31:0] instruction
);

reg [7:0] Memory [0:255];

// 初始化指令存储器
initial begin
    // add 
    {Memory[0], Memory[1], Memory[2], Memory[3]} = 32'b000000_00010_00011_00001_00000_100000;
    // sub 
    {Memory[4], Memory[5], Memory[6], Memory[7]} = 32'b000000_00101_00110_00100_00000_100010;
    // beq
    {Memory[8], Memory[9], Memory[10], Memory[11]} = 32'b000100_00111_01000_0000000000000001;
    // subu
    {Memory[12], Memory[13], Memory[14], Memory[15]} = 32'b000000_01010_01011_01001_00000_100011;
    // sltu
    {Memory[16], Memory[17], Memory[18], Memory[19]} = 32'b000000_01101_01110_01100_00000_101011;
    // sw 
    {Memory[20], Memory[21], Memory[22], Memory[23]} = 32'b101011_10000_01111_0000000000000100;
    // lw 
    {Memory[24], Memory[25], Memory[26], Memory[27]} = 32'b100011_10010_10001_0000000000001000;    
    // slt 
    {Memory[28], Memory[29], Memory[30], Memory[31]} = 32'b000000_10100_10101_10011_00000_101010;    
    // addiu 
    {Memory[32], Memory[33], Memory[34], Memory[35]} = 32'b001001_10111_10110_0000000011111111;    
    // ori
    {Memory[36], Memory[37], Memory[38], Memory[39]} = 32'b001101_11001_11000_0000000001111111;    
    // jump 
    {Memory[40], Memory[41], Memory[42], Memory[43]} = 32'b000010_00000000000000000100000000;
end

// 根据地址输出指令
always @(*) begin
    instruction = {Memory[address], Memory[address + 1], Memory[address + 2], Memory[address + 3]};
end

endmodule