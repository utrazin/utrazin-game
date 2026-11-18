Stylized, seamlessly tileable 1024x1024 textures (albedo `_D` sRGB + DirectX/green-down normal `_N`), generated 100% procedurally with no source images.

Materials: Grass, Dirt, Gravel, Rock, Concrete, Wood, RustMetal, ZombieSkin, Cloth.
Alien set: AlienGrass, AlienMoss, RedSand, AlienDirt, CrystalRock, Toxic, AlienMetal, ZombieAlien, Asphalt.
Grayscale masks: `T_Detail_Grunge.png` (detail multiply) and `T_Emissive_Mask_Veins.png` (black bg, white veins; same vein network as ZombieAlien, so it lines up as an emissive mask, e.g. Emissive = Mask * cyan * intensity).

Regenerate with `python3 make_textures.py [out_dir] [material ...]` (numpy, Pillow, scipy). Material names are the function names: grass dirt gravel rock concrete wood rustmetal zombieskin cloth grunge alien_grass alien_moss red_sand alien_dirt crystal_rock toxic alien_metal zombie_alien asphalt emissive_veins.
`textures_preview.png` shows each albedo tiled 2x2 with its normal.
License: original work by the project, released CC0.
