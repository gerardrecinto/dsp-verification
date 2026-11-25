// 4-tap FIR filter, Q1.15 coefficients, saturating 16-bit output, two-cycle latency.
// y[n] = sat16((c0*x[n] + c1*x[n-1] + c2*x[n-2] + c3*x[n-3]) >>> 15)
// Each BUG_* macro plants one design error. The regression must fail every one of them.
module fir4 (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               in_valid,
    input  wire signed [15:0] in_data,
    input  wire               coef_we,
    input  wire        [1:0]  coef_idx,
    input  wire signed [15:0] coef_data,
    output reg                out_valid,
    output reg  signed [15:0] out_data,
    output reg                sat
);
    reg signed [15:0] c0, c1, c2, c3;
    reg signed [15:0] x0, x1, x2;
    reg signed [33:0] acc;
    reg               v1;

    // Samples the multiply-accumulate sees at this edge: the new input and three older ones.
`ifdef BUG_TAP
    wire signed [15:0] n3 = x1;          // off-by-one tap: reads the wrong delay
`else
    wire signed [15:0] n3 = x2;
`endif
    wire signed [33:0] sum_next = in_data * c0 + x0 * c1 + x1 * c2 + n3 * c3;

`ifdef BUG_SHIFT
    wire signed [33:0] scaled = $signed({1'b0, acc[33:1]}) >>> 14;   // logical shift on a signed value
`else
    wire signed [33:0] scaled = acc >>> 15;
`endif

    wire pos_ovf = (scaled > 34'sd32767);
`ifdef BUG_SATNEG
    wire neg_ovf = (scaled < -34'sd32767);   // clamps one code too early
`else
    wire neg_ovf = (scaled < -34'sd32768);
`endif

`ifdef BUG_VALID
    // Drops every fourth output valid: a pipeline control error.
    reg [1:0] vcount;
    wire out_valid_gate = (vcount != 2'd3);
    always @(posedge clk) begin
        if (!rst_n) vcount <= 0; else if (v1) vcount <= vcount + 1;
    end
`endif

    always @(posedge clk) begin
        if (!rst_n) begin
            c0 <= 0; c1 <= 0; c2 <= 0; c3 <= 0;
`ifndef BUG_RESET
            x0 <= 0; x1 <= 0; x2 <= 0;
`endif
            acc <= 0; v1 <= 0;
            out_valid <= 0; out_data <= 0; sat <= 0;
        end else begin
            if (coef_we) begin
                case (coef_idx)
                    2'd0: c0 <= coef_data;
                    2'd1: c1 <= coef_data;
                    2'd2: c2 <= coef_data;
`ifndef BUG_COEF
                    2'd3: c3 <= coef_data;
`endif
                endcase
            end

            v1 <= in_valid;
            if (in_valid) begin
                x2 <= x1; x1 <= x0; x0 <= in_data;
                acc <= sum_next;
            end

`ifdef BUG_VALID
            out_valid <= v1 & out_valid_gate;
`else
            out_valid <= v1;
`endif
            if (v1) begin
`ifdef BUG_WRAP
                out_data <= scaled[15:0]; sat <= 0;          // no saturation: wraps around
`else
                if (pos_ovf)      begin out_data <= 16'sd32767;  sat <= 1; end
                else if (neg_ovf) begin out_data <= -16'sd32768; sat <= 1; end
                else              begin out_data <= scaled[15:0]; sat <= 0; end
`endif
            end
        end
    end

endmodule
