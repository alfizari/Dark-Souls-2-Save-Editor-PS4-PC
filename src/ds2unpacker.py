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

# The key to encrypt/decrypt SL2 files from Dark Souls 2: Scholar of the First Sin.
DS2_KEY = b'\x59\x9f\x9b\x69\x96\x40\xa5\x52\x36\xee\x2d\x70\x83\x5e\xc7\x44'
DEBUG_MODE = False


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

    def decrypt(self) -> None:
        '''Decrypts this BND4 entry, and saves it to the output directory if specified.'''
        
        try:
            
            # Decrypt with AES-128 in CBC mode using the DS2 key
            decryptor = Cipher(algorithms.AES128(DS2_KEY), modes.CBC(self._iv)).decryptor()
            self._decrypted_data = decryptor.update(self._encrypted_data) + decryptor.finalize()

            # The length of the decrypted record is an integer at offset 16-20.
            # Make sure we have enough data to read the length
            if len(self._decrypted_data) >= 20:
                self._decrypted_data_length = struct.unpack("<i", self._decrypted_data[16:20])[0]
                
                # Additional validity check - if length is negative or unreasonably large
                if self._decrypted_data_length < 0 or self._decrypted_data_length > len(self._decrypted_data):
                    debug(f"Invalid decrypted data length: {self._decrypted_data_length}")
                    # Use the actual size of the buffer minus header
                    self._decrypted_data_length = len(self._decrypted_data) - 20
                
                # Skip the first 16 bytes (that's the IV that was decrypted into meaningless data), and also skip the length field we read above.
                self._decrypted_data = self._decrypted_data[20:]

                # There is some postfix that should be removed.
                if len(self._decrypted_data) >= self._decrypted_data_length:
                    self._decrypted_data = self._decrypted_data[0:self._decrypted_data_length]
            else:
                debug(f"Decrypted data too short to read length: {len(self._decrypted_data)} bytes")
                # Just use what we have
                self._decrypted_data = self._decrypted_data[16:] if len(self._decrypted_data) > 16 else b''
            if self._decrypted_slot_path is not None and self._decrypted_data:
                script_dir = os.path.dirname(os.path.abspath(__file__))

                # Set decrypted output folder relative to script
                self._decrypted_slot_path = os.path.join(script_dir, "decrypted_output")

                # Now create it if it doesn't exist
                if self._decrypted_slot_path is not None and self._decrypted_data:
                    if not os.path.isdir(self._decrypted_slot_path):
                        debug(f"Decrypted slot path {self._decrypted_slot_path} does not exist. Creating it...")
                        os.makedirs(self._decrypted_slot_path)

                # Ensure filename is valid and unique
                filename = f"{'USERDATA'}"
                
                slot_full_path = os.path.join(self._decrypted_slot_path, filename)
                
                # Ensure unique filename by adding a number if file exists
                counter = 1
                base_path = slot_full_path
                for counter in range(1, 23):
                    if not os.path.exists(slot_full_path):
                        break
                    slot_full_path = f"{base_path}{counter}"
                    counter += 1
                
                debug(f"Writing decrypted data to {slot_full_path}...")
                with open(slot_full_path, 'wb') as output:
                    output.write(self._decrypted_data)
                    
            # Set the decrypted flag.
            self.decrypted = True
            
        except Exception as e:
            debug(f"Error in decrypt method: {str(e)}")
            raise
    
    def ds2_get_slot_occupancy(self) -> Dict[int, str]:
        '''For Dark Souls II saves, reads the first BND4 entry to determine which save slots are occupied.'''

        if self.index != 0:
            debug("ERROR: ds2_get_slot_occupancy() can only be called on entry #0!")
            return {}

        if not self.decrypted:
            self.decrypt()
            
        # Skip if decryption failed or data is too small
        if not self.decrypted or len(self._decrypted_data) < 1300:
            debug(f"Cannot get slot occupancy - decrypted data too small: {len(self._decrypted_data)} bytes")
            return {}

        _slot_occupancy = {}
        try:
            for index in range(0, 10):
                offset_check = 892 + (496 * index)
                offset_name = 1286 + (496 * index)
                
                # Make sure we have enough data to check these offsets
                if offset_check >= len(self._decrypted_data) or offset_name + 28 >= len(self._decrypted_data):
                    debug(f"Skipping slot {index+1} - data too small")
                    continue
                
                if self._decrypted_data[offset_check] != 0:
                    name_bytes = self._decrypted_data[offset_name:offset_name + (14 * 2)]

                    # If the name bytes contain a null byte, truncate it and everything after.
                    null_pos = name_bytes.find(b'\x00\x00')
                    if null_pos != -1:
                        name_bytes = name_bytes[0:null_pos + 1]

                    try:
                        char_name = name_bytes.decode('utf-16')
                        _slot_occupancy[index + 1] = char_name
                    except UnicodeDecodeError:
                        _slot_occupancy[index + 1] = f"Character_{index+1}"
        except Exception as e:
            debug(f"Error in ds2_get_slot_occupancy: {str(e)}")
            # Continue with whatever slots we found

        debug(f"ds2_get_slot_occupancy() returning: {_slot_occupancy}")
        return _slot_occupancy
