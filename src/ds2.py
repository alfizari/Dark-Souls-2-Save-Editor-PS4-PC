import os
import struct
import json
import pc as pc
import pc_import as pc_import
from tkinter import filedialog, messagebox

name_offset    = 960
souls_distance = 60
hp_distance    = 72
ng_distance    = 1028

# Global MODE — set when a file is opened
MODE = None

stats_offsets_for_stats_tap = {
    "Level":        0x38,
    "Vigor":        32,
    "Attunement":   38,
    "Endurance":    34,
    "Vitality":     36,
    "Strength":     40,
    "Dexterity":    42,
    "Intelligence": 46,
    "Faith":        48,
    "Adaptability": 44,
}

working_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(working_directory)

def load_json(file_name):
    file_path = os.path.join(working_directory, "Resources/json", file_name)
    with open(file_path, "r") as f:
        return json.load(f)

goods_id   = load_json('items.json')
rings_id   = load_json('rings.json')
weapons_id = load_json('weapons.json')
armors_id  = load_json('armors.json')
key_id     = load_json('key.json')
bolts_id   = load_json('bolts.json')
spells_id  = load_json('spells.json')
upgrade_id = load_json('upgrade.json')


# ══════════════════════════════════════════════════════════════════════════════
#  FILE I/O
# ══════════════════════════════════════════════════════════════════════════════

def open_file():
    """
    Opens a file dialog for the user to pick a save file.
    Returns (char_list, file_path) where char_list is [(name, slot_path), ...].
    Returns None if the user cancels or no characters are found.
    """
    global MODE

    file_path = filedialog.askopenfilename(
        title="Select a save file"
    )
    if not file_path:
        return None

    file_name = os.path.basename(file_path)

    if file_name.startswith('DS2SOFS0000.sl2'):
        MODE = 'PC'
        pc.decrypt_ds2_sl2(file_path, 'decrypted_output')
        char_list = _scan_pc_folder('decrypted_output')
        if not char_list:
            messagebox.showerror("Error", "Can't find character name in the file.")
            return None
        return char_list, file_path

    elif file_name.lower().startswith('userdata'):
        MODE = 'ps4'
        with open(file_path, "rb") as f:
            raw = f.read()
        name = find_name(raw)
        if not name:
            messagebox.showerror("Error", "Can't find character name in the file.")
            return None
        # PS4 userdata is a single-character file — wrap as list for uniform API
        char_list = [(name, file_path)]
        return char_list, file_path

    else:
        messagebox.showerror("Error", "Please select a DS2SOFS0000.sl2 (PC) or USERDATA (PS4) file.")
        return None


def open_file_import():
    """
    Same as open_file but decrypts to a separate 'decrypted_output_import' folder
    so it doesn't overwrite the main session's decrypted files.
    Returns (char_list, file_path) or None.
    """
    global MODE

    file_path = filedialog.askopenfilename(
        title="Select import save file",
        filetypes=[("SL2 files", "*.sl2"), ("All files", "*.*")]
    )
    if not file_path:
        return None

    file_name = os.path.basename(file_path)

    if file_name.startswith('DS2SOFS0000.sl2'):
        pc_import.decrypt_ds2_sl2(file_path, 'decrypted_output_import')
        char_list = _scan_pc_folder('decrypted_output_import')
        if not char_list:
            messagebox.showerror("Error", "Can't find character name in the import file.")
            return None
        return char_list, file_path

    elif file_name.lower().startswith('userdata'):
        with open(file_path, "rb") as f:
            raw = f.read()
        name = find_name(raw)
        if not name:
            messagebox.showerror("Error", "Can't find character name in the import file.")
            return None
        char_list = [(name, file_path)]
        return char_list, file_path

    else:
        messagebox.showerror("Error", "Please select a DS2SOFS0000.sl2 (PC) or USERDATA (PS4) file.")
        return None


def _scan_pc_folder(folder_name='decrypted_output'):
    """Scan a decrypted PC save folder and return [(name, slot_path), ...]."""
    char_list = []
    split_dir = os.path.join(working_directory, folder_name)
    for i in range(1, 10):
        file_path = os.path.join(split_dir, f"USERDATA_0{i}")
        if not os.path.exists(file_path):
            continue
        with open(file_path, "rb") as f:
            raw = f.read()
        name = find_name(raw)
        if name:
            char_list.append((name, file_path))
    return char_list


def read_save(file_path):
    """Read raw bytes from a save slot file."""
    with open(file_path, "rb") as f:
        return f.read()


def save_progress(file_path, data):
    """Write bytes directly to a slot file (used for mid-session saves and import)."""
    with open(file_path, "wb") as f:
        f.write(data)


