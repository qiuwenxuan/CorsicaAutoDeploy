class GetNetworkInterfaceError(Exception):
    def __init__(self, message):
        # 调用父类的构造函数并传递错误消息
        super().__init__(message)
        self.error_code = 101  # 可以添加自定义的错误代码


class GetVirtioBlkError(Exception):
    def __init__(self, message):
        # 调用父类的构造函数并传递错误消息
        super().__init__(message)
        self.error_code = 102  # 可以添加自定义的错误代码


class ENVError(Exception):
    def __init__(self, message):
        # 调用父类的构造函数并传递错误消息
        super().__init__(message)
        self.error_code = 103  # 可以添加自定义的错误代码


class Error(Exception):
    def __init__(self, message):
        # 调用父类的构造函数并传递错误消息
        super().__init__(message)
        self.error_code = 104  # 可以添加自定义的错误代码


class TYPEError(Exception):
    def __init__(self, message):
        # 调用父类的构造函数并传递错误消息
        super().__init__(message)
        self.error_code = 105  # 可以添加自定义的错误代码