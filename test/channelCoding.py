import numpy as np
from scipy.sparse import coo_matrix
import commpy.channelcoding.ldpc as commpyldpc
import math, os ,time


def load_base_matrix_from_text(filename):
    rows = []
    
    with open(filename, 'r') as f:
        for line in f:
            # Strip whitespace, split by spaces
            str_vals = line.strip().split()
            # Convert each token to an int
            int_vals = list(map(int, str_vals))
            rows.append(int_vals)
    
    # Convert list of lists into a NumPy array
    # This assumes all rows have the same length
    base_matrix = np.array(rows, dtype=int)
    
    return base_matrix

def expand_submatrix(shift, Z):
    if shift == -1:
        # No connection => Zero submatrix
        data = []
        row = []
        col = []
        return coo_matrix((data, (row, col)), shape=(Z, Z))

    # For a shift >= 0, create a ZxZ identity matrix shifted by 'shift' columns (mod Z).
    # The (i, i+shift mod Z) = 1 for i in [0..Z-1].
    data = np.ones(Z, dtype=int)
    row = np.arange(Z)
    col = (row + shift) % Z
    return coo_matrix((data, (row, col)), shape=(Z, Z))

def create_5g_nr_parity_check_matrix(file, Z=4):

    base_graph_matrix = load_base_matrix_from_text(file)
    R, C = base_graph_matrix.shape

    big_data = []
    big_row = []
    big_col = []
    
    for r in range(R):
        for c in range(C):
            sub_H = expand_submatrix(base_graph_matrix[r, c], Z)
            # The top-left corner of the submatrix in the full H
            row_offset = r * Z
            col_offset = c * Z 
            # Convert sub_H into COO to extract data, row, col
            sub_H_coo = sub_H.tocoo()
            # Append to global row/col/data
            big_data.extend(sub_H_coo.data)
            big_row.extend(sub_H_coo.row + row_offset)
            big_col.extend(sub_H_coo.col + col_offset)
    
    # Final matrix size is (R*Z) x (C*Z)
    H = coo_matrix((big_data, (big_row, big_col)), shape=(R*Z, C*Z), dtype=int)
    return H




def create_5G_ldpc_params(file, Z=4):
    H = create_5g_nr_parity_check_matrix(file, Z)
    commpyldpc.write_ldpc_params(H, '5g_nr_ldpc_params.txt')

def get_5G_ldpc_params(file = '5g_nr_ldpc_params.txt'):
    return commpyldpc.get_ldpc_code_params(ldpc_design_filename=file, compute_matrix=True)   

def encode(msg, H_params, pad = 1):
    return commpyldpc.triang_ldpc_systematic_encode(message_bits=msg, ldpc_code_params=H_params, pad=pad)

# def decode(llr, H_params, decoder_algorithm = "SPA", n_iters=100):
#     return commpyldpc.ldpc_bp_decode(llr_vec=llr, ldpc_code_params=H_params, decoder_algorithm = decoder_algorithm, n_iters=n_iters)






def create_5G_ldpc_params(file, base_matrix_file, Z):
    """
    1) Builds the parity-check matrix H by expanding 'base_matrix_file' with factor Z.
    2) Writes LDPC params to a file (5g_nr_ldpc_params.txt).
    """
    H = create_5g_nr_parity_check_matrix(base_matrix_file, Z)
    commpyldpc.write_ldpc_params(H.toarray(), file)

def get_5G_ldpc_params(ldpc_param_file):
    """
    Reads the LDPC parameter file and returns a dictionary that
    CommPy uses for encode/decode.
    """
    return commpyldpc.get_ldpc_code_params(ldpc_design_filename=ldpc_param_file, compute_matrix=True)

def encode_bits(message_bits, H_params, pad=1):
    """
    Uses CommPy's systematic encode. 
    message_bits: 1D numpy array of 0/1, length = K
    H_params: the dictionary from get_5G_ldpc_params()
    Returns: 1D numpy array (mother codeword).
    """
    return commpyldpc.triang_ldpc_systematic_encode(
        message_bits=message_bits,
        ldpc_code_params=H_params,
        pad=pad
    )

def decode_llr(llr, H_params, decoder_algorithm="SPA", n_iters=100):
    """
    CommPy BP (SPA) decode.
    llr: 1D array of LLRs
    """
    return commpyldpc.ldpc_bp_decode(
        llr_vec=llr,
        ldpc_code_params=H_params,
        decoder_algorithm=decoder_algorithm,
        n_iters=n_iters
    )

def simple_rate_match(codeword, E):
    """
    Simplified rate-matching step: 
    Keep the first E bits (no sub-block interleaving, no circular buffer).
    If E > len(codeword), you could do repetition, but here we just raise an error.
    """
    if E <= len(codeword):
        return codeword[:E]
    else:
        raise ValueError(f"Requested E={E} > mother codeword length={len(codeword)}. "
                         "Implement repetition if needed.")