def save_file(file_path, data):
    """
    Save the edited data.
    - PC mode: writes the slot file then re-encrypts to a user-chosen .sl2 path.
    - PS4 mode: writes raw bytes to a user-chosen output path.
    """
    global MODE

    if MODE == 'PC':
        # Write the modified slot so encrypt can pick it up
        save_progress(file_path, data)
        out_path = filedialog.asksaveasfilename(
            title='Save PC save file',
            initialfile='DS2SOFS0000.sl2',
            defaultextension='.sl2',
            filetypes=[("SL2 files", "*.sl2")]
        )
        if out_path:
            pc.encrypt_modified_files(out_path, 'decrypted_output')

    elif MODE == 'ps4':
        out_path = filedialog.asksaveasfilename(
            title='Save PS4 save file',
            initialfile=os.path.basename(file_path),
            filetypes=[("All files", "*.*")]
        )
        if out_path:
            with open(out_path, "wb") as f:
                f.write(data)

    messagebox.showinfo("Save Complete", f"File saved to: {out_path}")

import re

def import_character(dest_path, import_path):
    try:
        import_data = read_save(import_path)
        save_progress(dest_path, import_data)

        dest_base   = os.path.basename(dest_path)    # e.g. USERDATA_01
        import_base = os.path.basename(import_path)  # e.g. USERDATA_01 or USERDATA_01

        # Find the number in the filename, add 10, rebuild with the SAME format
        dest_nums   = re.findall(r'\d+', dest_base)
        import_nums = re.findall(r'\d+', import_base)

        if not dest_nums or not import_nums:
            print("Could not parse slot numbers, skipping adjacent copy.")
            return import_data

        dest_num   = dest_nums[0]    # keep as string to preserve zero-padding
        import_num = import_nums[0]

        # Rebuild adjacent name by replacing the number with num+10,
        # preserving the exact same zero-padding width and surrounding text
        adj_dest_num   = str(int(dest_num)   + 10).zfill(len(dest_num))
        adj_import_num = str(int(import_num) + 10).zfill(len(import_num))

        adj_dest_name   = dest_base.replace(dest_num,   adj_dest_num,   1)
        adj_import_name = import_base.replace(import_num, adj_import_num, 1)

        adj_dest_path   = os.path.join(os.path.dirname(dest_path),   adj_dest_name)
        adj_import_path = os.path.join(os.path.dirname(import_path), adj_import_name)

        print(f"Adjacent copy: {adj_import_name} -> {adj_dest_name}")

        if os.path.exists(adj_import_path):
            save_progress(adj_dest_path, read_save(adj_import_path))
            print("Adjacent slot copied.")
        else:
            print("Adjacent import slot not found, skipping.")

        return import_data

    except Exception as e:
        messagebox.showerror("Import Error", str(e))
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER DATA
# ══════════════════════════════════════════════════════════════════════════════

def find_name(data):
    """Extract the character name from raw save bytes."""
    raw_name = data[name_offset:name_offset + 32]
    try:
        name = raw_name.decode("utf-16-le", errors="ignore").rstrip("\x00")
    except Exception:
        return None

    if not name:
        return None

    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")
    return name if all(c in allowed_chars for c in name) else None


def load_data(data):
    """
    Parse key character fields from raw save bytes.
    Returns a dict with name, souls, hp, ng, stats — or None if data is invalid.
    """
    if data is None:
        return None

    name  = find_name(data)
    souls = int.from_bytes(data[souls_distance:souls_distance + 4], 'little')
    hp    = int.from_bytes(data[hp_distance:hp_distance + 4], 'little')
    ng    = struct.unpack_from('<H', data, ng_distance)[0]

    stats = {}
    for stat, offset in stats_offsets_for_stats_tap.items():
        stats[stat] = int.from_bytes(data[offset:offset + 2], 'little')

    return {
        "name":  name,
        "souls": souls,
        "hp":    hp,
        "ng":    ng,
        "stats": stats,
    }


def change_name(data, new_name):
    data = bytearray(data)
    name_bytes = new_name.encode("utf-16-le")[:32].ljust(32, b'\x00')
    data[name_offset:name_offset + 32] = name_bytes
    return bytes(data)


def change_souls(data, souls):
    data   = bytearray(data)
    souls  = max(0, min(int(souls), 0xFFFFFFFF))
    off    = souls_distance
    data[off:off + 4] = souls.to_bytes(4, 'little')
    return bytes(data)


def change_hp(data, health):
    data   = bytearray(data)
    health = max(0, min(int(health), 0xFFFFFFFF))
    off    = hp_distance
    data[off:off + 4] = health.to_bytes(4, 'little')
    return bytes(data)


