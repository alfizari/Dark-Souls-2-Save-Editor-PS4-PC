# Dark Souls 2 Save Editor for PS4/PS5 and PC

A lightweight save editor for **Dark Souls II** that supports **PC (.sl2)** and **PS4/PS5 USERDATA saves**.
This tool allows you to inspect and modify various parts of your save file safely.

⚠️ **Always make a backup of your save before using this tool.**

---

## Features

* Edit **NG+ level**
* Edit **HP**
* Change **character name**
* Modify **player stats**
* View **inventory contents**
* **Spawn items** (weapons, goods, keys, spells, etc.)
* **Delete items**
* Works with:

  * **PC `.sl2` saves**
  * **PS4/PS5 `USERDATA` saves**

The tool automatically handles **decryption and re-encryption** for PC save files.

---

## Supported Item Types

You can spawn or manage:

* Weapons
* Armor
* Rings
* Goods
* Keys
* Spells
* Bolts / Arrows
* Upgrade materials

---

## Usage

1. **Backup your save file.**
2. Run the editor.
3. Open one of the following:

   * `DS2SOFS0000.sl2` (PC save)
   * `USERDATA` (PS4 / PS5 save) (USE HTOS discord or https://garlicsaves.com/ to decrypt/encrypt your ps4 save)
4. Select the character you want to edit.
5. Apply your changes.
6. Save the modified file.

For PC saves, the tool will:

* Decrypt the `.sl2`
* Modify the selected slot
* Re-encrypt the save automatically.

---

## Warning

⚠️ **Do NOT bulk add large numbers of items at once.**

Adding too many items simultaneously may **corrupt the save file** due to inventory limits in the game.

Recommended:

* Add items in **small batches**
* Save frequently
* Keep backups

---

## Credits

* **jtesta / souls_givifier**
  Used for `.sl2` decryption and encryption logic (modified version).
  https://github.com/jtesta/souls_givifier

* **@AsianMop**
  Provided the game copy used for research and testing.

---

## Disclaimer

This project is **not affiliated with FromSoftware or Bandai Namco**.

Use at your own risk. Always keep backups of your saves.

---
