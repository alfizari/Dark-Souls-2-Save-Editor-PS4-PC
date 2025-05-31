## ALL THIS SCRIPT IS FROM JTESTA AT GITHUB: https://github.com/jtesta/souls_givifier. A MODFIED VERSION OF THE SCRIPT TO HANDE DECRYPT AND ENCRYPT OF THE DS2 SL2 FILES.
## I HAVE NO IDEA HOW THIS WORKS, I JUST MODIFIED THE SCRIPT TO MAKE IT WORK WITH DS2 SL2 FILES WITH HELP OF CHATGPT.
# I DO NOT TAKE ANY CREDIT FOR THIS SCRIPT, ALL THE CREDIT GOES TO JTESTA.
# IF YOU WANT TO USE IT ON IT'S OWN, YOU COULD CALL decrypt_ds2_sl2() AND encrypt_ds2_sl2() TO DECRYPT AND ENCRYPT THE DS2 SL2 FILES.

import os
import sys
import struct
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Dict, List, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from typing import Optional
# The key to encrypt/decrypt SL2 files from Dark Souls 2: Scholar of the First Sin.
DS2_KEY = b'\x59\x9f\x9b\x69\x96\x40\xa5\x52\x36\xee\x2d\x70\x83\x5e\xc7\x44'
DEBUG_MODE = True
input_file = None

def bytes_to_intstr(byte_array: bytes) -> str:
    ret = ''
    for _, i in enumerate(byte_array):
        ret += "%u," % i
    return ret[0:-1]


def debug(msg: str = '') -> None:
    if DEBUG_MODE:
        print(msg)


def calculate_md5(data: bytes) -> bytes:
    '''Calculate MD5 hash of the data'''
    return hashlib.md5(data).digest()


