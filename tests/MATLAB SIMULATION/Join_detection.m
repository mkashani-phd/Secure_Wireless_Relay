% 2-FSK Superposition Coding Simulation
clear; close all; clc;
% ------------ parameters ------------
Nbits = 1e4;
Tb     = 1;               % bit duration (s)
Fs     = 1e3;           % sampling freq (Hz) – must exceed 2*(f_c + f1_bb)
Ns     = Fs * Tb;         % samples/bit
t      = (0:Ns-1)/Fs;     % time vector
% baseband tone offsets
delta_f = 10;
% carrier
fc     = 100;            % e.g. 100 Hz carrier
% passband FSK tones
f0 = fc - delta_f;
f1 = fc + delta_f;
% regener­ate your basis waveforms
% s0 = cos(2*pi*f0*t);
% s1 = cos(2*pi*f1*t);
% ------------ rest of your simulation follows unchanged ------------
function Pe = get_Pe(L, p, R)
    C = 1 + p .* log2(p) + (1 - p) .* log2(1 - p);
    z = sqrt( L / (p * (1 - p)) ) * (C - R) / log2( (1 - p) / p );
    Pe = qfunc(z);
end
function PER = simulate_LDPC_PER(berVec, numFrames, maxIt)
% simulate_LDPC_PER  Monte Carlo–simulate PER vs. BER for an LDPC code
%                    using ldpcEncode/ldpcDecode.  Handles both cases
%                    where ldpcDecode returns [n×1] or [k×1].
%
%   PER = simulate_LDPC_PER(berVec, numFrames, maxIt) returns a vector PER
%   (same size as berVec).  For each BER in berVec:
%     1) Build a rate-½ DVB-S.2 LDPC code (H from dvbs2ldpc).
%     2) For numFrames random messages:
%          a) Encode with ldpcEncode(msgBits, encCfg).
%          b) Send through a BSC (flip each bit w.p. = BER).
%          c) Form LLRs and call ldpcDecode(LLRin, decCfg, maxIt).
%          d) If ldpcDecode returns an [n×1] vector, take its last k bits.
%             If it returns a [k×1] vector, use it directly.
%          e) Compare to original msgBits to determine packet‐error.
%     3) Return PER(idx) = (# errored packets) / numFrames.
%
%   Inputs:
%     - berVec    : vector of bit‐error‐rates to test, e.g. [1e-4, 1e-3, 1e-2]
%     - numFrames : # of LDPC codewords (frames) to simulate per BER
%     - maxIt     : max # of belief-prop rounds for ldpcDecode
%
%   Output:
%     - PER       : same size as berVec, giving packet‐error‐rate at each BER
%
%   Example:
%     berVec    = [1e-4, 5e-4, 1e-3, 5e-3];
%     numFrames = 2000;
%     maxIt     = 50;
%     PER = simulate_LDPC_PER(berVec, numFrames, maxIt);
%     semilogx(berVec, PER, '-o');
%     xlabel('BER'); ylabel('PER'); grid on;
%     title('Rate-½ DVB-S.2 LDPC: PER vs. BER');
    %----------------------------------------------------------------------
    % 1) Build the DVB-S.2 rate-½ LDPC code's parity-check matrix H
    %----------------------------------------------------------------------
    H     = dvbs2ldpc(1/4);          % m × n parity-check matrix
    encCfg = ldpcEncoderConfig(H);   % encoder configuration
    decCfg = ldpcDecoderConfig(H);   % decoder configuration
    % Instead of querying encCfg, compute (n, k) from H:
    [m, n] = size(H);
    k      = n - m;                  % number of information bits
    % Preallocate output
    PER = zeros(size(berVec));
    %----------------------------------------------------------------------
    % 2) Loop over each BER value in berVec
    %----------------------------------------------------------------------
    for idx = 1 : numel(berVec)
        p = berVec(idx);
        % Precompute the LLR magnitude for a BSC of crossover p:
        %   LLR_mag = log((1 - p)/p).  Then for a received hard bit r∈{0,1}:
        %     r == 0 → LLR = +LLR_mag
        %     r == 1 → LLR = –LLR_mag
        LLR_mag = log((1 - p)/p);
        numErrPackets = 0;
        for frameIdx = 1 : numFrames
            %--------------------------------------------------------------
            % 2a) Generate one random k-bit message
            %--------------------------------------------------------------
            msgBits = randi([0 1], k, 1);  % column vector in {0,1}^k
            %--------------------------------------------------------------
            % 2b) LDPC-encode: cw is an n×1 codeword
            %     Use signature: ldpcEncode(msgBits, encCfg)
            %--------------------------------------------------------------
            cw = ldpcEncode(msgBits, encCfg);  % cw ∈ {0,1}^n ×1
            %--------------------------------------------------------------
            % 2c) Simulate a BSC: flip each bit with probability p
            %--------------------------------------------------------------
            flips = (rand(n, 1) < p);   % logical mask of which bits flip
            rxHard = xor(cw, flips);    % received hard bits ∈ {0,1}^n
            %--------------------------------------------------------------
            % 2d) Convert hard bits → LLR vector LLRin (n×1 real)
            %     If rxHard(i)==0 → +LLR_mag, else → –LLR_mag
            %--------------------------------------------------------------
            LLRin = (1 - 2*double(rxHard)) * LLR_mag;
            %--------------------------------------------------------------
            % 2e) Decode: call ldpcDecode(LLRin, decCfg, maxIt)
            %     Many MATLAB versions return a [n×1] decoded codeword or a [k×1] info only.
            %--------------------------------------------------------------
            decodedBitsOrLLR = ldpcDecode(LLRin, decCfg, maxIt);
            %--------------------------------------------------------------
            % 2f) Determine which length we got and extract k-bit info:
            %    • If length(decodedBitsOrLLR)==n → it's the full codeword bits (0/1).
            %      Take last k positions as info.
            %    • If length(decodedBitsOrLLR)==k → it's already just the info bits.
            %
            lenOut = numel(decodedBitsOrLLR);
            if lenOut == n
                % Full n-bit codeword was returned
                estInfoBits = decodedBitsOrLLR(n - k + 1 : n);
            elseif lenOut == k
                % Only the k-bit information was returned
                estInfoBits = decodedBitsOrLLR;
            else
                error("ldpcDecode returned length %d; expected either %d or %d.", ...
                      lenOut, n, k);
            end
            %--------------------------------------------------------------
            % 2g) Compare estInfoBits (k×1) to original msgBits (k×1)
            %     Any mismatch → packet error.
            %--------------------------------------------------------------
            if any(estInfoBits ~= msgBits)
                numErrPackets = numErrPackets + 1;
            end
        end
        % Compute PER at this BER
        PER(idx) = numErrPackets / numFrames;
        fprintf('BER = %.2e  →  PER = %.2e  (%d / %d errors)\n', ...
                p, PER(idx), numErrPackets, numFrames);
    end
