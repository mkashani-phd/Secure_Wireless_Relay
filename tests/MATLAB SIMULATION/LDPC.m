%% one_shot_ldpc.m
% One-shot LDPC encode: 256 bits -> 16384 bits at rate 1/64

% 1) Parameters
k   = 256;                % message length
R   = 1/64;               
n   = k / R;              % codeword length = 16384
M   = n - k;              % number of parity checks = 16128
dv  = 63;                 % column weight (d_v)
dc  = 64;                 % row weight    (d_c)
assert(M*dc == n*dv, 'dv/dc must equal (n-k)/n');

% 2) Generate regular LDPC H
H = generate_regular_ldpc(M, n, dv, dc);

% 3) Compute RREF of H over GF(2) to get pivot columns
[R, pivcols] = gf2rref_mod2(H);

% 4) Identify free columns → k_actual should equal 256
freecols  = setdiff(1:n, pivcols);
k_actual  = numel(freecols);
assert(k_actual == k, "Null‐space dimension ≠ 256!");

% 5) Build systematic generator G (k × n)
G = build_generator_from_rref(R, pivcols, freecols);

% 6) Your 256-bit message (row vector of 0/1)
message = randi([0 1], 1, k);

% 7) Encode: codeword = message * G mod 2
codeword = mod(message * G, 2);

fprintf("Encoded a %d-bit message into a %d-bit codeword.\n", k, numel(codeword));

%% --- Subfunctions ---

function H = generate_regular_ldpc(M, N, wc, wr)
% Generates an M×N regular LDPC parity-check matrix with
% column weight wc and row weight wr, avoiding duplicate 1's.
    rowStubs = repelem((1:M)', wr);
    colStubs = repelem((1:N)', wc);
    E = N*wc;
    H = zeros(M, N);
    while true
        perm = randperm(E);
        H(:) = 0;
        idx = sub2ind([M, N], rowStubs, colStubs(perm));
        H(idx) = H(idx) + 1;
        if all(H(:) <= 1)
            return;
        end
    end
end

function [R, pivcols] = gf2rref_mod2(A)
% Performs row-reduction over GF(2) on A, returns R in RREF
% and the list of pivot column indices.
    [M, N] = size(A);
    R = mod(A, 2);
    pivcols = [];
    r = 1;
    for c = 1:N
        if r > M, break; end
        % find a 1 in column c at or below row r
        rows = find(R(r:M, c), 1) + (r-1);
        if isempty(rows), continue; end
        % swap into pivot position
        if rows ~= r
            R([r rows], :) = R([rows r], :);
        end
        pivcols(end+1) = c;
        % eliminate all other 1's in column c
        for rr = [1:r-1, r+1:M]
            if R(rr, c)
                R(rr, :) = mod(R(rr, :) + R(r, :), 2);
            end
        end
        r = r + 1;
    end
end

function G = build_generator_from_rref(R, pivcols, freecols)
% Given RREF R of H and its pivot & free columns, build
% a systematic generator matrix G of size (numel(freecols) × size(R,2)).
    n = size(R, 2);
    k = numel(freecols);
    G = zeros(k, n);
    for i = 1:k
        f = freecols(i);
        v = zeros(1, n);
        v(f) = 1;
        % solve for pivot variables so that H * v' = 0
        for r = 1:numel(pivcols)
            pc = pivcols(r);
            if R(r, f) == 1
                v(pc) = 1;
            end
        end
        G(i, :) = v;
    end
end
