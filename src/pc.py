## ALL THIS SCRIPT IS FROM JTESTA AT GITHUB: https://github.com/jtesta/souls_givifier.
## MODIFIED VERSION TO HANDLE DECRYPT AND ENCRYPT OF DS2 SL2 FILES.
## ALL CREDIT GOES TO JTESTA AND Nordgaren: https://github.com/Nordgaren/ArmoredCore6SaveTransferTool

import os
import sys
import struct
import hashlib
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Dict, List
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# The key to encrypt/decrypt SL2 files from Dark Souls 2: Scholar of the First Sin.
DS2_KEY = b'\x59\x9f\x9b\x69\x96\x40\xa5\x52\x36\xee\x2d\x70\x83\x5e\xc7\x44'

DEBUG_MODE = True
input_file = None

# ------------------------------------------------------------------
# DS2 SL2 entry blob layout:
#
#   blob[0:16]   = MD5 checksum of blob[16:]  (i.e. MD5(IV + ciphertext))
#   blob[16:32]  = IV  (AES-CBC initialisation vector)
#   blob[32:]    = ciphertext
#
# Plaintext layout (what is encrypted):
#   [0:4]        = uint32 LE — length N of the actual game data
#   [4:4+N]      = actual game data
#   [4+N:]       = padding bytes to reach a 16-byte boundary
#                  pad_len = (16 - ((N+4) % 16)) % 16
#                  pad byte value = pad_len  (0x00 when pad_len == 0, i.e. no padding)
#
# On decrypt the length prefix tells us exactly how many bytes to take;
# trailing padding is ignored entirely.
# ------------------------------------------------------------------

CHECKSUM_OFFSET = 0
CHECKSUM_SIZE   = 16
IV_OFFSET       = 16
IV_SIZE         = 16
PAYLOAD_OFFSET  = 32   # ciphertext starts here

BND4_HEADER_LEN       = 64
BND4_ENTRY_HEADER_LEN = 32


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def bytes_to_intstr(byte_array: bytes) -> str:
    return ','.join(str(b) for b in byte_array)


def debug(msg: str = '') -> None:
    if DEBUG_MODE:
        print(msg)


def _make_padding(data_len: int) -> bytes:
    """Return padding so that 4 + data_len + len(padding) is a multiple of 16.
    When already aligned returns b'' (no padding).
    Padding byte value equals the padding length.
    """
    pad_len = (16 - ((data_len + 4) % 16)) % 16
    if pad_len == 0:
        return b''
    return bytes([pad_len] * pad_len)


# ──────────────────────────────────────────────────────────────────
# BND4Entry
# ──────────────────────────────────────────────────────────────────

