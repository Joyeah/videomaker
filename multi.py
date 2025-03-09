

from maker import VideoMaker


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Multiple Video Maker')
    parser.add_argument('--root', type=str, default='./input', help='image root forlder ')
    parser.add_argument('--output', type=str, default='./output', help='video output forlder')
    args = parser.parse_args()
    
    # 遍历所有文本夹
    import os
    n = 0
    for dir in os.listdir(args.root):
        if not os.path.isdir(os.path.join(args.root, dir)):
            continue
        n += 1
        print(f'{n}-Processing {dir}')
        maker = VideoMaker(os.path.join(args.root, dir), args.output)
        maker.run()

    if n == 0:
        print(f"{args.root} has No sub folder found")
    else:
        print(f'Done. Processed {n} folders.')