# Introduction
This python script is designed to take a 'Progress Flag Script' text file and compile it into a hex format that be can be read by KH2FM.

You can drag and drop your text file onto the python script directly, or you can call it via Command Line. Here's an example.

>py progress-compiler.py "your_text_file.txt"

I would recommend using the Progress Flag Scripts in the '00progress' folder as a base. Those are Progress Flag Scripts for each world in KH2. If used with the compiler, they will create the exact same hex file as they are found in a vanilla 00progress.bin file.

Credit to Num and his 00progress-Scripts, they were the base I used to create this tool. https://github.com/1234567890num/00progress-Scripts


# KH2FM's Progress Flag File Structure
The "world.bin" files have a structure with a Header, then the Progress Flag instructions.

The Header contains offsets to the start of each Progress Flag in the hex file. They are a ushort in length and are in little-Endian. So for example, if the offset for a progress flag is "FE 01", the start of that Progress Flag will be 0x1FE bytes into the hex file. There is no traditional "count" of Progress Flags, the Header simply has a certain amount of offsets, and that determines how many Progress Flags there are in the file.

The Progress Flag can contain any number of instructions and will stop when it reads a "00 00". The structure for the instructions is the following.
```
Offset	Size	Description
0x0		byte	Code Type
0x1		byte	Data Count
0x2		ushort	Data
```

This is the Enum for Code Types

```
typedef enum <ubyte> CODE_TYPE {
  CODE_END = 0x0,
  CODE_SET = 0x1,
  CODE_DSA_DISABLE = 0x2,
  CODE_DSA_ENABLE = 0x3,
  CODE_DSA_LOST = 0x4,
  CODE_DSA_RESET = 0x5,
  CODE_BGMSET = 0x6,
  CODE_RESET_PROGRESS = 0x7,
  CODE_MENUFLAG = 0x8,
  CODE_RESET_MENUFLAG = 0x9,
  CODE_WORLDSTATE2 = 0xa,
  CODE_SECOND = 0xb,
  CODE_SET_PROGRESS = 0xc,
  CODE_SCENARIO = 0xd,
} CODE_TYPE;
```

CODE_SECOND and CODE_WORLDSTATE2 from what I've seen are unused.

All of the Code Types that say DSA are referencing the "DSA.bin" subfile within 00progress.bin. The DSA subfile is a collection of Worlds and Rooms for the "Block, Unblock, Remove Warp, Add Warp" instructions. I've added a vanilla "DSA.bin" into the directory. This code uses that DSA.bin as a lookup table and will write the correct DSA index for those instructions. DSA index = (hex position - 2) / 2. 

So for example, for the instruction "Unblock: World 07 Room 02", the short 0702 is at hex location 0x42 in the DSA file. The index is then (0x42 - 2) / 2 = 0x20.

I put a DSA.bin file here instead of a .JSON so that you can modify the DSA.bin file for your own custom use, and the script will still function properly.


# How To Use
To write or make modifications to Progress Flags, these are the instruction sets that the compiler expects.

```
INSTRUCTION_MARKERS = [
    "[END]",
    "[SKIP]",
    "World Map:",
    "Raise Progress:",
    "Lower Progress:",
    "Spawn ID Change:",
    "Block:",
    "Unblock:",
    "Remove Warp:",
    "Add Warp:",
    "BGM Set:",
    "Lower Menu:",
    "Raise Menu:"
]
```

* **[END]** marks the end of a Progress Flag. It will create 2 bytes of buffer and will create an offset in the header to the beginning of the Progress Flag. This must be placed at the end of a Progress Flag for it to be valid.

* **[SKIP]** is self explanatory. The difference between [END] and [SKIP] is that [SKIP] does not create a buffer nor an offset to it's location. The offset in the header for skipped Progress Flags will always be 0x0000.

* **World Map** will set the status of the World on the World Map. This will vary from Unvisited, to Visited, to Visit X completed, and so on. I don't have full documentation on this but will fill this out when I do.
	* Example:
		```
		World Map: 00 01
  		```

* **Raise Progress** will mark another Progress Flag as complete and will activate any instructions within it's contents.
	* Example:
		```
		Raise Progress:
			0800 TT_START_1
  		```
			
* **Lower Progress** will reset the Progress Flag to an incomplete state. Note that this does not revert any instructions that were activated previously.
	* Example:
		```
		Lower Progress:
			0800 TT_START_1
  		```

* **Spawn ID Change** will modify the Map, Battle, and Event script respectively of a specified Room in the world.
	* Example:
		```
		Spawn ID Change:
			Room 24: 00 00 00
			Room 0D: 00 00 00
			Room 06: 00 00 00
  		```
		
* **Block** will make a Room unavailable for entrance. This code also references the text string that appears at the bottom of the screen when you attempt to enter that room. The code asks for 2 text strings, but really only seems to use the first one. The formatting is usually the first text string, then the second text string is the first text string +0x0001.
	* Example:
		```
		Block: World 07 Room 03
			Text: 0537 0538
  		```
			
* **Unblock** will make a Room available again after being Blocked. This code similar to Block but much simpler, all you need to do is reference the World and Room.
	* Example:
		```
		Unblock: World 07 Room 02
  		```
		
* **Remove Warp** will remove a warp-in point from the World Map of a specified room.
	* Example:
		```
		Remove Warp: World 07 Room 09
  		```
		
* **Add Warp** will add a warp-in point for use from the World Map.
	* Example:
		```
		Add Warp: World 07 Room 02
  		```
		
* **BGM Set** will set the BGM of a world. This is mostly used in Twilight Town as the BGM has to change between Roxas and Sora. There's also a portion where the BGM cuts out completely for Roxas on Day 7, this instruction handles that.
	* Example:
		```
		BGM Set: 2
  		```
		
* **Lower Menu** lowers a Menu Flag. This is mostly unused in the vanilla game.
	* Example:
		```
		Lower Menu:
			00 TEST
  		```
			
* **Raise Menu** will raise a Menu Flag. This is used to enable certain things in the Menu early on in Twilight Town, like the certain commands in the Command Menu, and things like Items, Equipment, Abilities etc. in the Camp Menu.
	* Example:
		```
		Raise Menu:
			73 CAMP_CMD_OPEN_JIMINYMEMO
			71 CAMP_CMD_OPEN_PARTY
  		```