class BND4Entry:
    """Handles decrypt, encrypt, and slot-occupancy queries for one BND4 entry."""

    def __init__(self, raw_data: bytes, index: int, output_folder: str,
                 size: int, offset: int, name_offset: int,
                 footer_length: int, data_offset: int) -> None:
        self.index         = index
        self.size          = size           # total blob size (checksum + IV + ciphertext)
        self.data_offset   = data_offset    # offset of the blob inside the full SL2 file
        self.footer_length = footer_length
        self.decrypted     = False

        # Full entry blob as a slice of the raw file
        self._entry_blob = raw_data[offset:offset + size]

        self._decrypted_slot_path = output_folder
        self._name       = f"USERDATA_{index:02d}"
        self._clean_data = b''             # decrypted game data (no prefix, no padding)

        # Pull IV and ciphertext using the named offsets
        self._iv         = self._entry_blob[IV_OFFSET:IV_OFFSET + IV_SIZE]
        self._ciphertext = self._entry_blob[PAYLOAD_OFFSET:]

        debug(f"IV for BND4Entry #{self.index}: {self._iv.hex()}")

    # ------------------------------------------------------------------
    # Decrypt
    # ------------------------------------------------------------------
    def decrypt(self) -> None:
        """Decrypt this BND4 entry and write the raw game data to disk.

        Ciphertext is at blob[32:].
        After AES-CBC decrypt the plaintext is [4B length][data][padding].
        We read the length prefix to extract exactly the game data bytes.
        """
        try:
            decryptor = Cipher(
                algorithms.AES(DS2_KEY), modes.CBC(self._iv)
            ).decryptor()
            plain = decryptor.update(self._ciphertext) + decryptor.finalize()

            if len(plain) < 4:
                raise ValueError(f"Decrypted data too short ({len(plain)} bytes)")

            data_len = struct.unpack("<I", plain[0:4])[0]

            if data_len > len(plain) - 4:
                raise ValueError(
                    f"Length prefix {data_len} exceeds available plaintext "
                    f"({len(plain) - 4} bytes)"
                )

            # Extract exactly N bytes; trailing padding is ignored
            self._clean_data = plain[4:4 + data_len]

            if self._decrypted_slot_path:
                os.makedirs(self._decrypted_slot_path, exist_ok=True)
                output_path = os.path.join(self._decrypted_slot_path, self._name)
                debug(f"Writing decrypted data to {output_path}...")
                with open(output_path, 'wb') as f:
                    f.write(self._clean_data)

            self.decrypted = True
            debug(f"Successfully decrypted entry #{self.index}: {self._name} ({data_len} bytes)")

        except Exception as e:
            debug(f"Error decrypting entry #{self.index}: {e}")
            raise

    # ------------------------------------------------------------------
    # Encrypt + sign
    # ------------------------------------------------------------------
    def encrypt_sl2_data(self) -> bytes:
        """Build the encrypted, signed blob from _clean_data.

        Plaintext = [4B LE length][data][padding]
        Padding   = _make_padding(len(data))

        Returns: checksum(16) + IV(16) + ciphertext
        """
        data    = self._clean_data
        padding = _make_padding(len(data))
        plain   = struct.pack("<I", len(data)) + data + padding

        encryptor = Cipher(
            algorithms.AES(DS2_KEY), modes.CBC(self._iv)
        ).encryptor()
        ciphertext = encryptor.update(plain) + encryptor.finalize()

        # Checksum = MD5(IV + ciphertext)  — covers everything after the checksum field
        iv_plus_ct = self._iv + ciphertext
        checksum   = hashlib.md5(iv_plus_ct).digest()

        return checksum + iv_plus_ct    # [checksum(16)][IV(16)][ciphertext]

    # ------------------------------------------------------------------
    # Slot occupancy (entry #0 only)
    # ------------------------------------------------------------------
    def ds2_get_slot_occupancy(self) -> Dict[int, str]:
        """Read the first BND4 entry to determine which save slots are occupied."""
        if self.index != 0:
            raise RuntimeError("ds2_get_slot_occupancy() can only be called on entry #0!")

        if not self.decrypted:
            self.decrypt()

        slot_occupancy: Dict[int, str] = {}
        for i in range(10):
            if self._clean_data[892 + (496 * i)] != 0:
                name_offset = 1286 + (496 * i)
                name_bytes  = self._clean_data[name_offset:name_offset + (14 * 2)]
                null_pos    = name_bytes.find(b'\x00\x00')
                if null_pos != -1:
                    name_bytes = name_bytes[:null_pos + 1]
                slot_occupancy[i + 1] = name_bytes.decode('utf-16-le', errors='replace')

        debug(f"ds2_get_slot_occupancy() returning: {slot_occupancy}")
        return slot_occupancy


# ──────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────

def process_entries_in_order(entries: List[BND4Entry]) -> List[BND4Entry]:
    sorted_entries = sorted(entries, key=lambda e: e.index)
    for entry in sorted_entries:
        entry.decrypt()
    return sorted_entries