def pick_bg1_file_for_Z(Z): 
    base_name = f"NR_1_0_{Z}.txt"  
    full_path = os.path.join("base_matrices", base_name)
    return full_path

def pick_bg2_file_for_Z(Z):
    base_name = f"NR_1_0_{Z}.txt"  
    full_path = os.path.join("base_matrices", base_name)
    return full_path

def find_smallest_Z_for_E(Z_min , Code_rate):
    Z_chosen = None
    for z_try in range(Z_min, 1025):  # or some upper bound
        if Code_rate < 0.3:
            fname = pick_bg1_file_for_Z(z_try)
        else:
            fname = pick_bg2_file_for_Z(z_try)
        if os.path.isfile(fname):
            Z_chosen = z_try
            break
    return Z_chosen

def generate_5g_codeword_bg2(message_bits, code_rate, pad=1):
    """
    High-level function that:
     1) Calculates the desired output length E = ceil(K / code_rate).
     2) Picks a BG2 expansion factor Z so that 52 * Z >= E.
     3) Loads the BG2 file (NR_2_7_Z.txt or similar), builds LDPC params.
     4) Encodes with CommPy.
     5) Rate-matches to produce E bits.
    Returns: codeword of length E (numpy array of 0/1).
    """


    K = len(message_bits)
    E = math.ceil(K / code_rate)
    print(f"Desired output length E = {math.ceil(K / code_rate)}, K = {K}")


    # BG1 typically has "C_bg1 = 68" columns and 'R_bg1 = 46' rows in the base matrix.
    C_bg1 = 68
    # BG2 typically has "C_bg2 = 52" columns and "R_bg2"=  42.
    C_bg2 = 52



    if code_rate < 0.3:
        # using the BG1 base matrix
        Z_min = math.ceil(E / C_bg1)
        Z_chosen = find_smallest_Z_for_E(Z_min, code_rate)
        print("BG1, Zchose:", Z_chosen, "Z_min*46", Z_chosen*46)
        base_matrix_file = pick_bg1_file_for_Z(Z_chosen)
        print(f"Using BG1 file: {base_matrix_file}  (Z={Z_chosen})")
        
    else:
        # using the BG2 base matrix
        Z_min = math.ceil(E / C_bg2)
        Z_chosen = find_smallest_Z_for_E(Z_min, code_rate)
        print("BG2, Zchose:", Z_chosen, "Z_min*42", Z_chosen*42)
        base_matrix_file = pick_bg2_file_for_Z(Z_chosen)
        print(f"Using BG2 file: {base_matrix_file}  (Z={Z_chosen})")

    # 2) Among your existing files, pick the smallest Z >= Z_min that you actually have
    #    In real code, you'd probably read the directory or keep a sorted list of valid Z's.
    #    We'll just do a brute force upwards from Z_min to some max.
    #    Then pick the first file that exists.


    if Z_chosen is None:
        raise FileNotFoundError(f"No valid BG2 file found for Z >= {Z_min}. "
                                f"Check your base_matrices folder or adjust search range.")




    # 3) Create 5G LDPC params from that file
    ldpc_file_design = "msg: "+str(len(message_bits)) + " code_rate: "+str(np.round(code_rate,2))+".txt"
    try:
        create_5G_ldpc_params(ldpc_file_design, base_matrix_file, Z_chosen)
    except FileExistsError:
        time.sleep(.1)
        ldpc_params = get_5G_ldpc_params(ldpc_file_design)
    except:
        print("Error creating 5G LDPC params")
        return None

    # 4) Encode
    mother_codeword = encode_bits(message_bits, ldpc_params, pad=pad)
    print(f"Mother codeword length = {mother_codeword.shape}")

    # 5) Rate-match to get exactly E bits
    # final_codeword = simple_rate_match(mother_codeword, E)
    # print(f"Final codeword length = {final_codeword.shape}")
    return mother_codeword








# ---------------------------
# EXAMPLE USAGE
# ---------------------------
 
def test():
    # Suppose you want to encode a 1024-bit message at rate ~1/2
    msg_1024 = np.random.randint(0, 2, 1024)
    code_rate = 1/3
    codeword_half_rate = generate_5g_codeword_bg2(msg_1024, code_rate)
    print(f"Codeword length = {len(codeword_half_rate)} (target rate ~ {len(msg_1024)/len(codeword_half_rate):.3f})")

    # Another example: 256-bit message at rate ~1/3
    msg_256 = np.random.randint(0, 2, 256)
    code_rate = 1/3
    codeword_third_rate = generate_5g_codeword_bg2(msg_256, code_rate)
    print(f"Codeword length = {len(codeword_third_rate)} (target rate ~ {len(msg_256)/len(codeword_third_rate):.3f})")



if __name__ == "__main__":
    test()


