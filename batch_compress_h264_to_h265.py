import click
from pathlib import Path
from subprocess import call, check_output
from tqdm import tqdm


@click.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive', is_flag=True, help='Recursive')
@click.option('--file-ext', help='File format to process')
@click.option('--crf', default=28, help='CRF (Constant Rate Factor) for x265. Allowed values in range 0-51. For more info please see https://slhck.info/video/2017/02/24/crf-guide.html')
@click.option('--quality', default=35, help='Video quality for hevc_videotoolbox encoder. Allowed values in range 0-100.')
@click.option('--encoder', type=click.Choice(['libx265', 'hevc_videotoolbox', 'libsvtav1'], case_sensitive=False))
def main(directory, file_ext='mp4', recursive=False, crf=28, quality=35, encoder='libsvtav1'):
    """ Compress h264 video files in a directory using libx265 codec with crf=28
    Args:
         directory: the directory to scan for video files
         file_ext: the file extension to consider for conversion
         recursive: whether to search directory or all its contents
         crf: Constant Rate Factor (CRF). Lower values would result in better quality, at the expense of higher file sizes.
                Higher values mean more compression, but at some point you will notice the quality degradation.
    """
    if recursive:
        video_files = [
            fp.absolute() for fp in Path(directory).rglob(f'*.{file_ext}')
        ]
    else:
        video_files = [
            fp.absolute() for fp in Path(directory).glob(f'*.{file_ext}')
        ]

    check_codec_cmd = 'ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "{fp}"'
    codecs = []
    for fp in tqdm(video_files, desc='Checking metadata', unit='videos'):
        codecs.append(
            check_output(check_codec_cmd.format(fp=fp),
                         shell=True).strip().decode('UTF-8'))

    codec_name_ffprobe = None
    if encoder == 'hevc_videotoolbox' or encoder == 'libx265':
        codec_name_ffprobe = 'hevc'
    else:
        codec_name_ffprobe = 'av1'

    files_to_process = [
        fp for fp, codec in zip(video_files, codecs) if codec != codec_name_ffprobe
    ]

    print(f'\nTOTAL FILES FOUND ({len(video_files)})')
    print(f'FILES TO PROCESS ({len(files_to_process)}):',
          [fp.name for fp in files_to_process], '\n')

    if len(files_to_process) == 0:
        raise click.Abort
    else:
        click.confirm('Do you want to continue?', abort=True)

    for fp in tqdm(files_to_process, desc='Converting files', unit='videos'):
        new_fp = fp.parent / 'temp_ffmpeg.mp4'
        if encoder == 'hevc_videotoolbox':
            convert_cmd = f'ffmpeg -i "{fp}" -map_metadata 0 -c:v {encoder}  -q:v {quality} -c:a copy -tag:v hvc1 "{new_fp}"'
        elif encoder == 'libx265':
            convert_cmd = f'ffmpeg -i "{fp}" -map_metadata 0 -c:v {encoder} -pix_fmt yuv420p -preset 2 -c:a copy -tag:v hvc1 -crf "{crf}" "{new_fp}"'
        elif encoder == 'libsvtav1':
            # Best results with preset 10 and crf 35 by default.
            convert_cmd = f'ffmpeg -i "{fp}" -map_metadata 0 -c:v {encoder} -preset 10 -crf "{crf}" -pix_fmt yuv420p10le -svtav1-params tune=0 -c:a copy "{new_fp}"'
        conversion_return_code = call(convert_cmd, shell=True)
        if conversion_return_code == 0:
            call(f'touch -r "{fp}" "{new_fp}"', shell=True)
            call(f'mv "{new_fp}" "{fp}"', shell=True)


if __name__ == '__main__':
    main()