def change_ng(data, ng_value):
    data     = bytearray(data)
    ng_value = max(0, min(int(ng_value), 0xFFFF))
    struct.pack_into('<H', data, ng_distance, ng_value)
    return bytes(data)


def change_stats(data, stat_name, stat_value):
    if stat_name not in stats_offsets_for_stats_tap:
        return data
    data     = bytearray(data)
    off      = stats_offsets_for_stats_tap[stat_name]
    stat_value = max(0, min(int(stat_value), 0xFFFF))
    data[off:off + 2] = stat_value.to_bytes(2, 'little')
    return bytes(data)


# ══════════════════════════════════════════════════════════════════════════════
#  INVENTORY
# ══════════════════════════════════════════════════════════════════════════════

class INVENTORY:
    BASE_SIZE = 16

    def __init__(self, unk_1, item_id, quantity, unk_2, offset):
        self.item_id  = item_id
        self.unk_1    = unk_1
        self.quantity = quantity
        self.unk_2    = unk_2
        self.offset   = offset
        self.size     = self.BASE_SIZE

    @classmethod
    def from_bytes(cls, data, offset=0):
        iid, un_1, qty, un_2 = struct.unpack_from("<IIII", data, offset)
        return cls(un_1, iid, qty, un_2, offset)


def parse_inventory(data, start_offset, end_offset):
    items  = []
    offset = start_offset
    while offset < end_offset:
        item = INVENTORY.from_bytes(data, offset)
        items.append(item)
        offset += item.size
    return items


def hex_dict_to_int(d):
    result = {}
    for k, v in d.items():
        try:
            b   = bytes.fromhex(v)
            iid = int.from_bytes(b, "little")
            result[iid] = k
        except ValueError:
            pass
    return result


def build_item_db():
    """Build a dict of {item_id_int: (name, category)} for all item types."""
    item_db = {}

    def add_items(d, category):
        for iid, name in hex_dict_to_int(d).items():
            item_db[iid] = (name, category)

    add_items(goods_id,   "goods")
    add_items(weapons_id, "weapons")
    add_items(armors_id,  "armors")
    add_items(rings_id,   "rings")
    add_items(key_id,     "keys")
    add_items(bolts_id,   "bolts")
    add_items(spells_id,  "spells")
    add_items(upgrade_id, "upgrade")
    return item_db




INVENTORY_START = 0x1E2C
INVENTORY_END   = 0x10E1C

KEY_START = 0x10E30
KEY_END   = 0x11DF0


def inventoryprint(data):
    """
    Parse inventory and bucket items by category.
    Keys are parsed separately to avoid mixing slot regions.
    """

    item_db = build_item_db()

    normal_items = parse_inventory(data, INVENTORY_START, INVENTORY_END)
    key_items    = parse_inventory(data, KEY_START, KEY_END)

    buckets = {
        "goods": [],
        "weapons": [],
        "armors": [],
        "rings": [],
        "keys": [],
        "bolts": [],
        "spells": [],
        "upgrade": [],
        "empty": [],
        "empty_keys": [],
        "all": []
    }

    # NORMAL INVENTORY
    for item in normal_items:

        if item.item_id == 0:
            buckets["empty"].append(item)
            continue

        buckets["all"].append(item)

        info = item_db.get(item.item_id)
        if info:
            name, category = info

            if category in buckets:
                buckets[category].append(item)

    # KEY INVENTORY
    for item in key_items:

        if item.item_id == 0:
            buckets["empty_keys"].append(item)
            continue

        buckets["all"].append(item)

        info = item_db.get(item.item_id)
        if info:
            name, category = info

            if category == "keys":
                buckets["keys"].append(item)

    return buckets


def add_items(data, item_name, category, quantity=None, stack=False):
    """
    Add or update an item in the inventory.
    For stackable categories (goods, bolts, spells, upgrade): updates existing stack
    or creates a new slot.
    For non-stackable (weapons, armors, rings, keys): always writes a new slot.
    Keys are written to the key inventory region (KEY_START/KEY_END).
    """
    data      = bytearray(data)
    inventory = inventoryprint(data)

    # Pick the correct empty slot list based on category
    if category == "keys":
        empty_list = inventory['empty_keys']
    else:
        empty_list = inventory['empty']

    if not empty_list:
        messagebox.showwarning("Inventory Full", "No empty inventory slots available.")
        return bytes(data)

    first_empty_offset = empty_list[0].offset

    category_map = {
        "goods":   goods_id,
        "weapons": weapons_id,
        "armors":  armors_id,
        "rings":   rings_id,
        "keys":    key_id,
        "bolts":   bolts_id,
        "spells":  spells_id,
        "upgrade": upgrade_id,
    }

    source = category_map.get(category)
    if source is None:
        raise ValueError(f"Unknown category: '{category}'")

    item_id_hex = source.get(item_name)
    if item_id_hex is None:
        raise ValueError(f"Item '{item_name}' not found in category '{category}'")

    item_id_bytes = bytes.fromhex(item_id_hex)
    item_id_int   = int.from_bytes(item_id_bytes, 'little')
    new_quantity  = min(int(quantity), 99) if quantity is not None else 1

    stackable = category in ("goods", "bolts", "spells", "upgrade")

    # Update existing stack for stackable items (unless stack=True forces a new slot)
    if stackable and not stack:
        for item in inventory[category]:
            if item.item_id == item_id_int:
                q_off = item.offset + 8
                data[q_off:q_off + 4] = new_quantity.to_bytes(4, 'little')
                return bytes(data)

    # Build a new inventory slot
    slot = _build_slot(item_id_bytes, item_id_hex, category, stackable, new_quantity, data)
    data[first_empty_offset:first_empty_offset + 16] = slot
    return bytes(data)