class BND4Entry:
    '''main to do decrypt,encrypt, and get slot occupancy'''

    def __init__(self, _raw: bytes, _index: int, _decrypted_slot_path: Optional[str], _size: int, _data_offset: int, _name_offset: int, _footer_length: int) -> None:
        self.raw = _raw
        self.index = _index
        self._decrypted_slot_path = _decrypted_slot_path
        self.size = _size
        self.data_offset = _data_offset
        self.name_offset = _name_offset
        self.footer_length = _footer_length

        # Handle name more carefully - get raw bytes first
        name_bytes = self.raw[self.name_offset:self.name_offset + 24]
        # Find null terminator
        null_pos = name_bytes.find(b'\x00')
        if null_pos != -1:
            name_bytes = name_bytes[:null_pos]
        
        # Try to decode, fall back to a safe name if it fails
        try:
            self._name = name_bytes.decode('utf-8').strip()
            if not self._name:  # If empty after stripping
                self._name = f"entry_{self.index}"
        except UnicodeDecodeError:
            self._name = f"entry_{self.index}"
        
        # Ensure name is valid as a filename
        for char in '<>:"/\\|?*':
            self._name = self._name.replace(char, '_')
            
        self._iv = self.raw[self.data_offset + 16:self.data_offset + 32]
        self._encrypted_data = self.raw[self.data_offset + 16:self.data_offset + self.size]
        self._decrypted_data = b''

        self._checksum = self.raw[self.data_offset:self.data_offset + 16]
        self.decrypted = False
        self._decrypted_data_length = 0

        self.character_name = ''
        self.occupied = False

        debug(f"IV for BNDEntry #{self.index}: {bytes_to_intstr(self._iv)}")
    def custom_pkcs7_padding(self) -> bytes:
        '''Returns some kind of customized PKCS#7 padding.'''

        pad_len = 16 - ((len(self._decrypted_data) + 4) % 16)

        # If it was already aligned to the block size (16), then no padding needed.
        if pad_len == 16:
            return b''

        return struct.pack('B', pad_len) * pad_len
    

    def decrypt(self) -> None:
        '''Decrypts this BND4 entry, and saves it to the output directory if specified.'''
        
        try:
            # Decrypt with AES-128 in CBC mode using the DS2 key
            decryptor = Cipher(algorithms.AES128(DS2_KEY), modes.CBC(self._iv)).decryptor()
            self._decrypted_data = decryptor.update(self._encrypted_data) + decryptor.finalize()

            # The length of the decrypted record is an integer at offset 16-20.
            if len(self._decrypted_data) >= 20:
                self._decrypted_data_length = struct.unpack("<i", self._decrypted_data[16:20])[0]
                
                if self._decrypted_data_length < 0 or self._decrypted_data_length > len(self._decrypted_data):
                    debug(f"Invalid decrypted data length: {self._decrypted_data_length}")
                    self._decrypted_data_length = len(self._decrypted_data) - 20
                
                self._decrypted_data = self._decrypted_data[20:]

                if len(self._decrypted_data) >= self._decrypted_data_length:
                    self._decrypted_data = self._decrypted_data[0:self._decrypted_data_length]
            else:
                debug(f"Decrypted data too short to read length: {len(self._decrypted_data)} bytes")
                self._decrypted_data = self._decrypted_data[16:] if len(self._decrypted_data) > 16 else b''
                
            if self._decrypted_slot_path is not None and self._decrypted_data:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                self._decrypted_slot_path = os.path.join(script_dir, "decrypted_output")

                if not os.path.isdir(self._decrypted_slot_path):
                    debug(f"Decrypted slot path {self._decrypted_slot_path} does not exist. Creating it...")
                    os.makedirs(self._decrypted_slot_path)

                # Use index-based filename - NO COUNTER LOOP
                filename = f"USERDATA_{self.index:02d}"
                slot_full_path = os.path.join(self._decrypted_slot_path, filename)
                
                debug(f"Writing decrypted data to {slot_full_path}...")
                with open(slot_full_path, 'wb') as output:
                    output.write(self._decrypted_data)
                    
            self.decrypted = True
            
        except Exception as e:
            debug(f"Error in decrypt method: {str(e)}")
            raise
        
    
    def ds2_get_slot_occupancy(self) -> Dict[int, str]:
        '''For Dark Souls II saves, reads the first BND4 entry to determine which save slots are occupied.'''

        if self.index != 0:
            print("ERROR: ds2_get_slot_occupancy() can only be called on entry #0!")
            sys.exit(-1)

        if not self.decrypted:
            self.decrypt()

        _slot_occupancy = {}
        for index in range(0, 10):
            if self._decrypted_data[892 + (496 * index)] != 0:
                name_offset = 1286 + (496 * index)
                name_bytes = self._decrypted_data[name_offset:name_offset + (14 * 2)]

                # If the name bytes contain a null byte, truncate it and everything after.
                null_pos = name_bytes.find(b'\x00\x00')
                if null_pos != -1:
                    name_bytes = name_bytes[0:null_pos + 1]

                _slot_occupancy[index + 1] = name_bytes.decode('utf-16')

        debug("ds2_get_slot_occupancy() returning: %s" % _slot_occupancy)
        return _slot_occupancy
    def encrypt_data(self, raw: bytes, all_entries: list) -> bytes:
        """
        Encrypt the data and update the BND4 structure properly.
        all_entries parameter is needed to update subsequent entry offsets.
        """
        key = DS2_KEY
        self._decrypted_data = self.load_modified_data()
        
        encryptor = Cipher(algorithms.AES128(key), modes.CBC(self._iv)).encryptor()
        length_prefix = struct.pack("<I", len(self._decrypted_data))
        padding = self.custom_pkcs7_padding()
        encrypted_payload = encryptor.update(length_prefix + self._decrypted_data + padding) + encryptor.finalize()

        self._encrypted_data = self._iv + encrypted_payload
        self._checksum = hashlib.md5(self._encrypted_data).digest()

        old_size = self.size
        new_entry_size = len(self._encrypted_data)
        size_difference = new_entry_size - old_size

        # Update raw data with new encrypted content
        new_raw = (
            raw[:self.data_offset] +
            self._checksum +
            self._encrypted_data +
            raw[self.data_offset + old_size:]
        )

        # If size changed, update headers
        if size_difference != 0:
            # 1. Update this entry's size in its header
            header_offset = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * self.index)
            new_raw = (
                new_raw[:header_offset + 8] +
                struct.pack("<I", new_entry_size) +
                new_raw[header_offset + 12:]
            )
            
            # 2. Update data offsets for all subsequent entries
            for other_entry in all_entries:
                if other_entry.index > self.index:
                    # Update the data offset in the header
                    other_header_offset = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * other_entry.index)
                    old_data_offset = other_entry.data_offset
                    new_data_offset = old_data_offset + size_difference
                    
                    # Update the data offset in the BND4 header (offset 16-20 in entry header)
                    new_raw = (
                        new_raw[:other_header_offset + 16] +
                        struct.pack("<I", new_data_offset) +
                        new_raw[other_header_offset + 20:]
                    )
                    
                    # Update the entry object's data_offset for future operations
                    other_entry.data_offset = new_data_offset
            
            # Update this entry's size
            self.size = new_entry_size

        return new_raw
    def load_modified_data(self) -> bytes:
        """Load the modified decrypted data from file based on entry index"""
        if self._decrypted_slot_path is None:
            raise ValueError("No decrypted slot path set")
        
        expected_filename = f"USERDATA_{self.index:02d}"
        file_path = os.path.join(self._decrypted_slot_path, expected_filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                modified_data = f.read()
            debug(f"Loaded modified data from {file_path} (size: {len(modified_data)})")
            return modified_data
        else:
            raise FileNotFoundError(f"Expected file {expected_filename} not found at {file_path}")
import json
def process_entries_in_order(entries):
        # Sort entries by index to ensure consistent processing order
        sorted_entries = sorted(entries, key=lambda e: e.index)
        debug(f"Processing {len(sorted_entries)} entries in index order")
        
        for entry in sorted_entries:
            debug(f"Processing entry {entry.index}: {entry._name}")
            entry.decrypt()
        
        return sorted_entries
def save_index_mapping(entries, output_path):
    mapping = {}
    for entry in entries:
        if entry.decrypted:
            # Assuming you're using the index-based filename from solution 1
            filename = f"USERDATA_{entry.index:02d}"
            mapping[entry.index] = filename
    
    mapping_file = os.path.join(output_path, "index_mapping.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f)
    debug(f"Saved index mapping to {mapping_file}")
def get_input() -> Optional[str]:
    return filedialog.askopenfilename(
        title="Select Decrypted SL2 File",
        filetypes=[("SL2 Files", "*.sl2"), ("All Files", "*.*")]
    )


def decrypt_ds2_sl2(log_callback=None) -> Dict[int, str]:
    """Main function to decrypt a Dark Souls 2 SL2 save file."""
    global original_sl2_path
    global input_decrypted_path
    global bnd4_entries
    global input_file
    if not input_file:
        input_file = get_input()  # Prompt only once

    if not input_file:
        return None

    original_sl2_path = input_file

    def log(message):
        if log_callback:
            log_callback(message)
        debug(message)

    try:
        with open(input_file, 'rb') as f:
            raw = f.read()
    except Exception as e:
        log(f"ERROR: Could not read input file: {e}")
        return {}
    
    raw = b''
    try:
        with open(input_file, 'rb') as f:
            raw = f.read()
    except Exception as e:
        log(f"ERROR: Could not read input file: {e}")
        return {}

    log(f"Read {len(raw)} bytes from {input_file}.")
    if raw[0:4] != b'BND4':
        log("ERROR: 'BND4' header not found! This doesn't appear to be a valid SL2 file.")
        return {}
    else:
        log("Found BND4 header.")

    num_bnd4_entries = struct.unpack("<i", raw[12:16])[0]
    log(f"Number of BND4 entries: {num_bnd4_entries}")

    unicode_flag = (raw[48] == 1)
    log(f"Unicode flag: {unicode_flag}")
    log("")

    BND4_HEADER_LEN = 64
    BND4_ENTRY_HEADER_LEN = 32

    slot_occupancy = {}
    bnd4_entries = []
    successful_decryptions = 0

    # Process all BND4 entries
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, "decrypted_output")
    input_decrypted_path=output_folder
    for i in range(num_bnd4_entries):
        pos = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * i)
        
        # Make sure we have enough data to read the entry header
        if pos + BND4_ENTRY_HEADER_LEN > len(raw):
            log(f"Warning: File too small to read entry #{i} header")
            break
            
        entry_header = raw[pos:pos + BND4_ENTRY_HEADER_LEN]

        if entry_header[0:8] != b'\x50\x00\x00\x00\xff\xff\xff\xff':
            log(f"Warning: Entry header #{i} does not match expected magic value - skipping")
            continue

        entry_size = struct.unpack("<i", entry_header[8:12])[0]
        entry_data_offset = struct.unpack("<i", entry_header[16:20])[0]
        entry_name_offset = struct.unpack("<i", entry_header[20:24])[0]
        entry_footer_length = struct.unpack("<i", entry_header[24:28])[0]
        
        # Validity checks
        if entry_size <= 0 or entry_size > 1000000000:  # Sanity check for size
            log(f"Warning: Entry #{i} has invalid size: {entry_size} - skipping")
            continue
            
        if entry_data_offset <= 0 or entry_data_offset + entry_size > len(raw):
            log(f"Warning: Entry #{i} has invalid data offset: {entry_data_offset} - skipping")
            continue
            
        if entry_name_offset <= 0 or entry_name_offset >= len(raw):
            log(f"Warning: Entry #{i} has invalid name offset: {entry_name_offset} - skipping")
            continue

        log(f"Processing Entry #{i} (Size: {entry_size}, Offset: {entry_data_offset})")

        try:
            entry = BND4Entry(raw, i, output_folder, entry_size, entry_data_offset, entry_name_offset, entry_footer_length)

            
            # Decrypt this entry
            try:
                entry.decrypt()
                bnd4_entries.append(entry)
                successful_decryptions += 1
                log(f"Successfully decrypted entry #{i}: {entry._name}")
            except Exception as e:
                log(f"Error decrypting entry #{i}: {str(e)}")
                continue

            # Get slot occupancy information from the first entry
            if i == 0:
                try:
                    slot_occupancy = entry.ds2_get_slot_occupancy()
                except Exception as e:
                    log(f"Error getting slot occupancy: {str(e)}")
                    
        except Exception as e:
            log(f"Error processing entry #{i}: {str(e)}")
            continue

    # Print information about occupied slots
    if slot_occupancy:
        log("\nOccupied save slots:")
        for slot, name in slot_occupancy.items():
            log(f"Slot #{slot} occupied; character name: [{name}]")
    else:
        log("\nNo occupied save slots found.")
        
    # Even without occupied slots, report on the decryption
    log(f"\nDONE! Successfully decrypted {successful_decryptions} of {num_bnd4_entries} entries.")
    save_index_mapping(bnd4_entries, input_decrypted_path)

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "decrypted_output")




    
    
