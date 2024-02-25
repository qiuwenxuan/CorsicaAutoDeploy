import paramiko
import time
import threading
import sys


class SSHShellSerial:
    def __init__(self, sshclient, mux):
        self.shell = None
        self.sshclient = sshclient
        self.mux = mux
        self.rcv_time_step = 0.1
        self.default_end_list = ['$ ', '# ']

    def __del__(self):
        self.close()

    def set_default_end_list(self, end_list):
        self.default_end_list = end_list

    def check_end(self, strData, endlist):
        for sub in endlist:
            if strData.endswith(sub):
                return True
        return False

    def rcv_for_ever(self, mod='show_only', timeout=0, timoutflg=True):
        return self.rcv(end_list=[], mod=mod, timeout=timeout, timoutflg=timoutflg)

    def thread_rcv(self, end_list=None, timeout=0):
        cur_end_list = []
        if end_list is not None:
            cur_end_list = end_list

        curthread = threading.Thread(target=self.rcv, kwargs={'end_list': cur_end_list,
                                                              'timeout': timeout, 'timoutflg': False})
        curthread.start()
        # curthread.join(timeout=100)
        return curthread

    def rcv(self, end_list=None, mod='show_only', timeout=0, timoutflg=True):
        if end_list is not None:
            full_end_list = end_list
        else:
            full_end_list = self.default_end_list
        ret = ''
        if not self.shell:
            return ret
        fulltime = 0
        endexit = False
        while True:
            self.mux.acquire()
            while self.shell.recv_ready():
                currcv = self.shell.recv(1024)
                if len(currcv) == 0:
                    endexit = True

                try:
                    curStr = currcv.decode(encoding='UTF-8')
                except BaseException as e:
                    try:
                        curStr = currcv.decode(encoding='GBK')
                    except BaseException as ee:
                        print(ee)
                        curStr = str(currcv)

                ret += curStr
                if mod == 'show_only':
                    print(curStr, end='')
                    sys.stdout.flush()
                    if len(ret) > 1000:
                        ret = ret[900:]
                elif mod == 'all':
                    print(curStr, end='')
                    sys.stdout.flush()
                elif mod == 'none':
                    pass
            self.mux.release()

            if self.shell.exit_status_ready():
                break

            if endexit:
                break

            if self.check_end(ret, full_end_list):
                endexit = True

            if 0 < timeout < fulltime:
                if timoutflg:
                    print('INTERNAL_ERR_TIMEOUT')
                    ret += 'INTERNAL_ERR_TIMEOUT'
                break

            time.sleep(self.rcv_time_step)
            fulltime += self.rcv_time_step

        return ret

    def open(self, rcv_end_list=None, timeout=120):
        self.shell = self.sshclient.invoke_shell()
        self.shell.resize_pty(width=180, height=200)
        self.rcv(mod='none', end_list=rcv_end_list, timeout=timeout)

    def run(self, command, rcv_end_list=None, mod='show_only', sleep=1, enter=0, timeout=180, timoutflg=True):
        ret = ''
        if self.shell:
            self.shell.sendall(command + '\r')
            for i in range(0, enter):
                time.sleep(sleep)
                self.shell.sendall('\r')
            ret = self.rcv(end_list=rcv_end_list, mod=mod, timeout=timeout, timoutflg=timoutflg)
        return ret

    def sendbytepretty(self, m, delay=0.1):
        for sub in m:
            self.sendbyte(sub)
            time.sleep(delay)

    def sendbyte(self, m):
        self.mux.acquire()
        if self.shell:
            self.shell.sendall(m)
        self.mux.release()

    def sendcmdpretty(self, m, delay=0.1, sleep=1):
        self.sendbytepretty(m, delay=delay)
        self.sendbyte('\r')
        time.sleep(sleep)

    def sendcmd(self, m, sleep=1):
        self.mux.acquire()
        if self.shell:
            self.shell.sendall(m)
            self.shell.sendall('\r')
        self.mux.release()
        time.sleep(sleep)

    def close(self):
        if self.shell:
            self.shell.close()
            status = self.shell.recv_exit_status()
            print(f'close shell: {status},', self.shell.exit_status_ready())
            # self.shell = None

    def run_by_auth(self, command, passwd, rcv_end_list=None):
        ret = True
        if rcv_end_list is None:
            end_list = self.default_end_list + ['： ', ': ']
        else:
            end_list = rcv_end_list + ['： ', ': ']
        info = self.run(command, rcv_end_list=end_list)
        if info.endswith(': ') or info.endswith('： '):
            result = self.run(passwd, rcv_end_list=rcv_end_list)
            ret = self.check_resp_connect(result)
        return ret

    def check_resp_connect(self, info):
        resp_fail_list = [
            'Permission denied',
            'INTERNAL_ERR_TIMEOUT',
            'No route to host',
            'Connection refused',
            'Connection reset by peer'
        ]

        for sub in resp_fail_list:
            if info.find(sub) != -1:
                return False
        return True

    def run_by_auth_yes(self, command, passwd, timeout=0):
        info = self.run(command, rcv_end_list=self.default_end_list + ['： ', ': ', ')? '], timeout=timeout)
        if info.endswith(')? '):
            ret = self.run_by_auth('yes', passwd)
        elif info.endswith(': ') or info.endswith('： '):
            result = self.run(passwd)
            ret = self.check_resp_connect(result)
        else:
            ret = self.check_resp_connect(info)
        return ret

    def su_login(self, passwd):
        return self.run_by_auth('sudo su', passwd)

    def scp(self, src, dest, passwd):
        return self.run_by_auth_yes('scp -r %s %s' % (src, dest), passwd)

    def enter_manual(self):
        from common.base_common import thread_stop, key_press
        print('enter manual mode, enter ctrl+D to continue when finished')
        self.run('')
        cur_thread = self.thread_rcv()
        keyentry = key_press.Keypress()
        keyentry.enable_input_mod()
        while True:
            c = keyentry.getch()
            if not cur_thread.is_alive():
                break
            elif c == '\x04':
                thread_stop.stop_thread(cur_thread)
                while not cur_thread.is_alive():
                    time.sleep(1)
                break
            self.sendbyte(c)
        del keyentry
        print('enter auto mode')
        self.run('', timeout=3)

    def auto_console(self, userfunc=None):
        curthread = threading.Thread(target=userfunc, args=[self])
        curthread.start()
        return curthread


