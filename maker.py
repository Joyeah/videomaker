from ast import arg
import os
import sys
from moviepy import AudioFileClip
import pyttsx3
import subprocess
import logging

from utils.txtutil import  split_text_by_count
# 配置日志记录器（可选）
logging.basicConfig(filename='app.log', level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class VideoMaker:
    '''
    将文字转换为音频文件，并与图片合并为视频文件片断；进而合并为整个视频文件.
    注：由于字幕内容需要在生成视频片断过程中生成，因此视频片断不清理的情况下不会再次生成。
    verison: 1.0
    '''
    def __init__(self, indir:str='input', outdir: str='output', outfilename:str=None):
        """
        Initialize the VideoMaker class.

        Args:
            indir (str, optional): Input directory containing images and text files. Defaults to 'input'.
            outdir (str, optional): Output directory for generated media files. Defaults to 'output'.
            outfilename (str, optional): Output file name for the final video. Defaults to the last part of the input directory.
        """
        self.indir = indir
        self.outdir = outdir
        self.outname = outfilename or self.indir.replace('\\','/').rstrip('/').split('/')[-1]
        os.makedirs(self.indir, exist_ok=True)
        os.makedirs(self.outdir, exist_ok=True)
        # 文件列表
        self.textpaths = []
        self.imgpaths = []
        self.mp3paths = []
        # 字幕内容列表
        self.audio_durations = dict() # 文本播放时长：key:<textfile>, value: <duration>
        self.srt_idx = 0 # 字幕索引
        self.srt_content = []
        self.srt_start= 0 # 下一句字幕起点时间
        self.subtitle_file = os.path.join(self.outdir, f'{self.outname}.srt')
        # 创建日志记录器实例
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        """
        TTS and Convert to MP4
        """               
        # step1: 转换文本到音频文件MP3
        engine = pyttsx3.init()
        # 设置语速
        # rate = engine.getProperty('rate')
        # engine.setProperty('rate', rate-50)
        # 检查图片对应的文本文件是否存在，若不存在根据article.txt生成
        self.check_input_files()

        # step2 列出所有图片文件名及文本文件
        for imgfilename in os.listdir(self.indir):
            if imgfilename.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.jfif')):
                txtfile = imgfilename.rstrip(imgfilename.split('.')[-1]) + 'txt'
                txtfile = os.path.join(self.indir, txtfile)
                if not os.path.exists(txtfile):
                    self.logger.warning(f'Text file not found: {txtfile}, use default text.')
                    with open(txtfile, "w", encoding='utf-8') as txt:
                        txt.write('Just watching this picture slience ...')
                
                mp3file = os.path.join(self.indir, imgfilename.rstrip(imgfilename.split('.')[-1]) + 'mp3')
                if os.path.exists(mp3file):
                    self.logger.info(f'Skip convert text to MP3: {mp3file}')
                    self.mp3paths.append(mp3file)
                    self.textpaths.append(txtfile)
                    self.imgpaths.append(os.path.join(self.indir, imgfilename))
                else:
                    try:
                        self.logger.info(f'Convert text to MP3: {mp3file}')
                        engine.save_to_file(open(txtfile, 'r', encoding='utf8').read(), mp3file)
                        engine.runAndWait()
                        self.mp3paths.append(mp3file)
                        self.textpaths.append(txtfile)
                        self.imgpaths.append(os.path.join(self.indir, imgfilename))
                
                    except Exception as e:
                        self.logger.error(e)
    
        engine = None
        if len(self.imgpaths) == 0:
            self.logger.error('No image files found.')
            return
        
        # 生成视频片段列表
        self.logger.info('Media Maded begin. images count: {len(imgpaths)}')
        video_clips = self.gen_videos()
        # 生成全部字幕文件
        self.gen_full_srt_file()
        
        # 生成视频片段列表文件
        clip_list_file = os.path.join(self.indir, 'list.txt')
        with open(clip_list_file, 'w', encoding='utf8') as f:
            for vid in video_clips:
                if os.path.exists(vid):
                    f.write("file '%s'\n" % vid.split(os.path.sep)[-1])
                else:
                    self.logger.error(f'{vid} NOT EXISTS!!!')

        # 将所有视频片段合并成一个视频
        self.merge_video_clips(clip_list_file)
        self.logger.info('Convert to mp4 Done')
        
        # 删除临时文件
        # for video_clip in video_clips:
        #     os.remove(video_clip)
        # os.remove(clip_list_file)

        # # 删除mp3文件
        # for mp3path in mp3paths:
        #     try:
        #         os.remove(mp3path)
        #     except Exception as e:
        #         self.logger.error(e)

        self.logger.info('Media Maded finished.')
    
    def gen_videos(self) -> list:
        """生成音频及视频文件,采用ffmepg生成单图片视频,再合并
        """
        # 创建一个列表存储视频片段
        video_clips = []
        
        # 遍历所有音频文件和对应的图片文件，生成视频片段
        for imgfile, textfile, mp3file in zip(self.imgpaths, self.textpaths, self.mp3paths):
            print(f'[MAKE VIDEO CLIP] {textfile} {imgfile} {mp3file}')
            fname = imgfile.rstrip(imgfile.split('.')[-1])  # 避免文件名中有.的情况
            video_clip = f'{fname}mp4'
            if os.path.exists(video_clip):
                self.logger.info(f'{video_clip} exists, skip making it.')
                # 片断音频时长
                self.audio_durations[textfile] = get_mp3_duration(mp3file)
                video_clips.append(video_clip)
            else:
                try:
                    self.make_video_clip(imgfile, mp3file, textfile, video_clip)
                    video_clips.append(video_clip)
                except Exception as e:
                    self.logger.error(e)

        return video_clips
    

    
    def make_video_clip(self, image_path, mp3path, textfile, output):
        """
           用ffmepg生成单图片视频片断（合成图片、音频、文字）。

        Args:
            image_path (str): 图片路径。
            mp3path (str): 音频文件路径。
            textfile (str): 文字文件路径(用作字幕)。

        Returns:
            str: 生成的视频片段路径。
        
        Notes:
            ffmpeg -loop 1 -i 1.jpg -i 1.mp3 -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -c:a aac -t 10 -pix_fmt yuv420p -y 1.mp4
            特效：
                fade=t=in:st=0:d=1：淡入效果，从第 0 秒开始，持续 1 秒。
                fade=t=out:st=4:d=1：淡出效果，从第 4 秒开始，持续 1 秒
        """
        # 获得音频文件的时长
        audio_duration = get_mp3_duration(mp3path)

        # 字幕文件
        # subtitle_file = textfile.rstrip(textfile.split('.')[-1]) + 'srt'
        # self.gen_srt_file(open(textfile, 'r', encoding='utf8').read(), audio_duration, output_file=subtitle_file)
        # 根据audio_duration生成字幕内容
        # self.append_srt_content(textfile, audio_duration)
        # 保存文本播放时长
        self.audio_durations[textfile] = audio_duration

        # output = image_path.rstrip(image_path.split('.')[-1]) + 'mp4'
        command = [
            'ffmpeg', '-loop', '1', '-i', image_path, '-i', mp3path,
            # '-vf', f'subtitles={subtitle_file}',
            '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fade=t=in:st=0:d=0.5,fade=t=out:st={audio_duration-1}:d=0.5',
            '-c:v', 'libx264', '-c:a', 'aac', '-t', str(audio_duration), '-pix_fmt', 'yuv420p', '-y', output
        ]
        print(' '.join(command))
        subprocess.run(command)
        self.logger.info('Make Video clip Done')
        # return video_clip_path

    def merge_video_clips(self, clip_list_file):
        """
        合并多个视频片段，并保存为一个新的视频文件。
        ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4
        Args:
            clip_list_file (str): 视频列表文件路径。

        Returns:
            None
        """
        # output1 = f'{os.path.basename(self.workdir)}_nomusic.mp4'
        output1 = os.path.join(self.outdir, f'{self.outname}_nomusic.mp4')
        command = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', clip_list_file, '-c', 'copy', '-y', output1
            # 'ffmpeg', '-f', 'concat', '-safe', '0', '-i', clip_list_file, '-c', 'copy', '-map', '0:v', '-map', '0:a', '-map', '0:s', '-y', output1
        ]
        print(' '.join(command))
        subprocess.run(command)
        self.logger.info('Merge Video Done')
        # 添加背景音乐
        # ffmpeg -i 1.mp4 -stream_loop -1 -i background.mp3 -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=3[audio]" -map 0:v:0 -map "[audio]" -c:v copy -shortest -y 1-mu.mp4
        subtitle_file = self.subtitle_file.replace(os.sep,"/") # 替换路径分隔符为'/'
        output2 = os.path.join(self.outdir, f'{self.outname}_music.mp4')
        # -vf "subtitles=sub.srt" 
        command = [
            'ffmpeg', '-i', output1, '-stream_loop', '-1','-i', 'background.mp3', '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=3[audio]', '-map', '0:v:0', '-map', '[audio]','-c:v', 'copy', '-c:a', 'aac', '-shortest', '-y', output2
            
            # 同时添加字幕失败
            # 'ffmpeg', '-i', output1, '-stream_loop', '-1','-i', 'background.mp3', '-i', subtitle_file
            # , '-map', '0:v', '-map', '0:a', '-map', '1:a', '-map', '2:s'
            # , '-metadata:s:s:0', 'language=chi'
            # , '-c:v', 'copy', '-c:a:0', 'copy', '-c:a:1', 'aac', '-c:s', 'mov_text', '-shortest', '-y', output2
        ]
        print(' '.join(command))
        subprocess.run(command)
        self.logger.info('Add backgroud music Done')

        # 添加字幕
        command = [
            # 软字幕：默认开户，可以关闭字幕;
            # mp4: 播放时不能默认打开字幕，需要手动打开
            # 'ffmpeg', '-i', output2, '-i', subtitle_file,'-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'title="default"', '-disposition:s:0', 'default', '-y', f'{self.outdir}/output_subtitles.mp4'
            # mkv: 播放时默认打开字幕
            'ffmpeg', '-i', output2, '-i', subtitle_file,'-c:v', 'copy', '-c:a', 'copy', '-c:s', 'srt', '-metadata:s:s:0', 'title="default"', '-disposition:s:0', 'default', '-y', f'{self.outdir}/{self.outname}_subtitles.mkv'
            # 硬字幕：视频重新编码，无法关闭字幕
            # 'ffmpeg', '-i', output2, '-vf', f'subtitles={subtitle_file}','-c:v', 'copy', '-c:a', 'copy', '-y', output3
        ]
        print(' '.join(command))
        subprocess.run(command)
        self.logger.info('Add subtitles Done')


    def append_srt_content(self, textfile, duration):
        """
            生成 SRT 字幕内容。根据句号分隔为多个字幕，每个字幕持续时间根据整个duration按比例计算。
        """
        # 读取文本文件的内容
        with open(textfile, 'r', encoding='utf8') as f:
            text = f.read()
            # 将文本按句号分隔为多个字幕(注意：小数点不能做为句号)
            texts = text.replace('\n','').replace('。','. ').strip().strip('.').split('. ')
            # 去掉空白字符的句子
            texts = [t.strip() for t in texts if len(t.strip()) > 0]
            srt_content = []

            # 计算每句的时长，生成字幕内容并追加到self.srt_content
            if len(texts) == 0:
                self.srt_idx += 1
                srt_content = generate_srt("No sentences here.", self.srt_idx, self.srt_start, duration)
                self.srt_start = self.srt_start + duration
            elif len(texts) == 1:
                self.srt_idx += 1
                srt_content = generate_srt(texts[0], self.srt_idx, self.srt_start, duration)
                self.srt_start = self.srt_start + duration
            else:
                # 按句计算总字符数,及每字所占时长
                count = sum([len(t.strip()) for t in texts])
                word_duration = duration / count
                # 根据每个句子所占比例的时长，生成多句字幕
                # start_time = 0
                for text in texts:
                    x = len(text)
                    sentence_duration = x * word_duration
                    self.srt_idx += 1
                    srt_content.extend(generate_srt(text, self.srt_idx, self.srt_start, sentence_duration)) 
                    
                    # 更新下一个句子的开始时间
                    self.srt_start = self.srt_start + sentence_duration
            # 追加到self.srt_content
            self.srt_content.extend(srt_content)
            
    def gen_full_srt_file(self):
        """
        生成完整的 SRT 字幕文件。
        """
        for textfile in self.textpaths:
            duration = self.audio_durations.get(textfile)
            self.append_srt_content(textfile, duration)

        with open(self.subtitle_file, 'w', encoding='utf8') as f:
            for line in self.srt_content:
                f.write(line)

    def gen_srt_file(self, text, duration, output_file="subtitle.srt"):
        """
        生成 SRT 字幕文件。根据句号分隔为多个字幕，每个字幕持续时间根据整个duration按比例计算

        Args:
            text (str): 字幕文本。
            duration (float, optional): 字幕持续的时间，以秒为单位。默认为5秒。
            output_file (str, optional): 输出的 SRT 文件名。默认为 "subtitle.srt"。

        Returns:
            None
        """
        # 将文本按句号分隔为多个字幕(注意：小数点不能做为句号)
        texts = text.replace('\n','').replace('。','. ').strip().strip('.').split('. ')
        # 去掉空白字符的句子
        texts = [t.strip() for t in texts if len(t.strip()) > 0]
        srt_content = []

        if len(texts) == 0:
            srt_content = generate_srt("No sentences here.", 1, 0, duration)
        elif len(texts) == 1:
            srt_content = generate_srt(texts[0], 1, 0, duration)
        else:
            # 按句计算总字符数,及每字所占时长
            count = sum([len(t.strip()) for t in texts])
            word_duration = duration / count
            # 根据每个句子所占比例的时长，生成多句字幕
            start_time = 0
            for i, text in enumerate(texts):
                x = len(text)
                sentence_duration = x * word_duration
                srt_content.extend(generate_srt(text, i+1, start_time, sentence_duration)) 

                # 更新下一个句子的开始时间
                start_time = start_time + sentence_duration

        # 写入 SRT 文件
        with open(output_file, "w", encoding="utf-8") as file:
            for line in srt_content:
                file.write(line)
    
    def check_input_files(self):
        '''检查文件夹内的图片对应的文本文件，若不存在，则根据article.txt分拆生成'''
        article_file = os.path.join(self.indir, 'article.txt')
        if os.path.exists(article_file):
    
            # List all image files
            image_files = [f for f in os.listdir(self.indir) if f.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.jfif'))]
            if len(image_files) == 0:
                self.logger.error('No image files found. exit.')
                sys.exit(1)
                return
            text_files = [f for f in os.listdir(self.indir) if f.endswith('.txt') and f != 'article.txt']
            if len(text_files) > 0:
                self.logger.info('Some txt files exist. you can delete them and recreate them.')
                return
            
            # Check if .txt exists
            # count = 0 
            # for image_file in image_files:
            #     text_file = os.path.join(self.indir, image_file.rsplit('.', 1)[0] + '.txt')
            #     if text_file in text_files:
            #         count += 1
            
            # if count == len(image_files):
            #     self.logger.info('All txt files exist.')
            #     return
            
        
            self.logger.info("picture's txt files not exist, generate them...")

            # Read the content of article.txt
            try:
                with open(os.path.join(self.indir, 'article.txt'), 'r', encoding='utf-8') as f:
                    article_content = f.read()
                    # max_len = math.ceil(len(article_content / len(image_files)))
                    # Split the article content into paragraphs
                    paragraphs = split_text_by_count(article_content, len(image_files))
                
                    # Check each image file
                    for i, image_file in enumerate(image_files):
                        text_file = os.path.join(self.indir, image_file.rsplit('.', 1)[0] + '.txt')
                        if not os.path.exists(text_file):
                            # If the text file does not exist, generate it using a paragraph from the article
                            if i < len(paragraphs):
                                with open(text_file, 'w', encoding='utf-8') as f:
                                    f.write(paragraphs[i])
                            else:
                                self.logger.warning(f'No more paragraphs in article.txt for {text_file}')
            except FileNotFoundError:
                self.logger.error('article.txt not found')
            except Exception as e:
                self.logger.error(f'Error generating text files: {e}')

def get_mp3_duration(mp3path):
    audio_clip = AudioFileClip(mp3path)
    audio_duration = audio_clip.duration
    audio_clip.close()
    return audio_duration  

def generate_srt(text, index=1, start_time=0, duration=5):
    """
    生成 SRT 字幕文件。

    Args:
        text (str): 字幕文本。
        index (int, optional): 字幕的序号。默认为1。
        start_time (float, optional): 字幕开始的时间，以秒为单位。默认为0。
        duration (float, optional): 字幕持续的时间，以秒为单位。默认为5秒。

    Returns:
        None
    """
    start_timestamp = format_time(start_time)
    end_timestamp = format_time(start_time + duration)
    return [f"{index}\n", f"{start_timestamp} --> {end_timestamp}\n", f"{text}\n"]
    
def format_time(seconds):
    # 将秒数转换为时间戳格式 (hh:mm:ss,ms)
    H = int(seconds // 3600)
    M = int((seconds % 3600) // 60)
    S = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{H:02d}:{M:02d}:{S:02d},{milliseconds:03d}"
    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Video Maker')
    parser.add_argument('-i', '--input', type=str, default='./input', help='image dir')
    parser.add_argument('-o', '--output', type=str, default='./output', help='output dir')
    args = parser.parse_args()
    
    maker = VideoMaker(args.input, args.output, 'output')
    maker.run()
    