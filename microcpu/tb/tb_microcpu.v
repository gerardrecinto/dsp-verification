module tb_microcpu;
 reg clk=0, rst=1; reg [7:0] instruction=0; wire [7:0] accumulator; wire halted;
 microcpu dut(clk,rst,instruction,accumulator,halted);
 always #5 clk=~clk;
 initial begin
   @(negedge clk); rst=0; instruction=8'h15;
   @(negedge clk); if(accumulator!==5) $fatal(1,"ADD expected 5 got %0d",accumulator);
   instruction=8'h23; @(negedge clk); if(accumulator!==6) $fatal(1,"XOR expected 6 got %0d",accumulator);
   instruction=8'hf0; @(negedge clk); if(!halted) $fatal(1,"HALT not set");
   instruction=8'h11; @(negedge clk); if(accumulator!==6) $fatal(1,"state changed after HALT");
   $display("PASS: reset, ADD, XOR, HALT, hold"); $finish;
 end
endmodule
