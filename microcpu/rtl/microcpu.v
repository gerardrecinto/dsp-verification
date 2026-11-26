// Educational single-issue, in-order 8-bit CPU. Not a production microprocessor.
module microcpu(input clk, input rst, input [7:0] instruction, output reg [7:0] accumulator, output reg halted);
  // 0x1N ADD immediate N; 0x2N XOR immediate N; 0xF0 HALT; 0x0N NOP.
  always @(posedge clk) begin
    if (rst) begin accumulator <= 0; halted <= 0; end
    else if (!halted) case (instruction[7:4])
      4'h1: accumulator <= accumulator + instruction[3:0];
      4'h2: accumulator <= accumulator ^ instruction[3:0];
      4'hf: halted <= 1;
      default: accumulator <= accumulator;
    endcase
  end
endmodule
