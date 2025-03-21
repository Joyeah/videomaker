# videomaker
批量图片生成视频

## 环境依赖
- python 3
- ffmpeg
- moviepy
- pyttsx3

## 功能
- 支持批量图片生成视频，图片格式为'.jpg', '.png', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.jfif'
- TTS
- 支持生成字幕
- 背景音乐

## maker.py的使用方法
第一步：准备图片和文字,将图片和文字放在input文件夹下
第二步：运行py maker.py
第三步：在output文件夹下查看生成的视频

## 图片和文字命名规则
### 方式一
图片文件名与文本文件名一一对应，例如：
```shell
├── input
│   ├── aaa.jpg
│   ├── aaa.txt
│   ├── bbb.jpg
│   ├── bbb.txt
│   ├── ccc.jpg
│   └── ccc.txt
```

### 方式二
全部文字保存在article.txt中，例如：
```shell
├── input
│   ├── aaa.jpg
│   ├── bbb.jpg
│   └── ccc.jpg
    └── article.txt
```
程序会自动根据图片文件名将article.txt中的内容分割成对应的文本文件。

## multi.py的使用方式
1. 在input文件夹建立多个子文件夹，每个文件夹放入同一视频的素材文件
2. 运行py multi.py
3. 在output文件夹中查看生成的结果

# TODO
- [ ] scrapy文字页面+提取关键词+搜索图片，生成素材文件夹，然后生成视频
- [✓] 支持多个视频生成
- [ ] 支持自定义视频参数，输出不同的视频格式