class SSHShell:
    shell = None
    thread = None

    def __init__(self, sshclient, mux):
        self.sshclient = sshclient
        self.mux = mux
        self.thread_on = False
        self.show_rcv = False

    def __del__(self):
        self.close()

    def process_rcv(self):
        if not self.shell:
            return
        while self.thread_on:
            self.mux.acquire()
            while self.shell.recv_ready():
                currcv = self.shell.recv(1024)
                if self.show_rcv:
                    print(currcv.decode(), end='')
            self.mux.release()

            time.sleep(0.1)

    def open(self):
        self.shell = self.sshclient.invoke_shell()
        self.thread = threading.Thread(target=self.process_rcv)
        # self.thread.setDaemon(True)
        self.thread_on = True
        self.thread.start()
        time.sleep(1)
        self.show_rcv = True
        self.run('')

    def run(self, command):
        if self.shell:
            self.shell.sendall(command + "\n")
        else:
            print("Shell not opened.")

    def close(self):
        if self.shell:
            self.shell.close()
            self.shell = None
        if self.thread:
            self.thread_on = False
            self.thread = None


class SSHSessions:
    thread_list = []
    client = None

    def __init__(self, address, username, password, port=22):
        print("Connecting to server on ip", str(address) + ":"+str(port)+".")
        self.address = address
        self.username = username
        self.password = password
        self.port = port
        self.mux = threading.Lock()
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        # self.client.connect(address, username=username, password=password, port=port, look_for_keys=False)

    def __del__(self):
        self.close()

    def connect(self):
        try:
            self.client.connect(self.address, username=self.username, password=self.password,
                                port=self.port, look_for_keys=False)
        except BaseException as e:
            print(e)
            return -1
        return 0

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            print('close session')

    def open_shell(self, rcv_end_list=None, timeout=0):
        shell = SSHShellSerial(self.client, mux=self.mux)
        shell.open(rcv_end_list=rcv_end_list, timeout=timeout)
        return shell

    def shell_run(self, userFunc, rcv_end_list=None, timeout=0, param=None):
        shell = SSHShellSerial(self.client, mux=self.mux)
        shell.open(rcv_end_list=rcv_end_list, timeout=timeout)
        ret = userFunc(shell, param=param)
        shell.close()
        return ret

    def thread_shell_run(self, userFunc, rcv_end_list=None, timeout=0, param=None):
        curthread = threading.Thread(target=self.shell_run, args=[userFunc],
                                     kwargs={'rcv_end_list': rcv_end_list,
                                             'timeout': timeout, 'param': param})
        curthread.start()
        self.thread_list += [curthread]

    def thread_join_all(self):
        for subthread in self.thread_list:
            subthread.join()

    def execute_command(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode()

    def shell_scp(self, src, dest, passwd, rcv_end_list=None, timeout=30):
        shell = SSHShellSerial(self.client, mux=self.mux)
        shell.open(rcv_end_list=rcv_end_list, timeout=timeout)
        ret = shell.scp(src, dest, passwd)
        shell.close()
        return ret


def test():
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    try:
        client.connect('10.20.25.22', username='jaguar', password='jaguar', look_for_keys=False)
    except BaseException as e:
        print(e)

    shell = client.invoke_shell()
    # shell.recv_exit_status()
    print(shell.exit_status_ready())


if __name__ == '__main__':
    test()
