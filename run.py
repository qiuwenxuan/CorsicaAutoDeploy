import argparse
import os

from cloudsupported.cloud_deploy import CloudDeploy, recover_bm_config
from common.utils.deploy_util import reboot_n2_by_bmc, dowload_all_file
from firmware.imu.imu_deploy import IMUDeploy
from firmware.scp.scp_deploy import SCPDeploy
import logging

logging.basicConfig(level=logging.INFO)  # 配置日志级别为INFO


def main():
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='自动化部署')

    # 添加命令行参数
    parser.add_argument('-s', '--scp', action='store_true',
                        help='部署SCP环境')
    # 添加命令行参数
    parser.add_argument('-i', '--imu', action='store_true',
                        help='部署IMU环境')

    # 添加命令行参数
    parser.add_argument('-c', action='store_true',
                        help='部署cloud support环境')

    # 添加命令行参数
    parser.add_argument('-r', '--recover', action='store_true',
                        help='恢复配置文件')

    # 添加命令行参数
    parser.add_argument('--reboot', action='store_true',
                        help='重启n2')

    # 添加命令行参数
    parser.add_argument('--release', action='store_true',
                        help='拉取业务的release版本文件')

    # 添加命令行参数
    parser.add_argument('--deploy-all', action='store_true',
                        help='一次性部署所有环境！(imu, scp, 业务版本)')

    # 添加命令行参数
    parser.add_argument('-d', '--date', type=str,
                        help='指定要下载的版本文件日期')
    # 添加命令行参数
    parser.add_argument('-u', '--url', type=str,
                        help='指定要下载的版本文件地址(URL)')

    # 添加命令行参数
    parser.add_argument('--search-url', type=str,
                        help='指定搜索的网址')

    # 添加命令行参数
    parser.add_argument('--jmnd-config', type=str,
                        help='指定jmnd部署模块')

    # 添加命令行参数
    parser.add_argument('--url-pattern', type=str,
                        help='指定版本文件的模式')

    # 添加命令行参数
    parser.add_argument('--config', type=str, default=None,
                        help='指定配置文件的路径')

    # 添加deploy all所需的参数
    parser.add_argument('--cloud-url', type=str,
                        help='指定业务版本的下载地址')
    parser.add_argument('--imu-url', type=str,
                        help='指定Imu版本的下载地址')
    parser.add_argument('--scp-url', type=str,
                        help='指定Scp版本的下载地址')

    # 解析命令行参数
    args = parser.parse_args()

    # 统计变量为True的数量
    count = args.scp + args.imu + args.c
    is_deploy = count == 1
    if args.c:
        if args.jmnd_config:
            assert args.jmnd_config in ['cloud', 'net'], "未知的jmnd部署模块"
        else:
            raise ValueError("-c 参数后需要接 --jmnd-config 参数指定jmnd部署模块['cloud', 'net']")

    if args.recover and not is_deploy:  # 恢复和部署不能同时进行
        recover_bm_config(args.config)
    elif is_deploy and not args.recover:
        search_url = args.search_url
        url_pattern = args.url_pattern
        if args.scp:
            scp_deploy_obj = SCPDeploy(args.date, args.url, search_url, url_pattern, args.config)
            scp_deploy_obj.deploy()
        elif args.imu:
            imu_deploy_obj = IMUDeploy(args.date, args.url, search_url, url_pattern, args.config)
            imu_deploy_obj.deploy()
        elif args.c:
            cloud_deploy_obj = CloudDeploy(args.date, args.url, search_url, url_pattern, args.release, args.config,
                                           args.jmnd_config)
            cloud_deploy_obj.deploy()
    elif args.reboot:
        reboot_n2_by_bmc(args.config)
    elif args.deploy_all:
        # 先清除version文件夹下的文件
        os.system('rm -rf ./version/*')

        # 先下载全部的版本文件，然后调用三个类的deploy方法
        cloud_version_filename, imu_version_filename, scp_version_filename = dowload_all_file(cloud_url=args.cloud_url,
                                                                                              imu_url=args.imu_url,
                                                                                              scp_url=args.scp_url,
                                                                                              release=args.release,
                                                                                              config_filepath=args.config)

        # 创建三个部署类
        cloud_deploy_obj = CloudDeploy(release=args.release, config=args.config,
                                       version_filename=cloud_version_filename)
        scp_deploy_obj = SCPDeploy(config=args.config, version_filename=scp_version_filename)
        imu_deploy_obj = IMUDeploy(config=args.config, version_filename=imu_version_filename)

        # 调用三个类的部署方法
        scp_deploy_obj.deploy()
        imu_deploy_obj.deploy()
        reboot_n2_by_bmc(args.config)  # 先重启n2，准备部署业务版本
        cloud_deploy_obj.deploy()
    else:
        # 说明用户要么同时部署与恢复了，要么指定的部署的环境数量不等于1（count != 1)
        raise ValueError("恢复和部署不可同时进行，如果想要部署环境，则指定1个环境类型(-s or -i or -c)")


if __name__ == '__main__':
    main()