def _build_slot(item_id_bytes, item_id_hex, category, stackable, quantity, data):
    """Build a 16-byte inventory slot."""

    inventory = inventoryprint(data)

    if stackable and category in ("goods", "bolts", "spells", "upgrade"):
        slot = bytearray.fromhex('40 05 99 03 00 00 00 00 01 00 00 00 00 00 00 00')
        slot[8:12] = quantity.to_bytes(4, 'little')
        slot[:4]   = item_id_bytes

    elif category == "weapons":
        weapon_slot = inventory['weapons'][0] if inventory['weapons'] else None

        if weapon_slot:
            slot = bytearray(16)
            slot[:4]   = item_id_bytes
            slot[4:8]  = weapon_slot.unk_1.to_bytes(4, 'little')
            slot[8:12] = weapon_slot.quantity.to_bytes(4, 'little')
            slot[12:16]= bytes.fromhex('00 00 00 00')
        else:
            slot = bytearray.fromhex('50 2D 19 00 00 00 00 00 00 00 20 42 00 00 00 00')
            slot[:4] = item_id_bytes

        print(f"Adding weapon: {item_id_hex} with quantity {quantity}", slot.hex())

    elif category == "armors":
        armor_slot = inventory['armors'][0] if inventory['armors'] else None

        if armor_slot:
            slot = bytearray(16)
            slot[:4]   = item_id_bytes
            slot[4:8]  = armor_slot.unk_1.to_bytes(4, 'little')
            slot[8:12] = armor_slot.quantity.to_bytes(4, 'little')
            slot[12:16]= bytes.fromhex('00 00 00 00')
        else:
            slot = bytearray.fromhex('A4 E0 42 01 00 00 00 00 00 00 7F 43 00 00 00 00')
            slot[:4] = item_id_bytes

    elif category == "rings":
        ring_slot = inventory['rings'][0] if inventory['rings'] else None

        if ring_slot:
            slot = bytearray(16)
            slot[:4]   = item_id_bytes
            slot[4:8]  = ring_slot.unk_1.to_bytes(4, 'little')
            slot[8:12] = ring_slot.quantity.to_bytes(4, 'little')
            slot[12:16]= bytes.fromhex('00 00 00 00')
        else:
            slot = bytearray.fromhex('10 81 62 02 00 00 00 00 00 00 F0 42 00 00 00 00')
            slot[:4] = item_id_bytes

    else:  # keys
        slot = bytearray.fromhex('40 05 99 03 00 00 00 00 01 00 00 00 00 00 00 00')
        slot[:4] = item_id_bytes

    return slot


def delete_item(data, item_name, category):
    """Zero out the 16-byte inventory slot for the named item."""
    data = bytearray(data)

    category_map = {
        "goods":   goods_id,
        "weapons": weapons_id,
        "armors":  armors_id,
        "rings":   rings_id,
        "keys":    key_id,
        "bolts":   bolts_id,
        "spells":  spells_id,
        "upgrade": upgrade_id,
    }

    source = category_map.get(category)
    if source is None:
        raise ValueError(f"Unknown category: '{category}'")

    item_id_hex = source.get(item_name)
    if item_id_hex is None:
        raise ValueError(f"Item '{item_name}' not found in category '{category}'")

    item_id_int = int.from_bytes(bytes.fromhex(item_id_hex), 'little')

    # Search the correct range based on category
    if category == "keys":
        items = parse_inventory(data, KEY_START, KEY_END)
    else:
        items = parse_inventory(data, INVENTORY_START, INVENTORY_END)

    for item in items:
        if item.item_id == item_id_int:
            data[item.offset:item.offset + 16] = bytearray(16)
            break

    return bytes(data)