end
% Power‐allocation factor (0 < alpha < 0.5)
alpha = 0.0;            
% Eb/N0 range (dB) and storage for BER
Eb = .1:.1:2;
N0 = .1;
EbN0_arr = Eb./N0;
BER_m   = zeros(size(EbN0_arr));
BER_n   = zeros(size(EbN0_arr));
llr_all = zeros(size(EbN0_arr));
Pe = zeros(size(EbN0_arr));
Pe_q = zeros(size(EbN0_arr));
thr_pos = 0;
thr_neg = 0;
% Loop over SNR points
for idx = 1:length(EbN0_arr)
    EbN0 = EbN0_arr(idx);
    
    % Amplitude weights as per your formula
    a = sqrt(1-alpha);    % weight for m
    b = sqrt(alpha);        % weight for n
    
    % Precompute decision thresholds 
    thr_pos = (log(((1-alpha)*EbN0 + 1)/(alpha*EbN0 + 1)) + log(1+EbN0))/2;
    thr_neg = (log((alpha*EbN0 + 1)/((1-alpha)*EbN0 + 1)) - log(1+EbN0))/2;
    
    errors_m = 0;
    errors_n = 0;
    
    for k = 1:Nbits
        % draw bits
        m = rand > 0.5;
        n = rand > 0.5;
        
        phase = rand*pi/2;
        s0 = sqrt(2*Eb(idx))*cos(2*pi*f0*t + phase);
        s1 = sqrt(2*Eb(idx))*cos(2*pi*f1*t + phase);
        % select FSK tone for each
        sm = (m==0)*s0 + (m~=0)*s1;
        sn = (n==0)*s0 + (n~=0)*s1;
        
        % superimposed transmit waveform
        tx = a*sm + b*sn;
        
        % AWGN
        % noise = sqrt(noiseVar) * randn(1, Ns);
            % Noise variance per sample
        sigma = sqrt(N0*Fs/2);
        noise = sigma * randn(1, Ns);
        r     = tx + noise;
        
        % energy measurements via correlator
        E0 = (sum(r .* cos(2*pi*(fc-delta_f)*t)))^2 + (sum(r .* sin(2*pi*(fc-delta_f)*t)))^2;
        E1 = (sum(r .* cos(2*pi*(fc+delta_f)*t)))^2 + (sum(r .* sin(2*pi*(fc+delta_f)*t)))^2;
        d  = log(E1/E0);
        llr_all(k) = d;
        
        % decode m
        m_hat = d > 0;
        errors_m = errors_m + (m_hat ~= m);
        
        % decode n using your thresholds
        if d > 0
            if d > thr_pos
                n_hat = 1;
            else
                n_hat = 0;
            end
        else
            if d < thr_neg
                n_hat = 0;
            else
                n_hat = 1;
            end
        end
        errors_n = errors_n + (n_hat ~= n);
    end
    
    BER_m(idx) = errors_m/Nbits;
    BER_n(idx) = errors_n/Nbits;
    R = 1/4;
    L = 256/R;
    Pe_q(idx) = get_Pe(L, BER_n(idx), R);
    % Pe(idx)  = simulate_LDPC_PER(BER_n(idx), 1000, 25);
    
    fprintf('Eb/N0 = %2d dB: BER_m = %.2e, BER_n = %.2e, Pe_n = %2e, Pe_q = %2e\n', ...
            10.*log10(EbN0_arr(idx)), BER_m(idx), BER_n(idx), Pe(idx), Pe_q(idx));