def get_input() -> dict[str]:
    """Get input from the user for the SL2 file to decrypt."""
    input_file = filedialog.askopenfilename(
        title="Select Dark Souls 2 SL2 File",
        filetypes=[("SL2 Files", "*.sl2"), ("All Files", "*.*")]
    )
    if not input_file:
        messagebox.showerror("Error", "No input file selected.")
        return None
    return input_file
original_sl2_path = None

def decrypt_ds2_sl2(log_callback=None) -> Dict[int, str]:
    """Main function to decrypt a Dark Souls 2 SL2 save file."""
    global original_sl2_path
    global input_decrypted_path
    input_file=get_input()
    if not input_file:
        return None  # Stop if no file was selected
    original_sl2_path = input_file
    def log(message):
        """Helper to log messages both to console and GUI"""
        if log_callback:
            log_callback(message)
        debug(message)
    
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
 
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "decrypted_output")



def encrypt_data(data: bytes, iv: bytes = None) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt the provided data using AES-128-CBC
    Returns: (checksum, iv, encrypted_data)
    """
    if iv is None:
        # Generate a random IV if none provided
        import os
        iv = os.urandom(16)
    
    # Calculate the length of the data and pack it at the beginning
    data_len = len(data)
    data_with_len = struct.pack("<i", data_len) + data
    
    # Add padding to ensure data is a multiple of 16 bytes (AES block size)
    padding_needed = 16 - (len(data_with_len) % 16)
    if padding_needed < 16:
        data_with_len += b'\x00' * padding_needed
    
    # Encrypt the data
    encryptor = Cipher(algorithms.AES128(DS2_KEY), modes.CBC(iv)).encryptor()
    encrypted_data = encryptor.update(data_with_len) + encryptor.finalize()
    
    # Calculate MD5 checksum of the encrypted data
    checksum = calculate_md5(encrypted_data)
    
    return checksum, iv, encrypted_data
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


def encrypt_ds2_sl2(log_callback=None) -> bool:
    """Main function to encrypt decrypted Dark Souls 2 save files back into an SL2 file."""
    global original_sl2_path
    global input_decrypted_path
    
    if original_sl2_path is None:
        log("ERROR: No original SL2 file provided for encryption.")
        return False
    original_sl2_file = original_sl2_path
    def log(message):
        """Helper to log messages both to console and GUI"""
        if log_callback:
            log_callback(message)
        debug(message)
    
    # First, read the original SL2 file to use as a template
    try:
        with open(original_sl2_file, 'rb') as f:
            original_data = f.read()
    except Exception as e:
        log(f"ERROR: Could not read original SL2 file: {e}")
        return False
    
    if original_data[0:4] != b'BND4':
        log("ERROR: Original file is not a valid SL2/BND4 file.")
        return False
    
    # Get basic header information
    num_entries = struct.unpack("<i", original_data[12:16])[0]
    log(f"Original SL2 file has {num_entries} entries.")
    
    # Constants
    BND4_HEADER_LEN = 64
    BND4_ENTRY_HEADER_LEN = 32
    input_directory= input_decrypted_path
    # Scan for decrypted files in the input directory
    decrypted_files = []
    try:
        for filename in os.listdir(input_directory):
            if os.path.isfile(os.path.join(input_directory, filename)):
                decrypted_files.append(filename)
    except Exception as e:
        log(f"ERROR: Could not read files in input directory: {e}")
        return False
    
    log(f"Found {len(decrypted_files)} files in decrypted directory.")
    
    # Create a new BND4 file structure
    new_bnd4_data = bytearray(original_data)  # Start with a copy of the original
    
    # Process each BND4 entry in the original file and replace with encrypted data
    for i in range(num_entries):
        pos = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * i)
        
        # Read header info
        entry_header = original_data[pos:pos + BND4_ENTRY_HEADER_LEN]
        entry_size = struct.unpack("<i", entry_header[8:12])[0]
        entry_data_offset = struct.unpack("<i", entry_header[16:20])[0]
        entry_name_offset = struct.unpack("<i", entry_header[20:24])[0]
        
        # Get the entry name
        name_bytes = original_data[entry_name_offset:entry_name_offset + 24]
        null_pos = name_bytes.find(b'\x00')
        if null_pos != -1:
            name_bytes = name_bytes[:null_pos]
        
        try:
            entry_name = name_bytes.decode('utf-8').strip()
            if not entry_name:
                entry_name = f"entry_{i}"
        except UnicodeDecodeError:
            entry_name = f"entry_{i}"
        
        for char in '<>:"/\\|?*':
            entry_name = entry_name.replace(char, '_')
        
        # Get original IV from the entry
        original_iv = original_data[entry_data_offset + 16:entry_data_offset + 32]
        
        # Find matching decrypted file
        matching_file = None
        for file in decrypted_files:
            base_name = os.path.splitext(file)[0]
            if base_name == entry_name or file == entry_name:
                matching_file = file
                break
        
        if matching_file:
            log(f"Found matching decrypted file for entry #{i}: {matching_file}")
            
            # Read the decrypted file
            with open(os.path.join(input_directory, matching_file), 'rb') as f:
                decrypted_data = f.read()
            
            # Encrypt the data with the original IV
            checksum, iv, encrypted_data = encrypt_data(decrypted_data, original_iv)
            
            # Replace the checksum in the file
            new_bnd4_data[entry_data_offset:entry_data_offset + 16] = checksum
            
            # Replace the encrypted data in the file (starting after the checksum)
            new_bnd4_data[entry_data_offset + 16:entry_data_offset + 16 + len(encrypted_data)] = encrypted_data
            
            # Update the entry size in the header if needed
            new_size = len(encrypted_data) + 16  # Add checksum length
            
            # Update the data in the file while maintaining its original size
            data_to_write = checksum + encrypted_data
            if len(data_to_write) <= entry_size:
                # If new data is smaller, pad it to match original size
                padding = b'\x00' * (entry_size - len(data_to_write))
                new_bnd4_data[entry_data_offset:entry_data_offset + entry_size] = data_to_write + padding
            else:
                # If new data is larger, we do need to update the size (but this is risky)
                new_bnd4_data[entry_data_offset:entry_data_offset + len(data_to_write)] = data_to_write
                new_bnd4_data[pos + 8:pos + 12] = struct.pack("<i", new_size)
                log(f"Warning: Entry #{i} size increased from {entry_size} to {new_size} - this may cause issues")
            
            log(f"Successfully encrypted entry #{i}")
        else:
            log(f"No matching decrypted file found for entry #{i}: {entry_name}")
    
    # Write the new SL2 file
    try:
        output_file = get_output()
        if not output_file:
            log("ERROR: No output file specified.")
            return False
        with open(output_file, 'wb') as f:
            f.write(new_bnd4_data)
        log(f"Successfully wrote encrypted SL2 file to: {output_file}")
        return True
    except Exception as e:
        log(f"ERROR: Could not write encrypted SL2 file: {e}")
        return False
