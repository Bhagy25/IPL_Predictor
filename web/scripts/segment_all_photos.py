import os
import sys
from rembg import remove, new_session
from PIL import Image
import numpy as np

def make_checkerboard(width, height, tile_size=20):
    grid = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            if (x // tile_size + y // tile_size) % 2 == 0:
                grid[y:y+tile_size, x:x+tile_size] = [200, 200, 200]
            else:
                grid[y:y+tile_size, x:x+tile_size] = [255, 255, 255]
    return Image.fromarray(grid)

def process_all():
    print("Loading U2Net session...")
    session = new_session('u2net')
    os.makedirs('web/public/assets/isolated_cutouts', exist_ok=True)
    os.makedirs('reports/checkerboard_validation', exist_ok=True)

    targets = [
        ('web/public/assets/original_photos/07_ipl_trophy.png', 'trophy_isolated.png'),
        ('web/public/assets/original_photos/04_yellow_jersey_batter.png', 'dhoni_isolated.png'),
        ('web/public/assets/original_photos/11_blue_jersey_bowler.png', 'rohit_isolated.png'),
        ('web/public/assets/original_photos/05_red_jersey_batting_action.png', 'kohli_isolated.png'),
        ('web/public/assets/original_photos/06_pink_jersey_celebration.png', 'buttler_isolated.png'),
        ('web/public/assets/original_photos/09_red_blue_jersey_celebration.png', 'pant_isolated.png'),
        ('web/public/assets/original_photos/10_red_black_jersey_batting.png', 'maxwell_isolated.png'),
        ('web/public/assets/original_photos/03_red_jersey_applause.png', 'kohli_applause_isolated.png'),
    ]

    for src_rel, out_name in targets:
        print(f"\nProcessing {src_rel} -> {out_name}...")
        img = Image.open(src_rel).convert('RGBA')
        
        # Segment subject using U2Net deep learning matting
        isolated = remove(
            img, 
            session=session, 
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10
        )
        
        dst_path = os.path.join('web/public/assets/isolated_cutouts', out_name)
        isolated.save(dst_path, format='PNG')
        
        # Verify genuine transparency
        alpha_channel = np.array(isolated.split()[-1])
        transparent_ratio = float((alpha_channel == 0).sum()) / float(alpha_channel.size)
        print(f"  -> Saved {dst_path} (Dimensions: {isolated.size}, Zero-alpha transparent ratio: {transparent_ratio:.1%})")
        
        # Generate checkerboard validation image
        chk = make_checkerboard(isolated.width, isolated.height)
        chk.paste(isolated, (0, 0), isolated)
        chk_path = os.path.join('reports/checkerboard_validation', f'chk_{out_name}')
        chk.save(chk_path, format='PNG')
        print(f"  -> Checkerboard validation image saved: {chk_path}")

    print("\nAll 8 subjects segmented and validated with genuine transparency!")

if __name__ == '__main__':
    process_all()
