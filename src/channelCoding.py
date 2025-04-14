import numpy as np
from scipy.sparse import coo_matrix
import matplotlib.pyplot as plt
import commpy.channelcoding.ldpc as ldpc
import os
import re



def create_LDPC(message_len:int, Codeword_length:int):

    # Example usage
    K = message_len
    N = Codeword_length


    bg, zc, kb = select_ldpc_and_Zc(K, N)
    # print(f"Selected Base Graph: BG{bg}, Selected Zc: {zc}")

    file_path = find_base_matrix_file(f"BG{bg}", zc)
    # print(f"Base matrix file found at: {file_path}")

    base_graph = load_base_matrix_from_text(file_path)
    if base_graph is None:
        exit("Error loading base matrix file")


    mb, nb = base_graph.shape
    #print(f"mb: {mb}, nb: {nb}")


    H = expand_base_graph(base_graph=base_graph, Zc=zc)
    # print(f"Actual K:{zc*kb}, Actual N:{H.shape[1]}")
    file_name = os.path.join(os.path.dirname(__file__), "__cache__", f'zc = {zc}, kb = {kb}, K_ldpc = {zc*kb}, N_ldpc = {H.shape[1]}, K  = {K}, N = {N}.bg')
    try:
        ldpc.write_ldpc_params(np.array(H, dtype=np.int8), file_name)
    except:
        pass


def parse_filename(filename:str):
    #f'zc = {zc}, kb = {kb}, K_ldpc = {zc*kb}, N_ldpc = {H.shape[1]}, K  = {K}, N = {N}.bg'
    if filename is None:
        raise Exception("Filename is None for parsing")
    res = {}
    res['zc'] = int(re.search(r'zc = (\d+)', filename).group(1))
    res['kb'] = int(re.search(r'kb = (\d+)', filename).group(1))
    res['K_ldpc'] = int(re.search(r'K_ldpc = (\d+)', filename).group(1))
    res['N_ldpc'] = int(re.search(r'N_ldpc = (\d+)', filename).group(1))
    res['K'] = int(re.search(r'K  = (\d+)', filename).group(1))
    res['N'] = int(re.search(r'N = (\d+)', filename).group(1))
    return res

def find_LDPC(serch:dict):
    files = []
    cache_folder = os.path.join(os.path.dirname(__file__), "__cache__")
    if os.path.exists(cache_folder):
        for file in os.listdir(cache_folder):
            if file.endswith('.bg'):
                files.append(os.path.join(cache_folder, file))

    for file in files:
        filename_paresed = parse_filename(file)
        if all([filename_paresed[key] == value for key, value in serch.items()]):
            return file
    return None



def encode_LDPC(message:list|np.ndarray, Codeword_length:int):

    #look in the path for all the .bg files and find the file that ends with  f'K  = {K}, N = {N}.bg'
    K = len(message)
    N = Codeword_length
    ldpc_search = {'K':K, 'N':N}
    filename = find_LDPC(ldpc_search)
    if filename is None:
        create_LDPC(K, N)
        filename = find_LDPC(ldpc_search)
    
    if filename is None:
        raise Exception("No LDPC file found")
    filename_paresed = parse_filename(filename)
    zc = filename_paresed['zc']
    kb = filename_paresed['kb']

    if len(message) != kb*zc:
        message = np.concatenate((message, np.zeros(kb*zc - len(message))))

    ldpc_param = ldpc.get_ldpc_code_params(ldpc_design_filename=filename, compute_matrix=True)
    codeword = ldpc.triang_ldpc_systematic_encode(message, ldpc_param, 0)

    return codeword

def decode_LDPC(codeword_llr:list|np.ndarray, message_length:int):
    K = message_length
    N_ldpc = len(codeword_llr)

    ldpc_search = {'K':K, 'N_ldpc':N_ldpc}
    filename = find_LDPC(ldpc_search)

    filename_paresed = parse_filename(filename)

    maximum = max(codeword_llr)
    if K < filename_paresed['K_ldpc']:
        codeword_llr[K:filename_paresed['K_ldpc']] = [maximum]* (filename_paresed['K_ldpc'] - K)



    ldpc_param = ldpc.get_ldpc_code_params(ldpc_design_filename=filename, compute_matrix=True)
    
    codeword_llr = np.array(codeword_llr)
    message = ldpc.ldpc_bp_decode(codeword_llr, ldpc_param, decoder_algorithm='SPA', n_iters=100)

    return message[0][:message_length]






def load_base_matrix_from_text(filename):
    """
    Loads a base matrix from a text file.
    Each line corresponds to a row of integers.
    Returns a 2D NumPy array with shape (R, C).
    """
    rows = []
    if filename is None:
        return None
    
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
    """
    Given a shift value and a lifting factor Z,
    return the Z x Z submatrix (in sparse format) that represents
    a cyclic shift (if shift >= 0) or a zero matrix (if shift == -1).
    """
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


