
import sys
import termios
import tty


class Keypress:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)

    def enable_input_mod(self):
        tty.setraw(self.fd)

    def disable_input_mod(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def getch(self):
        return sys.stdin.read(1)

    def __del__(self):
        self.disable_input_mod()


if __name__ == '__main__':
    entry = Keypress()
    entry.enable_input_mod()
    while True:
        c = entry.getch()
        print('d:', c)