end
% Plot results
figure;
semilogy(10.*log(EbN0_arr), BER_m, 'o-','LineWidth',1.5); hold on;
semilogy(10.*log(EbN0_arr), BER_n, 's-','LineWidth',1.5);
semilogy(10.*log(EbN0_arr), Pe, 's-','LineWidth',1.5)
semilogy(10.*log(EbN0_arr), Pe_q, 's-','LineWidth',1.5)
semilogy(10.*log(EbN0_arr), 0.5*exp(-Eb./(2.*N0)), '-','LineWidth',1.5)
grid on;
xlabel('Eb/N0 (dB)');
ylabel('Bit Error Rate');
ylim([1e-3 1])
legend('m (strong)','n (weak)', 'ldpc', 'pe_q','0.5*exp(-Eb./(2.*N0))','Location','southwest');
title('BER vs Eb/N0 for 2-FSK Superposition Coding');
figure;
histogram(llr_all, 100);
% plot( llr_all,1:Nbits, '.');
grid on;
xlabel('LLR = ln(E_1/E_0)');
ylabel('Count');
title(sprintf('LLR Histogram at \\itE_b/N_0 = %d dB', 10.*log10(EbN0_arr(idx))));
xline(thr_pos, 'r--', 'LineWidth',1.5, 'Label','Pos. thres.','LabelHorizontalAlignment','right');
xline(thr_neg, 'r--', 'LineWidth',1.5, 'Label','Neg. thres.','LabelHorizontalAlignment','left');