def save_index_mapping(entries: List[BND4Entry], output_path: str) -> None:
    mapping = {
        entry.index: f"USERDATA_{entry.index:02d}"
        for entry in entries if entry.decrypted
    }
    mapping_file = os.path.join(output_path, "index_mapping.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f)
    debug(f"Saved index mapping to {mapping_file}")


def get_input() -> Optional[str]:
    return filedialog.askopenfilename(
        title="Select SL2 File",
        filetypes=[("SL2 Files", "*.sl2"), ("All Files", "*.*")]
    )


def get_output() -> Optional[str]:
    filename = filedialog.asksaveasfilename(
        title="Save Encrypted SL2 File As",
        filetypes=[("SL2 Files", "*.sl2"), ("All Files", "*.*")],
        defaultextension=".sl2",
        initialfile="DS2SOFS0000.sl2"
    )
    if filename:
        print(f"Selected output SL2 file: {filename}")
        return filename
    return None


# ──────────────────────────────────────────────────────────────────
# Globals
# ──────────────────────────────────────────────────────────────────

bnd4_entries:         List[BND4Entry] = []
slot_occupancy:       Dict[int, str]  = {}
original_sl2_path:    str = ''
input_decrypted_path: str = ''


# ──────────────────────────────────────────────────────────────────
# Decrypt
# ──────────────────────────────────────────────────────────────────

def decrypt_ds2_sl2(input_file_path: Optional[str] = None,
                    directory: str = "decrypted_output",
                    log_callback=None) -> Optional[str]:
    """Decrypt a Dark Souls 2 SL2 save file.

    Args:
        input_file_path: Path to the .sl2 file. Prompts via dialog if None.
        directory:       Sub-folder name (relative to script dir) for output.
        log_callback:    Optional callable(str) for GUI log lines.

    Returns:
        Absolute path to the decrypted output folder, or None on failure.
    """
    global original_sl2_path, input_decrypted_path, bnd4_entries, slot_occupancy

    if not input_file_path:
        input_file_path = get_input()
    if not input_file_path:
        return None

    original_sl2_path = input_file_path

    def log(message: str) -> None:
        if log_callback:
            log_callback(message)
        debug(message)

    try:
        with open(input_file_path, 'rb') as f:
            raw_data = f.read()
    except Exception as e:
        log(f"ERROR: Could not read input file: {e}")
        return None

    log(f"Read {len(raw_data)} bytes from {input_file_path}.")

    if raw_data[0:4] != b'BND4':
        log("ERROR: 'BND4' header not found!")
        return None

    log("Found BND4 header.")
    num_bnd4_entries = struct.unpack("<i", raw_data[12:16])[0]
    log(f"Number of BND4 entries: {num_bnd4_entries}")
    unicode_flag = (raw_data[48] == 1)
    log(f"Unicode flag: {unicode_flag}\n")

    script_dir    = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, directory)
    input_decrypted_path = output_folder

    bnd4_entries   = []
    slot_occupancy = {}
    successful     = 0

    for i in range(num_bnd4_entries):
        pos = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * i)

        if pos + BND4_ENTRY_HEADER_LEN > len(raw_data):
            log(f"Warning: File too small to read entry #{i} header")
            break

        eh = raw_data[pos:pos + BND4_ENTRY_HEADER_LEN]

        if eh[0:8] != b'\x50\x00\x00\x00\xff\xff\xff\xff':
            log(f"Warning: Entry #{i} does not match expected magic — skipping")
            continue

        entry_size          = struct.unpack("<i", eh[8:12])[0]
        entry_data_offset   = struct.unpack("<i", eh[16:20])[0]
        entry_name_offset   = struct.unpack("<i", eh[20:24])[0]
        entry_footer_length = struct.unpack("<i", eh[24:28])[0]

        if entry_size <= 0 or entry_size > 1_000_000_000:
            log(f"Warning: Entry #{i} has invalid size {entry_size} — skipping")
            continue
        if entry_data_offset <= 0 or entry_data_offset + entry_size > len(raw_data):
            log(f"Warning: Entry #{i} has invalid data offset {entry_data_offset} — skipping")
            continue
        if entry_name_offset <= 0 or entry_name_offset >= len(raw_data):
            log(f"Warning: Entry #{i} has invalid name offset {entry_name_offset} — skipping")
            continue

        log(f"Processing Entry #{i} (size={entry_size}, offset={entry_data_offset})")

        try:
            entry = BND4Entry(
                raw_data=raw_data,
                index=i,
                output_folder=output_folder,
                size=entry_size,
                offset=entry_data_offset,
                name_offset=entry_name_offset,
                footer_length=entry_footer_length,
                data_offset=entry_data_offset,
            )
            entry.decrypt()
            bnd4_entries.append(entry)
            successful += 1

            if i == 0:
                try:
                    slot_occupancy = entry.ds2_get_slot_occupancy()
                except Exception as e:
                    log(f"Error getting slot occupancy: {e}")

        except Exception as e:
            log(f"Error processing entry #{i}: {e}")
            continue

    if slot_occupancy:
        log("\nOccupied save slots:")
        for slot, name in slot_occupancy.items():
            log(f"  Slot #{slot}: [{name}]")
    else:
        log("\nNo occupied save slots found.")

    log(f"\nDONE! Successfully decrypted {successful}/{num_bnd4_entries} entries.")
    save_index_mapping(bnd4_entries, input_decrypted_path)

    return output_folder


# ──────────────────────────────────────────────────────────────────
# Encrypt
# ──────────────────────────────────────────────────────────────────

def encrypt_modified_files(output_sl2_file: str,
                           directory: str = "decrypted_output") -> None:
    """Re-encrypt modified decrypted files back into a valid SL2.

    Each entry is patched in-place inside a copy of the original file.
    If the re-encrypted blob differs in size from the original the entry
    is skipped — the plaintext length is unchanged so ciphertext size must match.
    """
    global bnd4_entries, original_sl2_path

    if not original_sl2_path:
        print("ERROR: original_sl2_path not set. Call decrypt_ds2_sl2() first.")
        return

    with open(original_sl2_path, 'rb') as f:
        original_data = f.read()

    new_data   = bytearray(original_data)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_folder = os.path.join(script_dir, directory)

    for entry in bnd4_entries:
        file_path = os.path.join(out_folder, f"USERDATA_{entry.index:02d}")

        if not os.path.exists(file_path):
            debug(f"  Skipping entry #{entry.index} — modified file not found")
            continue

        with open(file_path, 'rb') as f:
            entry._clean_data = f.read()

        encrypted_blob = entry.encrypt_sl2_data()

        if len(encrypted_blob) != entry.size:
            print(
                f"  WARNING: Size mismatch for entry #{entry.index}! "
                f"Expected {entry.size}, got {len(encrypted_blob)} — skipping."
            )
            continue

        start = entry.data_offset
        new_data[start:start + len(encrypted_blob)] = encrypted_blob
        debug(f"  Encrypted USERDATA_{entry.index:02d}")

    with open(output_sl2_file, 'wb') as f:
        f.write(new_data)

    print(f"Saved re-encrypted SL2 to: {output_sl2_file}")