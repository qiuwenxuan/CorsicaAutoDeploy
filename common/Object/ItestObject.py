from enum import Enum, auto


class EnvironmentType(Enum):
    EMU = auto()
    SIM = auto()
    HYBRID = auto()
    CRB = auto()


class DevType(Enum):
    LEGACY = auto()
    MODERN = auto()
    PACKED = auto()  # 保留字段，目前SIM 没有这样环境
    NVME = auto()


class ItestObject:
    def __init__(self, env_type, dev_type):
        if (env_type not in {EnvironmentType.SIM, EnvironmentType.EMU, EnvironmentType.HYBRID,EnvironmentType.CRB} and \
                dev_type not in {DevType.LEGACY, DevType.MODERN, DevType.NVME, DevType.PACKED}):
            raise ValueError(f"Invalid environment and subtype combination.env_type={env_type},dev_type={dev_type}")

        self._env_type = env_type
        self._dev_type = dev_type

    def describe(self):
        return f"Environment ({self._env_type.name} env_type, {self._dev_type.name} dev_type) "

    def get_env_type(self):
        return self._env_type

    def get_dev_type(self):
        return self._dev_type


def main():
    hardware_env = ItestObject(EnvironmentType.EMU, DevType.LEGACY)
    software_env = ItestObject(EnvironmentType.SIM, DevType.NVME)
    hybrid_env = ItestObject(EnvironmentType.HYBRID, DevType.NVME)
    print(hardware_env.describe())
    print(software_env.describe())
    print(hybrid_env.describe())


if __name__ == "__main__":
    main()