def generate_circulant_matrix(size, shift):
    """
    Generates a circulant permutation matrix of given size with a right shift.

    Parameters:
        size (int): Size of the square matrix.
        shift (int): Number of positions to shift the identity matrix.

    Returns:
        np.ndarray: The Zc × Zc circulant permutation matrix.
    """
    identity_matrix = np.eye(size, dtype=int)
    return np.roll(identity_matrix, shift, axis=1)

def expand_base_graph(base_graph, Zc):
    """
    Expands the base graph using lifting factor Zc.

    Parameters:
        base_graph (nd_array):  base graph .
        Zc (int): Expansion factor.

    Returns:
        np.ndarray: The fully expanded parity-check matrix.
    """


    rows, cols = base_graph.shape
    expanded_matrix = np.zeros((rows * Zc, cols * Zc), dtype=int)

    for i in range(rows):
        for j in range(cols):
            value = base_graph[i, j]
            if value == -1:
                # Insert a Zc x Zc zero matrix
                expanded_matrix[i*Zc:(i+1)*Zc, j*Zc:(j+1)*Zc] = np.zeros((Zc, Zc), dtype=int)
            else:
                # Insert a Zc x Zc circulant matrix with the specified shift
                expanded_matrix[i*Zc:(i+1)*Zc, j*Zc:(j+1)*Zc] = generate_circulant_matrix(Zc, value)

    return expanded_matrix




def select_ldpc_and_Zc(K, N):
    """
    Determines the LDPC base graph (BG1 or BG2) and the minimum expansion factor Zc.
    
    Parameters:
        K (int): Number of information bits.
        R (float): Coding rate.
    
    Returns:
        tuple: (Selected BG, Zc)
    """
    # Define the table values from the provided image
    Zc_table = np.array([
        [2, 3, 5, 7, 9, 11, 13, 15],
        [4, 6, 10, 14, 18, 22, 26, 30],
        [8, 12, 20, 28, 36, 44, 52, 60],
        [16, 24, 40, 56, 72, 88, 104, 120],
        [32, 48, 80, 112, 144, 176, 208, 240],
        [64, 96, 160, 224, 288, 352, None, None],
        [128, 192, 320, None, None, None, None, None],
        [256, 384, None, None, None, None, None, None]
    ])

    # Flatten the table and filter valid Zc values
    valid_Zc_values = sorted(set(x for row in Zc_table for x in row if x is not None))

    # Step 1: Select BG
    R = K / N
    if (K <= 3824 and R <= 0.67) or (K <= 292) or (R <= 0.25):
        BG = 2
    else:
        BG = 1

    # Step 2: Determine Kb
    if BG == 1:
        Kb = 22
        nr, nc = 46, 68
    else:
        nr, nc = 42, 52
        # if K > 640:
        #     Kb = 10
        # elif 560 < K <= 640:
        #     Kb = 9
        # elif 192 < K <= 560:
        #     Kb = 8
        # else:
        #     Kb = 6
        Kb = 10

    # Step 3: Select the minimum Zc such that Kb * Zc >= K
    mb = np.floor((Kb / R) - (Kb - 2))+1  # Ensure it's an integer
    nb = Kb + mb
    for Zc in valid_Zc_values:
        if Kb * Zc >= K and nc * Zc >= N + 2*Zc:
            return BG, Zc, Kb

    return BG, None  # Return None if no suitable Zc is found



def find_base_matrix_file(bg, zc, folder_path="base_matrices"):
    """
    Searches for the correct base matrix file in the specified folder.
    
    Parameters:
        bg (str): Selected Base Graph ("BG1" or "BG2").
        zc (int): Selected expansion factor Zc.
        folder_path (str): Path to the folder containing base matrix files.
    
    Returns:
        str: The full path of the matching file if found, else None.
    """
    # give the realtive address of the search folder path
    folder_path = os.path.join(os.path.dirname(__file__), folder_path)
    #print(folder_path)

    # Convert BG to the expected number in filename (BG1 -> 1, BG2 -> 2)
    bg_num = 1 if bg == "BG1" else 2

    # Regex pattern to match the required file name
    pattern = re.compile(rf"NR_{bg_num}_.+_{zc}\.txt")

    # Search for the file in the given folder
    if os.path.exists(folder_path):
        for file_name in os.listdir(folder_path):
            if pattern.match(file_name):
                return os.path.join(folder_path, file_name)

    return None  # Return None if no matching file is found

def calculate_mb_nb(K, N, bg):
    """
    Calculates the number of rows (mb) and columns (nb) of the parity check matrix.

    Parameters:
        K (int): Output size.
        N (int): Input size.
        bg (str): Base graph, either "BG1" or "BG2".

    Returns:
        tuple: (mb, nb)
    """

    # Set kb based on the base graph selection
    if bg == "BG1":
        kb = 22
    else:  # bg == "BG2"
        kb = 10

    # Determine expansion factor Zc
    Zc = K // kb  # Since K = kb * Zc

    # Compute code rate R
    R = K / N

    # Compute mb using the formula
    mb = round((kb / R) - (kb - 2))  # Ensure it's an integer

    # Compute nb
    nb = mb + kb

    return mb, nb