def get_output() -> Optional[str]:
    filename = filedialog.asksaveasfilename(
        title="Save Encrypted SL2 File As",
        filetypes=[("SL2 Files", "*.sl2"), ("All Files", "*.*")],
        defaultextension=".sl2",
        initialfile="DS2SOFS0000.sl2"
    )
    if filename:
        print(f"Selected output SL2 file: {filename}")  # Or use logging
        return filename
    return None

raw = b''
def read_input():
    global input_file, raw

    if not input_file:
        print("ERROR: input_file is not set. Call decrypt_ds2_sl2() first.")
        sys.exit(1)

    original_sl2_path = input_file

    with open(original_sl2_path, 'rb') as f:
        raw = f.read()

    debug("Read %u bytes from %s." % (len(raw), original_sl2_path))

    if raw[0:4] != b'BND4':
        print("ERROR: 'BND4' header not found!")
        sys.exit(-1)
    else:
        debug("Found BND4 header.")

    num_bnd4_entries = struct.unpack("<i", raw[12:16])[0]
    debug("Number of BND4 entries: %u" % num_bnd4_entries)

    unicode_flag = (raw[48] == 1)
    debug("Unicode flag: %r" % unicode_flag)
    debug()

    return raw, num_bnd4_entries, unicode_flag


slot_occupancy = {}
bnd4_entries = []
BND4_HEADER_LEN = 64
BND4_ENTRY_HEADER_LEN = 32

