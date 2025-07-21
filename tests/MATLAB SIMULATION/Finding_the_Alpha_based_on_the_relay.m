% 2-FSK Superposition Coding Simulation
clear; close all; clc;
% ------------ parameters ------------
Nbits = 1e3;
Tb     = 1;               % bit duration (s)
Fs     = 1e4;           % sampling freq (Hz) – must exceed 2*(f_c + f1_bb)
Ns     = Fs * Tb;         % samples/bit
t      = (0:Ns-1)/Fs;     % time vector
% baseband tone offsets
delta_f = 1;
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

figure;
for alpha = 0:.05:.3
    alpha
    % Power‐allocation factor (0 < alpha < 0.5)       
    % Eb/N0 range (dB) and storage for BER
    Eb = .1:.01:.7;
    N0 = .1;
    EbN0_arr = Eb./N0;
    BER_m   = zeros(size(EbN0_arr));
    BER_n   = zeros(size(EbN0_arr));
    llr_all = zeros(size(EbN0_arr));
    Pe = zeros(size(EbN0_arr));
    Pe_q = zeros(size(EbN0_arr));
    Pe_m_trad = zeros(size(EbN0_arr));
    Pe_m_proposed = zeros(size(EbN0_arr));
    Pe_t_trad = zeros(size(EbN0_arr));
    Pe_t_proposed= zeros(size(EbN0_arr));
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
        errors_n2 = 0;
        
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
            
            % % decode n using your thresholds
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

            %  using the phase 2 information
            if m>0
                if E0 > alpha*E1 *.9
                    n_hat2 = 0;
                else
                    n_hat2 = 1;
                end
            else
                if E1 > alpha*E0  *.9
                    n_hat2 = 1;
                else
                    n_hat2 = 0;
                end
            end
            % fprintf('m = %2d, t = %2d, E0 = %2e, E1 = %2e, alpha*E0 * .95 = %2e, alpha*E1 *.95 = %2e\n', ...
            %     m,n, E0, E1,  alpha*E0 * .95 < E1, alpha*E1 * .95 < E0)
            
            errors_n = errors_n + (n_hat ~= n);
            errors_n2 = errors_n2 + (n_hat2 ~= n);
        end
        
        BER_m(idx) = errors_m/Nbits;
        BER_n(idx) = errors_n/Nbits;
        BER_n2(idx) = errors_n2/Nbits;
        R = 1/2;
        L = 256/R;
        Pe_q(idx) = get_Pe(L, BER_n(idx), R);
    
    
        m = 5504;
        tag = 256;
        R = .5;
        % estimate the probability of message error on relay in trad

        if alpha == 0
    
            L_t = tag/R;
            L_m = m/R;
            Pe_t_trad(idx) = get_Pe(L_t, BER_m(idx), R);
            Pe_m_trad(idx) = get_Pe(L_m, BER_m(idx), R);

            
        else
            total = (m+tag)/R;
            R_m = m/total;
            R_t = tag/total;
            Pe_m_proposed(idx) = get_Pe(total, BER_m(idx), R_m);
            Pe_t_proposed(idx) = get_Pe(total, BER_n(idx), R_t);

            


        end

        
        fprintf('Eb/N0 = %2d dB: BER_m = %.2e, BER_n = %.2e, Pe_t_trad = %2e, Pe_t_proposed = %2e\n', ...
                10.*log10(EbN0_arr(idx)), BER_m(idx), BER_n(idx), Pe_t_trad(idx), Pe_t_proposed(idx));
    end
    %     if alpha == 0
    %         alpha
    %         semilogy(10.*log(EbN0_arr/R), Pe_t_trad, 'o-','LineWidth',3.5,'DisplayName','Pe,t->traditional'); hold on;
    %     else
    %         alpha
    %         semilogy(10.*log((alpha)*EbN0_arr/R), Pe_t_proposed, 's-','LineWidth',1.5, 'DisplayName',sprintf('Pe,t->alpha = %2e', alpha)); hold on;
    %     end
end
% Plot results

semilogy(10.*log(EbN0_arr), BER_m, 'o-','LineWidth',1.5); hold on;
semilogy(10.*log(EbN0_arr), BER_n, 's-','LineWidth',1.5);
% 
semilogy(10.*log(EbN0_arr), 0.5*exp(-Eb./(2.*N0)), '-','LineWidth',1.5, 'DisplayName','0.5*exp(-Eb./(2.*N0))')
grid on;
xlabel('Eb/N0 (dB)');
ylabel('Bit Error Rate');
ylim([1e-3 1])
legend('Location','southwest');
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


figure;
semilogy(10.*log(EbN0_arr), BER_n, 's-','LineWidth',1.5,'DisplayName','joint detection');hold on;
semilogy(10.*log(EbN0_arr), BER_n2, 's-','LineWidth',1.5,'DisplayName','Successive cancelation' );
legend('Location','best');