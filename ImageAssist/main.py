import click
import os
import processor

@click.group()
def cli():
    """ImageAssist CLI for Etsy Business"""
    pass

@cli.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to the input image file')
@click.option('--output', '-o', default='./output', type=click.Path(), help='Output directory')
@click.option('--grid', '-g', required=True, help='Grid format e.g. "1x3" (rows x cols)')
def split(input, output, grid):
    """Split a single image into a grid"""
    print(f"Splitting {input} into {grid}...")
    processor.split_image(input, output, grid)

@cli.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True), help='Path to input folder')
@click.option('--output', '-o', default='./output', type=click.Path(), help='Output directory')
@click.option('--scale', '-s', required=True, type=float, help='Scale multiplier (e.g., 2.0 to double size)')
def resize(input_folder, output, scale):
    """Resize all images in a folder"""
    print(f"Resizing images in {input_folder} by {scale}x...")
    processor.resize_images(input_folder, output, scale)

@cli.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True), help='Path to input folder')
@click.option('--output', '-o', default='./output', type=click.Path(), help='Output directory')
@click.option('--width', '-w', required=True, type=int, help='Target width in pixels')
@click.option('--height', '-h', required=True, type=int, help='Target height in pixels')
def crop(input_folder, output, width, height):
    """Center-crop all images in a folder to exact dimensions"""
    print(f"Cropping images in {input_folder} to {width}x{height}...")
    processor.crop_images(input_folder, output, width, height)

@cli.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True), help='Path to input folder')
def remove_bg(input_folder):
    """Remove background from all images in a folder"""
    print(f"Removing backgrounds from images in {input_folder}...")
    processor.remove_background(input_folder)

@cli.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True), help='Folder containing the transparent PNG clipart pieces')
@click.option('--background', '-b', required=False, type=click.Path(exists=True), help='Path to the blank background image for the mockup')
def mockup_showcase(input_folder, background):
    """Automatically arrange all clipart pieces onto a single beautiful showcase listing image."""
    processor.create_showcase_mockup(input_folder, background)

@cli.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to the input sheet image')
@click.option('--bg', '-b', default='transparent', type=click.Choice(['transparent', 'black', 'white']), help='Background type of the sheet (transparent, black, white)')
def auto_process(input, bg):
    """Auto-detect objects, slice, resize, pad to 3000x3000 (white background), and save to Split folder"""
    processor.auto_process_sheet(input, bg_type=bg)

@cli.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True), help='Path to input folder')
def format_clipart(input_folder):
    """Format images for Etsy clipart (remove BG, 3000x3000px padding, 300 DPI)"""
    print(f"Formatting clipart in {input_folder}...")
    processor.format_clipart_batch(input_folder)

@cli.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to the input image file')
@click.option('--output', '-o', default='./output', type=click.Path(), help='Output directory')
def color_shift(input, output):
    """Open interactive UI to apply a hue shift to a single image"""
    print(f"Opening interactive color preview for {input}...")
    processor.color_shift_interactive(input, output)

if __name__ == '__main__':
    cli()
