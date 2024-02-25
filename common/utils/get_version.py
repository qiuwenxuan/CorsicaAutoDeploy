import os
import sys



__path = os.path.realpath(os.path.join(__file__, '..', '..', '..'))
if __path not in sys.path: sys.path.append(__path)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

print(__path)


class GetVersion:
    def get_version(self, url, download_dir):
        cmd = f'wget -P {download_dir} {url}'
        os.system(cmd)