# Do the first pass over all BND4 entries to decrypt them all, and acquire the list of occupied slots.


def encrypt_modified_files(output_sl2_file: str):
    """Alternative version that preserves BND4 headers more precisely"""
    global raw, bnd4_entries, original_sl2_path
    
    with open(original_sl2_path, 'rb') as f:
        original_raw = f.read()
    
    print(f"Original file size: {len(original_raw)} bytes")
    
    # Work with a copy of original data
    new_raw = bytearray(original_raw)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, "decrypted_output")
    
    # Load modified files
    for entry in bnd4_entries:
        expected_filename = f"USERDATA_{entry.index:02d}"
        edited_path = os.path.join(output_folder, expected_filename)
        
        if os.path.exists(edited_path):
            with open(edited_path, "rb") as f:
                modified_data = f.read()
                
            # Re-encrypt the modified data
            key = DS2_KEY
            encryptor = Cipher(algorithms.AES128(key), modes.CBC(entry._iv)).encryptor()
            length_prefix = struct.pack("<I", len(modified_data))
            
            # Calculate padding
            pad_len = 16 - ((len(modified_data) + 4) % 16)
            if pad_len == 16:
                padding = b''
            else:
                padding = struct.pack('B', pad_len) * pad_len
            
            encrypted_payload = encryptor.update(length_prefix + modified_data + padding) + encryptor.finalize()
            encrypted_data = entry._iv + encrypted_payload
            checksum = hashlib.md5(encrypted_data).digest()
            
            # Replace only the data section, preserve all headers
            data_start = entry.data_offset
            data_end = entry.data_offset + entry.size
            
            new_raw[data_start:data_start + 16] = checksum
            new_raw[data_start + 16:data_end] = encrypted_data
            
            print(f"✓ Re-encrypted {expected_filename} in place")
    
    # Preserve the critical first 783 bytes from original
    HEADER_PRESERVE_SIZE = 783
    final_raw = original_raw[:HEADER_PRESERVE_SIZE] + bytes(new_raw[HEADER_PRESERVE_SIZE:])
    
    with open(output_sl2_file, 'wb') as output:
        output.write(final_raw)
    print(f"Successfully saved with preserved headers to: {output_sl2_file}")




