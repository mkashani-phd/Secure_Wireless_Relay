import numpy as np


def hex_to_bits(hex_string):
    binary_list = []
    for hex_char in hex_string:
        # Convert each hex character to a 4-bit binary string
        binary_list.extend([int(bit) for bit in format(int(hex_char, 16), '04b')])
    return binary_list

def bits_to_hex(binary_list):
    # Ensure the length of the list is a multiple of 4
    if len(binary_list) % 4 != 0:
        raise ValueError("The length of the binary list must be a multiple of 4.")
    
    # Group into chunks of 4 bits and convert to hex
    hex_string = ''.join(
        hex(int(''.join(map(str, binary_list[i:i+4])), 2))[2:]  # Convert binary to hex and remove "0x"
        for i in range(0, len(binary_list), 4)
    )
    return hex_string.lower()  # Convert to uppercase if desired

def string_to_bits(s):
    bits = []
    for char in s:
        bin_repr = format(ord(char), '08b')  # 8-bit binary
        bits.extend([int(b) for b in bin_repr])
    return bits

def bits_to_string(bit_list):
        chars = []
        for i in range(0, len(bit_list), 8):
            byte_bits = bit_list[i:i+8]
            if len(byte_bits) < 8:
                break
            val = 0
            for b in byte_bits:
                val = (val << 1) | b
            chars.append(chr(val))
        return "".join(chars)






 


